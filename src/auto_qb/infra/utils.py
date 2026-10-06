"""通用工具函数: 解析器 / 路径 / 文件检查 / tracker 匹配

全部解析与检查函数集中于此, 供主程序(config/manager/exporter)与规则框架共用,
避免各模块重复实现。
"""
import base64
import json
import math
import os
import shutil
import tempfile
import hashlib
from functools import lru_cache
import re
import subprocess
import sys
import threading
import time
import logging
from dataclasses import dataclass
from datetime import time as dtime
from functools import wraps
from urllib.parse import urlparse
from typing import List

logger = logging.getLogger(__name__)

# atomic_write(keep_backup=True) 的备份后缀 —— 写侧与回退侧(state 恢复)共用同一常量,
# 防两侧命名漂移: 备份写出去却没人按同名读回来, 恢复分支就永远走不到(issue 26-09-21-1347)。
BACKUP_SUFFIX = ".bak"

# atomic_write 的临时文件后缀(写侧与启动清理侧共用同一常量, 理由同 BACKUP_SUFFIX)
TMP_SUFFIX = ".tmp"

# 匹配语法常量(用户配置的统一匹配语法, 解析唯一入口见 MatchPattern)
REGEX_PREFIX = "regex:"
IGNORE_CASE_SUFFIX = ":ignore_case"


def parse_hm(text: str) -> "tuple[int, int]":
    """解析 "HH:MM" -> (时, 分); 非法格式或越界(须 00:00-23:59)抛 ValueError
    (date_time 条件与通知免打扰时段共用, 越界提早暴露防运行时静默失配)"""
    try:
        h, m = str(text).strip().split(":")
        hour, minute = int(h), int(m)
    except ValueError as e:
        raise ValueError(f"非法 HH:MM 格式: {text}") from e
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"时间越界(须 00:00-23:59): {text}")
    return hour, minute


def time_in_range(now: dtime, spec: str) -> bool:
    """当前时刻是否在 "HH:MM-HH:MM" 区间内(支持跨午夜, 如 "23:00-08:00"; date_time 条件与通知共用)"""
    start_s, end_s = str(spec).split("-", 1)
    t_start = dtime(*parse_hm(start_s))
    t_end = dtime(*parse_hm(end_s))
    if t_start <= t_end:
        return t_start <= now <= t_end
    return now >= t_start or now <= t_end  # 跨午夜: 不在 start-24:00 即在 00:00-end


def atomic_write(path: str, write_fn, keep_backup: bool = False) -> None:
    """原子写盘: 同目录临时文件 -> fsync -> os.replace(Windows 上为原子替换)

    直接 `open(path, "w")` 会先 truncate 旧文件: 写盘途中被杀 / 磁盘满 / 序列化抛异常都会留下
    **半截文件**, 而 state.json 无备份 ⇒ 执行历史与去重记录全丢(规则重放)。本函数保证
    目标路径要么完全是旧内容, 要么完全是新内容。

    keep_backup=True 时先把当前文件复制为 `<path>.bak`(仅在写盘前存在旧文件时), 用于
    兜住"新内容本身是错的"这类非截断型损坏。临时文件与失败清理都由本函数负责。

    !空路径直接报错(不静默兜底): `abspath("")` 是 CWD, `dirname` 再取一级就成了 **CWD 的父目录**
    —— 空路径不会"什么都不写", 而是把临时文件丢到仓库外面(实测: 在 `.../auto-qb-clone1` 下跑
    测试会在 `.../` 留下 `.xxxxxxxx.tmp`), 随后 `os.replace(tmp, "")` 失败再把它删掉, 表现为
    "偶发、无害"的噪音, 实为调用方漏传路径。配置层已校验 `state_file` 等非空(见 config/validation),
    走到这里的空路径是编程错误, 应当早暴露。
    """
    if not path:
        raise ValueError("atomic_write: path 不能为空(空路径会把临时文件写到 CWD 的父目录)")
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    if keep_backup and os.path.exists(path):
        try:
            shutil.copy2(path, path + BACKUP_SUFFIX)
        except OSError as e:
            logger.warning(f"备份 {path} 失败(继续写盘): {e}")
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=os.path.basename(path) + ".", suffix=TMP_SUFFIX)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            write_fn(f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):  # os.replace 已成功时临时文件不存在, 不该再删
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def parse_bool(value) -> bool:
    """将字符串或布尔值转换为布尔值"""
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"无效布尔值: {value}")


def convert_bool_in_dict(d):
    """递归地将字典中的字符串布尔值转换为bool类型(纯数字字符串保持原样)"""
    if isinstance(d, str):
        try:
            d = parse_bool(d)
        except ValueError:
            pass

    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str) and not v.isdecimal():
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, dict):
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, list):
                # 列表元素与字典分支同口径(26-10-06-0028 H-03): 纯数字串跳过, 其余递归 ——
                # 无条件递归会把列表里的 "1"/"on" 改写成 True/False(导出模板回填类型漂移)
                d[k] = [
                    item if isinstance(item, str) and item.isdecimal() else convert_bool_in_dict(item) for item in v
                ]

    return d


def parse_time(time_str: str) -> float:
    """时间字符串(如 '3D', '12H', '10M') -> 秒; 空串返回0"""
    if not time_str:
        return 0
    units = {"S": 1, "M": 60, "H": 3600, "D": 86400}
    m = re.match(r"^([\d.]+)\s*([SMHD])$", str(time_str).strip().upper())
    if not m:
        raise ValueError(f"无效时间格式: {time_str}")
    value, unit = m.groups()
    return float(value) * units[unit]


def parse_fsize(fsize_str: str) -> int:
    """大小字符串(如 '10.5 GiB') -> 字节; 仅支持二进制单位: B, KiB, MiB, GiB, TiB, PiB"""
    units = {
        "B": 1,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
        "TIB": 1024**4,
        "PIB": 1024**5,
    }
    m = re.match(r"^([\d.]+)\s*([KMGTP]?i?B)$", str(fsize_str).strip().upper(), re.IGNORECASE)
    if not m:
        raise ValueError(f"无效大小格式: {fsize_str}")
    value, unit = m.groups()
    if unit not in units:
        raise ValueError(f"无效大小格式(需使用iB单位, 如 10MiB): {fsize_str}")
    return int(float(value) * units[unit])


def parse_speed(speed_str: str) -> int:
    """速度字符串(如 '10MiB/s', '1000KiB/s') -> 字节/秒; 空串返回0"""
    if not speed_str:
        return 0
    units = {"B/S": 1, "KIB/S": 1024, "MIB/S": 1024**2, "GIB/S": 1024**3}
    m = re.match(r"^([\d.]+)\s*([KMG]?i?B/S)$", str(speed_str).strip().upper(), re.IGNORECASE)
    if not m:
        raise ValueError(f"无效速度格式: {speed_str}")
    value, unit = m.groups()
    return int(float(value) * units[unit])


def parse_hr_condition(cond_str) -> tuple:
    """解析HR触发条件字符串 -> ('dlratio', ratio) 或 ('dlsize', bytes)

    示例: "80%" -> ('dlratio', 0.8), "10MiB" -> ('dlsize', 字节); 缺省默认80%
    边界在解析单点拦下(校验层经 _try 复用): 百分比须 (0, 100] —— "0%"/负数会让条件立即满足
    (种子一入站就打 HR 标), ">100%" 永不触发, 均与配置意图相反; 下载量须 > 0("0MiB" 同样立即满足)
    """
    cond_str = str(cond_str).strip()
    if not cond_str:
        return ("dlratio", 0.8)  # 默认80%触发
    if cond_str.endswith("%"):  # 百分比, 如 "70%"
        ratio = float(cond_str[:-1]) / 100.0
        if not math.isfinite(ratio) or not 0 < ratio <= 1:
            raise ValueError(f"HR 百分比条件须 (0, 100]: {cond_str}")
        return ("dlratio", ratio)
    size = parse_fsize(cond_str)  # 下载量绝对值, 如 "10MiB"
    if size <= 0:
        raise ValueError(f"HR 下载量条件须 > 0: {cond_str}")
    return ("dlsize", size)


def is_windows() -> bool:
    """判断当前操作系统是否为 Windows"""
    return sys.platform.startswith("win")


def is_linux() -> bool:
    """判断当前操作系统是否为 Linux"""
    return sys.platform.startswith("linux")


def is_mac() -> bool:
    """判断当前操作系统是否为 MacOS"""
    return sys.platform.startswith("darwin")


def is_posix() -> bool:
    """判断当前操作系统是否为 Unix 类系统(包含 Linux、macOS、BSD 等)"""
    return sys.platform.startswith(('linux', 'darwin', 'freebsd', 'aix'))


def add_long_path_prefix_for_win(path: str) -> str:
    """为 Windows 文件路径添加长路径支持前缀(\\\\?\\ 或 UNC), 非Windows系统则返回原路径

    已绝对的 Windows 路径(已有 \\\\?\\ 前缀 / UNC \\\\ / 盘符 X:\\)直接加前缀,
    不经 os.path.abspath — 后者在 Linux CI 上(monkeypatch 模拟 win32 时)会用 Linux 语义
    把 Windows 路径当相对路径并拼上 cwd, 导致测试失败。仅对真正相对的路径才走 abspath。
    """
    if not is_windows():
        return path

    norm = path.replace("/", "\\")
    # 已有 \\?\ 前缀 -> 原样返回
    if norm.startswith("\\\\?\\"):
        return norm
    # UNC 路径 (\\server\share\...) -> \\?\UNC\server\share\...
    if norm.startswith("\\\\"):
        return "\\\\?\\UNC" + norm[1:]
    # 盘符路径 (C:\...) -> 已绝对, 直接加前缀
    if re.match(r"^[A-Za-z]:[\\/]", norm):
        return "\\\\?\\" + norm
    # 相对路径 -> 先转绝对路径再加前缀
    abs_path = os.path.abspath(norm).replace("/", "\\")
    return "\\\\?\\" + abs_path


def parse_compare(spec: str, value_parser):
    """解析比较表达式: '>=100MiB' -> ('>=', 字节); '<24H' -> ('<', 秒); 缺省为 '=='"""
    m = re.match(r"^\s*(>=|<=|>|<|==|=|!=)?\s*(.+?)\s*$", str(spec))
    if not m:
        raise ValueError(f"无效比较表达式: {spec}")
    op, rest = m.group(1), m.group(2)
    if op in (None, "="):
        op = "=="
    return op, value_parser(rest)


def compare(op: str, left, right) -> bool:
    """执行比较: op 为 >, <, >=, <=, !=, =="""
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == "!=":
        return left != right
    return left == right


def extract_tracker_hostnames(trackers_info: list) -> set:
    """从 tracker 信息列表提取去重的 hostname 集合"""
    hosts = set()
    for t in trackers_info:
        url = t.get("url")
        if not url:
            continue
        try:
            host = urlparse(url).hostname
            if host:
                hosts.add(host.lower())
        except Exception:
            continue
    return hosts


# sanitize_tracker_url 解析失败时的占位串(与成功返回值同形状: 一眼能看出"这里本该有个地址")
SANITIZE_FALLBACK = "<invalid-url>"


def sanitize_tracker_url(url) -> str:
    """把 tracker URL 脱敏成"主地址": 只留 scheme://host[:port], 丢弃 path / query / fragment

    设计取舍(issue 26-09-21-1408): 私站 announce URL 的凭据参数**名不统一** —— passkey 只是最常见
    的一种, 实际还有 authkey / token / key / uid / secret 等任意命名, 按参数名黑名单剥离必然漏网
    (漏一个名字就等于漏一个站)。所以这里**不猜参数名**, 直接把 path 与 query 整段丢掉:
    排查只需要"哪个站"的信息(主地址已足够), 而任何形态、任何命名的凭据都在被丢弃的那一段里。

    - 凭据也可能藏在 userinfo 里(`http://user:pass@host/announce`), 故 netloc 只取 `@` 之后的部分。
    - 入参异常(空 / 非字符串 / 无法解析)一律返回 SANITIZE_FALLBACK, **绝不抛异常** —— 调用方都在
      日志路径上, 脱敏失败不该把业务动作(qB 写操作)打断。
    """
    if not isinstance(url, str):
        return SANITIZE_FALLBACK
    raw = url.strip()
    if not raw:
        return SANITIZE_FALLBACK
    try:
        parts = urlparse(raw)
    except Exception:
        return SANITIZE_FALLBACK
    # scheme 缺失时 urlparse 把 host 落进 path, 取首段兜底; 带 `@` 时取其后半(去 userinfo)
    netloc = (parts.netloc or "").rsplit("@", 1)[-1]
    if not netloc and parts.path:
        netloc = parts.path.split("/", 1)[0].rsplit("@", 1)[-1].split("?")[0]
    if not netloc:
        return SANITIZE_FALLBACK
    scheme = parts.scheme.lower()
    return f"{scheme}://{netloc.lower()}" if scheme else netloc.lower()


# 虚拟 tracker 条目前缀(DHT/PeX/LSD 与 qB 内部 "**" 标记): 非真实站点, 没有可脱敏的凭据,
# mask 原样透传。单点定义(计划 26-10-07-0055 S1): webui/views.py 引用本常量, 消双源字面量。
VIRTUAL_TRACKER_PREFIXES = ("**", "[DHT]", "[PeX]", "[LSD]")

# path 末段高熵判定(R5): >=16 位连续字母数字/下划线/连字符(首字符须为字母数字)视为可能藏凭据
_HIGH_ENTROPY_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{15,}$")


def _hash16(value: str) -> str:
    """R7 的 hash16: sha256 前 16 位 hex, 确定性不加盐(加盐则两次拉取值不同, 唯一性失效)"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def mask_tracker_url(url) -> str:
    """tracker URL 展示脱敏(方案 B, R1-R8): 保留结构与参数名, 所有"值"一律 hash

    与 sanitize_tracker_url(只留主地址, 排查用)不同, mask 的目标是**把 url 当内容标识用**:
    参数名/path 端点名可见(诊断价值), 凭据值不可见; 同 host 不同 path、同 path 不同凭据值
    的 mask 互异(R8, hash 保值差异) —— 删除定位才能拿 mask 比对原文(计划 26-10-07-0055)。

    - R1 虚拟条目("**"/"[DHT]"/"[PeX]"/"[LSD]" 开头, 含裸形态)原样透传: 在函数内挡掉,
      不依赖调用方过滤(sanitize 会把裸 "[DHT]" 小写破坏前缀识别, mask 不能踩同一个坑)。
    - R2 非字符串/空/解析不出 host -> SANITIZE_FALLBACK, 绝不抛异常(同 sanitize 口径:
      两侧同函数 => 比对一致; 多条不可解析 => 命中多条 => error 不猜)。
    - R3 scheme 保留并小写; 缺 scheme 时从 path 首段兜底取 host(镜像 sanitize 的处理)。
    - R4 netloc 去 userinfo(@ 之后), host 小写, 端口保留。
    - R5 path 保留; 末段 >=16 位高熵(可能藏 path 凭据)整段替换为 hash16, 其余原样; fragment 丢弃。
    - R6 query 按 & 拆段, 有 = 的段改写为 名=hash16(原值)——值取原文子串, 不做百分号解码;
      裸名参数原样; 段序不变。铁律: **不按参数名挑**, 所有值一律 hash(同 sanitize 的动机:
      passkey/authkey/token/uid/secret 任意私站命名同权, 黑名单必漏)。
    """
    if not isinstance(url, str):
        return SANITIZE_FALLBACK
    # R1: 原样透传(在 strip 之前判, 裸 "[DHT]" 才不会被后续路径破坏)
    if url.startswith(VIRTUAL_TRACKER_PREFIXES):
        return url
    raw = url.strip()
    if not raw:
        return SANITIZE_FALLBACK
    try:
        parts = urlparse(raw)
    except Exception:
        return SANITIZE_FALLBACK
    # R3/R4: netloc 取 @ 之后(去 userinfo); 缺 scheme 时 urlparse 把 host 落进 path,
    # 取首段兜底, 且首段已被当作 host 消费掉, 不再重复进 path
    netloc = (parts.netloc or "").rsplit("@", 1)[-1]
    path = parts.path or ""
    if not netloc and path:
        first, _, rest = path.partition("/")
        netloc = first.rsplit("@", 1)[-1].split("?")[0]
        # 首段已被当作 host 消费掉, 不再重复进 path; 分隔符 "/" 由 rest 补回
        path = f"/{rest}" if rest else ""
    if not netloc:
        return SANITIZE_FALLBACK
    # R5: 末段高熵整段换 hash(端点名 announce/announce.php 不命中, 保留诊断价值)
    if path:
        head, _, last = path.rpartition("/")
        if _HIGH_ENTROPY_SEGMENT_RE.match(last):
            path = f"{head}/{_hash16(last)}"
    # R6: query 全值 hash(不按参数名挑), 裸名参数原样, 段序不变
    query = parts.query or ""
    if query:
        segments = []
        for seg in query.split("&"):
            name, eq, value = seg.partition("=")
            segments.append(f"{name}={_hash16(value)}" if eq else seg)
        query = "&".join(segments)
    scheme = parts.scheme.lower()
    host_part = f"{scheme}://{netloc.lower()}" if scheme else netloc.lower()
    return host_part + path + (f"?{query}" if query else "")


def mask_tracker_entry(entry: dict) -> dict:
    """tracker 条目脱敏(R9): 只改 url 字段, 其余字段(status/msg/num_peers 等)原样不动

    条目缺 url 或命中 R1(虚拟条目)原样返回(同一对象, 不做无谓拷贝)。
    """
    url = entry.get("url") if isinstance(entry, dict) else None
    if not isinstance(url, str) or not url or url.startswith(VIRTUAL_TRACKER_PREFIXES):
        return entry
    return {**entry, "url": mask_tracker_url(url)}


# 展示口径的回环地址集合(IPv4 / IPv6 / IPv4-mapped / IPv6 全写法), 命中即统一显示成 localhost
DISPLAY_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1", "0:0:0:0:0:0:0:1"})


def display_host(host) -> str:
    """给用户看的地址: 回环地址一律写成 localhost, 其余(含对外地址)原样

    只改**展示**, 不动监听面(绑定仍用配置里的原值)。原因(2026-09-25 实测):
    浏览器把 `127.0.0.1` 与 `localhost` 视作**两个不同 origin**, localStorage(列偏好 / 登录态)
    各存一份, 而且 127.0.0.1 上的那份更容易被浏览器顺手清掉 —— 提示统一给 `localhost`,
    用户每次点开都是同一个 origin, 偏好不会"莫名其妙回默认"。

    - 入参异常(空 / 非字符串)原样返回: 调用方都在日志路径上, 不该因为取不到值就炸。
    """
    if not isinstance(host, str):
        return host
    raw = host.strip()
    return "localhost" if raw.lower() in DISPLAY_LOOPBACK_HOSTS else raw


def match_tracker_confs(trackers: dict, urls: list):
    """按 hostname 精确匹配 tracker 配置(含子域名), 返回所有匹配的 TrackerConfig"""
    hosts = set()
    for url in urls:
        try:
            host = urlparse(url).hostname
            if host:
                hosts.add(host.lower())
        except Exception:
            continue
    result = []
    for conf in trackers.values():
        for domain in conf.domains:
            domain = str(domain).lower()
            if any(host == domain or host.endswith("." + domain) for host in hosts):
                result.append(conf)
                break
    return result


@dataclass(frozen=True)
class MatchPattern:
    """单个匹配模式: 'regex:' 前缀(正则, re.search 子串匹配)与 ':ignore_case' 后缀的语法解析唯一入口

    解析顺序: 先剥 ':ignore_case' 后缀, 再识别 'regex:' 前缀
    (如 'regex:foo:ignore_case' => 正则 foo + 忽略大小写)。
    全项目所有该语法的解析(标签/分类/tracker/路径匹配、@tracker_tags 展开去重、
    config 正则校验)均经由本类, 不再各自手工剥离。
    """

    raw: str  # 原始模式串(含前缀与后缀)
    is_regex: bool  # 是否 'regex:' 前缀正则
    ignore_case: bool  # 是否 ':ignore_case' 后缀
    core: str  # 剥离前缀+后缀后的匹配主体

    @classmethod
    def parse(cls, raw: str) -> "MatchPattern":
        raw = str(raw)
        ignore_case = raw.endswith(IGNORE_CASE_SUFFIX)
        body = raw[:-len(IGNORE_CASE_SUFFIX)] if ignore_case else raw
        is_regex = body.startswith(REGEX_PREFIX)
        core = body[len(REGEX_PREFIX):] if is_regex else body
        return cls(raw=raw, is_regex=is_regex, ignore_case=ignore_case, core=core)

    @property
    def body(self) -> str:
        """保留 regex: 前缀、仅剥 :ignore_case 后缀的主体(@tracker_tags 展开去重用)"""
        return (REGEX_PREFIX if self.is_regex else "") + self.core

    @property
    def suffix(self) -> str:
        """:ignore_case 后缀(展开引用时回拼用), 未配置为空串"""
        return IGNORE_CASE_SUFFIX if self.ignore_case else ""

    def compile(self):
        """编译正则主体(flags 与运行时一致); 合法性由 config 校验阶段保证, 非法模式抛 re.error"""
        return re.compile(self.core, re.IGNORECASE if self.ignore_case else 0)


def match_value(value: str, patterns: List[str], normalize=None) -> bool:
    """候选值是否匹配任一模式 —— 标签/分类/tracker/路径匹配的唯一实现(语法见 MatchPattern)

    - 精确匹配: 字符串全等, 默认大小写敏感(':ignore_case' 后缀时两侧 lower 比较)
    - 'regex:' 前缀: re.search 子串匹配(':ignore_case' 对正则同样生效)
    - normalize: 匹配前对候选值与精确模式主体施加的规范化(如 path_normalize 统一斜杠);
      正则模式只对候选值规范化, 模式主体保持原样
    - 非法正则静默跳过(视为不匹配): 正常流程已在 config 校验阶段保证可编译
    """
    target = normalize(value) if normalize else value
    for raw in patterns or []:
        if not raw:
            continue
        pat = MatchPattern.parse(raw)
        if pat.is_regex:
            try:
                if re.search(pat.core, target, flags=re.IGNORECASE if pat.ignore_case else 0):
                    return True
            except re.error:
                continue
        else:
            core = normalize(pat.core) if normalize else pat.core
            if (pat.ignore_case and target.lower() == core.lower()) or target == core:
                return True
    return False


def match_tag_patterns(tag: str, patterns: List[str]) -> bool:
    """标签是否匹配任一格式: 精确匹配或 regex: 前缀正则, 支持 :ignore_case 后缀(见 match_value)"""
    return match_value(tag, patterns)


_EPISODE_PLACEHOLDERS = ("${episode_first}", "${episode_last}")


def auto_managed_tag_rules(config) -> "tuple[set, tuple]":
    """程序自动维护标签的识别规则: (精确集, 模板正则元组)

    WEB UI 标签候选过滤用(/api/tags?exclude_auto=1): 程序会自动打上的标签不进手动候选,
    免得站点名等刷屏。口径(2026-09-28 拍板):
    - 精确集 = 各站点 tags 全部 + HR 输出标签(add_tag / add_tag_for_satisfied 按该站点
      经 replace_vars 展开, 与维护路径同语义)
    - 模板正则 = 集数标签(值无界, 只能按形状匹配): add_episode_tags 启用时把单/多集模板的
      ${episode_*} 占位换成 \\d+、字面部分 re.escape
    - **不含** grouping.missing_tag / skip_checking_tag 等事件标记(程序只打不摘, 候选里
      留着才有摘除补救路径)与规则 add_tag 动作的输出(用户自己的自动化, 无固定清单)
    config 鸭子类型读字段(真实 Config 与测试替身通用)。
    """
    exact: set = set()
    for tracker in (getattr(config, "trackers", None) or {}).values():
        exact.update(t for t in (getattr(tracker, "tags", None) or []) if t)
        hr = getattr(tracker, "hr", None)
        if hr is not None:
            for key in ("add_tag", "add_tag_for_satisfied"):
                tag = replace_vars(getattr(hr, key, "") or "", tracker)
                if tag:
                    exact.add(tag)

    patterns = []
    episode_cfg = getattr(config, "add_episode_tags", None)
    if episode_cfg is not None and getattr(episode_cfg, "enabled", False):
        for key in ("add_tag_single", "add_tag_multi"):
            template = getattr(episode_cfg, key, "") or ""
            if not template:
                continue
            literal = re.escape(template)
            for ph in _EPISODE_PLACEHOLDERS:
                literal = literal.replace(re.escape(ph), r"\d+")
            patterns.append(re.compile(literal))
    return exact, tuple(patterns)


def is_auto_managed_tag(tag: str, exact: set, patterns: tuple) -> bool:
    """tag 是否命中 auto_managed_tag_rules 的任一规则(精确集或模板形状)"""
    return tag in exact or any(p.fullmatch(tag) for p in patterns)


def path_normalize(p: str) -> str:
    """
    路径规范化：仅统一分隔符并压缩冗余斜杠。
    重要：保留首尾斜杠不做删除，避免误匹配（如 'c:/windows/' 与 'c:/windowsg' 区分）。
    """
    if not p:
        return p
    # 1. 反斜杠转正斜杠
    p = p.replace('\\', '/')
    # 2. 压缩连续重复斜杠（如 "a//b" -> "a/b"），但保留根目录 "//" 或协议头 "file://" 等特殊场景（这里简单处理，仅压缩非边界处）
    # 使用正则替换 2 个以上斜杠为 1 个
    return re.sub(r'/{2,}', '/', p)


def match_path_patterns(path: str, patterns: List[str]) -> bool:
    """路径是否匹配任一格式(语法见 match_value): 精确匹配对两侧做 path_normalize
    统一斜杠(保留首尾斜杠, 防止 'c:/windows/' 与 'c:/windowsg' 误等), 正则模式
    只对候选路径规范化、模式主体保持原样(不能对正则做路径规范化)"""
    return match_value(path, patterns, normalize=path_normalize)


# qB 搬运未完成文件的临时后缀: qBittorrent 对未完成/被占用的搬运文件加 .!qB, 完成后改回原名。
# 全项目单一事实源(issue 26-09-21-0219 / plan 26-09-22-2038): 判定与日志文案一律引用本常量,
# 避免散落副本悄悄分叉。
QB_INCOMPLETE_SUFFIX = ".!qB"


def qb_incomplete_twin_path(path: str) -> str:
    """原名路径 -> 其 qB 未完成孪生路径(原名 + .!qB 后缀)

    纯字符串函数, 只负责后缀拼接的单点定义; 存在性探测由调用方经文件访问层
    (file_access.exists 三态语义)完成 —— 不在本函数里直接 os.path.exists:
    逻辑路径直探 syscall 会绕开 fs.path_map 映射(docker 部署下恒 False, 容忍静默失效)。
    """
    return path + QB_INCOMPLETE_SUFFIX


def timer(unit='s', log_func=print):
    """
    参数：
        unit: 时间单位，'s' 秒，'ms' 毫秒，'us' 微秒
        log_func: 输出函数，默认 print，可替换为 logging.info 等
        示例: @utils.timer(unit="ms", log_func=logger.debug)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            if unit == 'ms':
                elapsed *= 1000
            elif unit == 'us':
                elapsed *= 1_000_000

            log_func(f"{func.__name__} 耗时: {elapsed:.3f} {unit}")
            return result

        return wrapper

    return decorator


def is_manual_speed_limit(value_bytes: int) -> bool:
    """奇数 KiB/s 视为用户手动设置(项目约定, 如 2001KiB/s): 自动限速不覆盖

    三处共用(tracker 单种限速 / 规则限速动作 / 全局限速曲线), 语义必须保持一致。
    """
    return value_bytes > 0 and (value_bytes // 1024) % 2 == 1


def fmt_speed(value: int) -> str:
    """将字节/秒格式化为可读字符串"""
    for unit, div in (("PiB/s", 1024**5), ("TiB/s", 1024**4), ("GiB/s", 1024**3), ("MiB/s", 1024**2), ("KiB/s", 1024)):
        if value >= div:
            return f"{value / div:.2f} {unit}"
    return f"{value} B/s"


def fmt_size(value) -> str:
    """将字节数格式化为可读大小字符串(无 /s 后缀, 与 fmt_speed 区分)"""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "-"
    for unit, div in (("PiB", 1024**5), ("TiB", 1024**4), ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)):
        if value >= div:
            return f"{value / div:.2f} {unit}"
    return f"{value} B"


def replace_vars(text: str, tracker_conf) -> str:
    """替换标签/分类格式中的变量, 当前支持 ${required_seeding_time}

    注: required_seeding_time 是 _raw 字符串 (如 "3D"), 不是秒数 int
    """
    # TODO: 添加其它变量的支持
    hr_conf = tracker_conf.hr if tracker_conf else None
    if not hr_conf:
        return str(text)  # 无 HR 配置(无 tracker_conf 或 hr=None)时, 占位无法解析, 留原文
    return str(text).replace("${required_seeding_time}", hr_conf.required_seeding_time_raw)


# Windows MAX_PATH: 不含结尾 NUL 的最大字符数 —— 超过它, 裸路径在未开长路径支持的机器上
# 一律失败(`isdir` 给假 / `scandir` 抛 WinError 3), 必须走 `\\?\` 前缀或 Shell PIDL 路线。
WIN_MAX_PATH = 260

# CoInitializeEx 的单元模型与成功返回值(Windows Shell PIDL 路线用; S_OK 与 S_FALSE 均需配对 CoUninitialize)
_COINIT_APARTMENTTHREADED = 0x2
_COINIT_OK = (0, 1)


def _exists_dir(path: str) -> bool:
    """目录判定(Windows 长路径经 `\\\\?\\` 前缀; 非 Windows 是空操作 —— 见 add_long_path_prefix_for_win)"""
    return os.path.isdir(add_long_path_prefix_for_win(path))


def _exists_file(path: str) -> bool:
    """文件判定(同上, 长路径必须加前缀, 否则超长文件恒判不存在)"""
    return os.path.isfile(add_long_path_prefix_for_win(path))


def _win_shell_open(path: str) -> bool:
    """Windows 专用: 经 Shell 命名空间 PIDL 打开路径, **支持 >MAX_PATH 的长路径**。

    为何另起一条路线: `os.startfile` 与 `explorer /select,` 都是**字符串路径**入口, 实测对
    314 字符裸路径分别抛 `FileNotFoundError(WinError 2)` 与**静默打开"桌面"**(误导性失败);
    加 `\\\\?\\` 前缀也不行 —— ShellExecute 系不吃该前缀(实测 `SHParseDisplayName` 对它返回
    `0x80070057 E_INVALIDARG`)。PIDL 路线绕开字符串: `SHParseDisplayName(裸路径)` ->
    `SHOpenFolderAndSelectItems(pidl)`。实测(2026-09-30, Win11)目录/文件 pidl 行为一致:
    **都是打开父窗口并选中该条目**(旧注释"传目录 pidl = 打开该目录"与实测不符, 见
    `_win_reuse_title_candidates`)。

    实测约束(勿改):
    - `SHParseDisplayName` **只认反斜杠**, 正斜杠与 `\\\\?\\` 前缀都判 E_INVALIDARG;
    - WebUI 同步端点跑在 uvicorn/anyio 的线程池 worker 里, 而 Python 线程默认**不初始化 COM**
      —— 实测 worker 里不初始化时本调用返回 `0x800401F0 CO_E_NOTINITIALIZED` ⇒ 每次都得配一次
      `CoInitializeEx`(`S_OK`/`S_FALSE` 均需配对 `CoUninitialize`; `RPC_E_CHANGED_MODE`
      表示已被别处以 MTA 初始化, 不配对卸载, 此时若 Shell 调用失败由调用方降级兜住)。

    返回 True = 已交给 Shell; False = 本路线不可用, 调用方降级。**绝不抛错**。

    跨平台: 只在 `is_windows()` 为真时进入, 且 ctypes **惰性取用** —— `ctypes.windll` 在
    Linux/macOS 上不存在, 顶层引用会让 CI 直接 ImportError(见 testing/file-conventions.md)。
    """
    if not is_windows():
        return False
    try:
        import ctypes
        from ctypes import wintypes

        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
    except (ImportError, AttributeError, OSError):
        return False

    shell32.SHParseDisplayName.argtypes = [
        wintypes.LPCWSTR, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD)
    ]
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, wintypes.DWORD]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    # ole32 的 COM 初始化/卸载同样要绑: 第一参数是 LPVOID(指针宽度), 不绑会踩与
    # `_win_user32` 同一类 x64 传参问题(实测教训见该处 docstring)
    _win_bind(getattr(ole32, "CoInitializeEx", None), [ctypes.c_void_p, wintypes.DWORD], ctypes.c_long)
    _win_bind(getattr(ole32, "CoUninitialize", None), [], None)

    target = os.path.normpath(path).replace("/", "\\")
    if target.startswith("\\\\?\\"):  # 前缀与 PIDL 路线互斥, 传进去必 E_INVALIDARG
        target = target[4:]

    try:
        hr = ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
    except (AttributeError, OSError):
        return False
    pidl = ctypes.c_void_p()
    try:
        sfgao = wintypes.DWORD()
        if shell32.SHParseDisplayName(target, None, ctypes.byref(pidl), 0, ctypes.byref(sfgao)) != 0:
            logger.debug(f"Shell PIDL 解析失败, 退回字符串路线: {path}")
            return False
        if shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0) != 0:
            logger.debug(f"Shell PIDL 打开失败, 退回字符串路线: {path}")
            return False
        return True
    except (AttributeError, OSError) as e:  # pragma: no cover - 防御: Shell 异常不该逃逸
        logger.debug(f"Shell PIDL 路线异常, 退回字符串路线: {path} ({e})")
        return False
    finally:
        if pidl:
            shell32.ILFree(pidl)
        if hr in _COINIT_OK:
            ole32.CoUninitialize()


def _win_string_open(path: str, select: bool) -> None:
    """Windows 字符串路线(`os.startfile` / `explorer /select,`) —— PIDL 不可用时的兜底。

    超长路径上两者都不可靠(`os.startfile` 抛 `FileNotFoundError` 即使目录确实存在;
    `explorer /select,` **静默打开"桌面"**) ⇒ 先上溯到长度 < `WIN_MAX_PATH` 的祖先再打开,
    让用户至少落到正确分支的某层目录; 其它失败保持原样抛出, 不掩盖既有错误语义。

    `cand` 经上溯后必 < MAX_PATH ⇒ 这里的判定**无需前缀**, 裸路径即可。
    """
    cand = os.path.normpath(path)
    while len(cand) >= WIN_MAX_PATH and os.path.dirname(cand) != cand:
        cand = os.path.dirname(cand)
    if select and os.path.isfile(cand):
        subprocess.run(["explorer", "/select,", cand], check=False)
    else:
        os.startfile(cand)  # noqa: S606  仅 Windows 存在


# Explorer 文件夹主窗口的窗口类名 —— open_path 前后快照差集 = 本次新弹出的窗口
_EXPLORER_WND_CLASS = "CabinetWClass"
# 新弹出的 Explorer 窗口从创建到可被 EnumWindows 枚举到的等待上限与轮询步长。
# 上限必须够长: Shell 是走 DCOM 把请求交给已在跑的 explorer.exe 慢慢建窗, 冷启动 / 杀软
# 扫描 / 大量 Shell 扩展时实测可达数秒(旧实现的 2s 上限正是"仍有概率不置前"的根因之一);
# 太长则多占一个 daemon 线程。
_EXPLORER_FG_TIMEOUT = 5.0
_EXPLORER_FG_POLL = 0.1
# 窗口找到后强推前台的重试次数与间隔: 单次 SetForegroundWindow 会被前台锁随机拒绝,
# 重试能把命中率拉满; 次数必须封顶 —— 它只是锦上添花, 不该让后台线程执念太久。
_EXPLORER_FG_RETRY = 4
_EXPLORER_FG_RETRY_GAP = 0.12


def _win_bind(fn, argtypes, restype) -> bool:
    """给一个 windll 函数对象绑签名; 该导出不存在(老系统)时返回 False —— 绑不动不致命"""
    try:
        fn.argtypes = argtypes
        fn.restype = restype
        return True
    except (AttributeError, OSError, TypeError):
        return False


def _WIN_USER32_SIGNATURES():
    """user32 各 API 的 (名字, argtypes, restype) 清单 —— x64 上**必须**逐个绑死, 理由见 `_win_user32`"""
    import ctypes
    from ctypes import wintypes

    HWND, BOOL, UINT, DWORD = wintypes.HWND, wintypes.BOOL, wintypes.UINT, wintypes.DWORD
    INT, LPWSTR, LPARAM = ctypes.c_int, wintypes.LPWSTR, wintypes.LPARAM
    PDWORD, ENUMPROC = ctypes.POINTER(DWORD), ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
    return (
        ("IsWindow", [HWND], BOOL),
        ("IsIconic", [HWND], BOOL),
        ("IsWindowVisible", [HWND], BOOL),
        ("GetForegroundWindow", [], HWND),
        ("SetForegroundWindow", [HWND], BOOL),
        ("BringWindowToTop", [HWND], BOOL),
        ("SwitchToThisWindow", [HWND, BOOL], None),  # 非公开导出, 老系统可能没有
        ("ShowWindow", [HWND, INT], BOOL),
        ("SetWindowPos", [HWND, HWND, INT, INT, INT, INT, UINT], BOOL),
        ("GetWindowThreadProcessId", [HWND, PDWORD], DWORD),
        ("AttachThreadInput", [DWORD, DWORD, BOOL], BOOL),
        ("GetClassNameW", [HWND, LPWSTR, INT], INT),
        ("GetWindowTextW", [HWND, LPWSTR, INT], INT),
        ("EnumWindows", [ENUMPROC, LPARAM], BOOL),
    )


_bound_user32 = None
_bound_kernel32 = None


def _win_user32():
    """user32 句柄(惰性取用 + **逐个绑签名** + 拿不到返回 None)

    ⚠ 签名必须绑死 —— 2026-09-30 实测(同一窗口、同一时刻, 唯一变量是有没有 argtypes):
      未绑 -> `SetWindowPos(hwnd, HWND_TOPMOST, ...)` **ret=0**, Z 序纹丝不动, 且
      `GetLastError()` 仍为 0(典型的"静默无效"); 绑了 -> ret=1, 窗口立刻抬到顶层。
    根因: 不绑 argtypes 时 ctypes 把所有参数按 **32 位 int** 传, 而 `HWND` 与"可插图句柄"
    (`HWND_TOPMOST = (HWND)-1`) 是**指针宽度**的 —— x64 寄存器高 32 位留着上一个调用的
    残留值, 于是 -1 被当成真实窗口句柄、目标 hwnd 被当成无效句柄。凡**取 HWND 参数**的调用
    (`GetClassNameW` / `GetWindowTextW` / `SetForegroundWindow` …) 都吃同一套随机概率:
    窗口类名查不到、标题取空、焦点抢不上 —— 这才是"**有概率**不弹到顶层"的真根因,
    与前台锁、与 Z 序手段都无关(旧单测注入的是假 user32, 永远测不出这一类 x64 ABI 问题)。
    POSIX 上 `ctypes.windll` 不存在, 顶层引用会让 CI ImportError(见 testing/file-conventions.md)
    —— 返回 None 让调用方早退, 而不是靠"恰好抛了异常"决定行为。
    测试可 monkeypatch 本函数注入假 user32(理由同 `_WIN_USER32_SIGNATURES` 的存在: 真调
    shell API 会把开发机窗口摆弄乱)。
    """
    global _bound_user32
    if not is_windows():
        return None
    if _bound_user32 is not None:
        return _bound_user32
    try:
        import ctypes

        u = ctypes.windll.user32
    except (ImportError, AttributeError, OSError):
        return None
    for name, argtypes, restype in _WIN_USER32_SIGNATURES():
        _win_bind(getattr(u, name, None), argtypes, restype)
    _bound_user32 = u
    return u


def _win_kernel32():
    """kernel32 句柄(同上: 惰性 + 绑签名; 目前只需 `GetCurrentThreadId`)"""
    global _bound_kernel32
    if not is_windows():
        return None
    if _bound_kernel32 is not None:
        return _bound_kernel32
    try:
        import ctypes
        from ctypes import wintypes

        k = ctypes.windll.kernel32
    except (ImportError, AttributeError, OSError):
        return None
    _win_bind(getattr(k, "GetCurrentThreadId", None), [], wintypes.DWORD)
    _bound_kernel32 = k
    return k


def _win_explorer_hwnds() -> set:
    """当前所有 Explorer 文件夹窗口的 HWND 集合(EnumWindows 按类名过滤)。

    只读窗口枚举, 不产生任何系统副作用; 任何失败返回空集, 绝不抛错 —— 快照失败时调用方
    跳过置前, 行为退化为修复前。句柄一律经 `_win_user32()` 拿(签名已绑: 未绑时
    `GetClassNameW` 会 sporadically 返回垃圾, 差集快照跟着随机失灵 —— 见该处实测)。
    """
    user32 = _win_user32()
    if user32 is None:
        return set()
    try:
        import ctypes
        from ctypes import wintypes

        hwnds = set()
        enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _on_window(hwnd, _lparam):
            buf = ctypes.create_unicode_buffer(32)
            if user32.GetClassNameW(hwnd, buf, 32) and buf.value == _EXPLORER_WND_CLASS:
                hwnds.add(hwnd)
            return True

        proc = enum_proc(_on_window)  # 局部引用防回调被 GC
        user32.EnumWindows(proc, 0)
        return hwnds
    except (ImportError, AttributeError, OSError):
        return set()


def _win_topmost_once(hwnd) -> None:
    """把窗口压到**所有非 topmost 窗口之上**(TOPMOST 挂一下立刻摘, 即经典开关式提升)。

    为何必须有这一层: `SetForegroundWindow` 受 Windows 前台锁约束 —— 后台进程(WebUI 的
    uvicorn 线程池 / 托盘线程)没拿到前台权限时它会被**静默拒绝**, 新开的资源管理器因此留在
    浏览器后面(用户报的"不弹出至顶层")。而 Z 序调整不受前台锁约束: `SetWindowPos` 配
    `SWP_NOACTIVATE`(不抢焦点, 只动顺序)后台进程调用也必定被受理 —— "看得见"这一层单独
    兜住, 与"抢得到焦点"解耦。抬完立刻摘掉 topmost, 避免它长期钉在所有窗口之上。
    """
    user32 = _win_user32()
    if user32 is None:
        return
    try:
        HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
        SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0001, 0x0002, 0x0010, 0x0040
        flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    except (AttributeError, OSError):
        pass


def _win_switch_to_this_window(hwnd) -> bool:
    """兜底硬切: `user32.SwitchToThisWindow`(Win95 起在 user32 里导出, Win11 仍在)

    它绕的是前台锁本身( shell 内部切窗口就走这条路), 因此比 AttachThreadInput 那套更硬;
    代价是非公开接口 —— 取不到就 False, 绝不因为少了它影响前面两层的成果。
    """
    user32 = _win_user32()
    if user32 is None:
        return False
    try:
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except (AttributeError, OSError):
        return False


def _win_force_foreground(hwnd) -> bool:
    """把窗口抬到顶层并争取前台焦点; 返回它是否**真的**成了前台窗口。

    三层升级, 每层独立失败静默、互不为前置条件(见 `_win_topmost_once` 的为何必须):
      1. **Z 序**(必定受理): TOPMOST -> NOTOPMOST 提升 —— 用户看到的"不弹到顶层"由这层解决;
      2. **焦点**(可能被拒): AttachThreadInput 借前台线程的权限 -> SetForegroundWindow -> 拆开;
      3. **硬切**(兜底): 仍没拿到焦点才试 `SwitchToThisWindow`。
    窗口不可见 / 最小化的先还原、先显示 —— 被别的手段藏起来的窗口拿到焦点也看不见。
    三步跑完仍没焦点也**不算失败**: 它已经压在所有普通窗口之上, 用户点一下即可 —— 重试由
    调用方按 `_EXPLORER_FG_RETRY` 封顶地做, 这里不做无限执念。
    """
    user32 = _win_user32()
    kernel32 = _win_kernel32()
    if user32 is None or kernel32 is None:
        return False
    try:
        SW_SHOW, SW_RESTORE = 5, 9
        if not user32.IsWindow(hwnd):
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        elif not user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, SW_SHOW)
        _win_topmost_once(hwnd)
        fg = user32.GetForegroundWindow()
        cur = kernel32.GetCurrentThreadId()
        fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(fg) and fg_thread != cur and user32.AttachThreadInput(cur, fg_thread, True)
        try:
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(cur, fg_thread, False)
        if user32.GetForegroundWindow() == hwnd:
            return True
        _win_switch_to_this_window(hwnd)
        user32.BringWindowToTop(hwnd)
        return user32.GetForegroundWindow() == hwnd
    except (AttributeError, OSError):
        return False


def _win_reuse_title_candidates(target: str) -> set:
    """复用已有窗口场景下, 目标所在 Explorer 窗口可能的标题名集合。

    实测(2026-09-30, Win11): `SHOpenFolderAndSelectItems` 传目录/文件 pidl 都是**打开父窗口
    并选中目标**(目录也一样 —— 上面"传目录 pidl = 打开该目录"的旧描述与实测不符) —— 所以
    复用窗口的标题可能是父目录名(本次导航落点), 也可能是目标名(窗口本来就开着该目录)。
    盘根两候选都为空, 调用方据此跳过兜底。
    """
    t = os.path.normpath(target)
    names = {os.path.basename(t)}
    parent = os.path.dirname(t)
    if parent and parent != t:
        names.add(os.path.basename(parent))
    return {n for n in names if n}


def _win_match_reused_explorer(hwnds: set, before: set, names: set):
    """在**打开前就存在**的 Explorer 窗口里按标题找本次导航落点(HWND / 找不到 None)

    只在这些窗口里找: 差集(新窗口)优先, 复用场景根本没有新窗口; Win11 标题带
    " - 文件资源管理器" 类本地化后缀, 用 `名字 + " - "` 前缀匹配绕开语言差异。
    """
    for h in sorted(hwnds):
        if h not in before:
            continue
        title = _win_window_text(h)
        if any(title == n or title.startswith(n + " - ") for n in names):
            return h
    return None


def _win_wait_explorer(before: set, target: str):
    """等本次打开的资源管理器窗口出现并返回 HWND(超时 None)

    两条策略**每轮都试**(命中就停): ①快照差集 = 本次新建的 Explorer 窗口(最常见);
    ②按标题在旧窗口里找 = Explorer **复用已有窗口/标签页**导航, 不新建窗口 —— 这是上一轮
    修复的主要漏网点: 旧实现把②当"新窗口等不到"的兜底放在 2s 超时之后才做一次, 慢于 2s 的
    复用导航整个漏掉, 表现为"有概率不置前"。
    两条都不中有两种可能: Shell 还在慢慢建窗(继续轮询到 `_EXPLORER_FG_TIMEOUT`), 或本次
    打开压根没出窗口(PIDL/字符串路线都失败) —— 两者都静默处理, 返回 None 让调用方跳过置前。
    """
    before = set(before)
    names = _win_reuse_title_candidates(target)
    deadline = time.monotonic() + _EXPLORER_FG_TIMEOUT
    while True:
        hwnds = _win_explorer_hwnds()
        new = sorted(hwnds - before)
        if new:
            return new[0]  # 一般只有一个; 多个时任一都属本次打开
        if names:
            reused = _win_match_reused_explorer(hwnds, before, names)
            if reused is not None:
                return reused
        if time.monotonic() >= deadline:
            return None
        time.sleep(_EXPLORER_FG_POLL)


def _win_foreground_new_explorer(before: set, target: str) -> bool:
    """找到本次打开的资源管理器窗口并把它抬到顶层; 返回是否成功拿到前台焦点。

    只解决"用户看得见"(Z 序): 焦点靠 `_win_force_foreground` 尽力争取, 争不到也**不再有任何
    后果** —— 窗口已压在所有普通窗口之上, 用户点一下即可。失败一律静默(debug 留痕),
    绝不影响打开本体 —— 置前是锦上添花。
    """
    hwnd = _win_wait_explorer(before, target)
    if hwnd is None:
        logger.debug(f"打开目标文件夹: 未定位到本次的资源管理器窗口, 跳过置前 | {target}")
        return False
    for i in range(_EXPLORER_FG_RETRY):
        if _win_force_foreground(hwnd):
            return True
        time.sleep(_EXPLORER_FG_RETRY_GAP * (i + 1))  # 渐进间隔: 等 Shell 建窗动画落地再争取焦点
    logger.debug(f"打开目标文件夹: 窗口已抬到顶层但未取得前台焦点(前台锁) | hwnd={hwnd} {target}")
    return False


def _win_window_text(hwnd) -> str:
    """窗口标题文本(GetWindowTextW); 失败返回空串, 绝不抛错(仅置前兜底匹配用)"""
    user32 = _win_user32()
    if user32 is None:
        return ""
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except (AttributeError, OSError):
        return ""


def _win_foreground_explorer_async(before: set, target: str) -> None:
    """后台线程执行 `_win_foreground_new_explorer`(不阻塞调用线程, daemon 随进程退场)。

    open_path 的调用方是 WebUI 端点 / 托盘菜单 —— 找窗口最多轮询 `_EXPLORER_FG_TIMEOUT`,
    不能挂住它们。
    """
    threading.Thread(
        target=_win_foreground_new_explorer, args=(before, target), name="open-path-foreground", daemon=True
    ).start()


def open_path(path: str, select: bool = False) -> None:
    """用系统默认方式打开文件/目录(跨平台: Windows 资源管理器 / macOS open / Linux xdg-open)

    R10-10: `select=True` 表示"打开所在文件夹并**定位选中**该文件"(单文件种子: 用户要在
    文件夹里看到那一个文件, 而不是被丢进一个装了上百个种子的目录):
    - Windows: Shell PIDL 传**文件** pidl -> 资源管理器打开父目录并高亮选中该文件
      (长路径唯一可行; 见 `_win_shell_open`);
    - macOS: `open -R <file>`(Reveal in Finder);
    - Linux: 无通用"选中"语义(依赖具体文件管理器), 退化为打开父目录 —— 明确比静默丢弃好。
    目标不是已存在文件(或平台不支持)时退化为普通打开该路径, 不抛错(动作类工具的容错优先)。

    长路径(>MAX_PATH, Windows): 字符串路线对超长路径一个抛错、一个静默开错地方, 故
    **目录**与**定位选中**两种语义改走 Shell PIDL; 目录判定一律经 `_exists_dir`(带前缀)。
    macOS/Linux 无 260 限制(PATH_MAX 1024 / 4096), 分支**逐字保持改动前行为**。

    !`_win_shell_open` 只在 `is_windows()` 分支内调用 —— 它在 POSIX 上是空转, 而测试期副作用
    记账器把该入口整体计入 LAUNCH(放行清单为空), 无谓调用会变成假阳性。

    弹出置前: Shell 打开的资源管理器窗口对**后台进程调用方**(托盘 / uvicorn 线程池)有概率
    留在浏览器后面(不弹到顶层) —— 打开前快照 Explorer 窗口集合, 打开后后台线程找本次窗口
    抬到顶层(见 `_win_foreground_new_explorer`; 置前属锦上添花, 任何失败静默, 不影响打开本体)。
    """
    if is_windows():
        before = _win_explorer_hwnds()
        try:
            if select and _exists_file(path):
                if _win_shell_open(path):  # 文件 pidl -> 打开父目录并选中该文件
                    return
                _win_string_open(path, select=True)
                return
            if _exists_dir(path) and _win_shell_open(path):  # 目录 pidl -> 打开父窗口并选中该目录(实测)
                return
            _win_string_open(path, select=False)
            return
        finally:
            _win_foreground_explorer_async(before, path)
    # ---- macOS / Linux: 以下与改动前逐字一致 ----
    if select and os.path.isfile(path):
        if is_mac():
            subprocess.run(["open", "-R", path], check=False)
            return
        path = os.path.dirname(path)  # Linux: 退化到父目录
    if is_mac():
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


@lru_cache(maxsize=4096)
def encode_group_key(key: tuple) -> str:
    """分组 key(tuple) -> URL 安全字符串(base64url(JSON 数组)), WEB UI 分组路由标识

    lru_cache: key 可哈希且编码恒定(同 key 恒同串), 分组 key 含完整文件列表,
    未缓存时每 tick 每组重复 json.dumps+base64 数十 KB(py-spy 实测占 ~30% CPU)。
    """
    return base64.urlsafe_b64encode(json.dumps(list(key), ensure_ascii=False).encode("utf-8")).decode("ascii")


def decode_group_key(text: str) -> tuple:
    """encode_group_key 的逆变换; 内层文件列表保持 tuple(与 store.groups 的 key 结构一致)"""
    arr = json.loads(base64.urlsafe_b64decode(text.encode("ascii")))
    return (arr[0], tuple(arr[1]))

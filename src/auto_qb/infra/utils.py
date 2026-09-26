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
from functools import lru_cache
import re
import subprocess
import sys
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

    ❗空路径直接报错(不静默兜底): `abspath("")` 是 CWD, `dirname` 再取一级就成了 **CWD 的父目录**
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
                d[k] = [convert_bool_in_dict(item) for item in v]

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
    `SHOpenFolderAndSelectItems(pidl)`。传**目录** pidl = 打开该目录; 传**文件** pidl =
    打开父目录并选中该文件(正是 R10-10 的"定位选中"语义)。

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

    ❗`_win_shell_open` 只在 `is_windows()` 分支内调用 —— 它在 POSIX 上是空转, 而测试期副作用
    记账器把该入口整体计入 LAUNCH(放行清单为空), 无谓调用会变成假阳性。
    """
    if is_windows():
        if select and _exists_file(path):
            if _win_shell_open(path):  # 文件 pidl -> 打开父目录并选中该文件
                return
            _win_string_open(path, select=True)
            return
        if _exists_dir(path) and _win_shell_open(path):  # 目录 pidl -> 打开该目录
            return
        _win_string_open(path, select=False)
        return
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

"""utils_paths.py — R5 大文件拆分(计划 26-11-02-2342 §07)

原子写盘 / 匹配语法 / 文件格式与分组 key 域。原 `infra.utils` 的公开名由根模块重导出,
调用方 import 路径不变。只搬运定义, 实现逐行未改。

logger 显式沿用原模块名, 保持日志通道与拆分前一致。
"""

import base64
import ipaddress
import json
import math
import os
import shutil
import tempfile
import hashlib
from functools import lru_cache
import re
import secrets
import subprocess
import sys
import threading
import time
import logging
from dataclasses import dataclass
from datetime import time as dtime
from functools import wraps
from urllib.parse import urlparse
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger("auto_qb.infra.utils")

BACKUP_SUFFIX = ".bak"

# atomic_write 的临时文件后缀(写侧与启动清理侧共用同一常量, 理由同 BACKUP_SUFFIX)
TMP_SUFFIX = ".tmp"

# os.replace 的退避重试(仅 PermissionError; 理由见 _replace_retry 与 pitfalls/backend/platform-fs
# 「Windows 原子写与并发读者的双向瞬时拒绝」)。数字与 tools/global-traffic-monitor 的
# storage._replace_retry 一致(5 次 × 50ms): 该窗口是开-读-关的微秒~毫秒级, 不是持久故障。
REPLACE_RETRY_ATTEMPTS = 5
REPLACE_RETRY_DELAY_S = 0.05

# 匹配语法常量(用户配置的统一匹配语法, 解析唯一入口见 MatchPattern)
REGEX_PREFIX = "regex:"
IGNORE_CASE_SUFFIX = ":ignore_case"


def _replace_retry(tmp_path: str, path: str) -> None:
    """`os.replace` 的退避重试(仅 PermissionError; 其它 OSError 原样抛)

    !Windows 上目标文件被**任何**不含 `FILE_SHARE_DELETE` 的句柄持着时, `MoveFileEx` 拒绝替换
    并抛 WinError 5(Python 的 `open()` 正是这种句柄) —— 这类持有时长是「开-读-关」的微秒~毫秒
    窗口, 重试即可穿过; 对手是杀软/索引器/另一进程时同理。2026-10-16 用户实报 HR 注册表心跳
    一次性失败(`instances.json.o7e7o6ed.tmp` -> `instances.json`)即此坑的写侧; 坑档与同款实现在
    `memory-bank/pitfalls/backend/platform-fs.md` /
    `tools/global-traffic-monitor/src/gtm/storage.py::_replace_retry`(工具独立, 不 import 本模块,
    两处常量必须同值)。

    只对 PermissionError 重试: 磁盘满 / 路径非法 / 被杀软持续锁死重试都不解决, 早抛给调用方。
    POSIX 上 replace 不受读者影响, 本函数不会触发(合法权限错误会被重试 5 次, 是唯一的代价)。
    """
    last: Optional[OSError] = None
    for attempt in range(REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as e:
            last = e
            if attempt < REPLACE_RETRY_ATTEMPTS - 1:
                time.sleep(REPLACE_RETRY_DELAY_S)
    assert last is not None
    raise last


def atomic_write(path: str, write_fn, keep_backup: bool = False) -> None:
    """原子写盘: 同目录临时文件 -> fsync -> os.replace(Windows 上为原子替换)

    直接 `open(path, "w")` 会先 truncate 旧文件: 写盘途中被杀 / 磁盘满 / 序列化抛异常都会留下
    **半截文件**, 而 state.json 无备份 ⇒ 执行历史与去重记录全丢(规则重放)。本函数保证
    目标路径要么完全是旧内容, 要么完全是新内容。

    最后的换名走 `_replace_retry`(仅 PermissionError 退避重试): Windows 上并发读者/杀软/另一
    进程的瞬时句柄会让 `os.replace` 抛 WinError 5, 那是毫秒级窗口而非持久故障 —— 见坑档
    `pitfalls/backend/platform-fs.md`「Windows 原子写与并发读者的双向瞬时拒绝」(2026-10-16
    HR 心跳实报)。重试耗尽仍抛, 由调用方决定容错口径(如心跳下一周期重试)。

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
        _replace_retry(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):  # os.replace 已成功时临时文件不存在, 不该再删
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


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
    开头的 UNC 双斜杠边界豁免压缩(存量评审 R4#1 / R2#30)：UNC 写法(\\\\NAS\\share\\dl)折成
    `//NAS/share/dl` 后若照常压缩成 `/NAS/share/dl`，宿主侧会把单斜杠开头当相对路径处理：
    Windows 拼到 cwd 所在盘根下(实测 abspath('\\NAS\\share\\dl') = 'D:\\NAS\\share\\dl',
    或产出非法 \\\\?\\ 前缀串)，POSIX 上 `/NAS/...` 本就是绝对路径不发生拼接 —— 两种宿主
    都触达不了 UNC 目标本体(Local.scandir 抛 FileNotFoundError)。
    """
    if not p:
        return p
    # 1. 反斜杠转正斜杠
    p = p.replace('\\', '/')
    # 2. 压缩连续重复斜杠（如 "a//b" -> "a/b"）；开头两个及以上斜杠是 UNC 根边界，
    #    收敛到恰好两个（仍保持 UNC 形状），其余位置照常压缩
    if p.startswith("//"):
        return "//" + re.sub(r'/{2,}', '/', p.lstrip("/"))
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


# 单位阶梯单点: fmt_speed / fmt_size 共用骨架与单位表, 只差 suffix —— 改单位或小数精度只此处
_SIZE_UNITS = (("PiB", 1024**5), ("TiB", 1024**4), ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024))


def _fmt_ladder(value: int, units: tuple, suffix: str = "") -> str:
    """单位阶梯格式化骨架: 从高到低首个 rung 达值即 `X.XX unit<suffix>`, 未达任何即 `value B<suffix>`"""
    for unit, div in units:
        if value >= div:
            return f"{value / div:.2f} {unit}{suffix}"
    return f"{value} B{suffix}"


def fmt_speed(value: int) -> str:
    """将字节/秒格式化为可读字符串"""
    return _fmt_ladder(value, _SIZE_UNITS, "/s")


def fmt_size(value) -> str:
    """将字节数格式化为可读大小字符串(无 /s 后缀, 与 fmt_speed 区分)"""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "-"
    return _fmt_ladder(value, _SIZE_UNITS)


def replace_vars(text: str, tracker_conf) -> str:
    """替换标签/分类格式中的变量, 当前支持 ${required_seeding_time}

    注: required_seeding_time 是 _raw 字符串 (如 "3D"), 不是秒数 int
    """
    # TODO: 添加其它变量的支持
    hr_conf = tracker_conf.hr if tracker_conf else None
    if not hr_conf:
        return str(text)  # 无 HR 配置(无 tracker_conf 或 hr=None)时, 占位无法解析, 留原文
    return str(text).replace("${required_seeding_time}", hr_conf.required_seeding_time_raw)


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

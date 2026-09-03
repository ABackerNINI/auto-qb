"""通用工具函数: 解析器 / 路径 / 文件检查 / tracker 匹配

全部解析与检查函数集中于此, 供主程序(config/manager/exporter)与规则框架共用,
避免各模块重复实现。
"""
import os
import re
import sys
import time
import logging
from functools import wraps
from urllib.parse import urlparse
from typing import List

logger = logging.getLogger(__name__)


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
    """
    cond_str = str(cond_str).strip()
    if not cond_str:
        return ("dlratio", 0.8)  # 默认80%触发
    if cond_str.endswith("%"):  # 百分比, 如 "70%"
        return ("dlratio", float(cond_str[:-1]) / 100.0)
    return ("dlsize", parse_fsize(cond_str))  # 下载量绝对值, 如 "10MiB"


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
    """为 Windows 文件路径添加长路径支持前缀(\\\\?\\ 或 UNC), 非Windows系统则返回原路径"""
    if not is_windows():
        return path

    abs_path = os.path.abspath(path).replace("/", "\\")
    if abs_path.startswith("\\\\?\\"):
        return abs_path
    if abs_path.startswith("\\\\"):
        return "\\\\?\\UNC" + abs_path[1:]
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


def check_filelist(api, torrent):
    """检查种子文件是否存在且大小一致(api 为 QbApi 门面或兼容客户端). 返回错误描述字符串, 全部通过返回 None"""
    logger.info(f"检查种子文件完整性: {torrent.name} ({torrent.hash[:8]})")
    try:
        files = api.torrents_files(torrent.hash)
    except Exception as e:
        return f"获取文件列表失败: {e}"
    save_path = torrent.save_path
    for f in files:
        full_path = add_long_path_prefix_for_win(os.path.normpath(os.path.join(save_path, f.name)))
        if not os.path.exists(full_path):
            return f"文件缺失: {f.name}"
        try:
            if os.path.getsize(full_path) != f.size:
                return f"文件大小不一致: {f.name}"
        except OSError:
            return f"无法读取文件: {f.name}"
    return None


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


def match_tag_patterns(tag: str, patterns: List[str]) -> bool:
    """标签是否匹配任一格式: 精确匹配或`regex:`前缀正则(参考规则动作语义), 支持`:ignore_case`后缀"""
    for pat in patterns or []:
        if not pat:
            continue

        # 处理:ignore_case后缀
        ignore_case = False
        if pat.endswith(":ignore_case"):
            ignore_case = True
            pat = pat[:-12]

        if pat.startswith("regex:"):  # 正则匹配
            try:
                if re.search(pat[6:], tag, flags=re.IGNORECASE if ignore_case else 0):
                    return True
            except re.error:
                continue
        elif (ignore_case and pat.lower() == tag.lower()) or pat == tag:  # 精准匹配
            return True
    return False


def _path_normalize(p: str) -> str:
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
    """
    路径匹配函数。

    特性：
    - 精确匹配（默认）：字符串严格相等（已规范化斜杠）。
    - 正则匹配（前缀 'regex:'）：使用 re.search，支持子串匹配。
    - 忽略大小写（后缀 ':ignore_case'）：对精确匹配和正则均生效。
    """
    # 统一输入路径的斜杠格式（保留尾部斜杠）
    norm_path = _path_normalize(path)

    for raw_pattern in patterns:
        # ---------- 1. 解析后缀 :ignore_case ----------
        ignore_case = False
        pattern = raw_pattern
        if pattern.endswith(':ignore_case'):
            ignore_case = True
            pattern = pattern[:-len(':ignore_case')]

        # ---------- 2. 解析前缀 regex: ----------
        is_regex = False
        core = pattern
        if pattern.startswith('regex:'):
            is_regex = True
            core = pattern[len('regex:'):]

        # ---------- 3. 执行匹配 ----------
        if is_regex:  # 正则匹配不能对pattern进行_path_normalize
            flags = re.IGNORECASE if ignore_case else 0
            try:
                if re.search(core, norm_path, flags):
                    return True
            except re.error:
                continue
        else:
            # 精确匹配：对模式也做同样的规范化（保留尾部斜杠）
            match_core = _path_normalize(core)
            if (ignore_case and norm_path.lower() == match_core.lower()) or norm_path == match_core:
                return True

    return False


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


def fmt_speed(value: int) -> str:
    """将字节/秒格式化为可读字符串"""
    for unit, div in (("PiB/s", 1024**5), ("TiB/s", 1024**4), ("GiB/s", 1024**3), ("MiB/s", 1024**2), ("KiB/s", 1024)):
        if value >= div:
            return f"{value / div:.2f} {unit}"
    return f"{value} B/s"

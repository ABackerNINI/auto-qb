"""rules 框架通用工具: 时间/大小/速度/HR解析, tracker匹配, 文件检查"""
import os
import re
from urllib.parse import urlparse


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    if value.lower() in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"无效布尔值: {value}")


def parse_time(time_str: str) -> int:
    """时间字符串(如 '3D', '12H') -> 秒"""
    if not time_str:
        return 0
    units = {"S": 1, "M": 60, "H": 3600, "D": 86400}
    m = re.match(r"^([\d.]+)\s*([SMHD])$", str(time_str).strip().upper())
    if not m:
        raise ValueError(f"无效时间格式: {time_str}")
    value, unit = m.groups()
    return int(float(value) * units[unit])


def parse_fsize(fsize_str: str) -> int:
    """大小字符串(如 '10.5 GiB') -> 字节"""
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
    unit = unit.upper()
    if unit not in units:
        raise ValueError(f"无效大小单位: {fsize_str}")
    return int(float(value) * units[unit])


def parse_speed(speed_str: str) -> int:
    """速度字符串(如 '10MiB/s') -> 字节/秒"""
    if not speed_str:
        return 0
    units = {"B/S": 1, "KIB/S": 1024, "MIB/S": 1024**2, "GIB/S": 1024**3}
    m = re.match(r"^([\d.]+)\s*([KMG]?i?B/S)$", str(speed_str).strip().upper(), re.IGNORECASE)
    if not m:
        raise ValueError(f"无效速度格式: {speed_str}")
    value, unit = m.groups()
    return int(float(value) * units[unit.upper()])


def parse_hr_rule(rule_str: str):
    """
    解析HR规则: '3D@80%+12H' -> (required_seconds, ('dlratio'|'dlsize', value), extra_seconds)
    示例: "3D@70%+12H" -> (3D秒数, ('dlratio', 0.7), 12H秒数)
         "20H@30%"    -> (20H秒数, ('dlratio', 0.3), 0)
         "20H@10MiB"  -> (20H秒数, ('dlsize', 字节), 0)
    """
    rule_str = str(rule_str).strip()
    extra_time = 0
    if "+" in rule_str:
        main, extra = rule_str.split("+", 1)
        extra_time = parse_time(extra.strip())
    else:
        main = rule_str

    if "@" in main:
        time_part, cond_part = main.split("@", 1)
        required_time = parse_time(time_part.strip())
        cond_part = cond_part.strip()
        if cond_part.endswith("%"):
            condition = ("dlratio", float(cond_part[:-1]) / 100.0)
        else:
            condition = ("dlsize", parse_fsize(cond_part))
    else:
        required_time = parse_time(main.strip())
        condition = ("dlratio", 0.8)  # 默认80%触发

    return required_time, condition, extra_time


def parse_compare(spec: str, value_parser):
    """解析比较表达式: '>=100MiB' -> ('>=', 字节); '<24H' -> ('<', 秒)"""
    m = re.match(r"^\s*(>=|<=|>|<|==|=|!=)?\s*(.+?)\s*$", str(spec))
    if not m:
        raise ValueError(f"无效比较表达式: {spec}")
    op, rest = m.group(1), m.group(2)
    if op in (None, "="):
        op = "=="
    return op, value_parser(rest)


def compare(op: str, left, right) -> bool:
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


def add_long_path_prefix_for_win(path: str) -> str:
    """为 Windows 文件路径添加长路径支持前缀"""
    abs_path = os.path.abspath(path)
    abs_path = abs_path.replace("/", "\\")
    if abs_path.startswith("\\\\?\\"):
        return abs_path
    if abs_path.startswith("\\\\"):
        return "\\\\?\\UNC" + abs_path[1:]
    return "\\\\?\\" + abs_path


def check_filelist(client, torrent):
    """检查文件是否存在且大小一致. 返回错误描述字符串, 全部通过返回 None"""
    try:
        files = client.torrents_files(torrent.hash)
    except Exception as e:
        return f"获取文件列表失败: {e}"
    save_path = torrent.save_path
    for f in files:
        full_path = add_long_path_prefix_for_win(
            os.path.normpath(os.path.join(save_path, f.name))
        )
        if not os.path.exists(full_path):
            return f"文件缺失: {f.name}"
        try:
            if os.path.getsize(full_path) != f.size:
                return f"文件大小不一致: {f.name}"
        except OSError:
            return f"无法读取文件: {f.name}"
    return None


def match_tracker_confs(trackers: dict, urls: list):
    """
    精确匹配 tracker 域名(解析 hostname, 支持子域名), 返回匹配的 TrackerConfig 列表
    一个种子可能匹配多个 tracker 配置
    """
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

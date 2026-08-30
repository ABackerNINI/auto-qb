"""通用工具函数: 解析器 / 路径 / 文件检查 / tracker 匹配

全部解析与检查函数集中于此, 供主程序(config/manager/exporter)与规则框架共用,
避免各模块重复实现。
"""
import os
import re
import sys
import time
from functools import wraps
from urllib.parse import urlparse
from typing import List


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


def parse_time(time_str: str) -> int:
    """时间字符串(如 '3D', '12H', '10M') -> 秒; 空串返回0"""
    if not time_str:
        return 0
    units = {"S": 1, "M": 60, "H": 3600, "D": 86400}
    m = re.match(r"^([\d.]+)\s*([SMHD])$", str(time_str).strip().upper())
    if not m:
        raise ValueError(f"无效时间格式: {time_str}")
    value, unit = m.groups()
    return int(float(value) * units[unit])


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


def check_filelist(client, torrent):
    """检查种子文件是否存在且大小一致. 返回错误描述字符串, 全部通过返回 None"""
    try:
        files = client.torrents_files(torrent.hash)
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


# ---------- 集数解析(自动添加集数标签) ----------

# 文件名/种子名中提取集数的模式: 按优先级从高到低排列(第一个匹配者生效)
#   第5集 / 第05-08集 / S01E05  >  EP05  >  E05
# 每项: (正则, 提取函数(match -> List[int])), 提取函数返回该文件贡献的集数列表
# 新增模式: 在合适优先级位置插入一项即可, 无需改提取逻辑
_EPISODE_PATTERNS: List[tuple] = [
    # 第x集 / 第x-y集(区间展开为多集)
    (
        re.compile(r"第\s*(\d{1,4})\s*(?:[-~至]\s*(\d{1,4}))?\s*集",
                   re.IGNORECASE), lambda m: _expand_episode_range(int(m.group(1)), int(m.group(2)))
        if m.group(2) else [int(m.group(1))]
    ),
    # S01E05
    (re.compile(r"[Ss]\d{1,4}[Ee](\d{1,4})", re.IGNORECASE), lambda m: [int(m.group(1))]),
    # EP05
    (re.compile(r"[Ee][Pp](\d{1,4})", re.IGNORECASE), lambda m: [int(m.group(1))]),
    # E05
    (re.compile(r"[Ee](\d{1,4})", re.IGNORECASE), lambda m: [int(m.group(1))]),
]

# 文件名中独立数字模式(如 "01.mkv", "Show.Name.05"): 排除分辨率/年份等干扰
# 要求数字两侧是分隔符或边界(不能与字母粘连, 防止扩展名数字如 "xx.mp4" 的 4 被误判),
# 且排除 分辨率(720/1080/2160...) 与 年份(19xx/20xx)
_BARE_NUMBER_RE = re.compile(r"(?:^|[^A-Za-z0-9])(\d{1,4})(?:[^A-Za-z0-9]|$)")
_RESOLUTION_SET = {480, 576, 720, 1080, 2160, 4320}

# 视频文件扩展名(小写): 只有视频文件参与集数解析, 截图(jpg)/字幕(ass/srt)/字体等一律跳过
_VIDEO_EXTENSIONS = {
    "mkv",
    "mp4",
    "avi",
    "mov",
    "m4v",
    "m4p",
    "wmv",
    "flv",
    "webm",
    "mpg",
    "mpeg",
    "mpe",
    "m2v",
    "m2ts",
    "mts",
    "ts",
    "vob",
    "rm",
    "rmvb",
    "3gp",
    "3g2",
    "ogv",
    "ogm",
    "asf",
    "divx",
    "mpv",
    "f4v",
    "mxf",
    "wtv",
}


def _expand_episode_range(start: int, end: int) -> List[int]:
    """集数区间展开(第4-6集 -> [4,5,6]); 上限钳制到 9999"""
    return list(range(start, min(end, 9999) + 1))


def _match_episode_pattern(fname: str) -> List[int]:
    """按优先级匹配文件名集数模式: 返回第一个匹配模式提取的集数列表(区间模式展开为多集); 无匹配返回 []"""
    for regex, extractor in _EPISODE_PATTERNS:
        m = regex.search(fname)
        if m:
            return extractor(m)
    return []


def name_has_episode_marker(name: str) -> bool:
    """种子名称是否已含集数标记(S01E01/EP01/第1集等): 含则无需再从文件列表解析"""
    return bool(name and any(regex.search(name) for regex, _ in _EPISODE_PATTERNS))


def extract_episodes_from_files(files: list) -> List[int]:
    """从文件列表解析集数列表(去重排序)

    - 只考虑文件名部分: 忽略文件夹路径(如 "Season 1/01.mkv" 中的 "Season 1")
    - 只考虑视频文件(mkv/mp4/avi 等): 截图(jpg/png)/字幕(ass/srt)/字体等非视频文件跳过
    - 每个文件最多贡献一个集数: 有明确标记(第5集/第05-08集/S01E05/EP05/E05)
      按优先级取第一个匹配的模式; 区间标记(第4-6集)视为一个文件打包多集内容, 展开为 4,5,6
    - 无标记时, 仅当文件名中恰好只有一个候选数字(排除分辨率/年份)才视为集数,
      如 "01.mkv" -> 1; 多个候选数字(如日期截图 "2022.05.11_14.51.23.jpg")
      无法确定唯一集数, 跳过该文件
    - 解析不到返回空列表
    """
    episodes = set()
    for f in files:
        fname = getattr(f, "name", "") or ""
        if not fname:
            continue
        # 只取文件名部分, 忽略文件夹路径(统一分隔符后取最后一段)
        fname = fname.replace("\\", "/").rsplit("/", 1)[-1]
        # 只考虑视频文件: 非视频文件(截图/字幕/字体等)即使含集数标记也跳过
        ext = os.path.splitext(fname)[1].lower().lstrip(".")
        if ext not in _VIDEO_EXTENSIONS:
            continue
        # 1. 明确集数标记: 按优先级取第一个匹配的模式(每个文件一组集数)
        nums = _match_episode_pattern(fname)
        if nums:
            episodes.update(nums)
            continue
        # 2. 无标记: 仅当恰好一个候选数字(排除分辨率/年份)才提取
        candidates = []
        for m in _BARE_NUMBER_RE.finditer(fname):
            num = int(m.group(1))
            if num in _RESOLUTION_SET or (1900 <= num <= 2099):  # 分辨率/年份干扰
                continue
            if 1 <= num <= 9999:
                candidates.append(num)
        if len(candidates) == 1:
            episodes.add(candidates[0])
        # 多个候选数字(日期时间截图等) -> 无法确定唯一集数, 跳过该文件
    return sorted(episodes)


def format_episode_tag(episodes: List[int]) -> str:
    """集数列表 -> 标签: 集数必须连续才添加, 如 [1,2,3,4,5] -> 'E1-5', [3] -> 'E3';
    存在缺集(如 [1,2,3,5])或为空 -> 返回 ''(放弃添加)"""
    if not episodes:
        return ""
    nums = sorted(set(episodes))
    for a, b in zip(nums, nums[1:]):
        if b != a + 1:
            return ""  # 缺集 -> 放弃添加
    return f"zE{nums[0]}" if len(nums) == 1 else f"zE{nums[0]}-{nums[-1]}"

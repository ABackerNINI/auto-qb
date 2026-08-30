"""集数解析(自动添加集数标签)

集数识别是领域逻辑(剧集命名规范), 从 utils 独立出来便于聚焦扩展与测试。
新增命名模式: 在 _EPISODE_PATTERNS 列表合适优先级位置插入一项即可, 无需改提取逻辑。
"""
import os
import re
from typing import List

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

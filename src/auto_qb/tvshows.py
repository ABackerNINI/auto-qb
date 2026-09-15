"""剧集识别(追剧视图): 从种子名/文件列表解析 (剧键, 季, 集键) 三元组

与 episodes.py 同族的领域逻辑模块(零第三方依赖)。追剧视图是无监督聚类 —— 没有
TVDB 之类的真值可对, 只能靠种子自身携带的信息把"同一部剧"聚到一起。因此规则的
核心取向是 **宁可误拆, 不可误并**: 年份/国家标记/续作数字等"身份差分"一律保留进
聚合键 —— 误拆在界面上相邻可见、可人工纠偏(后续迭代), 误合并则几乎不可发现。

解析管线(parse_release):
  ① 定位剧集标记(S01E05/1x05/第x集[话]/EP05/E05/日期/动画 bare number), 以
    **最先出现的位置**为切分点(先找季标记, 集数标记在其之后找, 找不到再全局找);
  ② 标记前段 = 剧名候选(字幕组括号前缀剥离, 见 _strip_group_prefixes);
  ③ 剧名清洗(噪音词表正则 + 归一化) → 展示名 + 聚合键;
  ④ 季缺省: 带集数的无季标记种子归第 1 季(E05/第5集等); 日期型(综艺日播)无季;
  ⑤ 名称无标记 → parse_files 文件列表兜底(视图层接搜索索引缓存, 零新增 qB API)。

集键(episode key)三形态, 统一为元组便于排序与 JSON 序列化:
  ("ep", 5)               单集
  ("range", 1, 25)        多集包/整季包(不展开成 N 行, 一行表达范围)
  ("date", "2026-09-15")  日播/综艺
  ("pack",)               整季包但集数范围未知(文件列表不可用)

已知限制(文档化, 见 docs/webui-shows-view-plan.html):
  - 动画绝对编号(无季标记的 - 05)一律归第 1 季, 不做跨季映射;
  - 纯数字尾缀(Show Name 2)保守保留在剧名里, 不视为季;
  - 简繁异体同剧不做转换(同剧通常同简繁);
  - 多季合包(S01-S04/第1-4季)判为未识别, 避免错误归入单季。
"""
import datetime
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

KIND_EPISODE = "episode"  # 有明确集数(S01E05/第5集/动画编号等)
KIND_SEASON_PACK = "season_pack"  # 有季无集(S01 整包), 集范围待文件列表兜底
KIND_DATE = "date"  # 日期型集键(综艺/日播)
KIND_UNKNOWN = "unknown"  # 无任何标记(电影/命名过野), 进"未识别"折叠区


@dataclass(frozen=True)
class ParsedRelease:
    """单个种子的剧集解析结果(key 为空串 = 未识别出剧名, 视图层归入未识别桶)"""

    key: str  # 规范化剧键(聚合维度)
    title: str  # 清洗后的展示剧名(保留原大小写形态)
    kind: str
    season: Optional[int] = None  # 编号季; None = 未识别/日期型
    ep_start: Optional[int] = None  # 集数起点(含)
    ep_end: Optional[int] = None  # 集数终点(含); None = 单集
    date: Optional[str] = None  # ISO 日期(仅 KIND_DATE)

    @property
    def episode_key(self) -> tuple:
        """视图层的集节点键(kind=unknown 不取用)"""
        if self.kind == KIND_DATE:
            return ("date", self.date)
        if self.ep_start is None:
            return ("pack", )
        if self.ep_end is not None and self.ep_end != self.ep_start:
            return ("range", self.ep_start, self.ep_end)
        return ("ep", self.ep_start)


# ---------------------------------------------------------------- 中文数字

_CJK_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cjk_int(s: str) -> Optional[int]:
    """中文数字 → 整数(支持 一~一百零九 的常规写法); 解析失败返回 None"""
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    if not s:
        return None
    total, num = 0, 0
    for ch in s:
        if ch in _CJK_DIGITS:
            num = _CJK_DIGITS[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
        else:
            return None
    return total + num


# ---------------------------------------------------------------- 标记模式

_NUM_GROUP = r"(\d{1,4}|[零一二两三四五六七八九十百]{1,6})"

# 季标记(独立出现, 不带集数)。S01 需负向预查排除 S01E05/S01x05/S1 E05 —— 带集数的
# S 由集数模式匹配并回填季号, 若此处也命中会重复计位(标题被切短)。
_SEASON_PATTERNS = [
    (re.compile(r"(?<![A-Za-z0-9])[Ss](\d{1,2})(?![A-Za-z0-9]|\s*[EeXx]\s*\d)"), lambda m: _cjk_int(m.group(1))),
    (re.compile(r"(?<![A-Za-z0-9])Season[ ._-]?(\d{1,2})(?![0-9])", re.IGNORECASE), lambda m: _cjk_int(m.group(1))),
    (re.compile(r"第\s*" + _NUM_GROUP + r"\s*季"), lambda m: _cjk_int(m.group(1))),
    (re.compile(r"第\s*(\d{1,2})\s*期"), lambda m: _cjk_int(m.group(1))),
    (
        re.compile(r"(?<![A-Za-z0-9])(\d{1,2})(?:st|nd|rd|th)[ ._-]?Season\b",
                   re.IGNORECASE), lambda m: _cjk_int(m.group(1))
    ),
]

# 集数标记。每个 extractor 返回 (集起点, 集终点或None, 内嵌季号或None)。
# 每项第三元 bare 标志: 动画 bare number 只认 "- 05" 与 "[05]"/"(05)" 两种形态,
# 且起点需过 _bare_ok(排除分辨率/年份); 其余模式起点不设此限(E1080 类大编号合法)。
# 裸尾随数字(如 Oceans.11)不识别 —— 与 episodes.py 禁用 bare number 同一顾虑。
_EPISODE_PATTERNS = [
    # S01E05 / S01E05-E06 / S01E05E06 / S01x05(季号内嵌, 优先级最高)
    # 区间续接两分支: "-06"/"-E06"(破折号 + 可选 E)与 "E06"(直接连写); 裸空格接数字不算区间
    # (防 "S01E05 720p" 被当成 E05-E720 区间)
    (
        re.compile(
            r"(?<![A-Za-z0-9])[Ss](\d{1,2})\s*[EeXx]\s*(\d{1,4})(?:\s*[-~至到]\s*[Ee]?\s*(\d{1,4})|\s*[Ee](\d{1,4}))?"
        ),
        lambda m: (_cjk_int(m.group(2)), _cjk_int(m.group(3) or m.group(4)), _cjk_int(m.group(1))),
        False,
    ),
    # 1x05(旧 scene 风格, 季号内嵌)
    (
        re.compile(r"(?<![A-Za-z0-9])(\d{1,2})[Xx](\d{1,4})(?![0-9])"),
        lambda m: (_cjk_int(m.group(2)), None, _cjk_int(m.group(1))),
        False,
    ),
    # 第5集 / 第05-08集 / 第5话(話) / 第五集
    (
        re.compile(r"第\s*" + _NUM_GROUP + r"(?:\s*[-~至到]\s*" + _NUM_GROUP + r")?\s*[集话話]"),
        lambda m: (_cjk_int(m.group(1)), _cjk_int(m.group(2)), None),
        False,
    ),
    # EP05 / Episode 5
    (
        re.compile(r"(?<![A-Za-z0-9])(?:EP|Episode)[ ._-]?(\d{1,4})(?![0-9])", re.IGNORECASE),
        lambda m: (_cjk_int(m.group(1)), None, None),
        False,
    ),
    # E05(带左边界防 webdl5 类粘连)
    (
        re.compile(r"(?<![A-Za-z0-9])E(\d{1,4})(?![0-9])", re.IGNORECASE),
        lambda m: (_cjk_int(m.group(1)), None, None),
        False,
    ),
    # - 05 [1080p] / - 05 (行尾): 破折号形态(动画字幕组命名)
    (
        re.compile(r"(?<![\u4e00-\u9fff])[-–—]\s*(\d{1,4})(?:[Vv](\d+))?(?=\s*(?:$|[\[(【]))"),
        lambda m: (_cjk_int(m.group(1)), None, None),
        True,
    ),
    # [05] / (05) / [05v2]: 中括号形态
    (
        re.compile(r"[\[(](\d{1,4})(?:[Vv]\d+)?[\])]"),
        lambda m: (_cjk_int(m.group(1)), None, None),
        True,
    ),
]

# 日期型集键(综艺/日播): 2026.09.15 / 2026-09-15, 仅认 20xx 开头(与分辨率 1920/1080 天然区隔)
_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[ ._-](\d{1,2})[ ._-](\d{1,2})(?!\d)")

# 多季合包(S01-S04 / 第1-4季): 无法归入单季, 判为未识别(宁可进未识别桶也不错归 S1)。
# 第二个季号必须有 [Ss] 前缀或与破折号紧邻 —— 否则 "S2 - 05 [1080p]"(S2 第5集)会被误判成
# "S2-S5" 多季合包。
_MULTI_SEASON_RE = re.compile(
    r"(?<![A-Za-z0-9])[Ss]\d{1,2}[-~][Ss]?\d{1,2}(?![0-9])"
    r"|(?<![A-Za-z0-9])[Ss]\d{1,2}\s*[-~]\s*[Ss]\d{1,2}(?![0-9])"
    r"|第\s*\d{1,2}\s*[-~至到]\s*\d{1,2}\s*季"
)

# bare number 排除集: 分辨率与年份(1900-2099)
_BARE_EXCLUDE = {480, 576, 720, 1080, 2160, 4320}


def _bare_ok(n: Optional[int]) -> bool:
    return n is not None and n not in _BARE_EXCLUDE and not (1900 <= n <= 2099)


def _find_season(name: str) -> Optional[tuple]:
    """最早的季标记: 返回 (start, end, 季号); 无则 None"""
    best = None
    for regex, extractor in _SEASON_PATTERNS:
        m = regex.search(name)
        if not m:
            continue
        s = extractor(m)
        if s is None or not 1 <= s <= 99:
            continue
        if best is None or m.start() < best[0]:
            best = (m.start(), m.end(), s)
    return best


def _find_episode(name: str, after: Optional[int]) -> Optional[tuple]:
    """最早的集数标记: 返回 (start, end_pos, 集起点, 集终点, 内嵌季号); 无则 None

    两轮扫描: 有季标记时先只在季标记**之后**找(季在前集在后的常规命名);
    找不到再全局找(兼容 "Show E05 S01" 的集前季后写法)。
    """
    for pos in ([after] if after is not None else []) + [0]:
        best = None
        for regex, extractor, is_bare in _EPISODE_PATTERNS:
            m = regex.search(name, pos)
            if not m:
                continue
            start, end, embedded = extractor(m)
            if is_bare:
                if not _bare_ok(start):
                    continue  # 分辨率/年份不是集数(仅 bare 形态需此排除)
            elif start is None or not 1 <= start <= 9999:
                continue
            if end is not None and (end < start or end > 999):
                end = None  # 区间终点异常(常见为 1080p 粘连)按单集处理
            if best is None or m.start() < best[0]:
                best = (m.start(), m.end(), start, end, embedded)
        if best is not None:
            return best
    return None


def _find_date(name: str) -> Optional[tuple]:
    """最早的合法日期标记: 返回 (start, ISO 日期); 无则 None"""
    for m in _DATE_RE.finditer(name):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            datetime.date(y, mo, d)
        except ValueError:
            continue  # 月份/日期越界(如 2023.13.99)不算日期
        return m.start(), f"{y:04d}-{mo:02d}-{d:02d}"
    return None


# ---------------------------------------------------------------- 剧名清洗

# 剧名噪音词(发布参数类): 正则形态在归一化**之前**剥除(此时 5.1/web-dl 等尚未被拆散)。
# 注意: 年份/国家/续作数字是身份差分, 一律不在剥除之列(见模块 docstring 的取向说明)。
_NOISE_RE = re.compile(
    r"(?ix)(?<![a-z0-9])("
    r"\d{3,4}[ip]"  # 480p/720p/1080i/2160p
    r"|\d{1,2}bit|\d+fps"
    r"|4k|8k|uhd|fhd"
    r"|web[ ._-]?dl|web[ ._-]?rip"
    r"|hdtv|pdtv|bdrip|brrip|blu[ ._-]?ray|dvd(?:rip|r|5|9)?|remux|bd[ ._-]?rip"
    r"|x26[45]|h\.?26[45]|hevc|avc|xvid|divx|av1|vp9|mpeg-?[24]"
    r"|dd(?:p|\+)?(?:[ .]?\d(?:[ .]\d)?)?"  # DD/DD+/DDP/DDP5.1/DD5.1
    r"|ac-?3|eac-?3|dts(?:[ ._-]?h?d?(?:[ ._-]?ma)?)?|truehd|atmos"
    r"|flac|aac(?:[ .]?\d(?:\.\d)?)?|opus|l?pcm|mp3"
    r"|5[ .]1|7[ .]1|2[ .]0"
    r"|hdr(?:10)?\+?|dolby[ ._-]?(?:vision|atmos)|dovi"
    r"|proper|repack|remastered|extended|uncut|internal|retail|dual[ ._-]?audio"
    r")(?![a-z0-9])"
)

# 剧名噪音词(中文发布说明类)
_CJK_NOISE_RE = re.compile(
    "全集|全一?季|完[结语篇]|中[文字]{1,2}|简[体繁]|繁[体體]|简繁|雙語|双语|内[嵌封]|內[嵌封]"
    "|熟肉|生肉|官[方中]|中配|国语|國語|普通话|粤语|粵語|台配|无字幕|無字幕|硬字幕|外挂"
    "|特效字幕|字幕组|字幕社|简中|繁中|日配|压制|搬运"
)

# 归一化后仍残留的零散噪音 token(语言标记等); 纯数字 token 一律保留(身份差分)
_EXTRA_NOISE_TOKENS = frozenset(
    (
        "dl",
        "rip",
        "hd",
        "sd",
        "chs",
        "cht",
        "tc",
        "sc",
        "eng",
        "chi",
        "jpn",
        "jp",
        "sub",
        "subs",
        "raw",
        "v1",
        "v2",
        "v3",
        "complete",
        "pack",
        "season",
    )
)
_EXTRA_NOISE_BIGRAMS = frozenset(("web dl", "dts hd", "dts hd ma", "dd plus", "dual audio", "hdr10 plus"))

_LEADING_BRACKET_RE = re.compile(r"^[\[(]([^\[\]()]{1,64})[\])]\s*")
_GROUP_HINTS = (
    "sub", "fansub", "raw", "group", "team", "release", "studio", "forum", "字幕", "汉化", "漢化", "翻译", "翻譯", "工坊", "制作",
    "製作"
)

_TRIM_CHARS = " \t-–—_.·"


def _is_groupish(s: str) -> bool:
    low = s.lower()
    return any(h in low for h in _GROUP_HINTS)


def _strip_group_prefixes(seg: str) -> str:
    """剥离字幕组括号前缀, 返回标题候选

    - "[Group] Title - 05" 形态: 前缀括号段丢弃, 余下文本即标题;
    - "[Group][Title][05]" 形态(余下为空): 从括号段内容里取**最后一个**非纯数字、
      非组名特征的候选作标题(组名通常在前, 标题在后);
    - 剥空了也找不到候选: 返回原段(交由归一化, 通常最终落进未识别桶)。
    """
    stripped = []
    rest = seg
    while True:
        m = _LEADING_BRACKET_RE.match(rest)
        if not m:
            break
        stripped.append(m.group(1).strip())
        rest = rest[m.end():]
    if rest.strip(_TRIM_CHARS + "[]()"):
        return rest
    cands = [s for s in stripped if s and not s.isdigit()]
    if not cands:
        return seg
    non_group = [s for s in cands if not _is_groupish(s)]
    return (non_group or cands)[-1]


def _normalize_key(title: str) -> str:
    """展示名 → 规范化聚合键: 全角半角折叠 + 标点剥除 + 小写 + 零散噪音 token 剔除"""
    s = unicodedata.normalize("NFKC", title)
    s = re.sub(r"[^\w\s]+", " ", s)
    tokens = [t for t in s.lower().split() if t not in _EXTRA_NOISE_TOKENS]
    out, i = [], 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i] + " " + tokens[i + 1] in _EXTRA_NOISE_BIGRAMS:
            i += 2
            continue
        out.append(tokens[i])
        i += 1
    return " ".join(out)


def _title_and_key(seg: str) -> Tuple[str, str]:
    """标记前段 → (展示名, 聚合键); 全噪音时两者皆空串(未识别)"""
    seg = seg.strip(_TRIM_CHARS)
    if not seg:
        return "", ""
    seg = _strip_group_prefixes(seg)
    seg = _NOISE_RE.sub(" ", seg)
    seg = _CJK_NOISE_RE.sub(" ", seg)
    # 展示名同步点/下划线 → 空格(scene 命名的 "Show.Name" 展示为 "Show Name"), 保留原大小写
    title = re.sub(r"[._]+", " ", seg)
    title = re.sub(r"\s+", " ", title).strip(_TRIM_CHARS + "[]()【】")
    return title, _normalize_key(title)


# ---------------------------------------------------------------- 入口

_UNKNOWN = ParsedRelease("", "", KIND_UNKNOWN)


def parse_release(name: str) -> ParsedRelease:
    """种子名 → ParsedRelease; 解析不出剧名时 key 为空串(视图层归未识别桶)

    标题切分点 = 最早出现的任意标记(季/集/日期)的起点 —— 如 "Show Name S2 - 05"
    的标题按季标记切("Show Name"), 而不是按集数标记切("Show Name S2")。
    """
    name = (name or "").strip()
    if not name:
        return _UNKNOWN
    if _MULTI_SEASON_RE.search(name):
        return _UNKNOWN  # 多季合包不归单季, 进未识别桶
    season = _find_season(name)
    ep = _find_episode(name, season[1] if season else None)
    date = _find_date(name)
    cuts = [m[0] for m in (season, ep, date) if m is not None]
    if ep is not None:
        _, _, start, end, embedded = ep
        s = embedded if embedded is not None else (season[2] if season else None)
        if s is None:
            s = 1  # 带集数但无季标记(第5集/EP05/动画编号): 按第 1 季归档
        title, key = _title_and_key(name[:min(cuts)])
        return ParsedRelease(key, title, KIND_EPISODE, s, start, end)
    if date is not None:
        title, key = _title_and_key(name[:min(cuts)])
        return ParsedRelease(key, title, KIND_DATE, date=date[1])
    if season is not None:
        title, key = _title_and_key(name[:min(cuts)])
        return ParsedRelease(key, title, KIND_SEASON_PACK, season[2])
    title, key = _title_and_key(name)
    return ParsedRelease(key, title, KIND_UNKNOWN)


def parse_files(names: List[str]) -> Tuple[Optional[int], List[int]]:
    """文件列表(相对路径)兜底: 返回 (季号或None, 集数列表)

    - 季号扫**目录段**(Season 01/S01/第1季), 文件名部分不参与;
    - 集数复用 episodes 的解析(仅视频文件、明确标记、无 bare number)。
    """
    from . import episodes as _episodes

    season = None
    for n in names:
        parts = (n or "").replace("\\", "/").split("/")
        for part in parts[:-1]:
            p = part.strip()
            m = (
                re.search(r"第\s*(\d{1,2}|[一二三四五六七八九十]{1,3})\s*季$", p) or
                re.search(r"Season[ ._-]?(\d{1,2})$", p, re.IGNORECASE) or re.search(r"^[Ss](\d{1,2})$", p)
            )
            if m:
                season = _cjk_int(m.group(1))
                break
        if season is not None:
            break
    return season, _episodes.extract_episodes_from_names(names)


def refine_with_files(parsed: ParsedRelease, files: List[str]) -> ParsedRelease:
    """用文件列表补全: 整季包展开集数范围; 未识别种子从文件名抢救集数

    已有明确集数/日期的结果不改(名称标记优先于文件推断); 无剧名的结果同样不动。
    """
    if parsed.kind in (KIND_EPISODE, KIND_DATE) or not parsed.key:
        return parsed
    season_f, eps = parse_files(files)
    if not eps:
        return parsed
    start, end = min(eps), max(eps)
    season = parsed.season if parsed.season is not None else (season_f if season_f is not None else 1)
    return replace(
        parsed,
        kind=KIND_EPISODE,
        season=season,
        ep_start=start,
        ep_end=end if end != start else None,
    )

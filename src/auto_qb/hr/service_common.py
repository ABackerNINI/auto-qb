"""hr service 共用叶: logger / 常量 / 数据类 / 模块级纯函数(自 service.py move-only 切出)

拆分(R5)只搬位置: 区段文本与 service.py 原文件逐字一致, 仅 logger 名显式沿用原模块名。
"""
import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional, Set, Tuple

from .model import (
    FETCH_LANES,
    FULL_DEPTH_TEXT,
    LANE_FAILED,
    LANE_OK,
    LANE_TAGS,
    HrEntry,
    HrLaneState,
    HrSiteData,
    HrVerified,
    _lane_count_segment,
)
from .ratelimit import HrLimits, next_allowed_at, try_consume
from .resolve import HrAnchor

logger = logging.getLogger("auto_qb.hr.service")

# 刷新动作(报告的 action 字段)
ACTION_DISABLED = "disabled"
ACTION_REUSED = "reused"
ACTION_REFRESHED = "refreshed"
ACTION_PARTIAL = "partial"  # 波跑了一部分(预算截断/页面失败) —— 截断点之前的数据仍然有效
ACTION_WAITING = "waiting"  # 未到可取时刻(拉取间隔 / min_interval / 日额 / Retry-After / 时间窗 / 复用窗)
ACTION_LOCKED = "skipped-locked"
ACTION_NO_CHANNEL = "no-channel"
ACTION_ERROR = "error"

# 本轮「没跑完」的原因分类(告警分级与报告展示用)。
# !被**自己的频控**拦下 ≠ 故障: 那是设计如此, 而且会持续几小时;
#   真值得盯着的是页面/解析问题(可能是改版)。两者混成同一级会让用户在弹窗轰炸中开始忽略告警。
REASON_NONE = ""  # 没有「没跑完」这回事
REASON_BUDGET = "budget"  # 被自己的间隔/日额/时间窗拦下(可预期, 下轮继续)
REASON_PARSE = "parse"  # 页面/字段/翻页问题(可能是改版) —— 值得告警

# 生产路径在锁内等满频控间隔的上限(沿用 v2 口径): 单次等待超限放弃本档本轮;
# 一波的总等待超限放弃剩余请求(下波继续), 避免一次波把站点锁长期占住。
PROD_REQUEST_WAIT_MAX = 300.0
PROD_ROUND_WAIT_MAX = 900.0

#: 走查(--hr-once)单次最多等待的秒数: 防配置误设(如间隔 1H)把走查挂死
DIAGNOSTIC_MAX_WAIT = 600.0

# ---------------- v3 波次模型常量(程序能定的绝不配置, §6) ----------------

#: 覆盖早停1. 的对齐余量(§4.2): 本地完成时刻与站点页面完成时间的时差容差(时钟漂移/传输确认差);
#: 余量内不能确定就继续翻 —— 保守方向多花页数, 不会漏。
COVERAGE_SLACK = 86400.0  # 1D

#: 停翻2. 到期段强信号(§4.2): 页尾连续 N 行「剩余考察时间」为 0(跨页延续) ⇒ 深处全是到期行,
#: 考察中的对象(remain>0)不可能藏在更深处; 藏在深处的到期行无论看到与否结论相同 —— 停翻零漏判。
ZERO_REMAIN_STREAK = 5

#: 超额线(§3.3): 本地做种时长 >= 要求时长 × 该倍数 ⇒ 放行并免除在线对账义务(不进覆盖对象集)。
#: !不是判定上的免死金牌: 被动命中「考察中」仍是「考察中」(网站绝对权威)。
SEED_EXEMPT_RATIO = 3.0

#: 失踪观察期(§3.4): 上波命中考察中的种子, 自身位置被覆盖且连续 N 波未重见 ⇒ 判「移出」放行;
#: 任何波重见 ⇒ 按档位定论。「没看到」不终结「考察中」。
MISSING_GRACE_WAVES = 2

#: A 档流转守恒(§5.3, 首要防伪): 上波 A 档行在本波 A/B/C 已见行中的留存率须 >= 该值,
#: 不达标 ⇒ 批量「未列出」签发冻结(防 A 段定向吞行被当「未列出」整批误放行)。
LANE_RETENTION_MIN = 0.7

#: B/C/D 终态行宽泛名称粗配阈值(§4.5 D1 拍板): **去掉技术噪声后**本地名称与行名称存在足够长的
#: 连续重合段即判疑似本地; 粗配只是下载触发器, 定论一律 infohash 精配。
#: !2026-09-29 收紧: K 仍是 12, 变的是「拿哪部分参与重合」(见 FUZZY_NOISE_TOKEN)。
FUZZY_NAME_K = 12

#: 粗配前必须剔除的**技术噪声整词**: 分辨率 / 来源 / 编码 / 音轨 / 发布类型 / 字幕标记。
#: 做法是**先按分隔符切词再逐词判**(不做子串替换 —— 免得把标题里的字符一起啃掉)。
#: 这些词在几乎每个发布里都一样, 任由它们参与重合会造出成片的假重合。
#: 实证(2026-09-29, 用户真实数据 108 本地名 × 50 活跃行): 旧判据 159 对命中里 128 对是纯噪声段
#: (`1080pwebdlh26` / `0pwebdlh265aac` / `2026s01complete1080p` 这类 —— 注意最后一条 20 字符,
#: 光提高 K 拦不住), 真命中只有 Futsutsuka 与 Cat&Dragon 两族名称; 剔除后剩 31 对全真、**零新增**。
#: 顺带验过「再剔发布组后缀(最后一个 `-` 后的短段)」在本批数据上零收益(4 对 → 4 对), 故不做。
FUZZY_NOISE_TOKEN = re.compile(
    r"^(?:"
    r"(?:2160|1080|720|540|480|360)p|4k|8k|uhd|fhd|hd|sd|"
    r"(?:x|h)26[45]|26[45]|hevc|avc|av1|xvid|divx|vc1|"
    r"(?:10|8)bit|hi10p|"
    r"(?:aac|ac3|eac3|ddp?|dts|truehd|atmos|flac|mp3|opus|vorbis)\d*(?:ch)?|"
    r"web|webdl|webrip|dl|bd|blu|bluray|bdrip|brrip|hdtv|dvd|dvdrip|remux|rip|"
    r"nf|cr|amzn|dsnp|hmax|atvp|itunes|friday|hulu|pcok|"
    r"complete|repack|proper|internal|limited|multi|dual|"
    r"hdr|hdr10|sdr|dv|dolbyvision|"
    r"chs|cht|chtw|eng|jpn|kor|sc|tc"
    r")$"
)

#: 页面快照条目的陈旧淘汰(不触碰永久层 hr_downloaded)
INDEX_RETENTION = 30 * 86400.0

#: 单个 .torrent 取数失败重试上限, 达到后冷却(防烧配额)
MAX_DOWNLOAD_RETRIES = 3
#: 下载失败冷却时长(达重试上限后)
DL_RETRY_COOLDOWN = 3600.0

#: 通道静默告警阈值 / 同类解析告警的节流窗口
CHANNEL_SILENCE_WARN = 6 * 3600.0


def warn_gap_floor(threshold: float) -> float:
    """告警节流窗口的公共算法: 给定阈值下限 60s(防配置成 0 时刷屏)。

    service 与 worker 的节流点共用此算法(此前各写一遍 `max(60.0, float(<常量>))`); 阈值本身
    仍是各模块自己的常量, 便于单测按模块打补丁。
    """
    return max(60.0, float(threshold))


#: 取数线程醒来检查的节奏(worker 用; 配置键已删除, 常量化 §6.2)
POLL_INTERVAL = 60.0

#: 连续 N 波同档失效 → ERROR 告警(疑似改版, 建议 --hr-once 走查; §5.2 告警升级)
LANE_FAIL_ALERT_STREAK = 3

#: 全档失效时的数据复用短窗(盖过下一轮 —— 与 v2 同款理由)
ALL_FAILED_REUSE_WINDOW = 120.0

#: 拉取历史(计划 26-10-04-0312 §3.3): 记录器搬运现成文案时的截断口径
HISTORY_REASON_MAX = 200  # reason 截断长度(字符)
HISTORY_NOTES_MAX = 5  # wave.notes 保留条数(取前几条过程痕迹)


def _fuzzy_signal(name: str) -> str:
    """归一化到「信号串」: 小写 → 按分隔符切词 → 剔除技术噪声整词 → 拼回。

    切词时保留 CJK 连续段(汉字无分隔符, 整段即一个词)。拼回后分隔符形态差异(. - _ 空格)
    自然消失, 与旧判据「折叠全部非字母数字」行为一致 —— 只是中间多一道噪声过滤。
    """
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", (name or "").lower())
    return "".join(t for t in tokens if not FUZZY_NOISE_TOKEN.match(t))


def fuzzy_name_match(local_name: str, row_name: str, k: int = FUZZY_NAME_K) -> bool:
    """宽泛名称粗配(D1 拍板, §4.5): 两侧**信号串**存在长度 >= k 的连续重合段即判疑似本地。

    不是完整 / 前缀匹配, 判据仍偏宽: 误配 = 多下载一次(由 A 档全下载的精配自愈), 漏配最坏误管束
    (保守)。但「宽」只体现在**标题段**上 —— 分辨率/来源/编码/音轨这些每个发布都一样的词不参与
    重合(见 `FUZZY_NOISE_TOKEN`), 否则 12 字符的下限会被质量标签整段占满。

    信号串完全相等时不受 K 下限约束: 这是**短标题**的兜底通路(例: 同一中文标题在两个站点后缀
    不同)。已知残余(不修, 属行 4 本地兜底): 标题段短于 K 且两侧组标不同 ⇒ 不触发粗配。
    """
    a, b = _fuzzy_signal(local_name), _fuzzy_signal(row_name)
    if not a or not b:
        return False
    if a == b:
        return True  # 信号串完全相等: 不受 K 下限约束(短名精确同名也判疑似)
    if len(b) < k:
        return False
    return any(b[i:i + k] in a for i in range(len(b) - k + 1))


@dataclass(slots=True)
class HrRefreshResult:
    """一次波的结果(报告与日志用; 不含任何 qB 联动)"""

    site: str
    action: str
    reason: str = ""
    #: 没跑完的原因分类(REASON_*); 告警分层看它 —— 见模块顶部说明
    reason_kind: str = REASON_NONE
    #: 本轮是否**已由产生处**(本服务 / 存储层)报过 WARNING ⇒ 状态记录只记 INFO, 不重复告警
    alerted: bool = False
    pages_fetched: int = 0
    entries: int = 0
    torrents_fetched: int = 0
    torrents_failed: int = 0
    verified_count: int = 0
    path: str = ""
    lock_ok: bool = True
    persisted: bool = False
    elapsed_s: float = 0.0
    #: 各档波次状态的人话摘要(报告预览用; 生产消费方读已发布的只读视图)
    lane_texts: str = ""
    #: 本波签发的「未列出」放行数(批量 + 观察期出口; 观测)
    releases_signed: int = 0
    #: 本波结束时的**内存快照**(仅供走查/报告预览; 生产消费方读已发布的只读视图, 不读它)
    snapshot: Optional[HrSiteData] = None

    @property
    def ok(self) -> bool:
        return self.action in (ACTION_REFRESHED, ACTION_REUSED)


class _Budget:
    """一波内的请求预算: 每发起一次站点请求(页 / .torrent)都要过这里(单模型, §5.1)。

    - 间隔: 相邻两次请求间隔 >= min_interval(抖动只向上)
    - 日额: 全部请求合计, 零点重置, 到顶即截断(不报错)
    - Retry-After / allow_window: 由 next_allowed_at 一并给出

    sleeper 非空时遇到门槛**等满再发**(生产与走查都传); 等待上限两档: 单次 `sleep_max`,
    本波累计 `round_wait_max`(0 = 不限) —— 超限即放弃本波剩余请求, 不持着站点锁干等。
    """
    def __init__(
        self,
        data: HrSiteData,
        limits: HrLimits,
        now_fn,
        sleeper: Optional[Callable[[float], None]] = None,
        *,
        sleep_max: float = PROD_REQUEST_WAIT_MAX,
        round_wait_max: float = PROD_ROUND_WAIT_MAX,
    ) -> None:
        self._data = data
        self._limits = limits
        self._now = now_fn
        self._sleeper = sleeper
        self._sleep_max = sleep_max
        self._round_wait_max = round_wait_max
        self._waited = 0.0

    @property
    def waited(self) -> float:
        """本波已等掉的总秒数(供排障 / 断言)"""
        return self._waited

    def take(self) -> Tuple[bool, str]:
        """申请一次请求名额(页面与下载统一)"""
        now = self._now()
        due, why = next_allowed_at(self._data, self._limits, now)
        if due > now:
            wait = due - now
            if self._sleeper is None or wait > self._sleep_max or \
                    (self._round_wait_max > 0 and self._waited + wait > self._round_wait_max):
                return False, f"{why}: 还差 {wait:.0f}s"
            self._sleeper(wait)
            self._waited += wait
            now = self._now()
        if not try_consume(self._data, self._limits, now, 1):
            return False, "日额已用尽"
        return True, ""

    def mark(self) -> None:
        """请求已发出: 记下时刻, 作为下一次间隔门槛的基准"""
        self._data.rate.last_fetch_ts = self._now()


class _WaveContext:
    """一波内的可变状态(全部是波级临时量, 波结束即弃)"""
    def __init__(self, anchors: Mapping[str, HrAnchor]) -> None:
        self.anchors: Mapping[str, HrAnchor] = anchors
        self.local_hashes: Set[str] = {h for h in anchors if h}
        # 名称候选面(仅身份下载触发器 `_row_looks_local` 用): 只放**受管(未排除)**种子名 ——
        # 排除种子无对账义务(判定侧已短路), 其名称不该驱动 .torrent 下载(issue 26-10-08-1304)。
        # !命中面 `local_hashes` 仍从全量锚点构建(排除 ≠ 不认识)。
        self.local_names_managed: Tuple[str, ...] = tuple(
            a.name for a in anchors.values() if getattr(a, "name", "") and not a.excluded
        )
        self.seen: Dict[int, HrEntry] = {}  # 本波已见行 tid -> 行对象
        self.hits: Dict[str, str] = {}  # infohash -> 命中档位(本波定论)
        self.retracted = 0  # 撤销的放行记录数(观测)
        self.pending_downloads: Set[int] = set()  # 待身份登记的 tid(3.停翻的「无待回填」判据)
        self.dl_by_hash: Dict[str, int] = {}  # 永久层身份缓存(infohash -> tid), 行处理用
        self.order_directions: Dict[str, str] = {}  # 档位 -> 波级方向(翻转视同违反)
        self.prev_dones: Dict[str, List[float]] = {}  # 档位 -> 上一页完成时刻(跨页证据)
        self.zero_remain_streaks: Dict[str, int] = {}  # 档位 -> 跨页 remain==0 连续行数
        self.trusted_done: Dict[str, float] = {}  # infohash -> 可信完成时刻(1.的判据, §4.2 分层)
        self.current_lane: str = ""  # 当前正在取页的档位(页面级失败时定位截断档)
        # 档位 -> 站点声明行数(计划 26-09-29-2036 §2.1 波内临时账; 首个非 None 胜出 —— tab 形
        # 第 1 页即有值, 分页区间形中途页无键、末页才非 None 自然胜出; 随波生灭, 持久化面在 HrLaneState)
        self.counter_claims: Dict[str, int] = {}
        self.parse_problem = False
        self.budget_limited = False
        self.had_error = False
        self.notes: List[str] = []

    def seen_rows(self) -> Mapping[int, HrEntry]:
        return self.seen


def _release_record(
    *, infohash: str, tid: int, verified_ts: float, source: str, anchor: Optional[HrAnchor]
) -> HrVerified:
    """构造放行记录 —— **锚点快照的单点**(计划 §7.2: verified 记录「含锚点与 source」)。

    !三处签发(批量未列出 / 终态冻结 / 观察期移出)必须都经这里: 漏带快照的记录会被判定侧
    当成「锚点漂移」在**签发当刻**作废 —— 放行记录形同虚设, 种子回落本地兜底(2026-09-29 实报)。
    无锚点(本机已无该种子)时给全零 —— 判定侧的 `anchor is not None` 闸门自会跳过漂移检查。
    """
    snap = anchor if anchor is not None else HrAnchor()
    return HrVerified(
        infohash=infohash,
        tid=tid,
        verified_ts=verified_ts,
        source=source,
        anchor_added_on=snap.added_on,
        anchor_downloaded=snap.downloaded,
        anchor_completion_on=snap.completion_on,
        anchor_progress=snap.progress,
    )


class _LaneAbort(Exception):
    """档位结构失效的轮内跳出(表头缺失 / 字段缺失): 该档截断, 其它档继续(§3.4 档位独立)"""
    def __init__(self, lane: str, reason: str) -> None:
        super().__init__(reason)
        self.lane = lane
        self.reason = reason


def _settle_lane(st: HrLaneState, *, failed_detail: str, truncated_detail: str, count_failure: bool) -> bool:
    """档位收尾单点(§3.4 档位独立): 本波无页 = 记失效(可推进连续失效计数), 有页 = 记截断(之前有效)。

    三处调用只在文案与「是否推进连续失效」上不同: 结构失效 / 取数失败推进(要触发多波升级告警),
    预算截断不推进(不是故障)。返回 True = 记了失效(供调用方决定是否升级告警)。
    """
    if st.pages == 0:
        st.status = LANE_FAILED
        st.detail = failed_detail
        if count_failure:
            st.fail_streak += 1
        return True
    st.status = LANE_OK
    st.full_depth = False
    st.detail = truncated_detail
    return False


def _mark_fetch_failed_lane(lane_states, wave: "_WaveContext") -> bool:
    """页面级取数失败: 失败页无效, 该档在失效点截断(之前有效); 首页即失败 = 该档失效

    返回 True = 记了失效(调用方据此决定要不要走连续失效的升级告警, 与 `_settle_lane` 同口径)。
    """
    st = lane_states.get(wave.current_lane)
    if st is None or st.status == LANE_OK:
        return False
    return _settle_lane(st, failed_detail="页面取数失败", truncated_detail="页面取数失败(失效点之前数据有效)", count_failure=True)


# ---------------- 模块级纯函数(便于单测直调) ----------------


def _dl_by_hash(data: HrSiteData) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in data.downloaded.values():
        for h in (d.infohash_v1, d.infohash_v2):
            if h and h not in out:
                out[h] = d.tid
    return out


def _lane_covers_done(st, done: Optional[float], slack: float = 0.0) -> bool:
    """单档对「完成时刻 = done」这个位置的覆盖证明是否成立(§3.4, 三处判据的唯一口径)。

    - 全深度档(翻到末页 / 2.到期段停翻): 对**任意位置**成立, 位置无关;
    - 位置有界档(1.完成时间覆盖 / 3.本地全集停翻 / 预算或失效点截断): 仅当 done 已知且
      ``done - slack >= cutoff_done`` 才成立 —— 比它更深的页没翻到, 不可判;
    - ``cutoff_done <= 0`` = 该档**没有位置概念**(model.py 注释原话「0 = 没有位置概念」;
      供给侧 `_update_cutoff` 只在 page_deepest>0 时前进 ⇒ 整列 done 不可解析时恒为 0)
      ⇒ 位置**不可证**。

    第三条必须显式判死: 漏了它, `done < 0` 对任意真实 epoch(≈1.7e9)恒为 False, 「未覆盖」
    出口永不触发, 三处判据一起退化成恒通过 —— 终态冻结 / 观察期出口 / 批量签发三条路全部
    签发永续放行, 种子就此退出 HR 管束(issue 26-10-30-0550)。
    """
    if st.full_depth:
        return True
    if done is None or done <= 0:
        return False
    if st.cutoff_done <= 0:
        return False
    return done - slack >= st.cutoff_done


def _position_covered(entry: HrEntry, lane_states) -> bool:
    """种子完成时间位置是否被本波各档覆盖(§3.4 观察期推进判据)。

    条目的 done_iso 是**站点侧**时刻(无时钟漂移问题), 覆盖 = 该档全深度, 或
    done >= 该档已见最深行的完成时刻(更深未翻不可判)。任一档无有效数据 ⇒ 不可判。"""
    done = entry.done_epoch
    if done is None:
        return False
    for lane in FETCH_LANES:
        st = lane_states.get(lane)
        if st is None or not st.ok:
            return False
        if not _lane_covers_done(st, done):
            return False
    return True


def _absence_proven_all(lane_states, wave: _WaveContext, anchor: HrAnchor) -> bool:
    """该种子在所有取数档位的缺席证明(§3.2 行 3: 完成时间位置被覆盖且未命中)。

    全深度档(末页 / 2.到期段停翻)对**任意位置**的缺席证明成立 —— 深处的到期行无论看到与否
    结论相同(命中 → 终态放行, 没看到 → 未列出放行), 不依赖完成时间可信度; 位置有界档
    (1./3.停翻或截断)则需要可信完成时间推定位置(本机下载完成)—— 纯辅种只能由全深度收尾
    (方向安全, 只费页数, §4.2 可信度分层)。"""
    done = float(anchor.completion_on) if anchor.completion_on and anchor.completion_on > 0 else 0.0
    for lane in FETCH_LANES:
        st = lane_states.get(lane)
        if st is None or not st.ok or st.wave_ts <= 0:
            return False
        # 新鲜度闸门: 种子 added_on 晚于该档本波取数 ⇒ 该档快照对它无证明力 → 行 4
        if anchor.added_on and anchor.added_on > st.wave_ts:
            return False
        if not _lane_covers_done(st, done, COVERAGE_SLACK):
            return False
    return True


def _prune_index(data: HrSiteData, now: float) -> None:
    """非活跃条目的陈旧淘汰(观察期/终态存续的条目都保持活跃, 不在淘汰面)。

    计时起点 = entry.last_seen(_merge_seen 波合并时刷新, 退役后不再前进); 恒 0
    (issue 26-10-01-2335 修复前的存量条目)视为未知, 不淘汰。
    """
    if INDEX_RETENTION > 0:
        for tid in list(data.index):
            entry = data.index[tid]
            if not entry.active and entry.last_seen and now - entry.last_seen > INDEX_RETENTION:
                del data.index[tid]


def _lanes_summary_from(lane_states) -> str:
    parts = []
    for lane in FETCH_LANES:
        st = lane_states.get(lane)
        if st is None:
            parts.append(f"{lane}:无")
            continue
        # tag/深度/计数三部件读 model 单点(issue 26-10-29-1327), 未知状态透传判据见 model.LANE_TAGS
        tag = LANE_TAGS.get(st.status, st.status)
        parts.append(
            f"{lane}:{tag}{st.pages}页{st.rows}行" + (f"({FULL_DEPTH_TEXT})" if st.full_depth else "") +
            _lane_count_segment(st)
        )
    return " ".join(parts)

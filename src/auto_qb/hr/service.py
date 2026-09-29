"""HR 在线核实的波次引擎(v3 单波型, 计划 26-09-28-1932 §4)。

一次波 = 持锁 → 对象集现算 → A/B/C 轮流翻页(三停翻条件) → 行处理(命中定论 + 身份登记)
→ 防伪 → 放行签发/观察期推进 → 写盘 → 释放。

**单波型**(§4.1): 每波都从第 1 页开始、以覆盖全部对象为目标 —— 清单是动的, 任何「从断点
继续」「凭上波已见过而跳过」都在赌上波的覆盖假设仍然成立。每波**自证覆盖**: 覆盖结论只来自
本波抓到的页面。波的大小由覆盖对象集(未对账 ∪ 考察中, 超额 ≥3× 排除)最老的完成时间决定,
随对账与转终态单调变浅 —— 「这波 20 页、下波 1 页」由此涌现, 不靠波型配置。

**档位独立**(§3.4): 某档失败只影响该档的新证据, 不污染其他档 —— 无「整波成败」概念;
失败处置 = 档位截断(失效点之前数据有效) + 下周期自然重试, 无熔断/停用/退避(§5.2)。

三种运行口径:
- 主程序正常运行: `allow_fetch=True, persist=True`
- 主程序 `--dry-run`: `allow_fetch=False, persist=False`(**零请求也零写入**)
- `hr.once` 真机只读走查: `allow_fetch=True, persist=False`(出报告, 不写文件、不联动 qB)
"""
import logging
import re
import time
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Mapping, Optional, Set, Tuple

from ..config.models import HrCheckConfig, SiteHrCheckConfig
from . import events
from .adapters import build_adapter
from .bencode import compute_infohashes, torrent_display_name
from .fetcher import (
    HrChannelQuota,
    HrChannelStopped,
    HrChannelUnavailable,
    HrFetchError,
    HrFetcher,
    HrLoginExpired,
)
from .model import (
    CHANNEL_DISABLED,
    CHANNEL_OK,
    CHANNEL_SILENT,
    FETCH_LANES,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrLaneState,
    HrSiteData,
    HrVerified,
    lane_is_terminal,
)
from .parse import cross_page_violation, order_violations, page_javascript_marks
from .ratelimit import HrLimits, next_allowed_at, try_consume
from .resolve import HrAnchor, HrSiteView, build_site_view
from .store import HrLockBusy, HrSiteStore, hr_dir

logger = logging.getLogger(__name__)

# 刷新动作(报告的 action 字段)
ACTION_DISABLED = "disabled"
ACTION_REUSED = "reused"
ACTION_REFRESHED = "refreshed"
ACTION_PARTIAL = "partial"  # 波跑了一部分(预算截断/页面失败) —— 截断点之前的数据仍然有效
ACTION_WAITING = "waiting"  # 未到可取时刻(间隔 / 日额 / Retry-After / 时间窗 / 复用窗)
ACTION_LOCKED = "skipped-locked"
ACTION_NO_CHANNEL = "no-channel"
ACTION_ERROR = "error"

# 本轮「没跑完」的原因分类(告警分级与报告展示用)。
# ❗被**自己的频控**拦下 ≠ 故障: 那是设计如此, 而且会持续几小时;
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

#: 覆盖早停① 的对齐余量(§4.2): 本地完成时刻与站点页面完成时间的时差容差(时钟漂移/传输确认差);
#: 余量内不能确定就继续翻 —— 保守方向多花页数, 不会漏。
COVERAGE_SLACK = 86400.0  # 1D

#: 停翻② 到期段强信号(§4.2): 页尾连续 N 行「剩余考察时间」为 0(跨页延续) ⇒ 深处全是到期行,
#: 考察中的对象(remain>0)不可能藏在更深处; 藏在深处的到期行无论看到与否结论相同 —— 停翻零漏判。
ZERO_REMAIN_STREAK = 5

#: 超额线(§3.3): 本地做种时长 >= 要求时长 × 该倍数 ⇒ 放行并免除在线对账义务(不进覆盖对象集)。
#: ❗不是判定上的免死金牌: 被动命中「考察中」仍是「考察中」(网站绝对权威)。
SEED_EXEMPT_RATIO = 3.0

#: 失踪观察期(§3.4): 上波命中考察中的种子, 自身位置被覆盖且连续 N 波未重见 ⇒ 判「移出」放行;
#: 任何波重见 ⇒ 按档位定论。「没看到」不终结「考察中」。
MISSING_GRACE_WAVES = 2

#: A 档流转守恒(§5.3, 首要防伪): 上波 A 档行在本波 A/B/C 已见行中的留存率须 >= 该值,
#: 不达标 ⇒ 批量「未列出」签发冻结(防 A 段定向吞行被当「未列出」整批误放行)。
LANE_RETENTION_MIN = 0.7

#: B/C/D 终态行宽泛名称粗配阈值(§4.5 D1 拍板): **去掉技术噪声后**本地名称与行名称存在足够长的
#: 连续重合段即判疑似本地; 粗配只是下载触发器, 定论一律 infohash 精配。
#: ❗2026-09-29 收紧: K 仍是 12, 变的是「拿哪部分参与重合」(见 FUZZY_NOISE_TOKEN)。
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

#: 取数线程醒来检查的节奏(worker 用; 配置键已删除, 常量化 §6.2)
POLL_INTERVAL = 60.0

#: 连续 N 波同档失效 → ERROR 告警(疑似改版, 建议 --hr-once 走查; §5.2 告警升级)
LANE_FAIL_ALERT_STREAK = 3

#: 全档失效时的数据复用短窗(盖过下一轮 —— 与 v2 同款理由)
ALL_FAILED_REUSE_WINDOW = 120.0


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
        self.local_names: Tuple[str, ...] = tuple(a.name for a in anchors.values() if getattr(a, "name", ""))
        self.seen: Dict[int, HrEntry] = {}  # 本波已见行 tid -> 行对象
        self.hits: Dict[str, str] = {}  # infohash -> 命中档位(本波定论)
        self.retracted = 0  # 撤销的放行记录数(观测)
        self.pending_downloads: Set[int] = set()  # 待身份登记的 tid(③停翻的「无待回填」判据)
        self.dl_by_hash: Dict[str, int] = {}  # 永久层身份缓存(infohash -> tid), 行处理用
        self.order_directions: Dict[str, str] = {}  # 档位 -> 波级方向(翻转视同违反)
        self.prev_dones: Dict[str, List[float]] = {}  # 档位 -> 上一页完成时刻(跨页证据)
        self.zero_remain_streaks: Dict[str, int] = {}  # 档位 -> 跨页 remain==0 连续行数
        self.trusted_done: Dict[str, float] = {}  # infohash -> 可信完成时刻(①的判据, §4.2 分层)
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

    ❗三处签发(批量未列出 / 终态冻结 / 观察期移出)必须都经这里: 漏带快照的记录会被判定侧
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


class HrRefreshService:
    """单站点波次管道(每个站点一个 HrSiteStore; 站点之间互不阻塞)"""
    def __init__(
        self,
        *,
        data_dir: str,
        global_conf: HrCheckConfig,
        site_confs: Mapping[str, SiteHrCheckConfig],
        fetcher: HrFetcher,
        owner: str = "",
        persist: bool = True,
        allow_fetch: bool = True,
        now_fn=time.time,
        sleeper: Optional[Callable[[float], None]] = None,
        sleep_max: float = PROD_REQUEST_WAIT_MAX,
        round_wait_max: float = PROD_ROUND_WAIT_MAX,
    ) -> None:
        self.data_dir = data_dir
        self.global_conf = global_conf
        self.site_confs = dict(site_confs)
        self.fetcher = fetcher
        self.persist = persist
        self.allow_fetch = allow_fetch
        self._now = now_fn
        self._sleeper = sleeper
        self.sleep_max = sleep_max
        self.round_wait_max = round_wait_max
        self.dir = hr_dir(data_dir, global_conf.shared_dir)
        self._stores: Dict[str, HrSiteStore] = {}
        self._owner = owner
        #: 「无可用取数通道」已告警过的站点: 取数线程是分钟级轮询, 每轮都 WARNING 会把
        #: notify 的系统通知淹掉 —— 只在**状态变化**时报一次, 通道恢复后重置。
        self._no_channel_warned: set = set()
        #: 「扩展侧硬上限」已告警过的站点(超限会持续到下一个窗口, 只在状态变化时报一次)。
        self._ext_quota_warned: set = set()
        #: 「登录失效」已告警过的站点: 登录态没恢复前每轮都会命中登录页, 报一次就够。
        self._login_warned: set = set()
        #: 「页面形态异常」(排序/字段/表头/防伪)上一次告警时刻(站 -> 时刻): 持续多轮,
        #: 按 CHANNEL_SILENCE_WARN 节流。
        self._parse_warned_at: Dict[str, float] = {}

    # ---------- 基础访问 ----------

    def store(self, site: str) -> HrSiteStore:
        """该站点的文件存储(惰性建; 每站点一把锁)。锁等待常量化 0(拿不到直接等下一轮, §6.2)"""
        got = self._stores.get(site)
        if got is None:
            got = HrSiteStore(site, self.dir, lock_timeout=0.0, owner=self._owner)
            self._stores[site] = got
        return got

    def site_path(self, site: str) -> str:
        return str(self.store(site).path)

    def enabled_sites(self) -> Tuple[str, ...]:
        return tuple(sorted(s for s, c in self.site_confs.items() if c.enabled))

    def limits_for(self, site: str) -> HrLimits:
        return HrLimits.merge(self.global_conf, self.site_confs.get(site))

    # ---------- 波次入口 ----------

    def refresh_site(self, site: str, anchors: Optional[Mapping[str, HrAnchor]] = None) -> HrRefreshResult:
        """跑单个站点的一波; 任何异常都不外抛(单站点失败不拖垮其它站点)

        anchors: 本地种子锚点(infohash -> HrAnchor, 含 name)。由主循环在唤醒取数线程时
        **以不可变数据**交接, 取数线程不用读 store(线程边界不变)。
        """
        started = self._now()
        site_conf = self.site_confs.get(site)
        result = HrRefreshResult(site=site, action=ACTION_DISABLED, path=self.site_path(site))
        if site_conf is None or not site_conf.enabled:
            result.reason = "该站未接入 hr_check"
            return result
        if not self.global_conf.enabled:
            result.reason = "hr_check.enabled=false"
            return result
        adapter = build_adapter(site, site_conf)
        if adapter is None:
            result.action = ACTION_ERROR
            result.reason = f"未登记的 adapter: {site_conf.adapter}"
            return result

        try:
            with self.store(site).hold() as session:
                result.lock_ok = session.writable
                if session.read_error:
                    result.reason = session.read_error
                    result.alerted = session.read_alerted
                if session.version_mismatch:
                    # 站点文件 schema 比程序新(版本回退): 读侧「不符即拒」, 写侧更不能拿空壳数据
                    # 覆盖新版文件 —— 跳过取数与写盘, 等程序升级(用户升级后文件版本重新匹配)。
                    result.action = ACTION_ERROR
                    result.reason = (result.reason + "; " if result.reason else "") + \
                        "站点文件 schema 比程序新, 已跳过取数与写盘(请先升级程序)"
                    return result
                self._refresh_locked(site, site_conf, adapter, session, result, anchors or {})
        except HrLockBusy as e:
            result.action = ACTION_LOCKED
            result.reason = str(e)
        except Exception as e:  # 单站点失败不外抛
            result.action = ACTION_ERROR
            result.reason = f"{type(e).__name__}: {e}"
            result.alerted = True
            logger.error(f"HR 站点 {site} | 波次异常: {e}", exc_info=True)
        result.elapsed_s = max(0.0, self._now() - started)
        return result

    def refresh_all(self,
                    anchors_by_site: Optional[Mapping[str, Mapping[str, HrAnchor]]] = None) -> List[HrRefreshResult]:
        anchors_by_site = anchors_by_site or {}
        return [self.refresh_site(site, anchors_by_site.get(site)) for site in self.enabled_sites()]

    # ---------- 锁内主流程 ----------

    def _refresh_locked(
        self, site: str, site_conf: SiteHrCheckConfig, adapter, session, result, anchors: Mapping[str, HrAnchor]
    ) -> None:
        data = session.data
        limits = self.limits_for(site)
        now = self._now()

        if data.fetched_at > 0 and data.expires_at > now:
            # 复用窗内的数据直接采用(可能是别的实例刚抓的): 站点访问频率由复用窗决定
            result.action = ACTION_REUSED
            result.entries = len(data.index)
            result.verified_count = len(data.verified)
            result.lane_texts = _lanes_summary_from(data.wave.lanes)
            result.reason = f"数据仍在复用窗(至 {data.expires_at:.0f}), 直接复用"
            result.snapshot = data
            return

        if not self.allow_fetch:
            result.action = ACTION_WAITING
            result.reason = "dry-run / 只读模式: 不发起取数"
            return

        due, why = next_allowed_at(data, limits, now)
        if due > now:
            result.action = ACTION_WAITING
            result.reason = f"未到可取时刻({why}, 还差 {due - now:.0f}s)"
            return

        self._do_wave(site, site_conf, adapter, session, result, limits, anchors)

    # ---------- 波次引擎(§4) ----------

    def _do_wave(
        self, site: str, site_conf: SiteHrCheckConfig, adapter, session, result, limits: HrLimits,
        anchors: Mapping[str, HrAnchor]
    ) -> None:
        data = session.data
        budget = _Budget(
            data, limits, self._now, self._sleeper, sleep_max=self.sleep_max, round_wait_max=self.round_wait_max
        )
        # ---- 波前: 对象集现算(§4.2; 锚点漂移回炉也在这里发生) ----
        objects, observing, unmatched = self._build_objects(data, anchors, site_conf.required_seeding_time)
        wave = _WaveContext(anchors)
        wave.dl_by_hash = _dl_by_hash(data)
        wave.trusted_done = self._trusted_done_map(objects, observing)
        #: 各档本波状态(fail_streak / count_mismatch_streak 跨波延续, 其余波内重置)
        lane_states: Dict[str, HrLaneState] = {}
        for lane in FETCH_LANES:
            prev = data.wave.lanes.get(lane, HrLaneState(lane=lane))
            lane_states[lane] = HrLaneState(
                lane=lane,
                status=LANE_IDLE,
                fail_streak=prev.fail_streak,
                count_mismatch_streak=prev.count_mismatch_streak,
                wave_ts=prev.wave_ts if prev.ok else 0.0,
            )
        pages_left = max(1, int(self.global_conf.max_pages_per_wave))

        try:
            self._run_pages(
                site,
                adapter,
                data,
                session,
                result,
                budget,
                wave,
                lane_states,
                objects,
                unmatched,
                pages_left,
            )
        except HrChannelStopped as e:
            # 关停 / 热重挂时被叫停: 不告警、不计失败, 本轮让位(下轮自会重来)。
            result.action = ACTION_WAITING
            result.reason = f"本波取数被叫停(正在停止或重挂端点): {e}"
            return
        except HrChannelQuota as e:
            # 扩展侧硬上限(第二道闸)挡下: 不是「取数失败」—— 只让位 + 报一次。
            result.action = ACTION_WAITING
            result.reason = f"扩展侧硬上限挡下(后端频控可能失效), 本波让位: {e}"
            self._warn_ext_quota(site, e)
            return
        except HrChannelUnavailable as e:
            result.action = ACTION_NO_CHANNEL
            result.reason = str(e)
            self._warn_no_channel(site, e)
            return
        except HrLoginExpired as e:
            # 登录失效: 只有人去浏览器登录才会好 —— 不算取数失败。痕迹: ①一条 WARNING ②
            # wave.notes。不动任何数据语义(档位截断 + 周期自然重试, §5.2)。
            wave.notes.append(events.login_expired_note(site, e))
            self._warn_login(site, e)
            result.action = ACTION_ERROR
            result.reason = str(e)
            result.alerted = True
            # 扩展回传「登录页」时请求确实发出去了: 间隔基准必须前进, 否则登录态恢复前
            # 每轮 poll(60s)都立即重发, 白烧日额还持续刷站点(这条路径不经过页面级 mark)。
            budget.mark()
            self._finish_wave(site, site_conf, data, session, result, wave, lane_states, unmatched)
            return
        except HrFetchError as e:
            # 页面取数失败 = 该档证据在此截断(失效点之前有效), 其它档已按档位独立跑完各自的份;
            # Retry-After 是站点明确指令 → 记等待时刻(不是退避机制), 本波到此为止。
            retry_after = float(getattr(e, "retry_after", 0.0) or 0.0)
            if retry_after > 0:
                data.retry_after_until = self._now() + min(retry_after, 24 * 3600.0)
                # 指令必须落盘: hold() 每波从盘重读, 不 commit 的话下一波读到的 retry_after_until
                # 是 0, 等于无视站点指令继续打站点; mark() 让间隔基准同样前进(失败的请求也是真实请求)。
                budget.mark()
                self._persist_step(session)
                result.action = ACTION_WAITING
                result.reason = f"站点要求等待(Retry-After {retry_after:.0f}s): {e}"
                return
            wave.had_error = True
            wave.notes.append(f"页面取数失败: {e}")
            _mark_fetch_failed_lane(lane_states, wave)
            logger.warning(events.fetch_failed(site, 1, 1, str(e)))

        self._finish_wave(site, site_conf, data, session, result, wave, lane_states, unmatched)

    def _run_pages(
        self,
        site,
        adapter,
        data: HrSiteData,
        session,
        result,
        budget: _Budget,
        wave: _WaveContext,
        lane_states,
        objects,
        unmatched,
        pages_left: int,
    ) -> None:
        """A/B/C 轮流翻页(§4.1): 每档从第 1 页起, 每轮各推一页; 覆盖完成即退出轮转。"""
        active = list(FETCH_LANES)
        while active and pages_left > 0:
            progressed = False
            for lane in list(active):
                st = lane_states[lane]
                if pages_left <= 0:
                    break
                # ---- 取一页 ----
                allowed, why = budget.take()
                if not allowed:
                    wave.notes.append(f"档位 {lane} 配额/间隔受限({why})")
                    wave.budget_limited = True
                    self._truncate_lane(st, f"预算受限: {why}")
                    active.remove(lane)
                    continue
                page_no = st.pages + 1
                wave.current_lane = lane
                try:
                    html = self.fetcher.get_text(adapter.page_url(lane, page_no))
                except (HrChannelStopped, HrChannelQuota, HrChannelUnavailable, HrLoginExpired):
                    raise  # 让位 / 人工事件 / 端点级故障 → 波级处理(不计档位失败)
                except HrFetchError as e:
                    retry_after = float(getattr(e, "retry_after", 0.0) or 0.0)
                    if retry_after > 0:
                        raise  # 站点明确指令等待 → 波级处理(全档让位)
                    # 页面级失败: 该档在失效点截断(之前有效), 其它档独立继续(§3.4 档位独立)
                    wave.had_error = True
                    wave.notes.append(f"档位 {lane} 页面取数失败: {e}")
                    self._warn_parse(site, events.fetch_failed(site, 1, 1, str(e)))
                    _mark_fetch_failed_lane(lane_states, wave)
                    wave.current_lane = ""
                    active.remove(lane)
                    continue
                budget.mark()
                pages_left -= 1
                progressed = True
                result.pages_fetched += 1
                if adapter.looks_like_login(html):
                    raise HrLoginExpired(f"命中登录页(档位 {lane} 第 {page_no} 页): 登录态失效, 需人工处理")
                if adapter.looks_like_challenge(html):
                    raise HrFetchError(f"命中挑战页(档位 {lane} 第 {page_no} 页)")
                parsed = adapter.parse_page(lane, html)
                if st.wave_ts <= 0:
                    # 新鲜度闸门用本档**首页**取数时刻(该档快照的最早时刻, 最保守基准)
                    st.wave_ts = self._now()
                try:
                    if not parsed.header_found:
                        raise _LaneAbort(lane, f"第 {page_no} 页未找到 HR 表(疑似改版)")
                    # S2 零容忍(行内数据解析失败 = 页面形态变了): 该页无效, 该档证据在此截断
                    if parsed.missing_field_rate > 0:
                        raise _LaneAbort(lane, f"第 {page_no} 页必填字段缺失率 {parsed.missing_field_rate:.0%}")
                    # ---- 排序校验(顺序排列前提, §3.4): 违反 = 强制早停, 失效点之前的数据依然有效 ----
                    if self._order_violation(lane, parsed, wave, st):
                        wave.parse_problem = True
                        wave.notes.append(f"档位 {lane} 第 {page_no} 页{st.detail}(强制早停: 失效点之前数据有效, 该档等下周期)")
                        self._warn_parse(site, events.order_broken(site, f"档位 {lane} {st.detail}"))
                        active.remove(lane)
                        continue  # 该档强制早停, 同轮其它档照常推进
                    st.pages += 1  # 页面有效才计入(无效页不计覆盖进度)
                    # ---- 计数上交(计划 26-09-29-2036 §2.1): 与解析同源同一份 HTML, 零额外请求 ----
                    # 表头/字段/排序校验失败的页不上交(在上面各分支已截断); 首个非 None 胜出
                    for cl, claimed in (adapter.parse_counters(html) or {}).items():
                        if claimed is not None:
                            wave.counter_claims.setdefault(cl, claimed)
                    # ---- 行处理: 命中定论 + 身份登记(§4.3 STEP 2) ----
                    self._process_rows(lane, parsed.entries, data, wave)
                    st.rows += len(parsed.entries)
                    self._update_cutoff(st, parsed)
                    # ---- 回填下载(§4.5): A 档行无条件 / 终态行粗配疑似; 每条受同一频控 ----
                    self._run_downloads(site, adapter, data, budget, wave, result, session)
                    # ---- 增量落盘(分钟级波内 Ctrl+C 不丢已抓数据) ----
                    self._merge_seen(data, wave)
                    if self.persist:
                        session.commit(self._now())
                    # ---- 停翻条件(§4.2, 任一成立即该档停翻) ----
                    stop, full, why = self._stop_condition(lane, parsed, wave, objects, unmatched)
                    if stop:
                        st.status = LANE_OK
                        st.full_depth = full
                        st.detail = why
                        active.remove(lane)
                        continue  # 该档退出轮转, 同轮其它档照常推进
                    # ---- 翻到末页 = 全深度覆盖 ----
                    marks = page_javascript_marks(html)
                    cur_mark, max_mark = marks.get("currentpage"), marks.get("maxpage")
                    marks_says_next = cur_mark is not None and max_mark is not None and cur_mark < max_mark
                    if not parsed.has_next and not marks_says_next:
                        st.status = LANE_OK
                        st.full_depth = True
                        st.detail = "已翻到末页"
                        active.remove(lane)
                        continue  # 该档退出轮转, 同轮其它档照常推进
                except _LaneAbort as abort:
                    # 档位结构失效(表头缺失/字段缺失): 该档截断, 其它档继续(§3.4 档位独立)
                    st.detail = abort.reason
                    wave.parse_problem = True
                    wave.notes.append(f"档位 {abort.lane} {abort.reason}, 该档证据在此截断")
                    self._warn_parse(site, events.page_changed(site, ACTION_PARTIAL, f"档位 {abort.lane} {abort.reason}"))
                    if st.pages == 0:
                        st.status = LANE_FAILED
                        st.fail_streak += 1
                        self._maybe_alert_lane_fail(site, st)
                    else:
                        st.status = LANE_OK
                        st.full_depth = False
                    active.remove(lane)
            if not progressed:
                break
        # 轮转结束: 剩余未完成档按截断/未轮到收尾
        for lane in active:
            st = lane_states[lane]
            if st.status == LANE_OK:
                continue
            if pages_left <= 0 and st.pages > 0:
                self._truncate_lane(st, f"达到单波页数上限({self.global_conf.max_pages_per_wave})")
                wave.budget_limited = True
            elif st.pages == 0:
                st.status = LANE_FAILED
                st.detail = "本波未轮到取数(预算被其它档耗尽)" if pages_left <= 0 else "本波未取数"
                st.fail_streak += 1

    @staticmethod
    def _truncate_lane(st: HrLaneState, why: str) -> None:
        """预算截断: 该档证据在截断点截止(之前有效), 下波从头再翻(无断点续翻)"""
        if st.pages == 0:
            st.status = LANE_FAILED
            st.detail = why
            return
        st.status = LANE_OK
        st.full_depth = False
        st.detail = why

    def _order_violation(self, lane: str, parsed, wave: _WaveContext, st: HrLaneState) -> bool:
        """排序单调校验(§3.4): 页内逆序 / 跨页乱序 / 方向翻转。基于原始行序。"""
        dones = [e.done_epoch for e in parsed.entries if e.done_epoch is not None]
        check = order_violations(dones)
        page_bad = ""
        direction = wave.order_directions.get(lane, "")
        if check.ok:
            if not direction:
                wave.order_directions[lane] = check.direction
                direction = check.direction
            elif check.direction != direction:
                page_bad = f"方向翻转(本页 {check.direction}, 波级 {direction})"
        if not page_bad and check.inversions > 0:
            page_bad = f"页内逆序 {check.inversions} 处"
        if not page_bad and cross_page_violation(wave.prev_dones.get(lane), dones, direction):
            page_bad = "跨页乱序"
        if page_bad:
            st.detail = f"排序违反({page_bad})"
            return True
        wave.prev_dones[lane] = dones
        return False

    def _stop_condition(self, lane: str, parsed, wave: _WaveContext, objects, unmatched) -> Tuple[bool, bool, str]:
        """三停翻条件(§4.2, 每档独立, 任一成立即停)。返回 (停翻, 是否全深度, 原因)。"""
        # ---- ② 到期段强信号(纯页面信号, 不依赖本地完成时间): 页尾连续 remain==0 达阈值 ----
        tail_zero = 0
        for e in reversed(parsed.entries):
            if e.remain_seconds == 0:
                tail_zero += 1
            else:
                break
        streak = wave.zero_remain_streaks.get(lane, 0)
        if parsed.entries and tail_zero == len(parsed.entries):
            streak += tail_zero  # 整页全 0: 延续上一页尾部
        elif tail_zero:
            streak = tail_zero
        else:
            streak = 0
        wave.zero_remain_streaks[lane] = streak
        if streak >= ZERO_REMAIN_STREAK:
            return True, True, f"到期段强信号(连续 {streak} 行剩余考察时间为 0, 深处全是到期行)"

        # ---- ① 完成时间覆盖(本地推定信号): 最深行早于未定论对象里最早(最老)的可信完成时间 ----
        oldest = 0.0
        for h, anchor in objects.items():
            if h in wave.hits:
                continue  # 已定论的对象不再驱动覆盖深度
            done = wave.trusted_done.get(h) or (float(anchor.completion_on) if anchor.completion_on > 0 else 0.0)
            if done > 0 and (oldest <= 0 or done < oldest):
                oldest = done
        deepest = self._deepest_seen_done(parsed)
        if oldest > 0 and deepest > 0 and deepest < oldest - COVERAGE_SLACK:
            return True, False, (f"完成时间覆盖(本档最深行早于最老对象减对齐余量 1D, 更深的页只会有更老的行)")

        # ---- ③ 本地全集覆盖(本地确认信号): 未对账对象已全部与已见行 infohash 对上且无待回填 ----
        if unmatched and not wave.pending_downloads:
            if all(h in wave.hits for h in unmatched):
                return True, False, "本地全集覆盖(未对账种子已全部与已见行对上, 且无待回填)"
        return False, False, ""

    @staticmethod
    def _trusted_done_map(objects, observing) -> Dict[str, float]:
        """对象的可信完成时刻表(§4.2 可信度分层): 绑定行记住了站点侧 done_iso 的优先
        (站点侧时刻, 无时钟漂移); 本机下载完成(completion_on > 0)的次之; 纯辅种不可信不入表。"""
        out: Dict[str, float] = {}
        for h, entry in observing.items():
            done = entry.done_epoch
            if done is not None:
                out[h] = done
        return out

    @staticmethod
    def _deepest_seen_done(parsed) -> float:
        """本页已见最深(最老)行的完成时刻(行按完成时间有序, 取可解析值的最小者)"""
        dones = [e.done_epoch for e in parsed.entries if e.done_epoch is not None]
        return min(dones) if dones else 0.0

    @staticmethod
    def _update_cutoff(st: HrLaneState, parsed) -> None:
        """滚动记录该档已见最深行的完成时刻(缺席证明的位置边界; 截断式数据有效性, §3.4)"""
        page_deepest = HrRefreshService._deepest_seen_done(parsed)
        if page_deepest > 0 and (st.cutoff_done <= 0 or page_deepest < st.cutoff_done):
            st.cutoff_done = page_deepest

    # ---------- 行处理与身份登记(§4.3 STEP 2 / §4.5) ----------

    def _process_rows(self, lane: str, entries: List[HrEntry], data: HrSiteData, wave: _WaveContext) -> None:
        """行合并进波上下文: 继承已知身份; 命中即定论(撤销放行); 需要身份的行进下载队列。

        下载规则(§4.5, 21:44 定稿): A 档(考察中)行**无条件**全部下载(硬规则 —— A 命中是唯一
        管束正证据, 行身份完备性不依赖名称推断); B/C/D 终态行仅当宽泛名称粗配疑似本地才下;
        本地没有的种子(粗配也不像)不下载。
        """
        for row in entries:
            row.lane = lane
            old = data.index.get(row.tid)
            if old is not None:
                row.infohash_v1 = old.infohash_v1 or row.infohash_v1
                row.infohash_v2 = old.infohash_v2 or row.infohash_v2
                row.first_seen = old.first_seen
                row.missing_streak = 0  # 重见: 观察期清零(按本波档位定论)
            else:
                got = data.downloaded.get(row.tid)
                if got is not None:
                    row.infohash_v1 = got.infohash_v1 or row.infohash_v1
                    row.infohash_v2 = got.infohash_v2 or row.infohash_v2
            row.active = True
            wave.seen[row.tid] = row
            h = row.infohash_v1 or row.infohash_v2
            if h:
                if h in wave.local_hashes:
                    self._record_hit(data, wave, h, row)
                elif wave.dl_by_hash.get(h, row.tid) != row.tid:
                    # 同一 infohash 挂在别的 tid 名下(站点换 tid 重列): 新行接管身份, 命中照判
                    self._record_hit(data, wave, h, row)
            elif lane == LANE_SCOPE or self._row_looks_local(row, wave):
                wave.pending_downloads.add(row.tid)

    def _row_looks_local(self, row: HrEntry, wave: _WaveContext) -> bool:
        """终态行宽泛名称粗配(D1): 仅作**下载触发器**, 定论一律 infohash 精配(§4.5)。"""
        return any(fuzzy_name_match(name, row.name) for name in wave.local_names)

    def _record_hit(self, data: HrSiteData, wave: _WaveContext, h: str, row: HrEntry) -> None:
        """infohash 精配命中: 定论按档位(§3 矩阵); 命中即撤销既有放行(它已回清单/重考)。"""
        wave.hits[h] = row.lane
        wave.pending_downloads.discard(row.tid)
        if h in data.verified:
            del data.verified[h]
            wave.retracted += 1
        # 同一 infohash 若还挂在别的活跃条目名下(站点换 tid 重列): 新行接管, 旧条目退役
        for tid, entry in data.index.items():
            if tid != row.tid and entry.active and h in (entry.infohash_v1, entry.infohash_v2):
                entry.active = False

    def _run_downloads(
        self,
        site: str,
        adapter,
        data: HrSiteData,
        budget: _Budget,
        wave: _WaveContext,
        result: HrRefreshResult,
        session,
    ) -> None:
        """身份登记下载(§4.5): .torrent 的唯一目的是给清单行登记身份 —— 同 tid 永不重下,
        状态追踪靠 tid 读页面。A 档行无条件下载(硬规则); 终态行粗配疑似才下。
        下载量大时按日额跨波分摊, 未下完的下波续排(永久层去重)。"""
        for tid in sorted(wave.pending_downloads):
            entry = wave.seen.get(tid)
            if entry is None or (entry.infohash_v1 or entry.infohash_v2):
                wave.pending_downloads.discard(tid)
                continue
            got = data.downloaded.get(tid)
            if got is not None and (got.infohash_v1 or got.infohash_v2):
                entry.infohash_v1, entry.infohash_v2 = got.infohash_v1, got.infohash_v2
                wave.pending_downloads.discard(tid)
                h = got.infohash_v1 if got.infohash_v1 in wave.local_hashes else (
                    got.infohash_v2 if got.infohash_v2 in wave.local_hashes else ""
                )
                if h:
                    self._record_hit(data, wave, h, entry)
                continue
            fail = data.fails.get(tid)
            if fail is not None and fail.count >= MAX_DOWNLOAD_RETRIES and \
                    self._now() - fail.last_ts < DL_RETRY_COOLDOWN:
                continue
            allowed, _why = budget.take()
            if not allowed:
                return  # 预算受限: 未下完的下波续排(永久层去重)
            try:
                # dl_id: 行内链接提取的下载用种子 id(CarPT 等站点 H&R ID 与种子 id 两个空间);
                # None = 同空间站点, 回落 tid
                blob = self.fetcher.get_bytes(adapter.download_url(entry.dl_id or tid))
                budget.mark()
            except (HrChannelStopped, HrChannelQuota, HrChannelUnavailable, HrLoginExpired):
                # 让位 / 人工事件 / 端点级故障, 不是「这个种子取失败」: 计数会把「程序要关了 /
                # 扩展限流 / 该去登录 / 端点没在监听」伪装成「种子坏了」。原样上抛, 由上层折成备注。
                raise
            except HrFetchError as e:
                retry_after = float(getattr(e, "retry_after", 0.0) or 0.0)
                if retry_after > 0:
                    # 站点明确指令等待: 与页面同口径上抛波级落 retry_after_until 让位 ——
                    # 计成「种子失败」会把站点限速伪装成种子坏了, 且指令不会落盘。
                    raise
                self._note_dl_fail(data, tid)
                result.torrents_failed += 1
                self._persist_step(session)
                logger.warning(f"HR 站点 {site} | tid={tid} 取 .torrent 失败({data.fails[tid].count} 次): {e}")
                continue
            try:
                v1, v2, info = compute_infohashes(blob)
            except ValueError as e:
                self._note_dl_fail(data, tid)
                result.torrents_failed += 1
                self._persist_step(session)
                logger.warning(f"HR 站点 {site} | tid={tid} 返回内容不是合法 .torrent: {e}")
                continue
            entry.infohash_v1, entry.infohash_v2 = v1, v2
            # ts 是这一份 .torrent 自己的取回时刻(整批共用开始时刻会让取证误读)
            data.downloaded[tid] = HrDownloaded(
                tid=tid,
                ts=self._now(),
                name=torrent_display_name(info) or entry.name,
                infohash_v1=v1,
                infohash_v2=v2,
            )
            data.fails.pop(tid, None)
            wave.dl_by_hash.setdefault(v1, tid)
            wave.dl_by_hash.setdefault(v2, tid)
            wave.pending_downloads.discard(tid)
            result.torrents_fetched += 1
            h = v1 if v1 in wave.local_hashes else (v2 if v2 in wave.local_hashes else "")
            if h:
                self._record_hit(data, wave, h, entry)
            self._persist_step(session)

    @staticmethod
    def _note_dl_fail(data: HrSiteData, tid: int) -> None:
        fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
        fail.count += 1
        fail.last_ts = time.time()

    def _persist_step(self, session) -> None:
        """增量落盘的统一口(只在正式口径下写; 走查 persist=False 不落盘)。"""
        if session is not None and self.persist:
            session.commit(self._now())

    # ---------- 波后收尾: 合并 / 观察期 / 防伪 / 放行 ----------

    def _finish_wave(
        self,
        site: str,
        site_conf: SiteHrCheckConfig,
        data: HrSiteData,
        session,
        result: HrRefreshResult,
        wave: _WaveContext,
        lane_states,
        unmatched,
    ) -> None:
        now = self._now()
        self._merge_seen(data, wave)
        # ---- 观察期推进(§3.4): 没看到不终结「考察中」; 出口要自身位置被覆盖 ----
        exits = self._advance_observation(data, lane_states, wave)
        # ---- 证据防伪(§5.3): 流转守恒 + 零行戳。骤降保护已按 26-09-29 裁决移除: A 只流向
        #      B/C/D, 守恒直接盯 A 档正证据, 总量变化不构成漏 HR 面; 而基线是高水位不回落,
        #      站点合法清账后会把批量签发永久冻死(误触面)。 ----
        total_rows = sum(st.rows for st in lane_states.values())
        retention_ratio, retention_ok = self._retention_check(data, lane_states, wave)
        zero_rows = total_rows == 0
        if total_rows > 0:
            data.empty_confirmed_at = 0.0  # 清单再现任何非零行 → 确认戳自动失效(§5.3)
        # ---- 计数对平记账(计划 26-09-29-2036 §2.2/§2.4): 声明落档 + mismatch 定界 ----
        # mismatch 只在「本波承认了全深度」的档上成立; 截断/①③停翻波 rows<claim 是预期差值
        # (还没翻完), 只记量化差值不告警不冻结。无计数(claim=None)一律降级现状。
        depth_broken = False
        for st in lane_states.values():
            claim = wave.counter_claims.get(st.lane)
            st.count_claim = claim
            st.count_match = None if claim is None else (st.rows == claim)
            if st.ok and st.full_depth and st.count_match is False:
                st.count_mismatch_streak += 1
                depth_broken = True
                if st.rows == 0 and claim > 0:
                    # 计数>0 ∧ 行数=0: 整表被吃光 / 首页即被截的显式信号 —— 硬告警不经节流
                    logger.error(events.page_changed(site, ACTION_PARTIAL, f"档位 {st.lane} 声明 {claim} 行但实抓 0 行"))
                else:
                    wave.notes.append(f"档位 {st.lane} 计数对不平: 实抓 {st.rows}/声明 {claim}, 批量「未列出」签发冻结")
                    self._warn_parse(
                        site, events.counter_mismatch(site, st.lane, st.rows, claim, st.count_mismatch_streak)
                    )
                    if st.count_mismatch_streak >= LANE_FAIL_ALERT_STREAK:
                        logger.error(events.counter_mismatch(site, st.lane, st.rows, claim, st.count_mismatch_streak))
            else:
                st.count_mismatch_streak = 0  # 对平 / 无计数 / 截断波 / 失效档: 不构成对不平证据
            if claim is not None and not st.full_depth and st.rows < claim:
                wave.notes.append(f"档位 {st.lane} 未翻完: 实抓 {st.rows}/声明 {claim}, 差 {claim - st.rows} 行(预期内)")
        confirmed_empty = zero_rows and (
            data.empty_confirmed_at > 0 or all(st.count_claim == 0
                                               for st in lane_states.values())  # 站点自证空集(§2.5): None 参与即为假
        )
        # ---- 唯一行为变更点: 批量「未列出」签发闸门多一个 AND 条件(报告 §5.2 收束语落地) ----
        releases_enabled = (
            all(st.ok for st in lane_states.values()) and
            all(st.pages > 0 or st.full_depth for st in lane_states.values()) and (not zero_rows or confirmed_empty) and
            not depth_broken
        )
        # ---- 放行签发(§5.3): 批量「未列出」只走防伪全通的波; 观察期出口与批量签发解耦 ----
        signed = 0
        if releases_enabled and retention_ok:
            signed = self._sign_releases(site, data, lane_states, wave, unmatched, now)
        # ---- 终态冻结(§4.4): 消失且位置被证明的终态条目退役并落放行记录 ----
        frozen = self._freeze_terminal(data, lane_states, wave, now)
        # ---- 陈旧淘汰(非活跃条目超过保留期删除; 永久层不触碰) ----
        _prune_index(data, now)
        # ---- 元数据 ----
        healthy = any(st.ok and (st.rows > 0 or st.full_depth) for st in lane_states.values())
        data.wave = replace(
            data.wave,
            wave_ts=now,
            healthy_ts=now if healthy else data.wave.healthy_ts,
            lanes=lane_states,
            releases_enabled=releases_enabled,
            zero_rows=zero_rows,
            retention_ratio=retention_ratio,
            retention_ok=retention_ok,
            prev_a_tids={
                tid: data.infohash_of(tid)
                for tid, row in wave.seen.items() if row.lane == LANE_SCOPE
            },
            notes="; ".join(wave.notes),
        )
        data.fetched_at = now
        any_ok = any(st.ok for st in lane_states.values())
        # 复用窗: 有效波按周期挡住其它实例的重复取数; 全档失败无新数据可复用 → 不设窗
        # (下一个 poll 节拍即可重试 —— 失败处置 = 档位截断 + 周期自然重试, §5.2)
        data.expires_at = now + site_conf.refresh_interval if any_ok else 0.0
        result.entries = len(data.index)
        result.verified_count = len(data.verified)
        result.releases_signed = signed + exits
        result.lane_texts = _lanes_summary_from(lane_states)
        notes = list(wave.notes)
        if zero_rows and not confirmed_empty:
            notes.append("结构完好但清单为 0: 不签发放行(需 --hr-confirm-empty 人工对账)")
            if not wave.parse_problem and not wave.had_error:
                self._warn_parse(site, events.zero_listing(site))
        if not retention_ok:
            notes.append(f"A 档流转守恒不达标(留存率 {retention_ratio:.0%}), 批量未列出签发冻结")
            self._warn_parse(site, events.retention_violation(site, retention_ratio))
        if frozen:
            notes.append(f"终态冻结 {frozen} 条")
        result.reason_kind = REASON_BUDGET if (wave.budget_limited and not wave.parse_problem) else (
            REASON_PARSE if (wave.parse_problem or depth_broken) else REASON_NONE
        )
        all_failed = all(not st.ok for st in lane_states.values())
        result.action = ACTION_ERROR if all_failed else (
            ACTION_PARTIAL if (wave.parse_problem or wave.had_error) else ACTION_REFRESHED
        )
        # 本波产生处已打过 WARNING/ERROR(页面失败/改版/防伪/零行/计数对不平) ⇒ worker 状态层只记 INFO 不重复
        result.alerted = bool(
            wave.had_error or wave.parse_problem or not retention_ok or depth_broken or
            (zero_rows and not confirmed_empty)
        )
        result.reason = "; ".join(notes)
        result.snapshot = data
        if self.persist:
            status = session.commit(now)
            result.persisted = status == "written"
            if status == "readonly":
                result.reason = (result.reason + "; " if result.reason else "") + "锁自检失败, 未写盘(只读退化)"
        else:
            result.reason = (result.reason + "; " if result.reason else "") + "只读模式, 未写盘"
        self._no_channel_warned.discard(site)
        self._ext_quota_warned.discard(site)
        self._login_warned.discard(site)

    @staticmethod
    def _merge_seen(data: HrSiteData, wave: _WaveContext) -> None:
        """本波已见行合并进索引: 更新字段, 保留 first_seen 与已回填的 infohash。"""
        for tid, row in wave.seen.items():
            old = data.index.get(tid)
            row.first_seen = (old.first_seen if old is not None else 0.0) or row.first_seen or time.time()
            data.index[tid] = row

    @staticmethod
    def _prune_index(data: HrSiteData, now: float) -> None:
        """非活跃条目的陈旧淘汰(观察期/终态存续的条目都保持活跃, 不在淘汰面)。"""
        if INDEX_RETENTION > 0:
            for tid in list(data.index):
                entry = data.index[tid]
                if not entry.active and entry.last_seen and now - entry.last_seen > INDEX_RETENTION:
                    del data.index[tid]

    @staticmethod
    def _freeze_terminal(data: HrSiteData, lane_states, wave: _WaveContext, now: float) -> int:
        """终态冻结(§4.4): 终态档条目本波未再见、且其位置被本波覆盖证明 —— 退役并落放行记录
        (终态不可逆: 放行永续有效; 之后条目被站点彻底清掉也不影响判定)。"""
        frozen = 0
        for tid, entry in data.index.items():
            if tid in wave.seen or not entry.active or not lane_is_terminal(entry.lane):
                continue
            st = lane_states.get(entry.lane)
            if st is None or not st.ok:
                continue
            done = entry.done_epoch
            if not st.full_depth and (done is None or done < st.cutoff_done):
                continue  # 位置未被覆盖: 不能证明它离开了, 维持原状(命中照常, 保守无害)
            entry.active = False
            for h in (entry.infohash_v1, entry.infohash_v2):
                if h and h not in data.verified:
                    source = SOURCE_SATISFIED if entry.lane == LANE_SATISFIED else (
                        SOURCE_EXEMPT if entry.lane == LANE_EXEMPT else SOURCE_NOT_LISTED
                    )
                    data.verified[h] = _release_record(
                        infohash=h,
                        tid=tid,
                        verified_ts=now,
                        source=source,
                        anchor=wave.anchors.get(h),
                    )
                    frozen += 1
        return frozen

    @staticmethod
    def _advance_observation(data: HrSiteData, lane_states, wave: _WaveContext) -> int:
        """失踪观察期状态机(§3.4): 上波命中考察中、本波未重见的种子:
        - 本波重见(已在行处理清零 streak) → 按档位定论;
        - 未重见且自身位置被本波覆盖(每档都证明) → streak + 1;
          连续 MISSING_GRACE_WAVES 波 ⇒ 判「移出」放行(条目退役 + 放行记录);
        - 位置未被覆盖 → streak 冻结(维持管束)。与批量防伪解耦(22:38 定稿)。"""
        exits = 0
        now = time.time()
        for tid, entry in data.index.items():
            if entry.lane != LANE_SCOPE or not entry.active or tid in wave.seen:
                continue
            h = entry.infohash_v1 or entry.infohash_v2
            if not _position_covered(entry, lane_states):
                continue  # 位置未被覆盖: streak 冻结(维持管束)
            entry.missing_streak += 1
            if entry.missing_streak >= MISSING_GRACE_WAVES:
                entry.active = False
                entry.missing_streak = 0
                if h and h not in data.verified:
                    data.verified[h] = _release_record(
                        infohash=h,
                        tid=tid,
                        verified_ts=now,
                        source=SOURCE_NOT_LISTED,
                        anchor=wave.anchors.get(h),
                    )
                exits += 1
                logger.info(f"HR | tid={tid} 失踪观察期出口: 连续 {MISSING_GRACE_WAVES} 波未重见且位置被覆盖, "
                            "判移出放行")
        return exits

    @staticmethod
    def _retention_check(data: HrSiteData, lane_states, wave: _WaveContext) -> Tuple[float, bool]:
        """A 档流转守恒(§5.3): 上波 A 档行在本波 A/B/C 已见行中的留存率。
        上波 A 档 tid 集非空时留存率须 >= LANE_RETENTION_MIN, 不达标 ⇒ 批量「未列出」签发冻结
        (失踪者个体走观察期状态机, 与本校验解耦)。无上波 A 行返回 (-1.0, True)。"""
        prev = data.wave.prev_a_tids
        if not prev:
            return -1.0, True
        seen_tids = set(wave.seen.keys())
        retained = sum(1 for tid in prev if tid in seen_tids)
        ratio = retained / len(prev)
        return ratio, ratio >= LANE_RETENTION_MIN

    @staticmethod
    def _sign_releases(site: str, data: HrSiteData, lane_states, wave: _WaveContext, unmatched, now: float) -> int:
        """批量「未列出」放行签发(§3.2 行 3 / §4.2 停翻后): 覆盖范围内未命中的未对账对象。
        每个对象要过: 各档缺席证明(全深度 或 可信完成时间位置被覆盖) + 新鲜度闸门(added_on
        不晚于该档本波取数时刻)。放行永续有效(终态不可逆); 锚点快照供本机重下作废用。"""
        signed = 0
        for h, anchor in unmatched.items():
            if h in wave.hits:
                continue
            if not _absence_proven_all(lane_states, wave, anchor):
                continue
            data.verified[h] = _release_record(
                infohash=h,
                tid=wave.dl_by_hash.get(h, 0),
                verified_ts=now,
                source=SOURCE_NOT_LISTED,
                anchor=anchor,
            )
            signed += 1
        if signed:
            logger.info(f"HR 站点 {site} | 本波签发「未列出」放行 {signed} 条(覆盖范围内未命中)")
        return signed

    def _build_objects(
        self, data: HrSiteData, anchors: Mapping[str, HrAnchor], required_seeding_time: float
    ) -> Tuple[Dict[str, HrAnchor], Dict[str, HrEntry], Dict[str, HrAnchor]]:
        """覆盖对象集现算(§4.2): 未对账 ∪ 考察中; 终态/已放行/超额(≥3×)不出对象集。

        返回 (objects 全部对象, observing 考察中对象(观察期机器管), unmatched 未对账对象)。
        锚点漂移(本机重下)在这里把旧放行作废 —— 「回炉」(§3.2 行 3 机制保留)。
        """
        objects: Dict[str, HrAnchor] = {}
        observing: Dict[str, HrEntry] = {}
        unmatched: Dict[str, HrAnchor] = {}
        bound_entries: Dict[str, HrEntry] = {}
        for entry in data.index.values():
            if not entry.active:
                continue
            for h in (entry.infohash_v1, entry.infohash_v2):
                if h and h not in bound_entries:
                    bound_entries[h] = entry
        for h, anchor in anchors.items():
            if not h:
                continue
            ver = data.verified.get(h)
            if ver is not None and anchor.drift_reason(ver):
                # 本机重下: 放行作废(机制保留), 种子回对象集 —— 覆盖对账会重新给它定论
                del data.verified[h]
                ver = None
            entry = bound_entries.get(h)
            if entry is not None and lane_is_terminal(entry.lane):
                continue  # 终态冻结出对象集(终态不可逆, 不再为它翻页下载)
            if ver is not None:
                continue  # 放行记录在案(未列出/免罪): 被动命中由行处理撤销
            if required_seeding_time > 0 and anchor.seeding_time >= SEED_EXEMPT_RATIO * required_seeding_time:
                continue  # 超额线(§3.3): 免除在线对账义务; 被动命中考察中仍转管束(网站绝对权威)
            objects[h] = anchor
            if entry is not None and entry.lane == LANE_SCOPE:
                observing[h] = entry
            else:
                unmatched[h] = anchor
        return objects, observing, unmatched

    # ---------- 视图 ----------
    def build_view_for(self, site: str, data: HrSiteData) -> HrSiteView:
        """用给定(内存)数据构造视图 —— 供走查报告预览本轮结果(生产读已落盘视图)"""
        conf = self.site_confs[site]
        return build_site_view(
            site,
            conf.listing,
            data,
            channel_state=self.channel_state(site, data),
            generated_at=self._now(),
        )

    def build_views(self) -> Dict[str, HrSiteView]:
        """构建各站点的只读视图(不加锁读: 写入是原子替换, 读到的必然是完整的一份)"""
        out: Dict[str, HrSiteView] = {}
        for site, site_conf in self.site_confs.items():
            if not site_conf.enabled:
                continue
            data, _err = self.store(site).read_unlocked()
            out[site] = self.build_view_for(site, data)
        return out

    def channel_state(self, site: str, data: Optional[HrSiteData] = None) -> str:
        """通道状态: disabled(未启用 channel) / silent(长期没有健康波) / ok"""
        if not self.global_conf.channel.enabled:
            return CHANNEL_DISABLED
        if data is None:
            data, _err = self.store(site).read_unlocked()
        if data.wave.healthy_ts <= 0:
            return CHANNEL_SILENT
        if self._now() - data.wave.healthy_ts > CHANNEL_SILENCE_WARN:
            return CHANNEL_SILENT
        return CHANNEL_OK

    # ---------- 告警(升级但行为不变, §5.2) ----------

    def _warn_no_channel(self, site: str, err: Exception) -> None:
        """无通道告警: **每个站点只报一次**(直到通道恢复)"""
        if site in self._no_channel_warned:
            logger.debug(f"HR 站点 {site} | 无可用取数通道(已告警过, 不重复): {err}")
            return
        self._no_channel_warned.add(site)
        logger.warning(f"HR 站点 {site} | 无可用取数通道, 本轮不做在线核实(保守回落本地兜底): {err}")

    def _warn_login(self, site: str, err: Exception) -> None:
        """登录失效告警: **每个站点只报一次**(直到登录恢复); 文案单点在 events.login_expired"""
        if site in self._login_warned:
            logger.info(f"HR 站点 {site} | 登录态仍未恢复(已告警过, 本轮不做在线核实): {err}")
            return
        self._login_warned.add(site)
        logger.error(events.login_expired(site, err))

    def _warn_parse(self, site: str, detail: str) -> None:
        """页面形态异常告警(排序/字段/表头/防伪): WARNING 按 CHANNEL_SILENCE_WARN 节流"""
        warn_gap = max(60.0, float(CHANNEL_SILENCE_WARN))
        now = self._now()
        if now - self._parse_warned_at.get(site, 0.0) < warn_gap:
            logger.info(f"HR 站点 {site} | 页面形态异常仍存在(节流期内不重复告警): {detail}")
            return
        self._parse_warned_at[site] = now
        logger.warning(detail)

    def _maybe_alert_lane_fail(self, site: str, st: HrLaneState) -> None:
        """连续多波同档失效 → ERROR 告警(§5.2 告警升级): 只提示人, 不改变取数与判定行为"""
        if st.fail_streak >= LANE_FAIL_ALERT_STREAK:
            logger.error(events.lane_persistent_failure(site, st.lane, st.fail_streak, st.detail))

    def _warn_ext_quota(self, site: str, err: Exception) -> None:
        """扩展侧硬上限告警: 同样**只报一次**(超限会持续到下一个窗口)"""
        if site in self._ext_quota_warned:
            logger.info(f"HR 站点 {site} | 扩展侧硬上限仍生效(已告警过, 本波让位): {err}")
            return
        self._ext_quota_warned.add(site)
        logger.warning(
            f"HR 站点 {site} | 扩展侧硬上限挡下取数(第二道闸): 多半是后端频控失效(检查 hr_check 的间隔/日额配置"
            "与日志), 也可能是扩展上限本就低于后端配额(属正常优先)"
        )


class _LaneAbort(Exception):
    """档位结构失效的轮内跳出(表头缺失 / 字段缺失): 该档截断, 其它档继续(§3.4 档位独立)"""
    def __init__(self, lane: str, reason: str) -> None:
        super().__init__(reason)
        self.lane = lane
        self.reason = reason


def _mark_fetch_failed_lane(lane_states, wave: "_WaveContext") -> None:
    """页面级取数失败: 失败页无效, 该档在失效点截断(之前有效); 首页即失败 = 该档失效"""
    st = lane_states.get(wave.current_lane)
    if st is None or st.status == LANE_OK:
        return
    if st.pages == 0:
        st.status = LANE_FAILED
        st.detail = "页面取数失败"
        st.fail_streak += 1
    else:
        st.status = LANE_OK
        st.full_depth = False
        st.detail = "页面取数失败(失效点之前数据有效)"


# ---------------- 模块级纯函数(便于单测直调) ----------------


def _dl_by_hash(data: HrSiteData) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in data.downloaded.values():
        for h in (d.infohash_v1, d.infohash_v2):
            if h and h not in out:
                out[h] = d.tid
    return out


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
        if not st.full_depth and done < st.cutoff_done:
            return False
    return True


def _absence_proven_all(lane_states, wave: _WaveContext, anchor: HrAnchor) -> bool:
    """该种子在所有取数档位的缺席证明(§3.2 行 3: 完成时间位置被覆盖且未命中)。

    全深度档(末页 / ②到期段停翻)对**任意位置**的缺席证明成立 —— 深处的到期行无论看到与否
    结论相同(命中 → 终态放行, 没看到 → 未列出放行), 不依赖完成时间可信度; 位置有界档
    (①/③停翻或截断)则需要可信完成时间推定位置(本机下载完成)—— 纯辅种只能由全深度收尾
    (方向安全, 只费页数, §4.2 可信度分层)。"""
    done = float(anchor.completion_on) if anchor.completion_on and anchor.completion_on > 0 else 0.0
    for lane in FETCH_LANES:
        st = lane_states.get(lane)
        if st is None or not st.ok or st.wave_ts <= 0:
            return False
        # 新鲜度闸门: 种子 added_on 晚于该档本波取数 ⇒ 该档快照对它无证明力 → 行 4
        if anchor.added_on and anchor.added_on > st.wave_ts:
            return False
        if st.full_depth:
            continue  # 全深度证明: 位置无关
        if done <= 0:
            return False
        if done - COVERAGE_SLACK < st.cutoff_done:
            return False
    return True


def _prune_index(data: HrSiteData, now: float) -> None:
    """非活跃条目的陈旧淘汰(观察期/终态存续的条目都保持活跃, 不在淘汰面)。"""
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
        tag = {"ok": "✓", LANE_FAILED: "✗", LANE_IDLE: "-"}.get(st.status, st.status)
        counter = ""
        if st.count_claim is not None:  # 计数对平展示(计划 26-09-29-2036 §2.6)
            counter = f"/声明{st.count_claim}" + (" 对不平" if st.count_match is False else "")
        parts.append(f"{lane}:{tag}{st.pages}页{st.rows}行" + ("(全深度)" if st.full_depth else "") + counter)
    return " ".join(parts)


__all__ = [
    "ACTION_DISABLED",
    "ACTION_ERROR",
    "ACTION_LOCKED",
    "ACTION_NO_CHANNEL",
    "ACTION_PARTIAL",
    "ACTION_REFRESHED",
    "ACTION_REUSED",
    "ACTION_WAITING",
    "COVERAGE_SLACK",
    "FUZZY_NAME_K",
    "MISSING_GRACE_WAVES",
    "POLL_INTERVAL",
    "REASON_BUDGET",
    "REASON_NONE",
    "REASON_PARSE",
    "SEED_EXEMPT_RATIO",
    "ZERO_REMAIN_STREAK",
    "fuzzy_name_match",
    "HrRefreshResult",
    "HrRefreshService",
]

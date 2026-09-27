"""HR 在线核实的刷新管道(计划 §5/§7): 一次刷新 = 持锁 → 读 → 判有效期 → 必要时抓 → 写 → 释放。

**全程在站点锁内**(连分钟级的抓取也在锁内) ⇒ 即使代码有 bug 也不可能两个实例同时读/写/抓同一
站点; 拿不到锁的实例直接等下一轮(不排队、不重试轰炸)。存量数据仍在有效期内的实例, 把它
当作本次抓取的数据直接采用(并按窗口键幂等记一次配额) ⇒ 站点访问频率由**数据有效期**决定,
与实例数、谁抓的无关。

本模块**不碰 state_file / 任务队列 / store**(线程三分职责的硬约束) —— 它只读写 hr 文件与
返回结果对象; 取数一律经 `HrFetcher`(后端零 cookie、零直连站点)。

三种运行口径:
- 主程序正常运行: `allow_fetch=True, persist=True`
- 主程序 `--dry-run`: `allow_fetch=False, persist=False`(**零请求也零写入**: 清单恒空)
- `hr.once` 真机只读走查: `allow_fetch=True, persist=False`(出报告, 不写文件、不联动 qB)
"""
import logging
import time
from statistics import median
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Mapping, Optional, Tuple

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
    LANE_EXEMPT,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrRefreshMeta,
    HrSiteData,
    HrSuspension,
    HrVerified,
)
from .parse import cross_page_violation, order_violations, page_javascript_marks
from .ratelimit import (
    HrLimits,
    fuse_active,
    next_allowed_at,
    record_failure,
    record_success,
    split_next_allowed_at,
    split_try_consume,
    try_consume,
)
from .resolve import HrAnchor, HrSiteView, build_site_view
from .store import HrLockBusy, HrSiteStore, hr_dir

logger = logging.getLogger(__name__)

# 刷新动作(报告的 action 字段)
ACTION_DISABLED = "disabled"
ACTION_REUSED = "reused"
ACTION_REFRESHED = "refreshed"
ACTION_PARTIAL = "partial"  # 抓到数据但覆盖证明不成立(不完备)
ACTION_WAITING = "waiting"  # 未到可取时刻(间隔 / 配额 / 熔断 / 时间窗)
ACTION_LOCKED = "skipped-locked"
ACTION_NO_CHANNEL = "no-channel"
ACTION_ERROR = "error"
ACTION_SUSPENDED = "suspended"  # 站点已停用(计划 26-09-27-1815 §2 2.3): 零请求, 人工恢复

# 本轮「没跑完」的原因分类(告警分级与报告展示用)。
# ❗被**自己的频控**拦下 ≠ 故障: 那是设计如此(保守不产生放行), 而且会持续几小时;
#   真值得盯着的是页面/解析问题(可能是改版)。两者混成同一级会让用户在弹窗轰炸中开始忽略告警。
REASON_NONE = ""  # 没有「没跑完」这回事(完整刷新 / 复用 / 不适用)
REASON_BUDGET = "budget"  # 被自己的间隔/配额/时间窗拦下(可预期, 下轮继续)
REASON_PARSE = "parse"  # 页面/字段/翻页问题(可能是改版) —— 值得告警

# 生产路径在锁内等满频控间隔的两个上限(2026-09-25 修「下载被页面饿死」):
# - 单次等待超 `PROD_REQUEST_WAIT_MAX` 就放弃本轮 —— 配额窗口 / 熔断冷却 / 时间窗这类分钟级
#   以上的等待不该持着站点锁干等(合法的间隔等待是 90~113s, 远小于本值);
# - 一轮刷新的**总等待**超 `PROD_ROUND_WAIT_MAX` 也放弃剩余请求(下轮继续), 避免一次刷新
#   把站点锁长期占住(多实例时别人拿不到锁只能等下一轮)。
PROD_REQUEST_WAIT_MAX = 300.0
PROD_ROUND_WAIT_MAX = 900.0

#: 走查(--hr-once)单次最多等待的秒数: 防配置误设(如间隔 1H)把走查挂死
DIAGNOSTIC_MAX_WAIT = 600.0

#: 轮级骤降线(D1 拍板, 计划 26-09-27-1815 §5): 本轮合计 < 可信基线 × 30% 即骤降可疑。
#: 判据单位 = 全轮合计(所有抓取档位的解析行数和) —— 单档清零属站点正常语义(毕业迁移 /
#: 旧达标清除), 只有轮级合计崩塌才可疑; 基线 = 最近一次「结构完好且非零」轮, 可疑轮不计入。
PLUNGE_RATIO = 0.30

#: S1/S2 强信号连续 K 轮 ⇒ suspended(D1 同款直觉, 计划 §5: 持续零确认阈值与停用同款 3)
SUSPEND_ROUNDS = 3

#: 清单持续为零的告警升级阈值(计划 §2 2.2): 连续 K 轮零且结构完好 ⇒ 升级 WARNING + 人工确认口子
ZERO_LISTING_ROUNDS = 3

#: 早停② 的「已到期段」判定(计划 §2 4.4): 剩余达标时间为 0 的**连续**行数(跨页延续)达此值
#: 且考核期 P 一致 ⇒ 后续页只会是已到期种子, 本档在到期线内的清单已覆盖, 可停翻
AGE_STOP_STREAK = 5

#: 考核期 P 一致性容差(计划 §2 4.4): 反算 P 的离散超 ±1 天 ⇒ 告警 + 早停②/豁免 A 双双禁用
P_TOLERANCE_DAYS = 1.0


def plunge_suspect(total: int, baseline: int) -> bool:
    """轮级骤降判据(计划 §2 1.4): 合计归零或低于基线 30% ⇒ 可疑

    baseline <= 0 = 尚无可信基线(首刷 / 此前从未结构完好地跑完一轮)⇒ 不判 —— 首刷空表
    按现有口径是合法 complete, 骤降保护只对「有过可信基线之后的崩塌」生效。
    """
    if baseline <= 0:
        return False
    return total == 0 or total < baseline * PLUNGE_RATIO


class _SignalAbort(Exception):
    """S1/S2 强信号的轮内跳转(计划 §2 2.1): 停止本轮翻页, 折成 ACTION_ERROR

    用异常而非标志位: 处置要立刻跳出**两层**循环(页循环 + 档位循环), 已抓到的行在循环内
    已增量合并/落盘, 异常路径只负责记账(计失败 / 累计违反轮数 / 告警 / 写 meta)。
    """
    def __init__(self, kind: str, where: str, missing_rate: float = 0.0) -> None:
        super().__init__(where)
        self.kind = kind  # "order" = S1 排序违反 | "fields" = S2 必填字段缺失
        self.where = where
        self.missing_rate = missing_rate  # S2 的缺失率(告警文案用)


@dataclass(slots=True)
class HrRefreshResult:
    """一次刷新的结果(报告与日志用; 不含任何 qB 联动)"""

    site: str
    action: str
    reason: str = ""
    #: 没跑完的原因分类(REASON_*); 告警分层看它 —— 见模块顶部说明
    reason_kind: str = REASON_NONE
    #: 本轮是否**已由产生处**(本服务 / 存储层)报过 WARNING ⇒ 状态记录只记 INFO, 不重复告警
    #: (2026-09-24 用户实报: 同一次取数超时被 service 与 worker 各告警一次)
    alerted: bool = False
    complete: bool = False
    scopes_done: Tuple[str, ...] = ()
    pages_fetched: int = 0
    entries: int = 0
    entries_new: int = 0
    torrents_fetched: int = 0
    torrents_failed: int = 0
    verified_count: int = 0
    path: str = ""
    lock_ok: bool = True
    persisted: bool = False
    elapsed_s: float = 0.0
    #: 本轮排序校验是否发现违反(计划 §2 1.2/2.1; M5.1 只观测告警, M5.2 起消费为强信号处置)
    order_violated: bool = False
    #: 违反首处的人话位置(如「档位 A 第 2 页 页内逆序 1 处」; 告警与 --hr-status 展示共用)
    order_detail: str = ""
    #: 本轮结束时的**内存快照**(仅供走查/报告预览; 生产消费方读已发布的只读视图, 不读它)
    snapshot: Optional[HrSiteData] = None

    @property
    def ok(self) -> bool:
        return self.action in (ACTION_REFRESHED, ACTION_REUSED)


class HrRefreshService:
    """单站点刷新管道(每个站点一个 HrSiteStore; 站点之间互不阻塞)"""
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
        #: 遇到频控门槛时**等满再发**(生产与走查都传: 不等待就没法在一次刷新里发多个请求 ——
        #: 那会让「先页面后下载」的顺序把下载永久饿死, 见 `_backfill_on_reuse`);
        #: 传 None 只在测试里用(退回「本轮放弃」的旧语义)。
        self._sleeper = sleeper
        #: 单次 / 本轮总等待上限(秒); 走查模式放宽单次(要真跑完一轮), 总等待不限(0)
        self.sleep_max = sleep_max
        self.round_wait_max = round_wait_max
        self.dir = hr_dir(data_dir, global_conf.shared_dir)
        self._stores: Dict[str, HrSiteStore] = {}
        self._owner = owner
        #: 「无可用取数通道」已告警过的站点: 取数线程是分钟级轮询, 每轮都 WARNING 会把
        #: notify 的系统通知淹掉 —— 只在**状态变化**时报一次, 通道恢复后重置。
        self._no_channel_warned: set = set()
        #: 「扩展侧硬上限」已告警过的站点: 超限会持续到下一个窗口, 每轮都 WARNING 就是刷屏 ——
        #: 只在状态变化时报一次(与 `_no_channel_warned` 同一口径), 恢复正常后重置。
        self._ext_quota_warned: set = set()
        #: 「登录失效」(M4 四类事件之一)已告警过的站点: 登录态没恢复前每轮都会命中登录页,
        #: 每轮一条 WARNING 就是刷屏(而且它是**人工事件**, 报一次就够) —— 登录恢复后重置。
        self._login_warned: set = set()
        #: 「排序假设不成立」上一次告警时刻(站 -> 时刻): 排序违反往往持续多轮(页面真改版),
        #: 逐轮 WARNING 会刷屏 —— 按 channel_silence_warn 节流(计划 §2 1.6/2.1)。
        self._order_warned_at: Dict[str, float] = {}

    # ---------- 基础访问 ----------

    def store(self, site: str) -> HrSiteStore:
        """该站点的文件存储(惰性建; 每站点一把锁)"""
        got = self._stores.get(site)
        if got is None:
            got = HrSiteStore(site, self.dir, lock_timeout=self.global_conf.lock_timeout, owner=self._owner)
            self._stores[site] = got
        return got

    def site_path(self, site: str) -> str:
        return str(self.store(site).path)

    def enabled_sites(self) -> Tuple[str, ...]:
        return tuple(sorted(s for s, c in self.site_confs.items() if c.enabled))

    def limits_for(self, site: str) -> HrLimits:
        return HrLimits.merge(self.global_conf, self.site_confs[site])

    def verified_ttl_for(self, site: str) -> float:
        """放行有效期: 显式配置优先, 缺省跟随该站 refresh_interval(计划 §5)"""
        explicit = self.global_conf.verified_ttl
        return explicit if explicit is not None else self.site_confs[site].refresh_interval

    # ---------- 刷新 ----------

    def refresh_site(self, site: str, anchors: Optional[Mapping[str, HrAnchor]] = None) -> HrRefreshResult:
        """刷新单个站点; 任何异常都不外抛(单站点失败不拖垮其它站点)

        anchors: 本地种子锚点(infohash -> HrAnchor)。由主循环在唤醒取数线程时**以不可变数据**交接,
        取数线程不用读 store(线程边界不变)—— 用于写入放行记录的「提前作废」辅助信号。
        """
        started = self._now()
        site_conf = self.site_confs.get(site)
        result = HrRefreshResult(site=site, action=ACTION_DISABLED, path=self.site_path(site))
        if site_conf is None or not site_conf.enabled:
            result.reason = "该站未接入 hr_check(mode=off)"
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
                    # 存储层已按自己的节流口径告过这一条(坏文件是持续状态) ⇒ 状态记录不重复告警
                    result.alerted = session.read_alerted
                self._refresh_locked(site, site_conf, adapter, session, result, anchors or {})
        except HrLockBusy as e:
            result.action = ACTION_LOCKED
            result.reason = str(e)
        except Exception as e:  # 单站点失败不外抛
            result.action = ACTION_ERROR
            result.reason = f"{type(e).__name__}: {e}"
            result.alerted = True  # 上面这条 WARNING 就是本轮对它的告警, worker 不再重复
            logger.error(f"HR 站点 {site} | 刷新异常: {e}", exc_info=True)
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

        if data.suspended is not None:
            # 站点停用(计划 §2 2.3): 取数侧**零请求**(连复用轮的下载也让位) —— 数据是什么样
            # 就保持什么样, 直到人工排查后恢复。判定侧的回落语义见 resolve.judge_record。
            result.action = ACTION_SUSPENDED
            result.reason = f"站点已停用(suspended): {data.suspended.reason}(人工恢复, 见 --hr-status 指引)"
            return

        if data.login_backoff_until > now:
            # 登录失效指数退避(计划 §2 2.6): 退避期零请求 —— 登录没恢复前每轮照发只是白烧配额。
            # 不计失败、不推进熔断、不动 fetched_at(维持既有语义); 告警维持首见即报。
            result.action = ACTION_WAITING
            remain = data.login_backoff_until - now
            result.reason = f"登录失效退避中(还差 {remain:.0f}s, 期间零请求): 需人工在浏览器登录 {site}"
            return

        if data.fetched_at > 0 and data.expires_at > now:
            # 有效期内的数据直接采用(可能是别的实例刚抓的): 站点访问频率由数据有效期决定
            result.action = ACTION_REUSED
            result.complete = data.refresh.complete
            result.entries = len(data.index)
            result.verified_count = len(data.verified)
            result.scopes_done = tuple(data.refresh.scopes_done)
            result.reason = f"数据仍在有效期(至 {data.expires_at:.0f}), 直接复用"
            result.snapshot = data
            self._backfill_on_reuse(site, data, adapter, session, result, limits, now)
            return

        if not self.allow_fetch:
            result.action = ACTION_WAITING
            result.reason = "dry-run / 只读模式: 不发起取数"
            return

        if fuse_active(data.fuse, now):
            result.action = ACTION_WAITING
            result.reason = f"站点熔断中(至 {data.fuse.until_ts:.0f}): {data.fuse.reason}"
            return

        if limits.split:
            due, why = split_next_allowed_at(data.quota, limits, data.fuse, now, "page")
        else:
            due, why = next_allowed_at(data.quota, limits, data.fuse, now)
        if due > now:
            result.action = ACTION_WAITING
            result.reason = f"未到可取时刻({why}, 还差 {due - now:.0f}s)"
            return

        self._do_fetch(site, site_conf, adapter, session, result, limits, anchors)

    def _guarded_backfill(
        self,
        site: str,
        adapter,
        data: HrSiteData,
        pending: Mapping[int, HrEntry],
        budget,
        result: HrRefreshResult,
        session=None
    ) -> str:
        """跑一次回填, 把「让位 / 人工事件」类异常折成一句备注(**不计失败、不丢本轮已有成果**)。

        为什么必须包两层: `_fill_infohashes` 的间隔等待(可中断 sleeper)与 `get_bytes` 都可能抛
        `HrChannelStopped` / `HrChannelQuota` / `HrLoginExpired` —— 这些是 `HrFetchError` 的**子类**:
        - 漏到 `refresh_site` 的兜底 except ⇒ 被记成「刷新异常」WARNING(关停一次弹一条, 2026-09-24 实报同款);
        - 被 `_fill_infohashes` 的 `except HrFetchError` 吞掉 ⇒ 烧掉该 tid 的重试额度(把「程序要关了 /
          扩展限流 / 该去登录」伪装成「种子坏了」, 三次就是 12h 冷却)。
        故在 `_fill_infohashes` 里原样上抛、在这里折成备注。❗叫停也可能打在**派发前的间隔睡眠**上
        (sleeper 同样可中断), 故措辞是「下载阶段」而不是「取 .torrent 时」。
        """
        try:
            fetched, failed = self._fill_infohashes(
                adapter, data, pending, budget, site_conf=self.site_confs[site], session=session
            )
        except HrChannelStopped as e:
            return f"下载阶段被叫停(正在停止或重挂): {e}"
        except HrChannelQuota as e:
            self._warn_ext_quota(site, e)
            return f"下载阶段被扩展侧硬上限挡下: {e}"
        except HrLoginExpired as e:
            self._warn_login(site, e)
            return f"下载阶段命中登录页(需人工登录): {e}"
        result.torrents_fetched = fetched
        result.torrents_failed = failed
        if fetched or failed:
            result.snapshot = data
        return ""

    def _backfill_on_reuse(
        self, site: str, data: HrSiteData, adapter, session, result: HrRefreshResult, limits: HrLimits, now: float
    ) -> None:
        """复用轮: **只补下载**, 不碰页面(2026-09-25 实报修复)

        ❗为什么必须有: `_Budget` 的门槛是「相邻两次**请求**间隔 >= min_torrent_interval(只向上抖动)」,
        而 `_do_fetch` 的顺序是「先抓 A/B/C 页面, 后取 .torrent」⇒ 每个时间窗里**唯一**的那个名额
        总被页面拿走。实测(2026-09-25): 一小时内 11 次请求全花在页面重抓上(不完备刷新只给 60s
        有效期 ⇒ 下一轮又从头抓页面), `.torrent` 一次没取到 ⇒ 索引里 0 个 infohash 键 ⇒ 站点侧
        判定完全无从下手, 而整站种子会落到「未核实 ⇒ unknown_policy=hr」上去。
        故复用轮把名额全给下载: 每轮至少推进一条待回填, 索引才可能长出来。
        ❗窗口必须盖过下一轮: 不完备有效期只有 60s 时, 下一轮开始时刻(上一轮结束后再等 poll_interval)
        永远比 `expires_at` 晚一个 ε ⇒ 复用轮**从不发生**(窗口已改为 ≥ 2×poll_interval, 见 `_do_fetch`)。

        这里**不跑** `_refresh_verified`: 复用不是一次新的核实, 续放行有效期只能由真刷新给出。
        """
        if not self.allow_fetch or fuse_active(data.fuse, now):
            return
        pending = {tid: entry for tid, entry in data.index.items() if not (entry.infohash_v1 or entry.infohash_v2)}
        if not pending:
            return
        budget = _Budget(
            data, limits, self._now, self._sleeper, sleep_max=self.sleep_max, round_wait_max=self.round_wait_max
        )
        note = self._guarded_backfill(site, adapter, data, pending, budget, result, session=session)
        if not (result.torrents_fetched or result.torrents_failed):
            return
        result.reason += f"; 顺带补 infohash: 成功 {result.torrents_fetched} 失败 {result.torrents_failed}"
        if note:
            result.reason += f"; {note}"
        result.snapshot = data
        if self.persist:
            status = session.commit(self._now())
            result.persisted = status == "written"
            if status == "readonly":
                result.reason += "; 锁自检失败, 未写盘(只读退化)"

    def _backfill_on_page_failure(self, site: str, adapter, session, result: HrRefreshResult, limits: HrLimits) -> None:
        """页面取数失败后**仍补一次下载**(2026-09-25 实报「页面异常 ⇒ 回填被跳过」的饿死残留)

        待回填清单来自**已持久化的索引**(不依赖本轮页面), 页面失败不该把下载的名额一起带走。
        预算闸门照常生效: 熔断(刚失败可能刚推到冷却)/ 配额 / 间隔任一不满足就自然空手而回。
        split 站点跳过(下载只在复用轮做, §2 3.4): 页面失败轮的复用窗口(≥120s)内自会轮到下载。
        """
        if not self.allow_fetch or limits.split:
            return
        data = session.data
        pending = {tid: entry for tid, entry in data.index.items() if not (entry.infohash_v1 or entry.infohash_v2)}
        if not pending:
            return
        budget = _Budget(
            data, limits, self._now, self._sleeper, sleep_max=self.sleep_max, round_wait_max=self.round_wait_max
        )
        note = self._guarded_backfill(site, adapter, data, pending, budget, result, session=session)
        if note:
            result.reason = (result.reason + "; " if result.reason else "") + note
        if result.torrents_fetched or result.torrents_failed:
            result.snapshot = data
            if self.persist:
                status = session.commit(self._now())
                result.persisted = status == "written"

    def _do_fetch(
        self, site: str, site_conf: SiteHrCheckConfig, adapter, session, result, limits: HrLimits,
        anchors: Mapping[str, HrAnchor]
    ) -> None:
        data = session.data
        budget = _Budget(
            data, limits, self._now, self._sleeper, sleep_max=self.sleep_max, round_wait_max=self.round_wait_max
        )
        scopes: List[str] = list(site_conf.hr_page_scopes)
        entries_seen: Dict[int, HrEntry] = {}
        scopes_done: List[str] = []
        reached_last = True
        notes: List[str] = []
        max_missing = 0.0
        #: 没跑完的两类原因分开记: 频控拦下(可预期) / 页面问题(值得告警)
        budget_limited = False
        parse_problem = False
        #: 超龄豁免线(0 = 关闭): 开启时页面行按完成时间过滤 + 支持翻页早停(见 _apply_age_window)
        age_limit = site_conf.completed_age_limit
        # 预算轮转起点(D9=b, 计划 §2 4.3): 每轮从「上轮未完成」的档位起翻 —— 固定 A→B→C 在紧
        # 预算下会饿尾档(长清单吃光预算 ⇒ complete 恒假, §3.3「功能自废」换形态复发);
        # 跨轮语义不变(仍每档从第 1 页起翻), 只换档位间的先后。
        prev_done = set(data.refresh.scopes_done)
        scopes = [s for s in scopes if s not in prev_done] + [s for s in scopes if s in prev_done]
        #: 单轮页面总量上限(D5=a: 8~10 取 9; 0 = 不限) —— 单轮持锁时长的页数维度兜底
        pages_left_round = (self.global_conf.max_pages_per_round if self.global_conf.max_pages_per_round > 0 else None)
        round_pages_exhausted = False
        #: 早停② 状态(§2 4.4): 以已见最后一行结尾的连续 remain==0 行数(跨页延续)+ P 一致性
        zero_remain_streak = 0
        period_ok = True  # False = P 离散超容差 ⇒ 早停②禁用(豁免 A 由轮尾 meta 禁用)
        period_values: List[float] = []
        #: 排序观测(计划 26-09-27-1815 §2 1.2; M5.1 只记录不改判定): 判定前置 = 页面成功取回 +
        #: 表头解析出 + 可比行 ≥ 2(2026-09-26 用户定稿)。None = 证据不足未判定。
        order_verdict: Optional[bool] = None
        order_direction = ""  #: 轮级方向(由首个可推断的页推断; 之后翻转视同违反)
        order_where = ""  #: 首处违反的人话位置(告警与 --hr-status 共用)
        prev_order_dones: List[float] = []  #: 上一页可比完成时刻(跨页证据; age 过滤前)
        scope_counts: Dict[str, int] = {}  #: 本轮各档解析行数(观测「A: 37 → 0」用, age 过滤前)
        covered_local_any = False  #: 早停③是否命中(仅观测; 不改变判定语义)

        try:
            for scope in scopes:
                got_all_pages = True
                prev_page_dones: Optional[List[float]] = None  # 上一页的完成时刻(跨页倒序证据; None = 首页)
                for page in range(1, max(1, site_conf.max_pages_per_refresh) + 1):
                    # ---- 单轮页面总量(D5=a, §2 4.3): 超限 ⇒ 本轮剩余档位停止(不持锁干等) ----
                    if pages_left_round is not None and pages_left_round <= 0:
                        notes.append(f"达到单轮页面总量上限({self.global_conf.max_pages_per_round}), 本轮剩余档位停止")
                        budget_limited = True
                        got_all_pages = False
                        reached_last = False
                        round_pages_exhausted = True
                        break
                    allowed, why = budget.take("page")
                    if not allowed:
                        notes.append(f"配额/间隔受限({why})")
                        budget_limited = True
                        got_all_pages = False
                        reached_last = False
                        break
                    html = self.fetcher.get_text(adapter.page_url(scope, page))
                    budget.mark("page")
                    if pages_left_round is not None:
                        pages_left_round -= 1
                    if adapter.looks_like_login(html):
                        # 登录失效 → 专用异常(见 HrLoginExpired): 不计失败、不推进熔断, 要的是人去看一眼
                        raise HrLoginExpired(f"命中登录页(档位 {scope} 第 {page} 页): 登录态失效, 需人工处理")
                    if adapter.looks_like_challenge(html):
                        raise HrFetchError(f"命中挑战页(档位 {scope} 第 {page} 页)")
                    parsed = adapter.parse_page(scope, html)
                    result.pages_fetched += 1
                    if not parsed.header_found:
                        notes.append(f"档位 {scope} 第 {page} 页未找到 HR 表(疑似改版)")
                        parse_problem = True
                        got_all_pages = False
                        reached_last = False
                        break
                    max_missing = max(max_missing, parsed.missing_field_rate)
                    # ---- 排序观测(§2 1.2; 基于 age 过滤前的原始行序) ----
                    scope_counts[scope] = scope_counts.get(scope, 0) + len(parsed.entries)
                    dones = [e.done_epoch for e in parsed.entries if e.done_epoch is not None]
                    check = order_violations(dones)
                    page_bad = ""
                    if check.ok:
                        if not order_direction:
                            order_direction = check.direction
                        elif check.direction != order_direction:
                            page_bad = f"方向翻转(本页 {check.direction}, 轮级 {order_direction})"
                    if not page_bad and check.inversions > 0:
                        page_bad = f"页内逆序 {check.inversions} 处"
                    if not page_bad and cross_page_violation(prev_order_dones, dones, order_direction):
                        page_bad = "跨页乱序"
                    if page_bad:
                        order_verdict = False
                        if not order_where:
                            order_where = f"档位 {scope} 第 {page} 页 {page_bad}"
                        # S1 强信号处置(计划 §2 2.1, 2026-09-26 用户定稿): 哪怕 1 处 ⇒ 立即停止
                        # 本轮翻页并判失败 —— 排序假设崩塌时「未列出」不再可信, 继续翻只会白烧配额。
                        raise _SignalAbort("order", order_where)
                    if check.comparable >= 2 and order_verdict is None:
                        order_verdict = True
                    # S2 强信号处置: 必填字段缺失**不设比例阈值** —— 行数据读不全 = 页面形态变了,
                    # 与改版同罪; 旧缺失率阈值(0.5)会放走「缺一半」的页面, 那正是 P1 的形态。
                    if parsed.missing_field_rate > 0:
                        where = f"档位 {scope} 第 {page} 页必填字段缺失率 {parsed.missing_field_rate:.0%}"
                        raise _SignalAbort("fields", where, parsed.missing_field_rate)
                    prev_order_dones = dones
                    # ---- P 一致性机检(§2 4.4): 参与行反算 P, 离散超 ±1 天 ⇒ 禁用早停②(告警一次) ----
                    for e in parsed.entries:
                        # 参与行 = 还在线内的行(remain > 0; 已到期行 remain 被截 0, 反算为负不参与)
                        # ❗公式勘误(计划 26-09-27-1815 §2 4.4 三份制品同源的笔误): P = (now − done) + remain
                        # (考核期 = 已考核时长 + 剩余时长); 计划写成的 done + remain − now 在数学上恒为
                        # 负偏移量, 与 P 的物理定义矛盾 —— 按唯一正确方向实现, 回写时注明。
                        if e.done_epoch is not None and e.remain_seconds and e.remain_seconds > 0:
                            period_values.append((self._now() - e.done_epoch) + e.remain_seconds)
                    if period_values:
                        med_p = median(period_values)
                        if max(abs(v - med_p) for v in period_values) > P_TOLERANCE_DAYS * 86400.0:
                            if period_ok:
                                logger.warning(
                                    events.period_inconsistent(
                                        site, (max(period_values) - min(period_values)) / 86400.0
                                    )
                                )
                            period_ok = False
                    kept, early_stop, page_dones = self._apply_age_window(
                        parsed.entries, age_limit, self._now(), prev_page_dones
                    )
                    for entry in kept:
                        entries_seen[entry.tid] = entry
                    # 增量落盘(2026-09-25 实报「后端无落盘, Ctrl+C 后才落盘」): 一轮现在要跨多个扩展
                    # 轮询周期(分钟级、持锁进行), 只在轮尾写盘的话, 中途 Ctrl+C / 断电会把已抓的页面
                    # 与配额账本一起丢掉 —— 每抓到一页就合并 + 提交(complete=False 语义: 只把命中的
                    # 置 active, 保守方向); 轮尾仍按完整语义再合并一次并写覆盖证明。
                    self._merge_index(data, entries_seen, self._now(), False, self.global_conf.index_retention)
                    if self.persist:
                        session.commit(self._now())
                    # ---- 早停③ 覆盖本地(§2 4.6 严格版): 本地种子全部已见 + 索引无待回填 ⇒ 停翻 ----
                    # 只停「不影响本地判定」的部分: 本档不进 scopes_done ⇒ 不置 complete(绝不放行)。
                    # 基于本轮 merge 后的状态(hash 继承自旧 entry / 本轮回填), 故必须在 merge 之后检查。
                    if anchors:
                        local_hashes = {h for h in anchors if h}
                        seen_hashes = {h for e in entries_seen.values() for h in (e.infohash_v1, e.infohash_v2) if h}
                        pending_now = sum(
                            1 for e in data.index.values() if e.active and not e.infohash_v1 and not e.infohash_v2
                        )
                        if local_hashes and local_hashes <= seen_hashes and pending_now == 0:
                            notes.append("早停: 本站本地种子已全部出现在已抓行中(严格版), 本档停翻(不产生覆盖证明)")
                            covered_local_any = True
                            got_all_pages = False
                            break
                    if early_stop:
                        # 后续页只会更老 ⇒ 本档位在豁免线内的清单已全覆盖; 没翻到的页不值得再花配额
                        if parsed.has_next:
                            notes.append(
                                f"档位 {scope} 第 {page} 页整页超龄(完成时间超过 {age_limit / 86400:.0f} 天), "
                                "早停翻页(后续页不再取)"
                            )
                        break
                    # ---- 早停② 已到期段(§2 4.4): 连续 remain==0 达阈值且 P 一致 ⇒ 本档覆盖证明成立 ----
                    # 「活跃条目页数」取代「清单总页数」成为覆盖证明的分母(P1 断点续翻问题的消解):
                    # 到期段之后的页全是已到期种子, 不会再有线内清单行, 翻完只是白烧配额。
                    tail_zero = 0
                    for e in reversed(parsed.entries):
                        if e.remain_seconds == 0:
                            tail_zero += 1
                        else:
                            break
                    if parsed.entries and tail_zero == len(parsed.entries):
                        zero_remain_streak += tail_zero  # 整页全 0: 延续上一页尾部
                    elif tail_zero:
                        zero_remain_streak = tail_zero  # 页首延续(尾部段从本页某行起)
                    else:
                        zero_remain_streak = 0
                    if period_ok and zero_remain_streak >= AGE_STOP_STREAK and parsed.has_next:
                        notes.append(
                            f"档位 {scope} 第 {page} 页命中已到期段(连续 {zero_remain_streak} 行剩余达标时间为 0), "
                            "早停翻页(覆盖证明按已覆盖活跃段成立)"
                        )
                        break  # got_all_pages 保持 True ⇒ 本档 done(§2 4.2「翻到已到期段」)
                    prev_page_dones = page_dones
                    # 翻页判据并集(§2 1.3): 「下一页」真实链接与 maxpage/currentpage 脚本标记,
                    # **任一说还有下一页就继续翻**(保守方向) —— 顺带堵 P1 的英文站缺口
                    # (has_next_page 只认中文「下一页」的问题由第二判据兜住)。
                    marks = page_javascript_marks(html)
                    cur_mark, max_mark = marks.get("currentpage"), marks.get("maxpage")
                    marks_says_next = cur_mark is not None and max_mark is not None and cur_mark < max_mark
                    if not parsed.has_next and not marks_says_next:
                        break
                else:
                    # for-else: 到页数上限仍有下一页 ⇒ 没抓到底
                    notes.append(f"档位 {scope} 达到单次翻页上限({site_conf.max_pages_per_refresh})仍未到底")
                    parse_problem = True
                    got_all_pages = False
                    reached_last = False
                if got_all_pages:
                    scopes_done.append(scope)
                if round_pages_exhausted:
                    break  # 单轮页面总量耗尽: 剩余档位本轮不再发请求
        except _SignalAbort as sig:
            # S1/S2 强信号处置(计划 §2 2.1): ① 停止本轮翻页(异常即出, 不再发请求)
            # ② 判本轮拉取失败(ACTION_ERROR, 不产生放行) ③ 计入失败 + 累计连续违反轮数
            # ④ WARNING 告警(文案分开: order_broken / field_missing)。
            # 已抓到的行保留命中(循环内已增量合并/落盘, 不置 complete) —— 命中是站点侧事实,
            # 保留只会往受管束方向偏(保守无害)。
            now = self._now()
            record_failure(data.fuse, limits, now)
            signal_rounds = data.refresh.signal_rounds + 1
            if sig.kind == "order":
                order_verdict = False
                result.order_violated = True
                result.order_detail = sig.where
                self._warn_order(site, sig.where)
            else:
                self._warn_field(site, sig.where, sig.missing_rate)
            data.refresh = replace(
                data.refresh,
                complete=False,
                reason=f"{sig.where}; 强信号处置: 本轮判失败, 不产生放行",
                order_ok=order_verdict,
                order_detail=sig.where if sig.kind == "order" else data.refresh.order_detail,
                signal_rounds=signal_rounds,
            )
            result.action = ACTION_ERROR
            result.reason = sig.where
            result.alerted = True  # 告警已由 _warn_* 发出 ⇒ worker 不重复
            if signal_rounds >= SUSPEND_ROUNDS and data.suspended is None:
                data.suspended = HrSuspension(
                    reason=sig.where,
                    since=now,
                    evidence=f"连续 {signal_rounds} 轮 {'排序违反' if sig.kind == 'order' else '字段缺失'}强信号",
                    rounds=signal_rounds,
                )
                logger.error(events.suspended(site, signal_rounds, sig.where))
            if self.persist:
                status = session.commit(now)
                result.persisted = status == "written"
            else:
                result.reason = f"{result.reason}; 只读模式, 未写盘"
            return
        except HrChannelStopped as e:
            # 关停 / 热重挂时被叫停: 既不是「没通道」也不是故障 ⇒ 不告警、不计失败(不推进熔断),
            # 本轮直接让位(下轮自会重来)。
            result.action = ACTION_WAITING
            result.reason = f"本轮取数被叫停(正在停止或重挂端点): {e}"
            return
        except HrChannelQuota as e:
            # 扩展侧硬上限(第二道闸)挡下: 说明**后端自己的频控没生效** —— 但这仍不是「取数失败」,
            # 计失败会把站点推进熔断、把配置/逻辑问题掩盖成「站点坏了」。故只让位 + 报一次。
            result.action = ACTION_WAITING
            result.reason = f"扩展侧硬上限挡下(后端频控可能失效), 本轮让位: {e}"
            self._warn_ext_quota(site, e)
            return
        except HrChannelUnavailable as e:
            result.action = ACTION_NO_CHANNEL
            result.reason = str(e)
            self._warn_no_channel(site, e)
            return
        except HrLoginExpired as e:
            # 登录失效(四类事件之一): **只有人去浏览器登录才会好**, 故不算取数失败、不推进熔断 ——
            # 计失败会把「去登录」这个动作要求掩盖成「站点坏了」(而且熔断冷却会让用户登录完还要白等)。
            # 仍然留下的痕迹: ①一条 WARNING(文案直接给动作, 每站点一次) ②站点文件的 refresh.reason
            # (报告与视图 notes 都读它) —— 但**不动** fetched_at / 覆盖证明 / 新鲜度基准, 这是红线:
            # 登录失效不得变成新的放行背书, 也不得把老数据的新鲜度弄脏。
            result.action = ACTION_ERROR
            result.reason = str(e)
            result.alerted = True  # 下面这条 WARNING 已含原因与动作 ⇒ 状态记录只记 INFO
            data.refresh = replace(data.refresh, reason=events.login_expired_note(site, e))
            # 指数退避(计划 §2 2.6): 2^(n-1) × poll_interval, 上限 = refresh_interval ——
            # 登录没恢复前每轮照发只是白烧配额(≤12/时)。仍不计失败、不推进熔断、不动 fetched_at。
            streak = data.login_expired_streak + 1
            data.login_expired_streak = streak
            backoff = min(self.global_conf.poll_interval * (2.0**(streak - 1)), site_conf.refresh_interval)
            data.login_backoff_until = self._now() + backoff
            if self.persist:
                status = session.commit(self._now())
                result.persisted = status == "written"
            else:
                result.reason = f"{result.reason}; 只读模式, 未写盘"
            self._warn_login(site, e)
            return
        except HrFetchError as e:
            newly = record_failure(data.fuse, limits, self._now(), getattr(e, "retry_after", 0.0))
            result.action = ACTION_ERROR
            result.reason = str(e)
            result.alerted = True  # 下面这条 WARNING 已含原因与失败次数 ⇒ 状态记录只记 INFO
            if self.persist:
                # ❗失败计数/熔断也是**持久状态**: 只读口径(dry-run / hr.once)下同样不得落盘,
                # 否则「不写文件」是句空话 —— 走查会把熔断写进站点文件, 影响正式实例的取数节奏。
                status = session.commit(self._now())
                result.persisted = status == "written"
            else:
                result.reason = f"{result.reason}; 只读模式, 未写盘"
            if newly:
                logger.error(events.fuse_opened(site, data.fuse.until_ts, e))
            else:
                logger.warning(events.fetch_failed(site, data.fuse.failures, limits.failure_threshold, e))
            # 页面失败**不带走下载的名额**(2026-09-25 实报饿死残留): 待回填清单在已持久化的索引里,
            # 预算闸门(熔断/配额/间隔)会自己决定这一 shot 能不能发。
            self._backfill_on_page_failure(site, adapter, session, result, limits)
            return

        record_success(data.fuse)
        # 登录恢复(完整跑完一轮 = 登录态肯定回来了): 清零退避与连续失效计数(计划 §2 2.6)
        data.login_expired_streak = 0
        data.login_backoff_until = 0.0
        # 骤降观测(§2 1.4; M5.1 只记录, M5.2 起消费为「判不完备」): 轮级合计 vs 可信基线。
        # 基线只取「结构完好且完整跑完(无 budget 截断)、非零、非可疑」的轮 —— budget 截断轮的
        # 合计偏小(作基线会误伤后续轮), 可疑轮不计入(堵「0 vs 0」自愈洞), 排序违反轮可能是改版轮。
        total_now = len(entries_seen)
        suspect = plunge_suspect(total_now, data.refresh.entry_baseline)
        # 人工确认口子(D1, 计划 §2 2.2): 空清单 + 站点显式 accept_empty_listing ⇒ 接受为合法
        # (即使基线存在)。只豁免「零」这一形态 —— 非零骤降(改版丢行)不适用; 前提仍是本轮结构完好。
        if suspect and total_now == 0 and site_conf.accept_empty_listing and not parse_problem:
            suspect = False
        new_baseline = data.refresh.entry_baseline
        if not parse_problem and not budget_limited and total_now > 0 and not suspect \
                and order_verdict is not False:
            new_baseline = total_now
        new_plunge_rounds = data.refresh.plunge_rounds + 1 if suspect else 0
        self._no_channel_warned.discard(site)  # 通道恢复: 下次真的没通道时再报一次
        self._ext_quota_warned.discard(site)  # 恢复正常: 下次再超限时重新报一次
        self._login_warned.discard(site)  # 登录恢复: 下次真的又失效时再报一次
        entries_new = sum(1 for tid in entries_seen if tid not in data.downloaded)
        if limits.split:
            # 页面/下载分工(计划 §2 3.4): split 站点**页面只在新轮做、下载只在复用轮做** ——
            # 「种子可以慢慢下载」落地, 单轮持锁时长缩短; 复用轮(_backfill_on_reuse)已现成。
            dl_note = ""
        else:
            dl_note = self._guarded_backfill(site, adapter, data, entries_seen, budget, result, session=session)
        if dl_note:
            notes.append(dl_note)
        complete = bool(scopes) and len(scopes_done) == len(scopes) and reached_last and max_missing <= \
            self.global_conf.parse_missing_rate_max and not suspect
        # M5.2 骤降保护(计划 §2 2.2): 骤降可疑 ⇒ 判不完备, 不产生放行, 保留命中 ——
        # 一次性批量清除/迁移在下一轮以新基线自愈(代价 = 一轮刷新的放行延迟, 不完备轮后 120s 即重试)。
        if suspect and complete is False and not notes:
            notes.append(f"骤降可疑(本轮合计 {total_now} vs 基线 {data.refresh.entry_baseline}), 判不完备")
        # 持续零告警升级(计划 §2 2.2): 合计连续 K 轮为零且本轮结构完好 ⇒ WARNING + 人工确认口子指引。
        # 刻意不自动接受: 持续零 + 结构完好同样可由改版造出, 自动接受等于重开 P1 灾难面。
        if suspect and total_now == 0 and not parse_problem \
                and data.refresh.plunge_rounds + 1 >= ZERO_LISTING_ROUNDS:
            self._warn_zero_listing(site, data.refresh.plunge_rounds + 1)
        # M5.1 观测口径: 排序违反**不改判定**(处置在 M5.2), 只如实进 notes / meta / 告警
        if order_verdict is False:
            notes.append(f"排序假设不成立({order_where})")
            self._warn_order(site, order_where)
        self._merge_index(data, entries_seen, self._now(), complete, self.global_conf.index_retention)
        # 清单命中对账兜底(§2 2.5): 行重回清单时 hash 常从旧 entry 继承(回填循环会跳过),
        # 在 merge 后对「命中行名下已知 hash」统一对账 —— partial 轮也即时收放行, 不等下一次完整刷新。
        retracted = self._retract_on_listing(data, entries_seen)
        if retracted:
            logger.info(f"HR 站点 {site} | 清单对账: 撤销 {retracted} 条放行记录(种子已在清单, listed-late)")
        result.entries = len(data.index)
        result.entries_new = entries_new

        if not complete and not notes:
            notes.append("刷新不完备")
        if max_missing > self.global_conf.parse_missing_rate_max:
            notes.append(f"必填字段缺失率 {max_missing:.0%} 超阈({self.global_conf.parse_missing_rate_max:.0%})")
            parse_problem = True
        if not complete:
            # 分类判据: 只要沾了页面/字段/翻页问题就算 parse(**不明原因也保守当 parse** —— 宁可多看一眼);
            # 纯被频控拦下的才是 budget
            result.reason_kind = REASON_BUDGET if (budget_limited and not parse_problem) else REASON_PARSE

        now = self._now()
        data.refresh = HrRefreshMeta(
            # last_success_ts 只在**完整成功**时前进 —— 不完备刷新不得推进新鲜度基准(否则会误放行)
            last_success_ts=now if complete else data.refresh.last_success_ts,
            scopes_done=scopes_done,
            pages_fetched=result.pages_fetched,
            reached_last_page=reached_last,
            entry_count=len(entries_seen),
            missing_field_rate=max_missing,
            complete=complete,
            reason="; ".join(notes),
            order_ok=order_verdict,
            order_detail=order_where,
            probe_period_days=(median(period_values) / 86400.0 if period_values and period_ok else 0.0),
            period_consistent=bool(period_values) and period_ok,
            entry_baseline=new_baseline,
            plunge_suspect=suspect,
            plunge_rounds=new_plunge_rounds,
            scope_counts=scope_counts,
            prev_scope_counts=dict(data.refresh.scope_counts),
        )
        result.order_violated = order_verdict is False
        result.order_detail = order_where
        data.fetched_at = now
        # 有效期只由刷新周期决定; 不完备刷新不续放行(放行有效期仍以各记录的 verified_ts 计)。
        # ❗不完备窗口必须盖过取数线程的**下一轮**(2026-09-25 实报修复): 窗口 60s == poll_interval 60s,
        # 而下一轮从「上一轮结束后再等 poll_interval」才开始 ⇒ 现算时刻永远比 expires_at 晚一个 ε ⇒
        # 复用轮(唯一给下载让名额的轮次)**从不发生**。取 2×poll_interval(下限 120s)、以刷新周期封顶;
        # 判定不读 expires_at(三态按 last_success_ts / verified_ts 现算), 拉长它不产生任何放行,
        # 只是给 `_backfill_on_reuse` 留一个不重抓页面的轮次。
        backfill_window = min(max(120.0, 2.0 * self.global_conf.poll_interval), site_conf.refresh_interval)
        data.expires_at = now + site_conf.refresh_interval if complete else now + backfill_window
        result.verified_count = self._refresh_verified(data, entries_seen, complete, now, anchors)
        result.complete = complete
        result.scopes_done = tuple(scopes_done)
        result.action = ACTION_REFRESHED if complete else ACTION_PARTIAL
        result.reason = "; ".join(notes)
        result.snapshot = data

        if self.persist:
            status = session.commit(now)
            result.persisted = status == "written"
            if status == "readonly":
                result.reason = (result.reason + "; " if result.reason else "") + "锁自检失败, 未写盘(只读退化)"
        else:
            result.reason = (result.reason + "; " if result.reason else "") + "只读模式, 未写盘"

    # ---------- 索引与放行 ----------

    @staticmethod
    def _merge_index(
        data: HrSiteData, entries: Mapping[int, HrEntry], now: float, complete: bool, retention: float = 0.0
    ) -> None:
        """页面行合并进索引: 只更新字段, 保留 first_seen 与已回填的 infohash。

        active 语义(判定只认 active 条目):
        - **完整刷新**: 先把全部条目置 False, 再把本批命中的置 True —— 「本次没列出」才算消失;
        - **不完备刷新**: 只把命中的置 True —— "没抓全"不能证明其它条目已消失(保守方向)。
        """
        if complete:
            for old in data.index.values():
                old.active = False
        for tid, fresh in entries.items():
            old = data.index.get(tid)
            fresh.active = True
            if old is None:
                fresh.first_seen = now
                fresh.last_seen = now
                data.index[tid] = fresh
            else:
                fresh.first_seen = old.first_seen or now
                fresh.last_seen = now
                fresh.infohash_v1 = old.infohash_v1 or fresh.infohash_v1
                fresh.infohash_v2 = old.infohash_v2 or fresh.infohash_v2
                data.index[tid] = fresh
        # 页面快照条目的陈旧淘汰(不触碰永久层 hr_downloaded)
        if retention > 0:
            for tid in list(data.index):
                entry = data.index[tid]
                if not entry.active and entry.last_seen and now - entry.last_seen > retention:
                    del data.index[tid]

    @staticmethod
    def _apply_age_window(entries: List[HrEntry], limit: float, now: float,
                          prev_page_dones: Optional[List[float]]) -> Tuple[List[HrEntry], bool, List[float]]:
        """超龄行过滤 + 翻页早停信号(completed_age_limit 开启时; limit <= 0 原样返回, 零行为变更)。

        - **过滤**: 完成时间超过 limit 的行不入索引 —— 判定侧对这些种子直接超龄豁免, 索引行留着
          只会白白触发回填下载烧配额; 完成时间缺失/不可解析的行**保留**(不猜, 保守方向)。
        - **早停**: 整页每行都有可解析完成时间、全部超龄、且页内与跨页都呈**完成时间倒序** ⇒
          后续页只会更老, 本档位在豁免线内的清单已全覆盖, 可安全停翻。倒序证据不成立(页面按
          别的东西排序 / 有行缺完成时间)就继续翻 —— 错误方向的代价只是多花配额, 不是漏判;
          但一旦早停成立, 覆盖证明按「豁免线内全覆盖」计(可达 complete ⇒ 放行照常产生)。
        返回 (保留行, 是否早停, 本页可解析的完成时刻列表)。`prev_page_dones` 为 None 表示首页
        (无跨页约束), 为空列表表示上一页没有可解析的完成时刻(跨页证据缺失 ⇒ 不允许早停)。
        """
        if limit <= 0 or not entries:
            return list(entries), False, []
        dones = [e.done_epoch for e in entries if e.done_epoch is not None]
        kept = [e for e in entries if e.done_epoch is None or now - e.done_epoch < limit]
        early_stop = (
            len(dones) == len(entries) and all(now - d >= limit for d in dones) and
            all(dones[i] >= dones[i + 1] for i in range(len(dones) - 1)) and
            (prev_page_dones is None or (prev_page_dones and min(prev_page_dones) >= max(dones)))
        )
        return kept, early_stop, dones

    def _fill_infohashes(
        self,
        adapter,
        data: HrSiteData,
        entries: Mapping[int, HrEntry],
        budget,
        site_conf: SiteHrCheckConfig,
        session=None
    ) -> Tuple[int, int]:
        """为「索引里还没有 infohash」的 tid 取 .torrent 算 infohash。

        防重复下载三层: ① hr_downloaded 永久层(在则绝不重下) ② 索引已有 infohash 的只更新字段
        ③ 失败按 max_download_retries 计数, 达上限后冷却。二进制默认不落盘(只算 infohash)。
        `session` 给了就**每个结果落盘一次**(2026-09-25 实报): hr_downloaded 是「永不重取」的
        凭据、fails 是防烧配额的记账 —— 中途被杀不该丢, 丢了就是白烧配额重下。

        回填顺序按 first_seen **新行优先**(计划 §2 2.5): 新进的清单行先拿到 infohash,
        「放行收不回」的对账撤销就早一分钟发生(窗口从 ≤ verified_ttl 收缩到 ≤ 回填时延)。
        """
        fetched = failed = 0
        cooldown = self.global_conf.failure_cooldown
        ordered = sorted(entries.items(), key=lambda kv: kv[1].first_seen or 0.0, reverse=True)
        for tid, entry in ordered:
            if entry.infohash_v1 or entry.infohash_v2:
                continue
            got = data.downloaded.get(tid)
            if got is not None and (got.infohash_v1 or got.infohash_v2):
                entry.infohash_v1, entry.infohash_v2 = got.infohash_v1, got.infohash_v2
                # 永久层复用同样算「infohash 回填成功」: 对账撤销照跑(§2 2.5) —— 行重回清单时
                # 该 hash 的放行依据「未列出」已失效, 不管 hash 是刚下载算出还是从永久层恢复。
                if self._retract_on_backfill(data, got.infohash_v1, got.infohash_v2):
                    logger.info(f"HR 站点 {adapter.site} | tid={tid} 回填对账(永久层复用): 撤销放行记录"
                                "(种子已回清单, listed-late)")
                continue
            fail = data.fails.get(tid)
            if fail is not None and fail.count >= self.global_conf.max_download_retries and \
                    self._now() - fail.last_ts < cooldown:
                continue
            allowed, _why = budget.take("torrent")
            if not allowed:
                break
            try:
                # dl_id: 行内链接提取的下载用种子 id(CarPT 等站点 H&R ID 与种子 id 两个空间);
                # None = 同空间站点, 回落 tid
                blob = self.fetcher.get_bytes(adapter.download_url(entry.dl_id or tid))
                budget.mark("torrent")
            except (HrChannelStopped, HrChannelQuota, HrLoginExpired):
                # 让位 / 人工事件, 不是「这个种子取失败」: 计数会烧掉 max_download_retries 额度,
                # 把「程序要关了 / 扩展限流 / 该去登录」伪装成「种子坏了」。原样上抛,
                # 由 `_guarded_backfill` 折成备注(见其 docstring)。
                raise
            except HrFetchError as e:
                failed += 1
                fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
                fail.count += 1
                fail.last_ts = self._now()
                self._persist_step(session)
                logger.warning(f"HR 站点 {adapter.site} | tid={tid} 取 .torrent 失败({fail.count} 次): {e}")
                continue
            try:
                v1, v2, info = compute_infohashes(blob)
            except ValueError as e:
                failed += 1
                fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
                fail.count += 1
                fail.last_ts = self._now()
                self._persist_step(session)
                logger.warning(f"HR 站点 {adapter.site} | tid={tid} 返回内容不是合法 .torrent: {e}")
                continue
            entry.infohash_v1, entry.infohash_v2 = v1, v2
            retracted = self._retract_on_backfill(data, v1, v2)
            if retracted:
                logger.info(
                    f"HR 站点 {adapter.site} | tid={tid} 回填对账: 撤销 {retracted} 条放行记录"
                    "(种子已回清单, 放行依据「未列出」失效; listed-late)"
                )
            # ts 是这一份 .torrent 自己的取回时刻 —— 一批里各条互不相同(整批共用开始时刻会让取证误读)
            data.downloaded[tid] = HrDownloaded(
                tid=tid, ts=self._now(), name=torrent_display_name(info) or entry.name, infohash_v1=v1, infohash_v2=v2
            )
            data.fails.pop(tid, None)
            fetched += 1
            self._persist_step(session)
        return fetched, failed

    def _persist_step(self, session) -> None:
        """增量落盘的统一口(只在正式口径下写; 走查 persist=False 不落盘)。"""
        if session is not None and self.persist:
            session.commit(self._now())

    @staticmethod
    def _retract_on_backfill(data: HrSiteData, v1: str, v2: str) -> int:
        """回填对账撤销(计划 26-09-27-1815 §2 2.5, P2「放行收不回」修复)

        infohash 回填成功时与现有放行记录对账: 该 (站点, infohash) 若已有放行 ⇒ 说明种子其实
        已回清单, 放行依据「本次未列出」已失效 —— 命中即作废(listed-late), 未命中不动。
        撤销只发生在 hash **精确对上**时(无误伤面); 返回撤销条数(供日志)。
        """
        retracted = 0
        for h in (v1, v2):
            if h and h in data.verified:
                del data.verified[h]
                retracted += 1
        return retracted

    @staticmethod
    def _retract_on_listing(data: HrSiteData, entries: Mapping[int, HrEntry]) -> int:
        """清单命中行对账兜底(§2 2.5): 命中行名下**已知** hash 对上放行 ⇒ 撤销

        与 _retract_on_backfill 的分工: 那个管「hash 刚到账」(新算出 / 永久层复用, 复用轮也走),
        这个管「行重回清单时 hash 从旧 entry 继承」—— merge 保留旧 hash 后回填循环会跳过,
        兜底撤销只能在 merge 后做。完整刷新的批量对账在 _refresh_verified(complete 路径)。
        """
        retracted = 0
        for entry in entries.values():
            for h in (entry.infohash_v1, entry.infohash_v2):
                if h and h in data.verified:
                    del data.verified[h]
                    retracted += 1
        return retracted

    def _refresh_verified(
        self, data: HrSiteData, entries_seen: Mapping[int, HrEntry], complete: bool, now: float,
        anchors: Mapping[str, HrAnchor]
    ) -> int:
        """更新放行记录(计划 §9)

        - D 档(已免罪) ⇒ source=absent
        - 已取过 .torrent 但**本次完整刷新未列出**(且已不在 active 清单里) ⇒ source=not-listed
        - infohash 已进 A/B/C 清单 ⇒ 删除放行记录(它已受管束)
        - **不完备刷新不产生新放行, 也不续期已有放行** —— 放行只由完整核实产生
        """
        if not complete:
            return len(data.verified)
        listed: Dict[str, int] = {}
        exempt: set[str] = set()
        for entry in entries_seen.values():
            if entry.lane == LANE_EXEMPT:
                for h in (entry.infohash_v1, entry.infohash_v2):
                    if h:
                        data.verified[h] = _verified_for(h, entry.tid, SOURCE_EXEMPT, now, anchors.get(h))
                        exempt.add(h)
                continue
            for h in (entry.infohash_v1, entry.infohash_v2):
                if h:
                    listed[h] = entry.tid
        for h in list(data.verified):
            if h in listed:
                del data.verified[h]
        for got in data.downloaded.values():
            for h in (got.infohash_v1, got.infohash_v2):
                # D 档(已免罪)的放行依据更强(站点明确免罪), 不被 not-listed 覆盖
                if not h or h in listed or h in exempt:
                    continue
                data.verified[h] = _verified_for(h, got.tid, SOURCE_NOT_LISTED, now, anchors.get(h))
        return len(data.verified)

    # ---------- 视图 ----------
    def build_view_for(self, site: str, data: HrSiteData) -> HrSiteView:
        """用给定（内存）数据构造视图 —— 供走查报告预览本轮结果(生产读已落盘视图)"""
        return build_site_view(
            site,
            self.site_confs[site].mode,
            data,
            verified_ttl=self.verified_ttl_for(site),
            refresh_interval=self.site_confs[site].refresh_interval,
            channel_state=self.channel_state(site, data),
            generated_at=self._now(),
        )

    def build_views(self) -> Dict[str, "HrSiteView"]:
        """构建各站点的只读视图(不加锁读: 写入是原子替换, 读到的必然是完整的一份)"""
        out: Dict[str, "HrSiteView"] = {}
        for site, site_conf in self.site_confs.items():
            if not site_conf.enabled:
                continue
            data, _err = self.store(site).read_unlocked()
            out[site] = build_site_view(
                site,
                site_conf.mode,
                data,
                verified_ttl=self.verified_ttl_for(site),
                refresh_interval=site_conf.refresh_interval,
                channel_state=self.channel_state(site, data),
                generated_at=self._now(),
            )
        return out

    def channel_state(self, site: str, data: Optional[HrSiteData] = None) -> str:
        """通道状态: disabled(未启用 channel) / silent(长期没有成功刷新) / ok"""
        if not self.global_conf.channel.enabled:
            return CHANNEL_DISABLED
        if data is None:
            data, _err = self.store(site).read_unlocked()
        if data.refresh.last_success_ts <= 0:
            return CHANNEL_SILENT
        if self._now() - data.refresh.last_success_ts > self.global_conf.channel_silence_warn:
            return CHANNEL_SILENT
        return CHANNEL_OK

    def _warn_no_channel(self, site: str, err: Exception) -> None:
        """无通道告警: **每个站点只报一次**(直到通道恢复) —— 分钟级轮询下逐轮告警会淹没通知"""
        if site in self._no_channel_warned:
            logger.debug(f"HR 站点 {site} | 无可用取数通道(已告警过, 不重复): {err}")
            return
        self._no_channel_warned.add(site)
        logger.warning(f"HR 站点 {site} | 无可用取数通道, 本轮不做在线核实(保守回落未核实): {err}")

    def _warn_login(self, site: str, err: Exception) -> None:
        """登录失效告警: **每个站点只报一次**(直到登录恢复)

        文案单点在 `events.login_expired` —— 必须含**动作**(去哪个浏览器登录哪个站点), 否则用户
        只看到「失败了」; 标签前缀 `[HR 登录失效]` 让日志里这一类事件可 grep。
        """
        if site in self._login_warned:
            logger.info(f"HR 站点 {site} | 登录态仍未恢复(已告警过, 本轮不做在线核实): {err}")
            return
        self._login_warned.add(site)
        logger.error(events.login_expired(site, err))

    def _warn_order(self, site: str, detail: str) -> None:
        """排序假设不成立告警(计划 26-09-27-1815 §2 1.6/2.1): WARNING 按 channel_silence_warn 节流

        M5.1 观测期只告证不改判定(不早停、不判失败、不计停站计数); M5.2 起同轮由强信号处置
        (判失败 / 停站计数)接管, **文案不变** —— 真机观测期直接对文案排查。"""
        warn_gap = max(60.0, float(self.global_conf.channel_silence_warn))
        now = self._now()
        if now - self._order_warned_at.get(site, 0.0) < warn_gap:
            logger.info(f"HR 站点 {site} | 排序假设仍不成立(节流期内不重复告警): {detail}")
            return
        self._order_warned_at[site] = now
        logger.warning(events.order_broken(site, detail))

    def _warn_field(self, site: str, detail: str, rate: float) -> None:
        """必填字段缺失告警(S2, 计划 §2 2.1): 文案与排序违反**分开**, 节流窗口与 S1 共用

        (S1/S2 同属 parse 类信号且不会同轮同时发生 —— 先触发者先处置; 共用一个时间戳字典
        避免同一站点在同一天内两类告警各刷一条系统通知。)
        """
        warn_gap = max(60.0, float(self.global_conf.channel_silence_warn))
        now = self._now()
        if now - self._order_warned_at.get(site, 0.0) < warn_gap:
            logger.info(f"HR 站点 {site} | 必填字段缺失(节流期内不重复告警): {detail}")
            return
        self._order_warned_at[site] = now
        logger.warning(events.field_missing(site, rate))

    def _warn_zero_listing(self, site: str, rounds: int) -> None:
        """清单持续为零的告警升级(计划 §2 2.2): K 轮零且结构完好 ⇒ WARNING + 人工确认口子指引

        刻意不自动接受空清单 —— 持续零 + 结构完好同样可由改版造出, 自动接受等于重开 P1 灾难面;
        误要人工确认的代价只是终态场景多敲一次确认, 方向不对称故保守优先。
        """
        warn_gap = max(60.0, float(self.global_conf.channel_silence_warn))
        now = self._now()
        if now - self._order_warned_at.get(site, 0.0) < warn_gap:
            logger.info(f"HR 站点 {site} | 清单仍为 0(第 {rounds} 轮, 节流期内不重复告警)")
            return
        self._order_warned_at[site] = now
        logger.warning(events.zero_listing(site, rounds))

    def _warn_ext_quota(self, site: str, err: Exception) -> None:
        """扩展侧硬上限告警: 同样**只报一次**(超限会持续到下一个窗口)

        这条 WARNING 值得看一眼: 后端自己有频控, 正常**不该**惊动扩展的第二道闸 ——
        真触发说明后端频控没生效(配置被改坏 / 代码有 bug / 手工灌任务), 光看「本轮让位」的信息级
        日志会漏掉它。
        """
        if site in self._ext_quota_warned:
            logger.info(f"HR 站点 {site} | 扩展侧硬上限仍生效(已告警过, 本轮让位): {err}")
            return
        self._ext_quota_warned.add(site)
        logger.warning(
            f"HR 站点 {site} | 扩展侧硬上限挡下取数(第二道闸): 多半是后端频控失效(检查 hr_check 的间隔/配额配置"
            "与日志), 也可能是扩展上限本就低于后端配额(60/时·600/天 vs 后端 12~40/时, 属正常优先)"
        )


def _verified_for(infohash: str, tid: int, source: str, now: float, anchor: Optional[HrAnchor] = None) -> HrVerified:
    a = anchor or HrAnchor()
    return HrVerified(
        infohash=infohash,
        tid=tid,
        verified_ts=now,
        source=source,
        anchor_added_on=a.added_on,
        anchor_downloaded=a.downloaded,
        anchor_completion_on=a.completion_on,
        anchor_progress=a.progress,
    )


class _Budget:
    """一次刷新内的请求预算: 每发起一次站点请求(页 / .torrent)都要过这里。

    - 间隔: 相邻两次请求间隔 >= min_torrent_interval(抖动只向上)
    - 配额: 小时/天两级, 到顶即停(返回空清单语义), 不报错

    sleeper 非空时遇到门槛**等满再发**(生产路径与走查路径都传 —— 不等待的话一次刷新只能发出
    第一个请求, 「先页面后下载」的顺序会把下载永久饿死, 见 `_backfill_on_reuse`);
    等待上限两档: 单次 `sleep_max`(超过说明是配额窗口 / 熔断 / 时间窗这类分钟级以上的等待),
    本轮累计 `round_wait_max`(0 = 不限) —— 超限即放弃本轮, 不持着站点锁干等。
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
        """本轮已等掉的总秒数(供排障 / 断言) """
        return self._waited

    def take(self, kind: str = "page") -> Tuple[bool, str]:
        """申请一次请求名额; kind ∈ {page, torrent}(split 模型分开记账, legacy 忽略 kind)

        split(计划 26-09-27-1815 §2 3.2): 页面走 quota 桶、下载走 torrent_quota 桶,
        门槛 = 该类请求的最小间隔 + 令牌补充 + 天级硬顶; legacy 走合并账本(行为不变)。
        """
        if self._limits.split:
            return self._take_split(kind)
        now = self._now()
        due, why = next_allowed_at(self._data.quota, self._limits, self._data.fuse, now)
        if due > now:
            wait = due - now
            if self._sleeper is None or wait > self._sleep_max or \
                    (self._round_wait_max > 0 and self._waited + wait > self._round_wait_max):
                return False, f"{why}: 还差 {wait:.0f}s"
            self._sleeper(wait)
            self._waited += wait
            now = self._now()
        if not try_consume(self._data.quota, self._limits, now, 1):
            return False, "配额已用尽"
        return True, ""

    def _take_split(self, kind: str) -> Tuple[bool, str]:
        quota = self._data.quota if kind == "page" else self._data.torrent_quota
        now = self._now()
        due, why = split_next_allowed_at(quota, self._limits, self._data.fuse, now, kind)
        if due > now:
            wait = due - now
            if self._sleeper is None or wait > self._sleep_max or \
                    (self._round_wait_max > 0 and self._waited + wait > self._round_wait_max):
                return False, f"{why}: 还差 {wait:.0f}s"
            self._sleeper(wait)
            self._waited += wait
            now = self._now()
        if not split_try_consume(quota, self._limits, now, kind):
            return False, f"{'页面' if kind == 'page' else '下载'}桶令牌不足"
        return True, ""

    def mark(self, kind: str = "page") -> None:
        """请求已发出: 记下配额消耗时刻, 作为下一次间隔门槛的基准

        split 模型由 split_try_consume 在消费时推进对应桶的 refill_ts(等待后的时刻已正确),
        这里无需再记。
        """
        if self._limits.split:
            return
        self._data.quota.last_fetch_ts = self._now()


__all__ = [
    "ACTION_DISABLED",
    "ACTION_ERROR",
    "ACTION_LOCKED",
    "ACTION_NO_CHANNEL",
    "ACTION_PARTIAL",
    "ACTION_REFRESHED",
    "ACTION_REUSED",
    "ACTION_SUSPENDED",
    "ACTION_WAITING",
    "HrRefreshResult",
    "HrRefreshService",
]

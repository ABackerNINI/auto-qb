"""HR 在线核实的波次引擎(v3 单波型, 计划 26-09-28-1932 §4)。

一次刷新 = 持锁 → 对象集波前现算(计划 26-10-05-0555 §2.2 提级到 `_refresh_locked`: 每 poll
一次、各闸之前, 稳态判定与拉取间隔动态取值同点完成) → 复用窗 / 拉取间隔 / allow_fetch / 频控
各闸依次放行 → 开波: A/B/C 轮流翻页(三停翻条件) → 行处理(命中定论 + 身份登记) → 防伪 →
放行签发/观察期推进 → 写盘 → 释放。闸拦下则波不开, 波前现算照跑(各分支返回前稳态旗标都能刷新)。

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
from . import log as hr_log
from .adapters import build_adapter
from .bencode import compute_infohashes, torrent_display_name
from .fetcher import (
    HrChannelQuota,
    HrChannelStopped,
    HrChannelUnavailable,
    HrExtensionNetwork,
    HrExtensionNoPermission,
    HrFetchError,
    HrFetcher,
    HrLoginExpired,
)
from .model import (
    CHANNEL_DISABLED,
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    CHANNEL_SILENT,
    FETCH_LANES,
    FULL_DEPTH_TEXT,
    LANE_EXEMPT,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_TAGS,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrHistoryEvent,
    HrLaneState,
    HrSiteData,
    HrVerified,
    lane_is_terminal,
    prune_history,
    _lane_count_segment,
)
from .parse import cross_page_violation, order_violations, page_javascript_marks
from .ratelimit import HrLimits, next_allowed_at, try_consume
from .resolve import HrAnchor, HrSiteView, build_site_view
from .store import HrLockBusy, HrSiteStore, hr_dir
# 拆分后根模块仍是公开 import 面: 上面这些原文件已导入的名字在此续留(re-export), 调用方不变。
from .service_common import (
    ACTION_DISABLED,
    ACTION_ERROR,
    ACTION_LOCKED,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_REUSED,
    ACTION_WAITING,
    ALL_FAILED_REUSE_WINDOW,
    CHANNEL_SILENCE_WARN,
    COVERAGE_SLACK,
    DIAGNOSTIC_MAX_WAIT,
    DL_RETRY_COOLDOWN,
    FUZZY_NAME_K,
    FUZZY_NOISE_TOKEN,
    HISTORY_NOTES_MAX,
    HISTORY_REASON_MAX,
    INDEX_RETENTION,
    LANE_FAIL_ALERT_STREAK,
    LANE_RETENTION_MIN,
    MAX_DOWNLOAD_RETRIES,
    MISSING_GRACE_WAVES,
    POLL_INTERVAL,
    PROD_REQUEST_WAIT_MAX,
    PROD_ROUND_WAIT_MAX,
    REASON_BUDGET,
    REASON_NONE,
    REASON_PARSE,
    SEED_EXEMPT_RATIO,
    ZERO_REMAIN_STREAK,
    HrRefreshResult,
    _Budget,
    _LaneAbort,
    _WaveContext,
    _absence_proven_all,
    _dl_by_hash,
    _fuzzy_signal,
    _lane_covers_done,
    _lanes_summary_from,
    _mark_fetch_failed_lane,
    _position_covered,
    _prune_index,
    _release_record,
    _settle_lane,
    fuzzy_name_match,
    logger,
    warn_gap_floor,
)
from .service_status import StatusMixin
from .service_wave import WaveMixin


class HrRefreshService(StatusMixin, WaveMixin):
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
        self._owner = owner
        # 站点存储构造期预建(取数线程 × Web 线程并发首访各建一份、其一被引用覆盖丢弃 ——
        # FileLock 按路径互斥虽兜住后果, 「每站点一实例」契约却依赖实现时序; issue
        # 26-10-06-0028 chore-lazy-init-double-construct)。conf 外点名(CLI --hr-confirm-empty
        # 手输站点)仍走 store() 惰性分支兜底。
        self._stores: Dict[str, HrSiteStore] = {
            site: HrSiteStore(site, self.dir, lock_timeout=0.0, owner=owner)
            for site in site_confs
        }
        #: 「无可用取数通道」已告警过的站点: 取数线程是分钟级轮询, 每轮都 WARNING 会把
        #: notify 的系统通知淹掉 —— 只在**状态变化**时报一次, 通道恢复后重置。
        self._no_channel_warned: set = set()
        #: 「扩展未授权该站点」已告警过的站点(计划 26-10-29-0147 D7): 它是**要人动手**的配置态,
        #: 故单独一套去重集合 + ERROR 级 + 可见(进前端错误历史、触发主动通知);
        #: 与 `_no_channel_warned` 分开是因为两者级别与可见性不同, 共用一套会互相压掉。
        self._no_perm_warned: set = set()
        #: 「扩展到站点的网络层失败」已告警过的站点: 归通道层(等环境恢复), 每站一次 + silent
        self._network_warned: set = set()
        #: 「扩展侧硬上限」已告警过的站点(超限会持续到下一个窗口, 只在状态变化时报一次)。
        self._ext_quota_warned: set = set()
        #: 「登录失效」已告警过的站点: 登录态没恢复前每轮都会命中登录页, 报一次就够。
        self._login_warned: set = set()
        #: 「页面形态异常」(排序/字段/表头/防伪)上一次告警时刻(站 -> 时刻): 持续多轮,
        #: 按 CHANNEL_SILENCE_WARN 节流。
        self._parse_warned_at: Dict[str, float] = {}

    # ---------- 基础访问 ----------

    def store(self, site: str) -> HrSiteStore:
        """该站点的文件存储(每站点一把锁; site_confs 站点已构造期预建, 惰性分支只兜 conf 外
        点名)。锁等待常量化 0(拿不到直接等下一轮, §6.2)"""
        got = self._stores.get(site)
        if got is None:
            got = HrSiteStore(site, self.dir, lock_timeout=0.0, owner=self._owner)
            self._stores[site] = got
        return got

    def site_path(self, site: str) -> str:
        return str(self.store(site).path)

    def enabled_sites(self) -> Tuple[str, ...]:
        return tuple(sorted(s for s, c in self.site_confs.items() if c.enabled))

    def fetchable_sites(self) -> Tuple[str, ...]:
        """取数集合(清单型才翻页, issue 26-10-05-0922): 全站型(listing=none)不取数 —— 判定恒走
        行 4 本地兜底, 翻页只会白烧配额。展示/状态口径仍用 enabled_sites(全站型照样出状态)"""
        return tuple(sorted(s for s, c in self.site_confs.items() if c.fetchable))

    def limits_for(self, site: str) -> HrLimits:
        return HrLimits.merge(self.global_conf, self.site_confs.get(site))

    # ---------- 波次入口 ----------

    def refresh_site(
        self, site: str, anchors: Optional[Mapping[str, HrAnchor]] = None, force: bool = False
    ) -> HrRefreshResult:
        """跑单个站点的一波; 任何异常都不外抛(单站点失败不拖垮其它站点)

        anchors: 本地种子锚点(infohash -> HrAnchor, 含 name)。由主循环在唤醒取数线程时
        **以不可变数据**交接, 取数线程不用读 store(线程边界不变)。
        三态契约(计划 26-10-05-0555 §2.5): None = 锚点采集失败/未知 —— 稳态降频不生效
        (不把「不知道」当「零种子」), wave 行为与空锚点一致; {} = 采集成功且该站零锚点
        (确认零交集, 可降频); 非空映射 = 正常对账。
        force: 「立即拉取」(计划 26-09-30-0240) —— 跳过复用窗与拉取间隔两道调度闸;
        min_interval / 日额 / Retry-After / 时间窗(账号安全线与站点指令)照常生效。
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
                # anchors 的 None(采集失败/未知)原样直通, 不吞成 {} —— 三态契约见 refresh_site docstring(§2.5)
                self._refresh_locked(site, site_conf, adapter, session, result, anchors, force=force)
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

    def refresh_all(
        self,
        anchors_by_site: Optional[Mapping[str, Mapping[str, HrAnchor]]] = None,
        force: bool = False,
    ) -> List[HrRefreshResult]:
        # 三态与 worker.run_once 同款(计划 26-10-05-0555 §2.5): 顶层 None = 采集失败/未知 →
        # 各站 None(稳态不生效); 映射缺某站键 = 确认该站零锚点 → {}。
        # 站点集合走 fetchable(非 enabled): 全站型(listing=none)不取数, issue 26-10-05-0922。
        return [
            self.refresh_site(
                site, anchors_by_site.get(site, {}) if anchors_by_site is not None else None, force=force
            ) for site in self.fetchable_sites()
        ]

    # ---------- 锁内主流程 ----------

    def _refresh_locked(
        self,
        site: str,
        site_conf: SiteHrCheckConfig,
        adapter,
        session,
        result,
        anchors: Optional[Mapping[str, HrAnchor]],
        force: bool = False,
    ) -> None:
        data = session.data
        limits = self.limits_for(site)
        now = self._now()

        # ---- 波前: 对象集现算(§2.2 提级, 计划 26-10-05-0555) ----
        # 每 poll 每站一次纯内存现算(零额外 IO, 报告 §13.2 裁定可接受); 锚点漂移回炉随之从
        # 「波时」提前到「poll 时」(≤60s) —— 本机重下的种子其放行记录作废更及时, 且它把对象集
        # 翻非空 ⇒ 间隔闸回退(报告 §13.2「新下载自动破稳态」依赖的正是这一步, 回炉语义不变)。
        # 复用窗 / 拉取间隔 / allow_fetch / 频控各提前 return 分支返回前判据已在手。
        anchors_known = anchors is not None
        wave_anchors = anchors or {}
        objects, observing, unmatched = self._build_objects(data, wave_anchors, site_conf.required_seeding_time)
        # 稳态判定(§2.1): 对账对象集为空 ∧ 锚点采集成功 —— 采集失败(None)不算稳态(§2.5),
        # 否则主循环侧故障会被当成「零交集」而错误降频(报告 R5 唯一实质风险)。
        steady = anchors_known and not objects
        interval = site_conf.idle_refresh_interval if steady else site_conf.refresh_interval
        # 稳态旗标只在**翻转时**写盘(§2.4): 稳态期反复 poll 旗标不变 ⇒ 零写盘(守「自动 poll
        # 零写盘」纪律, 翻转至多每天几次); 旗标只供展示链读, 闸门永远用上面的本实例现算值(§06 R6)。
        if data.wave.idle_mode != steady:
            data.wave.idle_mode = steady
            self._persist_step(session)

        # 复用窗(新鲜度闸): 窗内数据直接采用(可能是别的实例刚抓的)。force(立即拉取)跳过本闸 ——
        # 两道调度闸(复用窗 + 拉取间隔)都可被人工意志越过, 账号安全线(min_interval 等)不在此列
        if not force and data.fetched_at > 0 and data.expires_at > now:
            result.action = ACTION_REUSED
            result.entries = len(data.index)
            result.verified_count = len(data.verified)
            result.lane_texts = _lanes_summary_from(data.wave.lanes)
            result.reason = f"数据仍在复用窗(至 {data.expires_at:.0f}), 直接复用"
            result.snapshot = data
            return

        # 拉取间隔闸门(计划 26-09-30-0240 + 26-10-05-0555 §2.3): 节奏硬闸, 与复用窗(新鲜度)解耦 ——
        # 下次核对清单 = 上次健康波 + 拉取间隔(动态取值: 稳态期 = idle_refresh_interval; 对象集
        # 一翻非空自动回退 refresh_interval, 而 healthy + refresh_interval 早已过去 ⇒ 下一 poll
        # 立即开波)。失败波不推进 healthy_ts ⇒ 失败的档位仍按「下一轮(60s)重试」, 与现状一致。
        # force(立即拉取)跳过本闸; min_interval / 日额 / Retry-After / 时间窗在下方照常生效
        #(账号安全线不被越过)。
        healthy = data.wave.healthy_ts
        if not force and healthy > 0:
            due_wave = healthy + interval
            if now < due_wave:
                result.action = ACTION_WAITING
                result.reason = (
                    f"未到拉取时刻(拉取间隔·稳态降频, 还差 {due_wave - now:.0f}s)"
                    if steady else f"未到拉取时刻(拉取间隔, 还差 {due_wave - now:.0f}s)"
                )
                return

        if not self.allow_fetch:
            result.action = ACTION_WAITING
            result.reason = "dry-run / 只读模式: 不发起取数"
            if force:  # defer 只记用户点击级(§3.3); 自动 poll 的 waiting 不记不写盘(60s 节拍零写盘)
                self._append_history(
                    site, data, kind="defer", trigger="manual", action=ACTION_WAITING, reason=result.reason
                )
                self._persist_step(session)
            return

        due, why = next_allowed_at(data, limits, now)
        if due > now:
            result.action = ACTION_WAITING
            result.reason = f"未到可取时刻({why}, 还差 {due - now:.0f}s)"
            if force:  # min_interval / 日额 / Retry-After / 时间窗都在本闸汇成一条 defer(账号安全线拦下的立即拉取)
                self._append_history(
                    site, data, kind="defer", trigger="manual", action=ACTION_WAITING, reason=result.reason
                )
                self._persist_step(session)
            return

        self._do_wave(
            site, site_conf, adapter, session, result, limits, wave_anchors, objects, observing, unmatched, force=force
        )

    @staticmethod
    def _update_cutoff(st: HrLaneState, parsed) -> None:
        """滚动记录该档已见最深行的完成时刻(缺席证明的位置边界; 截断式数据有效性, §3.4)"""
        page_deepest = HrRefreshService._deepest_seen_done(parsed)
        if page_deepest > 0 and (st.cutoff_done <= 0 or page_deepest < st.cutoff_done):
            st.cutoff_done = page_deepest

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

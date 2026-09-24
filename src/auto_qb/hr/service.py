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
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional, Tuple

from ..config.models import HrCheckConfig, SiteHrCheckConfig
from .adapters import build_adapter
from .bencode import compute_infohashes, torrent_display_name
from .fetcher import HrChannelUnavailable, HrFetchError, HrFetcher
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
    HrVerified,
)
from .ratelimit import HrLimits, fuse_active, next_allowed_at, record_failure, record_success, try_consume
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

#: 走查(--hr-once)单次最多等待的秒数: 防配置误设(如间隔 1H)把走查挂死
DIAGNOSTIC_MAX_WAIT = 600.0


@dataclass(slots=True)
class HrRefreshResult:
    """一次刷新的结果(报告与日志用; 不含任何 qB 联动)"""

    site: str
    action: str
    reason: str = ""
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
    ) -> None:
        self.data_dir = data_dir
        self.global_conf = global_conf
        self.site_confs = dict(site_confs)
        self.fetcher = fetcher
        self.persist = persist
        self.allow_fetch = allow_fetch
        self._now = now_fn
        #: 走查模式可传入睡睡函数: 遇到间隔/配额门槛时**等满**而不是放弃本轮(生产不传 = 等下一轮)
        self._sleeper = sleeper
        self.dir = hr_dir(data_dir, global_conf.shared_dir)
        self._stores: Dict[str, HrSiteStore] = {}
        self._owner = owner
        #: 「无可用取数通道」已告警过的站点: 取数线程是分钟级轮询, 每轮都 WARNING 会把
        #: notify 的系统通知淹掉 —— 只在**状态变化**时报一次, 通道恢复后重置。
        self._no_channel_warned: set = set()

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
                self._refresh_locked(site, site_conf, adapter, session, result, anchors or {})
        except HrLockBusy as e:
            result.action = ACTION_LOCKED
            result.reason = str(e)
        except Exception as e:  # 单站点失败不外抛
            result.action = ACTION_ERROR
            result.reason = f"{type(e).__name__}: {e}"
            logger.warning(f"HR 站点 {site} | 刷新异常: {e}", exc_info=True)
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
            # 有效期内的数据直接采用(可能是别的实例刚抓的): 站点访问频率由数据有效期决定
            result.action = ACTION_REUSED
            result.complete = data.refresh.complete
            result.entries = len(data.index)
            result.verified_count = len(data.verified)
            result.scopes_done = tuple(data.refresh.scopes_done)
            result.reason = f"数据仍在有效期(至 {data.expires_at:.0f}), 直接复用"
            result.snapshot = data
            return

        if not self.allow_fetch:
            result.action = ACTION_WAITING
            result.reason = "dry-run / 只读模式: 不发起取数"
            return

        if fuse_active(data.fuse, now):
            result.action = ACTION_WAITING
            result.reason = f"站点熔断中(至 {data.fuse.until_ts:.0f}): {data.fuse.reason}"
            return

        due, why = next_allowed_at(data.quota, limits, data.fuse, now)
        if due > now:
            result.action = ACTION_WAITING
            result.reason = f"未到可取时刻({why}, 还差 {due - now:.0f}s)"
            return

        self._do_fetch(site, site_conf, adapter, session, result, limits, anchors)

    def _do_fetch(
        self, site: str, site_conf: SiteHrCheckConfig, adapter, session, result, limits: HrLimits,
        anchors: Mapping[str, HrAnchor]
    ) -> None:
        data = session.data
        budget = _Budget(data, limits, self._now, self._sleeper)
        scopes: List[str] = list(site_conf.hr_page_scopes)
        entries_seen: Dict[int, HrEntry] = {}
        scopes_done: List[str] = []
        reached_last = True
        notes: List[str] = []
        max_missing = 0.0

        try:
            for scope in scopes:
                got_all_pages = True
                for page in range(1, max(1, site_conf.max_pages_per_refresh) + 1):
                    allowed, why = budget.take()
                    if not allowed:
                        notes.append(f"配额/间隔受限({why})")
                        got_all_pages = False
                        reached_last = False
                        break
                    html = self.fetcher.get_text(adapter.page_url(scope, page))
                    budget.mark()
                    if adapter.looks_like_login(html):
                        raise HrFetchError(f"命中登录页(档位 {scope} 第 {page} 页): 登录态失效, 需人工处理")
                    if adapter.looks_like_challenge(html):
                        raise HrFetchError(f"命中挑战页(档位 {scope} 第 {page} 页)")
                    parsed = adapter.parse_page(scope, html)
                    result.pages_fetched += 1
                    if not parsed.header_found:
                        notes.append(f"档位 {scope} 第 {page} 页未找到 HR 表(疑似改版)")
                        got_all_pages = False
                        reached_last = False
                        break
                    max_missing = max(max_missing, parsed.missing_field_rate)
                    for entry in parsed.entries:
                        entries_seen[entry.tid] = entry
                    if not parsed.has_next:
                        break
                else:
                    # for-else: 到页数上限仍有下一页 ⇒ 没抓到底
                    notes.append(f"档位 {scope} 达到单次翻页上限({site_conf.max_pages_per_refresh})仍未到底")
                    got_all_pages = False
                    reached_last = False
                if got_all_pages:
                    scopes_done.append(scope)
        except HrChannelUnavailable as e:
            result.action = ACTION_NO_CHANNEL
            result.reason = str(e)
            self._warn_no_channel(site, e)
            return
        except HrFetchError as e:
            newly = record_failure(data.fuse, limits, self._now(), getattr(e, "retry_after", 0.0))
            result.action = ACTION_ERROR
            result.reason = str(e)
            session.commit(self._now())
            result.persisted = session.writable
            if newly:
                logger.warning(f"HR 站点 {site} | 连续失败达阈值, 熔断至 {data.fuse.until_ts:.0f}: {e}")
            else:
                logger.warning(f"HR 站点 {site} | 取数失败({data.fuse.failures} 次): {e}")
            return

        record_success(data.fuse)
        self._no_channel_warned.discard(site)  # 通道恢复: 下次真的没通道时再报一次
        entries_new = sum(1 for tid in entries_seen if tid not in data.downloaded)
        fetched, failed = self._fill_infohashes(adapter, data, entries_seen, budget, site_conf)
        complete = bool(scopes) and len(scopes_done) == len(scopes) and reached_last and max_missing <= \
            self.global_conf.parse_missing_rate_max
        self._merge_index(data, entries_seen, self._now(), complete, self.global_conf.index_retention)
        result.entries = len(data.index)
        result.entries_new = entries_new
        result.torrents_fetched = fetched
        result.torrents_failed = failed

        if not complete and not notes:
            notes.append("刷新不完备")
        if max_missing > self.global_conf.parse_missing_rate_max:
            notes.append(f"必填字段缺失率 {max_missing:.0%} 超阈({self.global_conf.parse_missing_rate_max:.0%})")

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
        )
        data.fetched_at = now
        # 有效期只由刷新周期决定; 不完备刷新不续放行(放行有效期仍以各记录的 verified_ts 计)
        data.expires_at = now + site_conf.refresh_interval if complete else now + min(60.0, site_conf.refresh_interval)
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

    def _fill_infohashes(
        self, adapter, data: HrSiteData, entries: Mapping[int, HrEntry], budget, site_conf: SiteHrCheckConfig
    ) -> Tuple[int, int]:
        """为「索引里还没有 infohash」的 tid 取 .torrent 算 infohash。

        防重复下载三层: ① hr_downloaded 永久层(在则绝不重下) ② 索引已有 infohash 的只更新字段
        ③ 失败按 max_download_retries 计数, 达上限冷却。二进制默认不落盘(只算 infohash)。
        """
        fetched = failed = 0
        now = self._now()
        cooldown = self.global_conf.failure_cooldown
        for tid, entry in entries.items():
            if entry.infohash_v1 or entry.infohash_v2:
                continue
            got = data.downloaded.get(tid)
            if got is not None and (got.infohash_v1 or got.infohash_v2):
                entry.infohash_v1, entry.infohash_v2 = got.infohash_v1, got.infohash_v2
                continue
            fail = data.fails.get(tid)
            if fail is not None and fail.count >= self.global_conf.max_download_retries and \
                    now - fail.last_ts < cooldown:
                continue
            allowed, _why = budget.take()
            if not allowed:
                break
            try:
                blob = self.fetcher.get_bytes(adapter.download_url(tid))
                budget.mark()
            except HrFetchError as e:
                failed += 1
                fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
                fail.count += 1
                fail.last_ts = now
                logger.warning(f"HR 站点 {adapter.site} | tid={tid} 取 .torrent 失败({fail.count} 次): {e}")
                continue
            try:
                v1, v2, info = compute_infohashes(blob)
            except ValueError as e:
                failed += 1
                fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
                fail.count += 1
                fail.last_ts = now
                logger.warning(f"HR 站点 {adapter.site} | tid={tid} 返回内容不是合法 .torrent: {e}")
                continue
            entry.infohash_v1, entry.infohash_v2 = v1, v2
            data.downloaded[tid] = HrDownloaded(
                tid=tid, ts=now, name=torrent_display_name(info) or entry.name, infohash_v1=v1, infohash_v2=v2
            )
            data.fails.pop(tid, None)
            fetched += 1
        return fetched, failed

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

    sleeper 非空时(走查模式)遇到门槛**等满再发**, 让单次走查也能跑完一轮;
    生产路径不传 sleeper ⇒ 本轮直接放弃, 下一轮再来(绝不阻塞取数线程)。
    """
    def __init__(
        self, data: HrSiteData, limits: HrLimits, now_fn, sleeper: Optional[Callable[[float], None]] = None
    ) -> None:
        self._data = data
        self._limits = limits
        self._now = now_fn
        self._sleeper = sleeper

    def take(self) -> Tuple[bool, str]:
        now = self._now()
        due, why = next_allowed_at(self._data.quota, self._limits, self._data.fuse, now)
        if due > now:
            wait = due - now
            if self._sleeper is None or wait > DIAGNOSTIC_MAX_WAIT:
                return False, f"{why}: 还差 {wait:.0f}s"
            self._sleeper(wait)
            now = self._now()
        if not try_consume(self._data.quota, self._limits, now, 1):
            return False, "配额已用尽"
        return True, ""

    def mark(self) -> None:
        """请求已发出: 记下配额消耗时刻, 作为下一次间隔门槛的基准"""
        self._data.quota.last_fetch_ts = self._now()


__all__ = [
    "ACTION_DISABLED",
    "ACTION_ERROR",
    "ACTION_LOCKED",
    "ACTION_NO_CHANNEL",
    "ACTION_PARTIAL",
    "ACTION_REFRESHED",
    "ACTION_REUSED",
    "ACTION_WAITING",
    "HrRefreshResult",
    "HrRefreshService",
]

"""hr 波次引擎 mixin: 翻页 / 下载 / 裁剪 / 停止条件 / 波后收尾(自 service.py move-only 切出)

拆分(R5)只搬位置: 方法文本与 service.py 原文件逐字一致(保留缩进与注释)。
"""
from dataclasses import replace
from typing import Dict, List, Mapping, Optional, Tuple

from ..config.models import SiteHrCheckConfig
from . import events
from .bencode import compute_infohashes, torrent_display_name
from .fetcher import (
    HrChannelQuota,
    HrChannelStopped,
    HrChannelUnavailable,
    HrFetchError,
    HrLoginExpired,
)
from .model import (
    FETCH_LANES,
    LANE_EXEMPT,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    LANE_SATISFIED,
    LANE_SCOPE,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrHistoryEvent,
    HrLaneState,
    HrSiteData,
    lane_is_terminal,
    prune_history,
)
from .parse import cross_page_violation, order_violations, page_javascript_marks
from .ratelimit import HrLimits
from .resolve import HrAnchor
from .service_common import (
    ACTION_ERROR,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_WAITING,
    COVERAGE_SLACK,
    DL_RETRY_COOLDOWN,
    HISTORY_NOTES_MAX,
    HISTORY_REASON_MAX,
    LANE_FAIL_ALERT_STREAK,
    LANE_RETENTION_MIN,
    MAX_DOWNLOAD_RETRIES,
    MISSING_GRACE_WAVES,
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
    _lane_covers_done,
    _lanes_summary_from,
    _mark_fetch_failed_lane,
    _position_covered,
    _prune_index,
    _release_record,
    _settle_lane,
    fuzzy_name_match,
    logger,
)


class WaveMixin:
    """波次/翻页/下载/裁剪/停止条件/波后收尾域方法"""

    # ---------- 波次引擎(§4) ----------

    def _do_wave(
        self,
        site: str,
        site_conf: SiteHrCheckConfig,
        adapter,
        session,
        result,
        limits: HrLimits,
        anchors: Mapping[str, HrAnchor],
        objects: Dict[str, HrAnchor],
        observing: Dict[str, HrEntry],
        unmatched: Dict[str, HrAnchor],
        force: bool = False
    ) -> None:
        data = session.data
        # 拉取历史的 trigger 口径(计划 26-10-04-0312 §3.3): 立即拉取=manual, 调度自动=auto
        trigger = "manual" if force else "auto"
        wave_started = self._now()

        def _stamp_elapsed() -> None:
            # 记录点现算波耗时(result.elapsed_s 会被 refresh_site 收尾用含锁全波值再盖一次)
            result.elapsed_s = max(0.0, self._now() - wave_started)

        budget = _Budget(
            data, limits, self._now, self._sleeper, sleep_max=self.sleep_max, round_wait_max=self.round_wait_max
        )
        # ---- 对象集 (objects, observing, unmatched) 已由 _refresh_locked 波前现算并传入
        #(§2.2 提级, 计划 26-10-05-0555): 这里不再现算 —— 杜绝双跑现算与双回炉;
        # trusted_done / _run_pages / _finish_wave 的消费口径不变。
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
                # wave_ts **不跨波继承**(2026-10-03 修 C1): 原 `prev.wave_ts if prev.ok else 0.0`
                # 让连续 ok 档的 wave_ts 永停在进程内首次成功波(每波只在本档取到首页时置一次,
                # 见下方 `if st.wave_ts <= 0`), 违背 model.py:319「本档最近一波完成取的时刻」,
                # 并让 _absence_proven_all 的新鲜度闸(anchor.added_on > st.wave_ts)用陈旧基准 ⇒
                # 近几天新加本地种子拿不到「未列出」批量放行(方向保守不误放行, 但违背字段语义)。
                # 置 0 = 本波重算; 真正的时刻由本波首次取到该档首页时写入。
                wave_ts=0.0,
            )
        pages_left = max(1, int(self.global_conf.max_pages_per_wave))

        def _abort_wave() -> None:
            """波级让位收尾单点(§3.3): 盖时间戳 → 记拉取历史 → 落盘; 三处异常分支共用。"""
            _stamp_elapsed()
            self._append_history(
                site, data, kind="wave", trigger=trigger, result=result, lanes=lane_states, notes=wave.notes
            )
            self._persist_step(session)

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
            # 拉取历史也不记(§3.3): 瞬态内部事件, 重挂期间会刷屏。
            result.action = ACTION_WAITING
            result.reason = f"本波取数被叫停(正在停止或重挂端点): {e}"
            return
        except HrChannelQuota as e:
            # 扩展侧硬上限(第二道闸)挡下: 不是「取数失败」—— 只让位 + 报一次。
            result.action = ACTION_WAITING
            result.reason = f"扩展侧硬上限挡下(后端频控可能失效), 本波让位: {e}"
            self._warn_ext_quota(site, e)
            _abort_wave()
            return
        except HrChannelUnavailable as e:
            result.action = ACTION_NO_CHANNEL
            result.reason = str(e)
            # 落盘通道痕(计划 26-10-29-0147 W2): 只有「缺站点权限 / 网络层失败」两种新形态写,
            # 让展示层能直接说「扩展未授权该站点」, 而不是让用户从「三档全失败」反推。
            # 必须在 _abort_wave 之前 —— 随同一次 commit 落盘。
            self._note_channel_error(data, e)
            self._warn_no_channel(site, e)
            _abort_wave()
            return
        except HrLoginExpired as e:
            # 登录失效: 只有人去浏览器登录才会好 —— 不算取数失败。痕迹: 1.一条 WARNING 2.
            # 拉取历史 notes。不动任何数据语义(档位截断 + 周期自然重试, §5.2)。
            wave.notes.append(events.login_expired_note(site, e))
            self._warn_login(site, e)
            result.action = ACTION_ERROR
            result.reason = str(e)
            result.alerted = True  # 让位收尾不重算 alerted, 产生处直接置位
            # 扩展回传「登录页」时请求确实发出去了: 间隔基准必须前进, 否则登录态恢复前
            # 每轮 poll(60s)都立即重发, 白烧日额还持续刷站点(这条路径不经过页面级 mark)。
            budget.mark()
            # 让位收尾与 quota / 无通道路径同口径(_abort_wave 单点, issue 26-11-07-0527 #14):
            # 不碰 data.wave.lanes / fetched_at —— 上一波挣得的档位覆盖证据与新鲜度基准
            # 原样保留, 与 fetcher.HrLoginExpired「证据链不会被动」的承诺一致。
            _abort_wave()
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
                result.action = ACTION_WAITING
                result.reason = f"站点要求等待(Retry-After {retry_after:.0f}s): {e}"
                _abort_wave()
                return
            wave.had_error = True
            wave.notes.append(f"页面取数失败: {e}")
            _mark_fetch_failed_lane(lane_states, wave)
            logger.warning(events.fetch_failed(site, 1, 1, str(e)))

        _stamp_elapsed()
        self._finish_wave(site, site_conf, data, session, result, wave, lane_states, unmatched, trigger=trigger)

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
                    # 失败的请求也是真实请求(与波级 Retry-After 分支同口径, issue
                    # 26-11-07-0527 #2): 间隔基准照常前进, 否则连续失败时同波内后续
                    # 档位被即时放行, 零间隔连发真实站点请求, 绕过 min_interval 安全线。
                    budget.mark()
                    # 页面级失败: 该档在失效点截断(之前有效), 其它档独立继续(§3.4 档位独立)
                    wave.had_error = True
                    wave.notes.append(f"档位 {lane} 页面取数失败: {e}")
                    self._warn_parse(site, events.fetch_failed(site, 1, 1, str(e)))
                    if _mark_fetch_failed_lane(lane_states, wave):
                        # 连续多波同档失效的 ERROR 升级(§5.2 / 计划 26-10-29-0147 D8): 此前只有
                        # 「结构失效」(_LaneAbort)那条路接了升级告警, 取数失败这条没接 —— 于是
                        # fail_streak 涨到 58 也没有一句「疑似改版」, 信号全被节流成 INFO。
                        # 通道层不会走到这里(上面那行 except 已把 HrChannelUnavailable 家族 raise 走),
                        # 所以这条天然只覆盖「真·页面层失败」。
                        self._maybe_alert_lane_fail(site, st)
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
                # ---- 站点恢复重置(§5.2 告警口径): 正常内容页到手 = 通道/额度/登录态都通 ——
                # 清三个「已告警过」去重标记, 同类事件再次发生时重新报一次。
                self._reset_warned_on_recovery(site, data)
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
                    self._merge_seen(data, wave, self._now())
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
                    wave.parse_problem = True
                    wave.notes.append(f"档位 {abort.lane} {abort.reason}, 该档证据在此截断")
                    self._warn_parse(site, events.page_changed(site, ACTION_PARTIAL, f"档位 {abort.lane} {abort.reason}"))
                    if _settle_lane(st, failed_detail=abort.reason, truncated_detail=abort.reason, count_failure=True):
                        self._maybe_alert_lane_fail(site, st)
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
        _settle_lane(st, failed_detail=why, truncated_detail=why, count_failure=False)

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
        # ---- 2. 到期段强信号(纯页面信号, 不依赖本地完成时间): 页尾连续 remain==0 达阈值 ----
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

        # ---- 1. 完成时间覆盖(本地推定信号): 最深行早于未定论对象里最早(最老)的可信完成时间 ----
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

        # ---- 3. 本地全集覆盖(本地确认信号): 未对账对象已全部与已见行 infohash 对上且无待回填 ----
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
        """终态行宽泛名称粗配(D1): 仅作**下载触发器**, 定论一律 infohash 精配(§4.5)。

        候选面只含**受管(未排除)**本地种子名 —— 排除种子无对账义务、判定侧已短路, 取回的身份
        无消费方 ⇒ 不该驱动 .torrent 下载(issue 26-10-08-1304)。!A 档不走这里(`_process_rows` 里
        `lane == LANE_SCOPE` 短路在前, 无条件下载)。用**收窄候选集**而非「命中排除名即 return False」:
        粗配宽松(K=12 标题重合即命中), 同一行可能同时命中排除与受管种子, 收窄写法保住受管那侧
        (绝不漏下受管种子身份; 漏管束 > 多一次请求)。
        """
        return any(fuzzy_name_match(name, row.name) for name in wave.local_names_managed)

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
                # 失败的请求也是真实请求(与页面级失败同口径, issue 26-11-07-0527 #2):
                # 一批 pending 下载连续失败时, 间隔基准必须逐个前进, 否则同波内零间隔连发。
                budget.mark()
                self._note_dl_fail(data, tid, self._now())
                result.torrents_failed += 1
                self._persist_step(session)
                logger.warning(f"HR 站点 {site} | tid={tid} 取 .torrent 失败({data.fails[tid].count} 次): {e}")
                continue
            try:
                v1, v2, info = compute_infohashes(blob)
            except ValueError as e:
                self._note_dl_fail(data, tid, self._now())
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
    def _note_dl_fail(data: HrSiteData, tid: int, now: float) -> None:
        fail = data.fails.setdefault(tid, HrDlFail(tid=tid))
        fail.count += 1
        fail.last_ts = now

    def _persist_step(self, session) -> None:
        """增量落盘的统一口(只在正式口径下写; 走查 persist=False 不落盘)。"""
        if session is not None and self.persist:
            session.commit(self._now())

    # ---------- 拉取历史(计划 26-10-04-0312 §3.3: 记录器只搬运现成数据, 无 IO) ----------

    def _append_history(
        self,
        site: str,
        data: HrSiteData,
        *,
        kind: str,
        trigger: str,
        action: str = "",
        reason: str = "",
        reason_kind: str = "",
        result: Optional[HrRefreshResult] = None,
        lanes: Optional[Mapping[str, HrLaneState]] = None,
        notes: Optional[List[str]] = None,
    ) -> None:
        """记一条拉取历史事件进站点数据的 history 表(纯内存: 构造 + prune_history 修剪 + 追加)。

        字段口径: result 非空 = wave 终态事件(全部字段搬运自 HrRefreshResult / lane_states /
        wave.notes, 不新算业务语义); result 为空 = defer / confirm_empty(用显式 action/reason,
        计数字段留 0)。持久化由调用方负责(随既有 commit 或补一次 _persist_step), 本方法无 IO。
        整体 try 保护: 历史是纯观测, 记录失败降级为日志, 绝不外抛进取数主流程。
        """
        try:
            now = self._now()
            states = lanes or {}
            snapshot = [
                {
                    "lane": states[lane].lane,
                    "status": states[lane].status,
                    "pages": states[lane].pages,
                    "rows": states[lane].rows,
                    "detail": states[lane].detail,
                } for lane in FETCH_LANES if lane in states
            ]
            event = HrHistoryEvent(
                ts=now,
                kind=kind,
                trigger=trigger,
                action=result.action if result is not None else action,
                reason=(result.reason if result is not None else reason)[:HISTORY_REASON_MAX],
                reason_kind=result.reason_kind if result is not None else reason_kind,
                pages=result.pages_fetched if result is not None else 0,
                rows=result.entries if result is not None else 0,
                torrents_ok=result.torrents_fetched if result is not None else 0,
                torrents_fail=result.torrents_failed if result is not None else 0,
                # 口径 = 本波签发放行数(releases_signed), 不是放行记录存量总数
                #(verified_count 是 len(data.verified) 存量, 会随累积变大; issue 26-11-07-0527 #13)
                verified=result.releases_signed if result is not None else 0,
                elapsed_s=result.elapsed_s if result is not None else 0.0,
                lanes=snapshot,
                notes=[str(n) for n in (notes or [])][:HISTORY_NOTES_MAX],
                by=(self.store(site).owner or "")[:6],
            )
            data.history = prune_history(data.history, now)
            data.history.append(event)
        except Exception:
            logger.warning(f"HR 站点 {site} | 记录拉取历史失败(降级忽略, 不影响取数): ", exc_info=True)

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
        trigger: str = "auto",
    ) -> None:
        now = self._now()
        self._merge_seen(data, wave, now)
        # ---- 观察期推进(§3.4): 没看到不终结「考察中」; 出口要自身位置被覆盖 ----
        exits = self._advance_observation(data, lane_states, wave, now)
        # ---- 证据防伪(§5.3): 流转守恒 + 零行戳。骤降保护已按 26-09-29 裁决移除: A 只流向
        #      B/C/D, 守恒直接盯 A 档正证据, 总量变化不构成漏 HR 面; 而基线是高水位不回落,
        #      站点合法清账后会把批量签发永久冻死(误触面)。 ----
        total_rows = sum(st.rows for st in lane_states.values())
        retention_ratio, retention_ok = self._retention_check(data, lane_states, wave)
        # 「结构完好的零行波」= **全档有效但清单为空**(计划 26-10-29-0147 D4)。改前只判总量为 0,
        # 于是「一页都没取到」的全档失败波也被算成零行 —— 它随后把 WebUI 引向
        # `--hr-confirm-empty` 人工对账(2026-10-28 实报: 12h 里一直在说「结构完好但清单为 0」)。
        # 有档没取到, 这一波就**没资格**判定「清单为空」: 释放闸门本就先要求 all(st.ok),
        # 故收紧后不会误放行, 只让展示与告警不再撒谎。
        zero_rows = total_rows == 0 and all(st.ok for st in lane_states.values())
        if total_rows > 0:
            data.empty_confirmed_at = 0.0  # 清单再现任何非零行 → 确认戳自动失效(§5.3)
        # ---- 失效波数清零(model.py「干净波清零」口径): 「连续失效」只跨失效波延续 ——
        #      本波跑通的档不背历史计数。既有实现从未清零, 恢复后单次失效会把陈旧波数
        #      一并计入, ERROR 升级虚报「已连续 N 波」。失效波自身(非 ok)不清, 照常累加。 ----
        for st in lane_states.values():
            if st.ok:
                st.fail_streak = 0
        # ---- 计数对平记账(计划 26-09-29-2036 §2.2/§2.4): 声明落档 + mismatch 定界 ----
        # mismatch 只在「本波承认了全深度」的档上成立; 截断/1.3.停翻波 rows<claim 是预期差值
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
            notes=" ; ".join(wave.notes),
        )
        data.fetched_at = now
        any_ok = any(st.ok for st in lane_states.values())
        # 复用窗(计划 26-09-30-0240): 时长 = min(reuse_window, 拉取间隔), clamp 保证新鲜窗永不把
        # 节奏拖过拉取间隔(拉取间隔是硬节奏)。有效波才设窗; 全档失败无新数据可复用 → 不设窗
        # (下一个 poll 节拍即可重试 —— 失败处置 = 档位截断 + 周期自然重试, §5.2)
        data.expires_at = now + min(self.global_conf.reuse_window, site_conf.refresh_interval) if any_ok else 0.0
        result.entries = len(data.index)
        result.verified_count = len(data.verified)
        result.releases_signed = signed + exits
        result.lane_texts = _lanes_summary_from(lane_states)
        notes = list(wave.notes)
        # `not wave.had_error` 是判据修正之外的第二道守卫(D4): 即便哪天判据再被改宽, 有取数
        # 失败的波也不许自称「结构完好」——「结构」根本没被看到过。
        if zero_rows and not confirmed_empty and not wave.had_error:
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
        result.reason = " ; ".join(notes)
        result.snapshot = data
        # 拉取历史(计划 26-10-04-0312 §3.3): 波终态事件, 随下方既有 commit 落盘
        self._append_history(
            site, data, kind="wave", trigger=trigger, result=result, lanes=lane_states, notes=wave.notes
        )
        if self.persist:
            status = session.commit(now)
            result.persisted = status == "written"
            if status == "readonly":
                result.reason = (result.reason + " ; " if result.reason else "") + "锁自检失败, 未写盘(只读退化)"
        else:
            result.reason = (result.reason + " ; " if result.reason else "") + "只读模式, 未写盘"

    @staticmethod
    def _merge_seen(data: HrSiteData, wave: _WaveContext, now: float) -> None:
        """本波已见行合并进索引: 更新字段, 保留 first_seen 与已回填的 infohash。

        last_seen 在此刷新(issue 26-10-01-2335): 「最近一次在站点清单见到」= 合并进索引的
        时刻; 条目退役(终态冻结/观察期出口/换 tid 接管)后不再进入本口, last_seen 冻结在
        最后一次见到的时刻 —— 即 INDEX_RETENTION 陈旧淘汰的计时起点。恒 0 是修复前的
        存量条目, 淘汰条件视为未知不淘汰。
        """
        for tid, row in wave.seen.items():
            old = data.index.get(tid)
            row.first_seen = (old.first_seen if old is not None else 0.0) or row.first_seen or now
            row.last_seen = now
            data.index[tid] = row

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
            if not _lane_covers_done(st, entry.done_epoch):
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
    def _advance_observation(data: HrSiteData, lane_states, wave: _WaveContext, now: float) -> int:
        """失踪观察期状态机(§3.4): 上波命中考察中、本波未重见的种子:
        - 本波重见(已在行处理清零 streak) → 按档位定论;
        - 未重见且自身位置被本波覆盖(每档都证明) → streak + 1;
          连续 MISSING_GRACE_WAVES 波 ⇒ 判「移出」放行(条目退役 + 放行记录);
        - 位置未被覆盖 → streak 冻结(维持管束)。与批量防伪解耦(22:38 定稿)。"""
        exits = 0
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
        """覆盖对象集现算(§4.2): 未对账 ∪ 考察中; 终态/已放行/超额(≥3×)/HR 排除 不出对象集。

        返回 (objects 全部对象, observing 考察中对象(观察期机器管), unmatched 未对账对象)。
        锚点漂移(本机重下)在这里把旧放行作废 —— 「回炉」(§3.2 行 3 机制保留)。
        !第四档「HR 排除」(计划 26-10-08-1249 方案 B): 命中排除表的种子无对账义务 ⇒ 不进对象集
        (否则对象集恒非空、稳态降频永不生效, 实报 2026-10-08)。但**只在这里跳过** —— 命中识别
        用的 `local_hashes` 由 `_WaveContext` 从**全量锚点**构建, 不受影响(名称候选面另行收窄为
        受管集, 见 `_row_looks_local` / issue 26-10-08-1304)。
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
            if anchor.excluded:
                # HR 排除(第四档): 判定侧已短路, 无对账义务 ⇒ 不进对象集(计划 26-10-08-1249 方案 B)。
                # 放在漂移回炉之前 ⇒ 排除种子的放行记录不被锚点漂移作废; 撤销排除后重新进本循环,
                # 漂移检查随之恢复(不产生不可逆残留)。命中识别不受影响(见 docstring)。
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

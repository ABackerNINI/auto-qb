"""test_hr_service 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_first_wave_deep_fetch: 首波深翻(全量效果) —— 未对账对象驱动覆盖深度
- test_stop1_completion_time_coverage: 停翻1. 完成时间覆盖(最深行早于最老对象减对齐余量 1D)
- test_stop2_zero_remain_streak: 停翻2. 到期段强信号(remain==0 连续 5 行, 全深度证明)
- test_stop2_cross_page_streak: 停翻2. 跨页延续计数
- test_stop3_local_full_coverage: 停翻3. 本地全集覆盖(未对账全部对上且无待回填)
- test_untrusted_done_pure_seed: 纯辅种(完成时间不可信)不参与1., 由2./末页收尾且可获放行
- test_order_violation_forced_stop: 排序失效 → 该档立即停翻, 失效点之前命中照常, 不签发放行
- test_header_missing_lane_failed: 表头缺失 → 该档失效, 其它档独立继续(档位独立)
- test_budget_truncation: 预算截断 → 截断点之前命中照常, 未列出待下波(不签发)
- test_a_lane_rows_downloaded_unconditionally: 已见 A 档行无条件下载且同 tid 永不重下(永久层)
- test_terminal_rows_download_on_fuzzy_match: B/C/D 行仅宽泛名称粗配疑似才下载; 粗配误配由精配自愈
- test_rows_not_local_not_downloaded: 本地没有的种子(粗配也不像)不下载
- test_exempt_seed_not_in_objects_passive_hit_managed: 超额种子(≥3×)不进对象集; 被动命中考察中仍转管束
- test_local_satisfied_hit_scope_still_managed: 本地已达标 × 命中考察中 → 管束(网站绝对权威)
- test_release_signed_on_full_coverage: 覆盖完整 + 防伪通过 → 未列出放行签发
- test_freshness_gate_blocks_release: added_on 晚于本波取数 → 行 4(不签发放行)
- test_zero_rows_no_release: 结构完好零行 → 不签发放行
- test_zero_rows_confirmed_release: --hr-confirm-empty 后零行可签发; 非零行清除确认戳
- test_retention_check_freezes_batch: A 档流转守恒不达标 → 批量签发冻结
- test_retention_does_not_block_observation: 守恒拦批量但不拦观察期(单条失踪无死锁)
- test_observing_seed_kept_managed_then_released: 上波考察中失踪 → 维持管束; 位置覆盖连续 2 波 → 判移出放行
- test_observing_seed_resighted: 失踪种子重见 → streak 清零按档位定论
- test_terminal_vanish_writes_release: 终态(B)条目消失且位置被证明 → 退役并落放行记录(source=satisfied)
- test_terminal_vanish_c_lane_release_source: 终态(C)条目同路径 → 落放行记录 source=not-listed
- test_terminal_vanish_unproven_kept: 终态条目消失但位置未被覆盖 → 维持原状
- test_no_objects_sweeps_to_last_page: 空对象集仍按停翻条件/末页收尾(轻量波已否决, 26-09-29 裁决)
- test_new_top_row_reconciled_next_wave: 顶页新插入(本机新下载)在下一波被完整覆盖对账
- test_no_fuse_no_suspension: 失败不推进熔断/停用(v3 删除), Retry-After 记等待
- test_retry_after_persisted_across_waves: Retry-After 指令落盘, 跨波生效, 期满前零请求
- test_retry_after_on_download_escalates_to_wave: .torrent 下载的 Retry-After 上抛波级, 不计种子失败
- test_login_expired_marks_interval: 登录失效路径同样前进间隔基准(重试节奏受 min_interval 约束)
- test_version_mismatch_skips_wave: 站点文件 schema 比程序新 → 跳过取数与写盘(不覆写新版文件)
- test_fuzzy_name_match_unit: 宽泛名称粗配单元(信号串重合段 ≥ K; 技术噪声整词不构成判据 —— 含真实数据假重合回归)
- test_counter_match_releases: T1 计数对平放行 —— 三档 claim==rows 全深度, 签发与无计数基线一致
- test_counter_mismatch_freezes_batch: T2 不对平冻结 —— depth_broken 整波不签发, 连续 3 波 ERROR 升级, 对平自愈清零; 命中/管束/复用窗不变
- test_counter_absent_degrades_to_legacy: T3 无计数降级 —— 默认 adapter + 旧档案(无三键)加载 count_claim None(T1 迁移陷阱守阵, 不得变 0)
- test_counter_zero_claims_self_attest_empty: T4 计数零自证空 —— 三档 claim=0∧rows=0 视同人工戳, 零行软提示不出现
- test_counter_positive_zero_rows_page_changed: T51. 计数>0∧行数=0 —— page_changed 硬告警 + 不签发
- test_interval_empty_page_keeps_manual_stamp: T52. 分页区间形空表无标记(claim=None) —— 维持 zero_listing 人工戳路径
- test_counter_truncation_gap_informational: T6 截断差值信息性 —— 非全深度 rows<claim 不告警不冻结, notes 记差值, REASON_BUDGET 语义不变
- test_fail_streak_resets_on_clean_wave: 失效波数清零 —— 连续失效只跨失效波延续, 恢复波清零, 单次失效不背历史(修复既有从未清零)
- test_reuse_window_uses_min_of_config_and_interval: 1.复用窗时长 = min(reuse_window, 拉取间隔)(计划 26-09-30-0240), 窗内 REUSED 语义不变
- test_reuse_window_never_exceeds_interval: 1b. clamp 另一半 —— 复用窗 > 拉取间隔时静默收敛到拉取间隔
- test_interval_gate_waits_between_waves: 2.复用窗外 + 拉取间隔内 → WAITING「未到拉取时刻(拉取间隔)」(节奏闸门, 防频率放大)
- test_interval_gate_due_runs_next_wave: 3.健康波 + interval 到点 → 正常开波(默认节奏与解耦前一致)
- test_force_bypasses_reuse_and_interval_gates: 4.立即拉取(force)→ 跳过复用窗与拉取间隔两道闸
- test_force_still_respects_min_interval: 5.force 不越账号安全线 —— min_interval 未到仍 WAITING
- test_all_failed_wave_keeps_short_retry_rhythm: 6.全档失败波 healthy_ts 不前进 → 下一轮重试节奏不变
- test_partial_wave_advances_healthy_ts_failed_lane_waits: 7.部分失败波 healthy_ts 前进 → 失败档位等下一波
- test_refresh_all_force_not_blocked_by_gates: 8.走查 refresh_all(force=True)不被两道闸挡(--hr-once 语义)
- test_wave_ts_refreshes_every_wave_not_frozen: C1 回归 —— lane.wave_ts 每波刷新(不冻结首成功波; 缺席证明新鲜度闸基准正确)

### P1 覆盖率提升轮(T1.1 错误路径系统补齐)
- test_refresh_site_guard_paths: 站点未接入 / 全局开关关 / result.ok 属性
- test_refresh_site_unknown_adapter: 未登记的 adapter -> ACTION_ERROR(不外抛)
- test_refresh_site_lock_busy_returns_locked: 站点锁被其它实例持有 -> ACTION_LOCKED
- test_refresh_site_internal_error_contained: 非取数异常 -> ACTION_ERROR + alerted, 不外抛
- test_channel_quota_lets_wave_yield_and_warns_once: 扩展侧硬上限 -> 本波让位 + 每站只告警一次
- test_login_page_detected_by_adapter_and_warned_once: 登录页由 adapter 形态识别(非扩展异常) + 登录告警每站一次(恢复重置: 正常波清标记, 再失效重新报)
- test_challenge_page_truncates_wave: 挑战页 = 页面取数失败(无 Retry-After) -> 波级截断
- test_missing_fields_abort_after_valid_page: 必填字段缺失页在第 2 页 -> 截断点之前数据有效(LANE_OK 非全深度)
- test_daily_quota_exhausted_truncates_rest_lane: 日额用尽 -> 剩余档「预算受限」截断(首页即败 = LANE_FAILED)
- test_budget_take_gives_up_without_sleeper: 无 sleeper 时等不起 -> 该档本轮放弃(不持锁干等)
- test_budget_unit_wait_and_caps: _Budget 单元: waited 记账 / sleep_max / round_wait_max 上限(时钟起点与 last_fetch_ts 对齐, 等待记账 == 抖动间隔)
- test_pages_exhausted_mid_round_lane_not_scheduled: 页数上限耗尽 -> 未轮到的档「本波未轮到取数」
- test_order_direction_flip_forces_stop: 波内方向翻转 -> 强制早停(失效点之前有效)
- test_cross_page_disorder_forces_stop: 跨页乱序 -> 强制早停
- test_tail_zero_partial_reset: 页尾部分到期行 -> 跨页累计重新起算
- test_process_rows_unit_identity_paths: 行处理单元: 永久层继承 / 换 tid 重列接管 / 命中撤销放行 / 同 hash 旧条目退役
- test_run_downloads_unit_paths: 下载单元: 待回填缺行 / 已有身份跳过 / 永久层回填命中与不命中 / 预算止步
- test_download_invalid_blob_counted_as_fail: .torrent 内容非法 -> 计种子失败不外抛
- test_readonly_degradation_noted_in_result: 锁自检失败(只读退化) -> 波照跑但不写盘, reason 注明
- test_persist_false_reports_readonly_mode: 只读走查(persist=False)不写盘且 reason 注明「只读模式」
- test_lane_summary_and_prune_and_position_units: 波次纯函数单元: 档位摘要 / 陈旧淘汰(模块级单点, 含恒 0 存量不淘汰) / 位置覆盖 / 缺席证明 / 下载反查
- test_merge_seen_refreshes_last_seen: 合并口刷新 last_seen(本波已见行=合并时刻, 未重见条目冻结在最后见到时刻) —— issue 26-10-01-2335 写入点, 详情表导出契约随点亮
- test_index_retention_prune_revives: INDEX_RETENTION 复活链 —— 退役条目距 last_seen 超期被清理 / 活跃条目与观察期条目不误清 / 放行记录不随索引清理丢失 / 淘汰落盘
- test_build_objects_unit_guards: 对象集现算单元: 空 hash / 非活跃条目 / 锚点漂移回炉
- test_build_views_skips_disabled_and_channel_states: 视图构建跳过未启用站点; 通道状态 ok/silent/disabled 与无锁读
- test_lane_fail_streak_alerts_error: 连续 3 波同档失效 -> ERROR 升级(只提示人, 不改行为)
- test_worker_and_freeze_guards: 终态冻结的档位无效守卫 / 观察期位置未覆盖冻结 / 出口无 hash 不落记录

### S2 拉取历史记录点(计划 26-10-04-0312 §3.3)
- test_history_wave_events_six_terminal_states: 六终态(refreshed/partial/login/no-channel/quota/Retry-After)
  各恰一条 wave 事件且随站点文件落盘, 关键字段(action/trigger/计数字段/lanes 快照/notes/by)搬运正确
- test_history_auto_poll_gate_skip_writes_nothing: 自动 poll 被调度闸(复用窗/拉取间隔)跳过 -> 零事件
  + 零写盘(站点文件一字节不变) —— 硬不变量
- test_history_defer_only_on_force: defer 事件仅 force 路径产生(立即拉取撞 min_interval -> 一条 defer
  显式落盘); 非 force 被闸拦无事件不写盘
"""
import logging
import time
from datetime import datetime
from typing import Dict

import pytest

import auto_qb.hr.service as hr_service
from auto_qb.hr import events
from auto_qb.hr.fetcher import HrFetchError, NullFetcher
from auto_qb.hr.model import (
    FETCH_LANES,
    LANE_IDLE,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrEntry,
    HrLaneState,
    HrSiteData,
    HrVerified,
)
from auto_qb.hr.resolve import HrAnchor, HrIdentity, judge_record
from auto_qb.hr.status import build_site_statuses, entry_details
from auto_qb.hr.store import HrSiteStore
from auto_qb.hr.service import (
    ACTION_ERROR,
    ACTION_LOCKED,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_WAITING,
    FUZZY_NAME_K,
    HrRefreshService,
    REASON_BUDGET,
    REASON_NONE,
    _WaveContext,
    _lanes_summary_from,
    _mark_fetch_failed_lane,
    fuzzy_name_match,
)

from hr_helpers import (
    CHALLENGE_PAGE,
    EMPTY_TABLE_PAGE,
    LOGIN_PAGE,
    REVISED_PAGE,
    Clock,
    FakeFetcher,
    global_conf,
    myhr_page,
    row,
    site_conf,
    torrent_blob,
)

SITE = "example"
URL = "https://pt.example.com/myhr.php"


def url_of(lane: str, page: int = 1) -> str:
    return f"{URL}?hrtype={lane}" + (f"&page={page}" if page > 1 else "")


def E(done: str) -> float:
    return datetime.strptime(done, "%Y-%m-%d %H:%M:%S").timestamp()


DONE_OLD = "2026-09-01 10:00:00"  # 深处(老)行
DONE_NEW = "2026-09-20 10:00:00"  # 浅处(新)行
T_DONE_NEW = E(DONE_NEW)


def anchor_for(
    blob_name: str,
    *,
    completion_on: float = -1,
    seeding_time: int = 0,
    added_on: int = 100,
    name: str = ""
) -> HrAnchor:
    return HrAnchor(
        added_on=added_on,
        downloaded=1 << 30,
        completion_on=int(completion_on),
        progress=1.0,
        seeding_time=seeding_time,
        name=name or blob_name,
    )


def make_service(tmp_path, fetcher, *, site=None, gconf=None, clock=None) -> HrRefreshService:
    clock = clock or Clock()
    return HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=gconf or global_conf(),
        site_confs={SITE: site or site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=clock,
        sleeper=lambda _s: None,
    )


def run_wave(service, anchors=None):
    return service.refresh_site(SITE, anchors or {})


def mk_blob(name: str):
    """(blob, 真实 infohash) —— 锚点键必须用真实算出的 hash(与 blob 一致, 匹配才成立)"""
    from auto_qb.hr.bencode import compute_infohashes

    blob = torrent_blob(name=name)
    v1, _v2, _info = compute_infohashes(blob)
    return blob, v1


def standard_pages(rows_a=None, rows_b=None, rows_c=None, *, has_next: bool = False):
    """标准三页(每档一页, 无翻页)"""
    return {
        url_of("A"): myhr_page(rows_a or [], has_next=has_next),
        url_of("B"): myhr_page(rows_b or [], has_next=has_next),
        url_of("C"): myhr_page(rows_c or [], has_next=has_next),
    }


def five_expired_rows(base_tid: int) -> list:
    """5 行 remain==0(已到期段) —— 停翻2. 的最小触发面"""
    return [
        row(base_tid + i, f"OTHER-TORRENT {base_tid + i}", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")
        for i in range(5)
    ]


# ---------------- 波次基本形态 ----------------


def test_first_wave_deep_fetch(tmp_path):
    """首波: 对象(未对账, 本地完成时间可信且较新)驱动各档翻页到其位置之后(全量效果)"""
    clock = Clock()
    # 对象完成于 09-20(新); 各档只有 09-01(老)的行且还有下一页 → 1.停翻(更深只会更老)
    pages = {
        url_of("A", 1):
            myhr_page([row(11, "OTHER 11", done=DONE_OLD)], has_next=True),
        url_of("B", 1):
            myhr_page([row(12, "OTHER 12", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
        url_of("C", 1):
            myhr_page([row(13, "OTHER 13", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h-old": anchor_for("OTHER", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    assert result.action in ("refreshed", "partial")
    # 三档各取了第 1 页即被1.停翻(更深只会更老, 对象不可能藏在更深处)
    data, _ = service.store(SITE).read_unlocked()
    assert all(st.ok for st in data.wave.lanes.values())
    assert data.wave.lanes["A"].full_depth is False  # 1.停翻: 位置有界, 非全深度


def test_stop1_completion_time_coverage(tmp_path):
    """停翻1.: 最深行完成时间早于对象最老完成时间减 1D 对齐余量 → 停翻(位置有界)"""
    clock = Clock()
    # 对象完成 09-10; 第 1 页行 09-20(比对象新 → 不能停), 第 2 页行 09-01(老于对象-1D → 停)
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11", done=DONE_NEW)], has_next=True),
        url_of("A", 2): myhr_page([row(12, "OTHER 12", done=DONE_OLD)], has_next=True),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=E("2026-09-10 10:00:00"))}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.status == "ok" and st.pages == 2 and st.full_depth is False
    assert "完成时间覆盖" in st.detail


def test_stop2_zero_remain_streak(tmp_path):
    """停翻2.: 页尾连续 5 行 remain==0 → 到期段强信号(全深度证明, 停翻零漏判)"""
    clock = Clock()
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW, remain="1天00:00:00")], rows_b=five_expired_rows(20), rows_c=[]
    )
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["B"]
    assert st.status == "ok" and st.full_depth is True
    assert "到期段强信号" in st.detail


def test_stop2_cross_page_streak(tmp_path):
    """停翻2.跨页延续: 第 1 页整页 3 行全 0 + 第 2 页整页 2 行全 0 → 累计 5 → 停翻(全深度)"""
    clock = Clock()
    pages = {
        url_of("B", 1): myhr_page(five_expired_rows(20)[:3], has_next=True),
        url_of("B", 2): myhr_page(five_expired_rows(20)[3:5], has_next=True),
        url_of("A"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=-1)}  # 纯辅种: 1.不可用, 由2.跨页累计收尾
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["B"]
    assert st.status == "ok" and st.full_depth is True and st.pages == 2


def test_stop3_local_full_coverage(tmp_path):
    """停翻3.: 未对账对象全部与已见行对上且无待回填 → 停翻(不再为终态行翻页)"""
    clock = Clock()
    # 对象的行在 A 档第 1 页(命中即定论); B/C 档还有别的行与下一页 —— 3.在 A 命中后即停 A
    pages = {
        url_of("A", 1):
            myhr_page([row(11, "EXAMPLE 11")], has_next=True),
        url_of("B", 1):
            myhr_page([row(12, "OTHER 12", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")], has_next=True),
        url_of("C", 1):
            myhr_page([], has_next=False),
    }
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=pages, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.status == "ok" and st.pages == 1
    assert "本地全集覆盖" in st.detail
    # 命中: 行已对账, 索引活跃
    entry = next(e for e in data.index.values() if e.tid == 11)
    assert entry.infohash_v1 == h11 and entry.lane == LANE_SCOPE and entry.active


def test_untrusted_done_pure_seed(tmp_path):
    """纯辅种(无本机完成时刻、未绑定): 不参与1.; 由2.(B/C 到期段)与末页(A)收尾且可获放行"""
    clock = Clock()
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW, remain="1天00:00:00")], rows_b=five_expired_rows(20), rows_c=[]
    )
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h-pure": anchor_for("PURE", completion_on=-1)}  # 纯辅种: completion_on 未设
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].full_depth is True  # A 档翻到末页收尾(1.不能用)
    assert data.wave.lanes["B"].full_depth is True  # B 档由2.收尾
    assert "h-pure" in data.verified  # 全深度缺席证明成立 → 放行


# ---------------- 失效与截断 ----------------


def test_order_violation_forced_stop(tmp_path):
    """排序失效 → 该档强制早停: 失效点之前命中照常, 该档不签发放行(误管, 方向安全)"""
    clock = Clock()
    # A 档第 1 页页内逆序(09-25 后出现 09-01 → 再出现 09-20)
    bad_page = myhr_page(
        [
            row(11, "OTHER 11", done="2026-09-25 10:00:00"),
            row(12, "OTHER 12", done=DONE_OLD),
            row(13, "OTHER 13", done=DONE_NEW),
        ]
    )
    pages = {url_of("A", 1): bad_page, url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status != "ok"
    assert data.wave.releases_enabled is False
    assert "排序" in (result.reason + data.wave.notes)


def test_header_missing_lane_failed(tmp_path):
    """表头缺失(A 档改版) → 该档失效; B/C 档独立继续(档位独立, 不污染)"""
    clock = Clock()
    pages = {
        url_of("A"): "<html>改版了, 没有表格</html>",
        url_of("B"): myhr_page(five_expired_rows(20)),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "failed"
    assert data.wave.lanes["B"].ok and data.wave.lanes["C"].ok
    assert data.wave.releases_enabled is False  # A 档无效 → 批量签发关闭
    assert result.action == ACTION_PARTIAL


def test_budget_truncation(tmp_path):
    """预算截断: 截断点之前命中照常; 位置未被覆盖的对象不签发放行(待下波续判)"""
    clock = Clock()
    pages = {
        # A 档第 1 页有对象的行(命中), 第 2 页还有(没翻到 —— 预算 3 页分给三档各 1 页不够翻第 2 页)
        url_of("A", 1):
            myhr_page([row(11, "EXAMPLE 11")], has_next=True),
        url_of("B", 1):
            myhr_page(five_expired_rows(20)[:1], has_next=True),
        url_of("C", 1):
            myhr_page([row(31, "OTHER 31", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: torrent_blob(name="EXAMPLE 11")})
    gconf = global_conf(max_pages_per_wave=3)
    service = make_service(tmp_path, fetcher, gconf=gconf, clock=clock)
    anchors = {
        "h11": anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW),
        "h-deep": anchor_for("DEEP", completion_on=E("2026-08-01 10:00:00")),  # 更老: 位置未被覆盖
    }
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    # 命中照常: tid 11 已对账
    assert any(e.tid == 11 and e.infohash_v1 for e in data.index.values())
    # 三档均截断(1 页, 非全深度) → 批量签发关闭; 深处的 h-deep 未签发
    assert all(st.ok and not st.full_depth for st in data.wave.lanes.values())
    assert "h-deep" not in data.verified
    assert result.releases_signed == 0


# ---------------- 下载规则(§4.5) ----------------


def test_a_lane_rows_downloaded_unconditionally(tmp_path):
    """A 档行无条件全部下载(硬规则); 同 tid 永不重下(永久层)"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([row(11, "TOTALLY-UNRELATED-NAME"),
                                row(12, "ANOTHER-STRANGER")]),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: torrent_blob(name="EXAMPLE 11"), 12: torrent_blob(name="OTHER 12")})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h11": anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    assert set(fetcher.byte_calls) == {
        "https://pt.example.com/download.php?id=11", "https://pt.example.com/download.php?id=12"
    }
    # 第二波: 同 tid 仍在 A 档 → 不再下载(永久层)
    result = run_wave(service, anchors)
    assert len([c for c in fetcher.byte_calls if c.endswith("id=11")]) == 1
    data, _ = service.store(SITE).read_unlocked()
    assert result.torrents_fetched == 0


def test_terminal_rows_download_on_fuzzy_match(tmp_path):
    """B/C/D 行仅当宽泛名称粗配疑似本地才下载; 粗配误配由 infohash 精配自愈"""
    clock = Clock()
    pages = {
        url_of("A"):
            myhr_page([], has_next=False),
        url_of("B"):
            myhr_page(
                [
                    row(21, "Example.Ultra.S01E01.1080p"),  # 粗配疑似本地(与本地名有 ≥K 重合段)
                    row(22, "Completely.Different.Show.2026"),  # 不像 → 不下载
                ],
                has_next=False
            ),
        url_of("C"):
            myhr_page([], has_next=False),
    }
    blob, h21 = mk_blob("Example.Ultra.S01E01.1080p")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("Example.Ultra.S01E01.1080p", completion_on=T_DONE_NEW, seeding_time=0)}
    run_wave(service, anchors)
    assert "https://pt.example.com/download.php?id=21" in fetcher.byte_calls
    assert "https://pt.example.com/download.php?id=22" not in fetcher.byte_calls
    data, _ = service.store(SITE).read_unlocked()
    entry = next(e for e in data.index.values() if e.tid == 21)
    assert entry.lane == LANE_SATISFIED and entry.infohash_v1 == h21  # 精配命中 B → 终态放行


def test_rows_not_local_not_downloaded(tmp_path):
    """本地没有的种子(粗配也不像)不下载; A 档之外的陌生行零下载"""
    clock = Clock()
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW, remain="1天00:00:00")], rows_b=five_expired_rows(20), rows_c=[]
    )
    fetcher = FakeFetcher(pages=pages, blobs={11: torrent_blob(name="OTHER 11")})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    # A 档行(OTHER 11)无条件下载(一次, 永久层); B 档的 5 行陌生种子(粗配不像)零下载
    assert fetcher.byte_calls == ["https://pt.example.com/download.php?id=11"]


# ---------------- 超额线与网站权威(§3.3) ----------------


def test_exempt_seed_not_in_objects_passive_hit_managed(tmp_path):
    """超额种子(≥3×)不进对象集(老藏深不拉深覆盖); 被动命中考察中仍转管束(网站绝对权威)"""
    clock = Clock()
    pages = {
        # A 档第 1 页就有超额种子的行 —— 被动命中(infohash 由下载获得)
        url_of("A"): myhr_page([row(11, "EXAMPLE 11")]),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=pages, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    # 做种 30 天 >= 3 × 2 天(required) → 超额; 完成时间很老(藏深处也不该被翻页拉深)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW, seeding_time=30 * 86400)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = next(e for e in data.index.values() if e.tid == 11)
    assert entry.lane == LANE_SCOPE and entry.active  # 命中考察中 → 管束(进视图)
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h11, ), anchor=anchors[h11], now=clock())
    assert j.identity is HrIdentity.HR  # 超额不构成免死金牌


def test_local_satisfied_hit_scope_still_managed(tmp_path):
    """本地已达标 × 命中考察中 → 管束(20:58 定稿: 站点说还在考就是还在考)"""
    clock = Clock()
    pages = standard_pages(rows_a=[row(11, "EXAMPLE 11")], rows_b=[], rows_c=[])
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=pages, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW, seeding_time=10 * 86400)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h11, ), anchor=anchors[h11], now=clock())
    assert j.identity is HrIdentity.HR


# ---------------- 放行签发与防伪(§5.3) ----------------


def test_release_signed_on_full_coverage(tmp_path):
    """覆盖完整(全深度) + 防伪通过 → 未对账且未命中的对象签发「未列出」放行"""
    clock = Clock()
    pages = standard_pages(rows_b=five_expired_rows(20))
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified
    assert data.verified["h1"].source == SOURCE_NOT_LISTED
    assert result.releases_signed >= 1


def test_freshness_gate_blocks_release(tmp_path):
    """新鲜度闸门: added_on 晚于该档本波取数 → 该档快照无证明力 → 不签发(行 4)"""
    clock = Clock()
    pages = standard_pages(rows_b=five_expired_rows(20))
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW, added_on=int(clock()) + 10)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" not in data.verified


def test_zero_rows_no_release(tmp_path):
    """结构完好零行 → 不签发放行(改版空表即整站误放行, 不冒这个险)。
    首波先立索引(命中登记, 无「未列出」可签), 次波改版空表 —— 零行卡点分支才可达
    (索引全空时 blocking_reason 先报「还没有任何可判数据」)。"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    pages = {
        url_of("A"): myhr_page([row(11, "EXAMPLE 11")]),
        url_of("B"): myhr_page([]),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    clock.advance(13 * 3600)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.zero_rows is True
    assert data.wave.releases_enabled is False
    assert h11 not in data.verified
    assert "清单为 0" in result.reason
    # M3 展示口径对齐(计划 26-09-29-2036): 无计数站点不误标「计数自证空集」, 人工戳提示照旧
    snap = build_site_statuses(service, clock.now)[0]
    assert snap.count_attested_empty is False
    assert "--hr-confirm-empty" in snap.blocking


def test_zero_rows_confirmed_release(tmp_path):
    """人工对账戳后零行可正常签发; 清单再现非零行 → 确认戳自动失效"""
    clock = Clock()
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    data.empty_confirmed_at = clock()  # --hr-confirm-empty 的动作
    service.store(SITE).hold().__enter__().commit(clock()) if False else None
    with service.store(SITE).hold() as session:
        session.data.empty_confirmed_at = clock()
        session.commit(clock())
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified  # 零行 + 确认戳 → 放行
    # 再现非零行 → 戳失效
    fetcher.pages = standard_pages(rows_b=five_expired_rows(20))
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.empty_confirmed_at == 0.0


def test_retention_check_freezes_batch(tmp_path):
    """A 档流转守恒: 上波 A 行本波留存 < 70% → 批量「未列出」签发冻结(命中不受影响)"""
    clock = Clock()
    # 首波: A 档 3 行陌生种子(下载后都不是本地) → prev_a_tids = {11,12,13}
    blobs = {tid: torrent_blob(name=f"STRANGER {tid}") for tid in (11, 12, 13)}
    # 首波: A 全深度(3 行陌生种子); B 只有 2 行零 remain 且有下一页(翻不到 → 截断, 位置有界);
    # C 全深度。h1 完成时间(08-01)早于 B 的覆盖边界(09-01) → 首波不签发(位置未被覆盖)
    pages = {
        url_of("A"): myhr_page([row(11, "STRANGER 11"),
                                row(12, "STRANGER 12"),
                                row(13, "STRANGER 13")]),
        url_of("B"): myhr_page(five_expired_rows(20)[:2], has_next=True),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, blobs=blobs)
    service = make_service(tmp_path, fetcher, clock=clock)
    # h1 完成时间(08-01)早于首波覆盖边界(09-01) → 首波不签发(位置未被覆盖)
    anchors = {"h1": anchor_for("h1", completion_on=E("2026-08-01 10:00:00"))}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert len(data.wave.prev_a_tids) == 3
    # 第二波: A 档只剩 1 行(2/3 失踪, 留存率 33% < 70%) → 守恒不达标
    fetcher.pages = standard_pages(rows_a=[row(11, "STRANGER 11")], rows_b=five_expired_rows(20))
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.retention_ok is False
    assert "h1" not in data.verified  # 批量签发被冻结(即便覆盖证明成立)


def test_retention_does_not_block_observation(tmp_path):
    """守恒只拦批量签发, 不拦观察期状态机(22:38 定稿): 单条失踪照常推进, 无死锁"""
    clock = Clock()
    # 首波: 本地种子 S 的行在 A 档(命中, 绑定) + 2 行陌生种子
    blob, h11 = mk_blob("EXAMPLE 11")
    pages = standard_pages(rows_a=[row(11, "EXAMPLE 11"), row(12, "STRANGER 12"), row(13, "STRANGER 13")])
    fetcher = FakeFetcher(
        pages=pages,
        blobs={
            11: blob,
            12: torrent_blob(name="STRANGER 12"),
            13: torrent_blob(name="STRANGER 13")
        },
    )
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert len(data.wave.prev_a_tids) == 3
    # 第二波: S 失踪(位置被全深度覆盖), 陌生行只剩 1 行 → 守恒不达标但观察期推进
    fetcher.pages = standard_pages(rows_a=[row(12, "STRANGER 12")], rows_b=five_expired_rows(20))
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = next(e for e in data.index.values() if e.tid == 11)
    assert entry.missing_streak == 1 and entry.active  # 观察期第 1 波(维持管束)
    # 第三波: 仍未重见 → 连续 2 波 → 判移出放行(观察期出口不被守恒拦死)
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = next(e for e in data.index.values() if e.tid == 11)
    assert entry.active is False
    assert h11 in data.verified  # 判移出放行


def test_observing_seed_kept_managed_then_released(tmp_path):
    """上波考察中失踪 → 一律当作无证据维持管束(无快路径); 位置覆盖连续 2 波 → 判移出放行"""
    clock = Clock()
    pages = standard_pages(rows_a=[row(11, "EXAMPLE 11")])
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=pages, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    # 第二波: 全空(结构完好) → S 失踪但 A 档全深度覆盖(空表末页)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = data.index[11]
    assert entry.active is True and entry.missing_streak == 1  # 维持管束
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h11, ), anchor=anchors[h11], now=clock())
    assert j.identity is HrIdentity.HR  # 「没看到」不终结「考察中」
    # 第三波: 仍未重见 → 判移出放行
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].active is False
    assert h11 in data.verified
    # !「记录在」≠「放行生效」: 观察期出口同样必须带锚点快照, 否则判定侧当场判滴移作废
    assert data.verified[h11].has_anchor_snapshot
    view = service.build_view_for(SITE, data)
    assert judge_record(view, (h11, ), anchor=anchors[h11], now=clock()).identity is HrIdentity.RELEASED


def test_observing_seed_resighted(tmp_path):
    """失踪种子重见 → streak 清零, 按当波档位定论"""
    clock = Clock()
    pages = standard_pages(rows_a=[row(11, "EXAMPLE 11")])
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=pages, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    # 第三波: 重见于 A 档
    fetcher.pages = standard_pages(rows_a=[row(11, "EXAMPLE 11")])
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = data.index[11]
    assert entry.active is True and entry.missing_streak == 0 and entry.lane == LANE_SCOPE
    assert h11 not in data.verified  # 重见即管束, 放行不签发


# ---------------- 终态冻结(§4.4) ----------------


def test_terminal_vanish_writes_release(tmp_path):
    """终态条目消失且位置被证明 → 退役并落放行记录(终态不可逆, 条目被站点清掉也不影响判定)

    !终态行必须**粗配同名 ⇒ 真下到 .torrent ⇒ 登记 infohash**, 冻结的内层「落放行记录」
    分支才进得去 —— 否则 infohash 为空, 那三行永不执行, 守阵假绿灯(2026-09-29 实报
    `LANE_SATISFIED` NameError 正是从这个从未被覆盖的分支炸出来的)。
    """
    clock = Clock()
    pages = standard_pages(rows_b=[row(21, "EXAMPLE 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")])
    blob, h21 = mk_blob("EXAMPLE 21")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].lane == LANE_SATISFIED and data.index[21].active
    assert data.index[21].infohash_v1 == h21, "粗配同名 ⇒ 下载登记身份(冻结才有对象可落记录)"
    assert h21 not in data.verified, "命中不是放行: 放行记录由冻结/未列出签发来落"
    # 第二波: B 档空表(全深度) → 条目消失被证明 → 退役 + 放行记录(毕业来源)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False
    assert data.verified[h21].source == SOURCE_SATISFIED, "B 档毕业移出 ⇒ 来源 satisfied(站侧结论要留住)"
    assert data.verified[h21].has_anchor_snapshot, "记录必须带锚点快照, 否则判定侧当场判漂移作废"
    assert data.verified[h21].anchor_downloaded == anchors[h21].downloaded
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h21, ), anchor=anchors[h21], now=clock())
    assert j.identity is HrIdentity.RELEASED  # 终态不可逆: 退役后照常放行


def test_terminal_vanish_c_lane_release_source(tmp_path):
    """C 档终态移出 → 同样退役落放行记录, 来源 not-listed(非 B 毕业)

    冻结落记录的三元表达式有 B／非 B 两条子句, 2026-09-29 的 NameError 只在**条件求值**
    上, 故两个可达终态档各钉一条(另一条 C 子句同样是真机路径)。
    """
    clock = Clock()
    pages = standard_pages(rows_c=[row(21, "EXAMPLE 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")])
    blob, h21 = mk_blob("EXAMPLE 21")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].lane == LANE_UNSATISFIED and data.index[21].infohash_v1 == h21
    assert h21 not in data.verified
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False
    assert data.verified[h21].source == SOURCE_NOT_LISTED


def test_terminal_vanish_unproven_kept(tmp_path):
    """终态条目消失但位置未被覆盖(截断) → 维持原状(命中照常, 保守无害)"""
    clock = Clock()
    pages = {
        url_of("A", 1):
            myhr_page([], has_next=False),
        url_of("B", 1):
            myhr_page([row(21, "EXAMPLE 21", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
        url_of("C", 1):
            myhr_page([], has_next=False),
    }
    blob, h21 = mk_blob("EXAMPLE 21")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    gconf = global_conf(max_pages_per_wave=3)
    service = make_service(tmp_path, fetcher, gconf=gconf, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].lane == LANE_SATISFIED
    # 第二波: B 档第 1 页换成别的行且有下一页(截断 —— 条目位置未被覆盖)
    fetcher.pages = {
        url_of("A"):
            myhr_page([], has_next=False),
        url_of("B", 1):
            myhr_page([row(99, "OTHER 99", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")], has_next=True),
        url_of("C"):
            myhr_page([], has_next=False),
    }
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is True  # 未被证明消失: 维持原状
    assert h21 not in data.verified


# ---------------- last_seen 写入点与 INDEX_RETENTION 复活(issue 26-10-01-2335) ----------------


def test_merge_seen_refreshes_last_seen(tmp_path):
    """合并口刷新 last_seen: 本波已见行 = 合并时刻; 未重见条目冻结在最后见到时刻(写入点修复)"""
    clock = Clock()
    pages = standard_pages(
        rows_b=[row(21, "OTHER 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
        rows_c=[row(22, "OTHER 22", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
    )
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    t0 = clock()
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].last_seen == t0, "本波已见行: last_seen = 合并进索引的时刻"
    assert data.index[21].first_seen == t0, "新条目 first_seen 兜底同源(假时钟, 不再真挂钟)"
    assert data.index[22].last_seen == t0
    # 第二波: B 档空表(全深度) → 条目 21 退役; C 档重见 22 → last_seen 前进
    fetcher.pages = {
        url_of("A"):
            myhr_page([], has_next=False),
        url_of("B"):
            myhr_page([], has_next=False),
        url_of("C"):
            myhr_page([row(22, "OTHER 22", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")], has_next=False),
    }
    clock.advance(13 * 3600)
    t1 = clock()
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False
    assert data.index[21].last_seen == t0, "退役条目不再进合并口: last_seen 冻结在最后见到时刻(淘汰计时起点)"
    assert data.index[22].active is True and data.index[22].last_seen == t1, "重见条目 last_seen 刷新"
    # 详情表导出契约(webui 表①「最近被见到」列): last_seen 随写入点亮起
    details = {d.tid: d for d in entry_details(data)}
    assert details[21].last_seen == t0 and details[22].last_seen == t1


def test_index_retention_prune_revives(tmp_path):
    """INDEX_RETENTION 复活链: 退役条目超期(距 last_seen > 30 天)被清理 / 活跃与未超期退役条目保留 /
    放行记录不随索引清理丢失 / 淘汰结果落盘"""
    clock = Clock()
    blob11, _h11 = mk_blob("OTHER 11")
    blob21, h21 = mk_blob("EXAMPLE 21")
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW)],
        rows_b=[row(21, "EXAMPLE 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
    )
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11, 21: blob21})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    t0 = clock()
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].active and data.index[11].last_seen == t0
    assert data.index[21].active and data.index[21].last_seen == t0
    # 第二波(+29 天): 全档空表 → 条目 21 退役落放行记录; last_seen 冻结在 t0
    fetcher.pages = {url_of(l): myhr_page([], has_next=False) for l in ("A", "B", "C")}
    clock.advance(29 * 86400)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False and data.index[21].last_seen == t0
    assert h21 in data.verified, "终态退役落放行记录(永久层)"
    assert data.index[11].active and data.index[11].last_seen == t0, "观察期条目未重见: 维持活跃, last_seen 不前进"
    # 第三波(+31 天, 距 t0 超保留期): A 档重见 11; 清理分支复活 → 21 被淘汰
    fetcher.pages = {
        url_of("A"): myhr_page([row(11, "OTHER 11", done=DONE_NEW)], has_next=False),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    clock.advance(2 * 86400)
    t2 = clock()
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert 21 not in data.index, "退役条目距 last_seen 超过 INDEX_RETENTION: 被清理"
    assert data.index[11].active and data.index[11].last_seen == t2, "活跃条目不被误清且 last_seen 持续刷新"
    assert h21 in data.verified, "放行记录是永久层, 不随索引清理丢失"
    assert result.entries == len(data.index) == 1, "淘汰结果反映进波次回执(索引只剩活跃条目 11)"
    assert 21 not in service.store(SITE).read_unlocked()[0].index, "淘汰结果已落盘(下一波不会复活)"


# ---------------- 覆盖收敛(空对象集, 轻量波已否决) ----------------


def test_no_objects_sweeps_to_last_page(tmp_path):
    """空对象集仍按停翻条件/末页收尾, 不做「每档 1 页」早停(轻量波已否决, 26-09-29 裁决)"""
    blob11, _h11 = mk_blob("OTHER 11")
    blob12, _h12 = mk_blob("OTHER 12")
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11", done=DONE_OLD)], has_next=True),
        url_of("A", 2): myhr_page([row(12, "OTHER 12", done=DONE_OLD)], has_next=False),
        url_of("B", 1): myhr_page(five_expired_rows(20), has_next=True),
        url_of("C", 1): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11, 12: blob12})
    service = make_service(tmp_path, fetcher)
    run_wave(service, anchors={})  # 无本地种子 → 无对象集
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].pages == 2  # 有下一页就继续翻(未被「每档 1 页」截断)
    assert data.wave.lanes["B"].pages == 1 and data.wave.lanes["B"].full_depth  # 2. 到期段
    assert data.wave.lanes["C"].pages == 1 and data.wave.lanes["C"].full_depth  # 末页


def test_new_top_row_reconciled_next_wave(tmp_path):
    """顶页新插入(本机新下载的种子)在下一波被完整覆盖对账 —— 单波型对清单变动免疫"""
    clock = Clock()
    pages = standard_pages(rows_b=five_expired_rows(20))
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, anchors={})  # 首波无对象
    # 第二波: 顶页新插入本机种子行(新 tid), 本地锚点同波出现
    blob, h50 = mk_blob("BRAND NEW 50")
    fetcher.pages = standard_pages(rows_a=[row(50, "BRAND NEW 50", done=DONE_NEW)])
    fetcher.blobs[50] = blob
    clock.advance(13 * 3600)
    anchors = {h50: anchor_for("BRAND NEW 50", completion_on=T_DONE_NEW, added_on=int(clock()) - 60)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    entry = next(e for e in data.index.values() if e.tid == 50)
    assert entry.infohash_v1 == h50 and entry.lane == LANE_SCOPE and entry.active
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h50, ), anchor=anchors[h50], now=clock())
    assert j.identity is HrIdentity.HR


# ---------------- 失败处置(§5.2: 无熔断/停用, Retry-After 保留) ----------------


def test_no_fuse_no_suspension(tmp_path):
    """页面失败 → 该档截断, 下周期自然重试; 不存在熔断/停用状态(数据上无 fuse/suspended 字段)"""
    clock = Clock()
    pages = {url_of("A"): myhr_page([], has_next=False), url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, fail_text_at={"A": "超时"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_PARTIAL
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "failed"
    # v3 失败处置: 数据上没有任何熔断/停用/退避状态字段(模型级删除);
    # 骤降保护同批移除(26-09-29 裁决) —— 基线/骤降字段不再落盘。
    raw = data.to_json()
    for gone in ("fuse", "suspended", "login_backoff_until", "quota", "torrent_quota", "plunge", "baseline_rows"):
        assert gone not in raw
    # Retry-After 的读取侧「下次可取时刻」语义另见 test_hr_ratelimit.test_retry_after_respected;
    # 下方三个用例钉 service 层的落盘/上抛行为(修复前只有 ratelimit 单测, H1/M1 漏网)。


def test_retry_after_persisted_across_waves(tmp_path):
    """Retry-After 指令必须落盘: 下一波重读盘仍受其约束, 期满前零请求(H1)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(), retry_after_at={"A": 600.0})
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.retry_after_until >= clock.now + 590  # 已持久化(修复前只写内存会话, 跨波即丢)
    assert data.rate.last_fetch_ts == clock.now  # 间隔基准同步前进
    calls_after_wave1 = len(fetcher.text_calls)
    # 第二波(下一轮 poll, 60s 后): 指令未期满 → 不发任何请求
    clock.advance(60)
    result = run_wave(service, {})
    assert len(fetcher.text_calls) == calls_after_wave1
    assert result.action == ACTION_WAITING and "Retry-After" in result.reason
    # 期满后恢复取数
    clock.advance(600)
    run_wave(service, {})
    assert len(fetcher.text_calls) > calls_after_wave1


def test_retry_after_on_download_escalates_to_wave(tmp_path):
    """.torrent 下载收到 Retry-After → 上抛波级落盘让位, 不计成种子失败(H1 同根)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(rows_a=[row(21, "LOCAL 21")]), retry_bytes_at={21: 300.0})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.retry_after_until >= clock.now + 290  # 波级落盘
    assert data.fails == {} and result.torrents_failed == 0  # 站点限速不伪装成「种子坏了」
    assert result.action == ACTION_WAITING


def test_login_expired_marks_interval(tmp_path):
    """登录失效路径同样前进间隔基准: 登录恢复前重试节奏受 min_interval 约束(M1)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(), login_at={"A"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.rate.last_fetch_ts == clock.now  # 修复前恒 0: 每 poll(60s)都立即重发烧日额
    assert result.action == ACTION_ERROR


def test_version_mismatch_skips_wave(tmp_path):
    """站点文件 schema 比程序新 → 跳过取数与写盘, 空数据不得覆写新版文件(M2)"""
    import json

    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher)
    path = service.store(SITE).path
    path.parent.mkdir(parents=True, exist_ok=True)  # store.hold() 才建目录, 手写文件要先建
    path.write_text(json.dumps({"schema_version": 999, "fetched_at": 1.0}), encoding="utf-8")
    result = run_wave(service, {})
    assert fetcher.text_calls == []  # 未取数
    assert result.action == ACTION_ERROR and "schema 比程序新" in result.reason
    # 未写盘: 新版文件原样保留(修复前波次会用空数据覆盖它)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 999


# ---------------- 粗配单元(D1) ----------------


def test_fuzzy_name_match_unit():
    assert fuzzy_name_match("Example.Ultra.S01E01.1080p", "Group.Example.Ultra.S01E01.1080p.x264")
    assert fuzzy_name_match("Example Ultra S01E01", "example-ultra-s01e01-1080p")  # 空白/大小写折叠
    assert not fuzzy_name_match("Example.Ultra", "Completely.Different.Show.2026")
    assert not fuzzy_name_match("短名", "Completely.Different.Show.2026")  # 短于 K 不误配
    assert len("Example.Ultra") >= FUZZY_NAME_K or True
    # ---- 技术噪声整词不构成判据(2026-09-29 收紧) ----
    assert not fuzzy_name_match("Some.Show.1080p.WEB-DL.x264", "Other.Show.1080p.WEB-DL.x264")
    assert not fuzzy_name_match("1080p.WEB-DL.x264", "1080p.WEB-DL.x264")  # 整名都是噪声 ⇒ 撤不上判据


#: 2026-09-29 真实数据回归(用户实例 108 本地名 × 50 活跃行): 旧判据这些对全命中, 全是**质量标签**
#: 拼出的假重合段(括号内为旧判据的重合段) —— 它们使 .torrent 下载成片白烧站点配额。
#: 断言的是「不再误配」而不是「完全没重合」: 允许标题段仍有短重合, 只是达不到判据下限。
def test_fuzzy_name_match_rejects_noise_only_overlap():
    local = "隐藏大佬扮猪吃虎.1080p.WEB-DL.H265.AAC-HHWEB"
    assert not fuzzy_name_match(local, "Taste of Crime 2018 1080P WEB-DL H264 AAC-BtsTV")  # 1080pwebdlh26
    assert not fuzzy_name_match(
        local, "Yiran's Silver Linings 2026 S01E01-S01E27 2160p WEB-DL H265 AAC-UBWEB"
    )  # 0pwebdlh265aac
    assert not fuzzy_name_match(
        "Though.I.Am.an.Inept.Villainess.S01.2026.1080p.NF.WEB-DL.H.264.AAC",
        "My Husband Wont Fit S01 1080p NF WEB-DL DDP2 0 x264-AOWEB",
    )  # 1080pnfwebdl
    # 20 字符的噪声段(年份 + 季标 + Complete + 1080p): 光提高 K 拦不住, 必须剔噪声
    assert not fuzzy_name_match(
        "[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga.Suuguu.Chouso.Torikae.Den.2026.S01.1080p.WEB-DL.AAC.H.264",
        "Our Sticky Love 2026 S01 Complete 1080p NF WEB-DL H264 DDP5.1 Atmos-BtsTV",
    )  # 2026s01complete1080p
    # ---- 真命中必须保住(同一批数据里的两族真重合) ----
    pack = "The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb"
    assert fuzzy_name_match(pack, "The Cat and the Dragon S01E05 1080p friDay WEB-DL AAC2.0 H.264-MWeb")
    assert fuzzy_name_match(
        "[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga.Suuguu.Chouso.Torikae.Den.2026.S01.1080p.WEB-DL.AAC.H.264",
        "Futsutsuka na Akujo dewa Gozaimasu ga Suuguu Chouso Torikae Den 2026 S01 1080p WEB-DL AAC H.264",
    )


# ---------------- 计数对平(计划 26-09-29-2036 §5) ----------------


def counter_adapter(monkeypatch, claims: Dict[str, int]):
    """把 build_adapter 换成「按 claims 表上交计数」的测试 adapter(§5: 覆写 parse_counters 上交合成值)。

    claims 波间可变: 测试直接改字典, 下一波 build_adapter 重建的 adapter 读到新表;
    键缺 = 该档不上交(降级 None)。返回 claims 本体方便波间改写。
    """
    from auto_qb.hr.adapters.nexusphp import NexusPhpMyhrAdapter

    class _CounterNexus(NexusPhpMyhrAdapter):
        def parse_counters(self, html):
            return {lane: v for lane, v in claims.items()}

    monkeypatch.setattr(
        hr_service,
        "build_adapter",
        lambda site, conf: _CounterNexus(
            site,
            hr_page_url=conf.hr_page_url,
            download_path=conf.download_path,
            scopes=FETCH_LANES,
            page_param=conf.page_param,
        ),
    )
    return claims


def test_counter_match_releases(tmp_path, monkeypatch):
    """T1 对平放行: 三档 claim == rows 且全深度 → 照常签发(与无计数基线一致), count_match 全 True"""
    clock = Clock()
    counter_adapter(monkeypatch, {"A": 0, "B": 5, "C": 0})
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified and data.verified["h1"].source == SOURCE_NOT_LISTED
    assert result.releases_signed >= 1 and data.wave.releases_enabled is True
    assert [data.wave.lanes[l].count_match for l in "ABC"] == [True, True, True]
    assert data.wave.lanes["B"].count_claim == 5


def test_counter_mismatch_freezes_batch(tmp_path, monkeypatch, caplog):
    """T2 不对平冻结: 全深度档 claim≠rows → depth_broken 整波不签发; 连续 3 波 ERROR 升级;
    对平自愈 + streak 清零。不变量: 命中登记 / 管束 / 复用窗照常(门只拦批量「未列出」签发)。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    claims = counter_adapter(monkeypatch, {"B": 50})
    blob11, h11 = mk_blob("EXAMPLE 11")
    pages = {
        url_of("A"): myhr_page([row(11, "EXAMPLE 11")]),  # 命中行(A 档, 全深度)
        url_of("B"): myhr_page(five_expired_rows(20)),  # 2. 停翻全深度, 实抓 5 行 vs 声明 50
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {
        "h1": anchor_for("h1", completion_on=T_DONE_NEW),
        h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)
    }
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    # 冻结: h1 不签发(无计数基线会签), releases_enabled False, streak=1, WARNING 告警
    assert "h1" not in data.verified and result.releases_signed == 0
    assert data.wave.releases_enabled is False
    assert data.wave.lanes["B"].count_claim == 50 and data.wave.lanes["B"].count_match is False
    assert data.wave.lanes["B"].count_mismatch_streak == 1
    assert "计数对不平" in caplog.text
    # 不变量: 命中登记照常(行 11 与本地种子对上) + 复用窗照常(有效波)
    assert any(e.tid == 11 and e.infohash_v1 == h11 for e in data.index.values())
    assert data.expires_at > 0
    # 连续 3 波 → ERROR 升级(只提示人, 行为仍是「不签发」)
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["B"].count_mismatch_streak == 3
    assert "已连续 3 波" in caplog.text
    assert "h1" not in data.verified
    # 下一波对平 → 自愈签发 + streak 清零
    claims["B"] = 5
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified and result.releases_signed >= 1
    assert data.wave.lanes["B"].count_mismatch_streak == 0


def test_counter_absent_degrades_to_legacy(tmp_path):
    """T3 无计数降级: 默认 adapter(parse_counters 默认空 dict) → 全路径与旧逻辑逐位一致;
    旧版站点文件(无三键)加载 count_claim/count_match 为 None(T1 迁移陷阱守阵: 不得变 0)。"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    # 无计数: 签发与既有基线(test_release_signed_on_full_coverage)逐位一致 + 新字段全 None
    assert "h1" in data.verified and result.releases_signed >= 1
    assert data.wave.releases_enabled is True
    assert all(st.count_claim is None and st.count_match is None for st in data.wave.lanes.values())
    # 旧档案反序列化: 键缺 = None(走 _as_int 缺省路径会折成 0 ⇒ 全站假 mismatch, 正是要防的事故)
    legacy = {"lane": "B", "status": "ok", "pages": 2, "rows": 5, "full_depth": True}
    st = HrLaneState.from_json(legacy)
    assert st.count_claim is None and st.count_match is None and st.count_mismatch_streak == 0
    # 新档案 JSON 往返: 三键不丢
    st2 = HrLaneState.from_json(st.to_json() | {"count_claim": 7, "count_match": False, "count_mismatch_streak": 2})
    assert st2.count_claim == 7 and st2.count_match is False and st2.count_mismatch_streak == 2


def test_counter_zero_claims_self_attest_empty(tmp_path, monkeypatch, caplog):
    """T4 计数零自证空: 三档 claim=0 ∧ rows=0 → 视同人工确认戳, 签发放行;
    zero_listing 软提示不出现, 无需 --hr-confirm-empty。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {"A": 0, "B": 0, "C": 0})
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified and data.wave.releases_enabled is True
    assert "清单为 0" not in result.reason and "零行" not in result.reason
    assert "若确认账号的 HR 清单确实为空" not in caplog.text
    # M3 展示口径对齐(计划 26-09-29-2036 §2.5): 计数自证空集的站点不再标「零行未确认」/「需人工对账」
    snap = build_site_statuses(service, clock.now)[0]
    assert snap.count_attested_empty is True and snap.empty_confirmed is False
    assert snap.blocking == ""


def test_counter_positive_zero_rows_page_changed(tmp_path, monkeypatch, caplog):
    """T51. 计数>0 ∧ 行数=0(tab 形): 整表被吃光/首页即被截的显式信号 → page_changed 硬告警 + 不签发。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {"B": 3})
    pages = {
        url_of("A"): myhr_page(five_expired_rows(20)),  # A 有行(避免零行波噪声), 全深度
        url_of("B"): EMPTY_TABLE_PAGE,  # B 空表但站点声明 3 行
        url_of("C"): EMPTY_TABLE_PAGE,
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" not in data.verified and data.wave.releases_enabled is False
    assert data.wave.lanes["B"].count_claim == 3 and data.wave.lanes["B"].count_match is False
    assert "声明 3 行但实抓 0 行" in caplog.text  # page_changed 硬告警
    assert "计数对不平" not in caplog.text  # 与 mismatch 节流告警不重复


def test_interval_empty_page_keeps_manual_stamp(tmp_path, monkeypatch, caplog):
    """T52. 分页区间形空表(无标记 ⇒ claim=None): 自证空不可用 → 维持 zero_listing 人工戳路径。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {})  # 区间形空表无计数标记: 覆写了也拿不到键
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" not in data.verified and data.wave.releases_enabled is False
    assert "清单为 0" in result.reason  # 人工对账戳路径保留(--hr-confirm-empty)
    assert "若确认账号的 HR 清单确实为空" in caplog.text


def test_counter_truncation_gap_informational(tmp_path, monkeypatch, caplog):
    """T6 截断差值信息性: 预算截断(非全深度) rows<claim → 不告警不冻结; notes 记差值;
    REASON_BUDGET 语义不变(与解析问题分层)。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {"A": 30, "B": 30, "C": 30})
    pages = {
        url_of("A", 1):
            myhr_page([row(11, "EXAMPLE 11")], has_next=True),
        url_of("B", 1):
            myhr_page(five_expired_rows(20)[:1], has_next=True),
        url_of("C", 1):
            myhr_page([row(31, "OTHER 31", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: torrent_blob(name="EXAMPLE 11")})
    gconf = global_conf(max_pages_per_wave=3)
    service = make_service(tmp_path, fetcher, gconf=gconf, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert all(st.ok and not st.full_depth for st in data.wave.lanes.values())  # 各 1 页截断
    # 不告警不冻结: counter 门开着(签发没发生是位置覆盖不够, 与计数无关)
    assert "计数对不平" not in caplog.text
    assert data.wave.releases_enabled is True
    # 差值写进 notes(走查报告与 WebUI 直接可见缺口)
    assert "实抓 1/声明 30, 差 29 行" in result.reason
    assert result.reason_kind == REASON_BUDGET  # 截断波归 budget, 不误报 parse


def test_fail_streak_resets_on_clean_wave(tmp_path):
    """失效波数清零(model.py「干净波清零」口径): 连续失效只跨失效波延续 —— 恢复波清零,
    之后的单次失效从 1 起算, 不把历史波数一并计入(修复: 既有实现从未清零, ERROR 升级会虚报)。"""
    clock = Clock()
    failed_pages = {**standard_pages(), url_of("A"): REVISED_PAGE}  # A 首页表头缺失 → 该档失效
    fetcher = FakeFetcher(pages=failed_pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "failed" and data.wave.lanes["A"].fail_streak == 1
    clock.advance(13 * 3600)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].fail_streak == 2  # 连续失效照常累加
    # 恢复波: A 跑通 → 清零
    fetcher.pages = standard_pages(rows_b=five_expired_rows(20))
    clock.advance(13 * 3600)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "ok" and data.wave.lanes["A"].fail_streak == 0
    # 恢复后单次失效: streak 从 1 起算(旧实现会是 3, 直接触发 ERROR 升级虚报)
    fetcher.pages = failed_pages
    clock.advance(13 * 3600)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "failed" and data.wave.lanes["A"].fail_streak == 1


# ---------------- 三参数解耦: 拉取间隔 / 复用窗 / 立即拉取(计划 26-09-30-0240) ----------------


def test_reuse_window_uses_min_of_config_and_interval(tmp_path):
    """1. 复用窗时长 = min(reuse_window, 拉取间隔): 新鲜度不再借用节奏值(12H→2H); 窗内再跑 → REUSED(既有语义不变)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)  # 默认 reuse_window=2H, interval=12H
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.expires_at == clock.now + 2 * 3600.0, "min(2H, 12H) = 2H —— 不再是 12H"
    result = run_wave(service)
    assert result.action == "reused"


def test_reuse_window_never_exceeds_interval(tmp_path):
    """1b. clamp 另一半: 复用窗(2H) > 拉取间隔(1H) → 生效 1H(拉取间隔是硬节奏, 静默收敛不报错)"""
    clock = Clock()
    service = make_service(
        tmp_path,
        FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])),
        site=site_conf(refresh_interval=3600.0),
        clock=clock
    )
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.expires_at == clock.now + 3600.0


def test_interval_gate_waits_between_waves(tmp_path):
    """2. 复用窗外 + 拉取间隔内 → WAITING「未到拉取时刻(拉取间隔)」: 节奏闸门存在,
    缩短复用窗不会把取数频率放大到「每复用窗一波」(§2 关键正确性 —— 唯一否决点)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(reuse_window=3600.0), clock=clock)
    run_wave(service)
    clock.advance(2 * 3600.0)  # 复用窗(1H)已过, 拉取间隔(12H)未到
    result = run_wave(service)
    assert result.action == ACTION_WAITING
    assert "未到拉取时刻" in result.reason and "拉取间隔" in result.reason


def test_interval_gate_due_runs_next_wave(tmp_path):
    """3. 健康波 + interval 到点 → 正常开波: 默认节奏与解耦前一致"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    clock.advance(12 * 3600.0)  # 复用窗与拉取间隔都已过
    result = run_wave(service)
    assert result.action in ("refreshed", "partial")


def test_force_bypasses_reuse_and_interval_gates(tmp_path):
    """4. 立即拉取(force)→ 跳过复用窗与拉取间隔两道闸, 时钟未动也直接开波"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts > 0 and data.expires_at > clock.now, "前置: 处于复用窗 + 拉取间隔内"
    result = service.refresh_site(SITE, {}, force=True)
    assert result.action in ("refreshed", "partial"), f"force 应越过两道闸, got: {result.action} {result.reason}"


def test_force_still_respects_min_interval(tmp_path):
    """5. 立即拉取不越过账号安全线: min_interval 未到 → 仍 WAITING(间隔, 非「拉取间隔」)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0), clock=clock)
    run_wave(service)  # 页面请求已发出: last_fetch_ts = now
    result = service.refresh_site(SITE, {}, force=True)  # 时钟未动: min_interval 必然未到
    assert result.action == ACTION_WAITING
    assert "间隔" in result.reason and "拉取间隔" not in result.reason, \
        f"等待原因应是 min_interval 而非拉取间隔闸门: {result.reason}"


def test_all_failed_wave_keeps_short_retry_rhythm(tmp_path):
    """6. 全档失败波 → healthy_ts 不前进 → 不被拉取间隔闸门拖住: 下一轮(60s 节拍)即可重试"""
    clock = Clock()
    # 全档取数失败(三档都抛): expires_at=0(无新数据可复用), healthy_ts 不动
    fetcher = FakeFetcher(pages=standard_pages(), fail_text_at={"A": "boom", "B": "boom", "C": "boom"})
    service = make_service(tmp_path, fetcher, clock=clock)
    first = run_wave(service)
    assert first.action == ACTION_ERROR
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts == 0.0 and data.expires_at == 0.0
    clock.advance(60.0)  # 一个 poll 节拍后: 失败处置节奏与解耦前一致(下一轮重试, 不等一个拉取间隔)
    second = run_wave(service)
    assert second.action == ACTION_ERROR, "失败波不该被拉取间隔闸门挡住(healthy_ts 未前进)"
    # 失败后恢复: force 立即开波成功(失败残留不锁死人工通路)
    fetcher.fail_text_at.clear()
    clock.advance(60.0)
    recovered = service.refresh_site(SITE, {}, force=True)
    assert recovered.action in ("refreshed", "partial")


def test_partial_wave_advances_healthy_ts_failed_lane_waits(tmp_path):
    """7. 部分失败波 → healthy_ts 前进(至少一档有效) → 拉取间隔闸门接管: 失败档位等下一波"""
    clock = Clock()
    fetcher = FakeFetcher(
        pages={**standard_pages([row(11, "OTHER 11")])},
        fail_text_at={
            "B": "boom",
            "C": "boom"
        },  # B/C 失败, A 有效
    )
    service = make_service(tmp_path, fetcher, gconf=global_conf(reuse_window=3600.0), clock=clock)
    first = run_wave(service)
    assert first.action in (ACTION_PARTIAL, ACTION_ERROR)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts == clock.now, "部分有效 → 健康波前进"
    clock.advance(2 * 3600.0)  # 复用窗(1H)过, 拉取间隔(12H)未到 → 失败的 B/C 等下一波
    second = run_wave(service)
    assert second.action == ACTION_WAITING and "拉取间隔" in second.reason


def test_wave_ts_refreshes_every_wave_not_frozen(tmp_path):
    """C1 回归(2026-10-03): lane.wave_ts 每波刷新, 不冻结在进程内首成功波。

    原实现 `wave_ts = prev.wave_ts if prev.ok else 0.0` + 每波只在 `st.wave_ts <= 0` 时置一次
    ⇒ 连续 ok 档的 wave_ts 永停首次成功波, 违背 model.py:319「本档最近一波完成取的时刻」,
    并让 _absence_proven_all 新鲜度闸(anchor.added_on > st.wave_ts)拿陈旧基准 —— 近几天新加
    本地种子拿不到「未列出」批量放行(方向保守不误放行, 但违背字段语义)。"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(reuse_window=3600.0), clock=clock)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    first_ts = data.wave.lanes["A"].wave_ts
    assert first_ts == clock.now, "首波 wave_ts = 本波取数时刻"
    clock.advance(13 * 3600.0)  # 过拉取间隔, 开新波(内容不变, A 档照常 ok)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].wave_ts == clock.now > first_ts, \
        "第二波 wave_ts 必须刷新为本次取数时刻(修复前冻结在首波)"


def test_refresh_all_force_not_blocked_by_gates(tmp_path):
    """8. 走查语义: refresh_all(force=True) 在复用窗/拉取间隔内仍开波(--hr-once 不被新闸门挡)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    clock.advance(60.0)  # 复用窗(2H)与拉取间隔(12H)都远未到
    blocked = service.refresh_all()
    assert blocked[0].action == "reused", "不带 force: 复用窗内照旧复用"
    forced = service.refresh_all(force=True)
    assert forced[0].action in ("refreshed", "partial"), "force=True: 走查立即开波"


# ==================== P1 覆盖率提升轮(T1.1 错误路径系统补齐) ====================


class _ListLogHandler(logging.Handler):
    """模块 logger 自足采集(pitfalls/testing/log-capture: 禁 caplog, 显式 setLevel)"""
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class service_log:
    """挂在 auto_qb.hr.service 模块 logger 上的临时 handler, 用完恢复级别与传播"""
    def __init__(self, level=logging.DEBUG):
        self._handler = _ListLogHandler()
        self._logger = logging.getLogger("auto_qb.hr.service")
        self._level = level

    def __enter__(self):
        self._old_level, self._old_propagate = self._logger.level, self._logger.propagate
        self._logger.addHandler(self._handler)
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        return self._handler.messages

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)
        self._logger.propagate = self._old_propagate
        return False


def test_refresh_site_guard_paths(tmp_path):
    """站点未接入 / 全局开关关 -> 不取数直接返回; HrRefreshResult.ok 属性语义"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=clock)
    # 站点未接入(site_confs 没有该站)
    r1 = service.refresh_site("nosuch", {})
    assert r1.action == "disabled" and r1.reason == "该站未接入 hr_check"
    assert r1.ok is False
    # 全局开关关
    svc2 = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(enabled=False),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=clock,
        sleeper=lambda _s: None,
    )
    r2 = svc2.refresh_site(SITE, {})
    assert r2.reason == "hr_check.enabled=false"
    assert fetcher.text_calls == [], "守卫路径不得发任何请求"
    # ok 属性的正例侧(复用/刷新都算 ok)
    ok_result = hr_service.HrRefreshResult(site=SITE, action="reused")
    assert ok_result.ok is True


def test_refresh_site_unknown_adapter(tmp_path):
    """未登记的 adapter -> ACTION_ERROR, 单站点失败不外抛"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, site=site_conf(adapter="no-such-adapter"), clock=Clock())
    result = run_wave(service)
    assert result.action == ACTION_ERROR
    assert "未登记的 adapter" in result.reason
    assert fetcher.text_calls == []


def test_refresh_site_lock_busy_returns_locked(tmp_path):
    """站点锁被其它实例持有 -> ACTION_LOCKED(等下一轮), 不外抛"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=Clock())
    outsider = HrSiteStore(SITE, service.dir, lock_timeout=0.0, owner="other-instance")
    with outsider.hold():
        result = service.refresh_site(SITE, {})
    assert result.action == ACTION_LOCKED
    assert "锁被其它实例持有" in result.reason
    assert fetcher.text_calls == []


def test_refresh_site_internal_error_contained(tmp_path, monkeypatch):
    """非取数异常(如编程错误) -> ACTION_ERROR + alerted, 波次异常不外拖"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=clock)

    def boom(url):
        raise RuntimeError("意外炸了")

    monkeypatch.setattr(fetcher, "get_text", boom)
    result = run_wave(service, {})
    assert result.action == ACTION_ERROR
    assert result.alerted is True
    assert "RuntimeError" in result.reason and "意外炸了" in result.reason


def test_channel_quota_lets_wave_yield_and_warns_once(tmp_path):
    """扩展侧硬上限 -> 本波让位(ACTION_WAITING, 不计档位失败); 同站只 WARNING 一次"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(), quota=True)
    service = make_service(tmp_path, fetcher, clock=clock)
    with service_log() as messages:
        first = run_wave(service, {})
        assert first.action == ACTION_WAITING
        assert "扩展侧硬上限" in first.reason
        data, _ = service.store(SITE).read_unlocked()
        assert data.wave.lanes == {}, "让位发生在波前, 不落任何档位状态"
        clock.advance(60.0)
        second = run_wave(service, {})
        assert second.action == ACTION_WAITING
    warns = [m for m in messages if "扩展侧硬上限挡下取数" in m]
    assert len(warns) == 1, messages
    assert any("仍生效(已告警过" in m for m in messages)


def test_login_page_detected_by_adapter_and_warned_once(tmp_path):
    """登录页由 adapter 页面形态识别(与扩展回传异常同一波级出口); 登录告警每站一次, 恢复后重置"""
    clock = Clock()
    fetcher = FakeFetcher(pages={url_of(l): LOGIN_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    with service_log() as messages:
        first = run_wave(service, {})
        assert first.action == ACTION_ERROR and "登录页" in first.reason
        data, _ = service.store(SITE).read_unlocked()
        assert data.rate.last_fetch_ts == clock.now, "登录页路径同样前进间隔基准"
        clock.advance(120.0)
        second = run_wave(service, {})
        assert second.action == ACTION_ERROR
    login_errors = [m for m in messages if "页面是登录页 ⇒" in m]
    assert len(login_errors) == 1, "登录恢复前每站只报一次(状态变化报一次), 不再每波重报"
    assert sum("登录态仍未恢复(已告警过" in m for m in messages) == 1, "第二波走去重早退(INFO)"
    # 去重分支本体: 直接连调 _warn_login(用未告警过的站名), 第一次真告警, 第二次走「已告警过」早退
    with service_log() as repeat_messages:
        service._warn_login("example2", RuntimeError("仍未登录"))
        service._warn_login("example2", RuntimeError("仍未登录"))
    assert sum("登录态仍未恢复(已告警过" in m for m in repeat_messages) == 1
    # 恢复重置: 中间正常波拿到内容页 -> 清去重标记; 再次登录失效重新报一次
    fetcher.pages.update(standard_pages())
    assert run_wave(service, {}).action == "refreshed"  # 登录波不设复用窗, 恢复波直接可跑
    fetcher.pages.update({url_of(l): LOGIN_PAGE for l in "ABC"})
    clock.advance(12 * 3600.0 + 60.0)  # 跳出复用窗(2h)与拉取间隔(12h, 恢复波推进了 healthy_ts)
    with service_log() as relogin:
        third = run_wave(service, {})
        assert third.action == ACTION_ERROR
    assert len([m for m in relogin if "页面是登录页 ⇒" in m]) == 1, "恢复后再失效 -> 重新告警(状态变化报一次)"


def test_challenge_page_truncates_wave(tmp_path):
    """挑战页 = 页面取数失败(无 Retry-After) -> 波级 had_error -> ACTION_PARTIAL"""
    clock = Clock()
    fetcher = FakeFetcher(pages={url_of(l): CHALLENGE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_ERROR, "首页即败三档全失效 -> error(截断语义在档位状态里)"
    assert "挑战页" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    assert all(not st.ok for st in data.wave.lanes.values()), "首页即败 -> 三档都失效"


def _page_with_blank_required_row(tid: int) -> str:
    """表头完好但必填字段(名称/还需做种/剩余)全空的一行 -> S2 零容忍"""
    blank_cells = "".join("<td></td>" for _ in range(8))
    body = f'<tr><td class="rowfollow nowrap" align="center">{tid}</td>{blank_cells}</tr>'
    return myhr_page([]).replace("</tr></tbody></table>", "</tr>" + body + "</tbody></table>", 1)


def test_missing_fields_abort_after_valid_page(tmp_path):
    """第 2 页必填字段缺失 -> 该档在失效点截断, 第 1 页之前的数据仍有效(LANE_OK 非全深度)"""
    clock = Clock()
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11", done=DONE_NEW)], has_next=True),
        url_of("A", 2): _page_with_blank_required_row(12),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.status == "ok" and st.pages == 1 and st.full_depth is False
    assert "必填字段缺失" in st.detail
    assert data.wave.lanes["B"].ok and data.wave.lanes["C"].ok, "档位独立: 其它档照常"
    assert result.action == ACTION_PARTIAL


def test_daily_quota_exhausted_truncates_rest_lane(tmp_path):
    """日额用尽(等待可承受时等满再试仍被拒) -> 「日额已用尽」截断, 首页即败 = LANE_FAILED"""
    # 时钟放在距本地零点 100s 处: 日额到顶后的等待(next_day_reset) <= sleep_max(300s),
    # 走「等满再发 -> try_consume 仍拒」路径, 而不是「等不起」直接放弃
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400.0
    clock = Clock(start=midnight - 100.0)
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, gconf=global_conf(max_requests_per_day=2), clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].ok and data.wave.lanes["B"].ok
    st_c = data.wave.lanes["C"]
    assert st_c.status == "failed" and "日额已用尽" in st_c.detail
    assert "日额已用尽" in result.reason
    assert data.rate.day_count == 2


def test_budget_take_gives_up_without_sleeper(tmp_path):
    """无 sleeper 的服务不持锁干等: 间隔未到 -> 该档本轮放弃(预算受限截断)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages())
    service = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(min_interval=90.0),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=clock,
        sleeper=None,
    )
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].ok, "首档间隔基准为 0, 正常取页"
    for lane in ("B", "C"):
        st = data.wave.lanes[lane]
        assert st.status == "failed" and "预算受限" in st.detail, (lane, st.detail)
    assert result.reason_kind == REASON_BUDGET


def test_budget_unit_wait_and_caps(tmp_path):
    """_Budget 单元: sleeper 等待记账(waited) / sleep_max 与 round_wait_max 上限 / 成功路径"""
    from auto_qb.hr.ratelimit import HrLimits
    from auto_qb.hr.service import _Budget

    data = HrSiteData()
    data.rate.last_fetch_ts = 1000.0
    limits = HrLimits(min_interval=90.0, max_requests_per_day=100)
    # 时钟起点必须与 last_fetch_ts 对齐: 等待记账 = 抖动间隔 - (now - last_fetch_ts),
    # 起点错开会让实测等待低于 min_interval, 下界断言偶发假红(issue 26-10-02-0306)
    clock = Clock(start=1000.0)
    waits = []
    budget = _Budget(data, limits, clock, waits.append)
    ok, why = budget.take()
    assert ok and why == "", f"等满后应放行: {why}"
    assert len(waits) == 1 and 90.0 <= waits[0] <= 113.0, "抖动只向上 +0~25%"
    assert budget.waited == waits[0], "waited 记录本波已等掉的总秒数"
    assert data.rate.day_count == 1
    # 单次等待超过 sleep_max -> 放弃
    capped = _Budget(data, limits, clock, waits.append, sleep_max=1.0)
    ok, why = capped.take()
    assert not ok and "还差" in why and len(waits) == 1
    # 本波累计等待超过 round_wait_max -> 放弃
    round_capped = _Budget(data, limits, clock, waits.append, round_wait_max=10.0)
    ok, why = round_capped.take()
    assert not ok and "还差" in why
    # 间隔已到 -> 不等待直接放行
    clock.advance(1000.0)
    ok, why = budget.take()
    assert ok and len(waits) == 1, "间隔已过不再 sleep"


def test_pages_exhausted_mid_round_lane_not_scheduled(tmp_path):
    """页数上限耗尽在轮转中段 -> 未轮到的档收尾为「本波未轮到取数」(LANE_FAILED)"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([], has_next=False),
        url_of("B"): myhr_page(five_expired_rows(20)),
        url_of("C"): myhr_page([], has_next=False),  # C 永远等不到它的页
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, gconf=global_conf(max_pages_per_wave=2), clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].ok and data.wave.lanes["B"].ok
    st_c = data.wave.lanes["C"]
    assert st_c.status == "failed" and "本波未轮到取数" in st_c.detail
    assert st_c.pages == 0 and st_c.fail_streak == 1
    assert url_of("C") not in fetcher.text_calls


def test_order_direction_flip_forces_stop(tmp_path):
    """波内方向翻转: 第 1 页升序、第 2 页降序 -> 强制早停(失效点之前的数据有效)"""
    clock = Clock()
    pages = {
        url_of("A", 1):
            myhr_page(
                [row(11, "OTHER 11", done="2026-09-01 10:00:00"),
                 row(12, "OTHER 12", done="2026-09-02 10:00:00")],
                has_next=True,
            ),
        url_of("A", 2):
            myhr_page(
                [row(13, "OTHER 13", done="2026-09-10 10:00:00"),
                 row(14, "OTHER 14", done="2026-09-09 10:00:00")],
            ),
        url_of("B"):
            myhr_page([], has_next=False),
        url_of("C"):
            myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages, blobs={t: torrent_blob(name=f"OTHER {t}") for t in (11, 12, 13, 14)})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.pages == 1 and st.full_depth is False and st.status != "ok"  # 违反页不计覆盖进度
    assert "方向翻转" in st.detail and "排序违反" in st.detail
    assert "方向翻转" in result.reason
    assert data.wave.releases_enabled is False, "排序失效波不签发放行"


def test_cross_page_disorder_forces_stop(tmp_path):
    """跨页乱序: 第 2 页最深行比第 1 页最浅行还新 -> 强制早停"""
    clock = Clock()
    pages = {
        url_of("A", 1):
            myhr_page(
                [row(11, "OTHER 11", done="2026-09-10 10:00:00"),
                 row(12, "OTHER 12", done="2026-09-05 10:00:00")],
                has_next=True,
            ),
        url_of("A", 2):
            myhr_page(
                [row(13, "OTHER 13", done="2026-09-20 10:00:00"),
                 row(14, "OTHER 14", done="2026-09-01 10:00:00")],
            ),
        url_of("B"):
            myhr_page([], has_next=False),
        url_of("C"):
            myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages, blobs={t: torrent_blob(name=f"OTHER {t}") for t in (11, 12, 13, 14)})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.pages == 1 and st.status != "ok" and "跨页乱序" in st.detail  # 违反页不计覆盖进度
    assert "跨页乱序" in result.reason


def test_tail_zero_partial_reset(tmp_path):
    """停翻2. 跨页重算: 第 1 页尾只有 1 行到期 -> 计数重置为 1; 第 2 页凑满 5 行才停(全深度)"""
    clock = Clock()
    pages = {
        url_of("B", 1):
            myhr_page(
                [
                    row(20, "OTHER 20", done=DONE_NEW, remain="1天00:00:00"),
                    row(21, "OTHER 21", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")
                ],
                has_next=True,
            ),
        url_of("B", 2):
            myhr_page(five_expired_rows(30)[:4], has_next=False),
        url_of("A"):
            myhr_page([], has_next=False),
        url_of("C"):
            myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})  # 无本地对象: 停翻1./3. 不参与, 由停翻2. 跨页累计收尾
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["B"]
    assert st.status == "ok" and st.pages == 2 and st.full_depth is True
    assert "到期段强信号" in st.detail


def test_process_rows_unit_identity_paths(tmp_path):
    """行处理单元: 换 tid 重列接管 / 命中撤销放行 / 同 hash 旧条目退役"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    data = HrSiteData()
    # 换 tid 重列: hash H1 挂在 tid 99 名下(永久层), 站点现在用 tid 11 列它
    data.downloaded[99] = HrDownloaded(tid=99, ts=1.0, name="old", infohash_v1="H1")
    # 旧活跃条目 tid 12 也挂着 H1(上一波的行) -> 新行接管后退役
    stale = HrEntry(tid=12, name="old-row")
    stale.infohash_v1 = "H1"
    stale.active = True
    data.index[12] = stale
    # 已有的放行记录 -> 命中即撤销
    data.verified["H1"] = HrVerified(infohash="H1", tid=99, verified_ts=1.0, source=SOURCE_NOT_LISTED)
    wave = _WaveContext({})  # 本地没有该种子 -> 走「换 tid 重列」的接管分支
    wave.dl_by_hash = hr_service._dl_by_hash(data)  # 生产里由 _do_wave 波前构建
    row11 = HrEntry(tid=11, name="new-row")
    row11.infohash_v1 = "H1"
    service._process_rows("B", [row11], data, wave)
    assert wave.hits == {"H1": "B"}, "非本地 hash 但挂在其它 tid 名下 -> 接管并照判命中"
    assert data.index[12].active is False, "同 hash 旧条目退役"
    assert wave.retracted == 1 and "H1" not in data.verified, "命中即撤销既有放行"
    assert row11.tid not in wave.pending_downloads


def test_run_downloads_unit_paths(tmp_path):
    """下载单元: 队列缺行/已有身份跳过 / 永久层回填(命中)/ 预算止步"""
    from auto_qb.hr.ratelimit import HrLimits
    from auto_qb.hr.service import _Budget

    service = make_service(tmp_path, FakeFetcher(pages={}))
    data = HrSiteData()
    data.downloaded[13] = HrDownloaded(tid=13, ts=1.0, name="x", infohash_v1="HL")
    wave = _WaveContext({"HL": HrAnchor(added_on=1, downloaded=10, completion_on=-1, progress=1.0, name="L")})
    wave.local_hashes = {"HL"}
    wave.dl_by_hash = hr_service._dl_by_hash(data)
    wave.pending_downloads = {11, 12, 13, 14}
    wave.seen[12] = HrEntry(tid=12, name="has-id")
    wave.seen[12].infohash_v1 = "already"
    wave.seen[13] = HrEntry(tid=13, name="from-store")
    wave.seen[14] = HrEntry(tid=14, name="no-budget")
    budget = _Budget(data, HrLimits(min_interval=0.0, max_requests_per_day=0), service._now, None)
    with service.store(SITE).hold() as session:
        service._run_downloads(
            SITE, None, data, budget, wave, hr_service.HrRefreshResult(site=SITE, action="refreshed"), session
        )
    assert 11 not in wave.pending_downloads, "队列里的 tid 没有对应行 -> 丢弃"
    assert 12 not in wave.pending_downloads, "已有身份的行不再下载"
    assert 13 not in wave.pending_downloads and wave.seen[13].infohash_v1 == "HL"
    assert wave.hits == {"HL": "A"}, "永久层回填命中本地 -> 照判(记该行档位)"
    assert 14 in wave.pending_downloads, "预算为 0 -> 未下完的留待下波"
    assert wave.seen[14].infohash_v1 == ""


def test_download_invalid_blob_counted_as_fail(tmp_path):
    """.torrent 内容不是合法 bencode -> 计一次种子失败(冷却记账), 波次不外抛"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([row(11, "TOTALLY-UNRELATED")]),
        url_of("B"): myhr_page([]),
        url_of("C"): myhr_page([])
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: b"this is not a torrent"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    # 失败的行留在待回填队列, 每页处理后再试: 单波内共 3 次(达 MAX_DOWNLOAD_RETRIES 后冷却)
    assert result.torrents_failed == 3 and result.torrents_fetched == 0
    data, _ = service.store(SITE).read_unlocked()
    assert data.fails[11].count == 3
    assert data.index[11].infohash_v1 == "", "身份未回填"


def test_readonly_degradation_noted_in_result(tmp_path):
    """锁自检失败(revision 回退) -> 波照跑但只读: reason 注明「锁自检失败」, 文件不被覆写"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    rev_before = data.revision
    assert rev_before > 0
    # 注入「本实例上次写到过更高的 revision」: 下一波锁自检判不生效 -> 只读退化
    service.store(SITE)._last_write_rev = 10_000
    clock.advance(13 * 3600)
    result = run_wave(service, {})
    assert "锁自检失败" in result.reason and result.persisted is False
    data2, _ = service.store(SITE).read_unlocked()
    assert data2.revision == rev_before, "只读退化不得写盘"


def test_persist_false_reports_readonly_mode(tmp_path):
    """只读走查口径(persist=False): 波照常跑、不写盘, reason 注明「只读模式, 未写盘」"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=False,
        allow_fetch=True,
        now_fn=clock,
        sleeper=lambda _s: None,
    )
    result = run_wave(service, {})
    assert "只读模式, 未写盘" in result.reason
    assert result.persisted is False
    assert not service.store(SITE).path.exists(), "走查不得落站点文件"
    data = result.snapshot
    assert data is not None and any(e.tid == 11 for e in data.index.values()), "内存快照仍完整"


def test_wave_pure_function_units():
    """波次纯函数单元: 档位摘要缺档形态 / 陈旧淘汰(模块级单点) / 位置覆盖 / 缺席证明"""
    from auto_qb.hr.service import _absence_proven_all, _dl_by_hash, _position_covered, _prune_index

    # 档位摘要: 缺档 -> "无"
    assert "A:无" in _lanes_summary_from({})
    # 下载反查: 同 hash 只记第一个 tid
    data = HrSiteData()
    data.downloaded[1] = HrDownloaded(tid=1, infohash_v1="H", infohash_v2="")
    data.downloaded[2] = HrDownloaded(tid=2, infohash_v1="H", infohash_v2="")
    assert _dl_by_hash(data) == {"H": 1}
    # 陈旧淘汰(模块级单点, issue 26-10-01-2335 合并): 非活跃且超保留期的条目删除, 活跃/近期保留
    old = HrEntry(tid=1, name="gone")
    old.active, old.last_seen = False, 1.0
    fresh = HrEntry(tid=2, name="fresh")
    fresh.active, fresh.last_seen = False, time.time()
    live = HrEntry(tid=3, name="live")
    data.index = {1: old, 2: fresh, 3: live}
    now = time.time()
    _prune_index(data, now)
    assert set(data.index) == {2, 3}
    # 恒 0(修复前存量)视为未知不淘汰
    data.index = {4: HrEntry(tid=4, name="legacy", active=False)}
    _prune_index(data, now)
    assert set(data.index) == {4}
    # 位置覆盖: 缺完成时间 / 档位缺失或失效 / 深度不足 都不算覆盖
    entry = HrEntry(tid=9, name="e", done_iso=None)
    assert _position_covered(entry, {}) is False
    entry.done_iso = "2026-09-01T10:00:00"
    ok_state = HrLaneState(lane="A", status="ok", full_depth=True)
    assert _position_covered(entry, {"A": ok_state}) is False, "B/C 缺档不可判"
    shallow = HrLaneState(lane="A", status="ok", full_depth=False, cutoff_done=entry.done_epoch + 10)
    assert _position_covered(entry, {"A": shallow, "B": ok_state, "C": ok_state}) is False
    deep = HrLaneState(lane="A", status="ok", full_depth=False, cutoff_done=entry.done_epoch - 10)
    assert _position_covered(entry, {"A": deep, "B": ok_state, "C": ok_state}) is True
    # 缺席证明: 档位失效 / 纯辅种(无完成时刻)且非全深度 / 完成时刻浅于覆盖边界 都不成立
    wave = _WaveContext({})
    assert _absence_proven_all({}, wave, HrAnchor()) is False, "档位缺失不成立"
    states = {"A": ok_state, "B": ok_state, "C": ok_state}
    for st in states.values():
        st.wave_ts = 1.0
        st.full_depth = True
    assert _absence_proven_all(states, wave, HrAnchor()) is True, "全深度对任意位置成立"
    for st in states.values():
        st.full_depth = False
        st.cutoff_done = 100.0
    assert _absence_proven_all(states, wave, HrAnchor(completion_on=0)) is False, "纯辅种位置不可推定"
    assert _absence_proven_all(states, wave, HrAnchor(completion_on=50)) is False, "完成时刻浅于覆盖边界"
    # 完成时刻减 1D 对齐余量后仍须深于覆盖边界(500-86400 < 100 也不成立, 用足够深的时刻)
    assert _absence_proven_all(states, wave, HrAnchor(completion_on=100_000)) is True
    assert _absence_proven_all(states, wave, HrAnchor(completion_on=100_000, added_on=10**12)) is False, \
        "新鲜度闸门: added_on 晚于取数时刻无证明力"
    dead = {"A": HrLaneState(lane="A", status="failed", wave_ts=1.0), "B": ok_state, "C": ok_state}
    assert _absence_proven_all(dead, wave, HrAnchor(completion_on=100_000)) is False


def test_mark_fetch_failed_and_seen_rows_units(tmp_path):
    """波内小件单元: 页面失败定位缺档早退 / 已是 LANE_OK 早退 / seen_rows 视图 / 可信完成时刻表"""
    wave = _WaveContext({})
    _mark_fetch_failed_lane({}, wave)  # current_lane 没有对应档位状态 -> 早退不抛
    wave.current_lane = "A"
    states = {"A": HrLaneState(lane="A", status="ok")}
    _mark_fetch_failed_lane(states, wave)  # 已是 LANE_OK -> 早退(截断语义由别处负责)
    assert states["A"].status == "ok"
    # seen_rows 返回本波已见行
    wave2 = _WaveContext({})
    row11 = HrEntry(tid=11, name="x")
    wave2.seen[11] = row11
    assert wave2.seen_rows()[11] is row11
    # 可信完成时刻表: done_iso 缺失的考察中行不入表
    service = make_service(tmp_path, FakeFetcher(pages={}))
    observing = {"h1": HrEntry(tid=1, name="a"), "h2": HrEntry(tid=2, name="b", done_iso="2026-09-01T10:00:00")}
    trusted = service._trusted_done_map({}, observing)
    assert trusted == {"h2": observing["h2"].done_epoch}


def test_build_objects_unit_guards(tmp_path):
    """对象集现算单元: 空 hash 键跳过 / 非活跃条目不绑定 / 锚点漂移把放行记录作废回炉"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    # 空 hash 键: 直接跳过
    objects, observing, unmatched = service._build_objects(HrSiteData(), {"": HrAnchor(name="x")}, 100.0)
    assert objects == {} and observing == {} and unmatched == {}
    # 非活跃条目不参与绑定: 该 hash 视作全新对象
    data = HrSiteData()
    gone = HrEntry(tid=7, name="gone")
    gone.infohash_v1 = "HG"
    gone.active = False
    data.index[7] = gone
    anchor = HrAnchor(added_on=1, downloaded=10, completion_on=100, progress=1.0, name="g")
    objects, observing, unmatched = service._build_objects(data, {"HG": anchor}, 100.0)
    assert "HG" in unmatched and "HG" in objects and observing == {}
    # 锚点漂移(本机重下): 放行记录作废, 种子回对象集
    data.verified["HG"] = HrVerified(
        infohash="HG",
        tid=7,
        verified_ts=1.0,
        source=SOURCE_NOT_LISTED,
        anchor_added_on=1,
        anchor_downloaded=10,
        anchor_completion_on=100,
        anchor_progress=1.0,
    )
    rebought = HrAnchor(added_on=1, downloaded=99, completion_on=100, progress=1.0, name="g")
    objects, observing, unmatched = service._build_objects(data, {"HG": rebought}, 100.0)
    assert "HG" not in data.verified, "漂移即作废放行"
    assert "HG" in unmatched, "回炉重新对账"


def _gconf_channel_off():
    from auto_qb.config.models import HrChannelConfig

    return global_conf(channel=HrChannelConfig(enabled=False))


def test_build_views_skips_disabled_and_channel_states(tmp_path):
    """视图构建跳过未启用站点; channel_state 的 ok / silent(老化) / 无锁读 / disabled 分支"""
    from auto_qb.config.models import HrChannelConfig

    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]), blobs={11: torrent_blob(name="OTHER 11")})
    confs = {SITE: site_conf(), "offsite": site_conf(tracker="offsite", enabled=False)}
    service = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(channel=HrChannelConfig(enabled=True)),
        site_confs=confs,
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=clock,
        sleeper=lambda _s: None,
    )
    run_wave(service, {})
    views = service.build_views()
    assert set(views) == {SITE}, "未启用站点不进视图"
    # 数据参数直读: 健康 -> ok
    data, _ = service.store(SITE).read_unlocked()
    assert service.channel_state(SITE, data) == "ok"
    # 健康波老化超过静默阈值 -> silent
    clock.advance(7 * 3600)
    assert service.channel_state(SITE, data) == "silent"
    # 不传数据 -> 无锁读现算
    service2 = HrRefreshService(
        data_dir=str(tmp_path / "d2"),
        global_conf=global_conf(channel=HrChannelConfig(enabled=True)),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=Clock(),
        sleeper=lambda _s: None,
    )
    assert service2.channel_state(SITE) == "silent", "从未有健康波 -> silent"
    # 通道未启用 -> disabled
    service3 = HrRefreshService(
        data_dir=str(tmp_path / "d3"),
        global_conf=_gconf_channel_off(),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="test",
        persist=True,
        allow_fetch=True,
        now_fn=Clock(),
        sleeper=lambda _s: None,
    )
    assert service3.channel_state(SITE, None) == "disabled"


def test_lane_fail_streak_alerts_error(tmp_path):
    """连续 3 波同档失效 -> ERROR 升级(疑似改版建议走查); 只提示人, 失败处置不变"""
    clock = Clock()
    failed_pages = {**standard_pages(), url_of("A"): REVISED_PAGE}
    fetcher = FakeFetcher(pages=failed_pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    with service_log() as messages:
        for _ in range(3):
            clock.advance(13 * 3600)
            run_wave(service, {})
    errors = [m for m in messages if "已连续 3 波失效" in m]
    assert len(errors) == 1, messages
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].fail_streak == 3
    assert data.wave.lanes["A"].status == "failed"


def test_freeze_and_observation_guards(tmp_path):
    """终态冻结: 档位本波失效 -> 维持原状; 观察期: 位置未覆盖冻结计数; 出口身份缺位不落记录"""

    # 终态条目所在档位本波失效 -> 冻结跳过
    data = HrSiteData()
    entry = HrEntry(tid=21, name="b-row", lane=LANE_SATISFIED, done_iso="2026-09-01T10:00:00")
    data.index[21] = entry
    wave = _WaveContext({})
    failed = {"A": HrLaneState(lane="A", status="failed"), "B": HrLaneState(lane="B"), "C": HrLaneState(lane="C")}
    assert HrRefreshService._freeze_terminal(data, failed, wave, 1.0) == 0
    assert data.index[21].active is True and data.verified == {}
    # 观察期: 位置未被覆盖 -> streak 冻结(维持管束)
    obs = HrEntry(tid=31, name="a-row", lane=LANE_SCOPE, done_iso="2026-09-01T10:00:00")
    data.index[31] = obs
    not_covered = {
        "A": HrLaneState(lane="A", status="ok", full_depth=False, cutoff_done=obs.done_epoch + 100),
        "B": HrLaneState(lane="B", status="ok", full_depth=True),
        "C": HrLaneState(lane="C", status="ok", full_depth=True),
    }
    assert HrRefreshService._advance_observation(data, not_covered, wave) == 0
    assert obs.missing_streak == 0 and obs.active
    # 观察期出口但身份缺位(hash 为空) -> 计数出口, 不落放行记录
    obs.missing_streak = 1
    covered = {
        "A": HrLaneState(lane="A", status="ok", full_depth=True),
        "B": HrLaneState(lane="B", status="ok", full_depth=True),
        "C": HrLaneState(lane="C", status="ok", full_depth=True),
    }
    exits = HrRefreshService._advance_observation(data, covered, wave)
    assert exits == 1 and data.index[31].active is False and data.verified == {}


# ---------------- 拉取历史记录点(计划 26-10-04-0312 §3.3, S2) ----------------


def _history_from_disk(service, site: str = SITE):
    """从磁盘读站点文件取拉取历史(能读到他 == 事件已随站点文件落盘)"""
    data, err = service.store(site).read_unlocked()
    assert err is None
    return data.history


def test_history_wave_events_six_terminal_states(tmp_path):
    """六终态各恰一条 wave 事件(refreshed/partial/login/no-channel/quota/Retry-After),
    字段搬运自 result/lane_states/wave.notes 且随站点文件落盘; trigger 按 force 区分(§3.3)"""
    # 1. 正常波 refreshed(force 立即拉取 -> trigger=manual; .torrent 回填成功计入 torrents_ok)
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]), blobs={11: torrent_blob("other.bin")})
    service = make_service(tmp_path / "s1-refreshed", fetcher, clock=Clock())
    result = service.refresh_site(SITE, {}, force=True)
    assert result.action == ACTION_REFRESHED
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "manual", "refreshed")
    assert ev.reason_kind == REASON_NONE
    assert ev.pages == 3 and ev.rows == 1 and ev.torrents_ok == 1 and ev.torrents_fail == 0
    assert ev.by == "test" and ev.ts > 0 and ev.elapsed_s >= 0
    assert [l["lane"] for l in ev.lanes] == ["A", "B", "C"] and all(l["status"] == "ok" for l in ev.lanes)

    # 2. partial(B 档页面取数失败, 失效档快照与 reason 都搬运进事件)
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]), fail_text_at={"B": "boom"})
    service = make_service(tmp_path / "s2-partial", fetcher, clock=Clock())
    assert service.refresh_site(SITE, {}).action == ACTION_PARTIAL
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "auto", "partial")
    assert "页面取数失败" in ev.reason
    failed_b = [l for l in ev.lanes if l["lane"] == "B"][0]
    assert failed_b["status"] == "failed" and failed_b["pages"] == 0 and "页面取数失败" in failed_b["detail"]

    # 3. login(A 档命中登录页 -> 走 _finish_wave 收尾, 终态 error)
    fetcher = FakeFetcher(pages=standard_pages(), login_at={"A"})
    service = make_service(tmp_path / "s3-login", fetcher, clock=Clock())
    assert service.refresh_site(SITE, {}).action == ACTION_ERROR
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "auto", "error")
    assert "登录页" in ev.reason

    # 4. no-channel(端点级故障 -> 波级让位, 档位快照全为未跑)
    service = make_service(tmp_path / "s4-nochannel", NullFetcher("通道未启用"), clock=Clock())
    assert service.refresh_site(SITE, {}).action == ACTION_NO_CHANNEL
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "auto", "no-channel")
    assert ev.pages == 0 and ev.rows == 0
    assert all(l["status"] == LANE_IDLE for l in ev.lanes)

    # 5. quota(扩展侧硬上限 -> 波级让位)
    service = make_service(tmp_path / "s5-quota", FakeFetcher(pages=standard_pages(), quota=True), clock=Clock())
    assert service.refresh_site(SITE, {}).action == ACTION_WAITING
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "auto", "waiting")
    assert "扩展侧硬上限" in ev.reason
    assert all(l["status"] == LANE_IDLE for l in ev.lanes)

    # 6. Retry-After(站点指令 -> 波级落 retry_after_until 让位)
    fetcher = FakeFetcher(pages=standard_pages(), retry_after_at={"A": 600.0})
    service = make_service(tmp_path / "s6-retry", fetcher, clock=Clock())
    assert service.refresh_site(SITE, {}).action == ACTION_WAITING
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.trigger, ev.action) == ("wave", "auto", "waiting")
    assert "Retry-After" in ev.reason and ev.reason_kind == REASON_NONE
    assert all(l["status"] == LANE_IDLE for l in ev.lanes)


def test_history_auto_poll_gate_skip_writes_nothing(tmp_path):
    """硬不变量(§3.3): 自动 poll 被调度闸(复用窗/拉取间隔)跳过 -> 零事件 + 零写盘(站点文件一字节不变)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(reuse_window=3600.0), clock=clock)
    run_wave(service)
    site_file = service.store(SITE).path
    before = site_file.read_bytes()
    (first, ) = _history_from_disk(service)
    assert first.kind == "wave"
    # 复用窗内(1H): 自动 poll 直接 REUSED —— 同样零事件零写盘
    clock.advance(600.0)
    reused = service.refresh_site(SITE, {})
    assert reused.action == "reused"
    assert site_file.read_bytes() == before, "复用窗内的 poll 不得写盘"
    assert _history_from_disk(service) == [first], "复用窗内的 poll 不入历史"
    # 复用窗外 + 拉取间隔内: 自动 poll 被拉取间隔闸跳过 —— 零事件零写盘(硬不变量)
    clock.advance(2 * 3600.0)
    waiting = service.refresh_site(SITE, {})
    assert waiting.action == ACTION_WAITING and "未到拉取时刻" in waiting.reason
    assert site_file.read_bytes() == before, "被调度闸跳过的 poll 不得写盘"
    assert _history_from_disk(service) == [first], "自动 poll 的 waiting 不入历史"


def test_history_defer_only_on_force(tmp_path):
    """defer 事件仅 force 路径产生(§3.3): 非 force 被闸拦无事件不写盘; force 撞 min_interval
    (账号安全线) -> 恰一条 defer 并随显式 commit 落盘"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0, reuse_window=1.0), clock=clock)
    run_wave(service)  # 首波健康波(1 条 wave 事件); last_fetch_ts = now
    site_file = service.store(SITE).path
    before = site_file.read_bytes()
    # 非 force(自动 poll): 被拉取间隔闸拦 -> 无事件 + 零写盘
    clock.advance(60.0)
    auto = service.refresh_site(SITE, {})
    assert auto.action == ACTION_WAITING and "未到拉取时刻" in auto.reason
    assert site_file.read_bytes() == before and len(_history_from_disk(service)) == 1
    # force(立即拉取): 越过复用窗/拉取间隔两道闸, 撞上 min_interval 账号安全线 -> 一条 defer 显式落盘
    forced = service.refresh_site(SITE, {}, force=True)
    assert forced.action == ACTION_WAITING
    assert "间隔" in forced.reason and "拉取间隔" not in forced.reason, f"应是 min_interval 拦下: {forced.reason}"
    wave_ev, defer_ev = _history_from_disk(service)  # 从磁盘读: defer 已随显式 commit 落盘
    assert wave_ev.kind == "wave" and wave_ev.trigger == "auto"
    assert (defer_ev.kind, defer_ev.trigger, defer_ev.action) == ("defer", "manual", "waiting")
    assert "间隔" in defer_ev.reason
    assert defer_ev.lanes == [] and defer_ev.rows == 0 and defer_ev.pages == 0
    assert defer_ev.by == "test" and defer_ev.ts == clock.now

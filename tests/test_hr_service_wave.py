"""test_hr_service_wave 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_first_wave_deep_fetch: 首波深翻(全量效果) —— 未对账对象驱动覆盖深度
- test_stop1_completion_time_coverage: 停翻1. 完成时间覆盖(最深行早于最老对象减对齐余量 1D)
- test_stop2_zero_remain_streak: 停翻2. 到期段强信号(remain==0 连续 5 行, 全深度证明)
- test_stop2_cross_page_streak: 停翻2. 跨页延续计数
- test_order_violation_forced_stop: 排序失效 → 该档立即停翻, 失效点之前命中照常, 不签发放行
- test_header_missing_lane_failed: 表头缺失 → 该档失效, 其它档独立继续(档位独立)
- test_budget_truncation: 预算截断 → 截断点之前命中照常, 未列出待下波(不签发)
- test_release_signed_on_full_coverage: 覆盖完整 + 防伪通过 → 未列出放行签发
- test_freshness_gate_blocks_release: added_on 晚于本波取数 → 行 4(不签发放行)
- test_observing_seed_kept_managed_then_released: 上波考察中失踪 → 维持管束; 位置覆盖连续 2 波 → 判移出放行
- test_new_top_row_reconciled_next_wave: 顶页新插入(本机新下载)在下一波被完整覆盖对账
- test_retry_after_persisted_across_waves: Retry-After 指令落盘, 跨波生效, 期满前零请求
- test_retry_after_on_download_escalates_to_wave: .torrent 下载的 Retry-After 上抛波级, 不计种子失败
- test_version_mismatch_skips_wave: 站点文件 schema 比程序新 → 跳过取数与写盘(不覆写新版文件)
- test_fail_streak_resets_on_clean_wave: 失效波数清零 —— 连续失效只跨失效波延续, 恢复波清零, 单次失效不背历史(修复既有从未清零)
- test_interval_gate_waits_between_waves: 2.复用窗外 + 拉取间隔内 → WAITING「未到拉取时刻(拉取间隔)」(节奏闸门, 防频率放大)
- test_interval_gate_due_runs_next_wave: 3.健康波 + interval 到点 → 正常开波(默认节奏与解耦前一致)
- test_all_failed_wave_keeps_short_retry_rhythm: 6.全档失败波 healthy_ts 不前进 → 下一轮重试节奏不变
- test_partial_wave_advances_healthy_ts_failed_lane_waits: 7.部分失败波 healthy_ts 前进 → 失败档位等下一波
- test_wave_ts_refreshes_every_wave_not_frozen: C1 回归 —— lane.wave_ts 每波刷新(不冻结首成功波; 缺席证明新鲜度闸基准正确)

### 稳态降频(计划 26-10-05-0555 §2/S4; 锚点三态契约: None=采集失败不降频 / {}=确认零锚点可降频)
- test_idle_gate_releases_immediately_when_objects_become_nonempty: 稳态 2. 破稳态即时回退 —— 稳态期锚点翻非空, 下一 poll 立即开波(间隔闸沿用旧 healthy_ts)

### HR 排除落到取数侧(计划 26-10-08-1249 方案 B)

### HR 排除种子终态行身份下载短路(计划 26-10-09-1057 / issue 26-10-08-1304)
- test_wave_context_name_candidate_excludes_excluded_seed: 名称候选面=受管集(排除名不在); 命中面 local_hashes 仍全量
- test_a_lane_row_downloads_even_when_matching_excluded_seed: A 档硬规则不动 —— 行命中被排除种子仍无条件下载

### P1 覆盖率提升轮(T1.1 错误路径系统补齐)
- test_channel_quota_lets_wave_yield_and_warns_once: 扩展侧硬上限 -> 本波让位 + 每站只告警一次
- test_challenge_page_truncates_wave: 挑战页 = 页面取数失败(无 Retry-After) -> 波级截断
- test_daily_quota_exhausted_truncates_rest_lane: 日额用尽 -> 剩余档「预算受限」截断(首页即败 = LANE_FAILED)
- test_budget_take_gives_up_without_sleeper: 无 sleeper 时等不起 -> 该档本轮放弃(不持锁干等)
- test_budget_unit_wait_and_caps: _Budget 单元: waited 记账 / sleep_max / round_wait_max 上限(时钟起点与 last_fetch_ts 对齐, 等待记账 == 抖动间隔)
- test_pages_exhausted_mid_round_lane_not_scheduled: 页数上限耗尽 -> 未轮到的档「本波未轮到取数」
- test_order_direction_flip_forces_stop: 波内方向翻转 -> 强制早停(失效点之前有效)
- test_cross_page_disorder_forces_stop: 跨页乱序 -> 强制早停
- test_wave_pure_function_units: 波次纯函数单元: 档位摘要缺档形态 / 陈旧淘汰(模块级单点) / 位置覆盖 / 缺席证明
- test_lane_fail_streak_alerts_error: 连续 3 波同档失效 -> ERROR 升级(只提示人, 不改行为)

### S2 拉取历史记录点(计划 26-10-04-0312 §3.3)
  + 零写盘(站点文件一字节不变) —— 硬不变量

### R16 变异审计守阵(计划 26-10-09-1459 / issue 26-10-10-1108-test-hr-mutation-service-engine)

- test_stop_condition_zero_remain_streak_counts_from_zero: 停翻2. 连击起点为 0(单页 4 行全到期不足 5 不停翻)
- test_stop_condition_tail_nonzero_resets_streak: 停翻2. 页尾非到期行 -> 连击清零(非从 1 起算)
- test_stop_condition_empty_page_resets_streak: 停翻2. 空页不算整页全到期 -> 连击清零
- test_stop_condition_hit_object_skipped_in_oldest_scan: 停翻1. 已定论对象跳过但扫完其余(continue 非 break)
- test_stop_condition_trusted_done_keyed_by_hash: 停翻1. 可信完成时间按 infohash 取值
- test_stop_condition_oldest_is_min_not_last: 停翻1. 取最老可信完成时间(逐个取小)
- test_stop_condition_zero_done_not_selected_as_oldest: 停翻1. 完成时刻 0(未知)不参与最老判定
- test_stop_condition_slack_boundary_is_exclusive: 停翻1. 对齐余量边界(恰等不停翻, < 而非 <=)
- test_run_downloads_subsecond_retry_after_yields_wave: 下载 Retry-After 亚秒级也认 -> 上抛波级让位
- test_finish_wave_meta_and_result_fields: 波元数据(wave_ts/retention)与 result 汇总字段落盘
- test_finish_wave_releases_signed_includes_observation_exits: releases_signed = 批量签发 + 观察期出口
- test_finish_wave_depth_broken_reason_parse_and_alerted: depth_broken -> reason_kind=parse ∧ alerted=True
- test_finish_wave_alerted_from_parse_problem: alerted: 排序违反单因即告警(不依赖 had_error)
- test_finish_wave_empty_stamp_any_positive: 零行确认戳任何正数都生效(> 0 而非 > 1)
- test_finish_wave_single_row_clears_empty_stamp: 再现恰好 1 行即清确认戳(> 0 而非 > 1)
- test_finish_wave_truncation_note_boundary: 截断差值只在 rows < claim 时记(恰等不记)
- R22(issue 26-10-10-1108 余量函数守阵):
- test_run_pages_budget_denied_lane_does_not_abort_others: 档位被预算挡下只截断自己: 后续档仍被尝试(continue 非 break)
- test_run_pages_subsecond_page_retry_yields_wave: 页面级 Retry-After 亚秒级也认(> 0 而非 > 1): 上抛波级让位并落 retry_after_until
- test_run_pages_order_violation_lets_other_lanes_finish: 排序违反只强制停该档: 同轮其它档照常推进(continue 非 break)
- test_run_pages_last_page_completes_all_lanes: 翻到末页只结束该档: 同轮其它档照常收尾(continue 非 break)
- test_run_pages_unscheduled_lane_fail_streak_accumulates: 未轮到取数的档位失败计数跨波累加(+= 而非 = 1)
- test_do_wave_single_wait_cap_blocks_second_request: 单次等待上限从服务配置接进波内预算(sleep_max)
- test_do_wave_round_wait_cap_blocks_second_request: 本波累计等待上限从服务配置接进波内预算(round_wait_max)
- test_do_wave_retry_after_clamped_to_24h: 站点指令等待时刻按 24h 封顶
- test_finish_wave_ok_lanes_clear_fail_and_mismatch_streaks: 干净波清零: fail_streak / count_mismatch_streak 归 0
- test_finish_wave_empty_confirmed_at_reset_to_zero: 清单再现非零行: 人工对账戳清 0(不是 None)
- test_finish_wave_notes_joined_with_semicolon: 多条 note 以「 ; 」连接(持久化 notes 字段)
- test_finish_wave_notes_keep_url_separated_from_semicolon: URL 结尾的 note 与分隔分号之间必须有空格
- test_finish_wave_healthy_wave_has_no_retention_note: 留存达标(空基线)的波不得记「流转守恒不达标」note
- test_finish_wave_persist_false_reason_appends_after_existing_reason: 只读走查的未写盘说明追加在原有原因之后
- test_finish_wave_readonly_degradation_reason_appends_after_existing_reason: 锁自检失败(只读退化)说明追加在原有原因之后
- test_sign_releases_skips_unproven_then_signs_rest: 缺席证明不通过的先跳过(continue 非 break): 后续可签对象照常签发
- test_sign_releases_records_downloaded_tid: 观察期满放行: 记录带上该 infohash 曾经登记过的 tid
- test_wave_context_initial_invariants: _WaveContext 构造初值单点: 容器字段空容器(不是 None)、标志位显式 False
- test_sign_releases_hit_head_does_not_abort_rest: 本波命中对象跳过(continue 非 break): unmatched 首条命中也不拦后续签发

### 站点可选权限轮(计划 26-10-29-0147 W2/W4): 归层、判据与告警

### 覆盖率第三轮 T1b: 波次引擎长尾分支
- test_counter_claim_none_value_is_not_claimed: parse_counters 上交 None 值不上交(首个非 None 胜出口跳过弧)
- test_run_pages_final_sweep_classifies_active_lanes: 轮转收尾分类直驱 —— LANE_OK 档跳过不改写 / 零页档记失效
- test_downloaded_identity_backfills_row_not_in_index: 永久层身份回填(行不在索引但 downloaded 有记录)
- test_append_history_swallows_internal_error: 记录历史内部异常降级 WARNING 不外抛, 历史原样
- test_finish_wave_zero_listing_warn_gated_by_parse_problem: 零行波第二道守卫 —— parse_problem 在场不打 zero_listing 告警
"""

import logging

import re

import tempfile

import time

from datetime import datetime

from typing import Dict

import pytest

import auto_qb.hr.service as hr_service

from auto_qb.hr import events

from auto_qb.hr.fetcher import (
    HrChannelStopped,
    HrChannelTimeout,
    HrExtensionNetwork,
    HrExtensionNoPermission,
    HrFetchError,
    NullFetcher,
)

from auto_qb.hr.model import (
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    FETCH_LANES,
    LANE_EXEMPT,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDlFail,
    HrDownloaded,
    HrEntry,
    HrLaneState,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
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
    ACTION_REUSED,
    ACTION_WAITING,
    CHANNEL_SILENCE_WARN,
    COVERAGE_SLACK,
    DL_RETRY_COOLDOWN,
    FUZZY_NAME_K,
    HISTORY_NOTES_MAX,
    INDEX_RETENTION,
    LANE_FAIL_ALERT_STREAK,
    MISSING_GRACE_WAVES,
    HrRefreshResult,
    HrRefreshService,
    MAX_DOWNLOAD_RETRIES,
    REASON_BUDGET,
    REASON_NONE,
    REASON_PARSE,
    _absence_proven_all,
    _Budget,
    _lane_covers_done,
    _position_covered,
    _prune_index,
    _release_record,
    _settle_lane,
    _WaveContext,
    _lanes_summary_from,
    _mark_fetch_failed_lane,
    fuzzy_name_match,
)

from helpers import capture_logs

from hr_helpers import (
    CHALLENGE_PAGE,
    EMPTY_TABLE_PAGE,
    LOGIN_PAGE,
    REVISED_PAGE,
    Clock,
    FakeFetcher,
    global_conf,
    make_service as hr_make_service,
    myhr_page,
    row,
    site_conf,
    torrent_blob,
)

from hr_service_support import (
    DONE_NEW,
    DONE_OLD,
    E,
    SITE,
    T_DONE_NEW,
    URL,
    _Parsed,
    _expired,
    _live,
    _no_sleep,
    _site_file_json,
    anchor_for,
    counter_adapter,
    five_expired_rows,
    make_service,
    mk_blob,
    run_wave,
    standard_pages,
    url_of,
)


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


def test_idle_gate_releases_immediately_when_objects_become_nonempty(tmp_path):
    """稳态 2. 破稳态即时回退: 稳态期内新增本地种子(锚点翻非空 → 对象集翻非空) → 下一 poll
    立即开波 —— 无需等 idle 闸到点, 也不要求先有新的健康波(间隔闸沿用旧 healthy_ts 判已到点)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})  # 零锚点首波 → 稳态
    clock.advance(13 * 3600.0)  # 常态间隔(12H)已过, idle(24H)未到
    waiting = run_wave(service, {})
    assert waiting.action == ACTION_WAITING and "稳态降频" in waiting.reason
    # 稳态期内本机新下载一个种子 → 锚点翻非空(刚完成, 不吃超额线)
    _, h_new = mk_blob("BRAND NEW 99")
    anchors = {h_new: anchor_for("BRAND NEW 99", completion_on=T_DONE_NEW, seeding_time=0)}
    released = run_wave(service, anchors)
    assert released.action in (ACTION_REFRESHED, ACTION_PARTIAL), \
        f"破稳态即时回退: healthy+12H 早已过去, 下一 poll 应立即开波: {released.action} {released.reason}"
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.idle_mode is False


def test_wave_context_name_candidate_excludes_excluded_seed():
    """派生(计划 26-10-09-1057 S1): 名称候选面 `local_names_managed` 只含受管(未排除)种子名;
    命中面 `local_hashes` 仍从全量锚点构建(排除 ≠ 不认识)。"""
    exc = HrAnchor(added_on=1, downloaded=1, completion_on=-1, progress=1.0, name="EXC SHOW", excluded=True)
    keep = HrAnchor(added_on=1, downloaded=1, completion_on=-1, progress=1.0, name="KEEP SHOW", excluded=False)
    wave = _WaveContext({"HE": exc, "HK": keep})
    assert "KEEP SHOW" in wave.local_names_managed, "受管种子名在候选面"
    assert "EXC SHOW" not in wave.local_names_managed, "排除种子名不在候选面(不再驱动 .torrent 下载)"
    assert wave.local_hashes == {"HE", "HK"}, "命中面仍全量(排除 ≠ 不认识)"


def test_a_lane_row_downloads_even_when_matching_excluded_seed(tmp_path):
    """A 档硬规则不动(issue 明示): `lane == LANE_SCOPE` 在 `_process_rows` 里短路在前 ⇒ 行名即使
    命中被排除种子也**无条件**下载(与终态行的粗配触发器无关)。"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([row(21, "Example.Ultra.S01E01.1080p")], has_next=False),
        url_of("B"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    blob, h21 = mk_blob("Example.Ultra.S01E01.1080p")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    exc = HrAnchor(
        added_on=100,
        downloaded=1 << 30,
        completion_on=-1,
        progress=1.0,
        name="Example.Ultra.S01E01.1080p",
        excluded=True
    )
    run_wave(service, {h21: exc})
    assert "https://pt.example.com/download.php?id=21" in fetcher.byte_calls, \
        "A 档行无条件下载: 收窄名称候选面不该误伤 A 档硬规则"


def test_channel_quota_lets_wave_yield_and_warns_once(tmp_path):
    """扩展侧硬上限 -> 本波让位(ACTION_WAITING, 不计档位失败); 同站只 WARNING 一次"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(), quota=True)
    service = make_service(tmp_path, fetcher, clock=clock)
    with capture_logs("auto_qb.hr.service") as cap:
        first = run_wave(service, {})
        assert first.action == ACTION_WAITING
        assert "扩展侧硬上限" in first.reason
        data, _ = service.store(SITE).read_unlocked()
        assert data.wave.lanes == {}, "让位发生在波前, 不落任何档位状态"
        clock.advance(60.0)
        second = run_wave(service, {})
        assert second.action == ACTION_WAITING
    warns = [m for m in cap.messages if "扩展侧硬上限挡下取数" in m]
    assert len(warns) == 1, cap.messages
    assert any("仍生效(已告警过" in m for m in cap.messages)


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
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0), clock=clock, sleeper=None)
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


def test_lane_fail_streak_alerts_error(tmp_path):
    """连续 3 波同档失效 -> ERROR 升级(疑似改版建议走查); 只提示人, 失败处置不变"""
    clock = Clock()
    failed_pages = {**standard_pages(), url_of("A"): REVISED_PAGE}
    fetcher = FakeFetcher(pages=failed_pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    with capture_logs("auto_qb.hr.service") as cap:
        for _ in range(3):
            clock.advance(13 * 3600)
            run_wave(service)
    errors = [m for m in cap.messages if "已连续 3 波失效" in m]
    assert len(errors) == 1, cap.messages
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].fail_streak == 3
    assert data.wave.lanes["A"].status == "failed"


def test_stop_condition_zero_remain_streak_counts_from_zero(tmp_path):
    """停翻2. 跨页连击的**起点**是 0: 单页 4 行全到期不足 5 ⇒ 不停翻(不是 1+4=5 就停)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    stop, full, _why = service._stop_condition("B", _Parsed([_expired(i) for i in range(4)]), wave, {}, {})
    assert (stop, full) == (False, False)
    assert wave.zero_remain_streaks["B"] == 4


def test_stop_condition_tail_nonzero_resets_streak(tmp_path):
    """停翻2. 页尾非到期行 ⇒ 连击清零(不是从 1 起算)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    service._stop_condition("B", _Parsed([_expired(1), _live(2)]), wave, {}, {})
    assert wave.zero_remain_streaks["B"] == 0


def test_stop_condition_empty_page_resets_streak(tmp_path):
    """停翻2. 空页不算「整页全到期」⇒ 连击清零(空 entries 不得沿用上一页连击)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    wave.zero_remain_streaks["B"] = 3
    service._stop_condition("B", _Parsed([]), wave, {}, {})
    assert wave.zero_remain_streaks["B"] == 0


def test_stop_condition_hit_object_skipped_in_oldest_scan(tmp_path):
    """停翻1. 已定论(hit)的对象不驱动覆盖深度 —— 跳过它之后仍要扫完其余对象(continue 非 break)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    wave.hits = {"h1": "A"}
    objects = {"h1": anchor_for("h1"), "h2": anchor_for("h2")}
    wave.trusted_done = {"h2": E("2026-09-20 10:00:00")}
    stop, _full, why = service._stop_condition("A", _Parsed([_live(1, "2026-09-01 10:00:00")]), wave, objects, {})
    assert stop is True and "完成时间覆盖" in why


def test_stop_condition_trusted_done_keyed_by_hash(tmp_path):
    """停翻1. 可信完成时间按 **infohash** 取值(取 None/空键会让最老判定失效)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    objects = {"h2": anchor_for("h2")}
    wave.trusted_done = {"h2": E("2026-09-20 10:00:00")}
    stop, _full, _why = service._stop_condition("A", _Parsed([_live(1, "2026-09-01 10:00:00")]), wave, objects, {})
    assert stop is True


def test_stop_condition_oldest_is_min_not_last(tmp_path):
    """停翻1. 取对象里**最老**的可信完成时间(逐个比较取小), 不是被最后一个覆盖"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    objects = {"a": anchor_for("a"), "b": anchor_for("b")}
    wave.trusted_done = {"a": E("2026-09-20 10:00:00"), "b": E("2026-09-25 10:00:00")}
    stop, _full, _why = service._stop_condition("A", _Parsed([_live(1, "2026-09-21 10:00:00")]), wave, objects, {})
    assert stop is False  # 09-21 不早于 09-20 - 1D


def test_stop_condition_zero_done_not_selected_as_oldest(tmp_path):
    """停翻1. 完成时刻为 0(未知)的对象不参与最老判定(否则 oldest 归零 ⇒ 永不停翻)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    objects = {
        "a": anchor_for("a", completion_on=E("2026-09-20 10:00:00")),
        "b": anchor_for("b", completion_on=0),
    }
    stop, _full, _why = service._stop_condition("A", _Parsed([_live(1, "2026-09-01 10:00:00")]), wave, objects, {})
    assert stop is True


def test_stop_condition_slack_boundary_is_exclusive(tmp_path):
    """停翻1. 对齐余量边界: 最深行**恰好**等于「最老完成 - 1D」⇒ 不停翻(< 而非 <=)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    deepest = E("2026-09-01 10:00:00")
    objects = {"a": anchor_for("a", completion_on=deepest + COVERAGE_SLACK)}
    stop, _full, _why = service._stop_condition("A", _Parsed([_live(1, "2026-09-01 10:00:00")]), wave, objects, {})
    assert stop is False


def test_run_downloads_subsecond_retry_after_yields_wave(tmp_path):
    """下载收到 Retry-After(亚秒级也认) → 上抛波级让位, 不计种子失败"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(rows_a=[row(21, "LOCAL 21")]), retry_bytes_at={21: 0.5})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert result.torrents_failed == 0 and result.action == ACTION_WAITING
    assert data.retry_after_until >= clock.now


def test_finish_wave_meta_and_result_fields(tmp_path):
    """波元数据落盘: wave_ts=本波时刻; 无上波 A 行时 retention_ratio=-1 ∧ retention_ok=True;
    result 汇总字段(lane_texts/verified_count/persisted)如实填写"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20))), clock=clock)
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.wave_ts == clock.now
    assert data.wave.retention_ratio == -1.0
    assert data.wave.retention_ok is True
    assert result.verified_count == len(data.verified) == 1
    assert "A:" in result.lane_texts and "C:" in result.lane_texts
    assert result.persisted is True


def test_finish_wave_releases_signed_includes_observation_exits(tmp_path):
    """releases_signed = 批量签发 + 观察期出口(相加, 不是相减)"""
    clock = Clock()
    blob, h11 = mk_blob("EXAMPLE 11")
    fetcher = FakeFetcher(pages=standard_pages(rows_a=[row(11, "EXAMPLE 11")]), blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    fetcher.pages = standard_pages()
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    assert result.releases_signed == 1  # 批量签发 0 + 观察期出口 1


def test_finish_wave_depth_broken_reason_parse_and_alerted(tmp_path, monkeypatch):
    """depth_broken(计数对不平) ⇒ reason_kind=parse ∧ alerted=True"""
    clock = Clock()
    counter_adapter(monkeypatch, {"B": 50})
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    assert result.reason_kind == REASON_PARSE
    assert result.alerted is True


def test_finish_wave_alerted_from_parse_problem(tmp_path):
    """alerted: 排序违反(parse_problem)单因即告警 —— 不依赖 had_error, 也不依赖 depth_broken"""
    clock = Clock()
    bad = myhr_page(
        [
            row(11, "OTHER 11", done="2026-09-25 10:00:00"),
            row(12, "OTHER 12", done=DONE_OLD),
            row(13, "OTHER 13", done=DONE_NEW),
        ]
    )
    pages = {url_of("A"): bad, url_of("B"): myhr_page(five_expired_rows(20)), url_of("C"): myhr_page([])}
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    assert result.alerted is True


def test_finish_wave_empty_stamp_any_positive(tmp_path):
    """零行确认戳任何正数都生效(判据是 > 0 而非 > 1)"""
    clock = Clock()
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    with service.store(SITE).hold() as session:
        session.data.empty_confirmed_at = 1.0  # 任何正数都算确认戳
        session.commit(clock())
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" in data.verified


def test_finish_wave_single_row_clears_empty_stamp(tmp_path):
    """清单再现**恰好 1 行**即清确认戳(判据是 > 0 而非 > 1)"""
    clock = Clock()
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    with service.store(SITE).hold() as session:
        session.data.empty_confirmed_at = clock()
        session.commit(clock())
    clock.advance(13 * 3600)
    fetcher.pages = standard_pages(rows_a=[row(11, "OTHER 11")])  # 恰好 1 行
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.empty_confirmed_at == 0.0


def test_finish_wave_truncation_note_boundary(tmp_path, monkeypatch):
    """截断差值只在 rows < claim 时记(恰好相等不记)"""
    clock = Clock()
    counter_adapter(monkeypatch, {"A": 1, "B": 1, "C": 1})
    pages = {
        url_of("A", 1):
            myhr_page([row(11, "OTHER 11")], has_next=True),
        url_of("B", 1):
            myhr_page(five_expired_rows(20)[:1], has_next=True),
        url_of("C", 1):
            myhr_page([row(31, "OTHER 31", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")], has_next=True),
    }
    gconf = global_conf(max_pages_per_wave=3)
    service = make_service(
        tmp_path, FakeFetcher(pages=pages, blobs={11: torrent_blob(name="OTHER 11")}), gconf=gconf, clock=clock
    )
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    assert all(st.rows == 1 and st.count_claim == 1 and not st.full_depth for st in data.wave.lanes.values())
    assert "未翻完" not in result.reason


def test_run_pages_budget_denied_lane_does_not_abort_others(tmp_path):
    """档位被预算挡下只截断自己: 后续档仍被尝试(continue 非 break)—— 否则末档连截断记录都没有"""
    clock = Clock()
    pages = standard_pages([row(11, "OTHER 11")])
    service = make_service(tmp_path, FakeFetcher(pages=pages), gconf=global_conf(max_requests_per_day=1), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    for lane in ("B", "C"):
        st = data.wave.lanes[lane]
        assert "预算受限" in st.detail, f"{lane} 也应走到预算截断(continue 非 break)"


def test_run_pages_subsecond_page_retry_yields_wave(tmp_path):
    """页面级 Retry-After 亚秒级也认(> 0 而非 > 1): 上抛波级让位并落 retry_after_until"""
    clock = Clock()
    pages = standard_pages([row(11, "OTHER 11")])
    fetcher = FakeFetcher(pages=pages, retry_after_at={"B": 0.5})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_WAITING and "Retry-After" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    assert data.retry_after_until == clock.now + 0.5


def test_run_pages_order_violation_lets_other_lanes_finish(tmp_path):
    """排序违反只强制停该档: 同轮其它档照常推进(continue 非 break)"""
    clock = Clock()
    pages = {
        # A 页内逆序(09-25 后出现 09-01 → 再出现 09-20): 第 1 页即失效, 强制早停
        url_of("A", 1):
            myhr_page(
                [
                    row(11, "A 11", done="2026-09-25 10:00:00"),
                    row(12, "A 12", done=DONE_OLD),
                    row(13, "A 13", done=DONE_NEW),
                ]
            ),
        url_of("B", 1):
            myhr_page([row(21, "B 21", done=DONE_NEW)]),
        url_of("C", 1):
            myhr_page([]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert "排序违反" in data.wave.lanes["A"].detail
    assert data.wave.lanes["B"].status == "ok" and data.wave.lanes["B"].pages == 1, "B 档照常取完"


def test_run_pages_last_page_completes_all_lanes(tmp_path):
    """翻到末页只结束该档: 同轮其它档照常收尾(continue 非 break)"""
    clock = Clock()
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11", done=DONE_NEW)]),
        url_of("B", 1): myhr_page([row(21, "OTHER 21", done=DONE_NEW)]),
        url_of("C", 1): myhr_page([]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].status == "ok" and data.wave.lanes["A"].detail == "已翻到末页"
    assert data.wave.lanes["B"].status == "ok" and data.wave.lanes["B"].detail == "已翻到末页"


def test_run_pages_unscheduled_lane_fail_streak_accumulates(tmp_path):
    """未轮到取数的档位失败计数跨波累加(+= 而非 = 1): 连续 3 波才够升级告警线"""
    clock = Clock()
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11")]),
        url_of("B", 1): myhr_page([row(21, "OTHER 21")]),
        url_of("C", 1): myhr_page([row(31, "OTHER 31")]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), gconf=global_conf(max_pages_per_wave=1), clock=clock)
    for _ in range(LANE_FAIL_ALERT_STREAK):
        result = service.refresh_site(SITE, {}, force=True)
        assert result.action in (ACTION_REFRESHED, ACTION_PARTIAL)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["B"].fail_streak == LANE_FAIL_ALERT_STREAK, "每波未轮到 +1"
    assert data.wave.lanes["C"].fail_streak == LANE_FAIL_ALERT_STREAK


def test_do_wave_single_wait_cap_blocks_second_request(tmp_path):
    """单次等待上限从服务配置接进波内预算(sleep_max): 第 2 个请求的间隔等待越过上限即放弃(不持锁干等)"""
    clock = Clock()
    pages = standard_pages([])
    fetcher = FakeFetcher(pages=pages)
    # 首请求无间隔门槛(last_fetch_ts=0) => A 档首页必发; 之后 min_interval 门槛即生效
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0), clock=clock, sleep_max=1.0)
    run_wave(service, {})
    assert fetcher.text_calls, "首档首页仍发出(无门槛)"
    data, _ = service.store(SITE).read_unlocked()
    for lane in ("B", "C"):
        st = data.wave.lanes[lane]
        assert st.pages == 0 and "预算受限" in st.detail, f"{lane} 应被间隔等待上限挡下: {st.detail}"
    assert len(fetcher.text_calls) == 1, "越上限即放弃, 不再发后续页"


def test_do_wave_round_wait_cap_blocks_second_request(tmp_path):
    """本波累计等待上限从服务配置接进波内预算(round_wait_max): 累计越过上限即放弃"""
    clock = Clock()
    pages = standard_pages([])
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0), clock=clock, round_wait_max=1.0)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert len(fetcher.text_calls) == 1, "累计等待越过 round_wait_max 即放弃后续请求"
    for lane in ("B", "C"):
        assert data.wave.lanes[lane].pages == 0


def test_do_wave_retry_after_clamped_to_24h(tmp_path):
    """站点指令等待时刻按 24h 封顶: 更长的 Retry-After 不把站点永久锁死"""
    clock = Clock()
    pages = standard_pages([])
    fetcher = FakeFetcher(pages=pages, retry_after_at={"A": 30 * 3600.0})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_WAITING and "Retry-After" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    assert data.retry_after_until == clock.now + 24 * 3600.0, "30h 指令封顶到 24h"


def test_finish_wave_ok_lanes_clear_fail_and_mismatch_streaks(tmp_path):
    """干净波清零: 本波跑通的档 fail_streak / count_mismatch_streak 归 0(恢复后不背陈旧计数)"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    for lane in FETCH_LANES:
        st = data.wave.lanes[lane]
        assert st.ok and st.fail_streak == 0 and st.count_mismatch_streak == 0, f"{lane} 计数应清零"


def test_finish_wave_empty_confirmed_at_reset_to_zero(tmp_path):
    """清单再现非零行: 人工对账戳清 0(不是 None —— 站点文件不留 null 语义位)"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    run_wave(service, {})
    payload = _site_file_json(service)
    assert payload["empty_confirmed_at"] == 0.0, "非零行波后确认戳必须是 0.0"


def test_finish_wave_notes_joined_with_semicolon(tmp_path):
    """多条 note 以「; 」连接(持久化 notes 字段): 两条截断痕迹都要在"""
    clock = Clock()
    pages = {
        url_of("A"): "<html>改版了, 没有表格</html>",  # 表头缺失 -> 结构失效
        url_of("B"): myhr_page([]),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, fail_text_at={"B": "连接超时"})
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    notes = data.wave.notes
    assert "表" in notes and "页面取数失败" in notes, f"两条痕迹都应持久化: {notes!r}"
    assert notes.count(" ; ") == 1, f"分隔符是「 ; 」(URL 结尾的 note 不会与分号粘连): {notes!r}"
    assert "; " in data.history[-1].notes[0] or len(data.history[-1].notes) >= 1


def test_finish_wave_notes_keep_url_separated_from_semicolon(tmp_path):
    """note 以 URL 结尾时, 与后一条之间的分隔符必须是「 ; 」, URL 后不能直接贴分号"""
    clock = Clock()
    url_b, url_c = url_of("B"), url_of("C")
    fetcher = FakeFetcher(
        pages={url_of("A"): myhr_page([])},
        fail_text_at={
            "B": f"扩展取数失败: {url_b}",
            "C": f"扩展取数失败: {url_c}"
        },
    )
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert f"{url_b} ; " in result.reason, result.reason
    assert f"{url_c}" in result.reason, result.reason


def test_finish_wave_healthy_wave_has_no_retention_note(tmp_path):
    """留存达标(空基线)的波不得记「流转守恒不达标」note: 防伪只拦真不达标"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert "流转守恒" not in data.wave.notes
    assert data.wave.retention_ok is True


def test_finish_wave_persist_false_reason_appends_after_existing_reason(tmp_path):
    """只读走查的未写盘说明追加在原有原因之后(分号分隔, 不吞原有 reason)"""
    clock = Clock()
    pages = {url_of("A"): myhr_page([row(11, "OTHER 11")]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, fail_text_at={"B": "连接超时"})
    service = make_service(tmp_path, fetcher, clock=clock, persist=False)
    result = run_wave(service, {})
    assert result.reason.startswith("档位 B 页面取数失败: 连接超时 ; "), f"原有 reason 不被吞: {result.reason!r}"
    assert result.reason.endswith("只读模式, 未写盘")


def test_finish_wave_readonly_degradation_reason_appends_after_existing_reason(tmp_path):
    """锁自检失败(只读退化)的说明追加在原有原因之后: 原有 reason 不被吞"""
    clock = Clock()
    pages = {url_of("A"): myhr_page([row(11, "OTHER 11")]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, fail_text_at={"B": "连接超时"})
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)  # anchors=None: 非稳态, 拉取间隔取 refresh_interval(12h)
    service.store(SITE)._last_write_rev = 10_000  # 下一波锁自检判不生效 -> 只读退化
    clock.advance(13 * 3600)
    result = run_wave(service)
    assert result.persisted is False
    assert result.reason.startswith("档位 B 页面取数失败: 连接超时 ; 锁自检失败"), f"reason 拼接口径: {result.reason!r}"


def test_sign_releases_skips_unproven_then_signs_rest(tmp_path):
    """缺席证明不通过的先跳过(continue 非 break): 后续可签对象照常签发, 计数逐条累加"""
    clock = Clock()
    pages = {url_of("A"): myhr_page([row(11, "OTHER 11")]), url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    anchors = {
        "h_future": anchor_for("FUTURE 1", completion_on=T_DONE_NEW, added_on=2_000_000_000),  # 新鲜度闸拦下
        "h_a": anchor_for("GHOST A", completion_on=T_DONE_NEW),
        "h_b": anchor_for("GHOST B", completion_on=T_DONE_NEW),
    }
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h_future" not in data.verified, "added_on 晚于本波取数 -> 无证明力, 不签发"
    assert "h_a" in data.verified and "h_b" in data.verified, "跳过不拦后续对象"
    assert result.releases_signed == 2, f"逐条累加(不是 1/3): {result.releases_signed}"
    rec = data.verified["h_a"]
    assert rec.tid == 0 and rec.source == SOURCE_NOT_LISTED
    assert rec.has_anchor_snapshot and rec.anchor_downloaded == anchors["h_a"].downloaded


def test_sign_releases_records_downloaded_tid(tmp_path):
    """观察期满放行: 记录带上该 infohash 曾经登记过的 tid(站点换 tid 重列时能对上)"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    pages = {url_of("A"): myhr_page([row(11, "EXAMPLE 11")]), url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    clock.advance(13 * 3600)
    run_wave(service, anchors)  # 连续 2 波位置被覆盖且未重见 -> 判移出
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].active is False and h11 in data.verified
    assert data.verified[h11].tid == 11, "放行记录带原 tid(不是 0/None/1)"
    assert data.verified[h11].source == SOURCE_NOT_LISTED
    assert data.verified[h11].has_anchor_snapshot


def test_wave_context_initial_invariants():
    """_WaveContext 构造初值单点: 容器字段空容器(不是 None)、标志位显式 False(不是
    None)、current_lane 空串(尚未取页) —— 波级临时量, 一个 None 初值就能在后续
    写路径上炸/在布尔判断上静默变形"""
    wctx = _WaveContext({})
    assert wctx.local_hashes == set() and wctx.local_names_managed == ()
    assert wctx.seen == {} and wctx.hits == {} and wctx.pending_downloads == set()
    for name in (
        "dl_by_hash",
        "order_directions",
        "prev_dones",
        "zero_remain_streaks",
        "trusted_done",
        "counter_claims",
    ):
        assert getattr(wctx, name) == {}, f"{name} 初值必须空字典(不是 None)"
    assert wctx.current_lane == "", "未取页时 current_lane 空串(不是 None/哨兵串)"
    assert wctx.parse_problem is False and wctx.budget_limited is False and wctx.had_error is False, \
        "标志位初值显式 False(is False, 不是 falsy None)"
    assert wctx.retracted == 0 and wctx.notes == []


def test_sign_releases_hit_head_does_not_abort_rest(tmp_path):
    """本波命中对象跳过(continue 非 break): unmatched 首条命中也不拦后续对象的签发"""
    clock = Clock()
    blob_hit, h_hit = mk_blob("HIT ME")
    pages = {
        url_of("A"): myhr_page([row(11, "HIT ME")]),  # 下载登记后精配命中 -> wave.hits
        url_of("B"): myhr_page([row(99, "OTHER 99", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")]),
        url_of("C"): myhr_page([row(98, "OTHER 98", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob_hit})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {
        h_hit: anchor_for("HIT ME", completion_on=T_DONE_NEW),
        "h_ghost": anchor_for("GHOST 1", completion_on=T_DONE_NEW),
    }
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].infohash_v1 == h_hit and h_hit not in data.verified, "本波命中不放行"
    assert "h_ghost" in data.verified, "跳过命中的不拦后续对象"
    assert result.releases_signed == 1, f"逐条累加(不是 0/2): {result.releases_signed}"


# ---------- 覆盖率第三轮 T1b: 波次引擎长尾分支 ----------


def test_counter_claim_none_value_is_not_claimed(tmp_path, monkeypatch):
    """parse_counters 上交 None 值 = 该档无声明(首个非 None 胜出口的跳过弧): count_claim 保持 None"""
    counter_adapter(monkeypatch, {"A": None, "B": 5, "C": 0})
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=Clock())
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].count_claim is None, "None 值不上交(降级现状: 视同无计数)"
    assert data.wave.lanes["A"].count_match is None
    assert data.wave.lanes["B"].count_claim == 5 and data.wave.lanes["B"].count_match is True
    assert data.wave.lanes["C"].count_claim == 0, "0 是合法声明值(不是 None), 照常上交"
    assert result.action == ACTION_REFRESHED


def test_run_pages_final_sweep_classifies_active_lanes(tmp_path):
    """轮转收尾分类(直驱 pages_left=0): 已是 LANE_OK 的活跃档直接跳过不改写; 零页档记「未轮到」失效"""
    from auto_qb.hr.service import _dl_by_hash

    from hr_service_support import _StubAdapter, _dl_budget

    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages()), clock=clock)
    with service.store(SITE).hold() as session:
        data = session.data
        result = HrRefreshResult(site=SITE, action=ACTION_REFRESHED)
        wave = _WaveContext({})
        wave.dl_by_hash = _dl_by_hash(data)
        lanes = {
            "A": HrLaneState(lane="A", status=LANE_OK, detail="已翻到末页"),
            "B": HrLaneState(lane="B", status=LANE_IDLE),
            "C": HrLaneState(lane="C", status=LANE_IDLE),
        }
        service._run_pages(
            SITE,
            _StubAdapter(),
            data,
            session,
            result,
            _dl_budget(service, data),
            wave,
            lanes,
            objects={},
            unmatched={},
            pages_left=0,
        )
        assert lanes["A"].status == LANE_OK and lanes["A"].detail == "已翻到末页", "已完成档不被二次收尾改写"
        assert lanes["B"].status == LANE_FAILED and lanes["B"].fail_streak == 1, "零页档记失效"
        assert lanes["B"].detail == "本波未轮到取数(预算被其它档耗尽)", "pages_left<=0 的零页档文案"
        assert lanes["C"].status == LANE_FAILED, "逐档分类(continue 非 break)"


def test_downloaded_identity_backfills_row_not_in_index(tmp_path):
    """永久层身份回填: 行不在活跃索引但 downloaded 有记录 -> infohash 从永久层回填, 永不重取"""
    clock = Clock()
    blob, h1 = mk_blob("LOCAL 21")
    fetcher = FakeFetcher(pages=standard_pages(rows_b=[row(21, "OTHER 21", done=DONE_OLD)]))
    service = make_service(tmp_path, fetcher, clock=clock)
    with service.store(SITE).hold() as session:
        session.data.downloaded[21] = HrDownloaded(tid=21, ts=clock.now, name="LOCAL 21", infohash_v1=h1)
        session.commit(clock())
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].infohash_v1 == h1, "行身份从永久层回填(不用重新下载)"
    assert data.index[21].infohash_v2 == ""
    assert result.torrents_fetched == 0, "已下载过: 同 tid 永不重下"


def test_append_history_swallows_internal_error(tmp_path):
    """历史是纯观测: 记录内部异常降级为 WARNING 不外抛进取数主流程, 历史原样"""
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages()), clock=Clock())
    data, _ = service.store(SITE).read_unlocked()
    before = list(data.history)
    with capture_logs("auto_qb.hr.service") as cap:
        service._append_history(SITE, data, kind="wave", trigger="auto", result=object())  # 缺字段 -> 内部异常
    assert list(data.history) == before, "异常路径不写历史"
    assert any("记录拉取历史失败" in m for m in cap.messages), cap.messages


def test_finish_wave_zero_listing_warn_gated_by_parse_problem(tmp_path, monkeypatch):
    """零行波第二道守卫: parse_problem 在场 -> 不打 zero_listing 告警(754 假弧); 干净零行波才打"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages()), clock=clock)
    warns = []
    monkeypatch.setattr(service, "_warn_parse", lambda *a, **k: warns.append(a))
    site_c = service.site_confs[SITE]

    def _zero_wave(wave):
        with service.store(SITE).hold() as session:
            result = HrRefreshResult(site=SITE, action=ACTION_REFRESHED)
            lanes = {lane: HrLaneState(lane=lane, status=LANE_OK, full_depth=True) for lane in FETCH_LANES}
            service._finish_wave(SITE, site_c, session.data, session, result, wave, lanes, unmatched={})
            session.commit(clock())
        return result

    wave = _WaveContext({})
    wave.parse_problem = True
    result = _zero_wave(wave)
    assert "结构完好但清单为 0" in result.reason, "零行 note 仍在(第一道守卫, 752)"
    assert warns == [], "parse_problem 在场 -> zero_listing 告警被第二道守卫跳过"

    result2 = _zero_wave(_WaveContext({}))
    assert "结构完好但清单为 0" in result2.reason
    assert len(warns) == 1 and SITE in warns[0][1], "干净零行波(无 parse_problem)才打 zero_listing 告警"
    assert result2.alerted is True, "零行未确认也是告警态"

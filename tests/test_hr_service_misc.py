"""test_hr_service_misc 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_retention_check_freezes_batch: A 档流转守恒不达标 → 批量签发冻结
- test_retention_does_not_block_observation: 守恒拦批量但不拦观察期(单条失踪无死锁)
- test_observing_seed_resighted: 失踪种子重见 → streak 清零按档位定论
- test_no_objects_sweeps_to_last_page: 空对象集仍按停翻条件/末页收尾(轻量波已否决, 26-09-29 裁决)
- test_no_fuse_no_suspension: 失败不推进熔断/停用(v3 删除), Retry-After 记等待
- test_interval_empty_page_keeps_manual_stamp: T52. 分页区间形空表无标记(claim=None) —— 维持 zero_listing 人工戳路径
- test_channel_timeout_routes_to_no_channel: 等扩展超时 ⇒ 通道层(action=no-channel · 不写 wave.notes · 不推进档位失败)
- test_event_domains_are_declared: 事件 → 归属层单点(parse=站点 / login=账号 / silence·channel=通道)
- test_channel_unavailable_has_own_label: 通道不可用文案带独立标签, 不借 [HR 页面改版]
- test_channel_timeout_never_upgrades_to_page_changed: 连续多波通道不可用也不升成「疑似改版」ERROR
- test_generic_fetch_error_still_page_failure: 边界回归 —— 真页面失败仍按站点层处理(收层不一刀切)
- test_reuse_window_uses_min_of_config_and_interval: 1.复用窗时长 = min(reuse_window, 拉取间隔)(计划 26-09-30-0240), 窗内 REUSED 语义不变
- test_reuse_window_never_exceeds_interval: 1b. clamp 另一半 —— 复用窗 > 拉取间隔时静默收敛到拉取间隔
- test_reuse_window_not_extended_by_idle_interval: 1c. 复用窗公式 min(reuse_window, refresh_interval) 不跟随 idle —— 稳态降频只动节奏闸, 新鲜度窗不放大(计划 26-10-05-0555 §2.7 不变项)
- test_force_bypasses_reuse_and_interval_gates: 4.立即拉取(force)→ 跳过复用窗与拉取间隔两道闸
- test_force_still_respects_min_interval: 5.force 不越账号安全线 —— min_interval 未到仍 WAITING
- test_refresh_all_force_not_blocked_by_gates: 8.走查 refresh_all(force=True)不被两道闸挡(--hr-once 语义)

### 稳态降频(计划 26-10-05-0555 §2/S4; 锚点三态契约: None=采集失败不降频 / {}=确认零锚点可降频)
- test_idle_interval_used_when_objects_empty: 稳态 1. 零锚点站点(对象集空)healthy+idle 内 WAITING(理由带「稳态降频」), 过 idle 闸正常开波
- test_anchor_collection_failure_disables_idle: 稳态 3. 锚点采集失败(None)≠稳态 —— 常态间隔照常判闸, wave 行为与实施前一致
- test_zero_anchors_site_still_idles: 稳态 4. 显式 {}(采集成功零种子)照常降频 —— 与失败路径的区分回归钉
- test_idle_mode_flip_persists_once: 稳态 5. 旗标仅翻转时写盘(翻转恰一次, 稳态期反复 poll 零额外写), JSON 往返保真

### HR 排除落到取数侧(计划 26-10-08-1249 方案 B)
- test_build_objects_skips_hr_excluded_anchor: excluded 锚点不进对象集; 未排除锚点照常进(零静默变更)
- test_hr_excluded_anchor_does_not_break_idle: 站点只剩被排除种子 ⇒ 对象集空 ⇒ 稳态降频照常生效(实施前的回归钉)

### 取数侧强制 fetchable(issue 26-10-05-0922)
- test_fetchable_filter_skips_none_listing_site: 全站型(listing=none)不进取数集合(refresh_all 零波次); 展示口径(enabled_sites/build_views)照常含它

### HR 排除种子终态行身份下载短路(计划 26-10-09-1057 / issue 26-10-08-1304)

### P1 覆盖率提升轮(T1.1 错误路径系统补齐)
- test_refresh_site_guard_paths: 站点未接入 / 全局开关关 / result.ok 属性
- test_refresh_site_unknown_adapter: 未登记的 adapter -> ACTION_ERROR(不外抛)
- test_refresh_site_lock_busy_returns_locked: 站点锁被其它实例持有 -> ACTION_LOCKED
- test_refresh_site_internal_error_contained: 非取数异常 -> ACTION_ERROR + alerted, 不外抛
- test_login_page_detected_by_adapter_and_warned_once: 登录页由 adapter 形态识别(非扩展异常) + 登录告警每站一次(恢复重置: 正常波清标记, 再失效重新报)
- test_missing_fields_abort_after_valid_page: 必填字段缺失页在第 2 页 -> 截断点之前数据有效(LANE_OK 非全深度)
- test_tail_zero_partial_reset: 页尾部分到期行 -> 跨页累计重新起算
- test_run_downloads_unit_paths: 下载单元: 待回填缺行 / 已有身份跳过 / 永久层回填命中与不命中 / 预算止步
- test_download_invalid_blob_counted_as_fail: .torrent 内容非法 -> 计种子失败不外抛, fail.last_ts 记注入时钟(26-10-02-0526 时钟收编守阵)
- test_readonly_degradation_noted_in_result: 锁自检失败(只读退化) -> 波照跑但不写盘, reason 注明
- test_merge_seen_refreshes_last_seen: 合并口刷新 last_seen(本波已见行=合并时刻, 未重见条目冻结在最后见到时刻) —— issue 26-10-01-2335 写入点, 详情表导出契约随点亮
- test_index_retention_prune_revives: INDEX_RETENTION 复活链 —— 退役条目距 last_seen 超期被清理 / 活跃条目与观察期条目不误清 / 放行记录不随索引清理丢失 / 淘汰落盘
- test_build_objects_unit_guards: 对象集现算单元: 空 hash / 非活跃条目 / 锚点漂移回炉 / 已放行未漂移不回对象集(issue 26-10-02-0526)
- test_build_views_skips_disabled_and_channel_states: 视图构建跳过未启用站点; 通道状态 ok/silent/disabled 与无锁读
- test_freeze_and_observation_guards: 终态冻结: 档位本波失效 -> 维持原状; 观察期: 位置未覆盖冻结计数; 出口身份缺位不落记录

### S2 拉取历史记录点(计划 26-10-04-0312 §3.3)
  + 零写盘(站点文件一字节不变) —— 硬不变量

### R16 变异审计守阵(计划 26-10-09-1459 / issue 26-10-10-1108-test-hr-mutation-service-engine)

- test_run_downloads_continues_after_backfill: 回填分支后继续处理后续 tid(continue 非 break)
- test_run_downloads_cooldown_gate_boundaries: 下载失败冷却闸(达上限且窗内跳过 / 恰到期放行)
- test_run_downloads_failure_paths_count_and_continue: 失败路径各计一次并 continue; 计数累加; 告警文案保留
- test_run_downloads_registers_hash_pending_and_clears_fail: 成功落 dl_by_hash(v1/v2)/tid 出队/清失败记账
- test_run_downloads_downloaded_record_fields: HrDownloaded 记录字段(ts/name 取 torrent 名/v1 v2 双写)
- R22(issue 26-10-10-1108 余量函数守阵):
- test_run_pages_page_cap_one_keeps_rotation_bounded: 单波页数下限是 1: max_pages_per_wave=1 时每档恰取 1 页(不是 0 页也不是 2 页)
- test_run_pages_merge_seen_uses_now: 合并口传入取数时刻(不是 None): 索引行 last_seen = 本波时刻
- test_run_pages_commits_stamp_writer_heartbeat: 增量落盘时间戳 = 本波时刻(不是 None): 站点文件 heartbeat
- test_refresh_locked_reuse_window_boundary_refetches: 复用窗边界是「到期即取」(expires_at > now)
- test_refresh_locked_reuse_path_fills_result_fields: 复用(不取数)路径也回填结果字段
- test_refresh_locked_fetch_interval_reason_exact_seconds: 拉取间隔闸门: 还差多少秒如实算(due - now), action=WAITING
- test_refresh_locked_min_interval_force_defers_with_exact_seconds: force 撞账号安全线(min_interval): 让位 + defer 历史, 还差秒数如实
- test_advance_observation_multi_entry_exit_counts: 观察期逐条目推进: 位置未证明的 streak 冻结, 被覆盖的连续 2 波后各自出口
- test_version_mismatch_reason_exact_text: 版本回退的跳过说明文案单点
- test_read_error_recovers_with_empty_data: 站点文件读坏: 坏文件挪走 + 本波按空数据保守跑
- test_refresh_all_anchors_map_shape_passthrough: refresh_all 三态直通: 顶层 None → 各站 None; 映射缺站键 → {}; 带站键原样透传
- test_build_view_for_passes_listing_state_generated: build_view_for 透传单点: conf.listing / channel_state(按内存 data, 不是回读盘) / generated_at=当前时刻
- test_absence_proven_all_boundary_matrix: _absence_proven_all 判据边界单点: 完成时间不可信/wave_ts=0/added_on 恰等/cutoff 恰等四边
- test_advance_observation_scope_exit_resets_streak: A 档观察条目连续 2 波位置覆盖出口: 出口后 streak 显式清零(不是 None)
- test_position_proof_cutoff_zero_is_unprovable: issue 26-10-30-0550 守阵 —— cutoff_done<=0 ∧ 非全深度
  ⇒ 位置不可证(三判据同口径 `_lane_covers_done`), 并反向钉死全深度 / 边界已越过的正常路径不被拦死

### 站点可选权限轮(计划 26-10-29-0147 W2/W4): 归层、判据与告警
- test_no_permission_is_channel_layer_and_persisted: 缺站点权限归通道层(fail_streak 不增长)+ 落盘
  channel_last_error + channel_state 出 no-permission(改回 HrFetchError 即红)
- test_network_failure_persists_network_kind: 网络层落成**不同** kind(动作不同: 查代理 vs 去授权)
- test_channel_error_cleared_on_recovery: 拿到正常内容页即清通道痕(告警态与展示态同一恢复点)
- test_page_fetch_failure_escalates_after_streak: 页面层连续 3 波同档失效 ⇒ ERROR 升级(D8: 只接页面层;
  改前 fail_streak 涨到 58 也没有一句「疑似改版」)
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
    FakeFetcher,
    global_conf,
    make_service as hr_make_service,
    myhr_page,
    row,
    site_conf,
    torrent_blob,
)

from clock import FakeClock
from hr_service_support import (
    DONE_NEW,
    DONE_OLD,
    E,
    SITE,
    T_DONE_NEW,
    URL,
    _StubAdapter,
    _TimeoutFetcher,
    _dl_budget,
    _gconf_channel_off,
    _history_from_disk,
    _no_sleep,
    _page_with_blank_required_row,
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


def test_retention_check_freezes_batch(tmp_path):
    """A 档流转守恒: 上波 A 行本波留存 < 70% → 批量「未列出」签发冻结(命中不受影响)"""
    clock = FakeClock()
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
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.retention_ok is False
    assert abs(data.wave.retention_ratio - 1 / 3) < 1e-9  # 观测值如实落盘(非 -1 哨兵 / 字段不丢)
    assert result.alerted is True  # 守恒不达标 = 产生处已告警(单因即成立)
    assert "h1" not in data.verified  # 批量签发被冻结(即便覆盖证明成立)


def test_retention_does_not_block_observation(tmp_path):
    """守恒只拦批量签发, 不拦观察期状态机(22:38 定稿): 单条失踪照常推进, 无死锁"""
    clock = FakeClock()
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


def test_observing_seed_resighted(tmp_path):
    """失踪种子重见 → streak 清零, 按当波档位定论"""
    clock = FakeClock()
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


def test_merge_seen_refreshes_last_seen(tmp_path):
    """合并口刷新 last_seen: 本波已见行 = 合并时刻; 未重见条目冻结在最后见到时刻(写入点修复)"""
    clock = FakeClock()
    pages = standard_pages(
        rows_b=[row(21, "OTHER 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
        rows_c=[row(22, "OTHER 22", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
    )
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    t0 = clock.now()
    run_wave(service)
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
    t1 = clock.now()
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False
    assert data.index[21].last_seen == t0, "退役条目不再进合并口: last_seen 冻结在最后见到时刻(淘汰计时起点)"
    assert data.index[22].active is True and data.index[22].last_seen == t1, "重见条目 last_seen 刷新"
    # 详情表导出契约(webui 表1「最近被见到」列): last_seen 随写入点亮起
    details = {d.tid: d for d in entry_details(data)}
    assert details[21].last_seen == t0 and details[22].last_seen == t1


def test_index_retention_prune_revives(tmp_path):
    """INDEX_RETENTION 复活链: 退役条目超期(距 last_seen > 30 天)被清理 / 活跃与未超期退役条目保留 /
    放行记录不随索引清理丢失 / 淘汰结果落盘"""
    clock = FakeClock()
    blob11, _h11 = mk_blob("OTHER 11")
    blob21, h21 = mk_blob("EXAMPLE 21")
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW)],
        rows_b=[row(21, "EXAMPLE 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")],
    )
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11, 21: blob21})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    t0 = clock.now()
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
    t2 = clock.now()
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert 21 not in data.index, "退役条目距 last_seen 超过 INDEX_RETENTION: 被清理"
    assert data.index[11].active and data.index[11].last_seen == t2, "活跃条目不被误清且 last_seen 持续刷新"
    assert h21 in data.verified, "放行记录是永久层, 不随索引清理丢失"
    assert result.entries == len(data.index) == 1, "淘汰结果反映进波次回执(索引只剩活跃条目 11)"
    assert 21 not in service.store(SITE).read_unlocked()[0].index, "淘汰结果已落盘(下一波不会复活)"


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


def test_no_fuse_no_suspension(tmp_path):
    """页面失败 → 该档截断, 下周期自然重试; 不存在熔断/停用状态(数据上无 fuse/suspended 字段)"""
    clock = FakeClock()
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


def test_interval_empty_page_keeps_manual_stamp(tmp_path, monkeypatch, caplog):
    """T52. 分页区间形空表(无标记 ⇒ claim=None): 自证空不可用 → 维持 zero_listing 人工戳路径。"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = FakeClock()
    counter_adapter(monkeypatch, {})  # 区间形空表无计数标记: 覆写了也拿不到键
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert "h1" not in data.verified and data.wave.releases_enabled is False
    assert "清单为 0" in result.reason  # 人工对账戳路径保留(--hr-confirm-empty)
    assert result.alerted is True  # 零行未确认 = 产生处已告警
    assert "若确认账号的 HR 清单确实为空" in caplog.text


def test_reuse_window_uses_min_of_config_and_interval(tmp_path):
    """1. 复用窗时长 = min(reuse_window, 拉取间隔): 新鲜度不再借用节奏值(12H→2H); 窗内再跑 → REUSED(既有语义不变)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)  # 默认 reuse_window=2H, interval=12H
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.expires_at == clock.now() + 2 * 3600.0, "min(2H, 12H) = 2H —— 不再是 12H"
    result = run_wave(service)
    assert result.action == "reused"


def test_reuse_window_never_exceeds_interval(tmp_path):
    """1b. clamp 另一半: 复用窗(2H) > 拉取间隔(1H) → 生效 1H(拉取间隔是硬节奏, 静默收敛不报错)"""
    clock = FakeClock()
    service = make_service(
        tmp_path,
        FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])),
        site=site_conf(refresh_interval=3600.0),
        clock=clock
    )
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.expires_at == clock.now() + 3600.0


def test_reuse_window_not_extended_by_idle_interval(tmp_path):
    """1c. 复用窗公式不跟随 idle(计划 26-10-05-0555 §2.7 不变项): 稳态降频只动拉取间隔闸,
    复用窗仍 = min(reuse_window, refresh_interval) —— 新鲜度与节奏解耦, 稳态期窗不放大到 24H"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)  # 默认 reuse_window=2H / refresh=12H / idle=24H
    run_wave(service, {})  # 确认零锚点 → 稳态降频生效
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.idle_mode is True, "前置: 零对象站点已进稳态"
    assert data.expires_at == clock.now() + 2 * 3600.0, "稳态期复用窗仍 min(2H, 12H)=2H, 不跟随 idle(24H)"


def test_force_bypasses_reuse_and_interval_gates(tmp_path):
    """4. 立即拉取(force)→ 跳过复用窗与拉取间隔两道闸, 时钟未动也直接开波"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts > 0 and data.expires_at > clock.now(), "前置: 处于复用窗 + 拉取间隔内"
    result = service.refresh_site(SITE, {}, force=True)
    assert result.action in ("refreshed", "partial"), f"force 应越过两道闸, got: {result.action} {result.reason}"


def test_force_still_respects_min_interval(tmp_path):
    """5. 立即拉取不越过账号安全线: min_interval 未到 → 仍 WAITING(间隔, 非「拉取间隔」)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, gconf=global_conf(min_interval=90.0), clock=clock)
    run_wave(service)  # 页面请求已发出: last_fetch_ts = now
    result = service.refresh_site(SITE, {}, force=True)  # 时钟未动: min_interval 必然未到
    assert result.action == ACTION_WAITING
    assert "间隔" in result.reason and "拉取间隔" not in result.reason, \
        f"等待原因应是 min_interval 而非拉取间隔闸门: {result.reason}"


def test_refresh_all_force_not_blocked_by_gates(tmp_path):
    """8. 走查语义: refresh_all(force=True) 在复用窗/拉取间隔内仍开波(--hr-once 不被新闸门挡)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    clock.advance(60.0)  # 复用窗(2H)与拉取间隔(12H)都远未到
    blocked = service.refresh_all()
    assert blocked[0].action == "reused", "不带 force: 复用窗内照旧复用"
    forced = service.refresh_all(force=True)
    assert forced[0].action in ("refreshed", "partial"), "force=True: 走查立即开波"


def test_idle_interval_used_when_objects_empty(tmp_path):
    """稳态 1. 零锚点站点(对账对象集为空): healthy+idle 间隔内 WAITING 且理由带「稳态降频」标记,
    过 idle 闸后正常开波 —— 降频只动节奏闸, 波的形态不变"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    first = run_wave(service, {})  # 首波 healthy_ts=0 间隔闸不拦, 照常开波并立稳态旗
    assert first.action in (ACTION_REFRESHED, ACTION_PARTIAL)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts == clock.now() and data.wave.idle_mode is True
    clock.advance(3 * 3600.0)  # 复用窗(2H)外, idle 间隔(24H)内
    waiting = run_wave(service, {})
    assert waiting.action == ACTION_WAITING
    assert "未到拉取时刻" in waiting.reason and "稳态降频" in waiting.reason
    clock.advance(21 * 3600.0 + 60.0)  # 过 idle 闸(累计 24H+60s)
    assert run_wave(service, {}).action in (ACTION_REFRESHED, ACTION_PARTIAL)


def test_anchor_collection_failure_disables_idle(tmp_path):
    """稳态 3. 锚点采集失败(None)≠稳态(§2.5, 报告 R5 唯一实质风险): 常态间隔照常判闸 ——
    已过 12H 即开波不吃 idle 降频; wave 拿到空锚点, 行为与实施前一致"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})  # 首波零锚点 → 稳态立旗
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.idle_mode is True
    clock.advance(13 * 3600.0)  # 常态间隔(12H)已过, idle(24H)未到
    result = run_wave(service, None)  # anchors=None: 采集失败/未知原样直通(不被吞成 {})
    assert result.action in (ACTION_REFRESHED, ACTION_PARTIAL), \
        f"采集失败不构成稳态: 常态间隔已到应立即开波: {result.action} {result.reason}"
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.idle_mode is False and data.wave.lanes["A"].status == "ok"


def test_zero_anchors_site_still_idles(tmp_path):
    """稳态 4. 显式 {}(采集成功但该站零种子)照常降频 —— 与失败路径的区分回归钉:
    同为「13H 处 poll」, {} 等 idle 闸; None 立即开波(test_anchor_collection_failure_disables_idle)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})  # 确认零锚点 → 稳态
    clock.advance(13 * 3600.0)  # 常态间隔(12H)已过, idle(24H)未到
    waiting = run_wave(service, {})
    assert waiting.action == ACTION_WAITING
    assert "未到拉取时刻" in waiting.reason and "稳态降频" in waiting.reason
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.idle_mode is True


def test_idle_mode_flip_persists_once(tmp_path):
    """稳态 5. 旗标仅翻转时写盘(§2.4): 翻转 poll 恰好一次写(revision +1), 稳态期反复 poll
    零额外写; 落盘数据 JSON 往返保真(idle_mode 不丢)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)

    def revision():
        data, _ = service.store(SITE).read_unlocked()
        return data.revision, data.wave.idle_mode

    run_wave(service)  # 锚点未知(None): 不构成稳态, 旗标保持 False; 波照常跑
    rev0, idle0 = revision()
    assert idle0 is False
    result = run_wave(service, {})  # 确认零锚点 → 翻稳态; 复用窗内 REUSED —— 翻转写是本次唯一写
    assert result.action == "reused"
    rev1, idle1 = revision()
    assert idle1 is True and rev1 == rev0 + 1, "翻转 False→True 恰写一次(只有旗标写, 复用窗分支无波次写)"
    clock.advance(3 * 3600.0)  # 复用窗外, idle 间隔内
    waiting = run_wave(service, {})
    assert waiting.action == ACTION_WAITING and "稳态降频" in waiting.reason
    assert revision() == (rev1, True), "稳态期 poll 零写盘(revision 不变)"
    clock.advance(3600.0)
    assert run_wave(service, {}).action == ACTION_WAITING
    assert revision() == (rev1, True), "稳态期反复 poll 零额外写"
    data, _ = service.store(SITE).read_unlocked()
    assert HrWaveMeta.from_json(data.wave.to_json()).idle_mode is True, "JSON 往返保真"
    # 破稳态: 锚点翻非空 → 旗标翻回 False 也恰写一次; 间隔闸按常态 12H 判(4H 处仍 WAITING)
    result = run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW, seeding_time=0)})
    assert result.action == ACTION_WAITING and "稳态降频" not in result.reason
    assert revision() == (rev1 + 1, False), "破稳态翻转 True→False 恰写一次(间隔闸 WAITING 无波次写)"


def test_build_objects_skips_hr_excluded_anchor(tmp_path):
    """方案 B(计划 26-10-08-1249 S2): `excluded=True` 的锚点不进对象集 —— 稳态可达的前提;
    未排除的同款锚点照常进对象集(零静默变更)。实施前排除态在取数侧无载体, 两个锚点行为相同。"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    kept = HrAnchor(added_on=1, downloaded=10, completion_on=100, progress=1.0, name="keep")
    exc = HrAnchor(added_on=1, downloaded=10, completion_on=100, progress=1.0, name="exc", excluded=True)
    objects, observing, unmatched = service._build_objects(HrSiteData(), {"HK": kept, "HE": exc}, 100.0)
    assert "HK" in objects and "HK" in unmatched, "对照: 未排除锚点照常进对象集"
    assert "HE" not in objects and "HE" not in observing and "HE" not in unmatched, \
        "被排除锚点不进对象集(否则对象集恒非空 ⇒ 稳态降频永不生效)"


def test_hr_excluded_anchor_does_not_break_idle(tmp_path):
    """方案 B(计划 26-10-08-1249 S3-1): 站点只剩被排除的本地种子时, 对象集为空 ⇒ 稳态降频照常生效。
    实施前该锚点进对象集 ⇒ idle 永不成立、拉取停在 refresh_interval —— 本用例即该回归的钉。"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    _, h_exc = mk_blob("IYUU SEED 1")
    exc = HrAnchor(
        added_on=100,
        downloaded=1 << 30,
        completion_on=int(T_DONE_NEW),
        progress=1.0,
        seeding_time=0,
        name="IYUU SEED 1",
        excluded=True
    )
    anchors = {h_exc: exc}
    first = run_wave(service, anchors)
    assert first.action in (ACTION_REFRESHED, ACTION_PARTIAL)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.healthy_ts == clock.now() and data.wave.idle_mode is True, \
        "被排除种子不构成对账义务 ⇒ 稳态成立"
    clock.advance(13 * 3600.0)  # 常态间隔(12H)已过, idle(24H)未到
    waiting = run_wave(service, anchors)
    assert waiting.action == ACTION_WAITING
    assert "未到拉取时刻" in waiting.reason and "稳态降频" in waiting.reason, \
        f"被排除种子不该把间隔闸拉回常态: {waiting.action} {waiting.reason}"


def test_refresh_site_guard_paths(tmp_path):
    """站点未接入 / 全局开关关 -> 不取数直接返回; HrRefreshResult.ok 属性语义"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=clock)
    # 站点未接入(site_confs 没有该站)
    r1 = service.refresh_site("nosuch", {})
    assert r1.action == "disabled" and r1.reason == "该站未接入 hr_check"
    assert r1.ok is False
    # 全局开关关
    svc2 = make_service(tmp_path, fetcher, gconf=global_conf(enabled=False), clock=clock)
    r2 = svc2.refresh_site(SITE, {})
    assert r2.reason == "hr_check.enabled=false"
    assert fetcher.text_calls == [], "守卫路径不得发任何请求"
    # ok 属性的正例侧(复用/刷新都算 ok)
    ok_result = hr_service.HrRefreshResult(site=SITE, action="reused")
    assert ok_result.ok is True


def test_refresh_site_unknown_adapter(tmp_path):
    """未登记的 adapter -> ACTION_ERROR, 单站点失败不外抛"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, site=site_conf(adapter="no-such-adapter"), clock=FakeClock())
    result = run_wave(service)
    assert result.action == ACTION_ERROR
    assert "未登记的 adapter" in result.reason
    assert fetcher.text_calls == []


def test_refresh_site_lock_busy_returns_locked(tmp_path):
    """站点锁被其它实例持有 -> ACTION_LOCKED(等下一轮), 不外抛"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=FakeClock())
    outsider = HrSiteStore(SITE, service.dir, lock_timeout=0.0, owner="other-instance")
    with outsider.hold():
        result = service.refresh_site(SITE, {})
    assert result.action == ACTION_LOCKED
    assert "锁被其它实例持有" in result.reason
    assert fetcher.text_calls == []


def test_refresh_site_internal_error_contained(tmp_path, monkeypatch):
    """非取数异常(如编程错误) -> ACTION_ERROR + alerted, 波次异常不外拖"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher, clock=clock)

    def boom(url):
        raise RuntimeError("意外炸了")

    monkeypatch.setattr(fetcher, "get_text", boom)
    result = run_wave(service, {})
    assert result.action == ACTION_ERROR
    assert result.alerted is True
    assert "RuntimeError" in result.reason and "意外炸了" in result.reason


def test_login_page_detected_by_adapter_and_warned_once(tmp_path):
    """登录页由 adapter 页面形态识别(与扩展回传异常同一波级出口); 登录告警每站一次, 恢复后重置"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages={url_of(l): LOGIN_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    with capture_logs("auto_qb.hr.service") as cap:
        first = run_wave(service)
        assert first.action == ACTION_ERROR and "登录页" in first.reason
        data, _ = service.store(SITE).read_unlocked()
        assert data.rate.last_fetch_ts == clock.now(), "登录页路径同样前进间隔基准"
        clock.advance(120.0)
        second = run_wave(service)
        assert second.action == ACTION_ERROR
    login_errors = [m for m in cap.messages if "页面是登录页 ⇒" in m]
    assert len(login_errors) == 1, "登录恢复前每站只报一次(状态变化报一次), 不再每波重报"
    assert sum("登录态仍未恢复(已告警过" in m for m in cap.messages) == 1, "第二波走去重早退(INFO)"
    # 去重分支本体: 直接连调 _warn_login(用未告警过的站名), 第一次真告警, 第二次走「已告警过」早退
    with capture_logs("auto_qb.hr.service") as cap2:
        service._warn_login("example2", RuntimeError("仍未登录"))
        service._warn_login("example2", RuntimeError("仍未登录"))
    assert sum("登录态仍未恢复(已告警过" in m for m in cap2.messages) == 1
    # 恢复重置: 中间正常波拿到内容页 -> 清去重标记; 再次登录失效重新报一次
    fetcher.pages.update(standard_pages())
    assert run_wave(service).action == "refreshed"  # 登录波不设复用窗, 恢复波直接可跑
    fetcher.pages.update({url_of(l): LOGIN_PAGE for l in "ABC"})
    clock.advance(12 * 3600.0 + 60.0)  # 跳出复用窗(2h)与拉取间隔(12h, 恢复波推进了 healthy_ts)
    with capture_logs("auto_qb.hr.service") as cap3:
        third = run_wave(service)
        assert third.action == ACTION_ERROR
    assert len([m for m in cap3.messages if "页面是登录页 ⇒" in m]) == 1, "恢复后再失效 -> 重新告警(状态变化报一次)"


def test_missing_fields_abort_after_valid_page(tmp_path):
    """第 2 页必填字段缺失 -> 该档在失效点截断, 第 1 页之前的数据仍有效(LANE_OK 非全深度)"""
    clock = FakeClock()
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


def test_tail_zero_partial_reset(tmp_path):
    """停翻2. 跨页重算: 第 1 页尾只有 1 行到期 -> 计数重置为 1; 第 2 页凑满 5 行才停(全深度)"""
    clock = FakeClock()
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
    clock = FakeClock()
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
    assert data.fails[11].last_ts == clock.now(), "fail.last_ts 必须来自注入时钟, 不直调 time.time()"
    assert data.index[11].infohash_v1 == "", "身份未回填"


def test_readonly_degradation_noted_in_result(tmp_path):
    """锁自检失败(revision 回退) -> 波照跑但只读: reason 注明「锁自检失败」, 文件不被覆写"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service)
    data, _ = service.store(SITE).read_unlocked()
    rev_before = data.revision
    assert rev_before > 0
    # 注入「本实例上次写到过更高的 revision」: 下一波锁自检判不生效 -> 只读退化
    service.store(SITE)._last_write_rev = 10_000
    clock.advance(13 * 3600)
    result = run_wave(service)
    assert "锁自检失败" in result.reason and result.persisted is False
    data2, _ = service.store(SITE).read_unlocked()
    assert data2.revision == rev_before, "只读退化不得写盘"


def test_build_objects_unit_guards(tmp_path):
    """对象集现算单元: 空 hash 键跳过 / 非活跃条目不绑定 / 锚点漂移把放行记录作废回炉 / 已放行未漂移不回对象集"""
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
    # 已 verified 且未漂移: 不出对象集 —— 「批量签发整条覆写既有放行」不可达的前提(issue 26-10-02-0526 守阵)
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
    objects, observing, unmatched = service._build_objects(data, {"HG": anchor}, 100.0)
    assert data.verified["HG"].verified_ts == 1.0, "未漂移不作废放行"
    assert "HG" not in objects and "HG" not in observing and "HG" not in unmatched, "已放行未漂移不回对象集"


def test_build_views_skips_disabled_and_channel_states(tmp_path):
    """视图构建跳过未启用站点; channel_state 的 ok / silent(老化) / 无锁读 / disabled 分支"""
    from auto_qb.config.models import HrChannelConfig

    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]), blobs={11: torrent_blob(name="OTHER 11")})
    confs = {SITE: site_conf(), "offsite": site_conf(tracker="offsite", enabled=False)}
    service = make_service(
        tmp_path,
        fetcher,
        clock=clock,
        gconf=global_conf(channel=HrChannelConfig(enabled=True)),
        confs=confs,
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
    service2 = make_service(
        tmp_path,
        fetcher,
        data_dir=tmp_path / "d2",
        clock=FakeClock(),
        gconf=global_conf(channel=HrChannelConfig(enabled=True))
    )
    assert service2.channel_state(SITE) == "silent", "从未有健康波 -> silent"
    # 通道未启用 -> disabled
    service3 = make_service(tmp_path, fetcher, data_dir=tmp_path / "d3", clock=FakeClock(), gconf=_gconf_channel_off())
    assert service3.channel_state(SITE, None) == "disabled"


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
    assert HrRefreshService._advance_observation(data, not_covered, wave, 1.0) == 0
    assert obs.missing_streak == 0 and obs.active
    # 观察期出口但身份缺位(hash 为空) -> 计数出口, 不落放行记录
    obs.missing_streak = 1
    covered = {
        "A": HrLaneState(lane="A", status="ok", full_depth=True),
        "B": HrLaneState(lane="B", status="ok", full_depth=True),
        "C": HrLaneState(lane="C", status="ok", full_depth=True),
    }
    exits = HrRefreshService._advance_observation(data, covered, wave, 1.0)
    assert exits == 1 and data.index[31].active is False and data.verified == {}
    # 出口带身份 -> 落放行记录, verified_ts 取注入 now(issue 26-10-02-0526 时钟收编: 不直调 time.time())
    obs2 = HrEntry(tid=32, name="a-row2", lane=LANE_SCOPE, done_iso="2026-09-01T10:00:00")
    obs2.infohash_v1 = "HL-OBS"
    obs2.missing_streak = 1
    data.index[32] = obs2
    exits = HrRefreshService._advance_observation(data, covered, wave, 1234.5)
    assert exits == 1 and data.verified["HL-OBS"].verified_ts == 1234.5


def test_event_domains_are_declared():
    """事件 → 归属层单点(计划 §03.2/§03.4): 通道/账号/站点层各就各位

    层由**事件**推出而非调用点手写 —— 这是「通道层事件被贴上站点层标签」不可表达的落点。
    """
    assert events.domain_of(events.EVENT_PARSE) == events.DOMAIN_SITE
    assert events.domain_of(events.EVENT_LOGIN) == events.DOMAIN_ACCOUNT
    assert events.domain_of(events.EVENT_SILENCE) == events.DOMAIN_CHANNEL
    assert events.domain_of(events.EVENT_CHANNEL) == events.DOMAIN_CHANNEL
    assert events.domain_of("未登记") == "", "未登记 = 不分层(出口按可见处理, 向后兼容)"


def test_channel_unavailable_has_own_label():
    """通道不可用文案带**自己的**标签, 不再借 `[HR 页面改版]`(D3: 新增独立标签)"""
    msg = events.channel_unavailable("example", "等待浏览器扩展取数超时(180s)")
    assert msg.startswith("[HR 通道不可用]")
    assert "[HR 页面改版]" not in msg
    assert "不做在线核实" in msg


def test_channel_timeout_routes_to_no_channel(tmp_path, caplog):
    """等扩展超时 ⇒ **通道层**出口: action=no-channel · 不写 wave.notes · 不推进档位失败

    此前它抛裸 `HrFetchError` ⇒ 被当「页面取数失败」: 套 `[HR 页面改版]` 标签(进前端错误历史)、
    写 `wave.notes`(环境噪音进持久证据链)、推进 `fail_streak`(攒到 3 就升成「疑似改版」ERROR)
    —— 即计划 §03.3 的 P1/P2/P3(用户实报 2026-10-09)。
    """
    service = make_service(tmp_path, _TimeoutFetcher(), clock=FakeClock())
    with caplog.at_level(logging.WARNING):
        result = service.refresh_site(SITE, {})
    assert result.action == ACTION_NO_CHANNEL
    data, _err = service.store(SITE).read_unlocked()
    assert "取数失败" not in data.wave.notes, f"通道层不得写进 wave.notes: {data.wave.notes!r}"
    assert all(l.fail_streak == 0 for l in data.wave.lanes.values()), "通道层不得推进档位失败"
    assert not [r for r in caplog.records if "[HR 页面改版]" in r.getMessage()], "不得套「页面改版」标签"
    assert [r for r in caplog.records if "[HR 通道不可用]" in r.getMessage()], "通道层文案要带自己的标签"
    (ev, ) = _history_from_disk(service)
    assert (ev.kind, ev.action) == ("wave", "no-channel")


def test_channel_timeout_never_upgrades_to_page_changed(tmp_path, caplog):
    """连续多波通道不可用也**不**升级成「疑似改版」ERROR(§03.3 的 P2 升级路径)"""
    service = make_service(tmp_path, _TimeoutFetcher(), clock=FakeClock())
    with caplog.at_level(logging.ERROR):
        for _ in range(4):
            assert service.refresh_site(SITE, {}).action == ACTION_NO_CHANNEL
    assert not [r for r in caplog.records if "疑似改版" in r.getMessage()], "环境态不得升级成站点结论"
    data, _err = service.store(SITE).read_unlocked()
    assert all(l.fail_streak == 0 for l in data.wave.lanes.values())


def test_generic_fetch_error_still_page_failure(tmp_path, caplog):
    """边界回归: 真页面取数失败(HrFetchError)仍按**站点层**处理 —— 收层不得一刀切吞掉真异常"""
    fetcher = FakeFetcher(pages=standard_pages(), fail_text_at={"A": "HTTP 500"})
    service = make_service(tmp_path, fetcher, clock=FakeClock())
    with caplog.at_level(logging.WARNING):
        result = service.refresh_site(SITE, {})
    data, _err = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].fail_streak >= 1, "页面失败仍要推进档位失败计数"
    assert "取数失败" in data.wave.notes, f"页面失败仍要写 wave.notes: {data.wave.notes!r}"
    assert result.action in (ACTION_ERROR, ACTION_PARTIAL)
    assert [r for r in caplog.records if "[HR 页面改版]" in r.getMessage()], "页面失败仍要带「页面改版」标签"


def test_run_downloads_continues_after_backfill(tmp_path):
    """回填分支后继续处理后续 tid(continue 不是 break)"""
    clock = FakeClock()
    blob, h14 = mk_blob("T14")
    service = make_service(tmp_path, FakeFetcher(pages={}, blobs={14: blob}), clock=clock)
    data = HrSiteData()
    data.downloaded[13] = HrDownloaded(tid=13, ts=1.0, name="x", infohash_v1="HX")
    wave = _WaveContext({})
    wave.local_hashes = set()
    wave.dl_by_hash = hr_service._dl_by_hash(data)
    wave.pending_downloads = {13, 14}
    wave.seen[13] = HrEntry(tid=13, name="from-store")
    wave.seen[14] = HrEntry(tid=14, name="t14")
    budget = _dl_budget(service, data)
    result = hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED)
    with service.store(SITE).hold() as session:
        service._run_downloads(SITE, _StubAdapter(), data, budget, wave, result, session)
    assert result.torrents_fetched == 1 and wave.seen[14].infohash_v1 == h14


def test_run_downloads_cooldown_gate_boundaries(tmp_path):
    """下载失败冷却闸: 达上限 ∧ 冷却窗内 → 跳过; 恰好到期(now - last_ts == 冷却) → 放行"""
    clock = FakeClock()
    blob, _h = mk_blob("T11")
    fetcher = FakeFetcher(pages={}, blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED)

    def _run(data, wave):
        budget = _dl_budget(service, data)
        with service.store(SITE).hold() as session:
            service._run_downloads(SITE, _StubAdapter(), data, budget, wave, result, session)

    def _wave():
        wave = _WaveContext({})
        wave.local_hashes = set()
        wave.dl_by_hash = {}
        wave.pending_downloads = {11}
        wave.seen[11] = HrEntry(tid=11, name="t11")
        return wave

    data = HrSiteData()
    data.fails[11] = HrDlFail(tid=11, count=MAX_DOWNLOAD_RETRIES, last_ts=clock.now())
    _run(data, _wave())
    assert fetcher.byte_calls == [], "冷却窗内不得重下"

    fetcher.byte_calls.clear()
    data2 = HrSiteData()
    data2.fails[11] = HrDlFail(tid=11, count=MAX_DOWNLOAD_RETRIES, last_ts=clock.now() - DL_RETRY_COOLDOWN)
    _run(data2, _wave())
    assert fetcher.byte_calls, "恰好到期应放行下载"


def test_run_downloads_failure_paths_count_and_continue(tmp_path, caplog):
    """失败路径: HrFetchError 与非法 blob 各计一次失败并 **continue** 到后续 tid;
    torrents_failed / torrents_fetched 均累加(非赋值/自减); 两条告警文案保留"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = FakeClock()
    blob14, _h14 = mk_blob("T14")
    blob15, _h15 = mk_blob("T15")
    fetcher = FakeFetcher(
        pages={}, blobs={
            13: b"not a torrent",
            14: blob14,
            15: blob15
        }, fail_bytes_at={
            11: "boom-11",
            12: "boom-12"
        }
    )
    service = make_service(tmp_path, fetcher, clock=clock)
    data = HrSiteData()
    wave = _WaveContext({})
    wave.local_hashes = set()
    wave.dl_by_hash = {}
    wave.pending_downloads = {11, 12, 13, 14, 15}
    for tid in (11, 12, 13, 14, 15):
        wave.seen[tid] = HrEntry(tid=tid, name=f"t{tid}")
    budget = _dl_budget(service, data)
    result = hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED)
    with service.store(SITE).hold() as session:
        service._run_downloads(SITE, _StubAdapter(), data, budget, wave, result, session)
    assert result.torrents_failed == 3
    assert result.torrents_fetched == 2
    assert "取 .torrent 失败" in caplog.text and "不是合法 .torrent" in caplog.text


def test_run_downloads_registers_hash_pending_and_clears_fail(tmp_path):
    """下载成功: dl_by_hash 登记 v1/v2 → tid / tid 出队 / 清失败记账 / torrents_fetched 累加"""
    clock = FakeClock()
    blob11, _h11 = mk_blob("T11")
    blob12, _h12 = mk_blob("T12")
    service = make_service(tmp_path, FakeFetcher(pages={}, blobs={11: blob11, 12: blob12}), clock=clock)
    data = HrSiteData()
    data.fails[11] = HrDlFail(tid=11, count=1, last_ts=0.0)
    wave = _WaveContext({})
    wave.local_hashes = set()
    wave.dl_by_hash = {}
    wave.pending_downloads = {11, 12}
    wave.seen[11] = HrEntry(tid=11, name="t11")
    wave.seen[12] = HrEntry(tid=12, name="t12")
    budget = _dl_budget(service, data)
    result = hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED)
    with service.store(SITE).hold() as session:
        service._run_downloads(SITE, _StubAdapter(), data, budget, wave, result, session)
    rec11, rec12 = data.downloaded[11], data.downloaded[12]
    assert wave.dl_by_hash.get(rec11.infohash_v1) == 11
    assert wave.dl_by_hash.get(rec11.infohash_v2) == 11
    assert wave.dl_by_hash.get(rec12.infohash_v1) == 12
    assert 11 not in wave.pending_downloads and 12 not in wave.pending_downloads
    assert 11 not in data.fails
    assert result.torrents_fetched == 2


def test_run_downloads_downloaded_record_fields(tmp_path):
    """下载成功落 HrDownloaded: ts=取回时刻 / name 取 torrent 展示名(非行名) / v1 v2 双写"""
    clock = FakeClock()
    blob, h1 = mk_blob("other.bin")
    fetcher = FakeFetcher(pages=standard_pages(rows_a=[row(11, "EXAMPLE 11")]), blobs={11: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    rec = data.downloaded[11]
    assert rec.ts == clock.now()
    assert rec.name == "other.bin"
    assert rec.infohash_v1 == h1 and rec.infohash_v2


def test_run_pages_page_cap_one_keeps_rotation_bounded(tmp_path):
    """单波页数下限是 1: max_pages_per_wave=1 时每档恰取 1 页(不是 0 页也不是 2 页)"""
    clock = FakeClock()
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11")], has_next=True),
        url_of("A", 2): myhr_page([row(12, "OTHER 12")], has_next=False),
        url_of("B", 1): myhr_page([], has_next=False),
        url_of("C", 1): myhr_page([], has_next=False),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), gconf=global_conf(max_pages_per_wave=1), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.pages == 1, "每档只取 1 页(还有下一页也不越下限)"
    assert st.status == "ok" and st.detail == "达到单波页数上限(1)", "截断文案记上限值"


def test_run_pages_merge_seen_uses_now(tmp_path):
    """合并口传入取数时刻(不是 None): 索引行 last_seen = 本波时刻(陈旧淘汰计时起点)"""
    clock = FakeClock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].last_seen == clock.now()


def test_run_pages_commits_stamp_writer_heartbeat(tmp_path):
    """增量落盘时间戳 = 本波时刻(不是 None): 站点文件 heartbeat 供排障读"""
    clock = FakeClock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    run_wave(service, {})
    payload = _site_file_json(service)
    assert payload["writer"]["heartbeat"] == clock.now()


def test_refresh_locked_reuse_window_boundary_refetches(tmp_path):
    """复用窗边界是「到期即取」(expires_at > now): 窗口为 0 的站点不等下一节拍直接重取"""
    clock = FakeClock()
    service = make_service(
        tmp_path,
        FakeFetcher(pages=standard_pages([])),
        gconf=global_conf(reuse_window=0.0),
        site=site_conf(idle_refresh_interval=0.0),
        clock=clock,
    )
    first = run_wave(service, {})
    assert first.action in (ACTION_REFRESHED, ACTION_PARTIAL)
    data, _ = service.store(SITE).read_unlocked()
    assert data.expires_at == clock.now(), "复用窗 0: 窗边界恰在本波时刻"
    second = run_wave(service, {})
    assert second.action == ACTION_REFRESHED, f"边界当刻不复用, 应重取: {second.action}"


def test_refresh_locked_reuse_path_fills_result_fields(tmp_path):
    """复用(不取数)路径也回填结果字段: 条目数 / 计数 / 档位摘要 / 原因 / 快照"""
    clock = FakeClock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([row(11, "OTHER 11")])), clock=clock)
    first = run_wave(service, {})
    assert first.action == ACTION_REFRESHED
    second = run_wave(service, {})
    assert second.action == ACTION_REUSED and "复用窗" in second.reason
    assert second.entries == 1 and second.verified_count == 0
    assert second.lane_texts and second.lane_texts.startswith("A:")
    assert second.snapshot is not None and 11 in second.snapshot.index


def test_refresh_locked_fetch_interval_reason_exact_seconds(tmp_path):
    """拉取间隔闸门: 还差多少秒如实算(due - now), action=WAITING"""
    clock = FakeClock()
    service = make_service(
        tmp_path,
        FakeFetcher(pages=standard_pages([])),
        gconf=global_conf(reuse_window=100.0),
        site=site_conf(refresh_interval=3600.0),
        clock=clock,
    )
    run_wave(service, None)  # anchors=None: 非稳态, 拉取间隔取 refresh_interval
    clock.advance(200.0)  # 越过复用窗(100s), 未到拉取间隔(3600s)
    second = run_wave(service, None)
    assert second.action == ACTION_WAITING
    assert "未到拉取时刻(拉取间隔, 还差 3400s)" in second.reason, f"还差秒数应如实: {second.reason}"


def test_refresh_locked_min_interval_force_defers_with_exact_seconds(tmp_path):
    """force 撞账号安全线(min_interval): 让位 + defer 历史, 还差秒数如实(due - now)"""
    clock = FakeClock()
    service = make_service(
        tmp_path, FakeFetcher(pages=standard_pages([])), gconf=global_conf(min_interval=90.0), clock=clock
    )
    run_wave(service, {})  # 首波后 last_fetch_ts 前进
    forced = service.refresh_site(SITE, {}, force=True)
    assert forced.action == ACTION_WAITING
    m = re.search(r"还差 (\d+)s", forced.reason)
    assert m is not None, f"应如实报还差秒数: {forced.reason}"
    assert 90 <= int(m.group(1)) <= 112, f"还差秒数 = 抖动后的 min_interval(90, 只向上 25%): {forced.reason}"
    data, _ = service.store(SITE).read_unlocked()
    assert data.history[-1].kind == "defer" and data.history[-1].trigger == "manual"


def test_advance_observation_multi_entry_exit_counts(tmp_path):
    """观察期逐条目推进: 位置未证明的 streak 冻结, 被覆盖的连续 2 波后各自出口(逐个计数)"""
    clock = FakeClock()
    blobs = {}
    anchors = {}
    for tid in (11, 12, 13):
        blob, h = mk_blob(f"EXAMPLE {tid}")
        blobs[tid] = blob
        anchors[h] = anchor_for(f"EXAMPLE {tid}", completion_on=T_DONE_NEW)
    pages = {
        url_of("A"):
            myhr_page(
                [
                    row(11, "EXAMPLE 11", done=DONE_OLD),  # 位置深于后续 cutoff -> 不可证明
                    row(12, "EXAMPLE 12", done=DONE_NEW),  # 位置 == cutoff -> 被覆盖
                    row(13, "EXAMPLE 13", done=DONE_NEW),
                ]
            ),
        url_of("B"):
            myhr_page([]),
        url_of("C"):
            myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, blobs=blobs)
    service = make_service(tmp_path, fetcher, gconf=global_conf(max_pages_per_wave=3), clock=clock)
    run_wave(service, anchors)
    # 之后两波: A 档有下一页但未翻全(cutoff=DONE_NEW) -> 11 位置未证明; 12/13 done==cutoff 被覆盖
    a_partial = myhr_page([row(99, "OTHER 99", done=DONE_NEW)], has_next=True)
    for _ in range(MISSING_GRACE_WAVES):
        clock.advance(13 * 3600)
        fetcher.pages = {
            url_of("A"): a_partial,
            url_of("B"): EMPTY_TABLE_PAGE,
            url_of("C"): EMPTY_TABLE_PAGE,
        }
        run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].active is True and data.index[11].missing_streak == 0, "位置未证明: streak 冻结(不累加)"
    assert data.index[12].active is False and data.index[13].active is False, "位置被覆盖连续 2 波 -> 各自出口"
    assert data.index[12].missing_streak == 0, "出口后 streak 清零(不是 None/1)"
    rec12 = data.verified[data.index[12].infohash_v1] if data.index[12].infohash_v1 else None
    assert rec12 is not None and rec12.source == SOURCE_NOT_LISTED and rec12.tid == 12


def test_version_mismatch_reason_exact_text(tmp_path):
    """版本回退的跳过说明文案单点(不进前置 reason 拼接口径外的多余字符)"""
    import json

    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher)
    path = service.store(SITE).path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 999, "fetched_at": 1.0}), encoding="utf-8")
    result = run_wave(service, {})
    assert result.action == ACTION_ERROR
    assert result.reason.endswith("站点文件 schema 比程序新, 已跳过取数与写盘(请先升级程序)")
    assert "schema_version=999" in result.reason, "读坏/版本原因作为前缀保留(不被吞)"
    assert "; 站点文件 schema 比程序新" in result.reason and not result.reason.startswith("; ")


def test_read_error_recovers_with_empty_data(tmp_path):
    """站点文件读坏: 坏文件挪走 + 本波按空数据保守跑(不把读坏当「站点真为空」凭空签发放行)"""
    fetcher = FakeFetcher(pages=standard_pages([]))
    service = make_service(tmp_path, fetcher)
    path = service.store(SITE).path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ 这不是合法 JSON", encoding="utf-8")
    result = run_wave(service, {})
    assert result.action in (ACTION_REFRESHED, ACTION_PARTIAL), f"读坏不得让整站停摆: {result.action}"
    assert result.releases_signed == 0 and result.verified_count == 0, "空数据不得凭空签发放行"
    assert not path.exists() or "{ 这不是合法 JSON" not in path.read_text(encoding="utf-8"), "坏文件已挪走"


def test_refresh_all_anchors_map_shape_passthrough(tmp_path, monkeypatch):
    """refresh_all 三态直通(计划 26-10-05-0555 §2.5 与 worker.run_once 同款): 顶层 None →
    各站 None(稳态不生效); 映射缺站键 = 确认零锚点 → {}(可降频); 带站键原样透传"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher)
    seen = []

    def fake_refresh_site(site, anchors=None, force=False):
        seen.append((site, anchors, force))
        return "RESULT"

    monkeypatch.setattr(service, "refresh_site", fake_refresh_site)
    assert service.refresh_all(None) == ["RESULT"]
    assert seen[0] == (SITE, None, False), "顶层 None 原样直通, 不吞成 {}"
    assert service.refresh_all({"other": {}}) == ["RESULT"]
    assert seen[1][1] == {}, f"映射缺本站键必须降为 {{}}(确认零锚点): {seen[1][1]!r}"
    anchors = {SITE: {"aa": anchor_for("aa")}}
    assert service.refresh_all(anchors, force=True) == ["RESULT"]
    assert seen[2][1] is anchors[SITE] and seen[2][2] is True, "带站键映射原样透传, force 不丢"


def test_build_view_for_passes_listing_state_generated(tmp_path, monkeypatch):
    """build_view_for 透传单点: conf.listing / channel_state(site, data) / generated_at=当前时刻"""
    fetcher = FakeFetcher(pages=standard_pages())
    from auto_qb.config.models import HrChannelConfig
    service = make_service(tmp_path, fetcher, gconf=global_conf(channel=HrChannelConfig(enabled=True)))
    seen = {}

    def fake_build_site_view(site, listing, data, *, channel_state, generated_at):
        seen.update(site=site, listing=listing, data=data, channel_state=channel_state, generated_at=generated_at)
        return "VIEW"

    monkeypatch.setattr(hr_service, "build_site_view", fake_build_site_view)
    data, _ = service.store(SITE).read_unlocked()
    # 内存 data 与盘上故意不同: healthy_ts 置为当前时刻 -> 内存判 ok, 盘上(0.0)判 silent
    data.wave.healthy_ts = service._now()
    assert service.channel_state(SITE, data) == CHANNEL_OK, "内存面: 健康波新鲜 -> ok"
    assert service.build_view_for(SITE, data) == "VIEW"
    assert seen["site"] == SITE and seen["data"] is data
    assert seen["listing"] is service.site_confs[SITE].listing, "conf.listing 原样透传"
    assert seen["channel_state"] == CHANNEL_OK, "channel_state 按传入内存数据算(不是回读盘上的旧值)"
    assert seen["generated_at"] == service._now(), "generated_at 取当前时刻"


def test_absence_proven_all_boundary_matrix():
    """_absence_proven_all 判据边界单点: 完成时间不可信/档位从未有效取数/added_on 恰好等于
    wave_ts(不算晚)/cutoff 恰好等于 done-SLACK(余量内可证)四条边"""
    def lanes(**kw) -> dict:
        base = dict(wave_ts=2_000_000.0, status=LANE_OK, pages=1, rows=1, cutoff_done=913_600.0, full_depth=True)
        base.update(kw)
        return {ln: HrLaneState(lane=ln, **base) for ln in FETCH_LANES}

    def anchor(**kw) -> HrAnchor:
        base = dict(
            added_on=0, downloaded=1 << 30, completion_on=-1, progress=1.0, seeding_time=0, name="aa", excluded=False
        )
        base.update(kw)
        return HrAnchor(**base)

    empty_wave = _WaveContext({})
    # 完成时间闸: completion_on 不可信(None)→ done=0.0 → 非全深度档不可判
    assert _absence_proven_all(lanes(full_depth=False), empty_wave, anchor(completion_on=None)) is False
    # 档位从未有效取数(wave_ts=0)→ 该档无有效数据, 缺席不可判
    assert _absence_proven_all(lanes(wave_ts=0.0), empty_wave, anchor(completion_on=1_000_000)) is False
    # 新鲜度闸边界: added_on == wave_ts 恰好相等不算晚(严格 >) → 全深度档可证
    assert _absence_proven_all(lanes(wave_ts=1000.0), empty_wave, anchor(added_on=1000)) is True
    # 位置闸边界: done - COVERAGE_SLACK 恰好等于 cutoff(余量内) → 可证
    assert _absence_proven_all(lanes(full_depth=False), empty_wave, anchor(completion_on=1_000_000)) is True


def test_position_proof_cutoff_zero_is_unprovable():
    """issue 26-10-30-0550 守阵: cutoff_done<=0 ∧ 非全深度 ⇒ 位置不可证(三判据同口径)。

    改前三处各写一份 `done < st.cutoff_done`, cutoff=0 时它对任意真实 epoch(≈1.7e9)恒为
    False ⇒ 终态冻结 / 观察期出口 / 批量签发三条路全部签发永续放行, 种子退出 HR 管束。现三者
    共用 `_lane_covers_done` 一条口径; 本用例把「无位置概念」与「正常覆盖」两组都钉死, 防止
    修过头把正常路径一起拦死。
    """
    from auto_qb.hr.adapters.base import ParsedScope

    now = time.time()
    entry = HrEntry(tid=9, name="e", done_iso=DONE_OLD)
    real_done = entry.done_epoch
    assert real_done > COVERAGE_SLACK, "真实 epoch 须远深于对齐余量, 否则本用例失去意义"

    def states(full_depth: bool, cutoff: float) -> dict:
        base = dict(status=LANE_OK, wave_ts=now, pages=1, rows=1, full_depth=full_depth, cutoff_done=cutoff)
        return {ln: HrLaneState(lane=ln, **base) for ln in FETCH_LANES}

    zero = states(False, 0.0)
    # 三判据: 无位置概念 ⇒ 一律不可证(不是「位置 0 = 比一切都老」)
    assert _lane_covers_done(zero["A"], real_done) is False
    assert _position_covered(entry, zero) is False, "观察期 streak 冻结(维持管束)"
    assert _absence_proven_all(zero, _WaveContext({}), HrAnchor(completion_on=int(real_done))) is False, \
        "批量「未列出」不得签发"
    # 负哨兵同口径(<=0 整体视为「没有位置概念」)
    assert _position_covered(entry, states(False, -1.0)) is False
    assert _absence_proven_all(states(False, -1.0), _WaveContext({}), HrAnchor(completion_on=int(real_done))) is False
    # 对照组: 全深度与位置无关; 非全深度但边界已越过 ⇒ 可证(不是一刀切拦死)
    assert _position_covered(entry, states(True, 0.0)) is True
    assert _absence_proven_all(states(True, 0.0), _WaveContext({}), HrAnchor()) is True
    covered = states(False, real_done - COVERAGE_SLACK)
    assert _position_covered(entry, covered) is True
    assert _absence_proven_all(covered, _WaveContext({}), HrAnchor(completion_on=int(real_done))) is True
    assert _absence_proven_all(
        states(False, real_done - COVERAGE_SLACK + 1), _WaveContext({}), HrAnchor(completion_on=int(real_done))
    ) is False, "差 1s 落在余量外 ⇒ 不可证"
    # 供给侧成因: 整列 done 不可解析 ⇒ _update_cutoff 不前进, cutoff 恒 0(与前半段合成完整触发链)
    st = HrLaneState(lane="A", status=LANE_OK, full_depth=False)
    HrRefreshService._update_cutoff(
        st,
        ParsedScope(
            scope="A", entries=[
                HrEntry(tid=1, name="x", done_iso=""),
                HrEntry(tid=2, name="y", done_iso="昨日"),
            ]
        )
    )
    assert st.cutoff_done == 0.0, "整列失明不前进 cutoff(0 = 没有位置概念)"
    # 终态冻结端到端: cutoff=0 ∧ 非全深度 ⇒ 不退役、不签发(改前恒退役并签永续放行)
    data = HrSiteData()
    term = HrEntry(tid=21, name="t", done_iso=DONE_OLD, lane=LANE_SATISFIED, active=True, infohash_v1="H21")
    data.index[21] = term
    assert HrRefreshService._freeze_terminal(data, zero, _WaveContext({}), now) == 0
    assert term.active is True and not data.verified, "位置不可证 ⇒ 维持管束, 不签放行"


def test_advance_observation_scope_exit_resets_streak():
    """A 档观察条目连续 2 波位置被覆盖 → 出口; 出口后 streak 显式清零(不是 None)"""
    data = HrSiteData()
    entry = HrEntry(tid=11, lane=LANE_SCOPE, active=True, done_iso=DONE_NEW, infohash_v1="h11")
    data.index[11] = entry
    lanes = {
        ln: HrLaneState(lane=ln, wave_ts=1000.0, status=LANE_OK, pages=1, rows=1, cutoff_done=0.0, full_depth=True)
        for ln in FETCH_LANES
    }
    wave = _WaveContext({})
    for _ in range(MISSING_GRACE_WAVES):
        HrRefreshService._advance_observation(data, lanes, wave, 2000.0)
    assert entry.active is False, "位置被覆盖连续 2 波 -> 判移出"
    assert entry.missing_streak == 0, "出口后 streak 清零(不是 None)"
    assert "h11" in data.verified and data.verified["h11"].source == SOURCE_NOT_LISTED


def test_no_permission_is_channel_layer_and_persisted(tmp_path):
    """缺站点权限: 归通道层(不计档位失败) + 落盘 channel_last_error(计划 D3/D6)

    !这条是「环境态不许冒充站点结论」的机械守卫: 若哪天有人把它改回 HrFetchError,
    `fail_streak` 会开始涨、日志会带 `[HR 页面改版]`, 这里立刻红。
    """
    clock = FakeClock()
    from auto_qb.config.models import HrChannelConfig

    fetcher = FakeFetcher(pages={}, channel_error=HrExtensionNoPermission("扩展未授权该站点"))
    service = make_service(tmp_path, fetcher, clock=clock, gconf=global_conf(channel=HrChannelConfig(enabled=True)))
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert result.action == ACTION_NO_CHANNEL
    # 通道层失败走 _abort_wave: 波次结构不落盘(没有"这一波跑到哪"可言), 故 lanes 要么为空、
    # 要么全是上一波的旧值 —— 无论哪种, 都不许出现 fail_streak 增长。
    for lane_state in data.wave.lanes.values():
        assert lane_state.fail_streak == 0, "通道层失败不许推进档位连续失效计数"
    assert data.channel_last_error.get("kind") == CHANNEL_NO_PERMISSION
    assert data.channel_last_error.get("ts", 0) > 0
    assert service.channel_state(SITE, data) == CHANNEL_NO_PERMISSION


def test_network_failure_persists_network_kind(tmp_path):
    """网络层失败与缺权限落成**不同**的 kind(动作不同: 查代理 vs 去授权)"""
    clock = FakeClock()
    from auto_qb.config.models import HrChannelConfig

    fetcher = FakeFetcher(pages={}, channel_error=HrExtensionNetwork("Failed to fetch"))
    service = make_service(tmp_path, fetcher, clock=clock, gconf=global_conf(channel=HrChannelConfig(enabled=True)))
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.channel_last_error.get("kind") == CHANNEL_NETWORK
    assert service.channel_state(SITE, data) == CHANNEL_NETWORK


def test_channel_error_cleared_on_recovery(tmp_path):
    """拿到正常内容页即清通道痕 —— 告警态与展示态必须同一个恢复点"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages={}, channel_error=HrExtensionNoPermission("扩展未授权该站点"))
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.channel_last_error, "先确认痕迹已落盘"
    fetcher.channel_error = None
    fetcher.pages.update(standard_pages([], [], []))
    clock.advance(13 * 3600)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.channel_last_error == {}, "恢复后不许留旧痕(否则站点卡会一直红着)"
    assert service.channel_state(SITE, data) != CHANNEL_NO_PERMISSION


def test_page_fetch_failure_escalates_after_streak(tmp_path, caplog):
    """页面层连续 3 波同档失效 ⇒ ERROR 升级(计划 D8)

    此前只有「结构失效」(_LaneAbort)接了升级告警, 取数失败这条没接 —— 于是 fail_streak 涨到
    58 也没有一句「疑似改版」, 信号全被 `_warn_parse` 节流成 INFO(2026-10-28 实报)。
    """
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([], [], []), fail_text_at={"A": "HTTP 500"})
    service = make_service(tmp_path, fetcher, clock=clock)
    # 推进 25h: 部分成功波会把拉取间隔推到 24h(稳态降频), 13h 不够 —— 不然中间会夹一个
    # ACTION_WAITING("未到拉取时刻"), streak 永远差一波。
    for _ in range(3):
        run_wave(service, {})
        clock.advance(25 * 3600)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].fail_streak == 3
    assert "已连续 3 波失效" in caplog.text, "页面层取数失败也必须能升到 ERROR"


def test_fetchable_filter_skips_none_listing_site(tmp_path):
    """取数侧强制(issue 26-10-05-0922): 全站型(listing=none)站点不进取数集合 —— refresh_all
    不给它出波次; 展示口径不受影响(enabled_sites / build_views 照常含它, 判定侧恒行 4)"""
    clock = FakeClock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(
        tmp_path, fetcher, clock=clock, confs={
            SITE: site_conf(),
            "fullsite": site_conf(listing="none")
        }
    )
    assert service.fetchable_sites() == (SITE, ), "取数集合只含清单型"
    assert service.enabled_sites() == (SITE, "fullsite"), "展示口径不变: 全站型仍在启用集合"
    results = service.refresh_all(force=True)
    assert [r.site for r in results] == [SITE], "全站型不出波次"
    assert set(service.build_views()) == {SITE, "fullsite"}, "视图照常含全站型(判定走 listing=none 分支)"

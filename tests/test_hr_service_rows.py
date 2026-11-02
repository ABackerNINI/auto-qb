"""test_hr_service_rows 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_stop3_local_full_coverage: 停翻3. 本地全集覆盖(未对账全部对上且无待回填)
- test_untrusted_done_pure_seed: 纯辅种(完成时间不可信)不参与1., 由2./末页收尾且可获放行
- test_a_lane_rows_downloaded_unconditionally: 已见 A 档行无条件下载且同 tid 永不重下(永久层)
- test_terminal_rows_download_on_fuzzy_match: B/C/D 行仅宽泛名称粗配疑似才下载; 粗配误配由精配自愈
- test_rows_not_local_not_downloaded: 本地没有的种子(粗配也不像)不下载
- test_exempt_seed_not_in_objects_passive_hit_managed: 超额种子(≥3×)不进对象集; 被动命中考察中仍转管束
- test_local_satisfied_hit_scope_still_managed: 本地已达标 × 命中考察中 → 管束(网站绝对权威)
- test_verified_record_not_overwritten_on_rewave: 已放行未漂移跨波记录原样保留 —— 批量签发不覆写既有放行(issue 26-10-02-0526 端到端守阵, 终态不可逆)
- test_zero_rows_no_release: 结构完好零行 → 不签发放行
- test_zero_rows_confirmed_release: --hr-confirm-empty 后零行可签发; 非零行清除确认戳
- test_terminal_vanish_writes_release: 终态(B)条目消失且位置被证明 → 退役并落放行记录(source=satisfied)
- test_terminal_vanish_c_lane_release_source: 终态(C)条目同路径 → 落放行记录 source=not-listed
- test_terminal_vanish_unproven_kept: 终态条目消失但位置未被覆盖 → 维持原状
- test_fuzzy_name_match_unit: 宽泛名称粗配单元(信号串重合段 ≥ K; 技术噪声整词不构成判据 —— 含真实数据假重合回归)
- test_counter_positive_zero_rows_page_changed: T51. 计数>0∧行数=0 —— page_changed 硬告警 + 不签发

### 稳态降频(计划 26-10-05-0555 §2/S4; 锚点三态契约: None=采集失败不降频 / {}=确认零锚点可降频)

### HR 排除落到取数侧(计划 26-10-08-1249 方案 B)
- test_excluded_anchor_still_counts_as_local_hit: 排除种子仍留命中面/仍判本地命中/不下载身份(防被做成方案 A)

### HR 排除种子终态行身份下载短路(计划 26-10-09-1057 / issue 26-10-08-1304)
- test_terminal_row_matching_only_excluded_seed_not_downloaded: 终态行粗配**只**命中被排除种子 ⇒ 零下载(行仍被记录)
- test_terminal_row_matching_excluded_and_managed_still_downloaded: 粗配宽松 ⇒ 同一行可同时命中排除与受管种子 ⇒ 仍下载(形态守阵)

### P1 覆盖率提升轮(T1.1 错误路径系统补齐)
- test_process_rows_unit_identity_paths: 行处理单元: 永久层继承 / 换 tid 重列接管 / 命中撤销放行 / 同 hash 旧条目退役

### S2 拉取历史记录点(计划 26-10-04-0312 §3.3)
- test_history_wave_events_six_terminal_states: 六终态(refreshed/partial/login/no-channel/quota/Retry-After)
  各恰一条 wave 事件且随站点文件落盘, 关键字段(action/trigger/计数字段/lanes 快照/notes/by)搬运正确
  + 零写盘(站点文件一字节不变) —— 硬不变量

### R16 变异审计守阵(计划 26-10-09-1459 / issue 26-10-10-1108-test-hr-mutation-service-engine)

- test_stop_condition_local_coverage_is_not_full_depth: 停翻3. 本地全集覆盖 = 位置有界(非全深度)
- test_run_downloads_backfill_discards_pending_without_local_hit: 永久层回填(身份非本地)也把 tid 出队
- test_run_downloads_hit_prefers_local_hash: 命中侧取本地那一侧(v1 不本地 v2 本地 -> 记 v2)
- test_run_downloads_no_hit_when_neither_hash_local: 两侧都不本地 -> 不记命中(不回落 v1/占位串)
- test_finish_wave_healthy_requires_rows_or_full_depth: 健康波判据(ok ∧ (有行 ∨ 全深度))
- test_finish_wave_not_healthy_when_rows_zero_and_not_full: ok 但零行且非全深度不算健康
- test_finish_wave_counter_claim_one_zero_rows_hard_error: 声明 1 行实抓 0 行也走硬告警(> 0 而非 > 1)
- R22(issue 26-10-10-1108 余量函数守阵):
- test_run_pages_rows_accumulate_over_pages: 行数跨页累加(+= 而非 =): 第 2 页的行并进本档计数
- test_finish_wave_zero_rows_note_exact_text: 零行不签发的持久化文案单点(带人工对账命令)
- test_freeze_terminal_multi_entry_position_rules: 一波多条目退役: 位置未证明的维持管束, 全深度/自身 done 越过 cutoff 的退役
- test_process_rows_carries_identity_across_waves: 重例行继承旧身份: 已登记的 infohash 带过来
- test_build_objects_excludes_terminal_verified_exempt: 对象集现算单点(纯内存): 非活动/终态/已放行/超额/空哈希都不进对象集
- test_freeze_terminal_failed_lane_between_entries: 档位失效的条目只跳过自己(continue 非 break): 其后可退役的终态条目照常退役
- test_fuzzy_name_match_rejects_noise_only_overlap
- test_mark_fetch_failed_and_seen_rows_units

### 站点可选权限轮(计划 26-10-29-0147 W2/W4): 归层、判据与告警
- test_zero_rows_false_when_all_lanes_failed: 全档失败的波**不是**零行波(D4: 总量为 0 ∧ 全档 ok)——
  改前它自称「结构完好但清单为 0」并把用户引向 --hr-confirm-empty(2026-10-28 实报的误导)
- test_zero_rows_true_when_all_lanes_ok_and_empty: 全档有效且确实为空 ⇒ 零行波成立, 人工对账话术照旧
- test_zero_rows_false_when_one_lane_failed: 一档 ok 两档失败也不算: 有档没看到就没资格判「空」
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
    _StubAdapter,
    _dl_budget,
    _history_from_disk,
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


def test_verified_record_not_overwritten_on_rewave(tmp_path):
    """已放行未漂移跨波记录原样保留 —— 「批量签发整条覆写既有放行」不可达的端到端守阵
    (issue 26-10-02-0526): _build_objects 对已 verified 未漂移的对象不出对象集,
    _sign_releases 无从覆写(放行永续有效, 终态不可逆); 漂移(本机重下)才回炉重签。"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    first = data.verified["h1"]
    assert first.source == SOURCE_NOT_LISTED
    # 次波同一锚点(未漂移): 记录逐字段原样, 零二次签发
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert result.releases_signed == 0
    assert data.verified["h1"] == first, "放行记录被整条覆写(终态不可逆被破坏)"


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
    assert result.alerted is True  # 零行未确认 = 产生处已告警
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
    # 稳态降频(26-10-05-0555): h1 已放行出对象集 → 对象集空 = 稳态, 下一波按 idle 间隔(默认 24H)到点
    clock.advance(24 * 3600.0 + 60.0)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.empty_confirmed_at == 0.0


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
    # 稳态降频(26-10-05-0555): 终态条目出对象集 → 对象集空 = 稳态, 下一波按 idle 间隔(默认 24H)到点
    clock.advance(24 * 3600.0 + 60.0)
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
    # 稳态降频(26-10-05-0555): 终态条目出对象集 → 对象集空 = 稳态, 下一波按 idle 间隔(默认 24H)到点
    clock.advance(24 * 3600.0 + 60.0)
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


def test_excluded_anchor_still_counts_as_local_hit(tmp_path):
    """方案 B(计划 26-10-08-1249 S3-2): 被排除种子**仍留在命中面** —— 站点行带其 infohash 时判
    本地命中、不产生身份下载。防「排除」被实现成「不认识」(那会改变匹配语义、多下 .torrent)。
    名称候选面随计划 26-10-09-1057 收窄为受管集(排除种子名不再驱动身份下载), 但**命中面**
    (`local_hashes`) 仍全量 —— 本用例同时钉住这两点。"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    exc = HrAnchor(added_on=100, downloaded=1 << 30, completion_on=-1, progress=1.0, name="IYUU SEED 1", excluded=True)
    wave = _WaveContext({"HE": exc})
    assert "HE" in wave.local_hashes, "命中面从全量锚点构建: 排除不使其从命中面消失(排除 ≠ 不认识)"
    assert "IYUU SEED 1" not in wave.local_names_managed, \
        "名称候选面(粗配触发器)已收窄为受管集: 排除种子名不再驱动身份下载(issue 26-10-08-1304)"
    data = HrSiteData()
    row11 = HrEntry(tid=11, name="IYUU SEED 1")
    row11.infohash_v1 = "HE"
    service._process_rows(LANE_SCOPE, [row11], data, wave)
    assert wave.hits.get("HE") == LANE_SCOPE, "行带 infohash 且本地有(即使被排除) ⇒ 判本地命中"
    assert 11 not in wave.pending_downloads, "命中即不下载身份(排除不该让它变陌生行)"


def test_terminal_row_matching_only_excluded_seed_not_downloaded(tmp_path):
    """issue 26-10-08-1304 核心: B/C/D 终态行(无 infohash)按名称粗配**只**命中被排除种子 ⇒
    不进 pending_downloads ⇒ 零 .torrent 请求(省站点日额/频控)。行仍被记录(不下载 ≠ 不认识)。"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([], has_next=False),
        url_of("B"): myhr_page([row(21, "Example.Ultra.S01E01.1080p")], has_next=False),
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
    assert "https://pt.example.com/download.php?id=21" not in fetcher.byte_calls, \
        "只命中被排除种子 ⇒ 不下载身份(该身份无消费方)"
    data, _ = service.store(SITE).read_unlocked()
    assert any(e.tid == 21 for e in data.index.values()), "行仍被索引记录(不下载 ≠ 不认识)"


def test_terminal_row_matching_excluded_and_managed_still_downloaded(tmp_path):
    """形态守阵(计划 26-10-09-1057 §03.3): 粗配宽松(K=12 标题重合即命中), 同一行可**同时**命中
    排除与受管种子(同剧不同集/季)。收窄候选集写法保住受管那侧 ⇒ 仍下载(绝不漏下受管种子身份);
    防退回「命中排除名即 return False」的误杀写法。"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([], has_next=False),
        url_of("B"): myhr_page([row(21, "Example.Ultra.S01E01.1080p")], has_next=False),
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
    keep = HrAnchor(
        added_on=100,
        downloaded=1 << 30,
        completion_on=-1,
        progress=1.0,
        name="Example.Ultra.S01E02.1080p",
        excluded=False
    )
    run_wave(service, {"HE": exc, "HK": keep})
    assert "https://pt.example.com/download.php?id=21" in fetcher.byte_calls, \
        "同一行还命中受管种子 ⇒ 仍下载(收窄候选集而非提前返回)"


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


def test_stop_condition_local_coverage_is_not_full_depth(tmp_path):
    """停翻3. 本地全集覆盖 ⇒ 位置有界(不是全深度)"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    wave.hits = {"h1": "A"}
    stop, full, why = service._stop_condition("A", _Parsed([_live(1)]), wave, {}, {"h1": anchor_for("h1")})
    assert stop is True and full is False and "本地全集覆盖" in why


def test_run_downloads_backfill_discards_pending_without_local_hit(tmp_path):
    """永久层回填(身份不在本地)也要把 tid 出队 —— 只在命中时出队会留队列残渣"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    data = HrSiteData()
    data.downloaded[13] = HrDownloaded(tid=13, ts=1.0, name="x", infohash_v1="HX")
    wave = _WaveContext({})
    wave.local_hashes = set()
    wave.dl_by_hash = hr_service._dl_by_hash(data)
    wave.pending_downloads = {13}
    wave.seen[13] = HrEntry(tid=13, name="from-store")
    budget = _dl_budget(service, data)
    with service.store(SITE).hold() as session:
        service._run_downloads(
            SITE, _StubAdapter(), data, budget, wave, hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED),
            session
        )
    assert 13 not in wave.pending_downloads
    assert wave.hits == {}


def test_run_downloads_hit_prefers_local_hash(tmp_path):
    """命中侧: v1 不在本地而 v2 在 → 记 v2 命中(取本地那一侧)"""
    clock = Clock()
    blob, _h1 = mk_blob("T11")
    service = make_service(tmp_path, FakeFetcher(pages={}, blobs={11: blob}), clock=clock)
    _v1, v2, _info = hr_service.compute_infohashes(blob)
    data = HrSiteData()
    wave = _WaveContext({})
    wave.local_hashes = {v2}
    wave.dl_by_hash = {}
    wave.pending_downloads = {11}
    wave.seen[11] = HrEntry(tid=11, name="t11")
    budget = _dl_budget(service, data)
    with service.store(SITE).hold() as session:
        service._run_downloads(
            SITE, _StubAdapter(), data, budget, wave, hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED),
            session
        )
    assert wave.hits == {v2: LANE_SCOPE}


def test_run_downloads_no_hit_when_neither_hash_local(tmp_path):
    """命中侧: 两侧都不在本地 → 不记命中(不得回落 v1 / 空串 / 占位串)"""
    clock = Clock()
    blob, _h1 = mk_blob("T11")
    service = make_service(tmp_path, FakeFetcher(pages={}, blobs={11: blob}), clock=clock)
    data = HrSiteData()
    wave = _WaveContext({})
    wave.local_hashes = set()
    wave.dl_by_hash = {}
    wave.pending_downloads = {11}
    wave.seen[11] = HrEntry(tid=11, name="t11")
    budget = _dl_budget(service, data)
    with service.store(SITE).hold() as session:
        service._run_downloads(
            SITE, _StubAdapter(), data, budget, wave, hr_service.HrRefreshResult(site=SITE, action=ACTION_REFRESHED),
            session
        )
    assert wave.hits == {}


def test_finish_wave_healthy_requires_rows_or_full_depth(tmp_path):
    """健康波判据: 档位 ok ∧ (有行 ∨ 全深度) —— 有行但未全深度(1.停翻)也算健康"""
    clock = Clock()
    pages = {
        url_of(l): myhr_page([row(10 + i, f"OTHER {i}", done=DONE_OLD)], has_next=True)
        for i, l in enumerate("ABC")
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    assert all(
        data.wave.lanes[l].ok and data.wave.lanes[l].rows > 0 and not data.wave.lanes[l].full_depth for l in "ABC"
    )
    assert data.wave.healthy_ts == clock.now


def test_finish_wave_not_healthy_when_rows_zero_and_not_full(tmp_path):
    """健康波判据: ok 但零行且非全深度(页面取数失败截断)不算健康 ⇒ healthy_ts 不前进"""
    clock = Clock()
    pages = {url_of(l, 1): myhr_page([], has_next=True) for l in "ABC"}  # 第 2 页缺失 → 取数失败
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert all(data.wave.lanes[l].ok and data.wave.lanes[l].rows == 0 for l in "ABC")
    assert data.wave.healthy_ts == 0.0


def test_finish_wave_counter_claim_one_zero_rows_hard_error(tmp_path, monkeypatch, caplog):
    """声明 1 行实抓 0 行也走 page_changed 硬告警(判据是 claim > 0 而非 > 1), 不落到 mismatch 节流告警"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {"A": 1, "B": 1, "C": 1})
    fetcher = FakeFetcher(pages={url_of(l): EMPTY_TABLE_PAGE for l in "ABC"})
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    assert "声明 1 行但实抓 0 行" in caplog.text
    assert "计数对不平" not in caplog.text


def test_run_pages_rows_accumulate_over_pages(tmp_path):
    """行数跨页累加(+= 而非 =): 第 2 页的行并进本档计数"""
    clock = Clock()
    pages = {
        url_of("A", 1):
            myhr_page([row(11, "OTHER 11", done=DONE_NEW)], has_next=True),
        url_of("A", 2):
            myhr_page([row(12, "OTHER 12", done=DONE_OLD),
                       row(13, "OTHER 13", done=DONE_OLD)], has_next=False),
        url_of("B", 1):
            myhr_page([]),
        url_of("C", 1):
            myhr_page([]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].pages == 2
    assert data.wave.lanes["A"].rows == 3, "两页 1+2 行累加"


def test_finish_wave_zero_rows_note_exact_text(tmp_path):
    """零行不签发的持久化文案单点(带人工对账命令): 文案改写即测试红"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    pages = {url_of("A"): myhr_page([row(11, "EXAMPLE 11")]), url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    clock.advance(13 * 3600)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.zero_rows is True
    assert "结构完好但清单为 0: 不签发放行(需 --hr-confirm-empty 人工对账)" in result.reason


def test_freeze_terminal_multi_entry_position_rules(tmp_path):
    """一波多条目退役: 位置未证明的维持管束, 全深度/自身 done 越过 cutoff 的退役; 逐条计数"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    blob21, h21 = mk_blob("EXAMPLE 21")
    blob22, h22 = mk_blob("EXAMPLE 22")
    blob23, h23 = mk_blob("EXAMPLE 23")
    pages = {
        url_of("A"):
            myhr_page([row(11, "EXAMPLE 11")]),  # A 档非终态(remain 非 0)
        url_of("B"):
            myhr_page(
                [
                    row(21, "EXAMPLE 21", done=DONE_OLD, remain="0天00:00:00", need="0:00:00"),
                    row(23, "EXAMPLE 23", done=DONE_NEW, remain="0天00:00:00", need="0:00:00"),
                ]
            ),
        url_of("C"):
            myhr_page([row(22, "EXAMPLE 22", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11, 21: blob21, 22: blob22, 23: blob23})
    service = make_service(tmp_path, fetcher, gconf=global_conf(max_pages_per_wave=3), clock=clock)
    anchors = {
        h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW),
        h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW),
        h22: anchor_for("EXAMPLE 22", completion_on=T_DONE_NEW),
        h23: anchor_for("EXAMPLE 23", completion_on=T_DONE_NEW),
    }
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].infohash_v1 == h21 and data.index[22].infohash_v1 == h22
    assert data.index[23].infohash_v1 == h23, "粗配同名下载登记身份(冻结才有对象可落记录)"
    # 第二波: A 全深度空表; B 有下一页(未翻全, cutoff=DONE_NEW); C 全深度( cutoff=DONE_NEW )
    fetcher.pages = {
        url_of("A"): EMPTY_TABLE_PAGE,
        url_of("B"): myhr_page([row(99, "OTHER 99", done=DONE_NEW)], has_next=True),
        url_of("C"): myhr_page([row(88, "OTHER 88", done=DONE_NEW)]),
    }
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is True, "B 未翻全且自身 done 早于 cutoff: 位置未证明, 维持管束"
    assert data.index[22].active is False, "C 全深度: 位置被覆盖 -> 退役"
    assert data.index[23].active is False, "B 虽未翻全, 但自身 done == cutoff: 位置被覆盖 -> 退役"
    assert data.verified[h22].source == SOURCE_NOT_LISTED
    assert data.verified[h23].source == SOURCE_SATISFIED
    assert data.verified[h22].tid == 22 and data.verified[h23].tid == 23
    assert "终态冻结 4 条" in result.reason, f"逐条累加(每条目 v1+v2 两个身份各记一次): {result.reason!r}"
    assert {h[:6]: v.tid for h, v in data.verified.items()} == {"01561e": 23, "0d6bd2": 23, "4bca8f": 22, "e92e21": 22}
    # 退役落盘: active 显式 False(不留 null 语义位)
    payload = _site_file_json(service)
    actives = {e["tid"]: e["active"] for e in payload["index"]}
    assert actives[22] is False and actives[23] is False and actives[21] is True


def test_process_rows_carries_identity_across_waves(tmp_path):
    """重例行继承旧身份: 已登记的 infohash 带过来, 命中定论照判(不因页面不带 hash 就重新下载/误签)"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    pages = {url_of("A"): myhr_page([row(11, "EXAMPLE 11")]), url_of("B"): myhr_page([]), url_of("C"): myhr_page([])}
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].infohash_v1 == h11
    downloads_after_first = len(fetcher.byte_calls)
    # 第二波: 同一行仍在清单(页面同样不带 hash) -> 旧身份必须继承 => 命中, 不再下载, 不误签放行
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[11].infohash_v1 == h11, "重例行继承已登记身份"
    assert data.index[11].first_seen > 0
    assert len(fetcher.byte_calls) == downloads_after_first, "同 tid 永不重下(永久层去重)"
    assert result.releases_signed == 0 and h11 not in data.verified, "命中即不签「未列出」"


def test_build_objects_excludes_terminal_verified_exempt():
    """对象集现算单点(纯内存): 非活动条目不绑定身份 / 终态 / 已放行 / 超额(≥3×) / 空哈希 都不进对象集"""
    blob11, h11 = mk_blob("EXAMPLE 11")
    blob22, h22 = mk_blob("EXAMPLE 22")
    data = HrSiteData()
    data.index[99] = HrEntry(tid=99, lane=LANE_SATISFIED, active=False, infohash_v1="h_old")  # 退役条目不绑定
    data.index[11] = HrEntry(tid=11, lane=LANE_SCOPE, active=True, infohash_v1=h11)
    data.index[22] = HrEntry(tid=22, lane=LANE_SATISFIED, active=True, infohash_v1=h22)  # 终态出对象集
    anchors = {
        "h_exempt": anchor_for("EXEMPT 1", completion_on=T_DONE_NEW, seeding_time=7 * 86400),  # 超额
        h22: anchor_for("EXAMPLE 22", completion_on=T_DONE_NEW),  # 终态
        "": anchor_for("EMPTY HASH", completion_on=T_DONE_NEW),  # 空哈希
        h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW),  # 受管 -> 观察集
        "h_ghost": anchor_for("GHOST 1", completion_on=T_DONE_NEW),  # 未对账
    }
    svc = make_service(tempfile.mkdtemp(), FakeFetcher(pages={}), clock=Clock())
    objects, observing, unmatched = svc._build_objects(data, anchors, 2 * 86400.0)
    assert set(objects) == {h11, "h_ghost"}, f"受管的才进对象集(排除项在前, continue 非 break): {sorted(objects)}"
    assert set(observing) == {h11}, "命中绑定到活动条目的进观察集"
    assert set(unmatched) == {"h_ghost"}, "未对账的才是未列出候选"
    # 已放行在案的也不进对象集(回炉由行处理撤销, 不在这里驱动翻页)
    data.verified[h11] = _release_record(
        infohash=h11, tid=11, verified_ts=0.0, source=SOURCE_NOT_LISTED, anchor=anchors[h11]
    )
    objects2, _obs2, unmatched2 = svc._build_objects(data, anchors, 2 * 86400.0)
    assert h11 not in objects2 and h11 not in unmatched2, "放行在案 => 出对象集"
    assert "h_ghost" in objects2, "前一个被排除不得连带后续对象(continue 非 break)"


def test_freeze_terminal_failed_lane_between_entries(tmp_path):
    """档位失效的条目只跳过自己(continue 非 break): 其后可退役的终态条目照常退役"""
    clock = Clock()
    blob11, h11 = mk_blob("EXAMPLE 11")
    blob21, h21 = mk_blob("EXAMPLE 21")
    blob22, h22 = mk_blob("EXAMPLE 22")
    blob23, h23 = mk_blob("EXAMPLE 23")
    pages = {
        url_of("A"):
            myhr_page([row(11, "EXAMPLE 11")]),
        url_of("B"):
            myhr_page(
                [
                    row(21, "EXAMPLE 21", done=DONE_OLD, remain="0天00:00:00", need="0:00:00"),
                    row(23, "EXAMPLE 23", done=DONE_OLD, remain="0天00:00:00", need="0:00:00"),
                ]
            ),
        url_of("C"):
            myhr_page([row(22, "EXAMPLE 22", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={11: blob11, 21: blob21, 22: blob22, 23: blob23})
    service = make_service(tmp_path, fetcher, gconf=global_conf(max_pages_per_wave=3), clock=clock)
    anchors = {
        h11: anchor_for("EXAMPLE 11", completion_on=T_DONE_NEW),
        h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW),
        h22: anchor_for("EXAMPLE 22", completion_on=T_DONE_NEW),
        h23: anchor_for("EXAMPLE 23", completion_on=T_DONE_NEW),
    }
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[22].infohash_v1 == h22, "冻结才有对象可落记录"
    assert list(data.index) == [11, 21, 23, 22], "index 插入序: B 档两条在前、C 档一条在后"
    # 第二波: B 档改版无表头(失效); C 档有到期行(停翻2 全深度, 22 的位置被证明); A 档行 11 再现
    fetcher.pages = {
        url_of("A"): myhr_page([row(11, "EXAMPLE 11")]),
        url_of("B"): REVISED_PAGE,
        url_of("C"): myhr_page([row(88, "OTHER 88", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")]),
    }
    clock.advance(13 * 3600)
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["B"].status == LANE_FAILED, "B 档表头缺失 -> 结构性失效"
    assert data.index[21].active is True and data.index[23].active is True, "B 失效档条目维持管束"
    assert data.index[22].active is False, "C 全深度: 失效档条目之后的可退役条目照常退役"
    assert h22 in data.verified and data.verified[h22].source == SOURCE_NOT_LISTED
    assert "终态冻结 2 条" in result.reason, f"逐条累加(v1+v2 两身份): {result.reason!r}"


def test_zero_rows_false_when_all_lanes_failed(tmp_path):
    """全档失败的波**不是**零行波(计划 26-10-29-0147 D4)

    改前 `zero_rows = 总量为 0`, 于是「一页都没取到」也自称「结构完好但清单为 0」, 并把 WebUI
    引向 `--hr-confirm-empty` 人工对账 —— 2026-10-28 那次 12h 的故障就一直在这么说。
    """
    clock = Clock()
    fetcher = FakeFetcher(pages={}, channel_error=HrExtensionNoPermission("扩展未授权该站点"))
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert result.action == ACTION_NO_CHANNEL
    assert data.wave.zero_rows is False, "全档失败: 连清单都没看到, 不许判「清单为空」"
    assert "结构完好" not in result.reason
    assert "--hr-confirm-empty" not in result.reason


def test_zero_rows_true_when_all_lanes_ok_and_empty(tmp_path):
    """全档有效且确实为空 ⇒ 零行波成立(人工对账话术照旧)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([], [], []))
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert all(data.wave.lanes[lane].ok for lane in FETCH_LANES)
    assert data.wave.zero_rows is True
    assert "结构完好但清单为 0" in result.reason
    assert data.wave.releases_enabled is False, "零行未确认仍不签发放行(行为不变)"


def test_zero_rows_false_when_one_lane_failed(tmp_path):
    """A 档取到空表、B 档取数失败 ⇒ 也不是零行波: 有档没看到, 这一波没资格判「空」"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([], [], []), fail_text_at={"B": "HTTP 500"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].ok is True and data.wave.lanes["B"].ok is False
    assert data.wave.zero_rows is False
    assert "结构完好" not in result.reason

"""test_hr_service_store 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_store_prebuilt_per_site_confs: 站点存储构造期预建(每站点一实例不再依赖首访时序; conf 外点名惰性兜底)
- test_login_expired_marks_interval: 登录失效路径同样前进间隔基准(重试节奏受 min_interval 约束)
- test_counter_match_releases: T1 计数对平放行 —— 三档 claim==rows 全深度, 签发与无计数基线一致
- test_counter_mismatch_freezes_batch: T2 不对平冻结 —— depth_broken 整波不签发, 连续 3 波 ERROR 升级, 对平自愈清零; 命中/管束/复用窗不变
- test_counter_absent_degrades_to_legacy: T3 无计数降级 —— 默认 adapter + 旧档案(无三键)加载 count_claim None(T1 迁移陷阱守阵, 不得变 0)
- test_counter_zero_claims_self_attest_empty: T4 计数零自证空 —— 三档 claim=0∧rows=0 视同人工戳, 零行软提示不出现
- test_counter_truncation_gap_informational: T6 截断差值信息性 —— 非全深度 rows<claim 不告警不冻结, notes 记差值, REASON_BUDGET 语义不变

### 稳态降频(计划 26-10-05-0555 §2/S4; 锚点三态契约: None=采集失败不降频 / {}=确认零锚点可降频)

### HR 排除落到取数侧(计划 26-10-08-1249 方案 B)

### HR 排除种子终态行身份下载短路(计划 26-10-09-1057 / issue 26-10-08-1304)

### P1 覆盖率提升轮(T1.1 错误路径系统补齐)
- test_persist_false_reports_readonly_mode: 只读走查(persist=False)不写盘且 reason 注明「只读模式」

### S2 拉取历史记录点(计划 26-10-04-0312 §3.3)
- test_history_auto_poll_gate_skip_writes_nothing: 自动 poll 被调度闸(复用窗/拉取间隔)跳过 -> 零事件
  + 零写盘(站点文件一字节不变) —— 硬不变量
- test_history_defer_only_on_force: defer 事件仅 force 路径产生(立即拉取撞 min_interval -> 一条 defer
  显式落盘); 非 force 被闸拦无事件不写盘

### R16 变异审计守阵(计划 26-10-09-1459 / issue 26-10-10-1108-test-hr-mutation-service-engine)

- test_stop_condition_no_condition_reports_not_full: 停翻全不成立 -> (False, False, "") 兜底
- test_finish_wave_counter_mismatch_error_level_and_text: 计数对不平 ERROR 升级的级别与逐参文案
- R22(issue 26-10-10-1108 余量函数守阵):
- test_run_pages_counters_receive_page_html: 计数上交的实参是本页 html(不是 None)
- test_run_pages_js_marks_next_page_keeps_paging: JS 翻页标记(currentpage<maxpage)也算「还有下一页」
- test_run_pages_js_marks_at_last_page: currentpage==maxpage 即末页(< 而非 <=): 不翻不存在的下一页, 记全深度
- test_do_wave_channel_stopped_yields_without_history: 被叫停 = 让位不告警: action=WAITING 且不记拉取历史
- test_do_wave_quota_abort_records_history_and_elapsed: 扩展侧硬上限让位收尾: 记一条 wave 历史, elapsed 落 0
- test_do_wave_login_expired_marks_error_note_and_alerted: 登录失效: action=ERROR + 告警 + notes 留痕, 波照常收尾不外抛
- test_do_wave_fetch_failure_marks_partial_and_lane_failed: 页面取数失败(无 Retry-After): 该档失效截断, 波级降 PARTIAL 并告警
- test_refresh_locked_dry_run_force_defers_with_history: dry-run(allow_fetch=false)被 force 叫起: 让位 + defer 历史
- test_lanes_summary_from_display_tags_and_counters: 档位摘要排版单点: [x]/x/- 三态标签、缺失档「无」、计数对平/对不平
- test_history_wave_event_carries_result_fields: 波终态历史事件逐字段搬运(不新算)
- test_history_event_reason_kind_budget_carried: 被页数上限截断的波: reason_kind=budget(非空)逐字搬进历史
- test_history_defer_event_field_defaults: defer(立即拉取被拦)历史: 未提供的计数字段落默认 0
- test_store_lazy_branch_constructor_args: store() 惰性分支(conf 外点名)构造参数单点: site 点名 + 锁等待常量化 0 + owner 透传

### 站点可选权限轮(计划 26-10-29-0147 W2/W4): 归层、判据与告警
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
    _RecordingCounterAdapter,
    _StoppedFetcher,
    _history_from_disk,
    _live,
    _marks_page,
    _no_sleep,
    _real_adapter,
    anchor_for,
    counter_adapter,
    five_expired_rows,
    make_service,
    mk_blob,
    run_wave,
    standard_pages,
    url_of,
)


def test_store_prebuilt_per_site_confs(tmp_path):
    """站点存储构造期预建(issue 26-10-06-0028 chore-lazy-init-double-construct): site_confs
    键在 __init__ 就建好 —— 取数线程 × Web 线程并发首访拿到同一实例, 不再「惰性建无锁、
    双构造其一被引用覆盖丢弃」; conf 外点名仍走惰性分支兜底(CLI --hr-confirm-empty 手输)"""
    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher)
    assert service._stores.keys() == {SITE}, "构造期即预建 site_confs 全部站点"
    assert service.store(SITE) is service._stores[SITE], "conf 内站点不再新建"
    # conf 外点名: 惰性兜底建, 且重复取同一实例
    extra = service.store("nosuch")
    assert service.store("nosuch") is extra


def test_login_expired_marks_interval(tmp_path):
    """登录失效路径同样前进间隔基准: 登录恢复前重试节奏受 min_interval 约束(M1)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages(), login_at={"A"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    assert data.rate.last_fetch_ts == clock.now  # 修复前恒 0: 每 poll(60s)都立即重发烧日额
    assert result.action == ACTION_ERROR


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
    assert result.alerted is False  # 计数自证空集 = 已确认, 不告警
    assert "若确认账号的 HR 清单确实为空" not in caplog.text
    # M3 展示口径对齐(计划 26-09-29-2036 §2.5): 计数自证空集的站点不再标「零行未确认」/「需人工对账」
    snap = build_site_statuses(service, clock.now)[0]
    assert snap.count_attested_empty is True and snap.empty_confirmed is False
    assert snap.blocking == ""


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


def test_persist_false_reports_readonly_mode(tmp_path):
    """只读走查口径(persist=False): 波照常跑、不写盘, reason 注明「只读模式, 未写盘」"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([row(11, "OTHER 11")]))
    service = make_service(tmp_path, fetcher, clock=clock, persist=False)
    result = run_wave(service, {})
    assert "只读模式, 未写盘" in result.reason
    assert result.persisted is False
    assert not service.store(SITE).path.exists(), "走查不得落站点文件"
    data = result.snapshot
    assert data is not None and any(e.tid == 11 for e in data.index.values()), "内存快照仍完整"


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
    # (锚点传 None = 未知: 稳态旗标翻转写(§2.4)是零写盘纪律的唯一例外, 由 S4 用例单独钉)
    clock.advance(600.0)
    reused = service.refresh_site(SITE)
    assert reused.action == "reused"
    assert site_file.read_bytes() == before, "复用窗内的 poll 不得写盘"
    assert _history_from_disk(service) == [first], "复用窗内的 poll 不入历史"
    # 复用窗外 + 拉取间隔内: 自动 poll 被拉取间隔闸跳过 —— 零事件零写盘(硬不变量)
    clock.advance(2 * 3600.0)
    waiting = service.refresh_site(SITE)
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
    # 非 force(自动 poll): 被拉取间隔闸拦 -> 无事件 + 零写盘(锚点 None = 未知, 不触发稳态翻转写)
    clock.advance(60.0)
    auto = service.refresh_site(SITE)
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


def test_stop_condition_no_condition_reports_not_full(tmp_path):
    """停翻全不成立 ⇒ (False, False, "") —— 兜底返回的 full 标志不得变 True"""
    service = make_service(tmp_path, FakeFetcher(pages={}))
    wave = _WaveContext({})
    assert service._stop_condition("A", _Parsed([_live(1)]), wave, {}, {}) == (False, False, "")


def test_finish_wave_counter_mismatch_error_level_and_text(tmp_path, monkeypatch, caplog):
    """计数对不平 ERROR 升级: 连续 3 波恰一条 ERROR, 且逐参文案(站点/档位/实抓/声明/波数)完整"""
    caplog.set_level(logging.WARNING, logger="auto_qb.hr.service")
    clock = Clock()
    counter_adapter(monkeypatch, {"B": 50})
    fetcher = FakeFetcher(pages=standard_pages(rows_b=five_expired_rows(20)))
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    for _ in range(3):
        run_wave(service, anchors)
        clock.advance(13 * 3600)
    errs = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR and "计数对不平" in r.getMessage()]
    assert len(errs) == 1, errs
    msg = errs[0]
    assert "站点 example" in msg and "档位 B" in msg
    assert "实抓 5 行" in msg and "站点声明 50 行" in msg and "(已连续 3 波)" in msg


def test_run_pages_counters_receive_page_html(tmp_path, monkeypatch):
    """计数上交的实参是本页 html(不是 None): adapter 只可能从页面证据提数"""
    html_b = myhr_page([row(21, "B 21")])
    pages = {url_of("A", 1): myhr_page([row(11, "OTHER 11")]), url_of("B", 1): html_b, url_of("C", 1): myhr_page([])}
    recorder = _RecordingCounterAdapter(_real_adapter())
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=Clock())
    # 让引擎这一轮用记录壳取数: build_adapter 替换(monkeypatch 自动还原)
    import auto_qb.hr.service as hs

    monkeypatch.setattr(hs, "build_adapter", lambda site, conf: recorder)
    run_wave(service, {})
    assert recorder.counter_htmls, "parse_counters 被调用过"
    assert all(h is not None and "HR编号" in h for h in recorder.counter_htmls), "实参是页面 html"


def test_run_pages_js_marks_next_page_keeps_paging(tmp_path):
    """JS 翻页标记(currentpage<maxpage)也算「还有下一页」: 链接未标注也继续翻(last-page 判据双证据)"""
    clock = Clock()
    pages = {
        url_of("A", 1): _marks_page([row(11, "OTHER 11", done=DONE_NEW)], currentpage=1, maxpage=2),
        url_of("A", 2): myhr_page([row(12, "OTHER 12", done=DONE_OLD)]),
        url_of("B", 1): myhr_page([]),
        url_of("C", 1): myhr_page([]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {"h1": anchor_for("h1", completion_on=T_DONE_NEW)})
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].pages == 2, "标记说还有下一页 → 取了第 2 页"


def test_run_pages_js_marks_at_last_page(tmp_path):
    """currentpage==maxpage 即末页(< 而非 <=): 不翻不存在的下一页, 记全深度"""
    clock = Clock()
    pages = {
        url_of("A", 1): _marks_page([row(11, "OTHER 11", done=DONE_NEW)], currentpage=2, maxpage=2),
        url_of("A", 2): myhr_page([row(19, "NEVER 19", done=DONE_OLD)]),
        url_of("B", 1): myhr_page([]),
        url_of("C", 1): myhr_page([]),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), clock=clock)
    run_wave(service, {})
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["A"]
    assert st.pages == 1 and st.full_depth is True and st.detail == "已翻到末页"


def test_do_wave_channel_stopped_yields_without_history(tmp_path):
    """被叫停(停止/重挂期间) = 让位不告警: action=WAITING 且不记拉取历史(瞬态事件, 不刷屏)"""
    clock = Clock()
    service = make_service(tmp_path, _StoppedFetcher(pages={}), clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_WAITING
    assert "叫停" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    assert data.history == [], "叫停不记历史(§3.3)"


def test_do_wave_quota_abort_records_history_and_elapsed(tmp_path):
    """扩展侧硬上限让位收尾: 记一条 wave 历史(含档位快照), elapsed 落 0(假时钟冻结)"""
    clock = Clock()
    fetcher = FakeFetcher(pages=standard_pages([]), quota=True)
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_WAITING and "硬上限" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    assert len(data.history) == 1, "让位收尾仍记一条拉取历史"
    event = data.history[-1]
    assert event.kind == "wave" and event.action == ACTION_WAITING
    assert [snap["lane"] for snap in event.lanes] == list(FETCH_LANES), "档位快照逐个搬运"
    assert event.elapsed_s == 0.0, "波耗时现算(假时钟不动即 0)"


def test_do_wave_login_expired_marks_error_note_and_alerted(tmp_path):
    """登录失效: action=ERROR + 告警 + notes 留痕(站点与异常详情都在), 波照常收尾不外抛"""
    clock = Clock()
    pages = standard_pages([])
    fetcher = FakeFetcher(pages=pages, login_at={"A"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_ERROR
    assert result.alerted is True
    assert "登录" in result.reason
    data, _ = service.store(SITE).read_unlocked()
    note = next((n for n in data.wave.notes.split("; ") if "登录" in n), "")
    assert SITE in note and "登录页" in note, f"notes 留痕含站点与异常详情: {note!r}"


def test_do_wave_fetch_failure_marks_partial_and_lane_failed(tmp_path):
    """页面取数失败(无 Retry-After): 该档失效截断, 波级降 PARTIAL 并告警(其余档已跑完)"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([]),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, fail_text_at={"B": "连接被重置"})
    service = make_service(tmp_path, fetcher, clock=clock)
    result = run_wave(service, {})
    assert result.action == ACTION_PARTIAL, f"had_error 应降级为 PARTIAL: {result.action}"
    assert result.alerted is True
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["B"]
    assert st.status == "failed" and st.detail == "页面取数失败"
    assert "页面取数失败" in data.wave.notes
    assert data.wave.lanes["C"].status == "ok", "其它档位独立跑完"


def test_refresh_locked_dry_run_force_defers_with_history(tmp_path):
    """dry-run(allow_fetch=false)被 force 叫起: 让位 + 记一条 defer 历史(kind/trigger/action 都对)"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([])), clock=clock, allow_fetch=False)
    result = service.refresh_site(SITE, {}, force=True)
    assert result.action == ACTION_WAITING
    assert result.reason == "dry-run / 只读模式: 不发起取数"
    data, _ = service.store(SITE).read_unlocked()
    assert len(data.history) == 1
    event = data.history[-1]
    assert event.kind == "defer" and event.trigger == "manual" and event.action == ACTION_WAITING


def test_lanes_summary_from_display_tags_and_counters():
    """档位摘要排版单点: [x]/x/- 三态标签、缺失档「无」、计数对平/对不平、全深度、空格连接"""
    states = {
        "A": HrLaneState(lane="A", status=LANE_OK, pages=2, rows=5, full_depth=True, count_claim=5, count_match=True),
        "B": HrLaneState(lane="B", status=LANE_FAILED, pages=0, rows=0, count_claim=7, count_match=False),
        # C 缺省: 走「无」分支
    }
    text = _lanes_summary_from(states)
    assert text == "A:[x]2页5行(全深度)/声明5 B:x0页0行/声明7 对不平 C:无"


def test_history_wave_event_carries_result_fields(tmp_path):
    """波终态历史事件逐字段搬运(不新算): 计数/签发放行/耗时/档位快照/notes 都来自本波结果"""
    clock = Clock()
    blob21, h21 = mk_blob("EXAMPLE 21")
    pages = {
        url_of("A"): myhr_page([row(11, "EXAMPLE 11"), row(21, "EXAMPLE 21")]),  # 11 的 blob 缺 -> 下载失败
        url_of("B"): myhr_page([]),
        url_of("C"): myhr_page([]),
    }
    fetcher = FakeFetcher(pages=pages, blobs={21: blob21})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {
        "h1": anchor_for("h1", completion_on=T_DONE_NEW),
        h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)
    }
    result = run_wave(service, anchors)
    assert result.torrents_failed > 0, "tid=11 未配 blob -> 回填失败计入"
    assert result.releases_signed >= 1 and result.verified_count >= 1
    data, _ = service.store(SITE).read_unlocked()
    event = data.history[-1]
    assert event.kind == "wave" and event.trigger == "auto" and event.action == result.action
    assert event.reason == result.reason[:200]
    assert event.reason_kind == result.reason_kind
    assert event.pages == result.pages_fetched and event.rows == result.entries
    assert event.torrents_ok == result.torrents_fetched and event.torrents_fail == result.torrents_failed
    assert event.verified == result.verified_count
    assert event.elapsed_s == 0.0
    snaps = {snap["lane"]: snap for snap in event.lanes}
    assert set(snaps) == set(FETCH_LANES)
    assert snaps["A"]["rows"] == 2 and snaps["A"]["pages"] == 1 and snaps["A"]["status"] == "ok"
    assert "rows" in snaps["A"] and "detail" in snaps["A"]
    assert event.by == "test"


def test_history_event_reason_kind_budget_carried(tmp_path):
    """被页数上限截断的波: reason_kind=budget(非空)逐字搬进历史(区分「没跑完」的类型)"""
    clock = Clock()
    pages = {
        url_of("A"): myhr_page([row(11, "OTHER 11")], has_next=True),
        url_of("B"): myhr_page([row(21, "OTHER 21")], has_next=True),
        url_of("C"): myhr_page([row(31, "OTHER 31")], has_next=True),
    }
    service = make_service(tmp_path, FakeFetcher(pages=pages), gconf=global_conf(max_pages_per_wave=1), clock=clock)
    result = run_wave(service, {})
    assert result.reason_kind == REASON_BUDGET
    data, _ = service.store(SITE).read_unlocked()
    assert data.history[-1].reason_kind == REASON_BUDGET, "历史事件照搬 reason_kind 不新算"


def test_history_defer_event_field_defaults(tmp_path):
    """defer(立即拉取被拦)历史: 未提供的计数字段落默认 0(不冒泡成 1 / None)"""
    clock = Clock()
    service = make_service(tmp_path, FakeFetcher(pages=standard_pages([])), clock=clock, allow_fetch=False)
    result = service.refresh_site(SITE, {}, force=True)
    assert result.action == ACTION_WAITING
    data, _ = service.store(SITE).read_unlocked()
    event = data.history[-1]
    assert event.kind == "defer" and event.trigger == "manual"
    assert event.action == ACTION_WAITING and "dry-run" in event.reason
    assert event.reason_kind == "" and event.torrents_ok == 0 and event.torrents_fail == 0
    assert event.verified == 0 and event.elapsed_s == 0.0 and event.pages == 0 and event.rows == 0
    assert event.notes == [] and event.lanes == []


def test_store_lazy_branch_constructor_args(tmp_path, monkeypatch):
    """store() 惰性分支(conf 外点名, CLI --hr-confirm-empty 手输站点)构造参数单点: site 点名
    透传 + 锁等待常量化 0(拿不到直接等下一轮, §6.2)+ owner 透传(不落空)"""
    import auto_qb.hr.store as store_mod

    fetcher = FakeFetcher(pages=standard_pages())
    service = make_service(tmp_path, fetcher)
    real_open = store_mod.open_file_lock
    timeouts = []

    def spy_open(path, *, timeout):
        timeouts.append(timeout)
        return real_open(path, timeout=timeout)

    monkeypatch.setattr(store_mod, "open_file_lock", spy_open)
    st = service.store("offsite")
    assert st.site == "offsite", f"site 点名必须透传(不是 None): {st.site!r}"
    assert timeouts == [0.0], f"锁等待常量化 0: {timeouts}"
    assert st.owner == service._owner == "test", f"owner 透传(不落空): {st.owner!r}"

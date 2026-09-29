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
"""
import logging
import time
from datetime import datetime
from typing import Dict

import pytest

import auto_qb.hr.service as hr_service
from auto_qb.hr import events
from auto_qb.hr.fetcher import HrFetchError
from auto_qb.hr.model import (
    FETCH_LANES,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrLaneState,
    HrSiteData,
)
from auto_qb.hr.resolve import HrAnchor, HrIdentity, judge_record
from auto_qb.hr.status import build_site_statuses
from auto_qb.hr.service import (
    ACTION_ERROR,
    ACTION_PARTIAL,
    ACTION_WAITING,
    FUZZY_NAME_K,
    HrRefreshService,
    REASON_BUDGET,
    fuzzy_name_match,
)

from hr_helpers import (
    EMPTY_TABLE_PAGE,
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

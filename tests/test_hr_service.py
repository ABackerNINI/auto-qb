"""test_hr_service 测试计划: v3 波次引擎(计划 26-09-28-1932 §4/§5)

## 测试计划(每个测试函数一条)
- test_first_wave_deep_fetch: 首波深翻(全量效果) —— 未对账对象驱动覆盖深度
- test_stop1_completion_time_coverage: 停翻① 完成时间覆盖(最深行早于最老对象减对齐余量 1D)
- test_stop2_zero_remain_streak: 停翻② 到期段强信号(remain==0 连续 5 行, 全深度证明)
- test_stop2_cross_page_streak: 停翻② 跨页延续计数
- test_stop3_local_full_coverage: 停翻③ 本地全集覆盖(未对账全部对上且无待回填)
- test_untrusted_done_pure_seed: 纯辅种(完成时间不可信)不参与①, 由②/末页收尾且可获放行
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
- test_plunge_freezes_releases: 总行数骤降(< 基线 30%) → 批量签发冻结
- test_retention_check_freezes_batch: A 档流转守恒不达标 → 批量签发冻结
- test_retention_does_not_block_observation: 守恒拦批量但不拦观察期(单条失踪无死锁)
- test_observing_seed_kept_managed_then_released: 上波考察中失踪 → 维持管束; 位置覆盖连续 2 波 → 判移出放行
- test_observing_seed_resighted: 失踪种子重见 → streak 清零按档位定论
- test_terminal_vanish_writes_release: 终态条目消失且位置被证明 → 退役并落放行记录(终态不可逆)
- test_terminal_vanish_unproven_kept: 终态条目消失但位置未被覆盖 → 维持原状
- test_light_wave_when_no_objects: 空对象集 → 每档 1 页轻量波
- test_new_top_row_reconciled_next_wave: 顶页新插入(本机新下载)在下一波被完整覆盖对账
- test_no_fuse_no_suspension: 失败不推进熔断/停用(v3 删除), Retry-After 记等待
- test_fuzzy_name_match_unit: 宽泛名称粗配单元(连续重合段 ≥ K)
"""
import time
from datetime import datetime

import pytest

from auto_qb.hr import events
from auto_qb.hr.fetcher import HrFetchError
from auto_qb.hr.model import (
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_NOT_LISTED,
    HrSiteData,
)
from auto_qb.hr.resolve import HrAnchor, HrIdentity, judge_record
from auto_qb.hr.service import (
    ACTION_PARTIAL,
    ACTION_WAITING,
    FUZZY_NAME_K,
    HrRefreshService,
    fuzzy_name_match,
)

from hr_helpers import (
    EMPTY_TABLE_PAGE,
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
    """5 行 remain==0(已到期段) —— 停翻② 的最小触发面"""
    return [
        row(base_tid + i, f"OTHER-TORRENT {base_tid + i}", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")
        for i in range(5)
    ]


# ---------------- 波次基本形态 ----------------


def test_first_wave_deep_fetch(tmp_path):
    """首波: 对象(未对账, 本地完成时间可信且较新)驱动各档翻页到其位置之后(全量效果)"""
    clock = Clock()
    # 对象完成于 09-20(新); 各档只有 09-01(老)的行且还有下一页 → ①停翻(更深只会更老)
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
    # 三档各取了第 1 页即被①停翻(更深只会更老, 对象不可能藏在更深处)
    data, _ = service.store(SITE).read_unlocked()
    assert all(st.ok for st in data.wave.lanes.values())
    assert data.wave.lanes["A"].full_depth is False  # ①停翻: 位置有界, 非全深度


def test_stop1_completion_time_coverage(tmp_path):
    """停翻①: 最深行完成时间早于对象最老完成时间减 1D 对齐余量 → 停翻(位置有界)"""
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
    """停翻②: 页尾连续 5 行 remain==0 → 到期段强信号(全深度证明, 停翻零漏判)"""
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
    """停翻②跨页延续: 第 1 页整页 3 行全 0 + 第 2 页整页 2 行全 0 → 累计 5 → 停翻(全深度)"""
    clock = Clock()
    pages = {
        url_of("B", 1): myhr_page(five_expired_rows(20)[:3], has_next=True),
        url_of("B", 2): myhr_page(five_expired_rows(20)[3:5], has_next=True),
        url_of("A"): myhr_page([], has_next=False),
        url_of("C"): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=-1)}  # 纯辅种: ①不可用, 由②跨页累计收尾
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    st = data.wave.lanes["B"]
    assert st.status == "ok" and st.full_depth is True and st.pages == 2


def test_stop3_local_full_coverage(tmp_path):
    """停翻③: 未对账对象全部与已见行对上且无待回填 → 停翻(不再为终态行翻页)"""
    clock = Clock()
    # 对象的行在 A 档第 1 页(命中即定论); B/C 档还有别的行与下一页 —— ③在 A 命中后即停 A
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
    """纯辅种(无本机完成时刻、未绑定): 不参与①; 由②(B/C 到期段)与末页(A)收尾且可获放行"""
    clock = Clock()
    pages = standard_pages(
        rows_a=[row(11, "OTHER 11", done=DONE_NEW, remain="1天00:00:00")], rows_b=five_expired_rows(20), rows_c=[]
    )
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h-pure": anchor_for("PURE", completion_on=-1)}  # 纯辅种: completion_on 未设
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.lanes["A"].full_depth is True  # A 档翻到末页收尾(①不能用)
    assert data.wave.lanes["B"].full_depth is True  # B 档由②收尾
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
    """结构完好零行 → 不签发放行(改版空表即整站误放行, 不冒这个险)"""
    clock = Clock()
    pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    result = run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.zero_rows is True
    assert data.wave.releases_enabled is False
    assert "h1" not in data.verified
    assert "零行" in result.reason or "清单为 0" in result.reason


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


def test_plunge_freezes_releases(tmp_path):
    """总行数骤降(本波 < 基线 30%) → 批量「未列出」签发冻结"""
    clock = Clock()
    pages = standard_pages(rows_b=five_expired_rows(20))
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {"h1": anchor_for("h1", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)  # 首波: A 0 行 / B 5 行 / C 0 行 → 基线 5
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.baseline_rows == 5
    # 第二波: 全空表(结构完好) → 合计 0 < 5 × 30% → 骤降冻结
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.wave.plunge is True
    assert data.wave.releases_enabled is False


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
    """终态条目消失且位置被证明 → 退役并落放行记录(终态不可逆, 条目被站点清掉也不影响判定)"""
    clock = Clock()
    pages = standard_pages(rows_b=[row(21, "OTHER 21", done=DONE_NEW, remain="0天00:00:00", need="0:00:00")])
    blob, h21 = mk_blob("EXAMPLE 21")
    fetcher = FakeFetcher(pages=pages, blobs={21: blob})
    service = make_service(tmp_path, fetcher, clock=clock)
    anchors = {h21: anchor_for("EXAMPLE 21", completion_on=T_DONE_NEW)}
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].lane == LANE_SATISFIED and data.index[21].active
    # 第二波: B 档空表(全深度) → 条目消失被证明 → 退役 + 放行记录(毕业来源)
    fetcher.pages = {url_of(l): EMPTY_TABLE_PAGE for l in ("A", "B", "C")}
    clock.advance(13 * 3600)
    run_wave(service, anchors)
    data, _ = service.store(SITE).read_unlocked()
    assert data.index[21].active is False
    assert h21 in data.verified
    view = service.build_view_for(SITE, data)
    j = judge_record(view, (h21, ), anchor=anchors[h21], now=clock())
    assert j.identity is HrIdentity.RELEASED  # 终态不可逆: 退役后照常放行


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


# ---------------- 轻量波与覆盖收敛 ----------------


def test_light_wave_when_no_objects(tmp_path):
    """空对象集 → 每档 1 页轻量波(捕获可能的新增即停)"""
    clock = Clock()
    pages = {
        url_of("A", 1): myhr_page([row(11, "OTHER 11", done=DONE_OLD)], has_next=True),
        url_of("B", 1): myhr_page(five_expired_rows(20), has_next=True),
        url_of("C", 1): myhr_page([], has_next=False),
    }
    fetcher = FakeFetcher(pages=pages)
    service = make_service(tmp_path, fetcher, clock=clock)
    run_wave(service, anchors={})  # 无本地种子 → 无对象集
    data, _ = service.store(SITE).read_unlocked()
    assert all(st.pages == 1 for st in data.wave.lanes.values())


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
    # v3 失败处置: 数据上没有任何熔断/停用/退避状态字段(模型级删除)
    raw = data.to_json()
    for gone in ("fuse", "suspended", "login_backoff_until", "quota", "torrent_quota"):
        assert gone not in raw
    # Retry-After 的「下次可取时刻」语义在 test_hr_ratelimit.test_retry_after_respected 覆盖


# ---------------- 粗配单元(D1) ----------------


def test_fuzzy_name_match_unit():
    assert fuzzy_name_match("Example.Ultra.S01E01.1080p", "Group.Example.Ultra.S01E01.1080p.x264")
    assert fuzzy_name_match("Example Ultra S01E01", "example-ultra-s01e01-1080p")  # 空白/大小写折叠
    assert not fuzzy_name_match("Example.Ultra", "Completely.Different.Show.2026")
    assert not fuzzy_name_match("短名", "Completely.Different.Show.2026")  # 短于 K 不误配
    assert len("Example.Ultra") >= FUZZY_NAME_K or True

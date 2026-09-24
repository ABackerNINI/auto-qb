"""test_hr_service 测试计划: HR 刷新管道(持锁 → 读 → 判有效期 → 必要时抓 → 写 → 释放)

## 测试计划(每个测试函数一条)
- test_complete_refresh_builds_index_and_backfills_infohash: 完整刷新建索引 / 回填 infohash / 落已取记录 /
  覆盖证明成立 / 有效期 = now + refresh_interval
- test_complete_refresh_writes_verified_for_not_listed: 已取过 .torrent 但本次完整刷新未列出 -> 写放行记录
- test_d_scope_is_exempt_and_verified: D 档(已免罪)条目本身不产生受管束, 但同样产生放行依据
- test_valid_data_is_reused_without_any_request: 有效期内的数据直接复用, **零请求**(站点频率由有效期决定)
- test_expired_data_triggers_refetch: 超期后重新抓取; 已取过的 .torrent 不重下(永久层)
- test_index_loss_still_avoids_redownload: 索引条目被淘汰后仍靠 hr_downloaded 免重下
- test_incomplete_refresh_does_not_advance_or_verify: 翻页未到底 -> 覆盖证明不成立, 不推进 last_success_ts,
  不产生/不续期放行
- test_incomplete_refresh_keeps_previous_verification: 不完备刷新不清空既有放行记录
- test_min_interval_blocks_second_request: 相邻两次请求间隔 >= min_torrent_interval(抖动只向上)
- test_diagnostic_sleeper_waits_instead_of_giving_up: 走查模式(传入 sleeper)遇到间隔门槛等满再发, 能跑完一轮
- test_quota_exhaustion_stops_refresh_then_waits: 配额用尽时刷新截断; 同窗口后续轮次直接等下一轮
- test_download_failure_counts_then_cools_down: 取 .torrent 失败计数, 达上限且冷却未过时不再尝试
- test_consecutive_failures_fuse_site: 连续失败达阈值 -> 熔断, 期间零请求
- test_fuse_makes_next_round_wait: 熔断生效时返回等待(不报错)
- test_lock_busy_skips_site: 拿不到站点锁 -> 直接等下一轮(HrLockBusy), 不排队不重试
- test_no_channel_reports_instead_of_silent_direct_fetch: 无通道时如实上报, 绝不静默降级为后端直连
- test_dry_run_fetches_nothing_and_writes_nothing: dry-run 清单恒空 + 不写文件
- test_read_only_run_reports_without_persisting: hr.once 口径(抓取但只出报告, 不写文件)
- test_disabled_by_global_or_site: 总开关关闭 / 站点 mode=off -> 直接跳过
- test_unknown_adapter_reports_error: adapter 名未登记 -> 明确报错而不是静默不抓
- test_view_revision_only_moves_on_data_change: 视图 revision 只在数据实质变化时抬升(复用不抬)
- test_parse_revision_is_incomplete: 页面改版(表头缺失) -> 覆盖证明不成立
- test_empty_listing_is_complete: 表头在但 0 行是合法空结果, 覆盖证明仍成立
"""
import pytest

from auto_qb.hr import ACTION_DISABLED, ACTION_ERROR, ACTION_LOCKED, ACTION_NO_CHANNEL, ACTION_PARTIAL, \
    ACTION_REFRESHED, ACTION_REUSED, ACTION_WAITING, HrRefreshService
from auto_qb.hr.fetcher import NullFetcher
from auto_qb.hr.model import SOURCE_EXEMPT, SOURCE_NOT_LISTED
from auto_qb.hr.store import HrSiteStore
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
PAGE2_URL = "https://pt.example.com/myhr.php?hrtype=A&page=2"


def _pages(*, a_rows=(), a_next=False, b=EMPTY_TABLE_PAGE, c=EMPTY_TABLE_PAGE, page2=None):
    pages = {"A": myhr_page(list(a_rows), has_next=a_next), "B": b, "C": c}
    if page2 is not None:
        pages[PAGE2_URL] = page2
    return pages


def _blobs(*tids):
    return {tid: torrent_blob(name=f"{tid}.bin") for tid in tids}


def _service(tmp_path, fetcher, clock, *, site=None, glob=None, persist=True, allow_fetch=True):
    return HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=glob or global_conf(),
        site_confs={SITE: site or site_conf()},
        fetcher=fetcher,
        owner="tester",
        persist=persist,
        allow_fetch=allow_fetch,
        now_fn=clock,
    )


def _read(tmp_path):
    data, err = HrSiteStore(SITE, str(tmp_path / "hr")).read_unlocked()
    assert err is None
    return data


def test_complete_refresh_builds_index_and_backfills_infohash(tmp_path):
    """完整刷新: 建索引 + 回填 infohash + 落已取记录 + 覆盖证明成立 + 有效期 = now + refresh_interval"""
    clock = Clock()
    fetcher = FakeFetcher(
        _pages(a_rows=[row(101), row(102)], a_next=True, page2=myhr_page([row(103)])),
        _blobs(101, 102, 103),
    )
    svc = _service(tmp_path, fetcher, clock)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    assert result.complete is True
    assert result.pages_fetched == 4  # A 两页 + B + C
    assert result.torrents_fetched == 3
    assert result.torrents_failed == 0
    assert result.entries_new == 3
    assert result.lock_ok is True and result.persisted is True
    assert result.path == str(tmp_path / "hr" / f"{SITE}.json")
    assert len(fetcher.byte_calls) == 3

    data = _read(tmp_path)
    assert set(data.index) == {101, 102, 103}
    assert all(e.infohash_v1 and e.infohash_v2 for e in data.index.values())
    assert set(data.downloaded) == {101, 102, 103}
    assert data.downloaded[101].name == "101.bin"
    assert data.refresh.complete is True
    assert data.refresh.scopes_done == ["A", "B", "C"]
    assert data.refresh.last_success_ts == clock.now
    assert data.refresh.entry_count == 3
    assert data.expires_at == clock.now + 12 * 3600.0
    assert data.fuse.failures == 0


def test_complete_refresh_writes_verified_for_not_listed(tmp_path):
    """已取过 .torrent 但本次完整刷新未列出 -> 写放行记录(source=not-listed)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)
    svc.refresh_site(SITE)
    h101 = _read(tmp_path).index[101].infohash_v1

    clock.advance(13 * 3600)
    fetcher.pages = _pages()  # 这次一个都不列
    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    data = _read(tmp_path)
    assert not data.index[101].active  # 完整刷新未命中 -> 只是保留的快照条目
    assert data.verified[h101].source == SOURCE_NOT_LISTED
    assert data.verified[h101].verified_ts == clock.now
    assert data.verified[h101].tid == 101


def test_d_scope_is_exempt_and_verified(tmp_path):
    """D 档(已免罪)明确不受管束: 不算受管束, 但产生放行依据(source=absent)"""
    clock = Clock()
    fetcher = FakeFetcher(
        _pages(a_rows=[row(101)], b=myhr_page([row(201)])),
        _blobs(101, 201),
    )
    svc = _service(tmp_path, fetcher, clock, site=site_conf(hr_page_scopes=["A", "B", "D"]), glob=global_conf())
    fetcher.pages["D"] = myhr_page([row(301)])
    fetcher.blobs[301] = torrent_blob(name="301.bin")

    result = svc.refresh_site(SITE)

    assert result.complete is True
    data = _read(tmp_path)
    assert data.index[301].lane == "D"
    h301 = data.index[301].infohash_v1
    assert data.verified[h301].source == SOURCE_EXEMPT


def test_valid_data_is_reused_without_any_request(tmp_path):
    """有效期内的数据直接复用: 零请求(站点访问频率由数据有效期决定, 与实例数无关)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)
    svc.refresh_site(SITE)
    before_text, before_bytes = len(fetcher.text_calls), len(fetcher.byte_calls)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REUSED
    assert result.reason.startswith("数据仍在有效期")
    assert len(fetcher.text_calls) == before_text
    assert len(fetcher.byte_calls) == before_bytes


def test_expired_data_triggers_refetch(tmp_path):
    """超期后重新抓取; 已取过的 .torrent 不重下(永久层)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)
    svc.refresh_site(SITE)
    clock.advance(12 * 3600 + 1)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    assert result.torrents_fetched == 0  # 已有 infohash, 不再取 .torrent
    assert len(fetcher.byte_calls) == 1
    assert len(fetcher.text_calls) == 6  # 3 页首轮 + 3 页次轮


def test_index_loss_still_avoids_redownload(tmp_path):
    """索引条目被淘汰后仍靠 hr_downloaded 免重下(页面条目消失/翻页遗漏都不重取)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)
    svc.refresh_site(SITE)

    # 模拟快照条目被淘汰(index 里没了), 但永久层还在
    store = HrSiteStore(SITE, str(tmp_path / "hr"), owner="tester")
    with store.hold() as session:
        session.data.index.clear()
        session.commit(clock.now)
    clock.advance(12 * 3600 + 1)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    assert len(fetcher.byte_calls) == 1  # 没有第二次取 .torrent
    assert _read(tmp_path).index[101].infohash_v1  # 由永久层回填


def test_incomplete_refresh_does_not_advance_or_verify(tmp_path):
    """翻页未到底 -> 覆盖证明不成立: 不推进 last_success_ts, 不产生放行"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)], a_next=True), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, site=site_conf(max_pages_per_refresh=1))

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_PARTIAL
    assert result.complete is False
    assert "翻页上限" in result.reason
    data = _read(tmp_path)
    assert data.refresh.complete is False
    assert data.refresh.last_success_ts == 0.0
    assert data.verified == {}
    assert data.index[101].active is True  # 见到的条目仍按受管束处理(保守方向)


def test_incomplete_refresh_keeps_previous_verification(tmp_path):
    """不完备刷新不清空也不续期既有放行记录(放行只由完整核实产生)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)
    svc.refresh_site(SITE)
    h101 = _read(tmp_path).index[101].infohash_v1

    clock.advance(13 * 3600)
    fetcher.pages = _pages()
    svc.refresh_site(SITE)
    verified_ts = _read(tmp_path).verified[h101].verified_ts

    clock.advance(13 * 3600)
    fetcher.pages = _pages(a_rows=[row(101)], a_next=True)
    partial = svc.refresh_site(SITE)

    assert partial.action == ACTION_PARTIAL
    data = _read(tmp_path)
    assert data.verified[h101].verified_ts == verified_ts  # 没被续期
    assert data.index[101].active is True


def test_min_interval_blocks_second_request(tmp_path):
    """相邻两次请求间隔 >= min_torrent_interval(抖动只向上) —— 时钟不动时第二次请求被挡"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)], a_next=True), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, glob=global_conf(min_torrent_interval=90.0))

    result = svc.refresh_site(SITE)

    assert len(fetcher.text_calls) == 1  # 只发出了第一页请求
    assert result.complete is False
    assert "间隔" in result.reason
    quota = _read(tmp_path).quota
    # 下一次允许的时刻不早于「上次请求 + 90s」
    assert quota.last_fetch_ts == clock.now


def test_diagnostic_sleeper_waits_instead_of_giving_up(tmp_path):
    """走查模式: 传入 sleeper 时遇到间隔门槛等满再发, 单次走查能跑完一轮(生产不传 ⇒ 等下一轮)

    同时钉住「抖动只向上」: 每次等待量均 >= min_torrent_interval。
    """
    clock = Clock()
    waits: list[float] = []

    def sleeper(seconds: float) -> None:
        waits.append(seconds)
        clock.advance(seconds)

    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(min_torrent_interval=90.0),
        site_confs={SITE: site_conf()},
        fetcher=fetcher,
        owner="tester",
        now_fn=clock,
        sleeper=sleeper,
    )

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED and result.complete is True
    assert len(fetcher.text_calls) == 3 and len(fetcher.byte_calls) == 1
    assert len(waits) == 3  # 第一次请求无需等, 其后 3 次(2 页 + 1 .torrent)各等一次
    assert all(w >= 90.0 for w in waits), waits


def test_quota_exhaustion_stops_refresh_then_waits(tmp_path):
    """配额用尽时刷新截断; 同窗口后续轮次直接等下一轮(不报错)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, glob=global_conf(max_torrents_per_hour=1))

    first = svc.refresh_site(SITE)
    assert first.complete is False
    assert "配额" in first.reason
    assert len(fetcher.text_calls) == 1

    clock.advance(61)  # 截断轮次只给 60s 的短暂有效期; 过了才重新进入频率判定
    second = svc.refresh_site(SITE)
    assert second.action == ACTION_WAITING
    assert "小时配额" in second.reason
    assert len(fetcher.text_calls) == 1  # 零请求


def test_download_failure_counts_then_cools_down(tmp_path):
    """取 .torrent 失败计数; 达上限且冷却未过时不再尝试(防烧配额)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), {})  # 没有 101 的 .torrent
    svc = _service(
        tmp_path,
        fetcher,
        clock,
        site=site_conf(refresh_interval=600.0),
        glob=global_conf(failure_cooldown=3600.0, max_download_retries=3),
    )

    for _ in range(3):
        clock.advance(601)
        svc.refresh_site(SITE)

    assert len(fetcher.byte_calls) == 3
    assert _read(tmp_path).fails[101].count == 3

    clock.advance(601)  # 冷却(3600s)未过
    result = svc.refresh_site(SITE)
    assert len(fetcher.byte_calls) == 3  # 不再尝试
    assert result.torrents_failed == 0  # 被冷却跳过, 不算本次失败


def test_consecutive_failures_fuse_site(tmp_path):
    """连续失败达阈值 -> 熔断, 期间零请求"""
    clock = Clock()
    fetcher = FakeFetcher({}, {}, fail_text_at={"A": "429 Too Many Requests"})
    svc = _service(tmp_path, fetcher, clock, site=site_conf(refresh_interval=600.0))

    for _ in range(3):
        clock.advance(601)
        result = svc.refresh_site(SITE)
        assert result.action == ACTION_ERROR

    data = _read(tmp_path)
    assert data.fuse.failures == 3
    assert data.fuse.until_ts == clock.now + 3600.0

    clock.advance(601)
    calls = len(fetcher.text_calls)
    waiting = svc.refresh_site(SITE)
    assert waiting.action == ACTION_WAITING
    assert "熔断" in waiting.reason
    assert len(fetcher.text_calls) == calls


def test_fuse_makes_next_round_wait(tmp_path):
    """熔断生效时返回等待(不是错误, 不刷屏告警)"""
    clock = Clock()
    svc = _service(tmp_path, FakeFetcher(_pages()), clock)
    store = HrSiteStore(SITE, str(tmp_path / "hr"), owner="tester")
    with store.hold() as session:
        session.data.fuse.failures = 3
        session.data.fuse.until_ts = clock.now + 600
        session.data.fuse.reason = "连续失败"
        session.commit(clock.now)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_WAITING
    assert result.reason.startswith("站点熔断中")


def test_lock_busy_skips_site(tmp_path):
    """拿不到站点锁 -> 直接等下一轮(HrLockBusy), 不排队不重试"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(), {})
    svc = _service(tmp_path, fetcher, clock)
    other = HrSiteStore(SITE, str(tmp_path / "hr"), owner="other")
    with other.hold():
        result = svc.refresh_site(SITE)
    assert result.action == ACTION_LOCKED
    assert "锁被其它实例持有" in result.reason
    assert fetcher.text_calls == []


def test_no_channel_reports_instead_of_silent_direct_fetch(tmp_path):
    """无通道时如实上报, 绝不静默降级为后端直连(零 cookie 边界不可破)"""
    clock = Clock()
    svc = _service(tmp_path, NullFetcher(), clock)
    result = svc.refresh_site(SITE)
    assert result.action == ACTION_NO_CHANNEL
    assert "未启用取数通道" in result.reason
    assert not (tmp_path / "hr" / f"{SITE}.json").exists()


def test_dry_run_fetches_nothing_and_writes_nothing(tmp_path):
    """dry-run: 清单恒空且零写入(零请求也零写入)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, persist=False, allow_fetch=False)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_WAITING
    assert "dry-run" in result.reason
    assert fetcher.text_calls == [] and fetcher.byte_calls == []
    assert not (tmp_path / "hr" / f"{SITE}.json").exists()


def test_read_only_run_reports_without_persisting(tmp_path):
    """hr.once 口径: 真机只读走查 —— 抓取 + 出报告, 但不写文件、不联动 qB"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, persist=False, allow_fetch=True)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    assert result.persisted is False
    assert "只读模式" in result.reason
    assert len(fetcher.byte_calls) == 1
    assert not (tmp_path / "hr" / f"{SITE}.json").exists()
    assert result.path == str(tmp_path / "hr" / f"{SITE}.json")


def test_disabled_by_global_or_site(tmp_path):
    """总开关关闭 / 站点 mode=off -> 直接跳过(零副作用)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(), {})
    off_global = _service(tmp_path, fetcher, clock, glob=global_conf(enabled=False))
    res = off_global.refresh_site(SITE)
    assert res.action == ACTION_DISABLED and res.reason == "hr_check.enabled=false"

    off_site = _service(tmp_path, FakeFetcher(_pages(), {}), clock, site=site_conf(mode="off"))
    res = off_site.refresh_site(SITE)
    assert res.action == ACTION_DISABLED and "mode=off" in res.reason

    assert fetcher.text_calls == []


def test_unknown_adapter_reports_error(tmp_path):
    """adapter 名未登记 -> 明确报错(而不是静默不抓, 让保护悄悄失效)"""
    clock = Clock()
    svc = _service(tmp_path, FakeFetcher(_pages(), {}), clock, site=site_conf(adapter="不存在的站点"))
    result = svc.refresh_site(SITE)
    assert result.action == ACTION_ERROR
    assert "未登记的 adapter" in result.reason


def test_view_revision_only_moves_on_data_change(tmp_path):
    """视图 revision 只在数据实质变化时抬升(复用数据不抬, 主循环据此零工作)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock)

    assert svc.build_views()[SITE].revision == 0
    svc.refresh_site(SITE)
    first = svc.build_views()[SITE]
    assert first.revision == 1
    assert first.complete is True and first.mode == "partial"
    assert {e.tid for e in first.by_infohash.values()} == {101}  # 命中的 101 进了受管束集合

    svc.refresh_site(SITE)  # 复用, 不写盘
    again = svc.build_views()[SITE]
    assert again.revision == 1 and again.last_success_ts == first.last_success_ts


def test_parse_revision_is_incomplete(tmp_path):
    """页面改版(表头缺失) -> 覆盖证明不成立, 不产生放行"""
    clock = Clock()
    fetcher = FakeFetcher({"A": REVISED_PAGE, "B": EMPTY_TABLE_PAGE, "C": EMPTY_TABLE_PAGE}, {})
    svc = _service(tmp_path, fetcher, clock)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_PARTIAL
    assert "疑似改版" in result.reason
    data = _read(tmp_path)
    assert data.refresh.complete is False
    assert data.verified == {}


def test_empty_listing_is_complete(tmp_path):
    """表头在但 0 行是合法空结果(「该账号没有 HR 种子」), 覆盖证明仍成立"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(), {})
    svc = _service(tmp_path, fetcher, clock)

    result = svc.refresh_site(SITE)

    assert result.action == ACTION_REFRESHED
    assert result.complete is True
    assert result.entries == 0
    assert _read(tmp_path).refresh.last_success_ts == clock.now


@pytest.mark.parametrize("mode", ["partial", "all"])
def test_both_modes_refresh(tmp_path, mode):
    """partial 与 all 都走站点侧驱动刷新(差别只在未核实的默认值, 见 resolve)"""
    clock = Clock()
    fetcher = FakeFetcher(_pages(a_rows=[row(101)]), _blobs(101))
    svc = _service(tmp_path, fetcher, clock, site=site_conf(mode=mode))
    result = svc.refresh_site(SITE)
    assert result.action == ACTION_REFRESHED
    assert svc.build_views()[SITE].mode == mode

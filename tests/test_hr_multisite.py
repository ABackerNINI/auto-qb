"""test_hr_multisite 测试计划: 多站点(计划 §11 M4) —— 「接第二个站点」要付多少代价

M4 的结论必须是**配出来的**, 不是"文档里说可以": 本文件把「第二/第三个 NexusPHP 站点只改配置
就能用」与「站点之间严格隔离」钉成守阵 —— 站点分文件 / 每站点一把锁 / 每站点配额与熔断 /
各自的视图与索引, 全都不共用。

## 测试计划(每个测试函数一条)
- test_second_nexusphp_site_needs_config_only: 第二个 NexusPHP 站点**只改配置**就能用(同一 adapter
  工厂按站点构造, 各自的页面 URL / 下载路径 / 刷新周期互不影响)
- test_sites_do_not_share_quota_or_fuse: 站点 A 连续失败熔断, B 照常取数(配额账本与熔断都在各自站点文件里)
- test_sites_hold_independent_locks: A 持锁时 B 仍能刷新(锁粒度 = 站点; 拿不到锁只跳该站)
- test_same_infohash_keeps_independent_identity_per_site: 同一内容在两站身份独立(已取记录与索引不跨站)
- test_status_covers_every_site: 站点现状快照逐站点各一条(`--hr-status` 与 `/api/hr/status` 的共同层)
"""
from typing import Dict

from auto_qb.hr import ACTION_ERROR, ACTION_REFRESHED, HrRefreshService, build_adapter
from auto_qb.hr.fetcher import HrFetchError
from auto_qb.hr.status import build_site_statuses
from hr_helpers import Clock, FakeFetcher, global_conf, myhr_page, row, site_conf, torrent_blob

ALPHA = "alpha"
BETA = "beta"


def _conf(site: str, **overrides):
    """站点配置: 域名 / 周期 / 档位都由调用方给(测"只改配置"这件事本身)"""
    base = dict(hr_page_url=f"https://{site}.example.com/myhr.php", refresh_interval=6 * 3600.0)
    base.update(overrides)
    return site_conf(**base)


class _ByUrlFetcher:
    """按 **URL 前缀** 决定成功/失败的通道替身(FakeFetcher 只能按 scope 分级, 两站同 scope 时分不开)"""
    def __init__(self, pages: Dict[str, str], blobs: Dict[int, bytes], fail_prefix: str = "") -> None:
        self.pages = dict(pages)
        self.blobs = dict(blobs)
        self.fail_prefix = fail_prefix
        self.text_calls: list = []
        self.byte_calls: list = []

    def get_text(self, url: str) -> str:
        self.text_calls.append(url)
        if self.fail_prefix and url.startswith(self.fail_prefix):
            raise HrFetchError(f"假通道: 该站点取数失败({url})")
        return self.pages[url]

    def get_bytes(self, url: str) -> bytes:
        self.byte_calls.append(url)
        tid = int(url.split("id=", 1)[1].split("&", 1)[0])
        return self.blobs[tid]


def _pages_for(site: str, tids, conf) -> Dict[str, str]:
    """按**站点自己的 adapter** 拼 URL —— 这样断言不依赖 URL 细节(改拼法不用改测试)"""
    adapter = build_adapter(site, conf)
    return {adapter.page_url(scope, 1): myhr_page([row(t) for t in tids]) for scope in adapter.scopes}


def _service(tmp_path, fetcher, clock, confs=None):
    confs = confs or {ALPHA: _conf(ALPHA), BETA: _conf(BETA)}
    return HrRefreshService(
        data_dir=str(tmp_path),
        global_conf=global_conf(),
        site_confs=confs,
        fetcher=fetcher,
        owner="tester",
        now_fn=clock,
    )


def test_second_nexusphp_site_needs_config_only(tmp_path):
    """第二个 NexusPHP 站点**只改配置**就能用: 同一 adapter 工厂按站点构造, URL/周期互不影响

    这正是 M4「多站点」的实际形态 —— 绝大多数 PT 站是 NexusPHP 的 `myhr.php` 九列表, 接站点
    不需要写代码; 必须写代码的只有「有更便宜的来源(JSON 接口 / 逐种标记)」的少数站。
    """
    clock = Clock()
    conf_a, conf_b = _conf(ALPHA, refresh_interval=6 * 3600.0), _conf(BETA, refresh_interval=24 * 3600.0)
    pages = _pages_for(ALPHA, (101, ), conf_a)
    pages.update(_pages_for(BETA, (201, 202), conf_b))
    fetcher = FakeFetcher(
        pages, {
            101: torrent_blob("a101.bin"),
            201: torrent_blob("b201.bin"),
            202: torrent_blob("b202.bin")
        }
    )
    svc = _service(tmp_path, fetcher, clock, {ALPHA: conf_a, BETA: conf_b})

    results = {r.site: r for r in svc.refresh_all()}

    assert set(results) == {ALPHA, BETA} and all(r.action == ACTION_REFRESHED for r in results.values())
    assert results[ALPHA].entries == 1 and results[BETA].entries == 2, "各自的清单互不掺和"
    assert results[ALPHA].path.endswith(f"{ALPHA}.json") and results[BETA].path.endswith(f"{BETA}.json")
    # 各自的 adapter 只访问各自域名(站点隔离的第一道, 也是 URL 白名单的依据): 3 个档位各一次
    alpha_calls = [u for u in fetcher.text_calls if "alpha.example.com" in u]
    beta_calls = [u for u in fetcher.text_calls if "beta.example.com" in u]
    assert len(alpha_calls) == 3 and len(beta_calls) == 3, f"串域名了: {fetcher.text_calls}"


def test_sites_do_not_share_quota_or_fuse(tmp_path):
    """站点 A 连续失败熔断, B 照常取数: 配额账本与熔断都落在各自的站点文件里(不串味)"""
    clock = Clock()
    confs = {ALPHA: _conf(ALPHA), BETA: _conf(BETA)}
    pages = _pages_for(BETA, (201, ), confs[BETA])
    fetcher = _ByUrlFetcher(pages, {201: torrent_blob("b201.bin")}, fail_prefix="https://alpha.example.com/")
    svc = _service(tmp_path, fetcher, clock, confs)

    for _ in range(3):  # 连续失败达阈值
        assert svc.refresh_site(ALPHA).action == ACTION_ERROR
    clock.advance(60)
    beta = svc.refresh_site(BETA)

    assert beta.action == ACTION_REFRESHED, "A 熔断不该挡住 B"
    a_data = svc.store(ALPHA).read_unlocked()[0]
    b_data = svc.store(BETA).read_unlocked()[0]
    assert a_data.fuse.failures >= 3 and a_data.fuse.until_ts > clock.now
    assert b_data.fuse.failures == 0 and b_data.fuse.until_ts == 0.0
    # 配额按**请求**记(页面与 .torrent 都算): alpha 三轮各发一个请求就失败 = 3;
    # beta 一轮 A/B/C 三页 + 一次下载 = 4 —— 两侧各记各的, 没有互相叠加
    assert a_data.quota.hour_count == 3, f"alpha 配额: {a_data.quota}"
    assert b_data.quota.hour_count == 4, f"beta 配额: {b_data.quota}"


def test_sites_hold_independent_locks(tmp_path):
    """A 持锁时 B 仍能刷新(锁粒度 = 站点): 一个站点的抓取不会冻结其它站点"""
    clock = Clock()
    confs = {ALPHA: _conf(ALPHA), BETA: _conf(BETA)}
    pages = _pages_for(BETA, (201, ), confs[BETA])
    svc = _service(tmp_path, FakeFetcher(pages, {201: torrent_blob("b201.bin")}), clock, confs)

    with svc.store(ALPHA).hold():
        beta = svc.refresh_site(BETA)  # 同站点会 HrLockBusy; 跨站点不受影响

    assert beta.action == ACTION_REFRESHED


def test_same_infohash_keeps_independent_identity_per_site(tmp_path):
    """同一内容在两站身份独立: 已取记录 / 索引 / 视图键都不跨站(同一内容多站辅种各自算 HR)"""
    clock = Clock()
    confs = {ALPHA: _conf(ALPHA), BETA: _conf(BETA)}
    same = torrent_blob("same-content.bin")  # 两个站点下到的是同一个 .torrent
    pages = _pages_for(ALPHA, (101, ), confs[ALPHA])
    pages.update(_pages_for(BETA, (201, ), confs[BETA]))
    svc = _service(tmp_path, FakeFetcher(pages, {101: same, 201: same}), clock, confs)

    svc.refresh_all()

    a_data = svc.store(ALPHA).read_unlocked()[0]
    b_data = svc.store(BETA).read_unlocked()[0]
    assert set(a_data.downloaded) == {101} and set(b_data.downloaded) == {201}, "已取记录按站点各存各的"
    assert 201 not in a_data.index and 101 not in b_data.index, "索引不跨站"
    views = svc.build_views()
    a_view, b_view = views[ALPHA], views[BETA]
    assert a_view.site == ALPHA and b_view.site == BETA
    assert set(a_view.by_infohash) and set(a_view.by_infohash) == set(b_view.by_infohash), \
        "同一内容在两站各自都有键(身份独立但内容相同)"


def test_status_covers_every_site(tmp_path):
    """站点现状快照逐站点各一条(`--hr-status` 与 `/api/hr/status` 的共同层)"""
    clock = Clock()
    confs = {ALPHA: _conf(ALPHA), BETA: _conf(BETA)}
    pages = _pages_for(ALPHA, (101, ), confs[ALPHA])
    pages.update(_pages_for(BETA, (201, ), confs[BETA]))
    svc = _service(tmp_path, FakeFetcher(pages, {101: torrent_blob("a.bin"), 201: torrent_blob("b.bin")}), clock, confs)

    svc.refresh_all()
    rows = build_site_statuses(svc, clock.now)

    assert [s.site for s in rows] == [ALPHA, BETA], "两个站点都要有自己的一条(不是只报第一个)"
    assert all(s.complete and s.index_total == 1 and s.blocking == "" for s in rows)
    assert all(s.quota.hour > 0 for s in rows)

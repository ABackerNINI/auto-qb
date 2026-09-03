"""快照一致性回归测试: QbApi 门面写操作后同步 TorrentStore 快照

Bug 背景: _handle_delete_tags_if_has_no_torrents 用快照聚合 tag_usage() 判断标签使用数,
但同 tick 内其它任务(标签/分类/限速/启停)写标签只调客户端 API 不同步快照, 读到旧使用数
导致误删。方案: 新建 QbApi 门面统一封装所有 qB API 调用, 写操作后同步 store 快照字段
与全局缓存。

验证点:
- bug 场景: 同 tick 先 add_tag 再跑无种子标签清理, 已使用标签不被误删
- delete_tags 同步所有记录并失效全局标签缓存
- set_category / start / stop / 限速 / set_location / delete 同步 record 字段
- create_category 失效全局分类缓存
- RuleContext.api 在 manager 未绑定客户端时退化到 client(测试兼容)
"""
import os
import tempfile

from auto_qb.rules import RuleContext

from helpers import FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


def _make_client(mgr, *torrents):
    """构造 FakeClient, 灌入种子并绑定到 mgr(client setter 自动构建 api)"""
    client = FakeClient()
    for t in torrents:
        client.torrents[t.hash] = t
    mgr.client = client
    seed_store(mgr, list(torrents))
    return client


def test_delete_tags_if_has_no_torrents_not_deleted_after_same_tick_add():
    """Bug 回归(核心): 同 tick 内先 add_tag(经 api 同步快照), 无种子标签清理不应误删该标签"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", tags="C", state="stalledUP")
        client = _make_client(mgr, t1)
        client.tags = {"C", "D"}  # 全局标签定义

        # 同 tick 内其它任务给种子添加标签 D(经门面, 快照已同步)
        mgr.api.torrents_add_tags(tags=["D"], torrent_hashes="H1")
        assert "D" in mgr.store.get("H1").tags_set
        assert mgr.store.tag_usage().get("D") == 1

        # 无种子标签清理: D 已有种子使用 -> 不应删除
        mgr.config.delete_tags_if_has_no_torrents = ["D"]
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert ("delete_tags", {"D"}) not in client.calls, f"D 被误删: {client.calls}"

        # 对照: 真正无种子的标签 X 应被删除
        # (经门面给不存在的种子添加标签: 全局定义新增 X, 但快照无记录使用 -> 使用数为 0)
        mgr.api.torrents_add_tags(tags=["X"], torrent_hashes="NONEXISTENT")
        assert "X" in mgr.store.all_tags()
        assert mgr.store.tag_usage().get("X", 0) == 0
        mgr.config.delete_tags_if_has_no_torrents = ["X"]
        assert mgr._handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert ("delete_tags", {"X"}) in client.calls
        assert "X" not in mgr.store.all_tags()


def test_add_tags_syncs_snapshot_and_tag_usage():
    """add_tags 同步快照 tags_set, tag_usage 聚合立即可见"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", tags="", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_add_tags(tags=["New"], torrent_hashes="H1")
        assert mgr.store.get("H1").tags_set == {"New"}
        assert mgr.store.tag_usage()["New"] == 1
        # 标签写操作后全局标签缓存失效(再次拉取含新标签)
        assert "New" in mgr.store.all_tags()


def test_remove_tags_syncs_snapshot():
    """remove_tags 同步移除快照中的标签(保留其它标签)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", tags="X,Y", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_remove_tags(tags=["X"], torrent_hashes="H1")
        assert mgr.store.get("H1").tags_set == {"Y"}


def test_delete_tags_removes_from_all_records():
    """torrents_delete_tags(定义删除)同步从所有记录移除该标签并失效全局缓存"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", tags="X,Y", state="stalledUP")
        t2 = FakeTorrent(hash="H2", name="B", tags="X", state="stalledUP")
        client = _make_client(mgr, t1, t2)
        client.tags = {"X", "Y", "Z"}  # 全局标签定义
        mgr.api.torrents_delete_tags(tags=["X"])
        assert "X" not in mgr.store.get("H1").tags_set
        assert "Y" in mgr.store.get("H1").tags_set
        assert mgr.store.get("H2").tags_set == set()
        assert "X" not in mgr.store.all_tags()
        assert "Y" in mgr.store.all_tags()


def test_set_category_syncs_record():
    """set_category 同步快照 category 字段"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", category="", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_set_category(category="HR", torrent_hashes="H1")
        assert mgr.store.get("H1").category == "HR"
        # 清空分类同样同步
        mgr.api.torrents_set_category(category="", torrent_hashes="H1")
        assert mgr.store.get("H1").category == ""


def test_create_category_invalidates_categories_cache():
    """create_category 使全局分类缓存失效(下次读取重新拉取)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        client = _make_client(mgr, t1)
        counter = {"n": 0}
        orig = client.torrents_categories

        def counting():
            counter["n"] += 1
            return orig()

        client.torrents_categories = counting
        assert mgr.store.all_categories() == {}
        assert counter["n"] == 1
        mgr.api.torrents_create_category(name="HR")
        assert mgr.store.all_categories() == {}
        assert counter["n"] == 2  # 缓存已失效, 再次拉取


def test_start_stop_syncs_state():
    """start/stop 同步快照 state, is_paused 判定立即可用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_stop(torrent_hashes="H1")
        assert mgr.store.get("H1").state == "pausedUP"
        assert mgr.store.get("H1").is_stopped
        mgr.api.torrents_start(torrent_hashes="H1")
        assert mgr.store.get("H1").state == "stalledUP"
        assert not mgr.store.get("H1").is_stopped


def test_speed_limits_sync_record():
    """上传/下载限速同步快照 up_limit/dl_limit"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_set_upload_limit(torrent_hashes="H1", limit=1024 * 1000)
        assert mgr.store.get("H1").up_limit == 1024 * 1000
        mgr.api.torrents_set_download_limit(torrent_hashes="H1", limit=2048 * 1000)
        assert mgr.store.get("H1").dl_limit == 2048 * 1000


def test_set_location_syncs_save_path():
    """set_location 同步快照 save_path"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", save_path=r"R:\Old", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_set_location(torrent_hashes="H1", location=r"R:\New")
        assert mgr.store.get("H1").save_path == r"R:\New"


def test_torrents_delete_removes_from_snapshot():
    """torrents_delete 后快照立即移除该种子(其它种子保留)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        t2 = FakeTorrent(hash="H2", name="B", state="stalledUP")
        _make_client(mgr, t1, t2)
        mgr.api.torrents_delete(torrent_hashes=["H1"], delete_files=False)
        assert "H1" not in mgr.store
        assert "H2" in mgr.store


def test_read_ops_use_store():
    """读操作(快照内 hash)优先走 store 惰性缓存"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        client = _make_client(mgr, t1)
        client.tags = {"C"}
        # 快照内种子: trackers 走 store 记录缓存(与 client 返回值一致)
        assert mgr.api.torrents_trackers("H1") == client.torrents_trackers("H1")
        # 全局标签: 走 store 缓存(等价 client.torrents_tags)
        assert mgr.api.torrents_tags() == list(client.tags)
        assert mgr.api.torrents_categories() == {}


def test_ctx_api_fallback_without_manager_client():
    """RuleContext.api: manager 未绑定客户端时退化到 client(外部种子/测试兼容)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))  # 不设置 mgr.client
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert isinstance(ctx, RuleContext)
        assert ctx.api is client


def test_ctx_api_uses_manager_api_when_bound():
    """RuleContext.api: manager 绑定客户端后优先返回 manager.api 门面"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        client = _make_client(mgr, t1)
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert ctx.api is mgr.api

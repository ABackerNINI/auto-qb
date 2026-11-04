"""快照一致性回归测试: QbApi Facade写操作后同步 TorrentStore 快照

Bug 背景: _handle_delete_tags_if_has_no_torrents 用快照聚合 tag_usage() 判断标签使用数,
但同 tick 内其它任务(标签/分类/限速/启停)写标签只调客户端 API 不同步快照, 读到旧使用数
导致误删。方案: 新建 QbApi Facade统一封装所有 qB API 调用, 写操作后同步 store 快照字段
与全局缓存。

验证点:
- bug 场景: 同 tick 先 add_tag 再跑无种子标签清理, 已使用标签不被误删
- delete_tags 同步所有记录并失效全局标签缓存
- set_category / start / stop / 限速 / set_location / delete 同步 record 字段
- create_category 失效全局分类缓存
- RuleContext.api 恒为 manager.api(QbApi Facade); 未绑定客户端时 api.client 为 None

## 测试计划(每个测试函数一条)

- test_add_tags_syncs_snapshot_and_tag_usage
- test_create_category_invalidates_categories_cache
- test_ctx_api_not_fallback_without_manager_client
- test_ctx_api_uses_manager_api_when_bound
- test_delete_tags_if_has_no_torrents_not_deleted_after_same_tick_add
- test_delete_tags_removes_from_all_records
- test_qbapi_passthrough_methods_delegate
- test_qbapi_read_ops_fallback_on_cache_miss
- test_qbapi_to_list_normalization
- test_read_ops_use_store
- test_remove_tags_syncs_snapshot
- test_set_category_syncs_record
- test_set_location_waits_for_sync
- test_speed_limits_sync_record
- test_start_stop_syncs_state
- test_torrents_delete_removes_from_snapshot
- test_qbapi_delete_default_keeps_files_false: 守阵(W6 变异审计, 高危)—— delete 默认 delete_files=False 透传(跳检 delete+readd 依赖)
- test_qbapi_write_ops_wire_exact_kwargs: 守阵(W6, 中危)—— facade 写操作对 raw client 的调用参数逐位断言(接线族)
- test_qbapi_start_stop_note_own_write_store_side: 守阵(W6)—— start/stop 登记 own_writes(deferral 判据面)
- test_qbapi_delete_tags_store_side_removal: 守阵(W6)—— delete_tags 经 apply_tag_removal 摘除快照标签
- test_qbapi_read_fallback_wires_hash_to_client: 守阵(W6)—— store 未命中直连路径把 hash 传给 client
- test_qbapi_store_cache_hit_skips_repeat_client_call: 守阵(W6)—— 记录惰性缓存命中后不再直连 client
- test_qbapi_passthrough_positional_and_rid_default: 守阵(W6, 极低危)—— *args 透传与 sync_maindata rid 默认 0

覆盖率第三轮 T2b 补测(26-11-05):
- test_qbapi_tracker_invalidate_skips_unknown_hash: tracker 写后缓存失效, 未知/缺 hash 静默跳过(263->exit)
"""
import os
import tempfile
from unittest import mock

from auto_qb.core.qbapi import QbApi
from auto_qb.rules import RuleContext
from auto_qb.torrents import TorrentStore

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

        # 同 tick 内其它任务给种子添加标签 D(经Facade, 快照已同步)
        mgr.api.torrents_add_tags(tags=["D"], torrent_hashes="H1")
        assert "D" in mgr.store.get("H1").tags_set
        assert mgr.store.tag_usage().get("D") == 1

        # 无种子标签清理: D 已有种子使用 -> 不应删除
        mgr.config.delete_tags_if_has_no_torrents = ["D"]
        assert mgr.host.get("maintenance").handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
        assert ("delete_tags", {"D"}) not in client.calls, f"D 被误删: {client.calls}"

        # 对照: 真正无种子的标签 X 应被删除
        # (经Facade给不存在的种子添加标签: 全局定义新增 X, 但快照无记录使用 -> 使用数为 0)
        mgr.api.torrents_add_tags(tags=["X"], torrent_hashes="NONEXISTENT")
        assert "X" in mgr.store.all_tags()
        assert mgr.store.tag_usage().get("X", 0) == 0
        mgr.config.delete_tags_if_has_no_torrents = ["X"]
        assert mgr.host.get("maintenance").handle_delete_tags_if_has_no_torrents(None, dry_run=False) is True
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
        assert mgr.store.get("H1").state_enum.is_stopped
        mgr.api.torrents_start(torrent_hashes="H1")
        assert mgr.store.get("H1").state == "stalledUP"
        assert not mgr.store.get("H1").state_enum.is_stopped


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


def test_set_location_waits_for_sync():
    """set_location **不写快照**(等 qB 上报): save_path 是分组键输入, 而搬家是异步的

    26-10-21-2323 S2: 提前改写会让组归属在文件还没到位时就变(重归组/误扫描); 改后同 tick 读到旧值,
    一次同步应用后才落真值 —— 与「运行状态只等上报」同一条纪律。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", save_path=r"R:\Old", state="stalledUP")
        _make_client(mgr, t1)
        mgr.api.torrents_set_location(torrent_hashes="H1", location=r"R:\New")
        assert mgr.store.get("H1").save_path == r"R:\Old", "同 tick 不得改写快照(等上报)"
        mgr.store._apply({"H1": {"save_path": r"R:\New"}}, [], full=False)
        assert mgr.store.get("H1").save_path == r"R:\New", "同步应用后才落真值"


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


def test_ctx_api_not_fallback_without_manager_client():
    """RuleContext.api: manager.api(QbApi) 恒存在(未绑定客户端时不退化到 client)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))  # 不设置 mgr.client
        client = FakeClient()
        ctx = RuleContext(mgr, client, mgr.config, "HASH123", dry_run=False)
        assert isinstance(ctx, RuleContext)
        assert ctx.api is mgr.api  # manager.api 优先, 不退化
        assert ctx.api is not client
        assert ctx.api.client is None  # api 存在但尚未绑定原始客户端


def test_ctx_api_uses_manager_api_when_bound():
    """RuleContext.api: manager 绑定客户端后优先返回 manager.api Facade"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        t1 = FakeTorrent(hash="H1", name="A", state="stalledUP")
        client = _make_client(mgr, t1)
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert ctx.api is mgr.api


def test_qbapi_to_list_normalization():
    """_to_list: None -> [], 单个字符串 -> [str], 列表原样"""
    assert QbApi._to_list(None) == []
    assert QbApi._to_list("H1") == ["H1"]
    assert QbApi._to_list(["H1", "H2"]) == ["H1", "H2"]


def test_qbapi_passthrough_methods_delegate():
    """无快照变化的透传方法: 原样委托给 client"""
    client = mock.MagicMock()
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        api = QbApi(client, mgr.store)
        api.torrents_add(torrent_files="f.torrent")
        api.torrents_recheck(torrent_hashes="H1")
        api.torrents_reannounce(torrent_hashes="H1")
        api.torrents_info()
        api.torrents_piece_hashes("H1")
        api.torrents_export("H1")
        api.auth_log_in(username="u", password="p")
    client.torrents_add.assert_called_once_with(torrent_files="f.torrent")
    client.torrents_recheck.assert_called_once_with(torrent_hashes="H1")
    client.torrents_reannounce.assert_called_once_with(torrent_hashes="H1")
    client.torrents_info.assert_called_once()
    client.torrents_piece_hashes.assert_called_once_with("H1")
    client.torrents_export.assert_called_once_with("H1")
    client.auth_log_in.assert_called_once_with(username="u", password="p")


def test_qbapi_read_ops_fallback_on_cache_miss():
    """读操作兜底: store 快照缺该 hash 时 trackers/files 回退 client(命中则走记录缓存)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        t1 = FakeTorrent(hash="H1")
        t2 = FakeTorrent(hash="H2")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        mgr.client = client
        seed_store(mgr, [t2])  # 快照只有 H2(H1 仅存在于 client 端)
        # 快照缺 H1: trackers/files 回退 client
        assert mgr.api.torrents_trackers("H1") == client.torrents_trackers("H1")
        assert mgr.api.torrents_files("H1") == client.torrents_files("H1")
        # 快照命中 H2: files 走记录缓存
        assert mgr.api.torrents_files("H2") == t2.files(mgr.api.client)


# ---------- W6(R30) 变异审计守阵: qbapi.py facade -> raw client 接线族 ----------


def test_qbapi_delete_default_keeps_files_false():
    """守阵(变异审计 W6, 高危): torrents_delete 不传 delete_files 时默认 False 透传给 client

    ops_mod 跳检 delete+readd 依赖默认 False(调用点不传参) —— 默认翻 True 即跳检流程直接
    删盘(不可逆数据删除面)。delete_files 键整参丢失同样在此拦下(显式契约)。
    """
    client = mock.MagicMock()
    api = QbApi(client, mock.MagicMock())
    api.torrents_delete(torrent_hashes="H1")
    client.torrents_delete.assert_called_once_with(torrent_hashes="H1", delete_files=False)


def test_qbapi_write_ops_wire_exact_kwargs():
    """守阵(变异审计 W6, 中危): 写操作 facade 对 raw client 的调用参数逐位断言(接线族)

    池此前只断言 store 侧效果, client 接线参数(hashes/limit/category/name/location)全体
    无断言 —— 换 None/丢参即写意图被扭曲(qB 400 或全量作用域)。用 Mock client 一次钉死
    整族; store 侧效果由既有快照守阵覆盖, 两侧互补。
    """
    client = mock.MagicMock()
    api = QbApi(client, mock.MagicMock())
    api.torrents_add_tags(tags=["T"], torrent_hashes="H1")
    client.torrents_add_tags.assert_called_once_with(tags=["T"], torrent_hashes="H1")
    api.torrents_remove_tags(tags=["T"], torrent_hashes="H1")
    client.torrents_remove_tags.assert_called_once_with(tags=["T"], torrent_hashes="H1")
    api.torrents_create_category(name="HR")
    client.torrents_create_category.assert_called_once_with(name="HR")
    api.torrents_set_category(category="HR", torrent_hashes="H1")
    client.torrents_set_category.assert_called_once_with(category="HR", torrent_hashes="H1")
    api.torrents_set_upload_limit(torrent_hashes="H1", limit=1024)
    client.torrents_set_upload_limit.assert_called_once_with(torrent_hashes="H1", limit=1024)
    api.torrents_set_download_limit(torrent_hashes="H1", limit=2048)
    client.torrents_set_download_limit.assert_called_once_with(torrent_hashes="H1", limit=2048)
    api.torrents_set_location(torrent_hashes="H1", location=r"R:\New")
    client.torrents_set_location.assert_called_once_with(torrent_hashes="H1", location=r"R:\New")
    api.torrents_start(torrent_hashes="H1")
    client.torrents_start.assert_called_once_with(torrent_hashes="H1")
    api.torrents_stop(torrent_hashes="H1")
    client.torrents_stop.assert_called_once_with(torrent_hashes="H1")
    api.torrents_delete(torrent_hashes=["H1"], delete_files=False)
    client.torrents_delete.assert_called_once_with(torrent_hashes=["H1"], delete_files=False)


def test_qbapi_start_stop_note_own_write_store_side():
    """守阵(变异审计 W6, 中危): start/stop 后 store.own_writes 必须登记目标 hash

    own_writes 是 deferral 判据的来源(G4/G6 陈旧-放行窗口) —— note_own_write(None) 即
    意图登记丢失, 闸门失效。
    """
    store = TorrentStore()
    store.by_hash = {"H1": FakeTorrent(hash="H1", name="A", state="stalledUP")}
    api = QbApi(mock.MagicMock(), store)
    api.torrents_start(torrent_hashes="H1")
    assert "H1" in store.own_writes, "start 意图必须登记 own_writes"
    store.own_writes.clear()
    api.torrents_stop(torrent_hashes="H1")
    assert "H1" in store.own_writes, "stop 意图必须登记 own_writes"


def test_qbapi_delete_tags_store_side_removal():
    """守阵(变异审计 W6, 中危): delete_tags 经 store.apply_tag_removal 摘除快照标签

    用 Mock client 隔离替身的同名摘除副作用(FakeClient 会顺手改共享对象, 掩盖 store 侧
    登记丢失) —— apply_tag_removal(None/空表)即 tag_usage 陈旧 -> 清理误判面。
    """
    store = TorrentStore()
    r1 = FakeTorrent(hash="H1", name="A", tags="X,Y", state="stalledUP")
    r2 = FakeTorrent(hash="H2", name="B", tags="X", state="stalledUP")
    store.by_hash = {"H1": r1, "H2": r2}
    client = mock.MagicMock()
    api = QbApi(client, store)
    api.torrents_delete_tags(tags=["X"])
    client.torrents_delete_tags.assert_called_once_with(tags=["X"])
    assert r1.tags_set == {"Y"}, "标签定义删除必须从所有快照记录摘除"
    assert r2.tags_set == set()


def test_qbapi_read_fallback_wires_hash_to_client():
    """守阵(变异审计 W6, 中危): store 未命中直连路径必须把 hash 原样传给 client

    trackers/files 的 fallback 是第二条读路径(与 store 缓存路径口径一致) —— 传 None 即
    对 qB 错误请求(空/错数据)。
    """
    store = TorrentStore()
    client = mock.MagicMock()
    trackers_payload = [{"url": "https://hdchina.org/announce.php", "status": 0}]
    files_payload = [{"name": "a.mkv"}]
    client.torrents_trackers.return_value = trackers_payload
    client.torrents_files.return_value = files_payload
    api = QbApi(client, store)
    out = api.torrents_trackers("H1")
    client.torrents_trackers.assert_called_once_with("H1")
    assert len(out) == 1 and out[0]["status"] == 0, "直连路径结果原样回传(经 mask 不改字段集)"
    assert api.torrents_files("H1") == files_payload
    client.torrents_files.assert_called_once_with("H1")


def test_qbapi_store_cache_hit_skips_repeat_client_call():
    """守阵(变异审计 W6, 低危): 快照命中走记录惰性缓存, 重复读不再直连 client

    store.get 旁路(None/恒未命中)即每读一次打一次 qB(请求量面) —— 二次调用计数为红线。
    """
    store = TorrentStore()
    store.by_hash = {"H1": FakeTorrent(hash="H1", name="A", state="stalledUP")}
    client = mock.MagicMock()
    client.torrents_trackers.return_value = [{"url": "https://x.example/announce"}]
    client.torrents_files.return_value = [{"name": "f"}]
    api = QbApi(client, store)
    api.torrents_trackers("H1")
    api.torrents_trackers("H1")
    assert client.torrents_trackers.call_count == 1, "第二次读必须走记录惰性缓存"
    api.torrents_files("H1")
    api.torrents_files("H1")
    assert client.torrents_files.call_count == 1, "第二次读必须走记录惰性缓存"


def test_qbapi_passthrough_positional_and_rid_default():
    """守阵(变异审计 W6, 极低危): 透传契约 —— *args 位置实参原样透传; sync_maindata rid 默认 0"""
    client = mock.MagicMock()
    api = QbApi(client, mock.MagicMock())
    api.torrents_add("positional")
    client.torrents_add.assert_called_once_with("positional")
    api.torrents_info("H1")
    client.torrents_info.assert_called_once_with("H1")
    api.sync_maindata()
    client.sync_maindata.assert_called_once_with(rid=0)


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): tracker 缓存失效的未知 hash 面 ----------


def test_qbapi_tracker_invalidate_skips_unknown_hash():
    """(T2b)tracker 写后失效惰性缓存(263->exit): hash 不在快照库/未传 hash -> 静默跳过,
    写调用本身照常透传 —— 未知 hash 不炸"""
    client = mock.MagicMock()
    api = QbApi(client, TorrentStore())
    api.torrents_add_trackers(torrent_hash="NOPE", urls=["http://t/announce"])
    client.torrents_add_trackers.assert_called_once_with(torrent_hash="NOPE", urls=["http://t/announce"])
    api.torrents_remove_trackers(torrent_hash=None, urls=["http://t/announce"])
    client.torrents_remove_trackers.assert_called_once_with(torrent_hash=None, urls=["http://t/announce"])

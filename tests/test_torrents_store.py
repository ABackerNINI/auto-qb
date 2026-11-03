"""test_torrents_store 测试计划: 种子信息数据层(TorrentRecord/TorrentStore)自测(不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_store_refresh_first_round: 首轮全部视为新增, removed 为空
- test_store_refresh_diff: 次轮增删检测
- test_store_refresh_keeps_records: 已存在记录对象跨 tick 保留(惰性缓存存活)
- test_store_refresh_cleans_cache_on_remove: 删除种子的记录回收, 缓存清理- test_store_restore_torrent: restore_torrent 恢复删除前记录(对象身份+幂等)
- test_store_queries: get/__contains__/all/hashes/__len__
- test_store_trackers_lazy: 记录级 trackers_info/tracker_urls 惰性拉取+缓存
- test_store_files_lazy: 记录级 files 惰性拉取+缓存
- test_store_state_snapshot: update_state_snapshot 由 by_hash 派生 state_enum
- test_store_group_members: group_members/group_key(未归组 -> [自身]/None)
- test_store_group_has_downloading: group_has_downloading 组级活跃下载判定(上移单点: 有下载者/全暂停/不在库/幽灵成员/checkingDL 边缘态)
- test_store_all_tags: all_tags 惰性缓存 + invalidate_tags 失效
- test_store_all_categories: all_categories 惰性缓存 + invalidate_categories 失效
- test_store_tag_usage: 从快照聚合标签使用情况
- test_store_unbound_client: 未绑定 client 时惰性拉取报错
- test_store_view_changed_only_for_view_fields: 仅视图字段/成员变化置脏, 其它字段不置脏(downloaded 已进平铺视图)
- test_store_view_changed_consume: consume_view_changed 读取即复位
- test_store_update_fields_marks_view_changed: state/save_path 写操作置脏, 标签不置脏
- test_store_seeding_time_quantized_no_repaint: 做种时长秒级递增不每轮置脏, 跨分钟才置脏
- test_store_attaches_hr_link: 注入的判定桥挂到新记录上(未注入时不引入 HR 依赖)
- test_store_extension_fields_dirty_view_and_quantum: 视图纪律(缓存≠展示): 扩展字段已进平铺视图置脏; eta 分钟量化; 非展示字段不置脏
- test_store_refresh_skips_hashless_entries: refresh 跳过无 hash 的条目(不以 None 为主键)
- test_store_field_snapshots_lifecycle: update_field_snapshots 生命周期(空监听清基线 / 恢复监听清残影落新基线)
- test_store_register_field_changes_self_caused_confirmed: 自写确认(上报值与期望一致 -> 按自写消费, 不进事件候选)
- test_store_update_fields_idempotent_writes_not_registered: 幂等写(已有标签再加/删不存在标签/同值分类)不登记自写
- test_store_apply_tag_removal: torrents_delete_tags 全库移除(空表直返 / 命中移除并置脏视图与所在组)
- test_store_remove_torrent_pending_semantics: remove_torrent 已知 hash 登记 removed / 未知 hash 无操作
- test_store_reset_runtime_marks_view_changed: reset 仍置 view_changed(索引保留不改变重建判定)
- test_store_reset_runtime_keeps_group_index: reset_runtime 不清 groups/group_sizes/member_to_key(D1=B)
- test_store_reset_runtime_no_regroup_cost: reset 不触发 O(N) 重归组(不拉文件表/不标脏组)
- test_store_view_changed_on_membership
"""

from dataclasses import MISSING, fields as dc_fields

import pytest

from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, view_dirty, view_field_value

from auto_qb.torrents.compat import _SNAPSHOT_FIELDS

from auto_qb.torrents.view import _VIEW_EXCLUDED_FIELDS

from helpers import FakeClient, FakeTorrent

from torrents_support import (
    _EXAMPLE_TORRENT_INFO,
    _StubLink,
    _client,
    _count_trackers,
)


def test_store_refresh_first_round():
    store = TorrentStore()
    added, removed = store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    assert sorted(added) == ["H1", "H2"]
    assert removed == []
    assert sorted(store.hashes()) == ["H1", "H2"]


def test_store_attaches_hr_link():
    """store 注入的判定桥要挂到记录上; 未注入时纯数据层可用(不引入 HR 依赖)"""
    store = TorrentStore()
    link = _StubLink(None)
    store.hr_link = link
    store.refresh([FakeTorrent(hash="H1")])
    assert store.get("H1").hr_link is link
    plain = TorrentStore()
    plain.refresh([FakeTorrent(hash="H2")])
    assert plain.get("H2").hr_link is None


def test_store_restore_torrent():
    """restore_torrent: 记录放回 by_hash(对象身份保留) + 撤销待报删除; 幂等"""
    store = TorrentStore()
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    store.by_hash["H1"] = rec
    store.remove_torrent("H1")  # 模拟跳检删除: by_hash 移除, 待报删除登记
    assert store._pending_removed == {"H1"}
    store.restore_torrent(rec)
    assert store.get("H1") is rec, "记录对象身份应保留(tracker_conf/惰性缓存不丢)"
    assert store._pending_removed == set(), "重加后不应再被误报为已删除"
    store.restore_torrent(rec)  # 幂等: 重复调用无副作用
    assert store.get("H1") is rec
    assert store._pending_removed == set()


def test_store_refresh_diff():
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    added, removed = store.refresh([FakeTorrent(hash="H2"), FakeTorrent(hash="H3")])
    assert added == ["H3"]
    assert removed == ["H1"]


def test_store_refresh_keeps_records():
    client = _client()
    store = TorrentStore(client)
    store.refresh([FakeTorrent(hash="H1")])
    store.get("H1").files(client)  # 触发惰性拉取
    calls = client.files_calls
    store.refresh([FakeTorrent(hash="H1", name="Updated")])
    assert store.get("H1").name == "Updated"
    store.get("H1").files(client)
    assert client.files_calls == calls  # 记录对象保留, 缓存跨 tick 存活


def test_store_refresh_cleans_cache_on_remove():
    client = _client()
    store = TorrentStore(client)
    store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    store.get("H1").files(client)
    store.refresh([FakeTorrent(hash="H2")])
    assert "H1" not in store
    store.get("H2").files(client)  # 现有记录正常
    assert client.files_calls == 2  # H1 的缓存随记录回收


def test_store_queries():
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    assert store.get("H1").hash == "H1"
    assert store.get("NOPE") is None
    assert "H1" in store
    assert "NOPE" not in store
    assert len(store) == 2
    assert sorted(store.hashes()) == ["H1", "H2"]
    assert {r.hash for r in store.all()} == {"H1", "H2"}


def test_store_trackers_lazy():
    client = _client()
    counter = _count_trackers(client)
    store = TorrentStore(client)
    store.refresh([FakeTorrent(hash="H1")])
    assert store.get("H1").trackers_info(client) == [{"url": "https://tracker.hhanclub.net/announce.php"}]
    assert store.get("H1").tracker_urls(client) == ["https://tracker.hhanclub.net/announce.php"]
    assert counter["n"] == 1  # 记录级缓存: 只拉一次
    store.get("H1").tracker_urls(client)
    assert counter["n"] == 1


def test_store_files_lazy():
    files = [{"name": "a.mkv", "size": 100}, {"name": "b.mkv", "size": 200}]
    client = _client(files=files)
    store = TorrentStore(client)
    store.refresh([FakeTorrent(hash="H1")])
    assert store.get("H1").files(client) == files
    assert client.files_calls == 1  # 记录级缓存: 只拉一次
    store.get("H1").files(client)
    assert client.files_calls == 1


def test_store_state_snapshot():
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", state="stalledUP"), FakeTorrent(hash="H2", state="pausedUP")])
    store.update_state_snapshot()
    assert store.state_snapshot["H1"].is_uploading
    assert store.state_snapshot["H2"] == "pausedUP"  # TorrentState 是 str 子类枚举


def test_store_group_members():
    store = TorrentStore()
    key = ("R:\\Downloads", ("a.mkv", ))
    store.groups[key] = ["H1", "H2"]
    store.member_to_key["H1"] = key
    store.member_to_key["H2"] = key
    assert store.group_members("H1") == ["H1", "H2"]
    assert store.group_key("H1") == key
    assert store.group_members("H3") == ["H3"]  # 未归组 -> 单种子
    assert store.group_key("H3") is None


def test_store_group_has_downloading():
    """group_has_downloading: 组级活跃下载判定(谓词上移自 GroupingModule._group_has_downloading 单点, plan 26-10-05-0314 T9)

    组内有下载中成员 -> True(内部经 group_members 取全组, 任一成员入口同判); 全暂停/不在库 -> False;
    幽灵成员(组表有快照无)跳过; checkingDL(强制校验)边缘态不算活跃下载(口径锁)。
    """
    store = TorrentStore()
    key = ("R:\\Downloads", ("a.mkv", ))
    store.by_hash["H1"] = FakeTorrent(hash="H1", state="stalledDL")
    store.by_hash["H2"] = FakeTorrent(hash="H2", state="pausedUP")
    store.groups[key] = ["H1", "H2"]
    store.member_to_key["H1"] = key
    store.member_to_key["H2"] = key
    assert store.group_has_downloading("H1") is True  # 组内有下载中成员
    assert store.group_has_downloading("H2") is True  # 同组任一成员入口同判
    assert store.group_has_downloading("H3") is False  # 不在库(未归组 -> [自身], 自身不在 by_hash)
    store.groups[key].append("GHOST")
    assert store.group_has_downloading("H1") is True  # 幽灵成员跳过不崩溃
    store.by_hash["H1"].state = "pausedDL"
    assert store.group_has_downloading("H1") is False  # 全暂停(组内无活跃下载)
    store.by_hash["H1"].state = "checkingDL"
    assert store.group_has_downloading("H1") is False  # 强制校验不算活跃下载(边缘态口径)


def test_store_all_tags():
    client = _client()
    client.tags = {"a", "b"}
    n = {"count": 0}
    orig = client.torrents_tags

    def counting():
        n["count"] += 1
        return orig()

    client.torrents_tags = counting
    store = TorrentStore(client)
    assert store.all_tags() == {"a", "b"}
    assert n["count"] == 1  # 惰性缓存
    store.all_tags()
    assert n["count"] == 1
    client.tags.add("c")  # 外部变更
    store.invalidate_tags()
    assert store.all_tags() == {"a", "b", "c"}
    assert n["count"] == 2


def test_store_all_categories():
    client = _client()
    cats = {"a": {}}
    n = {"count": 0}

    def counting():
        n["count"] += 1
        return dict(cats)

    client.torrents_categories = counting  # FakeClient 的 categories 恒返回 {}, 用闭包可控
    store = TorrentStore(client)
    assert store.all_categories() == {"a": {}}
    assert n["count"] == 1
    store.all_categories()
    assert n["count"] == 1
    cats["b"] = {}
    store.invalidate_categories()
    assert set(store.all_categories()) == {"a", "b"}
    assert n["count"] == 2


def test_store_tag_usage():
    store = TorrentStore()
    store.refresh(
        [
            FakeTorrent(hash="H1", tags="a,b"),
            FakeTorrent(hash="H2", tags="b,c"),
            FakeTorrent(hash="H3", tags=""),
        ]
    )
    assert store.tag_usage() == {"a": 1, "b": 2, "c": 1}


def test_store_unbound_client():
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1")])
    # 记录级惰性拉取未绑定 client 报错
    rec = store.get("H1")
    try:
        rec.files(None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("记录级 files 未绑定 client 时应报错")
    # 全局标签/分类缓存未绑定 client 报错
    try:
        store.all_tags()
    except RuntimeError:
        pass
    else:
        raise AssertionError("all_tags 未绑定 client 时应报错")
    try:
        store.all_categories()
    except RuntimeError:
        pass
    else:
        raise AssertionError("all_categories 未绑定 client 时应报错")


def test_store_view_changed_only_for_view_fields():
    """仅视图相关字段变化置脏; 非视图字段(如 ratio_limit)变化不置脏

    downloaded 已进种子平铺视图(SEED_ITEM), 变化会置脏 —— 非视图字段改用
    ratio_limit(re-add 限速策略, 不在 Web 视图展示)作反例。
    """
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=0, downloaded=0)])
    assert store.consume_view_changed() is True  # 首轮(新增)
    store.refresh([FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=0, downloaded=0)])
    assert store.consume_view_changed() is False  # 完全无变化
    store.refresh([FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=0, downloaded=123)])
    assert store.consume_view_changed() is True  # downloaded 在平铺视图中(SEED_ITEM)
    store.refresh([FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=9, downloaded=123, ratio_limit=1.5)])
    assert store.consume_view_changed() is True  # upspeed 在视图中
    store.refresh([FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=9, downloaded=123, ratio_limit=-2.0)])
    assert store.consume_view_changed() is False  # ratio_limit 不在视图中(非展示字段)
    store.refresh([FakeTorrent(hash="H1", name="T1", state="pausedUP", upspeed=9, downloaded=123, ratio_limit=-2.0)])
    assert store.consume_view_changed() is True  # state 在视图中
    store.refresh(
        [FakeTorrent(hash="H1", name="T1", state="pausedUP", upspeed=9, downloaded=123, save_path=r"R:\Elsewhere")]
    )
    assert store.consume_view_changed() is True  # save_path 决定分组键


def test_store_view_changed_on_membership():
    """成员增删置脏(视图的组与成员集合随之变化)"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    store.consume_view_changed()
    store.refresh([FakeTorrent(hash="H1")])  # 删除 H2
    assert store.consume_view_changed() is True
    store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H3")])  # 新增 H3
    assert store.consume_view_changed() is True


def test_store_view_changed_consume():
    """consume_view_changed: 读取即复位(主循环每 tick 消费一次)"""
    store = TorrentStore()
    assert store.view_changed is True  # 初值(视图尚未建立)
    assert store.consume_view_changed() is True
    assert store.view_changed is False
    assert store.consume_view_changed() is False


def test_store_update_fields_marks_view_changed():
    """save_path/tags/category 写操作置脏(均为视图展示字段); 限速不置脏

    !A 系 26-10-13-0540 S1 起 `state` 不再是写方法形参(合成回写删除, 视图脏由同步 delta 的
    `_VIEW_FIELD_SET` 通路驱动), 故本用例的字段面收敛为 save_path/tags/category。
    """
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", state="stalledUP")])
    store.consume_view_changed()
    store.update_torrent_fields("H1", up_limit=1024)
    assert store.consume_view_changed() is False
    store.update_torrent_fields("H1", tags_add=["x"])
    assert store.consume_view_changed() is True  # 组级共同标签列
    store.update_torrent_fields("H1", category="cs")
    assert store.consume_view_changed() is True  # 组级共同分类列
    store.update_torrent_fields("H1", save_path=r"R:\Other")
    assert store.consume_view_changed() is True
    store.update_torrent_fields("H1", dl_limit=2048)
    assert store.consume_view_changed() is False  # 限速不参与视图


def test_store_reset_runtime_marks_view_changed():
    """热重载 L2 reset_runtime: 清缓存/tracker_conf 置空 -> 视图必须重建(分组索引按 D1=B 保留)"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1")])
    store.consume_view_changed()
    store.reset_runtime()
    assert store.consume_view_changed() is True


def test_store_reset_runtime_keeps_group_index():
    """reset_runtime **不清**分组索引(计划 26-11-03-2223 D1=B, issue 26-11-03-2206)

    分组键的三个输入(save_path/种子文件表/物理解析)不在 L2 重建判据的变更面, 重建后记录
    与文件表缓存仍在, 重算只能得到同一批键 —— 保留索引免 O(N) 重算。快照/缓存仍按原口径清。
    """
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", save_path=r"R:\D"), FakeTorrent(hash="H2", save_path=r"R:\D")])
    key = (r"R:\D", )
    groups_ref, member_ref, sizes_ref = store.groups, store.member_to_key, store.group_sizes
    store.groups[key] = ["H1", "H2"]
    store.member_to_key["H1"] = key
    store.member_to_key["H2"] = key
    store.group_sizes[key] = {"H1": {"movie.mkv": 100}, "H2": {"movie.mkv": 100}}
    store.group_key_migrations.add(key)
    store.transitional_missing_skips[key] = 1
    store.state_snapshot["H1"] = "stalledUP"
    for rec in store.by_hash.values():
        rec.tracker_conf = object()
    store.consume_view_changed()
    store.reset_runtime()
    assert store.groups is groups_ref and store.member_to_key is member_ref and store.group_sizes is sizes_ref, (
        "分组索引对象不得被替换/清空"
    )
    assert store.groups[key] == ["H1", "H2"] and store.member_to_key == {"H1": key, "H2": key}
    assert store.group_sizes[key] == {"H1": {"movie.mkv": 100}, "H2": {"movie.mkv": 100}}
    assert store.transitional_missing_skips == {} and store.state_snapshot == {}, "软信号/状态快照仍归零(重启口径)"
    assert all(rec.tracker_conf is None for rec in store.by_hash.values()), "conf 置空待全量轮重匹配"
    assert store.consume_view_changed() is True


def test_store_reset_runtime_no_regroup_cost():
    """reset_runtime 本身不触发 O(N) 重归组: 不增文件取证、不标脏组、索引原引用保留

    重算分组键需要逐种子拉文件表(grouping_mod._assign_new_torrent); reset 是纯运行态重置
    (黄金法则 1 幂等), 重归组只能在 refresh 管线发生。计数以 FakeClient.torrents_files 为准。
    """
    client = FakeClient()
    store = TorrentStore(client)
    store.refresh([FakeTorrent(hash="H1", save_path=r"R:\D"), FakeTorrent(hash="H2", save_path=r"R:\D")])
    for h in ("H1", "H2"):
        store.get(h).files(client)  # 灌满记录级文件表缓存(重建后仍可用)
    key = (r"R:\D", )
    store.groups[key] = ["H1", "H2"]
    store.member_to_key["H1"] = key
    store.member_to_key["H2"] = key
    store.group_sizes[key] = {"H1": {"movie.mkv": 100}, "H2": {"movie.mkv": 100}}
    files_calls = client.files_calls
    dirty_groups = set(store.dirty_groups)
    store.reset_runtime()
    assert client.files_calls == files_calls, "reset 不得为分组键重新拉文件表(O(N) 取证)"
    assert store.dirty_groups == dirty_groups, "reset 不得把全部组标脏(否则下游全量展开)"
    assert store.groups[key] == ["H1", "H2"], "索引内容原样"
    assert store.group_sizes[key]["H1"] == {"movie.mkv": 100} and store.group_sizes[key]["H2"] == {"movie.mkv": 100}


def test_store_seeding_time_quantized_no_repaint():
    """做种时长秒级递增不每轮置脏(量化到分钟), 跨分钟边界才置脏 —— 惰性重建对做种库真正生效"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", state="stalledUP", seeding_time=36_000)])
    assert store.consume_view_changed() is True  # 首轮(新增)
    store.refresh([FakeTorrent(hash="H1", state="stalledUP", seeding_time=36_030)])
    assert store.consume_view_changed() is False, "同分钟内递增不应触发重建"
    store.refresh([FakeTorrent(hash="H1", state="stalledUP", seeding_time=36_059)])
    assert store.consume_view_changed() is False
    store.refresh([FakeTorrent(hash="H1", state="stalledUP", seeding_time=36_060)])
    assert store.consume_view_changed() is True, "跨分钟边界应触发重建"


def test_store_extension_fields_dirty_view_and_quantum():
    """视图纪律(缓存≠展示): 扩展字段已进种子平铺视图(SEED_ITEM) -> 变化置脏;
    高频字段(eta)按分钟量化抑制同桶跳动; 非展示字段(ratio_limit)仍不置脏"""
    store = TorrentStore()
    store.refresh([dict(_EXAMPLE_TORRENT_INFO, hash="H1")])
    store.consume_view_changed()  # 首轮(新增)置脏

    store.refresh([{"hash": "H1", "eta": 100, "num_seeds": 5, "popularity": 1.5}])
    assert store.consume_view_changed() is True, "扩展字段已进平铺视图, 变化应置脏"

    # eta 分钟量化: 同桶内跳动不置脏(高频字段纪律), 跨桶才触发重建
    store.refresh([{"hash": "H1", "eta": 119}])
    assert store.consume_view_changed() is False, "eta 同分钟桶内变化不触发重建"
    store.refresh([{"hash": "H1", "eta": 120}])
    assert store.consume_view_changed() is True

    # 非展示字段(re-add 限速策略)不置脏
    store.refresh([{"hash": "H1", "ratio_limit": 1.5}])
    assert store.consume_view_changed() is False

    # 视图字段照常置脏(同一轮混合变化时)
    store.refresh([{"hash": "H1", "state": "pausedUP"}])
    assert store.consume_view_changed() is True


def test_store_refresh_skips_hashless_entries():
    """refresh: 无 hash 的条目跳过(防御: 不以 None 为主键)"""
    store = TorrentStore()
    added, removed = store.refresh([FakeTorrent(hash="H1"), {"name": "no-hash"}])
    assert added == ["H1"]
    assert removed == []
    assert None not in store.by_hash
    assert set(store.by_hash) == {"H1"}


def test_store_field_snapshots_lifecycle():
    """update_field_snapshots 生命周期: 空监听清空基线(零持久化开销); 恢复监听后清掉已删种子残影、为现存种子落基线"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", tags="a")])
    store.set_watch_fields({"tags"})
    store.update_field_snapshots()
    assert store.field_snapshots["H1"] == {"tags": ["a"]}

    store.set_watch_fields(set())
    store.update_field_snapshots()
    assert store.field_snapshots == {}  # 监听集合为空: 基线全清

    store.refresh([FakeTorrent(hash="H1", tags="a")])
    store.field_snapshots["GHOST"] = {"tags": []}  # 已删种子残留(手动注入: 模拟删种后基线未清的历史状态)
    store.set_watch_fields({"tags"})
    store.update_field_snapshots()
    assert "GHOST" not in store.field_snapshots  # 已删种子基线一并清掉
    assert store.field_snapshots["H1"] == {"tags": ["a"]}


def test_store_register_field_changes_self_caused_confirmed():
    """自写确认: 上报值与登记期望一致 -> 按自写处理(不打外部重检标记、不进事件候选), 登记消费后不残留"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", tags="x, y")])
    store.set_watch_fields({"tags"})
    store.update_field_snapshots()
    store.self_caused_fields["H1"] = {"tags": ["x", "y"]}  # 自写登记(与 qB 将上报的值一致)

    net = store._register_field_changes("H1", store.get("H1"), frozenset({"tags"}))
    assert net == frozenset()  # 与自写期望一致 -> 无净变化
    assert "H1" not in store.self_caused_fields  # 登记已被报告消费
    assert "H1" not in store.external_tag_changes  # 自写不触发外部重检


def test_store_update_fields_idempotent_writes_not_registered():
    """幂等写不登记自写: 已有标签再加 / 删不存在的标签 / 同值分类 —— qB 不会报告变化, 登记必成残留"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", tags="a", category="c")])
    store.update_torrent_fields("H1", tags_add=["a"])  # merged == current
    store.update_torrent_fields("H1", tags_remove=["zz"])  # remain == current
    store.update_torrent_fields("H1", category="c")  # 同值写
    assert store.get("H1").tags == "a"
    assert store.get("H1").category == "c"
    assert "H1" not in store.self_caused_fields


def test_store_apply_tag_removal():
    """torrents_delete_tags 后全库移除已删除标签: 空表直接返回; 命中者移除并置脏视图与所在组"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", tags="a, gone"), FakeTorrent(hash="H2", tags="keep")])
    store.member_to_key["H1"] = (r"R:\Downloads", "k1")  # 直填成员索引(模拟归组结果): 断言组级脏标记
    store.consume_view_changed()

    store.apply_tag_removal([])  # 空表: 直接返回
    assert store.get("H1").tags == "a, gone"
    assert store.consume_view_changed() is False

    store.apply_tag_removal(["gone"])
    assert store.get("H1").tags == "a"
    assert store.get("H2").tags == "keep"  # 未命中的种子不动
    assert store.consume_view_changed() is True  # 组级共同标签列随标签定义删除而变化
    assert (r"R:\Downloads", "k1") in store.dirty_groups  # 组内冲突集合需重算


def test_store_remove_torrent_pending_semantics():
    """remove_torrent: 已知 hash 移出快照并登记待报 removed; 未知 hash 无操作"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1")])
    store.remove_torrent("NOPE")
    assert store._pending_removed == set()  # 未知 hash: 不误报 removed
    store.remove_torrent("H1")
    assert store._pending_removed == {"H1"}  # 已知 hash: 下轮增量据此报 removed
    assert store.get("H1") is None

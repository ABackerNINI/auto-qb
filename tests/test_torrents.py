"""test_torrents 测试计划: 种子信息数据层(TorrentRecord/TorrentStore)自测(不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_record_from_torrent: TorrentRecord.from_torrent 逐字段复制(TorrentDictionary 兼容)
- test_record_update_from: apply_delta 更新快照字段(hash 不变)
- test_record_update_keeps_lazy_cache: apply_delta 保留惰性缓存(文件列表不重复拉取)
- test_record_state_enum: state_enum 解析与 UNKNOWN 降级
- test_record_state_enum_flags: state_enum 语义判定(暂停/上传/下载)
- test_record_tags_set: tags 字符串 -> 预计算集合(逗号分隔去空白)
- test_store_refresh_first_round: 首轮全部视为新增, removed 为空
- test_store_refresh_diff: 次轮增删检测
- test_record_check_hr_on_real_record: 真实 TorrentRecord.check_hr_* 直测(防鸭子影子掩盖)
- test_store_refresh_keeps_records: 已存在记录对象跨 tick 保留(惰性缓存存活)
- test_store_refresh_cleans_cache_on_remove: 删除种子的记录回收, 缓存清理
- test_missing_torrent_fields: 缺失字段清单(全字段/缺字段/dict 形状)
- test_record_check_hr_on_real_record: 真实 TorrentRecord.check_hr_* 直测(防鸭子影子掩盖)
- test_store_restore_torrent: restore_torrent 恢复删除前记录(对象身份+幂等)
- test_store_queries: get/__contains__/all/hashes/__len__
- test_store_trackers_lazy: 记录级 trackers_info/tracker_urls 惰性拉取+缓存
- test_store_files_lazy: 记录级 files 惰性拉取+缓存
- test_store_state_snapshot: update_state_snapshot 由 by_hash 派生 state_enum
- test_store_group_members: group_members/group_key(未归组 -> [自身]/None)
- test_store_all_tags: all_tags 惰性缓存 + invalidate_tags 失效
- test_store_all_categories: all_categories 惰性缓存 + invalidate_categories 失效
- test_store_tag_usage: 从快照聚合标签使用情况
- test_store_unbound_client: 未绑定 client 时惰性拉取报错
- test_record_trackers_info_unbound: 记录级 trackers_info 未绑定 client 报错
- test_record_hr_boundaries: HR 判定边界(total_size=0 兜底/小种子完全下载即触发/无 hr 恒 False)
- test_store_view_changed_only_for_view_fields: 仅视图字段/成员变化置脏, 其它字段不置脏(downloaded 已进平铺视图)
- test_store_view_changed_consume: consume_view_changed 读取即复位
- test_store_update_fields_marks_view_changed: state/save_path 写操作置脏, 标签不置脏
- test_record_update_from_returns_changed: update_from 返回视图字段变化标记
- test_view_field_value_quantizes_seeding_time: 视图量化: seeding_time 按分钟取整, 其余原样
- test_store_seeding_time_quantized_no_repaint: 做种时长秒级递增不每轮置脏, 跨分钟才置脏
- test_record_seeding_time_quantized_update_from: update_from 双通道(Mapping/对象)的分钟量化
- test_snapshot_fields_match_record_slots: 守卫: _SNAPSHOT_FIELDS ↔ record 声明字段一一对应, REQUIRED ⊆ SNAPSHOT
- test_record_from_real_example_payload: 真机 TorrentDictionary 字段样例全量入库(不再丢弃字段)
- test_store_extension_fields_dirty_view_and_quantum: 视图纪律(缓存≠展示): 扩展字段已进平铺视图置脏; eta 分钟量化; 非展示字段不置脏
"""
from dataclasses import MISSING, fields as dc_fields

from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, view_field_value
from auto_qb.torrents.compat import _SNAPSHOT_FIELDS

from helpers import FakeClient, FakeTorrent


# 真机 TorrentDictionary 字段样例(qB 5.x, 2026-09-15 字段表定稿依据; 见 docs/record-full-fields-plan.html)
# 全部字段必须能进入 TorrentRecord 快照(声明字段进 slot, 未声明的落 _raw —— 两者都不允许丢弃)
_EXAMPLE_TORRENT_INFO = {
    "added_on": 1786920863,
    "amount_left": 5196343118,
    "auto_tmm": False,
    "availability": 0,
    "category": "",
    "comment": "https://kufirc.com/torrents.php?id=240006",
    "completed": 0,
    "completion_on": -1,
    "connections_count": 0,
    "connections_limit": 30,
    "content_path": "G:\\临时\\[OnlyFans] Marly (mementomarly) Siterip",
    "created_by": "uTorrent/2210",
    "creation_date": 1665579740,
    "dl_limit": 0,
    "dlspeed": 0,
    "download_path": "",
    "downloaded": 0,
    "downloaded_session": 0,
    "eta": 8640000,
    "f_l_piece_prio": False,
    "force_start": False,
    "has_metadata": True,
    "hash": "047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "inactive_seeding_time_limit": -2,
    "infohash_v1": "047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "infohash_v2": "",
    "last_activity": 1786920863,
    "magnet_uri": "magnet:?xt=urn:btih:047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "max_inactive_seeding_time": -1,
    "max_ratio": -1,
    "max_seeding_time": -1,
    "name": "[OnlyFans] Marly (mementomarly) Siterip",
    "num_complete": 0,
    "num_incomplete": 0,
    "num_leechs": 0,
    "num_seeds": 0,
    "piece_size": 4194304,
    "pieces_have": 0,
    "pieces_num": 1239,
    "popularity": 0,
    "priority": 3,
    "private": True,
    "progress": 0,
    "ratio": 0,
    "ratio_limit": -2,
    "root_path": "G:\\临时\\[OnlyFans] Marly (mementomarly) Siterip",
    "save_path": "G:\\临时",
    "seeding_time": 0,
    "seeding_time_limit": -2,
    "seen_complete": -1,
    "seq_dl": False,
    "share_limit_action": "Default",
    "size": 5196343118,
    "state": "stoppedDL",
    "super_seeding": False,
    "tags": "Kufirc",
    "time_active": 23098,
    "total_size": 5196343118,
    "total_wasted": 0,
    "tracker": "http://kufirc.com:7456/announce",
    "trackers_count": 1,
    "up_limit": 0,
    "uploaded": 0,
    "uploaded_session": 0,
    "upspeed": 0,
    "reannounce_in": 0,
}


def _client(files=None):
    client = FakeClient()
    if files is not None:
        client.files = files
    return client


def test_record_from_torrent():
    tor = FakeTorrent(hash="H1", name="Movie", state="stalledUP", tags="a, b", ratio=1.5)
    rec = TorrentRecord.from_torrent(tor)
    assert rec.hash == "H1"
    assert rec.name == "Movie"
    assert rec.state == "stalledUP"
    assert rec.tags == "a, b"
    assert rec.ratio == 1.5
    assert rec.save_path == tor.save_path
    assert rec.total_size == tor.total_size


def test_record_update_from():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", name="Old", state="stalledUP"))
    changed = rec.apply_delta(FakeTorrent(hash="H1", name="New", state="pausedUP", category="HR-DONE"))
    assert rec.name == "New"
    assert rec.state == "pausedUP"
    assert rec.category == "HR-DONE"
    assert rec.hash == "H1"  # hash 是主键, 不更新
    assert {"name", "state", "category"} <= changed


def test_record_update_keeps_lazy_cache():
    client = _client()
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    _ = rec.files(client)
    calls = client.files_calls
    rec.apply_delta(FakeTorrent(hash="H1", name="Updated"))
    assert rec.files(client) == client.files
    assert client.files_calls == calls  # 缓存保留, 不重复拉取


def test_record_state_enum():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP"))
    assert rec.state_enum is not None
    assert rec.state_enum.value == "stalledUP"
    bad = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="not-a-real-state"))
    assert bad.state_enum is not None
    assert bad.state_enum.name == "UNKNOWN"


def test_record_state_enum_flags():
    """state_enum 提供语义判定(上传/下载/暂停), TorrentRecord 桥接到枚举"""
    paused = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="pausedUP"))
    assert paused.state_enum.is_stopped
    assert not paused.state_enum.is_uploading
    uploading = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP"))
    assert uploading.state_enum.is_uploading
    downloading = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="downloading"))
    assert downloading.state_enum.is_downloading
    assert not downloading.state_enum.is_stopped


def test_record_tags_set():
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", tags=" a ,b,,c "))
    assert rec.tags_set == frozenset({"a", "b", "c"})
    empty = TorrentRecord.from_torrent(FakeTorrent(hash="H1", tags=""))
    assert empty.tags_set == frozenset()


def test_store_refresh_first_round():
    store = TorrentStore()
    added, removed = store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
    assert sorted(added) == ["H1", "H2"]
    assert removed == []
    assert sorted(store.hashes()) == ["H1", "H2"]


def test_record_check_hr_on_real_record():
    """真实 TorrentRecord.check_hr_* 直测: 回归 2026-09-06 BUG(迁入时误用 self.torrent,
    被FakeTorrent鸭子影子掩盖, 真实记录上 AttributeError)"""
    from auto_qb.config import HRRule, TrackerConfig

    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stoppedDL"))
    rec.tracker_conf = TrackerConfig(
        name="X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7)),
    )
    rec.downloaded = 70 * 1024**2
    rec.total_size = 100 * 1024**2
    # dlratio 0.7 >= 0.7: 触发; 做种 0 < 3D: 未满足
    assert rec.check_hr_condition() is True
    assert rec.check_hr_satisfied() is False
    # 做种时长达标 -> satisfied
    rec.seeding_time = 3 * 86400 + 12 * 3600
    assert rec.check_hr_satisfied() is True
    # dlsize 条件: downloaded 提至 100MiB >= 100MiB 触发
    rec.downloaded = 100 * 1024**2
    rec.tracker_conf.hr.condition = ("dlsize", 100 * 1024**2)
    assert rec.check_hr_condition() is True
    # 无 hr: False
    rec.tracker_conf.hr = None
    assert rec.check_hr_condition() is False


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


def _count_trackers(client):
    """包装 torrents_trackers 返回计数函数, FakeClient 不记录该调用"""
    state = {"n": 0}
    orig = client.torrents_trackers

    def counting(h):
        state["n"] += 1
        return orig(h)

    client.torrents_trackers = counting
    return state


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


def test_record_trackers_info_unbound():
    """记录级 trackers_info 未绑定 client 报错(store 传入 client=None 时)"""
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    try:
        rec.trackers_info(None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("记录级 trackers_info 未绑定 client 时应报错")


def test_record_tracker_name_unknown_without_conf():
    """tracker_name: tracker_conf=None -> 'Unknown'(旧实现回退 tor.client, 真实
    TorrentDictionary 无 client 属性导致生产 log_repr AttributeError)"""
    from types import SimpleNamespace

    rec = TorrentRecord.from_torrent(SimpleNamespace(hash="ABC123", name="T"))
    assert rec.tracker_conf is None
    assert rec.tracker_name == "Unknown"  # 不触碰 tor.client
    assert rec.log_repr == "'T' [Unknown] (ABC123)"


def test_record_hr_boundaries():
    """HR 判定边界: 兜底触发 = 下载量达到种子完整大小; downloaded=0 纯辅种/下载 1B/total_size=0/无 hr 均不触发"""
    from auto_qb.config import HRRule, TrackerConfig

    conf = TrackerConfig(
        name="X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlsize", 100 * 1024**2)),
    )
    # total_size=0 空种子: 辅种排除兜底, 不触发
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="E1", state="stalledUP", total_size=0, downloaded=0))
    rec.tracker_conf = conf
    assert rec.check_hr_condition() is False
    # 小种子(10MiB, 触发量 100MiB 永不可达)完整下载完: downloaded == total_size -> 触发
    rec2 = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2", state="stalledUP", total_size=10 * 1024**2, downloaded=10 * 1024**2)
    )
    rec2.tracker_conf = conf
    assert rec2.check_hr_condition() is True
    # downloaded=0 的纯辅种种子(添加时数据已完整, progress=1.0): 不欠 HR 债, 不触发
    rec_seed = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2b", state="stalledUP", total_size=100 * 1024**2, downloaded=0, progress=1.0)
    )
    rec_seed.tracker_conf = conf
    assert rec_seed.check_hr_condition() is False, "纯辅种种子不应触发 HR"
    # 仅下载 1B: 远未"完整下载完", 不触发
    rec_1b = TorrentRecord.from_torrent(
        FakeTorrent(hash="E2c", state="stalledUP", total_size=10 * 1024**2, downloaded=1, progress=1.0)
    )
    rec_1b.tracker_conf = conf
    assert rec_1b.check_hr_condition() is False, "下载 1B 不应触发 HR"
    # 无 hr 配置 -> 恒 False
    conf_nohr = TrackerConfig(
        name="Y", domains=["d.com"], tags=[], remove_tags=[], upload_speed_limit=0, download_speed_limit=0
    )
    rec3 = TorrentRecord.from_torrent(FakeTorrent(hash="E3", state="stalledUP"))
    rec3.tracker_conf = conf_nohr
    assert rec3.check_hr_condition() is False


def test_record_tracker_name_and_hr_fallback():
    """tracker_name 取配置名; check_hr_satisfied 无 hr/条件未达 -> False"""
    from auto_qb.config import HRRule, TrackerConfig

    conf = TrackerConfig(
        name="配置名X",
        domains=["d.com"],
        tags=[],
        remove_tags=[],
        upload_speed_limit=0,
        download_speed_limit=0,
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7)),
    )
    rec = TorrentRecord.from_torrent(
        FakeTorrent(hash="T1", state="stalledUP", total_size=100 * 1024**2, downloaded=10 * 1024**2)
    )
    rec.tracker_conf = conf
    assert rec.tracker_name == "配置名X"
    # 比例 0.1 < 0.7: 条件未达 -> satisfied False(L235 分支)
    assert rec.check_hr_satisfied() is False
    # 无 hr 配置: condition/satisfied 均 False(L232 分支)
    conf_nohr = TrackerConfig(
        name="Y", domains=["d.com"], tags=[], remove_tags=[], upload_speed_limit=0, download_speed_limit=0
    )
    rec.tracker_conf = conf_nohr
    assert rec.check_hr_condition() is False
    assert rec.check_hr_satisfied() is False


# ---------- Web 分组视图惰性重建: 视图变化标记 ----------


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
    """state/save_path/tags/category 写操作置脏(均为视图展示字段); 限速不置脏"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1", state="stalledUP")])
    store.consume_view_changed()
    store.update_torrent_fields("H1", up_limit=1024)
    assert store.consume_view_changed() is False
    store.update_torrent_fields("H1", tags_add=["x"])
    assert store.consume_view_changed() is True  # 组级共同标签列
    store.update_torrent_fields("H1", category="cs")
    assert store.consume_view_changed() is True  # 组级共同分类列
    store.update_torrent_fields("H1", state="pausedUP")
    assert store.consume_view_changed() is True
    store.update_torrent_fields("H1", save_path=r"R:\Other")
    assert store.consume_view_changed() is True


def test_store_reset_runtime_marks_view_changed():
    """热重载 L2 reset_runtime: 分组索引清空 -> 视图必须重建"""
    store = TorrentStore()
    store.refresh([FakeTorrent(hash="H1")])
    store.consume_view_changed()
    store.reset_runtime()
    assert store.consume_view_changed() is True


def test_record_update_from_returns_changed():
    """TorrentRecord.apply_delta 返回变化字段名集合(空集 = 无变化)"""
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP", upspeed=0))
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=0)) == frozenset()
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=7)) == {"upspeed"}
    # 非视图字段变化: 同样计入变化集(downloaded 不在 _VIEW_FIELDS, 但仍是真变化)
    # 注: FakeTorrent 的 amount_left 由 total_size-downloaded 推导, 改 downloaded 会同时带动它
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", upspeed=7,
                                       downloaded=999)) == {"downloaded", "amount_left"}


def test_view_field_value_quantizes_seeding_time():
    """视图字段量化: seeding_time 按分钟取整(向下); 未配置步长的字段原样返回

    前端本就只展示到分钟, 故秒级精度对 UI 无信息量 —— 量化后做种中的种子库不再每轮重建视图。
    """
    assert view_field_value("seeding_time", 0) == 0
    assert view_field_value("seeding_time", 59) == 0
    assert view_field_value("seeding_time", 60) == 60
    assert view_field_value("seeding_time", 119) == 60
    assert view_field_value("seeding_time", 3600) == 3600
    # 未配置步长: 精确返回(速度/上传量等实时字段必须逐字节/逐 Bps 变化)
    assert view_field_value("upspeed", 123) == 123
    assert view_field_value("uploaded", 4096) == 4096
    assert view_field_value("name", "x") == "x"


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


def test_record_seeding_time_quantized_update_from():
    """apply_delta 的分钟量化在两种通道(Mapping dict / 普通对象)下一致"""
    # 对象通道(测试替身)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1", state="stalledUP", seeding_time=600))
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", seeding_time=659)) == frozenset()
    assert rec.apply_delta(FakeTorrent(hash="H1", state="stalledUP", seeding_time=660)) == {"seeding_time"}
    # Mapping 通道(真机 TorrentDictionary / sync 响应走这条快路径)
    rec2 = TorrentRecord(hash="H2")
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 600}) == {"state", "seeding_time"}
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 640}) == frozenset()
    assert rec2.apply_delta({"hash": "H2", "state": "stalledUP", "seeding_time": 660}) == {"seeding_time"}


def test_snapshot_fields_match_record_slots():
    """守卫: _SNAPSHOT_FIELDS ↔ TorrentRecord 声明字段一一对应(防漏声明/拼写错位);
    REQUIRED ⊆ SNAPSHOT; 除主键 hash 外全部字段带默认值"""
    lazy_slots = {"_tags_set", "_state_enum", "_trackers_info", "_files", "_raw", "tracker_conf"}
    declared = {f.name for f in dc_fields(TorrentRecord)}
    snapshot = set(_SNAPSHOT_FIELDS)

    assert snapshot <= declared - lazy_slots, "字段表有未声明的 slot(或拼错)"
    assert declared - lazy_slots - snapshot == set(), "有声明了但不在字段表的 slot(字段表漏登记)"
    assert set(REQUIRED_TORRENT_FIELDS) <= snapshot
    no_default = [f.name for f in dc_fields(TorrentRecord) if f.default is MISSING and f.default_factory is MISSING]
    assert no_default == ["hash"]


def test_record_from_real_example_payload():
    """真机字段样例全量入库: 每个响应字段都进快照(声明字段), 不再丢弃; 哨兵值原样透传"""
    rec = TorrentRecord.from_torrent(_EXAMPLE_TORRENT_INFO, hash=_EXAMPLE_TORRENT_INFO["hash"])

    assert rec.hash == "047b3fad9834f0f2c00f9d4a9189068431e4a191"
    assert rec.eta == 8640000 and rec.completion_on == -1 and rec.seen_complete == -1  # 哨兵原样
    assert rec.private is True and rec.priority == 3 and rec.has_metadata is True
    assert rec.magnet_uri.startswith("magnet:?")
    assert rec.trackers_count == 1 and rec.connections_limit == 30 and rec.time_active == 23098
    assert rec.popularity == 0 and rec.reannounce_in == 0 and rec.total_wasted == 0
    assert rec.comment == "https://kufirc.com/torrents.php?id=240006"
    assert rec.ratio_limit == -2 and rec.seeding_time_limit == -2  # 升格字段来自样例而非默认
    assert rec._raw is None  # 样例字段全部已声明, 无未知字段落 _raw

    d = rec.to_dict()
    assert set(_EXAMPLE_TORRENT_INFO) <= set(d)  # 样例字段全量导出无丢失(记录现声明字段更多)


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

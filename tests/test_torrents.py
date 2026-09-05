"""test_torrents 测试计划: 种子信息数据层(TorrentRecord/TorrentStore)自测(不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_record_from_torrent: TorrentRecord.from_torrent 逐字段复制(TorrentDictionary 兼容)
- test_record_update_from: update_from in-place 更新快照字段
- test_record_update_keeps_lazy_cache: update_from 保留惰性缓存(文件列表不重复拉取)
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
- test_store_state_snapshot: update_state_snapshot 存 state_enum
- test_store_group_members: group_members/group_key(未归组 -> [自身]/None)
- test_store_all_tags: all_tags 惰性缓存 + invalidate_tags 失效
- test_store_all_categories: all_categories 惰性缓存 + invalidate_categories 失效
- test_store_tag_usage: 从快照聚合标签使用情况
- test_store_unbound_client: 未绑定 client 时惰性拉取报错
- test_record_trackers_info_unbound: 记录级 trackers_info 未绑定 client 报错
"""
from auto_qb.torrents import TorrentRecord, TorrentStore

from helpers import FakeClient, FakeTorrent


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
    rec.update_from(FakeTorrent(hash="H1", name="New", state="pausedUP", category="HR-DONE"))
    assert rec.name == "New"
    assert rec.state == "pausedUP"
    assert rec.category == "HR-DONE"
    assert rec.hash == "H1"  # hash 是主键, 不更新


def test_record_update_keeps_lazy_cache():
    client = _client()
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    _ = rec.files(client)
    calls = client.files_calls
    rec.update_from(FakeTorrent(hash="H1", name="Updated"))
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
        name="X", domains=["d.com"], tags=[], remove_tags=[],
        upload_speed_limit=0, download_speed_limit=0,
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
    """restore_torrent: 记录放回 by_hash(对象身份保留) + _known_hashes 补录; 幂等"""
    store = TorrentStore()
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="H1"))
    store.remove_torrent("H1")  # 模拟跳检删除: by_hash 移除, _known_hashes 含 H1
    store._known_hashes = {"H1"}
    store.restore_torrent(rec)
    assert store.get("H1") is rec, "记录对象身份应保留(tracker_conf/惰性缓存不丢)"
    assert "H1" in store._known_hashes
    store.restore_torrent(rec)  # 幂等: 重复调用无副作用
    assert store.get("H1") is rec


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
    t1 = FakeTorrent(hash="H1", state="stalledUP")
    t2 = FakeTorrent(hash="H2", state="pausedUP")
    store.update_state_snapshot([t1, t2])
    assert store.state_snapshot["H1"] is t1.state_enum
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
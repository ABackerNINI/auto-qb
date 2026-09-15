"""增量同步层测试(qB /api/v2/sync/maindata rid 语义 + TorrentRecord.apply_delta)

背景: 主循环原先每 tick 全量拉 torrents/info, 导致 qB 端反复序列化全部种子(CPU 上涨)。
改为走 /api/v2/sync/maindata 的 rid 增量: 只含**变化种子**的**变化字段**, 未变化种子
完全不出现在响应中, 删除种子单列 torrents_removed。

实现(单一数据所有者, 无中间投影视图):
  src/auto_qb/torrents.py  TorrentRecord(快照 slot + _raw 兜底) / TorrentStore.apply_sync
  src/auto_qb/qbapi.py     QbApi.sync_maindata 透传
  src/auto_qb/qbmanager.py _refresh_torrents / _validate_torrent_schema

测试清单:
- test_apply_delta_only_touches_patch_fields: 增量只处理 patch 内字段, 未提及字段保持
- test_apply_delta_returns_changed_fields: 返回变化字段名集合(非视图字段/视图字段/升格字段)
- test_apply_delta_quantizes_view_field: seeding_time 秒级递增不计入变化(量化)
- test_apply_delta_object_source: 非 Mapping 源(测试替身)按必需字段收集
- test_apply_delta_promoted_readd_fields_to_slots: 升格字段写 slot, _raw 保持空
- test_apply_delta_unknown_fields_to_raw: 未声明字段(qB 新版本)落 _raw, 属性兜底(前向兼容)
- test_record_required_fields_always_present: 必需字段全为 slot 恒存在; 未知属性仍抛 AttributeError
- test_apply_delta_extension_fields: 扩展字段(可选快照字段)更新生效并计入变化集
- test_record_defaults_are_qb_sentinels: 未提供字段保持 qB 哨兵默认值(老版本兼容)
- test_record_to_dict_merges_raw: to_dict 快照全字段 + _raw 合并
- test_record_state_enum_cached_and_invalidated: state_enum 有缓存, state 变化后失效
- test_store_apply_sync_full_update_first_round: 首轮全量 -> added 全部 + need_validate + 样本
- test_validate_sample_includes_hash_for_sync_response: sync 值内不含 hash -> 样本需补齐(真机 bug 回归)
- test_store_apply_sync_delta_only_changed: 增量轮只应用变化记录(其余对象身份保留)
- test_store_apply_sync_no_change_is_noop: 无变化轮零成本(不重建 by_hash)
- test_store_apply_sync_delta_add_and_remove: 增量新增/删除
- test_store_apply_sync_full_prunes_context_missing: rid 失效全量 -> 未出现者视为删除
- test_store_remove_then_restore_pending: remove_torrent 登记待报删除 / restore_torrent 撤销
- test_store_apply_sync_fallback_when_endpoint_unavailable: 无 sync 端点 -> 降级 + 告警一次
- test_store_apply_sync_unknown_error_resets_rid: 未知异常 rid 归零后上抛
- test_store_reset_sync: 清同步态并强制下轮全量
- test_store_update_state_snapshot_from_by_hash: 状态快照由 by_hash 派生(缓存枚举)
- test_manager_refresh_uses_incremental_sync: 主循环走 sync 且 store 正确
- test_manager_refresh_validate_gate: 仅全量轮做版本兼容校验
- test_manager_delta_state_change_detected: 状态变化可被 store 观测(state_changed/快照)
- test_manager_no_change_round_is_cheap: 无变化轮变化集为空
- test_manager_conflict_recheck_incremental: 冲突检查只重算脏组(登记->消费复位)
- test_manager_refresh_fallback_client: 旧版 qB 替身(无 sync 端点)整轮可用
- test_store_apply_sync_captures_server_state_full_and_delta: server_state 全量/增量都捕获(原子替换)
- test_store_apply_sync_server_state_missing_keeps_previous: 响应缺失 server_state 时保留旧值
- test_store_apply_sync_fallback_clears_server_state: 降级全量置 None(前端空态)
- test_apply_delta_quantizes_eta_time_active_last_activity: 新量化字段(分钟桶); 负数哨兵不量化
"""
import logging
import os
import tempfile
from io import StringIO
from types import SimpleNamespace

import pytest

from qbittorrentapi import TorrentState

from auto_qb.qbapi import QbApi
from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, missing_torrent_fields

from helpers import FakeClient, FakeTorrent, make_manager


class _NoSyncClient(FakeClient):
    """无 sync 端点的客户端替身(模拟旧版 qB): 调用 sync_maindata 抛 AttributeError"""
    def sync_maindata(self, rid=0, **kw):
        raise AttributeError("'Client' object has no attribute 'sync_maindata'")


def _api(client: FakeClient, store: TorrentStore = None) -> QbApi:
    """构造与给定 store 绑定的 Facade(默认新建 store)"""
    return QbApi(client, store if store is not None else TorrentStore())


def _full_fields(hash: str, **over) -> dict:
    """合成 qB 全量响应里的单条种子字段(全部必需字段)"""
    d = {f: 0 for f in REQUIRED_TORRENT_FIELDS}
    d.update(
        {
            "hash": hash,
            "name": "T",
            "save_path": r"R:\D",
            "state": "stalledUP",
            "tags": "",
            "category": "",
            "content_path": r"R:\D\T",
        }
    )
    d.update(over)
    return d


# ---------- TorrentRecord.apply_delta ----------


def test_apply_delta_only_touches_patch_fields():
    """增量: 只处理 patch 中的字段, 未提及字段原样保留(成本 ∝ patch 字段数)"""
    rec = TorrentRecord(hash="H1", name="Old", upspeed=1, seeding_time=100)
    changed = rec.apply_delta({"upspeed": 7})

    assert rec.upspeed == 7
    assert rec.name == "Old" and rec.seeding_time == 100  # 未提及 -> 不动
    assert changed == {"upspeed"}


def test_apply_delta_returns_changed_fields():
    """返回变化字段名集合: 非视图字段值不同即计入, 相同值不计入"""
    rec = TorrentRecord(hash="H1", state="stalledUP", downloaded=0, category="")
    assert rec.apply_delta({"state": "stalledUP", "downloaded": 0}) == frozenset()  # 值相同
    assert rec.apply_delta({"downloaded": 5, "category": "X"}) == {"downloaded", "category"}
    rec2 = TorrentRecord(hash="H2")
    # None 视为"未提供"(与历史 update_from 一致), hash 是主键
    assert rec2.apply_delta({"hash": "H2", "name": None, "upspeed": 3}) == {"upspeed"}
    # 升格字段(原 RE_ADD_FIELDS)现在是快照 slot: 变化计入变化集(非视图字段, 不影响视图)
    assert rec2.apply_delta({"ratio_limit": 1.5}) == {"ratio_limit"}
    assert rec2.ratio_limit == 1.5


def test_apply_delta_quantizes_view_field():
    """seeding_time 秒级递增不计入变化(按分钟量化), 跨分钟边界才计入"""
    rec = TorrentRecord(hash="H1", seeding_time=3600)
    assert rec.apply_delta({"seeding_time": 3619}) == frozenset()
    assert rec.seeding_time == 3619  # 值仍写入, 仅"变化集"不含它(避免视图每轮重建)
    assert rec.apply_delta({"seeding_time": 3660}) == {"seeding_time"}


def test_apply_delta_object_source():
    """非 Mapping 源(测试替身): 按 REQUIRED_TORRENT_FIELDS 收集属性"""
    rec = TorrentRecord(hash="H9")
    changed = rec.apply_delta(FakeTorrent(hash="H9", name="N9", state="pausedUP", upspeed=42))

    assert rec.name == "N9" and rec.upspeed == 42
    assert rec.state_enum is TorrentState("pausedUP")
    assert {"name", "upspeed", "state"} <= changed
    # FakeTorrent 的可选字段默认 None -> 视为"未提供"(与历史 update_from 一致), 不入 _raw
    # 升格后必需字段全部为 slot(带默认值), 鸭子对象恒通过版本校验
    assert missing_torrent_fields(rec) == []


def test_apply_delta_promoted_readd_fields_to_slots():
    """升格字段(原 RE_ADD_FIELDS)写 slot 而非 _raw; 无未知字段时 _raw 保持未初始化"""
    rec = TorrentRecord(hash="H1")
    rec.apply_delta(_full_fields("H1", seq_dl=True, ratio_limit=1.5, share_limit_action="Remove"))

    assert rec.seq_dl is True and rec.ratio_limit == 1.5
    assert rec.share_limit_action == "Remove"
    assert rec._raw is None  # 升格后必需字段不落 _raw
    assert missing_torrent_fields(rec) == []


def test_apply_delta_unknown_fields_to_raw():
    """未声明字段(qB 新版本前向兼容)落 _raw, 属性/hasattr 兜底 —— 数据不丢"""
    rec = TorrentRecord(hash="H1")
    rec.apply_delta({"hash": "H1", "some_future_field": 42, "another": "x"})

    assert rec._raw == {"some_future_field": 42, "another": "x"}
    assert rec.some_future_field == 42 and rec.another == "x"
    assert "some_future_field" not in missing_torrent_fields(rec)  # 不影响必需字段校验


def test_record_required_fields_always_present():
    """必需字段(快照+重加)全部为 slot: 恒存在(升格后不再 AttributeError), 版本校验恒通过;
    真正未知的属性仍抛 AttributeError(与 qB AttrDict 语义一致)"""
    rec = TorrentRecord(hash="H1")
    assert rec.ratio_limit == -2.0  # qB 哨兵: -2 = 使用全局默认
    assert rec.share_limit_action == "Default"
    assert missing_torrent_fields(rec) == []
    with pytest.raises(AttributeError):
        _ = rec.not_a_real_field


def test_apply_delta_extension_fields():
    """扩展字段(可选快照字段)增量更新生效, 变化计入变化集(非视图字段); None 仍视为未提供"""
    rec = TorrentRecord(hash="H1")
    changed = rec.apply_delta({"hash": "H1", "eta": 120, "num_seeds": 3, "magnet_uri": "magnet:?xt=urn:btih:X"})

    assert rec.eta == 120 and rec.num_seeds == 3 and rec.magnet_uri == "magnet:?xt=urn:btih:X"
    assert changed == {"eta", "num_seeds", "magnet_uri"}
    assert rec.apply_delta({"eta": None}) == frozenset()  # None = 未提供
    assert rec.eta == 120


def test_record_defaults_are_qb_sentinels():
    """未提供扩展字段时保持 qB 哨兵默认值(老版本 qB / 端点差异不炸)"""
    rec = TorrentRecord(hash="H1")
    assert rec.eta == 8640000  # 无 ETA
    assert rec.completion_on == -1 and rec.seen_complete == -1 and rec.last_activity == -1
    assert rec.max_ratio == -1.0 and rec.max_seeding_time == -1 and rec.max_inactive_seeding_time == -1
    assert rec.magnet_uri == "" and rec.private is False and rec.popularity == 0.0
    assert rec.tracker == "" and rec.trackers_count == 0 and rec.priority == 0


def test_record_to_dict_merges_raw():
    """to_dict: 快照全字段(含扩展) + _raw 未知字段合并; 惰性缓存槽/tracker_conf 不出现"""
    rec = TorrentRecord(hash="H1")
    rec.apply_delta(_full_fields("H1", eta=60, num_leechs=2, popularity=0.5))
    rec.apply_delta({"hash": "H1", "some_future_field": 1})

    d = rec.to_dict()
    assert d["hash"] == "H1" and d["eta"] == 60 and d["num_leechs"] == 2 and d["popularity"] == 0.5
    assert d["some_future_field"] == 1
    assert "_tags_set" not in d and "_raw" not in d and "tracker_conf" not in d
    assert set(REQUIRED_TORRENT_FIELDS) <= set(d)


def test_record_state_enum_cached_and_invalidated():
    """state_enum 有缓存(每轮多次读取零构造); state 变化后失效重算"""
    rec = TorrentRecord(hash="H1", state="stalledUP")
    first = rec.state_enum
    assert rec.state_enum is first  # 缓存命中
    rec.apply_delta({"state": "pausedUP"})
    assert rec.state_enum is TorrentState("pausedUP")
    assert rec.state_enum.is_stopped


# ---------- TorrentStore.apply_sync(rid 增量) ----------


def test_store_apply_sync_full_update_first_round():
    """首轮 rid=0 -> full_update: added 为全部, need_validate 真, 样本为原始字段映射"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
    store = TorrentStore(client)

    added, removed = store.apply_sync(_api(client, store))

    assert added == ["H1"] and removed == []
    assert store.rid == 1
    assert store.need_validate is True
    assert store.using_fallback is False
    assert isinstance(store.validate_sample, dict)  # qB 原始字段映射
    assert missing_torrent_fields(store.validate_sample) == []  # 全量响应字段齐全


def test_validate_sample_includes_hash_for_sync_response():
    """回归(真机 2026-09-13): qB sync 响应的 hash 是 torrents 字典**键**, 值内不含 hash

    校验样本需把键补回样本的 `hash` 字段, 否则 `missing_torrent_fields` 会报缺 'hash'
    → `_validate_torrent_schema` 抛 QbCompatError 导致程序启动即退出。
    这里用"值内确实没有 hash"的客户端替身(与真机一致)直接断言样本完整。
    """
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
    store = TorrentStore(client)

    store.apply_sync(_api(client, store))

    assert "hash" not in client.sync_maindata(rid=0)["torrents"]["H1"]  # 替身值内确实无 hash(真机形状)
    assert store.validate_sample["hash"] == "H1"  # 已补齐
    assert missing_torrent_fields(store.validate_sample) == []
    assert not store.by_hash["H1"]._raw  # 补齐不影响实际字段; 升格后 _raw 仅存未知字段(此处为空/未初始化)
    assert store.by_hash["H1"].hash == "H1"


def test_store_apply_sync_delta_only_changed():
    """增量轮只应用变化记录: 未变化记录对象身份保留, delta_fields 只有变化种子"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", upspeed=0)
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2", upspeed=0)
    store = TorrentStore(client)
    api = _api(client, store)
    store.apply_sync(api)
    rec1, rec2 = store.get("H1"), store.get("H2")

    client.torrents["H1"].upspeed = 7
    added, removed = store.apply_sync(api)

    assert (added, removed) == ([], [])
    assert store.get("H1") is rec1 and store.get("H2") is rec2  # 对象跨轮保留(惰性缓存存活)
    assert store.get("H1").upspeed == 7
    assert store.get("H2").name == "T2"  # 未变化字段来自基线
    assert set(store.delta_fields) == {"H1"}
    assert store.need_validate is False


def test_store_apply_sync_no_change_is_noop():
    """无变化轮零成本: 不重建 by_hash, 变化集为空(静止种子库每 tick 近乎免费)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)
    api = _api(client, store)
    store.apply_sync(api)
    by_hash_before = store.by_hash

    added, removed = store.apply_sync(api)

    assert (added, removed) == ([], [])
    assert store.by_hash is by_hash_before  # 未重建/未拷贝
    assert store.delta_fields == {} and store.state_changed == []


def test_store_apply_sync_delta_add_and_remove():
    """增量轮新增(基线缺失 -> 全量字段)与删除(torrents_removed)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)
    api = _api(client, store)
    store.apply_sync(api)

    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2", state="downloading")
    added, removed = store.apply_sync(api)
    assert added == ["H2"] and removed == []
    assert store.get("H2").name == "T2"

    del client.torrents["H1"]
    added, removed = store.apply_sync(api)
    assert added == [] and removed == ["H1"]
    assert store.get("H1") is None and store.get("H2") is not None


def test_store_apply_sync_full_prunes_context_missing():
    """rid 失效 -> full_update: 响应未出现的旧种子视为删除(幽灵条目不残留)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)
    api = _api(client, store)
    store.apply_sync(api)
    store.by_hash["GHOST"] = TorrentRecord(hash="GHOST")  # 模拟本地与服务端失同步

    store.rid = 999  # 与服务端 rid 不匹配 -> full_update
    added, removed = store.apply_sync(api)

    assert store.need_validate is True
    assert "GHOST" in removed and store.get("GHOST") is None
    assert set(store.by_hash) == {"H1"}
    assert added == []


def test_store_remove_then_restore_pending():
    """remove_torrent 登记待报删除(供分组清理/事件); restore_torrent 撤销登记(跳检重加)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)
    api = _api(client, store)
    store.apply_sync(api)

    rec = store.get("H1")
    store.remove_torrent("H1")
    assert store.get("H1") is None
    added, removed = store.apply_sync(api)  # qB 已无该种子 -> 双路去重后只报一次
    assert removed == ["H1"] and added == []

    store.restore_torrent(rec)  # 跳检重加: 撤销待报登记
    added, removed = store.apply_sync(api)
    assert added == [] and removed == []


def test_store_reset_sync():
    """reset_sync: 清同步态与变化集(重连/热重载后旧 rid 失效)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)
    store.apply_sync(_api(client, store))
    assert store.rid != 0

    store.reset_sync()
    assert store.rid == 0
    assert store.need_validate is True
    assert store.validate_sample is None
    assert store.delta_fields == {} and store.state_changed == [] and store.dirty_groups == set()


def test_store_update_state_snapshot_from_by_hash():
    """状态快照由 by_hash 派生(缓存枚举); 自有动作同步过的状态同样计入"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", state="stalledUP")
    store = TorrentStore(client)
    store.apply_sync(_api(client, store))

    store.update_state_snapshot()
    assert store.state_snapshot["H1"].is_uploading

    store.update_torrent_fields("H1", state="pausedUP")  # 模拟自有动作停种
    store.update_state_snapshot()
    assert store.state_snapshot["H1"].is_stopped


# ---------- 降级与异常 ----------


def _capture_logger(name: str):
    """把指定模块 logger 输出捕获到 StringIO(避免 root handler 干扰)"""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    lg = logging.getLogger(name)
    saved = (lg.level, list(lg.handlers), lg.propagate)
    lg.setLevel(logging.INFO)
    lg.handlers = [handler]
    lg.propagate = False
    return stream, lambda: (
        lg.setLevel(saved[0]), setattr(lg, "handlers", saved[1]), setattr(lg, "propagate", saved[2])
    )


def test_store_apply_sync_fallback_when_endpoint_unavailable():
    """sync 端点不可用(旧版 qB) -> 降级全量 torrents_info, 告警仅一次"""
    client = _NoSyncClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore(client)

    stream, restore = _capture_logger("auto_qb.torrents")
    try:
        added, removed = store.apply_sync(_api(client, store))
        assert added == ["H1"] and removed == []
        assert store.using_fallback is True
        assert store.need_validate is True
        assert store.rid == 0  # 降级路径保持 rid 归零
        # 样本保持旧语义: 首个非 dict 的原始种子对象(测试注入的 plain dict 不作样本)
        assert store.validate_sample is client.torrents["H1"]
        store.apply_sync(_api(client, store))  # 第二次降级不再重复告警
        assert stream.getvalue().count("降级") == 1
    finally:
        restore()


def test_store_apply_sync_unknown_error_resets_rid():
    """非"端点缺失"异常(网络等) -> rid 归零后原样上抛(由调用方兜底)"""
    class _BoomClient(FakeClient):
        def sync_maindata(self, rid=0, **kw):
            raise RuntimeError("network down")

    store = TorrentStore()
    store.rid = 42
    with pytest.raises(RuntimeError):
        store.apply_sync(_api(_BoomClient(), store))
    assert store.rid == 0  # 下轮强制全量


# ---------- QbManager 接线 ----------


def test_manager_refresh_uses_incremental_sync():
    """主循环刷新走 sync_maindata(增量); 第二轮无变化仍保持 store 正确"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")

        mgr._refresh_torrents()
        assert client.sync_calls == 1
        rec = mgr.store.get("H1")
        assert rec is not None and rec.name == "T1"

        mgr._refresh_torrents()
        assert client.sync_calls == 2
        assert mgr.store.get("H1") is rec  # 记录对象跨轮保留


def test_manager_refresh_validate_gate():
    """版本兼容校验仅在全量轮放行(增量轮响应只含变化字段, 校验会误报)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")

        mgr._refresh_torrents()
        assert mgr.store.need_validate is True  # 首轮全量
        assert mgr._schema_validated is True

        mgr._refresh_torrents()
        assert mgr.store.need_validate is False  # 增量轮不校验


def test_manager_delta_state_change_detected():
    """增量轮的状态变化可被 store 观测(state_changed 快照 + 状态快照更新)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        mgr._refresh_torrents()
        assert mgr.store.state_snapshot["H1"].is_uploading

        client.torrents["H1"].state = "pausedUP"  # 只改 state
        mgr._refresh_torrents()

        rec = mgr.store.get("H1")
        assert rec is not None and rec.state == "pausedUP"
        assert rec.state_enum.is_stopped
        assert [h for h, _ in mgr.store.state_changed] == ["H1"]  # 供分组/事件分派按变化集筛选
        assert mgr.store.state_snapshot["H1"].is_stopped


def test_manager_no_change_round_is_cheap():
    """无变化轮: 变化集为空(下游按变化集驱动的扫描全部早退)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        mgr._refresh_torrents()

        mgr._refresh_torrents()
        assert mgr.store.delta_fields == {}
        assert mgr.store.state_changed == []


def test_manager_conflict_recheck_incremental():
    """冲突检查只重算脏组: 无变化轮不登记(不扫描), 相关变化轮登记并在检查时消费复位"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.grouping.enabled = True
        client = FakeClient()
        mgr.client = client
        client.files_map["H1"] = [SimpleNamespace(name="a.mkv", size=100)]
        client.torrents["H1"] = FakeTorrent(hash="H1", state="stalledUP", save_path=r"R:\D")
        mgr._refresh_torrents()
        assert mgr.store.member_to_key["H1"] is not None  # 已归组

        mgr._refresh_torrents()  # 无变化轮: _check_download_conflicts 早退并清空
        assert mgr.store.dirty_groups == set()

        client.torrents["H1"].state = "downloading"  # 冲突相关字段变化
        mgr._refresh_torrents()
        assert mgr.store.dirty_groups == set()  # 已在检查时取出并复位


def test_manager_refresh_fallback_client():
    """无 sync 端点的客户端替身: 主循环整轮仍可用(降级全量)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = _NoSyncClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")

        mgr._refresh_torrents()
        assert mgr.store.using_fallback is True
        assert mgr.store.get("H1") is not None
        assert mgr._schema_validated is True


# ---------- server_state 捕获(WEB /api/stats 数据源) ----------


def test_store_apply_sync_captures_server_state_full_and_delta():
    """server_state 捕获: 全量/增量响应都更新(整引用原子替换, Web 线程只读)"""
    client = FakeClient()
    store = TorrentStore()
    api = _api(client, store)
    client.server_state = {"dl_info_speed": 100, "dht_nodes": 3}
    store.apply_sync(api)
    assert store.server_state == {"dl_info_speed": 100, "dht_nodes": 3}
    # 增量轮(无种子变化)也带 server_state -> 更新
    client.server_state = {"dl_info_speed": 200, "dht_nodes": 5}
    store.apply_sync(api)
    assert store.server_state == {"dl_info_speed": 200, "dht_nodes": 5}


def test_store_apply_sync_server_state_missing_keeps_previous():
    """响应缺失 server_state(老版本/异常替身): 保留上次已知值, 不误清"""
    client = FakeClient()
    store = TorrentStore()
    api = _api(client, store)
    client.server_state = {"dht_nodes": 7}
    store.apply_sync(api)
    client.server_state = None  # 下一轮响应不再附带
    store.apply_sync(api)
    assert store.server_state == {"dht_nodes": 7}


def test_store_apply_sync_fallback_clears_server_state():
    """降级全量(torrents_info)无 server_state 可言 -> 置 None(前端空态渲染)"""
    client = _NoSyncClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    store = TorrentStore()
    store.server_state = {"stale": True}
    store.apply_sync(_api(client, store))
    assert store.server_state is None


def test_apply_delta_quantizes_eta_time_active_last_activity():
    """eta/time_active/last_activity 按分钟量化(与展示精度一致); 负数哨兵(-1)不量化"""
    rec = TorrentRecord(hash="H1")
    # 同一分钟桶内: 不计入变化(避免活跃种子每轮置脏)
    assert rec.apply_delta({"eta": 8640030, "time_active": 30, "last_activity": -1}) == frozenset()
    # 跨桶: 计入变化
    assert rec.apply_delta({"eta": 8640060, "time_active": 120}) == {"eta", "time_active"}
    assert rec.eta == 8640060 and rec.time_active == 120
    # 负数哨兵: 保持 -1(从未)原值, 不被地板除破坏
    assert rec.last_activity == -1
    assert rec.apply_delta({"last_activity": 1700000030}) == {"last_activity"}
    assert rec.last_activity == 1700000030

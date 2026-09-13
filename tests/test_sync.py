"""增量同步层(SyncTorrent / TorrentSync)测试

背景: 主循环原先每 tick 全量拉 torrents/info, 导致 qB 端反复序列化全部种子(CPU 上涨)。
改为走 /api/v2/sync/maindata 的 rid 增量: 只含**变化种子**的**变化字段**, 未变化种子
完全不出现在响应中, 删除种子单列 torrents_removed。

对应实现:
  src/auto_qb/torrents.py  SyncTorrent(字段视图) / TorrentSync(rid 合并)
  src/auto_qb/qbapi.py     QbApi.sync_maindata 透传
  src/auto_qb/qbmanager.py _refresh_torrents / _validate_torrent_schema

测试清单:
- test_sync_torrent_duck_typing: Mapping + 属性访问 + 缺失 AttributeError + state_enum
- test_sync_torrent_merge_object_source: 普通对象源按必需字段收集(测试替身兼容)
- test_sync_full_update_builds_all_fields: rid=0 -> full_update, 视图字段齐全, need_validate
- test_sync_delta_merges_only_changed: 增量轮只合并变化字段, 未变化字段取基线
- test_sync_delta_new_torrent_full_fields: 增量轮新种子回全量字段
- test_sync_delta_removed: torrents_removed 移除视图
- test_sync_full_update_rebuilds_baseline: rid 失效 -> 全量重建(旧基线整体丢弃)
- test_sync_reset: reset 清基线并强制下轮全量
- test_sync_fallback_when_endpoint_unavailable: 无 sync 端点 -> 降级 torrents_info + 告警一次
- test_sync_unknown_error_resets_rid_and_raises: 未知异常上抛且 rid 归零
- test_manager_refresh_uses_incremental_sync: 主循环走 sync 且 store 正确
- test_manager_refresh_validate_gate: 仅全量轮做版本兼容校验
- test_manager_state_snapshot_from_sync_view: SyncTorrent 视图提供 state_enum
- test_manager_refresh_fallback_client: 旧版 qB 替身(无 sync 端点)整轮可用
"""
import logging
import os
import tempfile
from io import StringIO

import pytest

from qbittorrentapi import TorrentState

from auto_qb.qbapi import QbApi
from auto_qb.torrents import SyncTorrent, TorrentStore, TorrentSync, missing_torrent_fields

from helpers import FakeClient, FakeTorrent, make_manager


class _NoSyncClient(FakeClient):
    """无 sync 端点的客户端替身(模拟旧版 qB): 调用 sync_maindata 抛 AttributeError"""
    def sync_maindata(self, rid=0, **kw):
        raise AttributeError("'Client' object has no attribute 'sync_maindata'")


def _api(client: FakeClient) -> QbApi:
    return QbApi(client, TorrentStore())


# ---------- SyncTorrent: 字段视图鸭子类型 ----------


def test_sync_torrent_duck_typing():
    """SyncTorrent 同时满足 Mapping 与属性访问; 缺失字段抛 AttributeError(对齐 AttrDict)"""
    view = SyncTorrent({"hash": "H1", "state": "stalledUP", "size": 10})
    # Mapping: 供 TorrentRecord.update_from 走 dict 级 item 访问
    assert view["state"] == "stalledUP"
    assert view.get("size") == 10
    assert view.get("nope") is None
    assert "state" in view
    assert len(view) == 3
    assert sorted(view) == ["hash", "size", "state"]
    # 属性访问: 供 store/规则/跳检等既有代码
    assert view.hash == "H1"
    assert view.size == 10
    assert "stalledUP" == view.state
    # state_enum 派生(与 TorrentRecord/TorrentDictionary 同语义)
    assert view.state_enum is TorrentState("stalledUP")
    assert view.state_enum.is_uploading
    # 缺失属性: 与 AttrDict 一致抛 AttributeError(不是 None, 便于 fail-fast)
    with pytest.raises(AttributeError):
        view.no_such_field
    # 非 dict 子类: 版本兼容校验的样本选择(跳过测试 plain dict)不受影响
    assert not isinstance(view, dict)


def test_sync_torrent_state_enum_unknown_fallback():
    """非法 state 字符串 -> TorrentState.UNKNOWN(与 TorrentRecord 兜底一致)"""
    view = SyncTorrent({"hash": "H1", "state": "not-a-state"})
    assert view.state_enum is TorrentState.UNKNOWN


def test_sync_torrent_state_enum_missing_state():
    """state 字段缺失(理论不可能, 防御) -> 走兜底而非 KeyError"""
    view = SyncTorrent({"hash": "H1"})
    assert view.state_enum is TorrentState.UNKNOWN


def test_sync_torrent_merge_object_source():
    """对象源(非 Mapping, 测试替身)按必需字段收集属性: 非 None 字段入视图, 并补 hash

    与 TorrentRecord.update_from 的非 Mapping 通道一致: None 值不入快照(视为"未提供"),
    故这类视图不是字段齐全的样本 —— 降级路径的校验样本取原始对象(见下)。
    """
    view = SyncTorrent({})
    view.merge(FakeTorrent(hash="H9", name="N9", state="pausedUP"), hash="H9")
    assert view.hash == "H9"
    assert view.name == "N9"
    assert view.state_enum is TorrentState("pausedUP")
    assert view.up_limit == 0  # 0 是有语义的值(不限速), 会入视图
    assert view.total_size > 0
    assert "ratio_limit" not in view  # None 值不入视图(与 update_from 一致)


# ---------- TorrentSync: rid 增量合并 ----------


def test_sync_full_update_builds_all_fields():
    """首轮 rid=0 -> full_update: 视图字段齐全, need_validate 为真, 样本为视图"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
    sync = TorrentSync()
    views = sync.fetch(_api(client))

    assert len(views) == 1
    assert views[0].hash == "H1"
    assert missing_torrent_fields(views[0]) == []  # 全量响应字段齐全
    assert sync.rid == 1
    assert sync.need_validate is True
    assert sync.validate_sample is views[0]
    assert sync.using_fallback is False


def test_sync_delta_merges_only_changed():
    """增量轮只合并变化字段, 未变化字段保留基线值(不再全量解析)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP", upspeed=0)
    sync = TorrentSync()
    api = _api(client)
    sync.fetch(api)

    client.torrents["H1"].upspeed = 123  # 只改一个字段
    views = sync.fetch(api)

    assert sync.need_validate is False  # 增量轮: 不做 schema 校验
    assert sync.validate_sample is None
    assert len(views) == 1
    assert views[0].upspeed == 123  # 变化字段已更新
    assert views[0].name == "T1"  # 未变化字段来自基线
    assert views[0].size == client.torrents["H1"].size


def test_sync_delta_new_torrent_full_fields():
    """增量轮新增种子: 基线缺失 -> 响应含全量字段, 视图字段齐全"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    sync = TorrentSync()
    api = _api(client)
    sync.fetch(api)

    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2", state="downloading")
    views = sync.fetch(api)

    by_hash = {v.hash: v for v in views}
    assert set(by_hash) == {"H1", "H2"}
    assert by_hash["H2"].name == "T2"
    assert missing_torrent_fields(by_hash["H2"]) == []


def test_sync_delta_removed():
    """torrents_removed: 删除的种子从视图中移除"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
    sync = TorrentSync()
    api = _api(client)
    assert len(sync.fetch(api)) == 2

    del client.torrents["H2"]
    views = sync.fetch(api)
    assert [v.hash for v in views] == ["H1"]
    assert sync.need_validate is False


def test_sync_full_update_rebuilds_baseline():
    """rid 失效 -> full_update: 旧基线整体丢弃(幽灵条目不会残留)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    sync = TorrentSync()
    api = _api(client)
    sync.fetch(api)

    sync._views["GHOST"] = SyncTorrent({"hash": "GHOST"})  # 模拟基线与服务端失同步
    sync.rid = 999  # 与服务端 rid 不匹配 -> full_update
    views = sync.fetch(api)

    assert sync.need_validate is True
    assert [v.hash for v in views] == ["H1"]


def test_sync_empty_qb():
    """空 qB: 全量轮无样本(不做校验), 视图为空; 增量轮仍返回空"""
    client = FakeClient()
    sync = TorrentSync()
    api = _api(client)
    assert sync.fetch(api) == []
    assert sync.need_validate is True
    assert sync.validate_sample is None
    assert sync.fetch(api) == []


def test_sync_reset():
    """reset: 清基线/样本并强制下轮全量(重连/热重载后旧 rid 失效)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    sync = TorrentSync()
    sync.fetch(_api(client))

    sync.reset()
    assert sync.rid == 0
    assert sync.need_validate is True
    assert sync.validate_sample is None
    assert sync._views == {}


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


def test_sync_fallback_when_endpoint_unavailable():
    """sync 端点不可用(旧版 qB) -> 降级全量 torrents_info, 告警仅一次"""
    client = _NoSyncClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    sync = TorrentSync()
    api = _api(client)

    stream, restore = _capture_logger("auto_qb.torrents")
    try:
        views = sync.fetch(api)
        assert [v.hash for v in views] == ["H1"]  # 降级后数据仍正确
        assert sync.using_fallback is True
        assert sync.need_validate is True
        # 降级路径样本保持旧语义: 首个非 dict 的原始种子对象(测试注入的 dict 不作样本)
        assert sync.validate_sample is client.torrents["H1"]
        assert sync.rid == 0  # 降级路径保持 rid 归零
        sync.fetch(api)  # 第二次降级不再重复告警
        assert stream.getvalue().count("降级") == 1
    finally:
        restore()


def test_sync_unknown_error_resets_rid_and_raises():
    """非"端点缺失"异常(网络等) -> rid 归零后原样上抛(由调用方兜底)"""
    class _BoomClient(FakeClient):
        def sync_maindata(self, rid=0, **kw):
            raise RuntimeError("network down")

    sync = TorrentSync()
    sync.rid = 42
    with pytest.raises(RuntimeError):
        sync.fetch(_api(_BoomClient()))
    assert sync.rid == 0  # 下轮强制全量


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
        assert rec is not None
        assert rec.name == "T1"

        # 第二轮: 全量未变化 -> 增量响应无 torrents, 视图仍保留该种子
        mgr._refresh_torrents()
        assert client.sync_calls == 2
        assert mgr.store.get("H1") is not None
        assert mgr.store.get("H1").name == "T1"


def test_manager_refresh_validate_gate():
    """版本兼容校验仅在全量轮放行(增量轮响应只含变化字段, 校验会误报)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")

        mgr._refresh_torrents()
        assert mgr._sync.need_validate is True  # 首轮全量
        assert mgr._schema_validated is True

        mgr._refresh_torrents()
        assert mgr._sync.need_validate is False  # 增量轮不校验


def test_manager_state_snapshot_from_sync_view():
    """store.update_state_snapshot 对 SyncTorrent 视图取到 state_enum(状态变化检测依赖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")

        mgr._refresh_torrents()
        snap = mgr.store.state_snapshot["H1"]
        assert snap is not None
        assert snap.is_uploading

        client.torrents["H1"].state = "pausedUP"
        mgr._refresh_torrents()
        assert mgr.store.state_snapshot["H1"].is_stopped


def test_manager_delta_state_change_detected():
    """增量轮的状态变化能被 store 观测到(规则/分组事件依赖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        mgr._refresh_torrents()

        client.torrents["H1"].state = "pausedUP"  # 只改 state
        mgr._refresh_torrents()
        rec = mgr.store.get("H1")
        assert rec is not None
        assert rec.state == "pausedUP"
        assert rec.state_enum.is_stopped


def test_manager_refresh_fallback_client():
    """无 sync 端点的客户端替身: 主循环整轮仍可用(降级全量)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = _NoSyncClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", state="stalledUP")

        mgr._refresh_torrents()
        assert mgr._sync.using_fallback is True
        assert mgr.store.get("H1") is not None
        assert mgr._schema_validated is True

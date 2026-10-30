"""test_transfer_adapters 测试计划: 转移执行层适配器(协议/注册表/qb 实现/tr stub, 全 mock 不联网)

## 测试计划(每个测试函数一条)
- test_registry_creates_by_type: 按 target.type 实例化(qb/tr), 且 target 绑定到实例
- test_registry_unknown_type_raises: 未知 type 抛 UnknownAdapterTypeError(文案含类型与已知清单)
- test_adapter_type_known: adapter_type_known 对已知/未知类型的预检结果
- test_qb_capabilities_cover_all_field_keys: qb capabilities = TRANSFER_FIELD_KEYS 全集
- test_qb_test_connection_success: 登录+取版本成功 -> "qBittorrent <version>" 描述信息
- test_qb_test_connection_login_failed: LoginFailed -> 抛 TransferAdapterError(文案含"登录失败")
- test_qb_test_connection_unreachable: APIConnectionError -> 抛 TransferAdapterError(文案含"无法连接")
- test_qb_test_connection_reuses_client: 同一 adapter 多次探测复用同一 client(单批一个连接)
- test_qb_add_field_mapping: 字段键 -> torrents/add 参数映射(category/tags/ratio_limit/seeding_time_limit/upload_limit/download_limit)
- test_qb_add_save_path_and_skip_check: save_path 必带 + skip_check 透传为 is_skip_checking(开/关两向)
- test_qb_add_text_ok_result: 旧形态纯文本 "Ok." -> ADDED
- test_qb_add_metadata_result: 新形态元数据(success_count/added_torrent_ids) -> ADDED 且 infohash 取自回执
- test_qb_add_duplicate_text_result: 响应文本含已存在文案 -> SKIPPED(不是失败)
- test_qb_add_rejected_with_probe_hash_exists: 全部被拒 + 探针 hash 在目标查得 -> SKIPPED
- test_qb_add_rejected_probe_hash_absent: 全部被拒 + 探针 hash 目标查无 -> FAILED
- test_qb_add_rejected_without_probe: 全部被拒且无探针 hash -> FAILED(不查重)
- test_qb_add_conflict409_duplicate: 抛 Conflict409Error 且文案含已存在 -> SKIPPED
- test_qb_add_connection_error_failed: 调用异常(网络) -> FAILED 态返回, 不上抛
- test_qb_add_missing_save_path_fails: save_path 缺失 -> FAILED 且未发起 torrents_add
- test_qb_add_empty_data_raises: data 空字节 -> TypeError(编程错误)
- test_qb_add_unknown_field_downgraded: capabilities 外的字段键被忽略并写进 ignored_fields(降级注明)
- test_qb_add_empty_tags_not_sent: tags 空串/逗号空项 -> 不下发 tags 参数
- test_qb_add_super_seeding_applied: 添加成功且 hash 可得 -> setSuperSeeding 一发 + reason 注明
- test_qb_add_super_seeding_without_hash: 添加成功但无回执 hash -> 不调 setSuperSeeding, reason 注明未应用
- test_tr_stub_capabilities_and_test: tr stub capabilities 空集 + test_connection 返回"暂未实现"前缀
- test_tr_stub_add_torrent_raises: tr stub add_torrent 抛 NotImplementedError
- test_add_result_ok_property: AddResult.ok 三态语义(failed=False, added/skipped=True)
- test_normalize_tags: tags 归一(str 逗号串/列表/去空项)
"""
from unittest.mock import MagicMock

import pytest
from qbittorrentapi import APIConnectionError, Conflict409Error, LoginFailed

from auto_qb.config import TRANSFER_FIELD_KEYS, TransferTargetConfig
from auto_qb.transfer.adapters import (
    AddResult,
    AddStatus,
    QbDownloaderAdapter,
    TrDownloaderStub,
    UnknownAdapterTypeError,
    adapter_type_known,
    create_adapter,
)
from auto_qb.transfer.adapters.qb import _normalize_tags

# ---------- 构造助手 ----------


def _make_target(**overrides) -> TransferTargetConfig:
    values = dict(
        name="目标A",
        type="qb",
        base_url="http://127.0.0.1:8081",
        username="user",
        password="pass",
        enabled=True,
    )
    values.update(overrides)
    return TransferTargetConfig(**values)


def _qb_adapter(monkeypatch, client: MagicMock) -> QbDownloaderAdapter:
    """qb adapter + 注入 mock 客户端(替换单点 _build_client, 全程不联网)"""
    adapter = QbDownloaderAdapter(_make_target())
    monkeypatch.setattr(adapter, "_build_client", lambda: client)
    return adapter


def _metadata_result(success=1, failure=0, pending=0, ids=()):
    """新形态 torrents/add 响应(WebAPI 2.14+ 元数据, dict 即可 —— 判定只认 Mapping)"""
    return {
        "success_count": success,
        "failure_count": failure,
        "pending_count": pending,
        "added_torrent_ids": list(ids),
    }


# ---------- 注册表 ----------


def test_registry_creates_by_type(monkeypatch):
    qb = create_adapter(_make_target(type="qb"))
    assert isinstance(qb, QbDownloaderAdapter)
    assert qb.target.name == "目标A"
    tr = create_adapter(_make_target(type="tr"))
    assert isinstance(tr, TrDownloaderStub)


def test_registry_unknown_type_raises():
    with pytest.raises(UnknownAdapterTypeError) as excinfo:
        create_adapter(_make_target(type="rtorrent"))
    assert "rtorrent" in str(excinfo.value)
    assert "qb" in str(excinfo.value) and "tr" in str(excinfo.value)


def test_adapter_type_known():
    assert adapter_type_known("qb") is True
    assert adapter_type_known("tr") is True
    assert adapter_type_known("rtorrent") is False


# ---------- qb: capabilities 与 test_connection ----------


def test_qb_capabilities_cover_all_field_keys(monkeypatch):
    adapter = _qb_adapter(monkeypatch, MagicMock())
    assert adapter.capabilities() == set(TRANSFER_FIELD_KEYS)


def test_qb_test_connection_success(monkeypatch):
    client = MagicMock()
    client.app_version.return_value = "v5.2.3"
    adapter = _qb_adapter(monkeypatch, client)
    assert adapter.test_connection() == "qBittorrent v5.2.3"
    client.app_version.assert_called_once()


def test_qb_test_connection_login_failed(monkeypatch):
    client = MagicMock()
    client.app_version.side_effect = LoginFailed()
    adapter = _qb_adapter(monkeypatch, client)
    with pytest.raises(Exception) as excinfo:  # noqa: B017 —— AutoQbError 家族, 文案可回显
        adapter.test_connection()
    assert "登录失败" in str(excinfo.value)


def test_qb_test_connection_unreachable(monkeypatch):
    client = MagicMock()
    client.app_version.side_effect = APIConnectionError("connection refused")
    adapter = _qb_adapter(monkeypatch, client)
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        adapter.test_connection()
    assert "无法连接" in str(excinfo.value)


def test_qb_test_connection_reuses_client(monkeypatch):
    client = MagicMock()
    client.app_version.return_value = "v5.2.3"
    adapter = QbDownloaderAdapter(_make_target())
    calls = []
    monkeypatch.setattr(adapter, "_build_client", lambda: calls.append(1) or client)
    adapter.test_connection()
    adapter.test_connection()
    assert len(calls) == 1


# ---------- qb: add_torrent 字段映射 ----------


def test_qb_add_field_mapping(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(
        b"d4:infod4:name3:abce",
        {
            "save_path": "/data/target",
            "category": "tv",
            "tags": ["zA", "zB"],
            "share_ratio_limit": 1.5,
            "seeding_time_limit": 10080,
            "up_limit": 1024,
            "down_limit": 2048,
        },
        skip_check=False,
    )
    assert result.status is AddStatus.ADDED
    kwargs = client.torrents_add.call_args.kwargs
    assert kwargs["save_path"] == "/data/target"
    assert kwargs["category"] == "tv"
    assert kwargs["tags"] == ["zA", "zB"]
    assert kwargs["ratio_limit"] == 1.5
    assert kwargs["seeding_time_limit"] == 10080
    assert kwargs["upload_limit"] == 1024
    assert kwargs["download_limit"] == 2048


def test_qb_add_save_path_and_skip_check(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=True)
    assert client.torrents_add.call_args.kwargs["is_skip_checking"] is True
    adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert client.torrents_add.call_args.kwargs["is_skip_checking"] is False


def test_qb_add_text_ok_result(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert result.status is AddStatus.ADDED
    assert result.infohash == ""


def test_qb_add_metadata_result(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = _metadata_result(success=1, ids=["ABC123"])
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert result.status is AddStatus.ADDED
    assert result.infohash == "ABC123"
    assert "成功 1" in result.reason


def test_qb_add_duplicate_text_result(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Torrent is already exist."
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=True)
    assert result.status is AddStatus.SKIPPED
    assert result.ok is True


def test_qb_add_rejected_with_probe_hash_exists(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = _metadata_result(success=0, failure=1)
    client.torrents_info.return_value = [{"hash": "ABC123"}]
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "infohash": "ABC123"}, skip_check=False)
    assert result.status is AddStatus.SKIPPED
    assert result.infohash == "ABC123"
    client.torrents_info.assert_called_once()


def test_qb_add_rejected_probe_hash_absent(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = _metadata_result(success=0, failure=1)
    client.torrents_info.return_value = []
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "infohash": "ABC123"}, skip_check=False)
    assert result.status is AddStatus.FAILED
    assert result.ok is False


def test_qb_add_rejected_without_probe(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = _metadata_result(success=0, failure=1)
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert result.status is AddStatus.FAILED
    client.torrents_info.assert_not_called()


def test_qb_add_conflict409_duplicate(monkeypatch):
    client = MagicMock()
    client.torrents_add.side_effect = Conflict409Error("Torrent is already exist.")
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert result.status is AddStatus.SKIPPED


def test_qb_add_connection_error_failed(monkeypatch):
    client = MagicMock()
    client.torrents_add.side_effect = APIConnectionError("refused")
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)
    assert result.status is AddStatus.FAILED
    assert "refused" in result.reason


def test_qb_add_missing_save_path_fails(monkeypatch):
    client = MagicMock()
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"category": "tv"}, skip_check=False)
    assert result.status is AddStatus.FAILED
    assert "保存路径" in result.reason
    client.torrents_add.assert_not_called()


def test_qb_add_empty_data_raises(monkeypatch):
    client = MagicMock()
    adapter = _qb_adapter(monkeypatch, client)
    with pytest.raises(TypeError):
        adapter.add_torrent(b"", {"save_path": "/d"}, skip_check=False)
    client.torrents_add.assert_not_called()


def test_qb_add_unknown_field_downgraded(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(
        b"d4:infod4:name3:abce",
        {
            "save_path": "/d",
            "future_field": "x"
        },
        skip_check=False,
    )
    assert result.status is AddStatus.ADDED
    assert result.ignored_fields == ("future_field", )
    assert "future_field" not in client.torrents_add.call_args.kwargs


def test_qb_add_empty_tags_not_sent(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "tags": ""}, skip_check=False)
    assert "tags" not in client.torrents_add.call_args.kwargs
    adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "tags": ", ,"}, skip_check=False)
    assert "tags" not in client.torrents_add.call_args.kwargs


def test_qb_add_super_seeding_applied(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = _metadata_result(success=1, ids=["ABC123"])
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "super_seeding": True}, skip_check=False)
    assert result.status is AddStatus.ADDED
    client.torrents_set_super_seeding.assert_called_once_with(enable=True, torrent_hashes="ABC123")
    assert "超级做种" in result.reason


def test_qb_add_super_seeding_without_hash(monkeypatch):
    client = MagicMock()
    client.torrents_add.return_value = "Ok."
    adapter = _qb_adapter(monkeypatch, client)
    result = adapter.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d", "super_seeding": True}, skip_check=False)
    assert result.status is AddStatus.ADDED
    client.torrents_set_super_seeding.assert_not_called()
    assert "超级做种未应用" in result.reason


# ---------- tr stub ----------


def test_tr_stub_capabilities_and_test():
    stub = TrDownloaderStub(_make_target(type="tr"))
    assert stub.capabilities() == set()
    text = stub.test_connection()
    assert text.startswith("暂未实现")


def test_tr_stub_add_torrent_raises():
    stub = TrDownloaderStub(_make_target(type="tr"))
    with pytest.raises(NotImplementedError):
        stub.add_torrent(b"d4:infod4:name3:abce", {"save_path": "/d"}, skip_check=False)


# ---------- 结果结构与纯函数 ----------


def test_add_result_ok_property():
    assert AddResult.added().ok is True
    assert AddResult.skipped().ok is True
    assert AddResult.failed().ok is False


def test_normalize_tags():
    assert _normalize_tags("a, b,,c") == ["a", "b", "c"]
    assert _normalize_tags(["x", "", "y"]) == ["x", "y"]
    assert _normalize_tags("") == []

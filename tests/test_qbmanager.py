"""qbmanager 模块测试: 全局任务创建 / 种子查询 / 连接"""
import os
import tempfile
from unittest import mock

from helpers import FakeClient, FakeConfig, FakeTorrent, make_manager


def test_create_global_tasks():
    """delete_tags 配置存在时创建 internal 全局任务并入队"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 无 delete_tags 配置: 不创建
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" not in names
        # 配置 delete_tags: 创建任务
        mgr.config.delete_tags = ["regex:^seed-"]
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" in names
        assert "delete_tags_if_has_no_torrents" in names


def test_get_torrent():
    """_get_torrent: 存在返回种子 / 删除返回 None / 异常返回 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        assert mgr._get_torrent("H1").hash == "H1"
        assert mgr._get_torrent("NOPE") is None
        client.torrents_info = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
        assert mgr._get_torrent("H1") is None


def test_connect_failure():
    """连接失败返回 False 且 client 保持 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.qbmanager.Client", side_effect=Exception("conn refused")):
            assert mgr.connect() is False
        assert mgr.client is None


def test_connect_success():
    """连接成功返回 True 并登录"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        fake = mock.Mock()
        with mock.patch("auto_qb.qbmanager.Client", return_value=fake):
            assert mgr.connect() is True
        fake.auth_log_in.assert_called_once()
        assert mgr.client is fake

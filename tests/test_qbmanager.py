"""test_qbmanager 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_create_global_tasks: 按配置创建 delete_tags 等全局任务
- test_get_torrent: _get_torrent 存在/删除/异常三种情形
- test_connect_failure: 连接失败返回 False 且 client 为 None
- test_connect_success: 连接成功返回 True 并登录
- test_safe_no_handler: 无 handler 的任务 -> True
- test_safe_handler_ok: handler 返回 False -> 任务消亡
- test_safe_handler_exception: handler 抛异常被捕获 -> True
- test_execute_due_reschedule: handler 成功 -> 任务 reschedule
- test_execute_due_drop: handler 返回 False -> 不 reschedule
- test_run_connect_failure: 连接失败 run 直接返回不进入主循环
"""
import os
import tempfile
import time
from unittest import mock

from auto_qb.taskqueue import PENDING, Task
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


def test_safe_no_handler():
    """_safe: 无 handler -> True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=0)
        assert mgr._safe(task, dry_run=False) is True


def test_safe_handler_ok():
    """_safe: handler 返回 False -> False(任务消亡)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=0, handler=lambda t, d: False)
        assert mgr._safe(task, dry_run=False) is False


def test_safe_handler_exception():
    """_safe: handler 抛异常 -> 捕获并返回 True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))

        def boom(t, d):
            raise RuntimeError("boom")

        task = Task("rule", "t", interval=0, handler=boom)
        assert mgr._safe(task, dry_run=False) is True


def test_execute_due_reschedule():
    """_execute_due: handler 返回 True -> 任务 reschedule(run_count+1, 回 PENDING)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: True)
        now = time.time()
        mgr._execute_due([task], dry_run=False, now=now)
        assert task.run_count == 1
        assert task.state == PENDING


def test_execute_due_drop():
    """_execute_due: handler 返回 False -> 不 reschedule(任务消亡)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: False)
        now = time.time()
        mgr._execute_due([task], dry_run=False, now=now)
        assert task.run_count == 0, "消亡任务不应 reschedule"


def test_run_connect_failure():
    """run: 连接失败直接返回, 不进入主循环"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        mgr.run(dry_run=False)  # 不应抛异常/不应调用 _tick
        mgr.connect.assert_called_once()

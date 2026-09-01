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
- test_execute_due_deferred: handler 让位(defer) -> 不 reschedule 不消亡, 保持 DEFERRED
- test_run_connect_failure: 连接失败 run 直接返回不进入主循环
- test_run_main_loop: 主循环: _tick 异常被捕获, KeyboardInterrupt 停止, finally 清理
- test_tick_full_flow: 快速队列到期任务执行全流程(含 check 轮询任务首轮发送)
- test_create_torrent_tasks_tor_missing: 种子不在快照 -> 直接返回
- test_create_torrent_tasks_no_tracker: 未匹配 tracker -> 拉取 + 警告 + False
- test_create_torrent_tasks_with_rules: 匹配 tracker -> 创建 maintenance + 规则任务
- test_handle_maintenance_tor_missing: 种子不存在 -> False(任务消亡)
- test_run_save_state_on_exit: run 退出后保存状态文件且为有效 JSON dict
- test_run_dry_run_no_save: dry_run=True 退出后不写状态文件
- test_tick_refresh_error_continues: 主循环内 _refresh_torrents 抛异常被捕获, 下一 tick 继续
- test_execute_due_respects_max: 每 tick 最多执行 max_tasks_per_tick 个, 超额留队列
"""
import json
import os
import tempfile
import time
from unittest import mock

from auto_qb.taskqueue import DEFERRED, PENDING, Task, TaskQueue
from helpers import FakeClient, FakeConfig, FakeTorrent, make_manager, seed_store


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
    """_get_torrent: 存在返回种子(store 快照) / 快照外返回 None / 删除后返回 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        assert mgr._get_torrent("H1") is None  # 未刷新快照 -> 无记录
        seed_store(mgr)
        assert mgr._get_torrent("H1").hash == "H1"
        assert mgr._get_torrent("NOPE") is None
        mgr.store.apply([])  # 种子删除 -> 快照移除
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


def test_execute_due_deferred():
    """_execute_due: handler 让位(defer) -> 不 reschedule 不消亡, 状态保持 DEFERRED"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: mgr.task_queue.defer(t) or True)
        now = time.time()
        mgr._execute_due([task], dry_run=False, now=now)
        assert task.state == DEFERRED, "让位任务状态应为 deferred"
        assert task.run_count == 0, "让位任务不应 reschedule"
        assert task not in mgr.task_queue._fast, "让位任务不应在队列中"
        assert task in mgr.task_queue._deferred, "让位任务应挂起到 _deferred"


def test_run_connect_failure():
    """run: 连接失败直接返回, 不进入主循环"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        mgr.run(dry_run=False)  # 不应抛异常/不应调用 _tick
        mgr.connect.assert_called_once()


def test_run_main_loop():
    """run: 连接成功进入主循环; _tick 异常被捕获; KeyboardInterrupt 停止; finally 清理+保存"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=[RuntimeError("boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._tick.call_count == 2, "异常应被捕获继续循环, KeyboardInterrupt 退出"
        assert os.path.exists(state_file), "finally 应保存状态"


def test_tick_full_flow():
    """_tick: 快速队列到期任务执行(含 check 轮询任务首轮执行 + 常规任务 reschedule)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(hash="HASH123", state="pausedUP")
        mgr.task_queue = TaskQueue()
        # check 轮询任务: 首轮执行后消亡(handler 返回 False)
        check_calls = []

        def check_poll(t, d):
            check_calls.append(1)
            return False

        mgr.task_queue.add_check_task(
            Task("check", "check-checking-result", torrent_hash="HASH123", interval=2.0, handler=check_poll)
        )
        # 常规到期任务
        due_task = Task("rule", "t", interval=0, handler=lambda t, d: True)
        due_task.next_run = time.time() - 1
        mgr.task_queue._fast.append(due_task)
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        assert check_calls == [1], "check 任务应执行"
        assert due_task.run_count == 1, "到期任务应执行并 reschedule"


def test_create_torrent_tasks_tor_missing():
    """_create_torrent_tasks: 种子不在快照 -> 直接返回, 不建任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr._snapshot = []
        assert mgr._create_torrent_tasks("NOPE") is None
        assert mgr.task_queue._fast == []


def test_create_torrent_tasks_no_tracker():
    """_create_torrent_tasks: 未匹配 tracker 配置 -> 拉取 trackers + 警告 + False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents_trackers = lambda h: [{"url": "https://tracker.other.org/announce"}]
        tor = FakeTorrent(hash="H1", tags="")
        seed_store(mgr, [tor])
        assert mgr._create_torrent_tasks("H1") is False, "未匹配应跳过"
        assert mgr.task_queue._fast == [], "不应创建任何任务"


def test_create_torrent_tasks_with_rules():
    """_create_torrent_tasks: 匹配 tracker -> 创建 maintenance + 全部规则任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="HASH123", tags="")
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        mgr._create_torrent_tasks("HASH123")
        names = [t.name for t in mgr.task_queue._fast]
        assert "maintenance" in names, f"应创建内置任务: {names}"
        assert "example_rules.add_site_tag" in names, f"应创建规则任务: {names}"


def test_handle_maintenance_tor_missing():
    """_handle_maintenance: 种子不存在 -> False(任务消亡, 不重入队)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        task = Task("internal", "maintenance", torrent_hash="NOPE", tracker_conf=mock.Mock())
        assert mgr._handle_maintenance(task, dry_run=False) is False


def test_run_save_state_on_exit():
    """run: 非 dry_run 退出后保存状态文件, 且内容为有效 JSON dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "状态文件应为 JSON dict"


def test_run_dry_run_no_save():
    """run: dry_run=True 退出后不写状态文件"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.qbmanager.time.sleep"):
            mgr.run(dry_run=True)
        assert not os.path.exists(state_file), "dry_run 不应写状态文件"


def test_tick_refresh_error_continues():
    """run 主循环: _refresh_torrents 抛异常被捕获, 循环继续到下一 tick"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # 第一次抛普通异常(被内层 except Exception 捕获), 第二次抛 KeyboardInterrupt(退出循环)
        mgr._refresh_torrents = mock.Mock(side_effect=[RuntimeError("refresh boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._refresh_torrents.call_count == 2, "第一次异常应被捕获, 第二次 tick 继续执行"


def test_execute_due_respects_max():
    """_tick: 每 tick 最多执行 max_tasks_per_tick 个到期任务, 超额留在队列"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.task_queue = TaskQueue()
        mgr.config.max_tasks_per_tick = 2
        for i in range(3):
            t = Task("rule", f"t{i}", interval=60, handler=lambda t, d: True)
            mgr.task_queue.add_task(t)  # next_run=now, 全部到期
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        executed = [t.name for t in mgr.task_queue._fast if t.run_count == 1]
        remaining = [t.name for t in mgr.task_queue._fast if t.run_count == 0]
        assert len(executed) == 2, f"每 tick 最多执行 max_tasks_per_tick=2: {executed}"
        assert len(remaining) == 1, f"超额任务应留在队列: {remaining}"

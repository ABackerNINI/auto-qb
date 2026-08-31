"""test_delete_tags 测试计划: 全局标签清理

## 测试计划(每个测试函数一条)
- test_global_delete_tags: 彻底删除标签(匹配正则的标签被删)
- test_global_delete_tags_dry_run: dry-run 不实际删除
- test_global_delete_tags_if_has_no_torrents: 仅删除无种子的标签
- test_global_delete_tags_no_pattern_match: 无匹配模式时无操作
- test_global_delete_tags_queued: 标签删除任务入队执行
"""
import os
import tempfile

from auto_qb.qbmanager import QbManager
from auto_qb.taskqueue import Task
from helpers import FakeClient, FakeConfig, FakeTorrent


def test_global_delete_tags():
    """全局任务彻底删除标签(精确 + 正则 regex: 前缀)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP", "regex:^BTSCHOOL"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # 客户端已有标签定义 + 种子使用中
        client.tags = {"HHan", "M-Team - TP", "BTSCHOOL-OLD", "KEEP"}
        tor = FakeTorrent(tags="HHan,M-Team - TP,BTSCHOOL-OLD")
        client.torrents["HASH123"] = tor

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=False)

        # 精确匹配 M-Team - TP, 正则匹配 BTSCHOOL-OLD; KEEP/HHan 保留
        assert ("delete_tags", {"M-Team - TP", "BTSCHOOL-OLD"}) in client.calls, f"应彻底删除匹配标签: {client.calls}"
        assert client.tags == {"HHan", "KEEP"}, f"标签定义剩余: {client.tags}"
        assert tor.tags == "HHan", f"种子标签应同步移除: {tor.tags}"


def test_global_delete_tags_dry_run():
    """全局删除标签 dry-run 无副作用"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.tags = {"HHan", "M-Team - TP"}

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=True)
        assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"
        assert client.tags == {"HHan", "M-Team - TP"}, "dry-run 不应改变标签"


def test_global_delete_tags_if_has_no_torrents():
    """全局任务彻底删除无种子的标签(仅删无种子使用的, 有种子使用保留)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        # 模拟 load_config 展开 @tracker_tags 后的结果: 站点标签 HHan
        cfg.delete_tags_if_has_no_torrents = ["HHan", "regex:^ORPHAN"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # HHan 无种子使用(孤儿), ORPHAN-1 无种子使用, KEEP 有种子使用
        client.tags = {"HHan", "ORPHAN-1", "KEEP"}
        tor = FakeTorrent(tags="KEEP")
        client.torrents["HASH123"] = tor

        task = Task(
            "internal",
            "delete_tags_if_has_no_torrents",
            interval=60,
            handler=mgr._handle_delete_tags_if_has_no_torrents
        )
        mgr._handle_delete_tags_if_has_no_torrents(task, dry_run=False)

        assert ("delete_tags", {"HHan", "ORPHAN-1"}) in client.calls, f"应删除无种子标签: {client.calls}"
        assert client.tags == {"KEEP"}, f"有种子使用的标签应保留: {client.tags}"


def test_global_delete_tags_no_pattern_match():
    """无匹配格式时不调用客户端"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["不存在的标签"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.tags = {"HHan", "KEEP"}
        tor = FakeTorrent(tags="HHan")
        client.torrents["HASH123"] = tor

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=False)
        assert client.calls == [], f"无匹配不应调用客户端: {client.calls}"


def test_global_delete_tags_queued():
    """配置非空时创建两个全局任务加入队列"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP"]
        cfg.delete_tags_if_has_no_torrents = ["@tracker_tags"]
        mgr = QbManager("", config=cfg)
        mgr._create_global_tasks()  # run() 中才自动创建; 测试直接构造后手动创建
        # 队列应包含两个全局标签清理任务
        names = {t.name for t in mgr.task_queue._fast}
        assert "delete_tags" in names, f"缺少 delete_tags 任务: {names}"
        assert "delete_tags_if_has_no_torrents" in names, f"缺少 delete_tags_if_has_no_torrents 任务: {names}"
        for t in mgr.task_queue._fast:
            if t.name in ("delete_tags", "delete_tags_if_has_no_torrents"):
                assert t.interval == cfg.interval, f"全局任务 interval 应为 {cfg.interval}: {t.interval}"

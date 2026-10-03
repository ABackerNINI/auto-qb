"""kernel-module-refactor P3 守阵: tracker / speed_curve / maintenance 三模块(plan 26-09-30-1819)

P3 内容: TrackerModule(_match_tracker_conf 升 ctx.trackers 服务 + 全量轮重匹配改订阅
full_round 相位) / SpeedCurveModule(曲线任务自注册 + 流量快照改 ctx.web 服务方法推送) /
MaintenanceModule(tags + _handle_maintenance + delete_tags 全局任务 + 集数标签一起搬) /
内核 _create_global_tasks 任务点名退役(只剩 queue_rebuilt 相位广播的兼容转发)。
本文件锁五件事:
1. ctx 服务/句柄装配: ctx.trackers 是已注册模块本体(决策点 D3), 装配序在 webui/hr 之后;
2. full_round 相位: 内核 emit -> tracker 模块重匹配 conf 置空记录(全量轮契约兑现);
3. 全局任务自注册: start 按配置入队 + 重复 start 幂等(has_named) + 队列重建(queue_rebuilt
   相位 / _create_global_tasks 兼容转发)后按新配置重新入队;
4. 流量快照发布走 ctx.web.set_traffic_view 服务方法(manager.web.traffic_view 同源可见);
5. sections 认领清单(P6 段认领完备守阵上线前的基线锁定)。

行为细节(限速/标签/集数/曲线节流)的守阵仍在原位: test_tracker / test_mixins_tags /
test_delete_tags / test_speed_curve / test_trigger_events(经 manager 旧名单行委托, plan §7.2)。

## 测试计划
- test_tracker_module_on_ctx_and_registered: ctx.trackers 是宿主注册表里的 tracker 模块本体
- test_full_round_phase_rematches_empty_confs: emit full_round -> conf 置空记录被重匹配
- test_speed_curve_start_registers_task_once: 配置存在 -> start 入队; 重复 start 幂等
- test_speed_curve_start_without_config_no_task: 未配置曲线 -> 不建任务
- test_speed_curve_queue_rebuilt_reregisters_with_new_interval: 队列整体重建后经相位重新入队, interval 取新值
- test_create_global_tasks_delegate_reregisters_both_modules: 兼容转发一发令, 曲线+标签清理两模块都入队
- test_create_global_tasks_delegate_idempotent_on_same_queue: 同队列重复调用不重复入队
- test_traffic_publish_goes_through_ctx_web_service: _publish_traffic 经 ctx.web.set_traffic_view, 别名同源可见
- test_maintenance_start_registers_delete_tags_per_config: delete_tags 两任务按配置入队, interval=主 interval
- test_maintenance_queue_rebuilt_reregisters: 队列重建后标签清理任务回到新队列
- test_p3_modules_sections_claims: 三模块 sections 认领清单锁定
- test_p2a_maintenance_added_event_unknown_hash_noop: 维护 added 事件 hash 不在快照早退 (P2-a)
- test_p2a_maintenance_register_global_tasks_without_queue: 队列引用 None 早退; 恢复后按配置入队 (P2-a)
- test_p2a_maintenance_task_interface_delegates: task 接口委托 handle_maintenance (P2-a)
- test_p2a_maintenance_remove_tags_dry_run_and_similar_paths: remove_tags/similar dry-run 与 False 路径 (P2-a)
- test_p2a_maintenance_add_episode_tags_no_episodes: 无集数不加标签 (P2-a)
- test_p2a_maintenance_create_category_existing_noop: 分类已存在不重建 (P2-a)
- test_p2a_maintenance_delete_unused_tags_dry_run: 删无种子标签 dry-run 命中不打 API (P2-a)
- test_p2a_tracker_added_event_unknown_hash_noop: tracker added 事件 hash 不在快照早退 (P2-a)
"""
import os
import tempfile
from unittest import mock

from auto_qb.core.modules import MaintenanceModule, SpeedCurveModule, TrackerModule
from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue
from helpers import FakeClient, FakeTorrent, make_manager, seed_store


def _mgr(td):
    return make_manager(os.path.join(td, "state.json"))


# ---------- 装配与 ctx 服务(plan §3.3 / 决策点 D3) ----------


def test_tracker_module_on_ctx_and_registered():
    """ctx.trackers 就是宿主注册表里的 tracker 模块本体(服务化不另立对象)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        assert isinstance(mgr.ctx.trackers, TrackerModule)
        assert mgr.host.get("tracker") is mgr.ctx.trackers
        # 装配序(plan §3.3): webui -> hr -> tracker -> speed_curve -> maintenance
        names = [m.name for m in mgr.host.modules()]
        assert names.index("webui") < names.index("hr") < names.index("tracker") \
            < names.index("speed_curve") < names.index("maintenance")


# ---------- full_round 相位(plan §4.2) ----------


def test_full_round_phase_rematches_empty_confs():
    """emit full_round -> tracker 模块把 conf 置空的存量记录重匹配(L2 全量轮契约)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        tor = FakeTorrent(hash="H1")
        seed_store(mgr, [tor])
        rec = mgr.store.get("H1")
        assert rec.tracker_conf is None
        n = mgr.events.emit("full_round")
        assert n == 2, "tracker(重匹配) + rules(种子级任务补建, issue 26-10-01-2147)订阅 full_round"
        assert rec.tracker_conf is not None, "全量轮相位应兑现重匹配"
        assert rec.tracker_conf.name == "HHan"


# ---------- 全局任务自注册(plan §3.2) ----------


def test_speed_curve_start_registers_task_once():
    """配置存在 -> start 入队(缺省 interval 回退主 interval); 重复 start 幂等"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.global_speed_limit_curve = mock.MagicMock(interval=None, enabled=True)
        mod = mgr.host.get("speed_curve")
        mod.start(mgr.ctx, dry_run=False)
        names = [t.name for t in mgr.task_queue._fast]
        assert names.count("speed_limit_curve") == 1
        assert mgr.task_queue._fast[0].interval == mgr.config.interval
        mod.start(mgr.ctx, dry_run=False)  # 黄金法则 1: 已注册必须零副作用
        assert [t.name for t in mgr.task_queue._fast].count("speed_limit_curve") == 1


def test_speed_curve_start_without_config_no_task():
    """未配置曲线 -> 不建任务(与原 _create_global_tasks 同判据)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.host.get("speed_curve").start(mgr.ctx, dry_run=False)
        assert all(t.name != "speed_limit_curve" for t in mgr.task_queue._fast)


def test_speed_curve_queue_rebuilt_reregisters_with_new_interval():
    """L2 整体重建队列 -> queue_rebuilt 相位按新配置重新入队(interval 取专属值)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.global_speed_limit_curve = mock.MagicMock(interval=None, enabled=True)
        mgr.host.get("speed_curve").start(mgr.ctx, dry_run=False)
        old_task = next(t for t in mgr.task_queue._fast if t.name == "speed_limit_curve")
        mgr.config.global_speed_limit_curve.interval = 600
        mgr.task_queue = TaskQueue()  # 模拟 L2: 队列整体替换(setter 落回 ctx)
        mgr.events.emit("queue_rebuilt")
        tasks = [t for t in mgr.task_queue._fast if t.name == "speed_limit_curve"]
        assert len(tasks) == 1 and tasks[0].interval == 600 and tasks[0] is not old_task


def test_create_global_tasks_delegate_reregisters_both_modules():
    """内核兼容转发一发令: 曲线 + 标签清理两模块都按当前配置入队(任务点名已退役)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.global_speed_limit_curve = mock.MagicMock(interval=None, enabled=True)
        mgr.config.delete_tags = ["regex:^seed-"]
        mgr._create_global_tasks()
        names = {t.name for t in mgr.task_queue._fast}
        assert {"speed_limit_curve", "delete_tags"} <= names


def test_create_global_tasks_delegate_idempotent_on_same_queue():
    """同一队列重复调用不重复入队(TaskQueue.has_named 幂等守卫, 黄金法则 1)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.global_speed_limit_curve = mock.MagicMock(interval=None, enabled=True)
        mgr.config.delete_tags = ["regex:^seed-"]
        mgr._create_global_tasks()
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert names.count("speed_limit_curve") == 1
        assert names.count("delete_tags") == 1


# ---------- 流量快照发布(plan §5: ctx.web 服务方法) ----------


def test_traffic_publish_goes_through_ctx_web_service():
    """_publish_traffic 经 ctx.web.set_traffic_view 发布; manager.web.traffic_view 同源可见"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        with mock.patch.object(mgr.web, "set_traffic_view", wraps=mgr.web.set_traffic_view) as pub:
            mgr.host.get("speed_curve")._publish_traffic("ok", periods=[{"period": "day"}], target={"up": 1, "down": 2})
        assert pub.call_count == 1
        view = mgr.web.traffic_view  # 旧名别名 -> self.web.traffic_view(同一份)
        assert view["state"] == "ok" and view["periods"] == [{"period": "day"}]
        assert view["limit"]["target"] == {"up": 1, "down": 2}


# ---------- maintenance 全局任务与认领 ----------


def test_maintenance_start_registers_delete_tags_per_config():
    """delete_tags 两个全局任务按配置入队, interval = 主 interval; 未配置不建"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.host.get("maintenance").start(mgr.ctx, dry_run=False)  # 默认空配置: 无任务
        assert all(t.name != "delete_tags" for t in mgr.task_queue._fast)
        mgr.config.delete_tags = ["M-Team - TP"]
        mgr.config.delete_tags_if_has_no_torrents = ["@tracker_tags"]
        mgr.host.get("maintenance").start(mgr.ctx, dry_run=False)
        for t in mgr.task_queue._fast:
            if t.name in ("delete_tags", "delete_tags_if_has_no_torrents"):
                assert t.interval == mgr.config.interval


def test_maintenance_queue_rebuilt_reregisters():
    """队列整体重建后经 queue_rebuilt 相位, 标签清理任务回到新队列"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.delete_tags = ["M-Team - TP"]
        mgr.host.get("maintenance").start(mgr.ctx, dry_run=False)
        assert any(t.name == "delete_tags" for t in mgr.task_queue._fast)
        mgr.task_queue = TaskQueue()
        mgr.events.emit("queue_rebuilt")
        assert any(t.name == "delete_tags" for t in mgr.task_queue._fast)


def test_p3_modules_sections_claims():
    """三模块 sections 认领清单锁定(maintenance 六段: P6 补登 hr/remove_similar_tags)"""
    assert TrackerModule(None).sections() == ("trackers", )
    assert SpeedCurveModule(None).sections() == ("global_speed_limit_curve", )
    assert MaintenanceModule(None).sections() == (
        "delete_tags",
        "delete_tags_if_has_no_torrents",
        "add_episode_tags",
        "maintenance_tag_mode",
        "remove_similar_tags",
        "hr",
    )


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def test_p2a_maintenance_added_event_unknown_hash_noop():
    """维护 added 事件: hash 不在快照(已删除) -> 直接返回零动作"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        maintenance = mgr.host.get("maintenance")
        maintenance._on_torrent_added(SimpleNamespace(payload={"hash": "GHOST", "dry_run": False}))
        assert mgr.client.calls == []


def test_p2a_maintenance_register_global_tasks_without_queue():
    """全局任务自注册: 队列引用为 None(L2 重建间隙) -> 直接返回; 恢复队列后按配置入队"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.config.delete_tags = ["old.*"]
        maintenance = mgr.host.get("maintenance")
        mgr.ctx.task_queue = None
        maintenance._register_global_tasks(mgr.ctx)  # 不崩溃, 无处入队
        assert mgr.task_queue is None
        mgr.ctx.task_queue = TaskQueue()
        maintenance._register_global_tasks(mgr.ctx)
        assert mgr.task_queue.has_named("delete_tags"), "队列恢复后按配置入队"


def test_p2a_maintenance_task_interface_delegates():
    """task 接口委托: handle_maintenance_task_interface 经 task.torrent 走到 handle_maintenance"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        tor = FakeTorrent(hash="H1", state="stalledUP")
        seed_store(mgr, [tor])
        rec = mgr.store.get("H1")
        rec.tracker_conf = mgr.config.trackers["HHan"]  # 维护读 conf.tags/remove_tags/hr
        task = Task("rule", "rule-test", hash="H1", store=mgr.store)
        result = mgr.host.get("maintenance").handle_maintenance_task_interface(task, dry_run=True)
        assert result is REQUEUE, f"维护任务返回 REQUEUE 语义: {result!r}"


def test_p2a_maintenance_remove_tags_dry_run_and_similar_paths():
    """remove_tags dry-run 命中不打 API; remove_similar_tags dry-run 命中不打 API / 不相似返回 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        maintenance = mgr.host.get("maintenance")
        tor = FakeTorrent(hash="H1", state="stalledUP", tags="ztag")
        assert maintenance.remove_tags(tor, ["ztag"], dry_run=True) is True
        assert mgr.client.calls == [], "dry-run 不打 API"
        tor2 = FakeTorrent(hash="H2", state="stalledUP", tags="ZTag")
        assert maintenance.remove_similar_tags(tor2, ["ztag"], dry_run=True) is True
        assert mgr.client.calls == [], "dry-run 不打 API"
        tor3 = FakeTorrent(hash="H3", state="stalledUP", tags="other")
        assert maintenance.remove_similar_tags(tor3, ["ztag"], dry_run=False) is False, "无相似标签: False"


def test_p2a_maintenance_add_episode_tags_no_episodes():
    """集数标签: 文件列表解析不出集数(电影/合集) -> 不加标签"""
    from auto_qb.config import AddEpisodeTagsConfig

    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.client.files = []  # 无文件
        mgr.config.add_episode_tags = AddEpisodeTagsConfig(enabled=True)
        tor = FakeTorrent(hash="H1", state="stalledUP")
        mgr.host.get("maintenance").add_episode_tags(tor, dry_run=False)
        assert not any(c[0] == "add_tags" for c in mgr.client.calls), "无集数不加标签"


def test_p2a_maintenance_create_category_existing_noop():
    """创建分类: 分类定义已存在 -> 不重复创建"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.client.torrents_categories = lambda: {"CAT": {"savePath": ""}}
        mgr.host.get("maintenance").create_category_if_not_exists("CAT", dry_run=False)
        assert not any(c[0] == "create_category" for c in mgr.client.calls)


def test_p2a_maintenance_delete_unused_tags_dry_run():
    """彻底删除无种子的标签: dry-run 命中但不打 API, 仍 REQUEUE 常驻"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.client.torrents_tags = lambda: {"unusedTag"}
        mgr.config.delete_tags_if_has_no_torrents = ["unusedTag"]
        result = mgr.host.get("maintenance").handle_delete_tags_if_has_no_torrents(object(), dry_run=True)
        assert result is REQUEUE
        assert not any(c[0] == "delete_tags" for c in mgr.client.calls), "dry-run 不打 API"


def test_p2a_tracker_added_event_unknown_hash_noop():
    """tracker added 事件: hash 不在快照 -> 直接返回(不匹配不限速)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.ctx.trackers._on_torrent_added(SimpleNamespace(payload={"hash": "GHOST", "dry_run": False}))
        assert not any(c[0].startswith("set_") for c in mgr.client.calls)

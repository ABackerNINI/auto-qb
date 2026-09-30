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
4. 流量快照发布走 ctx.web.set_traffic_view 服务方法(manager._traffic_view 别名同源可见);
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
"""
import os
import tempfile
from unittest import mock

from auto_qb.core.modules import MaintenanceModule, SpeedCurveModule, TrackerModule
from auto_qb.core.taskqueue import TaskQueue
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
        assert n == 1, "恰好 tracker 模块订阅 full_round"
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
    """_publish_traffic 经 ctx.web.set_traffic_view 发布; manager._traffic_view 别名同源可见"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        with mock.patch.object(mgr.web, "set_traffic_view", wraps=mgr.web.set_traffic_view) as pub:
            mgr.host.get("speed_curve")._publish_traffic("ok", periods=[{"period": "day"}], target={"up": 1, "down": 2})
        assert pub.call_count == 1
        view = mgr._traffic_view  # 旧名别名 -> self.web.traffic_view(同一份)
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

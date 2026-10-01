"""test_modules_p5 测试计划: rules 模块化 + 刷新管线收口(plan kernel-module-refactor P5)

P5 是「最大一刀」: RuleEngineMixin 迁 RulesModule, _dispatch_events 改走 EventBus 相位
(plan §4.2 相位表生效), _refresh_torrents 收口为「同步 + 相位广播」, L2 重建收进
rules.apply(W3), 级别分派层与三张手写表退役(W4)。规则行为本身的端到端覆盖仍在
test_rule_engine / test_trigger_events / test_rules_core(经同一刷新路径驱动); 本文件锁:

## 测试计划(每个测试函数一条)
- test_p5_modules_sections_claims: rules/tracker/maintenance 的 sections 认领锁定
- test_kernel_does_not_import_business_packages: 内核不再 import rules 业务包(§3.1 判据)
- test_phase_subscription_map: 事件两相位恰 rules 一家; torrents_added 四家按装配序
- test_refresh_phase_order_matches_plan_table: 刷新轮相位广播顺序 == plan §4.2 相位表
- test_torrents_added_pipeline_order: 逐种子管线四家按装配序(限速→维护→归组→建任务)
- test_suppress_window_covers_only_event_phases: 重放保护窗口只覆盖两个事件相位
- test_suppression_request_survives_failed_round: 失败轮不丢重放保护请求(审计 M1, 消费点贴挂旗标处)
- test_rules_apply_rebuild_on_section_change: L2 重建收进 rules.apply(整段短路 + 段变重建)
- test_rebuild_needed_matrix_each_criterion_alone_triggers_rebuild: 判据矩阵(审计 M2): 六判据段/三元组逐成员/trackers 增删各自单独变更必触发重建
- test_rebuild_needed_matrix_tracker_runtime_fields_do_not_rebuild: 判据矩阵负例(审计 M2): tracker 运行时现读字段变化不重建(过度重启族防线)
- test_rebuild_within_window_still_delivers_queue_rebuilt: 抑制窗内二次重建 queue_rebuilt 不被吞(issue 26-10-01-0750)
- test_rebuild_preserves_runtime_memory_state: 重建不重读磁盘, exec_history 原对象保留
- test_rebuild_benchmark_5000_seeds: 5000 种子下短路/重建耗时实测(数字入档任务档案)
"""
import os
import tempfile
import time
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb.core.modules import maintenance_mod, rules_mod, tracker_mod
from auto_qb.core.taskqueue import TaskQueue
from helpers import FakeClient, FakeTracker, FakeTorrent, make_manager, seed_store


def _mgr(td):
    return make_manager(os.path.join(td, "state.json"))


def _recorder(order, label):
    def rec(event):
        order.append(label)

    return rec


# ============================================================
# 契约与接线
# ============================================================
def test_p5_modules_sections_claims():
    """P5 相关模块的 sections 认领锁定: rules 两段(重建判据), tracker 不变;
    maintenance 六段(P6 补登 hr/remove_similar_tags, 见 maintenance_mod.sections 注)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        assert mgr.host.get("rules").sections() == ("rules_config", "interval")
        assert mgr.host.get("tracker").sections() == ("trackers", )
        assert mgr.host.get("maintenance").sections() == (
            "delete_tags",
            "delete_tags_if_has_no_torrents",
            "add_episode_tags",
            "maintenance_tag_mode",
            "remove_similar_tags",
            "hr",
        )


def test_kernel_does_not_import_business_packages():
    """内核不再 import rules 业务包(plan §3.1 判据: 「内核不知道何事」可用 AST 验证)

    装配清单经 core.modules 导入模块类(内核知道模块名字, plan §3.3 允许); 业务包
    (rules/...)的 import 必须为零 —— QbManager 的 import 语句逐条核对。
    """
    import ast
    import inspect

    import auto_qb.core.qbmanager as qbm

    tree = ast.parse(inspect.getsource(qbm))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("rules"), f"内核不得 import rules 业务包: line {node.lineno}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("rules"), f"内核不得 import rules 业务包: line {node.lineno}"


def test_phase_subscription_map():
    """事件两相位(events_removed/events_added)恰 rules 一家; torrents_added 四家按装配序

    §4.2 相位表的认领面: torrents_added = tracker → maintenance → grouping → rules
    (装配序 = 相位内消费序, plan §3.3)。组上下文等行为归各自模块测试。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        handlers = mgr.events._handlers
        assert [h.__self__.name for h in handlers.get("events_removed", [])] == ["rules"]
        assert [h.__self__.name for h in handlers.get("events_added", [])] == ["rules"]
        assert [h.__self__.name
                for h in handlers.get("torrents_added", [])] == ["tracker", "maintenance", "grouping", "rules"]


# ============================================================
# 相位顺序(plan §4.2 相位表)
# ============================================================
def test_refresh_phase_order_matches_plan_table():
    """刷新轮的相位广播顺序 == §4.2 相位表(全量轮: full_round 先于 transitions 等)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        order = []
        for phase in (
            "full_round", "transitions", "events_removed", "events_added", "torrents_added", "removed_scan", "post"
        ):
            mgr.events.on(phase, _recorder(order, phase))
        tor1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        tor2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = tor1
        client.torrents["H2"] = tor2
        mgr._refresh_torrents()
        # 全量轮: 重匹配 -> 状态转移 -> 删除事件分派 -> 新增事件分派 -> 逐种子管线×2 -> post
        # (首轮无删除, removed_scan 不发; 两种子各广播一次 torrents_added)
        assert order == [
            "full_round",
            "transitions",
            "events_removed",
            "events_added",
            "torrents_added",
            "torrents_added",
            "post",
        ], order

        # 第二轮(FakeClient 增量语义: rid 未失效, 只报 torrents_removed): 无全量轮、
        # 无 added 家族相位; removed_scan 在 post 之前
        order.clear()
        client.torrents.clear()
        mgr._refresh_torrents()
        assert order == ["transitions", "events_removed", "removed_scan", "post"], order


def test_torrents_added_pipeline_order():
    """逐种子管线按装配序: 限速(tracker) -> 维护(maintenance) -> 归组(grouping) -> 建任务(rules)

    §4.2 相位表「维护→限速→建任务→归组→集数」的忠实编码受装配序约束(plan §3.3 装配序
    = 相位内消费序), 相位内次序为 §4.2 认领清单的装配序实现 —— 数据互不依赖
    (各步只读 tracker_conf/store/config), 次序约束在此锁定, 变更必须是有意行为。
    集数标签与维护同属 maintenance, 在其单订阅内紧随维护执行(见 maintenance_mod._on_torrent_added)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        order = []
        patches = [
            mock.patch.object(
                tracker_mod.TrackerModule, "apply_speed_limit", side_effect=lambda *a, **k: order.append("limit")
            ),
            mock.patch.object(
                maintenance_mod.MaintenanceModule,
                "handle_maintenance",
                side_effect=lambda *a, **k: order.append("maintain")
            ),
            mock.patch.object(
                maintenance_mod.MaintenanceModule,
                "add_episode_tags",
                side_effect=lambda *a, **k: order.append("episodes")
            ),
            mock.patch.object(
                mgr.host.get("grouping").__class__,
                "_assign_new_torrent",
                side_effect=lambda *a, **k: order.append("group")
            ),
            mock.patch.object(
                rules_mod.RulesModule, "_create_torrent_tasks", side_effect=lambda *a, **k: order.append("tasks")
            ),
        ]
        for p in patches:
            p.start()
        try:
            mgr.config.add_episode_tags.enabled = True  # 集数一步启用(默认关)
            mgr.config.grouping.enabled = True  # 归组一步启用(默认关)
            tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
            client = FakeClient()
            mgr.client = client
            client.torrents["H1"] = tor
            mgr._refresh_torrents()
        finally:
            for p in patches:
                p.stop()
        assert order == ["limit", "maintain", "episodes", "group", "tasks"], order


# ============================================================
# 事件重放保护窗口(plan §4.3: 总线 suppress 只覆盖两个事件相位)
# ============================================================
def test_suppress_window_covers_only_event_phases():
    """L2 置位的重放保护: 同轮 full_round/transitions/torrents_added/post 照常广播,
    仅 events_removed / events_added 被抑制一轮 —— 与原 _suppress_events 只闸
    _dispatch_events 两个调用点的语义等价(plan §7.1 不变量)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@event_rules"])
        mgr.config.rules_config = {
            "event_rules":
                {
                    "r1": {
                        "enabled": True,
                        "trigger": "on_torrent_added",
                        "actions": [{
                            "add_tags": ["event-tag"]
                        }],
                    }
                }
        }
        mgr.host.get("rules").load_rules()
        order = []
        for phase in ("full_round", "transitions", "events_removed", "events_added", "torrents_added", "post"):
            mgr.events.on(phase, _recorder(order, phase))

        def _round(h):
            tor = FakeTorrent(hash=h, name=h, state="stalledUP", tags="")
            client = FakeClient()
            mgr.client = client
            client.torrents[h] = tor
            mgr._refresh_torrents()
            return client

        # 首轮(无抑制): 事件分派照常
        client = _round("HA")
        assert ("add_tags", ["event-tag"]) in client.calls
        assert order == ["full_round", "transitions", "events_removed", "events_added", "torrents_added", "post"]

        # 模拟 rules L2 重建挂请求(plan §4.3): 下轮事件分派被抑制(订阅者不被调用),
        # 其余相位照常广播 —— full_round/transitions/torrents_added/post 都在序
        order.clear()
        mgr.events.request_suppression()
        client = _round("HB")
        assert order == ["full_round", "transitions", "torrents_added", "post"], (f"窗口只覆盖两个事件相位, 其余照常: {order}")
        assert ("add_tags", ["event-tag"]) not in client.calls, "抑制期内 added 事件规则不得触发(重放保护)"
        # 窗口在轮内关闭: 下轮事件分派恢复
        order.clear()
        client = _round("HC")
        assert ("add_tags", ["event-tag"]) in client.calls, "抑制仅一轮(窗口随轮关闭)"


def test_suppression_request_survives_failed_round():
    """失败轮不丢重放保护请求(审计 M1): 请求位消费点必须贴着挂旗标处(events_removed 相位前)

    轮首消费时, 重建挂请求后的首轮刷新若在 apply_sync 抛异常(qB 连接抖动), 请求位已被
    读走而 live 旗标未挂 —— 下一轮全量同步(rid 已失效)把全部存量种子判为 added,
    on_torrent_added 事件规则对全库重放。消费点在 events_removed 相位前(take 即 arm),
    失败轮不消费, 抑制跨失败轮存活到下一个成功轮(原 _suppress_events 语义)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@event_rules"])
        mgr.config.rules_config = {
            "event_rules":
                {
                    "r1": {
                        "enabled": True,
                        "trigger": "on_torrent_added",
                        "actions": [{
                            "add_tags": ["event-tag"]
                        }],
                    }
                }
        }
        mgr.host.get("rules").load_rules()
        order = []
        for phase in ("full_round", "transitions", "events_removed", "events_added", "torrents_added", "post"):
            mgr.events.on(phase, _recorder(order, phase))

        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = tor
        mgr.events.request_suppression()  # L2 重建挂请求

        # 首轮刷新在 apply_sync 抛异常(qB 连接抖动): 请求位不得被消费
        with mock.patch.object(mgr.store, "apply_sync", side_effect=RuntimeError("qB 连接抖动")):
            with pytest.raises(RuntimeError, match="qB 连接抖动"):
                mgr._refresh_torrents()
        assert mgr.events.replay_requested, "失败轮不得消费重放保护请求(审计 M1)"
        assert not mgr.events.suppressed, "失败轮不得开启抑制窗口"

        # 下一个成功轮(全量, 存量种子判 added): added 事件规则被抑制, 其余相位照常
        order.clear()
        client.calls.clear()
        mgr._refresh_torrents()
        assert ("add_tags", ["event-tag"]) not in client.calls, "成功轮 added 事件规则必须被抑制(重放保护, 审计 M1)"
        assert order == ["full_round", "transitions", "torrents_added", "post"], (f"窗口只覆盖两个事件相位: {order}")
        assert not mgr.events.replay_requested, "请求位随成功轮消费(take 即 arm)"


# ============================================================
# L2 重建收进 rules.apply(W3) + 内存态保留
# ============================================================
def test_rules_apply_rebuild_on_section_change():
    """rules.apply: 判据段整段相等即短路; interval 变化触发重建(队列/规则/重连/抑制)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        seed_store(mgr, [tor])

        old = mgr.config
        new = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers"
        ):
            setattr(new, attr, getattr(old, attr))
        new.interval = old.interval
        assert rules.apply(old, new).action == "none", "判据段整段相等必须短路(W4: 无级别表兜底)"

        # interval 变化 -> 重建: 队列换新 / conf 置空 / 规则重载 / 抑制置位 / 重连
        rebuilt = []
        mgr.events.on("queue_rebuilt", lambda e: rebuilt.append(1))
        mgr.connect = mock.MagicMock(return_value=True)
        queue_before = mgr.task_queue
        new = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers"
        ):
            setattr(new, attr, getattr(old, attr))
        new.interval = 999.0
        res = rules.apply(old, new)
        assert res.action == "rebuilt"
        assert mgr.task_queue is not queue_before and isinstance(mgr.task_queue, TaskQueue)
        assert mgr.store.get("H1").tracker_conf is None, "reset_runtime 契约: conf 置空待 full_round 重匹配"
        assert rebuilt, "queue_rebuilt 相位应广播(全局任务各模块自注册重入队)"
        assert mgr.events.replay_requested, "重建应挂事件重放保护请求位(窗口协议见 EventBus)"
        assert not mgr.events.suppressed, "挂请求不得置 live 旗标(窗口内相位照常送达, issue 26-10-01-0750)"
        mgr.connect.assert_called_once(), "重建尾段重连(rid 失效 -> 下轮全量)"


# ============================================================
# L2 重建判据矩阵(审计 26-10-01-0918 M2: 六判据此前只有 interval 被单测单独触发, 漏任一成员守阵全绿)
# ============================================================
_REBUILD_SECTIONS = (
    "rules_config",
    "interval",
    "delete_tags",
    "delete_tags_if_has_no_torrents",
    "global_speed_limit_curve",
    "trackers",
)


def _new_cfg_like(old):
    """矩阵用例的 new 配置替身: 六判据段全部与 old 同对象, 用例在此之上只动一段"""
    new = mock.MagicMock()
    for attr in _REBUILD_SECTIONS:
        setattr(new, attr, getattr(old, attr))
    return new


def _tracker_variant(old_t, changed):
    """old_t 的替身 tracker: 三元组(domains/rules/groups)同构拷贝, 仅 changed 成员换新值"""
    t = FakeTracker(old_t.name, hr=old_t.hr, rules=list(old_t.rules), groups=list(old_t.groups))
    t.domains = list(old_t.domains)
    if changed == "domains":
        t.domains = ["matrix.example.net"]
    elif changed == "rules":
        t.rules = ["@example_rules.add_site_tag"]
    elif changed == "groups":
        t.groups = ["matrix_group"]
    return t


@pytest.mark.parametrize(
    "criterion",
    [
        "rules_config",
        "interval",
        "delete_tags",
        "delete_tags_if_has_no_torrents",
        "global_speed_limit_curve",
        "trackers.domains",
        "trackers.rules",
        "trackers.groups",
        "trackers.added",
        "trackers.removed",
    ],
)
def test_rebuild_needed_matrix_each_criterion_alone_triggers_rebuild(criterion):
    """_rebuild_needed 判据矩阵(审计 M2): 判据段逐段单独变更必须触发 L2 重建

    「该重建不重建」是计划点名的热重载四失效族之一 —— 矩阵把漏判从靠人眼变成靠守阵。
    trackers 判据按 _tracker_bindings_changed 的三元组逐成员 + 增删各一例; 重建副作用
    (队列换新/conf 置空/抑制请求位/重连)由 test_rules_apply_rebuild_on_section_change 的
    interval 例承担, 此处只断言判定本身。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        old = mgr.config
        new = _new_cfg_like(old)

        if criterion == "rules_config":
            new.rules_config = {**old.rules_config, "matrix_group": dict(old.rules_config["example_rules"])}
        elif criterion == "interval":
            new.interval = old.interval + 1
        elif criterion == "delete_tags":
            new.delete_tags = ["matrixDelete"]
        elif criterion == "delete_tags_if_has_no_torrents":
            new.delete_tags_if_has_no_torrents = ["matrixEmpty"]
        elif criterion == "global_speed_limit_curve":
            new.global_speed_limit_curve = [("00:00", 10240)]  # 判据只做段级不等比较, 替身无需全型
        elif criterion in ("trackers.domains", "trackers.rules", "trackers.groups"):
            new.trackers = {"HHan": _tracker_variant(old.trackers["HHan"], criterion.split(".")[1])}
        elif criterion == "trackers.added":
            new.trackers = {**old.trackers, "NEW": _tracker_variant(old.trackers["HHan"], None)}
        elif criterion == "trackers.removed":
            new.trackers = {}
        else:
            raise AssertionError(f"未知判据: {criterion}")

        mgr.connect = mock.MagicMock(return_value=True)  # rebuild_runtime 尾段重连, 不真连
        assert rules.apply(old, new).action == "rebuilt", f"判据段 {criterion} 单独变更必须触发 L2 重建"


def test_rebuild_needed_matrix_tracker_runtime_fields_do_not_rebuild():
    """判据矩阵负例(审计 M2): tracker 三元组外的运行时现读字段变化不得触发重建

    判据只看创建时固化的三元组(domains/rules/groups); tags/remove_tags/限速/hr_check
    运行时现读即生效(模块 docstring), 变化触发重建反而是过度重启族 + 丢运行态。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        rules = mgr.host.get("rules")
        old = mgr.config
        t = _tracker_variant(old.trackers["HHan"], None)
        t.tags = ["OTHER"]
        t.remove_tags = ["zGone"]
        t.remove_similar_tags = True
        t.upload_speed_limit = 1024
        t.download_speed_limit = 2048
        t.hr_check = SimpleNamespace(endpoint="matrix")
        new = _new_cfg_like(old)
        new.trackers = {"HHan": t}
        assert rules.apply(old, new).action == "none", "三元组外字段变化必须短路(过度重启族防线)"


def test_rebuild_within_window_still_delivers_queue_rebuilt():
    """抑制窗内二次重建: 首次重建挂的重放保护不得吞第二次重建的 queue_rebuilt(issue 26-10-01-0750)

    原实现 rebuild 置 live 旗标(emit 直接检查), 置位点到下轮轮首 take 之间所有相位一律
    被吞 —— 连续两次 L2 重建时第二次的 queue_rebuilt 丢失, 全局任务不重注册进新队列。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.config.delete_tags = ["issue-format"]  # 全局任务注册判据(夹具默认空 = 不注册)
        mgr.client = FakeClient()
        mgr.connect = mock.MagicMock(return_value=True)
        rebuilt = []
        mgr.events.on("queue_rebuilt", lambda e: rebuilt.append(1))
        rules = mgr.host.get("rules")

        rules.rebuild_runtime()  # 第一次重建: 挂重放保护请求(原实现置 live 旗标)
        rules.rebuild_runtime()  # 下轮轮首消费前第二次重建: queue_rebuilt 不得被吞

        assert len(rebuilt) == 2, "抑制窗内二次重建的 queue_rebuilt 不得被吞(issue 26-10-01-0750)"
        assert mgr.task_queue.has_named("delete_tags"), "全局任务必须重注册进最后一次重建出的队列"


def test_rebuild_preserves_runtime_memory_state():
    """重建不重读磁盘 state: exec_history 等运行期内存态原对象保留(issue 26-09-21-1347)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.state.update({"exec_history": {"r1:abc": {"ts": 1.0}}, "skip_check_day": {"abc": "d"}})
        state_before = mgr.state
        with open(os.path.join(td, "state.json"), "w", encoding="utf-8") as f:
            import json
            json.dump({"stale_marker": True}, f)  # 磁盘旧版
        mgr.client = FakeClient()
        mgr.connect = mock.MagicMock(return_value=True)
        mgr.host.get("rules").rebuild_runtime()
        assert mgr.state is state_before, "state 载荷对象不得被替换(重读磁盘 = 回滚)"
        assert mgr.state["exec_history"] == {"r1:abc": {"ts": 1.0}}


# ============================================================
# 5000 种子模拟: 短路/重建耗时实测(W3 验收数字, 入档任务档案)
# ============================================================
def test_rebuild_benchmark_5000_seeds(capsys):
    """5000 种子下: 整段短路 apply 耗时 vs L2 重建耗时(实测入档, 不做脆弱的时间断言)

    场景即 W3 验收口径: 热重载保存时「零规则相关变更」应接近零成本(短路), 「规则变更」
    的重建一次性成本应可接受(队列重建 + conf 置空 + 规则重载, 不含 API 调用)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        mgr.connect = mock.MagicMock(return_value=True)
        # 5000 条轻量记录(reset_runtime 只触碰 tracker_conf 等运行态字段)
        conf = mgr.config.trackers["HHan"]
        mgr.store.by_hash = {f"{i:032x}": SimpleNamespace(hash=f"{i:032x}", tracker_conf=conf) for i in range(5000)}
        rules = mgr.host.get("rules")
        old = mgr.config
        new = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers",
            "interval"
        ):
            setattr(new, attr, getattr(old, attr))
        t0 = time.perf_counter()
        assert rules.apply(old, new).action == "none"
        t_short = time.perf_counter() - t0

        new2 = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers"
        ):
            setattr(new2, attr, getattr(old, attr))
        new2.interval = 888.0
        t0 = time.perf_counter()
        assert rules.apply(old, new2).action == "rebuilt"
        t_rebuild = time.perf_counter() - t0
        out = (f"[5000-seed benchmark] short-circuit={t_short * 1000:.2f}ms "
               f"rebuild={t_rebuild * 1000:.2f}ms")
        print(out)
        capsys.readouterr()  # 数字入档由任务档案记录, 不做脆弱断言
        assert t_short < 1.0, "短路路径必须近似零成本(整段相等直接返回)"
        assert t_rebuild < 30.0, "重建在 5000 种子下必须完成(纯内存操作, 无 API)"

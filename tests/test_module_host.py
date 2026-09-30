"""内核地基守阵(plan kernel-module-refactor P0): ctx 服务同对象 / 委托面 / ModuleHost / EventBus

P0 是纯加法(契约 + 状态服务 + ctx 接线), 本文件锁住三件事:
1. ctx 是单一真相 —— manager 同名属性与 ctx 服务是**同一对象**(属性委托不得造出第二份真相);
2. 状态持久化迁 StateService 后, 旧调用面(load/save/flush/record)语义与接线位置原样;
3. ModuleHost / EventBus 骨架的编排语义(装配序 / 逆序停用 / 无条件 apply / 注册序分发 /
   总线级 suppress), P1 起模块挂入前先立规矩。

## 测试计划
- test_ctx_services_are_same_objects: ctx.store/api/config 与 manager 同名属性同对象; state 是服务的 data
- test_state_dict_identity_survives_reassignment: mgr.state 整体替换后 ctx.state.data 仍是同一对象, 基线重绑生效
- test_config_replace_via_delegation: 整对象替换 config 经委托落 ctx(热重载 L0 语义的接线前提)
- test_manager_state_delegate_roundtrip: record_execution/get_exec_record 经委托走 ctx.state(旧调用面不变)
- test_state_service_roundtrip_standalone: 服务独立构造: 空->写入->落盘->重读带 schema 版本章
- test_maybe_flush_via_service: 周期落盘到期触发/间隔内不重复/interval=0 关闭(语义与迁移前一致)
- test_module_host_register_order_and_dup_fail_fast: 注册保序; 无名/重名 fail-fast
- test_module_host_register_invokes_subscribe: 装配点回调 subscribe, 相位认领发生在注册时
- test_module_host_lifecycle_order: start_all/apply_all 装配序, stop_all 逆序
- test_module_host_loop_hooks_skipped_when_absent: loop hooks 有则按装配序调用, 无则跳过
- test_eventbus_registration_order_and_suppress: emit 按注册序同步分发; 抑制期零调用; 解除后恢复
"""
import json
import os
import tempfile

import pytest

from auto_qb.core.module import ApplyResult, BaseModule, EventBus, ModuleHost
from auto_qb.core.state import StateService
from auto_qb.infra import versioning
from helpers import make_manager

STATE_V = versioning.CURRENT_VERSIONS["state"]

# ---------- ctx 同对象守阵(P0 指定守阵) ----------


def test_ctx_services_are_same_objects():
    """ctx.store/api/config 与 manager 同名属性必须是同一对象; state 是服务的 data dict"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr.ctx.store is mgr.store, "ctx.store 与 manager.store 必须同对象(属性委托不得复制)"
        assert mgr.ctx.api is mgr.api, "ctx.api 与 manager.api 必须同对象"
        assert mgr.ctx.config is mgr.config, "ctx.config 与 manager.config 必须同对象"
        assert mgr.ctx.state.data is mgr.state, "manager.state 是 ctx.state 服务载荷本身(同一 dict)"
        assert mgr.ctx.state.state_file == mgr.state_file
        # 宿主与总线挂在内核侧, 指向同一 ctx; 装配清单随 P1(基建两模块)与 P2(门面转正)推进
        assert [m.name for m in mgr.host.modules()] == ["logging", "notify", "webui", "hr"]
        assert mgr.ctx.notify is mgr.host.get("notify"), "托盘经 ctx.notify 调公开方法(单一真相)"


def test_state_dict_identity_survives_reassignment():
    """mgr.state = {...} 整体替换后 ctx.state.data 仍是同一对象, 且字段基线重绑生效"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        new_state = {"exec_history": {"r:h": {"ts": 1.0}}}
        mgr.state = new_state
        assert mgr.ctx.state.data is new_state
        mgr._bind_field_snapshots()
        assert mgr.store.field_snapshots is new_state["field_snapshots"], "基线必须重绑到新 state 顶层键"


def test_config_replace_via_delegation():
    """整对象替换 config 经委托落 ctx(热重载 L0「替换 Config 对象」的接线前提)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        from helpers import FakeConfig

        other = FakeConfig()
        mgr.config = other
        assert mgr.ctx.config is other and mgr.config is other


def test_manager_state_delegate_roundtrip():
    """record_execution/get_exec_record 经委托走 ctx.state —— 规则侧旧调用面(manager.*)不变"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.record_execution("example_rules.add_site_tag", "HASH1")
        rec = mgr.get_exec_record("example_rules.add_site_tag", "HASH1")
        assert rec is not None and "ts" in rec
        assert "example_rules.add_site_tag:HASH1" in mgr.state["exec_history"], "历史落在同一份 state dict 上"
        assert mgr.get_exec_record("nope", "nope") is None


# ---------- StateService(迁移自 RuleEngineMixin, 语义原样) ----------


def test_state_service_roundtrip_standalone():
    """服务不依赖 manager 可独立构造: 写入->落盘->重读; 载荷带 schema 版本章"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "state.json")
        svc = StateService(path)
        assert svc.load() == {}, "首启静默返回空"
        svc.data["exec_history"] = {"r:h": {"ts": 1.0}}
        svc.save()
        raw = json.loads(open(path, encoding="utf-8").read())
        assert raw["schema_version"] == STATE_V, "落盘载荷必须盖 schema_version 章"
        svc2 = StateService(path)
        assert svc2.load() == {"exec_history": {"r:h": {"ts": 1.0}}, "schema_version": STATE_V}


def test_maybe_flush_via_service():
    """周期落盘语义原样: 到期触发并推进到期点 / 间隔内不重复 / interval=0 关闭"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "state.json")
        svc = StateService(path)
        svc.data["k"] = 1
        svc.maybe_flush(100.0, 30.0)  # 到期点初始为 0 -> 首调即落盘
        assert os.path.exists(path)
        assert svc.next_flush_at == 130.0
        os.remove(path)
        svc.maybe_flush(120.0, 30.0)  # 间隔内: 不重复落盘
        assert not os.path.exists(path)
        svc.maybe_flush(100.0, 0)  # interval=0: 关闭(旧行为逃生口)
        assert not os.path.exists(path)


# ---------- ModuleHost 骨架 ----------


class _Recorder(BaseModule):
    """记录生命周期调用序的假模块(守阵用, 不含业务)"""
    def __init__(self, name, log, apply_action="none"):
        self.name = name
        self._log = log
        self._apply_action = apply_action
        self.subscribed = None
        self.sync_forced = None
        self.task_forced = None

    def sections(self):
        return (self.name, )

    def start(self, ctx, dry_run):
        self._log.append(f"start:{self.name}:{dry_run}")

    def stop(self):
        self._log.append(f"stop:{self.name}")

    def apply(self, old, new):
        self._log.append(f"apply:{self.name}")
        return ApplyResult(self.name, self._apply_action)

    def subscribe(self, phases):
        self.subscribed = phases
        self._log.append(f"subscribe:{self.name}")


def _host_with(log, names):
    ctx_events = EventBus()
    host = ModuleHost(object(), ctx_events)  # ctx 在宿主编排测试里不被消费
    mods = [_Recorder(n, log) for n in names]
    for m in mods:
        host.register(m)
    return host, mods, ctx_events


def test_module_host_register_order_and_dup_fail_fast():
    """注册保序(装配序 = 相位内消费序 = 生命周期序); 无名 / 重名 fail-fast"""
    log = []
    host, mods, _ = _host_with(log, ["a", "b", "c"])
    assert [m.name for m in host.modules()] == ["a", "b", "c"]
    assert host.get("b") is mods[1] and host.get("zzz") is None
    with pytest.raises(ValueError):
        host.register(_Recorder("b", log))
    anon = _Recorder("", log)
    with pytest.raises(ValueError):
        host.register(anon)


def test_module_host_register_invokes_subscribe():
    """装配点即相位认领点: register 回调 subscribe 并传入同一条事件总线"""
    log = []
    host, mods, bus = _host_with(log, ["a"])
    assert mods[0].subscribed is bus, "subscribe 拿到的必须是宿主那条 EventBus"


def test_module_host_lifecycle_order():
    """start/apply 按装配序, stop 按装配逆序; apply 无条件逐个调用(统一挂载口语义)"""
    log = []
    host, _, _ = _host_with(log, ["a", "b"])
    host.start_all(dry_run=False)
    host.apply_all(object(), object())
    host.stop_all()
    assert log == [
        "subscribe:a", "subscribe:b", "start:a:False", "start:b:False", "apply:a", "apply:b", "stop:b", "stop:a"
    ]


def test_module_host_loop_hooks_skipped_when_absent():
    """loop hooks: 有则按装配序调用并聚合返回值, 无则跳过(BaseModule 不默认提供)"""
    log = []

    class WithHooks(BaseModule):
        name = "hooked"

        def __init__(self):
            self.outer = log

        def on_command_line(self):
            self.outer.append("cmd:hooked")
            return True

        def on_sync_line(self, force):
            self.outer.append(f"sync:hooked:{force}")

    plain = _Recorder("plain", log)
    host = ModuleHost(object(), EventBus())
    host.register(plain)
    host.register(WithHooks())
    assert host.run_command_line() is True, "任一模块改了 qB 状态 -> True"
    host.run_sync_line(force=True)
    host.run_task_line(force=False)
    assert log == [
        "subscribe:plain",
        "cmd:hooked",
        "sync:hooked:True",
    ], "plain 无 hooks 必须被跳过; task hook 缺失不报错"


# ---------- EventBus 骨架 ----------


def test_eventbus_registration_order_and_suppress():
    """emit 按注册序同步分发并返回触发数; 抑制期零调用, 解除后恢复"""
    bus = EventBus()
    seen = []
    bus.on("transitions", lambda e: seen.append(("first", e.phase, e.payload)))
    bus.on("transitions", lambda e: seen.append(("second", e.phase, e.payload)))
    bus.on("full_round", lambda e: seen.append(("other", e.phase, e.payload)))
    n = bus.emit("transitions", {"h": "abc"})
    assert n == 2 and [s[0] for s in seen] == ["first", "second"], "同相位按注册序同步分发"
    assert seen[0][2] == {"h": "abc"} and seen[1][1] == "transitions"
    bus.set_suppressed(True)
    assert bus.suppressed and bus.emit("transitions") == 0, "抑制期: added 重放保护, 零调用"
    assert len(seen) == 2
    bus.set_suppressed(False)
    assert bus.emit("transitions", {}) == 2, "解除后恢复分发"

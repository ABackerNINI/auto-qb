"""基建模块守阵(plan kernel-module-refactor P1): LoggingModule / NotifyModule 契约样板

P1 内容: 契约样板(sections 认领 + apply 整段短路) / run() 启动接线改经模块 /
热重载 L1 的手工重挂改 host.apply 广播(影子并行: L1 分支暂留 qb 重连 + web 重启) /
托盘 4 处 manager._notify_handler 直写改 ctx.notify 公开方法。本文件锁四件事:
1. 两个基建模块的契约语义(start 幂等 / apply 段相等短路 / 段变重挂);
2. apply_new_config 的统一挂载口接线(每次热重载广播, 改 notify 段才重挂、无关保存零动作);
3. 托盘开关所依赖的模块公开 API 契约(enabled_state 三态 / set_enabled 翻转与会话级挂载);
4. 外围私有面清零(托盘/内核源码零 _notify_handler 直写)。

## 测试计划
- test_logging_module_start_configures_once: start 建日志且幂等(重复 start 零动作)
- test_logging_module_apply_short_circuit_and_remount: 段相等短路 none; 段变重挂新配置
- test_notify_module_start_semantics: dry-run 不调挂载; start 无条件调 setup_notify(force=False, 未启用由其内部判 None); 重复 start 幂等
- test_notify_module_apply_remount: 段相等短路; 段变先摘旧再 force=True 重挂
- test_notify_module_tray_api: enabled_state 三态 / set_enabled 翻转与会话级挂载(托盘契约)
- test_apply_new_config_notify_remount_only_on_change: 改 notify 段才重挂, 无关保存零动作(P1 指定守阵)
- test_no_private_notify_access_from_outside: 托盘/内核源码零 manager._notify_handler 直写
"""
import copy
import inspect
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

from auto_qb.config import LoggingConfig, NotifyConfig
from auto_qb.config.impact import ConfigChange
from auto_qb.core.modules import LoggingModule, NotifyModule
from auto_qb.core.modules import logging_mod, notify_mod
from helpers import make_manager


def _ctx_with(logging_conf=None, notify_conf=None):
    """模块单测用的最小 ctx 替身(模块只消费 ctx.config 的对应段)"""
    config = SimpleNamespace()
    if logging_conf is not None:
        config.logging = logging_conf
    if notify_conf is not None:
        config.notify = notify_conf
    return SimpleNamespace(config=config)


# ---------- LoggingModule ----------


def test_logging_module_start_configures_once():
    calls = []
    conf = LoggingConfig(level="INFO", file="", max_bytes=1024, format="f")
    with mock.patch.object(logging_mod, "setup_logging", side_effect=lambda *a: calls.append(a)):
        mod = LoggingModule()
        ctx = _ctx_with(logging_conf=conf)
        mod.start(ctx, dry_run=True)  # dry_run 不影响日志(构造期即建, dry-run/导出模式也要)
        assert calls == [(conf.file, conf.level, conf.max_bytes, conf.format)]
        mod.start(ctx, dry_run=False)
        assert len(calls) == 1, "start 必须幂等: 重复初始化会清掉在用 handler 并重复启动行"


def test_logging_module_apply_short_circuit_and_remount():
    calls = []
    old = _ctx_with(logging_conf=LoggingConfig(level="INFO")).config
    new_same = _ctx_with(logging_conf=LoggingConfig(level="INFO")).config
    new_diff = _ctx_with(logging_conf=LoggingConfig(level="DEBUG")).config
    with mock.patch.object(logging_mod, "setup_logging", side_effect=lambda *a: calls.append(a)):
        mod = LoggingModule()
        mod.start(_ctx_with(logging_conf=old.logging), dry_run=False)
        res = mod.apply(old, new_same)
        assert res.module == "logging" and res.action == "none", "段整段相等必须短路(过度重启族防线)"
        assert len(calls) == 1, "短路 = 零重挂"
        res = mod.apply(old, new_diff)
        assert res.action == "remounted"
        assert len(calls) == 2 and calls[-1][1] == "DEBUG", "段变才按新配置重挂"


# ---------- NotifyModule ----------


def test_notify_module_start_semantics():
    with mock.patch.object(notify_mod, "setup_notify") as setup:
        ctx = _ctx_with(notify_conf=NotifyConfig(enabled=False))
        mod = NotifyModule(ctx)
        mod.start(ctx, dry_run=True)
        assert setup.call_count == 0, "dry-run 只打日志不挂通知(原 run() 调用点口径)"
        # 未启用也照常调用(原 run() 口径: 无条件调 setup_notify, 由它内部判 enabled 返回 None)
        mod.start(ctx, dry_run=False)
        assert setup.call_count == 1 and setup.call_args == mock.call(ctx.config.notify, force=False)
        enabled_ctx = _ctx_with(notify_conf=NotifyConfig(enabled=True))
        mod2 = NotifyModule(enabled_ctx)
        mod2.start(enabled_ctx, dry_run=False)
        setup.assert_called_with(enabled_ctx.config.notify, force=False)
        mod2.start(enabled_ctx, dry_run=False)
        assert setup.call_count == 2, "start 幂等: 已挂载不重复挂(否则双 handler 重复通知)"


def test_notify_module_apply_remount():
    with mock.patch.object(notify_mod, "setup_notify") as setup:
        handler = mock.MagicMock(name="handler")
        handler.enabled = True
        setup.return_value = handler
        old = _ctx_with(notify_conf=NotifyConfig(min_level="ERROR")).config
        new_same = _ctx_with(notify_conf=NotifyConfig(min_level="ERROR")).config
        new_diff = _ctx_with(notify_conf=NotifyConfig(min_level="WARNING")).config
        mod = NotifyModule(_ctx_with(notify_conf=old.notify))
        mod.start(_ctx_with(notify_conf=old.notify), dry_run=False)
        res = mod.apply(old, new_same)
        assert res.action == "none" and setup.call_count == 1, "段相等短路: 不摘不挂"
        res = mod.apply(old, new_diff)
        assert res.action == "remounted"
        assert setup.call_count == 2
        assert setup.call_args == mock.call(new_diff.notify, force=True), "重挂保留原 L1 语义: force=True(会话级)"
        assert mod.enabled_state() is True, "重挂后是新 handler(挂载即 enabled=True)"


def test_notify_module_tray_api():
    """托盘开关契约: enabled_state 三态 / set_enabled 翻转与会话级挂载(平台不支持异常上抛)"""
    with mock.patch.object(notify_mod, "setup_notify") as setup:
        handler = mock.MagicMock(name="handler")
        handler.enabled = True
        setup.return_value = handler
        ctx = _ctx_with(notify_conf=NotifyConfig())
        mod = NotifyModule(ctx)
        # 未挂载态(配置未启用且未会话挂载): 托盘按 None 区分, 不误同步开关
        assert mod.enabled_state() is None and mod.is_enabled() is False
        mod.set_enabled(False)
        setup.assert_not_called(), "未挂载 + 关 -> 无操作"
        # 会话级开启: force 挂载(重启后回到配置状态), 失败异常原样上抛由 UI 弹窗
        mod.set_enabled(True)
        setup.assert_called_once_with(ctx.config.notify, force=True)
        assert mod.enabled_state() is True
        # 已挂载: 翻转热开关(handler.enabled), 不重复挂载
        mod.set_enabled(False)
        assert handler.enabled is False and mod.enabled_state() is False and setup.call_count == 1
        mod.set_enabled(True)
        assert handler.enabled is True and mod.is_enabled() is True


# ---------- apply_new_config 接线(P1 指定守阵) ----------


def test_apply_new_config_notify_remount_only_on_change(monkeypatch):
    """改 notify 段才重挂, 无关保存零动作(统一挂载口: 每模块无条件 apply + 自判整段短路)

    变更判定由 config/impact 单测覆盖(与 test_apply_new_config_levels 同风格注入 diff),
    本守阵锁模块侧的决策与接线: old/new 段相等必须零动作, 段变恰好重挂一次。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.MagicMock(return_value=True)  # L1 分支的重连不真连
        notify_setup = mock.MagicMock(return_value=mock.MagicMock(enabled=True))
        logging_setup = mock.MagicMock()
        monkeypatch.setattr(notify_mod, "setup_notify", notify_setup)
        monkeypatch.setattr(logging_mod, "setup_logging", logging_setup)

        # 1. 仅 notify 段变化: 恰好重挂一次, 无关的 logging 段零动作
        new_cfg = copy.copy(mgr.config)
        new_cfg.notify = NotifyConfig(min_level="WARNING")
        monkeypatch.setattr(
            "auto_qb.config.impact.diff_config_impacts",
            lambda old, new: [ConfigChange("notify.min_level", "L1", "ERROR", "WARNING")],
        )
        res = mgr.apply_new_config(new_cfg)
        assert res["levels"] == ["L1"]
        assert notify_setup.call_count == 1, "改 notify 段 -> 重挂一次"
        assert mgr.ctx.notify.enabled_state() is True
        assert logging_setup.call_count == 0, "无关段(logging 未变)零动作 —— 过度重启族的模块化防线"

        # 2. 无关保存(main_tick, L0): 两模块都短路, 零重挂
        notify_setup.reset_mock()
        new_cfg2 = copy.copy(mgr.config)
        new_cfg2.main_tick = 9.9
        monkeypatch.setattr(
            "auto_qb.config.impact.diff_config_impacts",
            lambda old, new: [ConfigChange("main_tick", "L0", 2.0, 9.9)],
        )
        res = mgr.apply_new_config(new_cfg2)
        assert res["levels"] == ["L0"]
        notify_setup.assert_not_called()
        assert logging_setup.call_count == 0, "无关保存零动作(notify 段与 logging 段都未变)"

        # 3. 仅 logging 段变化: logging 重挂一次, notify 保持零动作
        new_cfg3 = copy.copy(mgr.config)
        new_cfg3.logging = LoggingConfig(level="DEBUG")
        monkeypatch.setattr(
            "auto_qb.config.impact.diff_config_impacts",
            lambda old, new: [ConfigChange("logging.level", "L1", "INFO", "DEBUG")],
        )
        res = mgr.apply_new_config(new_cfg3)
        assert res["levels"] == ["L1"]
        assert logging_setup.call_count == 1 and logging_setup.call_args[0][1] == "DEBUG"
        assert notify_setup.call_count == 0, "notify 段未变, 不得再重挂(计数已随第 2 轮清零)"


# ---------- 外围私有面清零 ----------


def test_no_private_notify_access_from_outside():
    """托盘 4 处 manager._notify_handler 直写改 ctx.notify 后, 私有字段访问必须保持清零"""
    import auto_qb.core.qbmanager as qbm
    import auto_qb.tray.app as tray_app

    tray_src = inspect.getsource(tray_app)
    assert "_notify_handler" not in tray_src, "托盘必须经 ctx.notify 公开方法(plan P1)"
    qm_src = inspect.getsource(qbm.QbManager)
    assert "_notify_handler" not in qm_src, "handler 归属 NotifyModule, 内核不再持有该私有字段"

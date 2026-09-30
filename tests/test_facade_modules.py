"""门面转正守阵(plan kernel-module-refactor P2): WebUIModule / HrModule 契约与内核接线

P2 内容: WebUIRuntime/HrRuntime 门面接入 Module 契约(webui/module.py + hr/module.py)/
run() 启停改 host.start_all/stop_all/_apply_web_config 并入 webui.apply/主循环对表现层的
语义调用改 loop hooks/store.hr_link 注入属装配/start_web_server 不再写 manager.web.token。
本文件锁五件事:
1. webui 模块生命周期契约(start 门控与幂等 / stop 只请求退出不等线程);
2. webui 模块热重载语义(有差异即置脏 / 仅监听身份变化才重启 / 密钥即时刷新 / 停止路径);
3. webui 模块 loop hooks(命令线返回值 / 同步线 / 任务线收尾次序);
4. hr 模块契约(start 的 dry-run 门 / apply 透传旧 hr_check 段 / sections 认领 hr_check+trackers);
5. 内核接线(run() 启停与主循环改经宿主, 不再点名 web 启动块 / hr.start / self.web.* 五调用)。

## 测试计划
- test_webui_module_start_semantics: dry-run/未启用无操作; 启用且未在跑 -> 启动; 已在跑幂等跳过
- test_webui_module_stop_requests_exit_without_wait: 只 handle.stop() 不等线程(原 finally 口径)
- test_webui_module_apply_marks_dirty_on_any_diff: 配置有差异 -> 置脏; 同一对象 -> 不置脏
- test_webui_module_apply_restarts_only_on_listen_identity_change: web 段非身份字段变化零启停; 身份变化先停旧(等退出)再启新; 关闭时清句柄
- test_webui_module_loop_hooks: on_command_line 聚合门面结果; on_sync_line 发布视图; on_task_line 预取->发布->索引次序
- test_hr_module_contract: start 的 dry-run 门 / start/stop/apply 透传(apply 拿旧 hr_check 段)/ sections 认领
- test_kernel_run_wiring_delegates_to_host: run() 启停经 host.start_all/stop_all; 主循环五调用改 loop hooks(flush_truths 次序语义留内核)
- test_facade_modules_in_assembly_and_bridge: 装配清单含 webui/hr 且顺序正确; hr_link 判定桥在装配期挂上
"""
import inspect
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

from auto_qb.config.models import HrCheckConfig
from auto_qb.core.qbmanager import QbManager
from auto_qb.webui.runtime import WebUIRuntime
from helpers import make_manager


def _web_stub(enabled=True, host="127.0.0.1", port=8080, token="t"):
    """WEB 段替身(仅监听身份与 token 判定关心的字段, 与 test_web 同款)"""
    return SimpleNamespace(enabled=enabled, host=host, port=port, token=token)


# ---------- WebUIModule 生命周期 ----------


def test_webui_module_start_semantics(monkeypatch):
    """start: dry-run/未启用无操作; 启用且未在跑 -> 启动; 已在跑幂等跳过(黄金法则 1)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("webui")
        started = mock.MagicMock()
        monkeypatch.setattr("auto_qb.webui.start_web_server", started)

        mod.start(mgr.ctx, dry_run=True)
        assert started.call_count == 0, "dry-run 只观察不对外服务"

        mgr.config.web = _web_stub(enabled=False)
        mod.start(mgr.ctx, dry_run=False)
        assert started.call_count == 0, "未启用无操作"

        mgr.config.web = _web_stub(enabled=True)
        mod.start(mgr.ctx, dry_run=False)
        assert started.call_count == 1, "启用时应启动服务器(密钥确定在 WebUIRuntime.start_server 内)"

        mgr.web.handle = "已有句柄"
        mod.start(mgr.ctx, dry_run=False)
        assert started.call_count == 1, "start 必须幂等: 已在跑不重复拉起(否则双服务器抢端口)"


def test_webui_module_stop_requests_exit_without_wait():
    """stop: 只 handle.stop()(置退出位)不等线程 —— 与原 run() finally 口径逐字一致"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("webui")
        handle = mock.MagicMock()
        mgr.web.handle = handle
        mod.stop()
        handle.stop.assert_called_once_with()
        handle.wait.assert_not_called(), "关停路径不等线程(daemon 随进程终灭), 热重载重启才需要等"


# ---------- WebUIModule 热重载语义 ----------


def test_webui_module_apply_marks_dirty_on_any_diff(monkeypatch):
    """apply: 配置有差异 -> 视图置脏(视图含配置派生展示值, 不限 web 段); 同一对象 -> 不置脏"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("webui")
        monkeypatch.setattr("auto_qb.webui.start_web_server", mock.MagicMock())
        monkeypatch.setattr("auto_qb.webui.stop_web_server", mock.MagicMock())
        with mock.patch.object(mgr.web, "mark_dirty") as dirty:
            mod.apply(SimpleNamespace(web=_web_stub()), mgr.config)
            assert dirty.call_count == 1, "新旧配置有差异即置脏(plan §4.3: webui.apply 不能完全短路)"
            mod.apply(mgr.config, mgr.config)
            assert dirty.call_count == 1, "同一对象(零差异)不置脏"


def test_webui_module_apply_restarts_only_on_listen_identity_change(monkeypatch):
    """apply: 仅监听身份(enabled/host/port)变化才重启; 非身份字段变化零启停; 重启先停旧(等退出)再启新"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("webui")
        started = mock.MagicMock(return_value="新句柄")
        stopped = mock.MagicMock()
        monkeypatch.setattr("auto_qb.webui.start_web_server", started)
        monkeypatch.setattr("auto_qb.webui.stop_web_server", stopped)
        mgr.web.handle = "旧句柄"
        mgr.config.web = _web_stub(port=8080)

        # web 段变了但监听身份没变(仅 token): 不重启
        mod.apply(SimpleNamespace(web=_web_stub(port=8080)), mgr.config)
        started.assert_not_called()
        stopped.assert_not_called()

        # 监听身份变化(端口): 先停旧(stop_web_server 含等待)再启新
        mgr.config.web = _web_stub(port=8081)
        mod.apply(SimpleNamespace(web=_web_stub(port=8080)), mgr.config)
        assert stopped.call_count == 1 and started.call_count == 1
        assert mgr.web.handle == "新句柄", "重启后句柄应换新"

        # 关闭(enabled=false): 停止并清空句柄
        mgr.config.web = _web_stub(enabled=False, port=8081)
        mod.apply(SimpleNamespace(web=_web_stub(port=8081)), mgr.config)
        assert stopped.call_count == 2
        assert mgr.web.handle is None, "关闭后句柄必须清空"


def test_webui_module_loop_hooks(monkeypatch):
    """loop hooks: on_command_line 聚合门面结果; on_sync_line 发布视图; on_task_line 收尾次序"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("webui")
        calls = []
        monkeypatch.setattr(mgr.web, "consume_commands", lambda: calls.append("consume") or True)
        monkeypatch.setattr(mgr.web, "check_pending", lambda: calls.append("check_pending"))
        monkeypatch.setattr(mgr.web, "advance_error_reasons", lambda: calls.append("reasons"))
        monkeypatch.setattr(mgr.web, "flush_views", lambda force: calls.append(f"views:{force}"))
        monkeypatch.setattr(mgr.web, "advance_search_index", lambda: calls.append("index"))

        assert mod.on_command_line() is True, "命令线返回「本批是否改了 qB 状态」(P0-5 补刷新判据)"
        assert calls == ["consume", "check_pending"], "命令线: 先消费命令再检查在途确认"
        calls.clear()

        mod.on_sync_line(force=True)
        assert calls == ["views:True"], "同步线收尾: 视图发布(force 绕过「已取走」门控)"
        calls.clear()

        mod.on_task_line(force=False)
        assert calls == ["reasons", "views:False", "index"], ("任务线收尾: 错误原因预取 -> 视图发布 -> 搜索索引推进(预取变更经置脏同轮可见)")


# ---------- HrModule 契约 ----------


def test_hr_module_contract():
    """hr 模块: start 的 dry-run 门 / start/stop/apply 透传(apply 拿旧 hr_check 段)/ sections 认领"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mod = mgr.host.get("hr")
        assert mod.name == "hr"
        assert mod.sections() == ("hr_check", "trackers"), "站点绑定派生自 trackers.X.hr_check, 必须一并认领"

        with mock.patch.object(mgr.hr, "start") as start, mock.patch.object(mgr.hr, "stop") as stop:
            mod.start(mgr.ctx, dry_run=True)
            start.assert_not_called(), "dry-run 不建端点/取数线程(原 run() 调用点口径)"
            mod.start(mgr.ctx, dry_run=False)
            start.assert_called_once_with(), "非 dry-run 透传 start(未启用由 HrRuntime.start 自判)"
            mod.stop()
            stop.assert_called_once_with()

        old_check = HrCheckConfig()
        with mock.patch.object(mgr.hr, "apply") as apply_:
            res = mod.apply(SimpleNamespace(hr_check=old_check), mgr.config)
            apply_.assert_called_once_with(old_check), "apply 透传旧 hr_check 段(短路/重建判据在门面)"
            assert res.module == "hr"


# ---------- 内核接线 ----------


def test_kernel_run_wiring_delegates_to_host():
    """P2 接线守阵: run() 启停经宿主, 主循环不再点名表现层调用(flush_truths 次序语义留内核)"""
    run_src = inspect.getsource(QbManager.run)
    assert "host.start_all" in run_src and "host.stop_all" in run_src, "web/hr 启停必须改经模块宿主(plan P2)"
    assert "start_web_server" not in run_src, "web 启动块已迁 WebUIModule.start"
    assert "self.hr.start" not in run_src and "self.hr.stop" not in run_src, "HR 启停已迁 HrModule"
    assert "consume_commands" not in run_src and "check_pending" not in run_src, "命令线改经 host.run_command_line"
    assert "flush_views" not in run_src and "advance_" not in run_src, "同步线/任务线收尾改经 loop hooks"
    assert "flush_truths" in run_src, "flush_truths 在刷新后落回执的次序语义留在内核(plan P2)"

    sync_src = inspect.getsource(QbManager._sync_line)
    assert "host.run_sync_line" in sync_src and "self.web." not in sync_src
    task_src = inspect.getsource(QbManager._task_line)
    assert "host.run_task_line" in task_src and "self.web." not in task_src


def test_facade_modules_in_assembly_and_bridge():
    """装配清单含 webui/hr 且顺序正确(plan §3.3); hr_link 判定桥在装配期挂上(P2 指定守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        names = [m.name for m in mgr.host.modules()]
        assert names.index("webui") < names.index("hr"), "装配序: webui 先于 hr(stop 逆序时 hr 先拆)"
        assert mgr.host.get("webui")._manager is mgr and mgr.host.get("hr")._manager is mgr
        assert mgr.store.hr_link is mgr.hr, "判定桥必须构造时就挂上(记录读取时现算, 不靠遍历刷新)"


def test_runtime_start_server_ensures_token_first(monkeypatch):
    """WebUIRuntime.start_server: 先确定密钥再拉起服务(令牌生命周期内聚门面, plan P2)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        rt = WebUIRuntime(mgr)
        order = []

        def _fake_ensure():
            order.append("token")
            rt.token = "tk"
            return "tk"

        monkeypatch.setattr(rt, "ensure_token", _fake_ensure)
        monkeypatch.setattr("auto_qb.webui.start_web_server", lambda m: order.append("server") or "句柄")
        rt.start_server()
        assert order == ["token", "server"], "密钥必须先于服务线程落定(start_web_server 已不代写)"
        assert rt.token == "tk" and rt.handle == "句柄"

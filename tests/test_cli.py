"""test_cli 测试计划: cli 模块 main 参数解析与分支

## 测试计划(每个测试函数一条)
- test_main_normal_mode: 正常模式: 无参数调用 main 进入运行分支
- test_main_export_yaml: --export-yaml 导出配置
- test_main_export_connect_failure: 导出时连接失败处理
- test_main_default_config_path: 缺省配置路径解析
- test_main_normal_mode_keyboard_interrupt: run 抛 KeyboardInterrupt -> 捕获退出不崩溃
- test_main_export_torrents_info_success: --export-torrents_info 连接成功 -> 导出并返回 0
- test_main_export_torrents_info_connect_failure: --export-torrents_info 连接失败 -> 不导出返回 1
- test_main_config_error_clean_exit: ConfigError 提前捕获, stderr 无堆栈, 返回 1
- test_main_lock_error_clean_exit: SingleInstanceLockError(构造期锁竞争)干净退出返回 1, 无堆栈无"配置错误"前缀
- test_main_qb_compat_error_clean_exit: QbCompatError(run 期 qB 版本不兼容)穿透 run 后干净退出返回 1, 无堆栈; 补发通知走 notify_fatal(测试内 mock —— MagicMock 的 config.notify 恒真, 不 mock 会真的发系统通知)
- test_main_qb_connect_error_clean_exit: QbConnectError(非托管首连失败)穿透 run 后干净退出返回 1, stderr 带地址与处置提示、无堆栈无"配置错误"前缀(docker 部署排障契约: 连不上 qB -> 退出码 1)
- test_main_unrelated_value_error_not_swallowed: 非 AutoQbError 的 ValueError(程序 bug)不被误捕, 照常抛出
- test_main_hr_status_mutex_with_hr_once: --hr-status 与 --hr-once 互斥 -> 退出码 2
- test_main_hr_status_runs_report_without_qb: --hr-status 不构造 manager(不连 qB), 行数上限透传
- test_main_tray_mutex_with_export: --tray 与 --export-yaml 互斥 -> 退出码 2
- test_main_split_trackers_requires_export_yaml: --split-trackers 单独传(无 --export-yaml)配合校验 -> 退出码 2
- test_main_export_yaml_split_trackers_passthrough: --export-yaml --split-trackers -> export_yaml_template kwargs.split_trackers is True
- test_main_export_yaml_default_merge_passthrough: --export-yaml 缺省 -> kwargs.split_trackers is False
- test_main_tray_mode_calls_run_tray: --tray 模式交由 ui.run_tray 托管
- test_main_tray_second_instance_wakes_running: --tray 双开唤起已运行实例 -> 静默退出 0
- test_main_tray_second_instance_wake_fail_returns_1: --tray 双开唤起失败 -> 常规锁错误退出 1
- test_main_normal_mode_installs_sigterm_handler: main() 入口注册 SIGTERM handler(P3, docker stop 优雅退出)
- test_sigterm_handler_raises_keyboard_interrupt: handler 触发即抛 KeyboardInterrupt(复用 Ctrl+C 路径), 且置 SIG_IGN 防清理期被打断
- test_install_sigterm_handler_registers: 平台允许注册时真注册(Windows/Linux 均允许注册; 真实 SIGTERM 投递由容器 docker stop 实测兜底)
- test_install_sigterm_handler_registration_failure_ignored: 注册失败(非主线程/平台不支持)静默跳过, 不影响启动
- test_main_arg_mutex_errors: 参数互斥矩阵(--hr-html-dir 无 --hr-once / --hr-once 与 --tray /
  --hr-status 与导出 / --hr-status-rows 非正 / --hr-confirm-empty 与其它 HR 模式) -> 退出码 2
- test_main_hr_confirm_empty: --hr-confirm-empty 站点清单解析(全角逗号归一)并转发, 透传返回码
- test_main_hr_confirm_empty_blank_errors: 清单解析后为空 -> parser.error 退出码 2
- test_main_hr_once_runs_report: --hr-once 不构造 manager, 转发 run_hr_once 并透传 hr_html_dir
- test_main_tray_second_instance_wake_raise_falls_through: 唤起实现自身抛异常 -> 吞掉走常规锁错误退出 1
- test_compat_entry_shim_runs_main: python auto-qb.py 兼容入口(runpy 进程内执行, __main__ 守卫生效)
- test_compat_entry_shim_imported_without_main_guard: 兼容入口被当模块导入(非 __main__) -> 只暴露 main, 不触发执行
- test_dunder_main_module_runs_main: python -m auto_qb(run_module, __main__.py 守卫 -> sys.exit(main()))
- test_cli_main_guard_under_dunder_main: 直接执行 cli.py 源码时 __main__ 守卫调 main()
- test_fuse_release_connect_failure_returns_false: fuse_release 连接失败 -> error 日志 + 返回 False, 不触 release
- test_fuse_release_snapshot_sync_failure_warns_and_continues: 放行前快照同步失败 -> warning 降级继续 release(只标记不写)
- test_fuse_release_dry_run_skips_state_save: dry-run 放行 -> release(dry_run=True) 且不落 state
- test_main_fuse_release_mutex_errors: fuse 放行互斥矩阵(--fuse-release 与 --all / 与托盘导出 HR 模式 / 纯分隔符空清单) -> 退出码 2
- test_main_fuse_release_dispatch_parses_hashes: --fuse-release 清单解析(全角逗号/空白归一小写)并派发 fuse_release, 落 state 后返回 0
- test_main_fuse_release_all_zero_entries_exits_0: --fuse-release-all 零条目合法清点 -> 仍返回 True/退出码 0(与显式列表零命中 False 相对)
"""
import signal
import sys
from pathlib import Path
from unittest import mock

import pytest

from auto_qb.config import ConfigError

from helpers import capture_logs

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _patch_argv(*args):
    return mock.patch.object(sys, "argv", list(args))


def test_main_normal_mode():
    """正常运行模式: 构造 manager 并 run(dry_run)"""
    manager = mock.MagicMock()
    manager.connect.return_value = True
    with _patch_argv("auto-qb", "config.yml", "--dry-run"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager) as m_qb, \
            mock.patch("auto_qb.cli.export_yaml_template") as m_exp:
        from auto_qb.cli import main
        main()
    m_qb.assert_called_once_with("config.yml", no_lock=False)
    manager.run.assert_called_once_with(True)
    m_exp.assert_not_called()


def test_main_export_yaml():
    """导出模式: 连接成功后调用 export_yaml_template 并退出"""
    manager = mock.MagicMock()
    manager.connect.return_value = True
    manager.config_path = "config.yml"
    with _patch_argv("auto-qb", "config.yml", "--export-yaml", "out.yml", "--only-missing"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.export_yaml_template") as m_exp:
        from auto_qb.cli import main
        main()
    m_exp.assert_called_once()  # 无 QbManager 断言, 已 mock
    args = m_exp.call_args[0]
    assert args[0] is manager.api  # 业务代码统一走 QbApi Facade
    assert args[1] is manager.config
    assert args[2] == "config.yml"
    assert args[3] == "out.yml"
    assert args[4] is False  # dry_run
    assert m_exp.call_args.kwargs["only_missing"] is True
    manager.run.assert_not_called()


def test_main_export_yaml_split_trackers_passthrough():
    """--split-trackers 经 cli 透传到 export_yaml_template 的 kwargs"""
    manager = mock.MagicMock()
    manager.connect.return_value = True
    manager.config_path = "config.yml"
    with _patch_argv("auto-qb", "config.yml", "--export-yaml", "out.yml", "--split-trackers"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.export_yaml_template") as m_exp:
        from auto_qb.cli import main
        main()
    assert m_exp.call_args.kwargs["split_trackers"] is True


def test_main_export_yaml_default_merge_passthrough():
    """缺省合并: 未传 --split-trackers 时 kwargs.split_trackers 为 False"""
    manager = mock.MagicMock()
    manager.connect.return_value = True
    manager.config_path = "config.yml"
    with _patch_argv("auto-qb", "config.yml", "--export-yaml", "out.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.export_yaml_template") as m_exp:
        from auto_qb.cli import main
        main()
    assert m_exp.call_args.kwargs["split_trackers"] is False


def test_main_export_connect_failure():
    """导出模式连接失败: 不导出直接返回"""
    manager = mock.MagicMock()
    manager.connect.return_value = False
    with _patch_argv("auto-qb", "config.yml", "-e", "out.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.export_yaml_template") as m_exp:
        from auto_qb.cli import main
        main()
    m_exp.assert_not_called()
    manager.run.assert_not_called()


def test_main_default_config_path():
    """未指定 config 时使用默认配置文件"""
    from auto_qb.config import DEFAULT_CONFIG_FILE
    manager = mock.MagicMock()
    with _patch_argv("auto-qb"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager) as m_qb:
        from auto_qb.cli import main
        main()
    m_qb.assert_called_once_with(DEFAULT_CONFIG_FILE, no_lock=False)


def test_main_normal_mode_keyboard_interrupt():
    """正常运行模式: run 抛 KeyboardInterrupt -> 捕获退出, 不崩溃"""
    manager = mock.MagicMock()
    manager.run.side_effect = KeyboardInterrupt()
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager) as m_qb:
        from auto_qb.cli import main
        main()  # 不应抛出 KeyboardInterrupt
    m_qb.assert_called_once_with("config.yml", no_lock=False)
    manager.run.assert_called_once_with(False)


def test_main_export_torrents_info_success():
    """--export-torrents_info 且连接成功: 导出 torrents.txt 并返回 0"""
    manager = mock.MagicMock()
    manager.connect.return_value = True
    with _patch_argv("auto-qb", "config.yml", "--export-torrents_info"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager):
        from auto_qb.cli import main
        ret = main()
    assert ret == 0
    manager.export_torrents_info.assert_called_once_with("torrents.txt")
    manager.run.assert_not_called()


def test_main_export_torrents_info_connect_failure():
    """--export-torrents_info 但连接失败: 不导出, 返回 1"""
    manager = mock.MagicMock()
    manager.connect.return_value = False
    with _patch_argv("auto-qb", "config.yml", "--export-torrents_info"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager):
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    manager.export_torrents_info.assert_not_called()
    manager.run.assert_not_called()


def test_main_config_error_clean_exit(capsys):
    """ConfigError(文件读取/YAML 解析/校验失败统一载体): 提前捕获, stderr 无堆栈, 返回 1"""
    err_msg = "配置校验失败(config.yml), 共 1 处:\n  [1] config: 未知键 ['x']"
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=ConfigError(err_msg)):
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "配置错误" in err and "配置校验失败" in err, err
    assert "Traceback" not in err


def test_main_lock_error_clean_exit(capsys):
    """SingleInstanceLockError(构造期锁竞争, AutoQbError 但非 ConfigError): 干净退出返回 1, 无堆栈不加配置前缀"""
    from auto_qb.infra.locking import SingleInstanceLockError
    err_msg = "另一实例已持有锁 auto-qb-data/state.lock (PID 123); auto-qb 仅允许同一配置一个运行实例"
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError(err_msg)):
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "另一实例已持有锁" in err
    assert "配置错误" not in err  # 非配置类致命错误不加"配置错误"前缀
    assert "Traceback" not in err


def test_main_qb_compat_error_clean_exit(capsys):
    """QbCompatError(run 期 qB 字段不兼容, AutoQbError 但非 ConfigError): 穿透 run 后干净退出返回 1, 无堆栈;
    致命退出补发通知走 notify_fatal —— 必须 mock: manager 是 MagicMock, `manager.config.notify` 恒真,
    notify_fatal 的 `not config or not config.enabled` 守卫会放行 -> 真的构造 PlatformChannel 发系统通知"""
    from auto_qb.torrents import QbCompatError
    manager = mock.MagicMock()
    manager.run.side_effect = QbCompatError("qBittorrent torrent info 缺少字段: ['foo']; 请检查版本兼容性")
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.notify_fatal") as m_notify:
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "缺少字段" in err
    assert "配置错误" not in err
    assert "Traceback" not in err
    assert m_notify.call_args[0][0] == "qBittorrent torrent info 缺少字段: ['foo']; 请检查版本兼容性", \
        "致命退出应把消息补发给 notify_fatal"


def test_main_qb_connect_error_clean_exit(capsys):
    """QbConnectError(非托管首连失败, run 内抛出): 穿透后干净退出返回 1, 无堆栈无"配置错误"前缀;
    消息带 qB 地址与处置提示(docker 部署排障契约, docs/deployment.md)"""
    from auto_qb.core.qbmanager import QbConnectError
    manager = mock.MagicMock()
    manager.run.side_effect = QbConnectError("无法连接 qBittorrent 127.0.0.1:16585: 请检查 qB 是否在运行、Web UI 地址/端口/凭据是否正确")
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.cli.notify_fatal"):
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "无法连接 qBittorrent 127.0.0.1:16585" in err
    assert "配置错误" not in err
    assert "Traceback" not in err


def test_main_unrelated_value_error_not_swallowed():
    """非 AutoQbError 的 ValueError(程序 bug)不被误捕: 照常抛出保留堆栈, 不打印'配置错误'"""
    manager = mock.MagicMock()
    manager.run.side_effect = ValueError("runtime bug")
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager):
        from auto_qb.cli import main
        with pytest.raises(ValueError, match="runtime bug"):
            main()


def test_main_tray_mutex_with_export():
    """--tray 与 --export-yaml 互斥: parser.error 退出码 2(manager 未构造)"""
    with _patch_argv("auto-qb", "config.yml", "--tray", "--export-yaml", "out.yml"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_split_trackers_requires_export_yaml():
    """--split-trackers 单独传(无 --export-yaml): 配合校验 parser.error 退出码 2(manager 未构造)"""
    with _patch_argv("auto-qb", "config.yml", "--split-trackers"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_hr_status_mutex_with_hr_once():
    """--hr-status 与 --hr-once 互斥(前者读已有数据, 后者真去抓一轮): 退出码 2, 不构造 manager"""
    with _patch_argv("auto-qb", "config.yml", "--hr-status", "--hr-once"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_hr_status_runs_report_without_qb():
    """--hr-status: 不构造 manager(不连 qB), 直接出只读报告"""
    with _patch_argv("auto-qb", "config.yml", "--hr-status", "--hr-status-rows", "3"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb, \
            mock.patch("auto_qb.cli.load_config") as m_conf, \
            mock.patch("auto_qb.hr.report.run_hr_status", return_value=0) as m_report:
        from auto_qb.cli import main
        assert main() == 0
    m_qb.assert_not_called()
    assert m_conf.called
    assert m_report.call_args[0][1] == 3, "行数上限要透传(--hr-status-rows)"


def test_main_tray_mode_calls_run_tray():
    """--tray 模式: 构造 manager 后交由 ui.run_tray 托管(而非 manager.run)"""
    manager = mock.MagicMock()
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.tray.run_tray", return_value=0) as m_tray:
        from auto_qb.cli import main
        ret = main()
    assert ret == 0
    m_tray.assert_called_once_with(manager, False)
    manager.run.assert_not_called()


def test_main_tray_second_instance_wakes_running():
    """--tray 双开: 锁被占且 ui.port 可达 -> 唤起已运行实例, 本实例静默退出 0"""
    from auto_qb.infra.locking import SingleInstanceLockError
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError("另一实例已持有锁")), \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.tray.send_show", return_value=True) as m_send:
        m_lc.return_value = mock.MagicMock(state_file="D:/x/state.json")
        from auto_qb.cli import main
        ret = main()
    assert ret == 0
    port_file = m_send.call_args[0][0]
    assert port_file.replace("\\", "/").endswith("ui.port"), "端口文件应位于 state_file 同目录"


def test_main_tray_second_instance_wake_fail_returns_1(capsys):
    """--tray 双开但唤起失败(端口文件缺失/首实例非托盘) -> 走常规锁错误, 退出码 1"""
    from auto_qb.infra.locking import SingleInstanceLockError
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError("另一实例已持有锁")), \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.tray.send_show", return_value=False):
        m_lc.return_value = mock.MagicMock(state_file="D:/x/state.json")
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "另一实例已持有锁" in err
    assert "Traceback" not in err


# ---------- SIGTERM 优雅退出(plan 26-09-25-2241 P3, 全方案唯一代码改动) ----------


def test_main_normal_mode_installs_sigterm_handler():
    """main() 入口注册 SIGTERM handler(docker stop -> Ctrl+C 同款优雅关闭路径的入口)"""
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb, \
            mock.patch("auto_qb.cli.signal.signal") as m_sig:
        from auto_qb import cli
        from auto_qb.cli import main
        main()
    m_sig.assert_called_once_with(signal.SIGTERM, cli._sigterm_to_keyboardinterrupt)
    m_qb.assert_called_once()


def test_sigterm_handler_raises_keyboard_interrupt():
    """SIGTERM handler: 触发即抛 KeyboardInterrupt 复用 Ctrl+C 路径; 且先置 SIG_IGN,
    清理期间(finally 落盘/停服)再到的 SIGTERM 不打断收尾"""
    from auto_qb.cli import _sigterm_to_keyboardinterrupt as handler
    orig = signal.getsignal(signal.SIGTERM)
    try:
        with pytest.raises(KeyboardInterrupt):
            handler(signal.SIGTERM, None)
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN, "首个信号后应改 SIG_IGN 保护清理窗口"
    finally:
        signal.signal(signal.SIGTERM, orig)


def test_install_sigterm_handler_registers():
    """平台允许注册时真注册(Windows/Linux 均允许注册, 差异只在信号投递; 真实投递由容器 docker stop 兜底)"""
    from auto_qb import cli
    orig = signal.getsignal(signal.SIGTERM)
    try:
        cli._install_sigterm_handler()
        assert signal.getsignal(signal.SIGTERM) is cli._sigterm_to_keyboardinterrupt
    finally:
        signal.signal(signal.SIGTERM, orig)


def test_install_sigterm_handler_registration_failure_ignored():
    """注册失败(signal.signal 抛 ValueError = 非主线程 / OSError = 平台不支持)静默跳过, 不影响启动"""
    from auto_qb import cli
    with mock.patch("auto_qb.cli.signal.signal", side_effect=ValueError("not main thread")):
        cli._install_sigterm_handler()  # 不应抛出


# ---------- T0.6 扩展: 参数互斥矩阵 / HR 写模式 / 入口壳 __main__ 守卫 ----------


@pytest.mark.parametrize(
    "argv",
    [
        ("auto-qb", "config.yml", "--hr-html-dir", "pages"),  # 缺 --hr-once
        ("auto-qb", "config.yml", "--hr-once", "--tray"),  # 与托盘互斥
        ("auto-qb", "config.yml", "--hr-status", "--export-yaml", "out.yml"),  # 与导出互斥
        ("auto-qb", "config.yml", "--hr-status", "--hr-status-rows", "0"),  # 行数须正
        ("auto-qb", "config.yml", "--hr-confirm-empty", "X", "--hr-status"),  # 写模式须独占
    ],
    ids=["html-dir-needs-once", "once-vs-tray", "status-vs-export", "rows-positive", "confirm-empty-exclusive"],
)
def test_main_arg_mutex_errors(argv):
    """参数互斥矩阵: 五条 parser.error 支路各自可达, 退出码 2 且不构造 manager"""
    with _patch_argv(*argv), \
            mock.patch("auto_qb.cli.QbManager") as m_qb, \
            mock.patch("auto_qb.cli.load_config") as m_lc:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()
    m_lc.assert_not_called()


def test_main_hr_confirm_empty():
    """--hr-confirm-empty: 站点清单解析(全角逗号归一 + 去空白), 转发 run_hr_confirm_empty
    并透传其返回码; 不构造 manager"""
    with _patch_argv("auto-qb", "config.yml", "--hr-confirm-empty", "Ａ站，B站, C站"), \
            mock.patch("auto_qb.hr.report.run_hr_confirm_empty", return_value=0) as m_run, \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        assert main() == 0
    m_qb.assert_not_called()
    assert m_lc.call_args[0][0] == "config.yml"
    assert m_run.call_args[0][1] == ["Ａ站", "B站", "C站"]


def test_main_hr_confirm_empty_blank_errors():
    """--hr-confirm-empty 清单解析后为空(纯分隔符) -> parser.error 退出码 2"""
    with _patch_argv("auto-qb", "config.yml", "--hr-confirm-empty", "， , "), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_hr_once_runs_report():
    """--hr-once: 只读走查不构造 manager(不连 qB), hr_html_dir 透传给 run_hr_once"""
    with _patch_argv("auto-qb", "config.yml", "--hr-once", "--hr-html-dir", "pages"), \
            mock.patch("auto_qb.hr.report.run_hr_once", return_value=0) as m_run, \
            mock.patch("auto_qb.cli.load_config"), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        assert main() == 0
    m_qb.assert_not_called()
    assert m_run.call_args[0][1] == "pages"


def test_main_tray_second_instance_wake_raise_falls_through(capsys):
    """--tray 双开: 唤起实现自身抛异常(端口文件损坏等) -> 吞掉, 走常规锁错误干净退出 1"""
    from auto_qb.infra.locking import SingleInstanceLockError
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError("另一实例已持有锁")), \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.tray.send_show", side_effect=OSError("port file corrupt")):
        m_lc.return_value = mock.MagicMock(state_file="D:/x/state.json")
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "另一实例已持有锁" in err
    assert "Traceback" not in err


def test_compat_entry_shim_runs_main():
    """python auto-qb.py 兼容入口: runpy 以 __main__ 进程内执行(零子进程), __main__ 守卫
    走到 sys.exit(main()); 参数互斥错误向上传播 SystemExit(2)"""
    import runpy

    path = str(_REPO_ROOT / "src" / "auto-qb.py")
    with _patch_argv("auto-qb", "config.yml", "--tray", "--export-yaml", "out.yml"):
        with pytest.raises(SystemExit) as ei:
            runpy.run_path(path, run_name="__main__")
    assert ei.value.code == 2


def test_compat_entry_shim_imported_without_main_guard():
    """兼容入口被当普通模块导入(非 __main__) -> 只完成 main 的暴露, 不触发执行不退出
    (import auto-qb 侧写面: 导入零副作用)"""
    import runpy

    path = str(_REPO_ROOT / "src" / "auto-qb.py")
    with _patch_argv("auto-qb", "config.yml", "--tray", "--export-yaml", "out.yml"):
        globs = runpy.run_path(path)  # 缺省 run_name != "__main__" -> 守卫走 False 支路
    import auto_qb.cli as cli_mod

    assert globs["main"] is cli_mod.main
    assert "sys" in globs


def test_dunder_main_module_runs_main():
    """python -m auto_qb: run_module 以 __main__ 执行包的 __main__.py, 守卫调用 main()"""
    import runpy

    with _patch_argv("auto-qb", "config.yml", "--hr-html-dir", "pages"):  # 互斥错误快速退出
        with pytest.raises(SystemExit) as ei:
            runpy.run_module("auto_qb", run_name="__main__")
    assert ei.value.code == 2


def test_cli_main_guard_under_dunder_main():
    """cli.py 自身的 __main__ 守卫: 以 __name__='__main__' + __package__='auto_qb' 进程内执行
    源码(runpy.run_path 解析不了包内相对导入), main() 被真调用一次"""
    import types

    import auto_qb.cli as cli_mod

    path = cli_mod.__file__
    code = open(path, encoding="utf-8").read()
    mod = types.ModuleType("__cli_dunder_main__")
    mod.__name__ = "__main__"
    mod.__package__ = "auto_qb"
    mod.__file__ = path
    with _patch_argv("auto-qb", "config.yml", "--hr-once", "--tray"):
        with pytest.raises(SystemExit) as ei:
            exec(compile(code, path, "exec"), mod.__dict__)
    assert ei.value.code == 2


# ---------- T0b 补测: fuse 放行 CLI 入口与互斥校验(零子进程, argv 直驱) ----------


def _fuse_mgr():
    """fuse_release 直驱用 manager 替身(连接成功 + 快照同步正常)"""
    mgr = mock.MagicMock()
    mgr.connect.return_value = True
    mgr.store.apply_sync.return_value = ([], [])
    mgr.ctx.fuse.release.return_value = 1
    return mgr


def test_fuse_release_connect_failure_returns_false():
    """fuse_release 连接失败: error 日志 + 返回 False, 不触快照同步与 release"""
    from auto_qb.cli import fuse_release

    mgr = mock.MagicMock()
    mgr.connect.return_value = False
    with capture_logs("") as cap:  # cli 用模块级 logging.*, 落 root logger
        assert fuse_release(mgr, ["x" * 40], False, False) is False
    mgr.store.apply_sync.assert_not_called()
    mgr.ctx.fuse.release.assert_not_called()
    assert any("放行失败" in m for m in cap.messages)


def test_fuse_release_snapshot_sync_failure_warns_and_continues():
    """放行前快照同步失败(qB 断连/旧版本降级): warning 降级, 仍继续 release(只标记不写的安全侧)"""
    from auto_qb.cli import fuse_release

    mgr = _fuse_mgr()
    mgr.store.apply_sync.side_effect = RuntimeError("connection closed")
    with capture_logs("") as cap:
        assert fuse_release(mgr, ["x" * 40], False, False) is True
    mgr.ctx.fuse.release.assert_called_once_with(["x" * 40], dry_run=False)
    assert any("快照同步失败" in m for m in cap.messages)
    mgr.ctx.state.save.assert_called_once()  # 非 dry-run 放行要落 state


def test_fuse_release_dry_run_skips_state_save():
    """dry-run 放行: release 收 dry_run=True, 不落 state(日志带 dry-run 标记)"""
    from auto_qb.cli import fuse_release

    mgr = _fuse_mgr()
    mgr.ctx.fuse.release.return_value = 2
    with capture_logs("") as cap:
        assert fuse_release(mgr, ["x" * 40], False, True) is True
    mgr.ctx.fuse.release.assert_called_once_with(["x" * 40], dry_run=True)
    mgr.ctx.state.save.assert_not_called()
    assert any("dry-run" in m and "已放行 2 个条目" in m for m in cap.messages)


@pytest.mark.parametrize(
    "argv",
    [
        ("auto-qb", "config.yml", "--fuse-release", "ABC", "--fuse-release-all"),  # 两放行形态互斥
        ("auto-qb", "config.yml", "--fuse-release-all", "--tray"),  # 写操作与托盘互斥
        ("auto-qb", "config.yml", "--fuse-release", "ABC", "--hr-once"),  # 写操作与 HR 走查互斥
        ("auto-qb", "config.yml", "--fuse-release-all", "--hr-status"),  # 写操作与 HR 现状互斥
        ("auto-qb", "config.yml", "--fuse-release", "ABC", "--hr-confirm-empty", "X"),  # 写操作与 HR 写模式互斥
        ("auto-qb", "config.yml", "--export-torrents_info", "--fuse-release-all"),  # 写操作与导出互斥
        ("auto-qb", "config.yml", "--fuse-release", "， , "),  # 清单解析后为空
    ],
    ids=["both-forms", "vs-tray", "vs-hr-once", "vs-hr-status", "vs-hr-confirm-empty", "vs-export", "blank-hashes"],
)
def test_main_fuse_release_mutex_errors(argv):
    """fuse 放行互斥矩阵: 七条 parser.error 支路各自可达, 退出码 2 且不构造 manager"""
    with _patch_argv(*argv), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_fuse_release_dispatch_parses_hashes():
    """--fuse-release 派发: 清单解析(全角逗号归一 + 去空白 + 小写)后转交 fuse_release, 落 state 返回 0

    26-11-05 合流对齐 02ad25d3 新语义: 入参加 40 位十六进制校验, 清单改用合法 hash
    (仍保留全角逗号/空白/大写以覆盖归一化路径); 另补非法 hash 被 parser.error 拒收断言。
    """
    manager = mock.MagicMock()
    manager.connect.return_value = True
    manager.store.apply_sync.return_value = ([], [])
    manager.ctx.fuse.release.return_value = 2
    with _patch_argv("auto-qb", "config.yml", "--fuse-release", " " + "A" * 40 + "，" + "b" * 40 + " "), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            capture_logs("") as cap:
        from auto_qb.cli import main
        assert main() == 0
    manager.ctx.fuse.release.assert_called_once_with(["a" * 40, "b" * 40], dry_run=False)
    manager.ctx.state.save.assert_called_once()
    assert any("已放行 2 个条目" in m for m in cap.messages), "放行汇总日志要带条目数"

    # 02ad25d3 新增校验: 非 40 位十六进制 -> parser.error(退出码 2, 不构造 manager)
    with _patch_argv("auto-qb", "config.yml", "--fuse-release", " ABC ，def,gh "), \
            mock.patch("auto_qb.cli.QbManager") as m_qb:
        from auto_qb.cli import main
        with pytest.raises(SystemExit) as ei:
            main()
    assert ei.value.code == 2
    m_qb.assert_not_called()


def test_main_fuse_release_all_zero_entries_exits_0():
    """--fuse-release-all 零条目是合法清点: release 返回 0 仍算成功 -> 退出码 0

    与显式列表零命中(返回 False -> 退出码 1)相对: --all 清零常与 enabled=false 配合清残留,
    回归翻转 `released == 0 and not release_all` 的条件会把这个合法场景误报成失败退出码。
    """
    manager = _fuse_mgr()
    manager.ctx.fuse.release.return_value = 0
    with _patch_argv("auto-qb", "config.yml", "--fuse-release-all"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            capture_logs("") as cap:
        from auto_qb.cli import main
        assert main() == 0
    manager.ctx.fuse.release.assert_called_once_with(None, dry_run=False)  # --all 以 None 清单放行全部
    manager.ctx.state.save.assert_called_once()
    assert any("已放行 0 个条目" in m for m in cap.messages), "零条目清点也要留汇总日志"

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
- test_main_qb_compat_error_clean_exit: QbCompatError(run 期 qB 版本不兼容)穿透 run 后干净退出返回 1, 无堆栈
- test_main_unrelated_value_error_not_swallowed: 非 AutoQbError 的 ValueError(程序 bug)不被误捕, 照常抛出
- test_main_tray_mutex_with_export: --tray 与 --export-yaml 互斥 -> 退出码 2
- test_main_tray_mode_calls_run_tray: --tray 模式交由 ui.run_tray 托管
- test_main_tray_second_instance_wakes_running: --tray 双开唤起已运行实例 -> 静默退出 0
- test_main_tray_second_instance_wake_fail_returns_1: --tray 双开唤起失败 -> 常规锁错误退出 1
"""
import sys
from unittest import mock

import pytest

from auto_qb.config import ConfigError


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
    m_exp.call_args.kwargs["only_missing"] is True
    manager.run.assert_not_called()


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
    from auto_qb.locking import SingleInstanceLockError
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
    """QbCompatError(run 期 qB 字段不兼容, AutoQbError 但非 ConfigError): 穿透 run 后干净退出返回 1, 无堆栈"""
    from auto_qb.torrents import QbCompatError
    manager = mock.MagicMock()
    manager.run.side_effect = QbCompatError("qBittorrent torrent info 缺少字段: ['foo']; 请检查版本兼容性")
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager):
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "缺少字段" in err
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


def test_main_tray_mode_calls_run_tray():
    """--tray 模式: 构造 manager 后交由 ui.run_tray 托管(而非 manager.run)"""
    manager = mock.MagicMock()
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager), \
            mock.patch("auto_qb.ui.run_tray", return_value=0) as m_tray:
        from auto_qb.cli import main
        ret = main()
    assert ret == 0
    m_tray.assert_called_once_with(manager, False)
    manager.run.assert_not_called()


def test_main_tray_second_instance_wakes_running():
    """--tray 双开: 锁被占且 ui.port 可达 -> 唤起已运行实例, 本实例静默退出 0"""
    from auto_qb.locking import SingleInstanceLockError
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError("另一实例已持有锁")), \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.ui.send_show", return_value=True) as m_send:
        m_lc.return_value = mock.MagicMock(state_file="D:/x/state.json")
        from auto_qb.cli import main
        ret = main()
    assert ret == 0
    port_file = m_send.call_args[0][0]
    assert port_file.replace("\\", "/").endswith("ui.port"), "端口文件应位于 state_file 同目录"


def test_main_tray_second_instance_wake_fail_returns_1(capsys):
    """--tray 双开但唤起失败(端口文件缺失/首实例非托盘) -> 走常规锁错误, 退出码 1"""
    from auto_qb.locking import SingleInstanceLockError
    with _patch_argv("auto-qb", "config.yml", "--tray"), \
            mock.patch("auto_qb.cli.QbManager", side_effect=SingleInstanceLockError("另一实例已持有锁")), \
            mock.patch("auto_qb.cli.load_config") as m_lc, \
            mock.patch("auto_qb.ui.send_show", return_value=False):
        m_lc.return_value = mock.MagicMock(state_file="D:/x/state.json")
        from auto_qb.cli import main
        ret = main()
    assert ret == 1
    err = capsys.readouterr().err
    assert "另一实例已持有锁" in err
    assert "Traceback" not in err

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
- test_main_unrelated_value_error_not_swallowed: 非配置类 ValueError(程序 bug)不被误捕, 照常抛出
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
    m_qb.assert_called_once_with("config.yml")
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
    m_exp.assert_called_once()
    args = m_exp.call_args[0]
    assert args[0] is manager.api  # 业务代码统一走 QbApi 门面
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
    m_qb.assert_called_once_with(DEFAULT_CONFIG_FILE)


def test_main_normal_mode_keyboard_interrupt():
    """正常运行模式: run 抛 KeyboardInterrupt -> 捕获退出, 不崩溃"""
    manager = mock.MagicMock()
    manager.run.side_effect = KeyboardInterrupt()
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager) as m_qb:
        from auto_qb.cli import main
        main()  # 不应抛出 KeyboardInterrupt
    m_qb.assert_called_once_with("config.yml")
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


def test_main_unrelated_value_error_not_swallowed():
    """非配置类 ValueError(程序 bug)不被误捕: 照常抛出保留堆栈, 不打印'配置错误'"""
    manager = mock.MagicMock()
    manager.run.side_effect = ValueError("runtime bug")
    with _patch_argv("auto-qb", "config.yml"), \
            mock.patch("auto_qb.cli.QbManager", return_value=manager):
        from auto_qb.cli import main
        with pytest.raises(ValueError, match="runtime bug"):
            main()

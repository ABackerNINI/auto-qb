"""test_cli 测试计划: cli 模块 main 参数解析与分支

## 测试计划(每个测试函数一条)
- test_main_normal_mode: 正常模式: 无参数调用 main 进入运行分支
- test_main_export_yaml: --export-yaml 导出配置
- test_main_export_connect_failure: 导出时连接失败处理
- test_main_default_config_path: 缺省配置路径解析
- test_main_normal_mode_keyboard_interrupt: run 抛 KeyboardInterrupt -> 捕获退出不崩溃
"""
import sys
from unittest import mock


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

"""命令行入口"""
import argparse
import logging
import os
import sys

from .config import DEFAULT_CONFIG_FILE, ConfigError, load_config
from .errors import AutoQbError
from .exporter import export_yaml_template
from .locking import SingleInstanceLockError
from .notify import notify_fatal
from .qbmanager import QbManager


def export_yaml(manager: QbManager, args):
    """导出模式: 连接后由 exporter 模块完成导出"""
    if not manager.connect():
        logging.error("导出失败: 无法连接 qBittorrent")
        return False
    export_yaml_template(
        manager.api,
        manager.config,
        manager.config_path,
        args.export_yaml,
        args.dry_run,
        only_missing=args.only_missing
    )
    return True


def export_torrents_info(manager: QbManager, output_file: str):
    """导出种子信息到指定文件"""
    if not manager.connect():
        logging.error("导出失败: 无法连接 qBittorrent")
        return False
    manager.export_torrents_info(output_file)
    return True


def main():
    parser = argparse.ArgumentParser(description="PT Seed Manager for qBittorrent")
    parser.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG_FILE,
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--export-yaml",
        "-e",
        metavar="OUTPUT",
        help="Export YAML templates to OUTPUT file and exit",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="只导出未配置的 tracker 站点(需配合 --export-yaml, 生成最小骨架)",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry run")
    parser.add_argument(
        "--tray",
        action="store_true",
        help="托盘常驻模式: 系统托盘图标 + 主窗口(再次启动将唤起已运行实例的窗口)",
    )
    parser.add_argument(
        "--export-torrents_info",
        action="store_true",
        help="Export torrents info to a file 'torrents.txt' for debugging"
    )
    args = parser.parse_args()

    if args.tray and (args.export_yaml or args.export_torrents_info):
        parser.error("--tray 与导出模式互斥")

    manager = None
    try:
        # 出口模式不持锁(只读, 可与正常实例并发); 正常 run 模式持锁
        manager = QbManager(args.config, no_lock=bool(args.export_yaml or args.export_torrents_info))

        if args.export_yaml:
            return 0 if export_yaml(manager, args) else 1

        if args.export_torrents_info:
            return 0 if export_torrents_info(manager, "torrents.txt") else 1

        # 托盘常驻模式: 第二实例(锁被占)尝试唤起已运行实例的窗口后静默退出
        if args.tray:
            from .ui import run_tray  # 延迟导入: GUI 栈仅托盘模式加载(无显示环境不影响其它模式)

            return run_tray(manager, args.dry_run)

        # 正常运行模式
        manager.run(args.dry_run)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except AutoQbError as e:
        # 托盘双开唤起: 单实例锁被占且 ui.port 可达 -> 唤起已运行实例的窗口, 本实例静默退出(退出码 0)。
        # 此时 manager 未构造成功, 重新读配置以定位端口文件(state_file 同目录); 唤起失败走常规锁错误提示
        if args.tray and isinstance(e, SingleInstanceLockError):
            try:
                from .ui import UI_PORT_FILE_NAME, send_show

                state_file = load_config(args.config).state_file
                if send_show(os.path.join(os.path.dirname(state_file), UI_PORT_FILE_NAME)):
                    return 0
            except Exception:
                pass
        # 致命错误(AutoQbError 体系)统一干净退出: 仅输出消息到 stderr, 不打印堆栈, 退出码 1
        # - ConfigError(配置读取/YAML 解析/校验失败): 加"配置错误"前缀
        # - SingleInstanceLockError(锁竞争, 构造期)/QbCompatError(qB 字段不兼容, 运行期)等:
        #   消息自身已含完整上下文, 直接输出
        # 非 AutoQbError 异常属程序 bug, 照常抛出保留堆栈
        prefix = "配置错误: " if isinstance(e, ConfigError) else ""
        print(f"{prefix}{e}", file=sys.stderr)
        # 运行期致命错误(如 QbCompatError)时 manager 已构造且通知启用 -> 补发一条退出通知;
        # 启动失败(配置错误/锁竞争)场景 manager 为 None(无配置可读), 不发; 任何失败不影响退出码
        notify_fatal(f"{prefix}{e}", manager.config.notify if manager is not None else None)
        return 1


if __name__ == "__main__":
    main()

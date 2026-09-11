"""命令行入口"""
import argparse
import logging
import sys

from .config import DEFAULT_CONFIG_FILE, ConfigError
from .errors import AutoQbError
from .exporter import export_yaml_template
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
        "--export-torrents_info",
        action="store_true",
        help="Export torrents info to a file 'torrents.txt' for debugging"
    )
    args = parser.parse_args()

    manager = None
    try:
        # 出口模式不持锁(只读, 可与正常实例并发); 正常 run 模式持锁
        manager = QbManager(args.config, no_lock=bool(args.export_yaml or args.export_torrents_info))

        if args.export_yaml:
            return 0 if export_yaml(manager, args) else 1

        if args.export_torrents_info:
            return 0 if export_torrents_info(manager, "torrents.txt") else 1

        # 正常运行模式
        manager.run(args.dry_run)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except AutoQbError as e:
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

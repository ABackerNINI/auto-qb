"""命令行入口"""
import argparse
import logging

from .config import DEFAULT_CONFIG_FILE
from .exporter import export_yaml_template
from .qbmanager import QbManager


def export_yaml(manager: QbManager, args):
    """导出模式: 连接后由 exporter 模块完成导出"""
    if not manager.connect():
        manager.logger.error("Cannot export: qBittorrent connection failed")
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
        manager.logger.error("Cannot export: qBittorrent connection failed")
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

    manager = QbManager(args.config)

    try:
        if args.export_yaml:
            return 0 if export_yaml(manager, args.export_yaml) else 1

        if args.export_torrents_info:
            return 0 if export_torrents_info(manager, "torrents.txt") else 1

        # 正常运行模式
        manager.run(args.dry_run)
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    main()

"""命令行入口"""
import argparse
import logging

from .config import DEFAULT_CONFIG_FILE
from .exporter import export_yaml_template
from .qbmanager import QbManager


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
    args = parser.parse_args()

    manager = QbManager(args.config)

    if args.export_yaml:
        # 导出模式: 连接后由 exporter 模块完成导出
        if not manager.connect():
            manager.logger.error("Cannot export: qBittorrent connection failed")
            return
        export_yaml_template(
            manager.api,
            manager.config,
            manager.config_path,
            args.export_yaml,
            args.dry_run,
            only_missing=args.only_missing,
        )
        return

    # 正常运行模式
    try:
        manager.run(args.dry_run)
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    main()

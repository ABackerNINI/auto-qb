"""auto_qb: PT Seed Manager for qBittorrent 包

模块结构:
- config.py   配置数据类与加载
- manager.py  PTManager 主类(内置处理步骤 + 规则框架集成)
- exporter.py YAML 配置模板导出
- rules/      规则框架(条件/动作插件 + RuleManager)
- cli.py      命令行入口
"""
from .config import Config, TrackerConfig, QbittorrentConfig, load_config
from .manager import PTManager

__version__ = "0.2.0"

__all__ = [
    "Config",
    "TrackerConfig",
    "QbittorrentConfig",
    "PTManager",
    "load_config",
    "__version__",
]

"""auto_qb: PT Seed Manager for qBittorrent 包

模块结构:
- config/      配置数据类(models)/加载(loaders)/校验(validation)
- qbmanager.py QbManager 主类(组合各 mixin: 种子刷新/规则/分组/限速曲线/异步校验轮询)
- exporter.py  YAML 配置模板导出
- rules/       规则框架(条件/动作插件, 由 QbManager 统一加载与调度)
- mixins/      QbManager 功能 mixin(rule_engine/tags/checking/grouping/tracker/speed_curve)
- cli.py       命令行入口
"""
from .config import Config, ConfigError, TrackerConfig, QbittorrentConfig, load_config
from .qbmanager import QbManager

__version__ = "0.2.0"

__all__ = [
    "Config",
    "ConfigError",
    "TrackerConfig",
    "QbittorrentConfig",
    "QbManager",
    "load_config",
    "__version__",
]

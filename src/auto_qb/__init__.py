"""auto_qb: PT Seed Manager for qBittorrent 包

模块结构 (2026-09-22 方案 C 分层归拢, plan memory-bank/plans/26-09-22-2112-src-layout-restructure-plan.html):
- cli.py / __main__.py  入口 (argparse / python -m; pyproject.scripts 钉在 auto_qb.cli:main)
- config/               配置层: 模型(models)/加载(loaders)/校验(validation)/schema/写回(writer)/影响分级(impact)
- core/                 核心域: qbmanager(主协调者+8 mixin 组合) / taskqueue / qbapi / qbclient /
                        curves / episodes / tvshows / exporter / mixins/(6 核心切片)
- infra/                基础设施: errors(错误根) / locking / logging / utils / notify / autostart
- rules/                规则框架(条件/动作插件 + expr 表达式引擎)
- torrents/             种子数据层(增量同步/记录/视图契约)
- webui/                WEB 表现层: runtime(门面) / views+commands(构建器+命令处理器) /
                        server/(FastAPI 路由) / static/(atlas·prism 前端资产)
- tray/                 桌面托盘表现层(CustomTkinter + pystray)
"""
from .config import Config, ConfigError, TrackerConfig, QbittorrentConfig, load_config
from .core.qbmanager import QbManager

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

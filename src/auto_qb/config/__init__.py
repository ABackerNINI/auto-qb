"""auto_qb.config: 配置模型 / fail-fast 全量校验 / 解析加载

拆分结构(按职责分层, 相似函数聚集):
- errors.py     ConfigError 统一配置异常
- models.py     DEFAULT_* 常量 + 全部数据类(仅声明)
- validation.py fail-fast 全量校验(validate_config 及各段校验器, 聚合错误一次性报告)
- loaders.py    解析加载(load_config 及各 load_* 函数, 先验证再解析, 假定配置正确)

本包重导出全部公共名称, 调用方保持 `from auto_qb.config import X` 不变。

校验约定:
- 显式留空的键(空串/None)视为未配置, 走默认值(_strip_none); 必填键缺失则报错
- 例外(config v4, report 26-10-03-0504 方案 B 阶段 1): schema 声明 tri_state 的键在站点段
  config.trackers.<名>.hr.<键> 的空串保留 = 「覆盖为空」; v3 及更早的存量空串由迁移链移除并打 WARNING
- 校验聚合全部错误一次性报告(validate_config), 每条带配置路径(如 config.trackers.tracker1)
- 值格式复用 utils.parse_*(时间/大小/速度/布尔)单一事实来源
- 规则集 spec 的条件/动作名称经 registry 延迟导入校验(避免模块循环依赖)
"""
from .errors import ConfigError
from . import migrations  # noqa: F401  # import 即注册 config schema 迁移链(早于任何 load_config)
from .models import (
    DEFAULT_CONFIG_FILE,
    UNLIMITED_SPEED,
    AddEpisodeTagsConfig,
    Config,
    CurvePoint,
    GlobalSpeedLimitCurve,
    GroupingConfig,
    HRRule,
    LoggingConfig,
    NotifyConfig,
    PathMapEntry,
    FsConfig,
    PeriodCurve,
    WebConfig,
    QbittorrentConfig,
    QbTraffic,
    TrackerConfig,
)
from .validation import validate_config
from .loaders import (
    load_config,
    load_global_hr,
    load_global_speed_limit_curve,
    load_grouping_config,
    load_logging_config,
    load_notify_config,
    load_web_config,
    load_qbittorrent_config,
    load_qb_traffic,
    load_tracker_config,
    load_tracker_hr,
)
from .loaders import _strip_none  # noqa: F401  # 供 exporter 原始重读复用(私有名, 不入 __all__)

__all__ = [
    "ConfigError",
    "Config",
    "CurvePoint",
    "FsConfig",
    "PathMapEntry",
    "GlobalSpeedLimitCurve",
    "GroupingConfig",
    "HRRule",
    "LoggingConfig",
    "NotifyConfig",
    "PeriodCurve",
    "WebConfig",
    "QbittorrentConfig",
    "QbTraffic",
    "TrackerConfig",
    "validate_config",
    "load_config",
    "load_global_hr",
    "load_global_speed_limit_curve",
    "load_grouping_config",
    "load_logging_config",
    "load_notify_config",
    "load_web_config",
    "load_qbittorrent_config",
    "load_qb_traffic",
    "load_tracker_config",
    "load_tracker_hr",
    "DEFAULT_CONFIG_FILE",
    "UNLIMITED_SPEED",
]

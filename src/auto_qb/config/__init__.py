"""auto_qb.config: 配置模型 / fail-fast 全量校验 / 解析加载

拆分结构(按职责分层, 相似函数聚集):
- errors.py     ConfigError 统一配置异常
- models.py     DEFAULT_* 常量 + 全部数据类(仅声明)
- validation.py fail-fast 全量校验(validate_config 及各段校验器, 聚合错误一次性报告)
- loaders.py    解析加载(load_config 及各 load_* 函数, 先验证再解析, 假定配置正确)

本包重导出全部公共名称, 调用方保持 `from auto_qb.config import X` 不变。

校验约定:
- 显式留空的键(空串/None)视为未配置, 走默认值(_strip_none); 必填键缺失则报错
- 校验聚合全部错误一次性报告(validate_config), 每条带配置路径(如 config.trackers.tracker1)
- 值格式复用 utils.parse_*(时间/大小/速度/布尔)单一事实来源
- 规则集 spec 的条件/动作名称经 registry 延迟导入校验(避免模块循环依赖)
"""
from .errors import ConfigError
from .models import (
    DEFAULT_ADD_EPISODE_TAGS,
    DEFAULT_CONFIG_FILE,
    DEFAULT_GROUPING_ENABLED,
    DEFAULT_GROUPING_INTERVAL,
    DEFAULT_GROUPING_MISSING_TAG,
    DEFAULT_HR_OUTPUT,
    DEFAULT_INTERVAL,
    DEFAULT_MAIN_TICK,
    DEFAULT_MAX_TASKS_PER_TICK,
    DEFAULT_REMOVE_SIMILAR_TAGS,
    DEFAULT_STATE_FILE,
    UNLIMITED_SPEED,
    Config,
    CurvePoint,
    GlobalSpeedLimitCurve,
    GroupingConfig,
    HRRule,
    LoggingConfig,
    PeriodCurve,
    QbittorrentConfig,
    TrackerConfig,
)
from .validation import validate_config
from .loaders import (
    load_config,
    load_global_hr,
    load_global_speed_limit_curve,
    load_grouping_config,
    load_logging_config,
    load_qbittorrent_config,
    load_tracker_config,
    load_tracker_hr,
)
from .loaders import _strip_none  # noqa: F401  # 供 exporter 原始重读复用(私有名, 不入 __all__)

__all__ = [
    "ConfigError",
    "Config",
    "CurvePoint",
    "GlobalSpeedLimitCurve",
    "GroupingConfig",
    "HRRule",
    "LoggingConfig",
    "PeriodCurve",
    "QbittorrentConfig",
    "TrackerConfig",
    "validate_config",
    "load_config",
    "load_global_hr",
    "load_global_speed_limit_curve",
    "load_grouping_config",
    "load_logging_config",
    "load_qbittorrent_config",
    "load_tracker_config",
    "load_tracker_hr",
    "DEFAULT_ADD_EPISODE_TAGS",
    "DEFAULT_CONFIG_FILE",
    "DEFAULT_GROUPING_ENABLED",
    "DEFAULT_GROUPING_INTERVAL",
    "DEFAULT_GROUPING_MISSING_TAG",
    "DEFAULT_HR_OUTPUT",
    "DEFAULT_INTERVAL",
    "DEFAULT_MAIN_TICK",
    "DEFAULT_MAX_TASKS_PER_TICK",
    "DEFAULT_REMOVE_SIMILAR_TAGS",
    "DEFAULT_STATE_FILE",
    "UNLIMITED_SPEED",
]

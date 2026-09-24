"""fail-fast 全量配置校验: 全部正确性检查集中于此, 聚合错误一次性报告(不抛异常, 由 load_config 统一抛出)

包拆分结构(2026-09-15 大文件拆分批次三):
- core.py      通用校验助手(_strip_none/_try*/_check_*) + validate_config 入口
- sections.py  config 各简单段校验器(log/qbittorrent/hr/grouping/web/notify/trackers 等)
- rules.py     规则集 spec 校验 + 插件 spec 深度校验分发
- curves.py    全局限速曲线段校验
- __init__.py  全量重导出(validate_config/KNOWN_*/_strip_none, 调用方零改动)

校验约定:
- 显式留空的键(空串/None)视为未配置, 走默认值(_strip_none); 必填键缺失则报错
- 校验聚合全部错误一次性报告(validate_config), 每条带配置路径(如 config.trackers.tracker1)
- 值格式复用 utils.parse_*(时间/大小/速度/布尔)单一事实来源
- 规则集 spec 的条件/动作名称经 registry 延迟导入校验(避免模块循环依赖)
"""
from .core import KNOWN_CONFIG_KEYS, _strip_none, validate_config
from .curves import _validate_curve_points, _validate_global_speed_limit_curve
from .rules import (
    CHECKING_ACTION_KNOWN_KEYS,
    CHECKING_VALID_BASIC,
    CHECKING_VALID_MODES,
    DELETED_TRIGGER_ALLOWED_ACTIONS,
    EXECUTE_ONCE_VALUES,
    RULE_KNOWN_KEYS,
    STOP_IF_VALUES,
    TRIGGER_VALUES,
)
from .sections import (
    HR_CHECK_MODES,
    HR_CHECK_UNKNOWN_POLICIES,
    KNOWN_GROUPING_KEYS,
    KNOWN_HR_CHANNEL_KEYS,
    KNOWN_HR_CHECK_KEYS,
    KNOWN_HR_KEYS,
    KNOWN_LOG_KEYS,
    KNOWN_NOTIFY_KEYS,
    KNOWN_QBITTORRENT_KEYS,
    KNOWN_SITE_HR_CHECK_KEYS,
    KNOWN_TRACKER_HR_KEYS,
    KNOWN_TRACKER_KEYS,
    KNOWN_WEB_KEYS,
    NOTIFY_CHANNELS,
    NOTIFY_LEVELS,
)

__all__ = [
    "validate_config",
    "KNOWN_CONFIG_KEYS",
    "KNOWN_LOG_KEYS",
    "KNOWN_QBITTORRENT_KEYS",
    "KNOWN_GROUPING_KEYS",
    "KNOWN_WEB_KEYS",
    "KNOWN_NOTIFY_KEYS",
    "NOTIFY_CHANNELS",
    "NOTIFY_LEVELS",
    "KNOWN_HR_KEYS",
    "KNOWN_TRACKER_KEYS",
    "KNOWN_TRACKER_HR_KEYS",
    "KNOWN_HR_CHECK_KEYS",
    "KNOWN_HR_CHANNEL_KEYS",
    "KNOWN_SITE_HR_CHECK_KEYS",
    "HR_CHECK_MODES",
    "HR_CHECK_UNKNOWN_POLICIES",
    "KNOWN_WEB_KEYS",
    "RULE_KNOWN_KEYS",
    "EXECUTE_ONCE_VALUES",
    "STOP_IF_VALUES",
    "TRIGGER_VALUES",
    "DELETED_TRIGGER_ALLOWED_ACTIONS",
    "CHECKING_ACTION_KNOWN_KEYS",
    "CHECKING_VALID_BASIC",
    "CHECKING_VALID_MODES",
]

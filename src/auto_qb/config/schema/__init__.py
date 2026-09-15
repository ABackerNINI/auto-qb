"""配置 UI 元数据: WEB UI 图形化配置编辑器的唯一描述来源(纯声明, 无副作用)

包拆分结构(2026-09-15 大文件拆分批次二):
- fields.py     Field/Group/Plugin 数据类 + 控件 kind 与选项常量(零依赖)
- trackers.py   站点段字段(HR 输出字段/站点 hr/站点字段)
- rules.py      规则字段 + 条件/动作插件表
- groups.py     GROUPS 顶层分组表(左导航 8 分组)
- __init__.py   访问函数(config_fields/schema_payload 等) + 全量重导出

职责:
- 描述 config 顶层每个可编辑键的展示方式(分组/标签/控件类型/单位/枚举/帮助/必填)
- 描述 trackers 站点段与站点 hr 段字段
- 描述规则级字段与全部条件/动作插件的 spec 结构

设计约束(与 memory-bank/conventions.md 一致):
1. **不承载正确性规则**: 合法性唯一入口仍是 config.validate_config(本模块只做输入提示与控件选择),
   前端提交的仍是 YAML 形状树, 由 load_config 走与启动完全相同的校验路径。
2. **键集合必须与 validation.KNOWN_*_KEYS 完全一致** —— 由 tests/test_config_schema.py 守卫,
   新增配置键若忘记登记此处, 守卫测试直接失败(保证"每一项配置都可图形化")。
3. **插件表必须覆盖 registry 注册的全部插件** —— 同样由守卫测试保证(15 条件 / 12 动作)。
4. 热重载级别不在此声明: 唯一来源是 config/impact.py(SECTION_LEVELS/TRACKER_FIELD_LEVELS),
   API 层负责合并, 避免双份维护。

字段键名与 YAML 空间一致(标量全为字符串), 前端持有的树即磁盘 YAML 的同构表示。
"""
from typing import Any, Dict, Tuple

from .fields import (
    CHECKING_BASIC,
    CHECKING_MODES,
    DELETED_ALLOWED_ACTIONS,
    EXECUTE_ONCE,
    Field,
    Group,
    HR_MODES,
    ITEM_KINDS,
    KINDS,
    LOG_LEVELS,
    NOTIFY_CHANNELS,
    NOTIFY_LEVELS,
    Plugin,
    SIZE_UNITS,
    SPEC_KINDS,
    SPEED_UNITS,
    STATE_ATTRS,
    STOP_IF,
    TIME_UNITS,
    TRIGGERS,
    UNIT_KINDS,
)
from .groups import GROUPS
from .rules import ACTION_PLUGINS, CHECKING_SECTION_FIELDS, CONDITION_PLUGINS, RULE_FIELDS
from .trackers import HR_OUTPUT_FIELDS, TRACKER_FIELDS, TRACKER_HR_FIELDS

__all__ = [
    "Field", "Group", "Plugin",
    "KINDS", "UNIT_KINDS", "TIME_UNITS", "SIZE_UNITS", "SPEED_UNITS", "SPEC_KINDS", "ITEM_KINDS",
    "LOG_LEVELS", "NOTIFY_LEVELS", "NOTIFY_CHANNELS", "EXECUTE_ONCE", "STOP_IF", "TRIGGERS",
    "CHECKING_BASIC", "CHECKING_MODES", "HR_MODES", "STATE_ATTRS", "DELETED_ALLOWED_ACTIONS",
    "HR_OUTPUT_FIELDS", "TRACKER_HR_FIELDS", "TRACKER_FIELDS",
    "RULE_FIELDS", "CONDITION_PLUGINS", "CHECKING_SECTION_FIELDS", "ACTION_PLUGINS",
    "GROUPS",
    "config_fields", "real_config_fields", "plugin_table", "plugins_by_kind", "schema_payload",
]


def config_fields() -> Tuple[Field, ...]:
    """全部 config 顶层字段(守卫测试与键集合导出的单一入口)"""
    return tuple(f for g in GROUPS for f in g.fields)

def real_config_fields() -> Tuple[Field, ...]:
    """对应真实配置键的顶层字段(排除 UI 专段入口)"""
    return tuple(f for f in config_fields() if not f.ui_only)

def plugin_table() -> Dict[str, Tuple[Plugin, ...]]:
    """插件元数据表: {"condition": (...), "action": (...)}"""
    return {"condition": CONDITION_PLUGINS, "action": ACTION_PLUGINS}

def plugins_by_kind(kind: str) -> Dict[str, Plugin]:
    """按插件名索引的元数据(供前端按名查 spec 结构)"""
    return {p.name: p for p in (CONDITION_PLUGINS if kind == "condition" else ACTION_PLUGINS)}

def schema_payload() -> Dict[str, Any]:
    """给 /api/config/schema 的完整载荷(热重载级别不在此, 由 API 层合并)"""
    return {
        "groups": GROUPS,
        "tracker_fields": TRACKER_FIELDS,
        "rule_fields": RULE_FIELDS,
        "plugins": plugin_table(),
        "constants":
            {
                "log_levels": list(LOG_LEVELS),
                "notify_levels": list(NOTIFY_LEVELS),
                "notify_channels": list(NOTIFY_CHANNELS),
                "execute_once": list(EXECUTE_ONCE),
                "stop_if": list(STOP_IF),
                "triggers": list(TRIGGERS),
                "checking_basic": list(CHECKING_BASIC),
                "checking_modes": list(CHECKING_MODES),
                "hr_modes": list(HR_MODES),
                "state_attrs": list(STATE_ATTRS),
                "deleted_allowed_actions": list(DELETED_ALLOWED_ACTIONS),
            },
    }

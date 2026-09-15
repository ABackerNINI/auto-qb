"""schema 基础件: Field/Group/Plugin 数据类 + 控件 kind 与选项常量(纯声明)

config.schema 包拆分(2026-09-15 大文件拆分批次二): 本模块无项目内依赖,
其余 schema 子模块(trackers/rules/groups)全部由它派生。
"""
from dataclasses import dataclass
from typing import Any, Optional, Tuple
# 前端渲染契约: kind 决定控件类型; 未知 kind 退化为单行文本框(向前兼容)
#   bool 开关 | int 整数 | float 小数 | str 单行 | text 多行 | password 密码
#   enum 下拉 | range 区间串(a-b 或单值) | time 时间串 | size 大小串 | speed 速度串
#   ratio 触发条件串(80%) | path 路径串
#   str_list 普通字符串列表 | pattern_list 模式列表(regex:/:ignore_case)
#   compare_size / compare_time / compare_number 比较表达式
#   object 子表单 | keyed_list 单键映射列表 | curve / trackers / rules 专段编辑器
KINDS = frozenset(
    {
        "bool",
        "int",
        "float",
        "str",
        "text",
        "password",
        "enum",
        "range",
        "time",
        "size",
        "speed",
        "ratio",
        "path",
        "str_list",
        "pattern_list",
        "compare_size",
        "compare_time",
        "compare_number",
        "object",
        "keyed_list",
        "curve",
        "trackers",
        "rules",
        "rules_ref",
    }
)

# 数值 + 单位下拉的适用 kind(前端 UNIT_OPTIONS 表与之对应): 这些 kind 的输入框
# 渲染为 "数值框 + 单位下拉", 不再让用户手写 "30M"/"10MiB" 这类复合串
UNIT_KINDS = frozenset({"time", "size", "speed"})

TIME_UNITS = ("S", "M", "H", "D")

SIZE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB")

SPEED_UNITS = ("B/s", "KiB/s", "MiB/s", "GiB/s")

# 插件 spec 形态(Plugin.spec_kind), 前端据此选择控件
SPEC_KINDS = frozenset({"str", "bool", "list", "object", "enum", "speed"})

# 插件列表项编辑方式(Plugin.item_kind): str 普通串 | pattern 模式串 | tag_group 逗号分组 | state_group 状态组
ITEM_KINDS = frozenset({"str", "pattern", "tag_group", "state_group"})


@dataclass(frozen=True)
class Field:
    """一个可编辑字段的 UI 元数据

    key:        YAML 空间键名(与 validation 的已知键一致)
    kind:       控件类型(见 KINDS)
    default:    "新增条目/新建站点/新建规则"时的初始值(YAML 空间, 标量为字符串); 仅作初始值, 非校验依据
    unit:       输入框单位提示(时间/大小/速度等)
    options:    enum 的可选值
    show_if:    (同段字段 key, 触发值) —— 仅当该字段等于该值时显示(如 checking 的自定义程序路径)
    fields:     kind == "object" 时的子字段
    optional:   object 字段是否可整段省略(前端以开关控制该键存在性, 子字段随之显示/隐藏)
    ui_only:    UI 专段入口(不对应真实配置键, 如规则集 "rules" 对应动态的 *_rules 键)
    unit_default: kind 属 UNIT_KINDS 时的**首选单位**(未配置/无法解析该值时下拉框的初值)。
                  留空则前端回退到该 kind 的第一个单位; 常见值可由默认值后缀直接读出
                  (如 default="3D" -> D), 只有需要偏离默认值后缀时才显式声明
                  (如 extra_seeding_time 的 default 为 0S, 但用户习惯从 H 开始填)。
    """
    key: str
    label: str
    kind: str = "str"
    default: Any = None
    unit: str = ""
    options: Tuple[str, ...] = ()
    help: str = ""
    required: bool = False
    placeholder: str = ""
    show_if: Tuple[str, str] = ()
    min: Optional[float] = None
    max: Optional[float] = None
    fields: Tuple["Field", ...] = ()
    optional: bool = False
    ui_only: bool = False
    grey_if: Tuple[str, str] = ()
    group_of: str = ""
    risk: str = ""
    unit_default: str = ""
    open: bool = False  # object 段缺省展开态(True = 不折叠, 如 日志/WEB UI/通知 这类短段)


@dataclass(frozen=True)
class Group:
    """左侧导航分组: 一组顶层配置键(按声明顺序展示)"""
    key: str
    label: str
    help: str = ""
    fields: Tuple[Field, ...] = ()
    icon: str = ""  # sprite symbol id(如 i-settings); 空 = 前端用默认图标


@dataclass(frozen=True)
class Plugin:
    """条件/动作插件 UI 元数据

    spec_kind: 单值 "str" | 开关 "bool" | 列表 "list" | 子表单 "object" | 枚举 "enum" | 速度 "speed"
    item_kind: spec_kind == "list" 时列表项的编辑方式(见 ITEM_KINDS)
    options:   spec_kind == "enum" 时的可选值
    fields:    spec_kind == "object" 时的子字段
    """
    name: str
    label: str
    kind: str  # condition | action
    spec_kind: str
    help: str = ""
    item_kind: str = ""
    options: Tuple[str, ...] = ()
    placeholder: str = ""
    fields: Tuple[Field, ...] = ()
    risk: str = ""  # 非空 = 高风险插件(前端在卡片头显示醒目警示)


LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

NOTIFY_LEVELS = ("INFO", "WARNING", "ERROR")

NOTIFY_CHANNELS = ("platform", )

EXECUTE_ONCE = ("never", "once", "daily", "hourly")

STOP_IF = ("conditions-met", "conditions-not-met", "action-failed", "all-actions-succeed", "always", "never")

TRIGGERS = ("interval", "on_torrent_added", "on_torrent_deleted", "on_torrent_state_enum_changed")

CHECKING_BASIC = ("filelist", "piecehashes", "custom")

CHECKING_MODES = ("skip-checking", "full-checking")

HR_MODES = ("condition-met", "condition-not-met", "satisfied")

# state 条件的 is_* 类别属性(与 validation._validate_state_condition_spec 一致)
STATE_ATTRS = ("is_downloading", "is_uploading", "is_complete", "is_checking", "is_stopped", "is_paused", "is_errored")

# on_torrent_deleted 允许的动作(与 validation.DELETED_TRIGGER_ALLOWED_ACTIONS 一致)
DELETED_ALLOWED_ACTIONS = ("print_torrent_details", )

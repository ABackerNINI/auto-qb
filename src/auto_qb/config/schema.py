"""配置 UI 元数据: WEB UI 图形化配置编辑器的唯一描述来源(纯声明, 无副作用)

职责:
- 描述 config 顶层每个可编辑键的展示方式(分组/标签/控件类型/单位/枚举/帮助/必填)
- 描述 trackers 站点段与站点 hr 段字段
- 描述规则级字段与全部条件/动作插件的 spec 结构

设计约束(与 ai/06 一致):
1. **不承载正确性规则**: 合法性唯一入口仍是 config.validate_config(本模块只做输入提示与控件选择),
   前端提交的仍是 YAML 形状树, 由 load_config 走与启动完全相同的校验路径。
2. **键集合必须与 validation.KNOWN_*_KEYS 完全一致** —— 由 tests/test_config_schema.py 守卫,
   新增配置键若忘记登记此处, 守卫测试直接失败(保证"每一项配置都可图形化")。
3. **插件表必须覆盖 registry 注册的全部插件** —— 同样由守卫测试保证(15 条件 / 12 动作)。
4. 热重载级别不在此声明: 唯一来源是 config/impact.py(SECTION_LEVELS/TRACKER_FIELD_LEVELS),
   API 层负责合并, 避免双份维护。

字段键名与 YAML 空间一致(标量全为字符串), 前端持有的树即磁盘 YAML 的同构表示。
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

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
    }
)

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


@dataclass(frozen=True)
class Group:
    """左侧导航分组: 一组顶层配置键(按声明顺序展示)"""
    key: str
    label: str
    help: str = ""
    fields: Tuple[Field, ...] = ()


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


# ---------------------------------------------------------------- 通用选项

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

# ---------------------------------------------------------------- HR 输出字段(全局/站点共用)

HR_OUTPUT_FIELDS: Tuple[Field, ...] = (
    Field("add_tag", "触发后添加标签", "str", default="", help="支持 ${required_seeding_time} 变量"),
    Field("add_category", "触发后设置分类", "str", default="", help="支持 ${required_seeding_time} 变量"),
    Field("overwrite_category", "覆盖已有分类", "bool", default="false", help="关闭时仅覆盖本程序上次自动设置的分类"),
    Field("add_tag_for_satisfied", "达标后添加标签", "str", default="", help="做种时长满足要求+额外时间后添加"),
    Field("add_category_for_satisfied", "达标后设置分类", "str", default="", help="同上, 分类形式"),
    Field("overwrite_category_for_satisfied", "达标后覆盖分类", "bool", default="false", help="达标分支是否覆盖已有分类"),
)

# ---------------------------------------------------------------- 站点段字段

TRACKER_HR_FIELDS: Tuple[Field, ...] = (
    Field("required_seeding_time", "要求做种时长", "time", default="3D", required=True, help="如 3D / 12H / 1.5D"),
    Field("required_share_ratio", "要求分享率", "float", default="0", help="0 = 不要求"),
    Field("extra_seeding_time", "额外做种时间", "time", default="0S", help="满足 要求+额外 视为达标"),
    Field("condition", "HR 触发条件", "ratio", default="80%", help="如 80% 或 10MiB"),
) + HR_OUTPUT_FIELDS

TRACKER_FIELDS: Tuple[Field, ...] = (
    Field("domains", "站点域名", "str_list", default=[], required=True, help="按 hostname 精确匹配(含子域名); 必填"),
    Field("tags", "站点标签", "str_list", default=[], help="种子匹配该站点时由维护任务添加"),
    Field("remove_tags", "删除标签格式", "pattern_list", default=[], help="支持 regex: 前缀与 :ignore_case 后缀"),
    Field("upload_speed_limit", "单种上传限速", "speed", default="0KiB/s", help="0 = 不限速; 奇数 KiB/s 视为用户手动设置, 不覆盖"),
    Field("download_speed_limit", "单种下载限速", "speed", default="0KiB/s", help="0 = 不限速"),
    Field("hr", "HR 规则", "object", default=None, optional=True, help="未配置 = 该站点不做 HR 管理", fields=TRACKER_HR_FIELDS),
    Field("rules", "引用的规则", "str_list", default=[], help="格式 @规则集 或 @规则集.规则名"),
    Field("remove_similar_tags", "删除类似标签", "bool", default="false", help="未配置时回退全局值"),
)

# ---------------------------------------------------------------- 规则集字段

RULE_FIELDS: Tuple[Field, ...] = (
    Field("enabled", "启用", "bool", default="true"),
    Field("trigger", "触发时机", "enum", default="interval", options=TRIGGERS, help="interval 周期轮询; 其余为事件触发(一次性, 不建周期任务)"),
    Field("interval", "扫描间隔", "time", default="0S", unit="S/M/H/D", help="0 = 每轮"),
    Field("execute_once", "执行一次", "enum", default="never", options=EXECUTE_ONCE, help="非幂等动作(校验/开始/汇报/限速)建议配置"),
    Field("cooldown", "冷却时间", "time", default="0S", unit="S/M/H/D", help="距上次成功不足该时间则跳过; 优先于 execute_once"),
    Field("stop_following_rules_if", "停止后续规则", "enum", default="conditions-met", options=STOP_IF),
)

# ---------------------------------------------------------------- 条件插件(15)

CONDITION_PLUGINS: Tuple[Plugin, ...] = (
    Plugin(
        "path",
        "路径",
        "condition",
        "list",
        "匹配 save_path 或 content_path; 列表为或关系",
        item_kind="pattern",
        placeholder="/downloads/anime"
    ),
    Plugin("size", "种子大小", "condition", "str", "比较种子总大小", placeholder=">=100MiB"),
    Plugin(
        "tags",
        "标签",
        "condition",
        "list",
        "组间为或, 组内逗号分隔为与; 支持 regex:/:ignore_case",
        item_kind="tag_group",
        placeholder="tag1,tag2"
    ),
    Plugin(
        "category",
        "分类",
        "condition",
        "list",
        "列表为或关系; 支持 regex:/:ignore_case",
        item_kind="pattern",
        placeholder="regex:^HR"
    ),
    Plugin("trackers", "站点", "condition", "list", "匹配站点配置名(非域名); 列表为或关系", item_kind="pattern", placeholder="HHan"),
    Plugin(
        "state",
        "状态",
        "condition",
        "list",
        "组间为或, 组内 & 连接为与",
        item_kind="state_group",
        placeholder="is_complete&is_uploading"
    ),
    Plugin("hr", "HR 条件", "condition", "enum", "依赖站点 HR 配置; 无 HR 配置的站点一律不匹配", options=HR_MODES),
    Plugin(
        "date_time",
        "日期时间",
        "condition",
        "object",
        "各项留空 = 不检查该项",
        fields=(
            Field("day_of_month", "每月第几天", "range", default="", unit="1-31", placeholder="1-31"),
            Field("day_of_week", "星期几", "range", default="", unit="1-7", placeholder="1-7", help="1 = 周一"),
            Field("time", "时间区间", "str", default="", placeholder="10:00-23:00", help="支持跨午夜"),
        )
    ),
    Plugin("seedtime", "做种时长", "condition", "str", "比较种子做种秒数", placeholder="<24H"),
    Plugin("upload_ratio", "分享率", "condition", "str", "比较种子分享率", placeholder=">1.5"),
    Plugin("upload_size", "总上传量", "condition", "str", "比较种子累计上传量", placeholder=">10GiB"),
    Plugin("upload_size_today", "今日上传量", "condition", "str", "基于状态文件基线的自然日增量", placeholder=">10GiB"),
    Plugin("upload_size_this_week", "本周上传量", "condition", "str", "ISO 周增量", placeholder=">10GiB"),
    Plugin("upload_size_this_month", "本月上传量", "condition", "str", "自然月增量", placeholder=">10GiB"),
    Plugin(
        "freespace",
        "磁盘可用空间",
        "condition",
        "object",
        "路径为空或不可用时视为不匹配",
        fields=(
            Field("path", "检查路径", "path", default="", required=True, placeholder="R:/"),
            Field("amount", "可用空间条件", "compare_size", default="<100GiB", required=True, placeholder="<100GiB"),
        )
    ),
)

# ---------------------------------------------------------------- 动作插件(12)

CHECKING_SECTION_FIELDS: Tuple[Field, ...] = (
    Field("enabled", "启用该分支", "bool", default="false"),
    Field(
        "mode",
        "校验方式",
        "enum",
        default="skip-checking",
        options=CHECKING_MODES,
        help="skip-checking 跳检(删种重加); full-checking 强制哈希校验"
    ),
    Field("auto_start", "校验后自动开始", "bool", default="false"),
)

ACTION_PLUGINS: Tuple[Plugin, ...] = (
    Plugin(
        "add_tags",
        "添加标签",
        "action",
        "list",
        "已存在则跳过; 支持 ${required_seeding_time}",
        item_kind="str",
        placeholder="tag-${required_seeding_time}"
    ),
    Plugin(
        "remove_tags",
        "删除标签",
        "action",
        "list",
        "支持 regex:/:ignore_case 与变量替换",
        item_kind="pattern",
        placeholder="regex:^tag"
    ),
    Plugin(
        "add_category",
        "设置分类",
        "action",
        "object",
        "已设置/已有分类且不允许覆盖时跳过",
        fields=(
            Field("format", "分类名称", "str", default="", required=True, help="支持 ${required_seeding_time}"),
            Field("overwrite", "覆盖已有分类", "bool", default="false", help="关闭时仅覆盖本程序上次自动设置的分类"),
        )
    ),
    Plugin("remove_category", "清空分类", "action", "bool", "分类为空时跳过"),
    Plugin("start", "开始种子", "action", "bool", "已开始则跳过"),
    Plugin("stop", "暂停种子", "action", "bool", "已暂停则跳过"),
    Plugin("print_torrent_details", "打印种子详情", "action", "bool", "只读留档动作; on_torrent_deleted 触发下唯一允许的动作"),
    Plugin(
        "checking",
        "校验/跳检",
        "action",
        "object",
        "用参考种子判定后跳检或强制校验(高风险, 需配合去重配置)",
        fields=(
            Field(
                "basic_check",
                "参考判定方式",
                "enum",
                default="filelist",
                required=True,
                options=CHECKING_BASIC,
                help="filelist 文件列表 / piecehashes 分片哈希 / custom 自定义程序"
            ),
            Field(
                "custom_basic_check_program_path",
                "自定义程序路径",
                "path",
                default="",
                show_if=("basic_check", "custom"),
                help="参数: <种子hash> <保存路径>, 返回码 0 即为参考"
            ),
            Field("with_reference", "有参考种子", "object", default=None, optional=True, fields=CHECKING_SECTION_FIELDS),
            Field(
                "without_reference",
                "无参考种子",
                "object",
                default=None,
                optional=True,
                help="跳检为高风险动作",
                fields=CHECKING_SECTION_FIELDS
            ),
        )
    ),
    Plugin(
        "move_to",
        "移动种子",
        "action",
        "object",
        "调用 qB set_location",
        fields=(Field("path", "目标路径", "path", default="", required=True, placeholder="R:/seeds"), )
    ),
    Plugin("reannounce", "强制汇报", "action", "bool", "⚠️ 高风险: 动作内置 10 分钟最小间隔, 未配去重时启动告警"),
    Plugin("upload_speed_limit", "上传限速", "action", "speed", "0 = 不限速; 奇数 KiB/s 视为用户手动设置, 不覆盖", placeholder="1000KiB/s"),
    Plugin("download_speed_limit", "下载限速", "action", "speed", "0 = 不限速", placeholder="1000KiB/s"),
)

# ---------------------------------------------------------------- 顶层分组(顺序即表单顺序)

GROUPS: Tuple[Group, ...] = (
    Group(
        "basic",
        "基础",
        "qBittorrent 连接与主循环节奏",
        fields=(
            Field(
                "qbittorrent",
                "qBittorrent",
                "object",
                help="主程序连接的客户端",
                fields=(
                    Field("host", "主机", "str", default="127.0.0.1", required=True),
                    Field("port", "端口", "int", default="8080", required=True, min=1, max=65535),
                    Field("username", "用户名", "str", default=""),
                    Field("password", "密码", "password", default=""),
                )
            ),
            Field("main_tick", "主循环间隔", "time", default="2S", unit="S/M/H/D", required=True, help="必须为正时间, 防止忙循环"),
            Field("max_tasks_per_tick", "每轮最大任务数", "int", default="20", min=1),
            Field("interval", "内置任务间隔", "time", default="60S", unit="S/M/H/D", help="从上一轮结束起算, 不叠加"),
            Field("data_dir", "运行时数据目录", "path", default="auto-qb-data", help="⚠️ 修改需重启进程; 状态/锁/日志/跳检备份默认派生其下"),
            Field("state_file", "状态文件", "path", default="", help="⚠️ 修改需重启进程; 留空 = <data_dir>/state.json"),
        )
    ),
    Group(
        "logging",
        "日志",
        "落盘轮转与格式",
        fields=(
            Field(
                "log",
                "日志设置",
                "object",
                fields=(
                    Field("level", "日志等级", "enum", default="INFO", options=LOG_LEVELS),
                    Field("file", "日志文件", "path", default="", help="留空 = <data_dir>/logs/auto-qb.log"),
                    Field("max_bytes", "轮转大小", "size", default="10MiB", help="保留 5 个备份"),
                    Field("format", "日志格式", "str", default="%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
                )
            ),
        )
    ),
    Group(
        "web",
        "WEB UI",
        "图形界面的监听与鉴权",
        fields=(
            Field(
                "web",
                "WEB UI",
                "object",
                fields=(
                    Field("enabled", "启用", "bool", default="false"),
                    Field("host", "监听地址", "str", default="127.0.0.1", help="⚠️ 改为 0.0.0.0 会把可删除种子的管理接口暴露到网络"),
                    Field("port", "监听端口", "int", default="8080", min=1, max=65535),
                    Field("token", "访问密钥", "password", default="", help="留空 = 首次启动随机生成并持久化到 data_dir/web.token"),
                )
            ),
        )
    ),
    Group(
        "notify",
        "通知",
        "WARNING 及以上日志推送平台原生通知",
        fields=(
            Field(
                "notify",
                "主动通知",
                "object",
                fields=(
                    Field("enabled", "启用", "bool", default="false"),
                    Field("min_level", "最低通知级别", "enum", default="WARNING", options=NOTIFY_LEVELS),
                    Field("quiet_hours", "免打扰时段", "str", default="", placeholder="23:00-08:00", help="支持跨午夜; 留空不启用"),
                    Field("max_per_hour", "每小时上限", "int", default="20", min=1, help="超出丢弃, 防通知风暴"),
                    Field("dedup_window", "去重窗口", "time", default="10M", unit="S/M/H/D", help="0 = 不去重"),
                    Field(
                        "channels",
                        "通知渠道",
                        "keyed_list",
                        default=["platform"],
                        options=NOTIFY_CHANNELS,
                        help="当前仅支持平台原生通知"
                    ),
                )
            ),
        )
    ),
    Group(
        "maintenance",
        "自动化",
        "标签/分类/HR/辅种分组管理",
        fields=(
            Field("remove_similar_tags", "删除类似标签", "bool", default="false", help="全局默认, 站点可覆盖; 删除大小写不同的同名标签"),
            Field("skip_checking_tag", "跳检标签名", "str", default="zSkipChecked", help="带此标签的种子未经哈希校验, 查找参考种子时一律排除"),
            Field(
                "grouping",
                "辅种分组",
                "object",
                help="相同文件列表的种子归为一组统一检查",
                fields=(
                    Field("enabled", "启用分组", "bool", default="true"),
                    Field("check_missing_files", "启用缺文件检查", "bool", default="true"),
                    Field("missing_tag", "缺文件标签", "str", default="MISSING"),
                )
            ),
            Field(
                "add_episode_tags",
                "集数标签",
                "object",
                help="仅在种子新增时触发; 多集不连续则不添加",
                fields=(
                    Field("enabled", "启用", "bool", default="false"),
                    Field("add_tag_single", "单集模板", "str", default="zE${episode_first}"),
                    Field("add_tag_multi", "多集模板", "str", default="zE${episode_first}-${episode_last}"),
                )
            ),
            Field(
                "delete_tags",
                "彻底删除标签",
                "pattern_list",
                default=[],
                help="匹配的标签对所有种子彻底删除; 支持 regex:/:ignore_case 与 @tracker_tags 引用"
            ),
            Field("delete_tags_if_has_no_torrents", "删除无种子标签", "pattern_list", default=[], help="仅当没有任何种子使用该标签时删除"),
            Field("hr", "HR 全局默认", "object", help="站点 hr 段未设置输出字段时回退此处", fields=HR_OUTPUT_FIELDS),
        )
    ),
    Group(
        "speed",
        "限速曲线",
        "按累计流量自动设置 qB 全局限速",
        fields=(
            Field(
                "global_speed_limit_curve",
                "全局限速曲线",
                "curve",
                default=None,
                help="读取 Traffic Monitor 数据, 按 day/month/Nd 累计聚合分档限速"
            ),
        )
    ),
    Group(
        "trackers",
        "站点",
        "站点匹配、标签、限速与 HR",
        fields=(Field("trackers", "站点列表", "trackers", default={}, help="按域名匹配; 未配置的站点不做任何管理"), )
    ),
    Group(
        "rules",
        "规则集",
        "条件 + 动作的自动化规则",
        fields=(
            # UI 专段: 真实配置键是动态的 "<名称>_rules"(规则集名由用户自定), 故标记 ui_only
            Field("rules", "规则集", "rules", default={}, ui_only=True, help="config 段下所有以 _rules 结尾的键"),
        )
    ),
)


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

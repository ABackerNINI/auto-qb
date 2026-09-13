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
    Field(
        "add_tag",
        "触发后添加标签",
        "str",
        default="",
        help="已触发 HR(下载量/比例达条件)但尚未满足做种时长/分享率时自动添加的标签; 支持 ${required_seeding_time} 变量; 留空 = 不添加"
    ),
    Field(
        "add_category",
        "触发后设置分类",
        "str",
        default="",
        help="同上, 但设置的是分类(一个种子只能有一个分类); 留空 = 不设置",
    ),
    Field(
        "overwrite_category",
        "覆盖已有分类",
        "bool",
        default="false",
        group_of="add_category",
        risk="开启后会覆盖人工设置的分类; 关闭时仅覆盖本程序上次自动设置的分类",
    ),
    Field(
        "add_tag_for_satisfied",
        "达标后添加标签",
        "str",
        default="",
        help="做种时长已达要求 + 额外时间(或分享率达标)后添加的标签; 用于标记“HR 已完成”; 可自行删除, 本程序不会再添加",
    ),
    Field(
        "add_category_for_satisfied",
        "达标后设置分类",
        "str",
        default="",
        help="达标分支设置的分类; 留空 = 不设置",
    ),
    Field(
        "overwrite_category_for_satisfied",
        "达标后覆盖分类",
        "bool",
        default="false",
        group_of="add_category_for_satisfied",
        risk="开启后会覆盖人工设置的分类",
    ),
)

# ---------------------------------------------------------------- 站点段字段

TRACKER_HR_FIELDS: Tuple[Field, ...] = (
    Field(
        "required_seeding_time",
        "要求做种时长",
        "time",
        default="3D",
        required=True,
        help="站点要求的做种时长(如 3D = 3 天 / 12H / 1.5D); 达到该时长才算满足 HR"
    ),
    Field("required_share_ratio", "要求分享率", "float", default="0", help="上传量/下载量 达到该值也算满足 HR(与做种时长二选一); 0 = 不要求"),
    Field(
        "extra_seeding_time",
        "额外做种时间",
        "time",
        default="0H",
        unit_default="H",
        help="缓冲量: 要求时长 + 额外时长 才判定达标(避免刚好卡在边界时被站点判定未达标)"
    ),
    Field(
        "condition", "HR 触发条件", "ratio", default="80%", help="下载比例(如 80%)或下载量(如 10MiB)达到该值即视为需要 HR 管理; 注意辅种(无下载量)不触发"
    ),
) + HR_OUTPUT_FIELDS

TRACKER_FIELDS: Tuple[Field, ...] = (
    Field(
        "domains",
        "站点域名",
        "str_list",
        default=[],
        required=True,
        help="按 hostname 精确匹配(含子域名), 例: hhanclub.net; 必填; 每行一个",
    ),
    Field("tags", "站点标签", "str_list", default=[], help="该站点的种子自动添加这些标签; 第一个标签同时用作日志/界面里的站点名"),
    Field(
        "remove_tags",
        "删除标签格式",
        "pattern_list",
        default=[],
        help="支持 regex: 前缀与 :ignore_case 后缀(可组合), 例: regex:^BTS / 'M-Team:ignore_case'",
        risk="匹配到的标签会从该站点的种子中删除",
    ),
    Field(
        "upload_speed_limit",
        "单种上传限速",
        "speed",
        default="0KiB/s",
        help="种子添加时写入 qB 的单种限速; 0 = 不限速; 奇数值(如 2001KiB/s)视为手动设置, 本程序不覆盖",
    ),
    Field("download_speed_limit", "单种下载限速", "speed", default="0KiB/s", help="同上, 作用于下载; 0 = 不限速"),
    Field(
        "hr",
        "HR 规则",
        "object",
        default=None,
        optional=True,
        help="未配置该段 = 该站点不做 HR 管理(不打 HR 标签/分类)",
        fields=TRACKER_HR_FIELDS
    ),
    Field(
        "rules",
        "引用的规则",
        "rules_ref",
        default=[],
        help="填写 @规则集 或 @规则集.规则名(可从右侧下拉选, 也可直接粘贴); 留空 = 该站点不执行任何规则——不会回退为\"执行全部启用规则\""
    ),
    Field(
        "remove_similar_tags",
        "删除类似标签",
        "bool",
        default="false",
        help="未配置时回退全局 自动化.删除类似标签 的值; 删除仅大小写不同的同名标签",
    ),
)

# ---------------------------------------------------------------- 规则集字段

RULE_FIELDS: Tuple[Field, ...] = (
    Field("enabled", "启用", "bool", default="true", help="关闭后该规则不参与任何匹配与执行"),
    Field(
        "trigger",
        "触发时机",
        "enum",
        default="interval",
        options=TRIGGERS,
        help="interval = 按扫描间隔周期检查; 其余为事件触发(种子新增/删除/状态变化时立即检查一次)",
    ),
    Field(
        "interval",
        "扫描间隔",
        "time",
        default="0S",
        help="仅 interval 触发时生效; 0 = 每轮都检查(受主循环间隔约束, 实际仍为 2s 级); 从上一轮结束起算, 不叠加"
    ),
    Field(
        "execute_once",
        "执行一次",
        "enum",
        default="never",
        options=EXECUTE_ONCE,
        help="窗口内最多成功执行一次(去重存于 state_file); 适合校验/开始/汇报等非幂等动作; 失败不计入"
    ),
    Field(
        "cooldown",
        "冷却时间",
        "time",
        default="0S",
        help="距上次成功不足该时间则跳过(优先于“执行一次”); 0 = 不冷却",
    ),
    Field(
        "stop_following_rules_if",
        "停止后续规则",
        "enum",
        default="conditions-met",
        options=STOP_IF,
        help="本规则条件满足后是否继续执行后续规则(优先级由规则列表顺序决定)",
    ),
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
        placeholder="regex:^tag",
        risk="匹配到的标签会从种子删除",
    ),
    Plugin(
        "add_category",
        "设置分类",
        "action",
        "object",
        "已设置/已有分类且不允许覆盖时跳过",
        fields=(
            Field("format", "分类名称", "str", default="", required=True, help="支持 ${required_seeding_time} 变量"),
            Field(
                "overwrite",
                "覆盖已有分类",
                "bool",
                default="false",
                group_of="format",
                risk="开启后会覆盖人工设置的分类; 关闭时仅覆盖本程序上次自动设置的分类",
            ),
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
        "用参考种子判定后跳检或强制校验",
        risk="跳检会删除种子并重新添加(期间停止做种), 请务必配置去重/冷却避免反复执行",
        fields=(
            Field(
                "basic_check",
                "参考判定方式",
                "enum",
                default="filelist",
                required=True,
                options=CHECKING_BASIC,
                help="filelist 比对文件列表 / piecehashes 比对分片哈希 / custom 调用自定义程序"
            ),
            Field(
                "custom_basic_check_program_path",
                "自定义程序路径",
                "path",
                default="",
                show_if=("basic_check", "custom"),
                risk="会以 <种子hash> <保存路径> 为参数执行该程序",
                placeholder="C:/tools/check.bat",
            ),
            Field("with_reference", "有参考种子", "object", default=None, optional=True, fields=CHECKING_SECTION_FIELDS),
            Field(
                "without_reference",
                "无参考种子",
                "object",
                default=None,
                optional=True,
                help="无参考种子时的处理方式(通常为跳检)",
                fields=CHECKING_SECTION_FIELDS
            ),
        )
    ),
    Plugin(
        "move_to",
        "移动种子",
        "action",
        "object",
        "调用 qB set_location(不移动磁盘文件, 仅改 qB 记录路径)",
        fields=(Field("path", "目标路径", "path", default="", required=True, placeholder="R:/seeds"), )
    ),
    Plugin("reannounce", "强制汇报", "action", "bool", "动作内置 10 分钟最小间隔, 未配去重时启动告警", risk="频繁汇报会被站点判定为异常流量"),
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
                help="主程序连接的客户端(需开启 WebUI)",
                fields=(
                    Field("host", "主机", "str", default="127.0.0.1", required=True, placeholder="127.0.0.1"),
                    Field("port", "端口", "int", default="8080", required=True, min=1, max=65535, help="qB WebUI 监听端口"),
                    Field("username", "用户名", "str", default="", help="qB WebUI 登录用户名"),
                    Field("password", "密码", "password", default="", help="qB WebUI 登录密码"),
                )
            ),
            Field(
                "main_tick",
                "主循环间隔",
                "time",
                default="2S",
                required=True,
                help="必须为正时间, 防止忙循环; 决定状态变化与数据刷新频率",
            ),
            Field(
                "max_tasks_per_tick",
                "每轮最大任务数",
                "int",
                default="20",
                min=1,
                help="单轮最多执行多少个到期任务; 过大可能使单轮阻塞过久",
            ),
            Field(
                "interval",
                "内置任务间隔",
                "time",
                default="60S",
                help="维护/全局清理/曲线等内置任务的周期; 从上一轮结束起算, 不叠加",
            ),
            Field(
                "data_dir",
                "运行时数据目录",
                "path",
                default="auto-qb-data",
                help="状态/锁/日志/跳检备份默认派生其下",
                risk="修改后需重启进程才生效",
            ),
            Field("state_file", "状态文件", "path", default="", help="留空 = <data_dir>/state.json", risk="修改后需重启进程才生效"),
        ),
        icon="i-settings",
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
                    Field(
                        "level",
                        "日志等级",
                        "enum",
                        default="INFO",
                        options=LOG_LEVELS,
                        help="低于该等级的日志不输出; 达到 通知.最低通知级别 的日志会推送通知"
                    ),
                    Field("file", "日志文件", "path", default="", help="留空 = <data_dir>/logs/auto-qb.log"),
                    Field(
                        "max_bytes",
                        "轮转大小",
                        "size",
                        default="10MiB",
                        unit_default="MiB",
                        help="单个日志文件上限, 超过则轮转; 保留 5 个备份"
                    ),
                    Field(
                        "format",
                        "日志格式",
                        "str",
                        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        help="Python logging 格式串, 可含 %(name)s(来源模块)",
                    ),
                )
            ),
        ),
        icon="i-list",
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
                    Field("enabled", "启用", "bool", default="false", help="启用后可在浏览器打开 主机:端口 管理辅种与配置"),
                    Field(
                        "host",
                        "监听地址",
                        "str",
                        default="127.0.0.1",
                        help="推荐保持 127.0.0.1(仅本机可访问)",
                        risk="改为 0.0.0.0 会把可暂停/删除种子的管理接口暴露到局域网",
                    ),
                    Field("port", "监听端口", "int", default="8080", min=1, max=65535, help="避免与 qB WebUI 端口冲突"),
                    Field("token", "访问密钥", "password", default="", help="留空 = 首次启动随机生成并持久化到 data_dir/web.token"),
                )
            ),
        ),
        icon="i-monitor",
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
                    Field("enabled", "启用", "bool", default="false", help="开启后无需额外配置, 日志即通知内容"),
                    Field(
                        "min_level",
                        "最低通知级别",
                        "enum",
                        default="WARNING",
                        options=NOTIFY_LEVELS,
                        grey_if=("enabled", "true"),
                        help="达到该等级的日志才会推送",
                    ),
                    Field(
                        "quiet_hours",
                        "免打扰时段",
                        "str",
                        default="",
                        placeholder="23:00-08:00",
                        grey_if=("enabled", "true"),
                        help="支持跨午夜; 留空不启用"
                    ),
                    Field(
                        "max_per_hour",
                        "每小时上限",
                        "int",
                        default="20",
                        min=1,
                        grey_if=("enabled", "true"),
                        help="超出丢弃, 防通知风暴"
                    ),
                    Field(
                        "dedup_window",
                        "去重窗口",
                        "time",
                        default="10M",
                        grey_if=("enabled", "true"),
                        help="窗口内相同内容的通知只推一次; 0 = 不去重",
                    ),
                    Field(
                        "channels",
                        "通知渠道",
                        "keyed_list",
                        default=["platform"],
                        options=NOTIFY_CHANNELS,
                        grey_if=("enabled", "true"),
                        help="当前仅支持平台原生通知"
                    ),
                )
            ),
        ),
        icon="i-bell",
    ),
    Group(
        "maintenance",
        "自动化",
        "标签/分类/HR/辅种分组管理",
        fields=(
            Field(
                "remove_similar_tags",
                "删除类似标签",
                "bool",
                default="false",
                help="全局默认, 站点可覆盖; 删除仅大小写不同的同名标签(如 HHan 与 hhan)"
            ),
            Field(
                "skip_checking_tag",
                "跳检标签名",
                "str",
                default="zSkipChecked",
                help="带此标签的种子未经哈希校验, 查找参考种子时一律排除; 留空 = 禁用",
            ),
            Field(
                "grouping",
                "辅种分组",
                "object",
                help="把文件列表相同的种子归为一组, 统一检查缺文件并避免重复下载",
                fields=(
                    Field("enabled", "启用分组", "bool", default="true", help="开启后替代单种子的缺文件检查"),
                    Field(
                        "check_missing_files",
                        "启用缺文件检查",
                        "bool",
                        default="true",
                        grey_if=("enabled", "true"),
                        help="扫描代表种子的磁盘文件, 缺失则暂停整组并打标签",
                    ),
                    Field(
                        "missing_tag",
                        "缺文件标签",
                        "str",
                        default="MISSING",
                        grey_if=("enabled", "true"),
                        help="发现缺文件时给组内每个种子添加的标签",
                    ),
                )
            ),
            Field(
                "add_episode_tags",
                "集数标签",
                "object",
                help="仅在种子新增时触发; 集数不连续时不做任何处理",
                fields=(
                    Field("enabled", "启用", "bool", default="false", help="开启后按文件名中的集数自动打标签"),
                    Field(
                        "add_tag_single",
                        "单集模板",
                        "str",
                        default="zE${episode_first}",
                        grey_if=("enabled", "true"),
                        help="${episode_first} = 集数; 例: zE01"
                    ),
                    Field(
                        "add_tag_multi",
                        "多集模板",
                        "str",
                        default="zE${episode_first}-${episode_last}",
                        grey_if=("enabled", "true"),
                        help="${episode_first}/${episode_last} = 首/末集; 例: zE01-12"
                    ),
                )
            ),
            Field(
                "delete_tags",
                "彻底删除标签",
                "pattern_list",
                default=[],
                help="匹配的标签从所有种子与全局标签表中删除; 支持 regex:/:ignore_case 与 @tracker_tags 引用",
                risk="标签定义一并删除, 相关自动化(如 HR 标记)会随之失效",
            ),
            Field(
                "delete_tags_if_has_no_torrents",
                "删除无种子标签",
                "pattern_list",
                default=[],
                help="仅当没有任何种子使用该标签时才删除(清理残留标签定义)"
            ),
            Field("hr", "HR 全局默认", "object", help="站点 hr 段未设置输出字段时回退此处", fields=HR_OUTPUT_FIELDS),
        ),
        icon="i-cards",
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
                help="读取 Traffic Monitor 数据, 按 day/month/Nd 累计流量分档限速(0 = 该档不限速)"
            ),
        ),
        icon="i-gauge",
    ),
    Group(
        "trackers",
        "站点",
        "站点匹配、标签、限速与 HR",
        fields=(Field("trackers", "站点列表", "trackers", default={}, help="按域名匹配; 未配置的站点不做任何管理"), ),
        icon="i-globe",
    ),
    Group(
        "rules",
        "规则集",
        "条件 + 动作的自动化规则",
        fields=(
            # UI 专段: 真实配置键是动态的 "<名称>_rules"(规则集名由用户自定), 故标记 ui_only
            Field("rules", "规则集", "rules", default={}, ui_only=True, help="config 段下所有以 _rules 结尾的键"),
        ),
        icon="i-bolt",
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

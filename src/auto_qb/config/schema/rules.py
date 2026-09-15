"""schema 规则集段: 规则字段 + 条件/动作插件 spec 元数据"""
from typing import Tuple
from .fields import CHECKING_BASIC, CHECKING_MODES, EXECUTE_ONCE, Field, HR_MODES, Plugin, STOP_IF, TRIGGERS

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

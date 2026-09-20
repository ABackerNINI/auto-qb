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
        help="何时检查该规则: interval = 按扫描间隔周期检查; 其余为事件触发(种子新增/删除/状态变化时立即检查一次)",
    ),
    Field("interval", "扫描间隔", "time", default="0S", help="多久检查一次该规则(仅周期触发时生效); 0 = 每轮都检查; 以上一轮结束起算, 不会叠加"),
    Field(
        "execute_once",
        "执行一次",
        "enum",
        default="never",
        options=EXECUTE_ONCE,
        help="窗口内最多成功执行一次, 重启也不重试(记录保存在运行状态文件里); 适合校验/开始/汇报这类不该反复执行的动作; 失败不计入"
    ),
    Field(
        "cooldown",
        "冷却时间",
        "time",
        default="0S",
        help="距上次成功执行不足该时间就先跳过(优先级高于「执行一次」); 0 = 不冷却",
    ),
    Field(
        "stop_following_rules_if",
        "停止后续规则",
        "enum",
        default="conditions-met",
        options=STOP_IF,
        help="什么情况下不再执行列表中排在后面的规则(默认: 条件满足后就停; 规则先后按列表顺序)",
    ),
)

CONDITION_PLUGINS: Tuple[Plugin, ...] = (
    Plugin(
        "path",
        "路径",
        "condition",
        "list",
        "按种子保存路径匹配(命中任意一条即满足); 支持正则",
        item_kind="pattern",
        placeholder="/downloads/anime"
    ),
    Plugin("size", "种子大小", "condition", "str", "按种子总大小比较", placeholder=">=100MiB"),
    Plugin(
        "tags",
        "标签",
        "condition",
        "list",
        "按种子标签筛选: 行内逗号分隔 = 同时具备, 不同行命中其一即可; 支持 regex:/:ignore_case",
        item_kind="tag_group",
        placeholder="tag1,tag2"
    ),
    Plugin(
        "category",
        "分类",
        "condition",
        "list",
        "按种子分类匹配(命中任意一条即满足); 支持 regex:/:ignore_case",
        item_kind="pattern",
        placeholder="regex:^HR"
    ),
    Plugin(
        "trackers",
        "站点",
        "condition",
        "list",
        "按「站点」页里配置的名字匹配(不是域名); 命中任意一个即满足",
        item_kind="pattern",
        placeholder="HHan"
    ),
    Plugin(
        "tracker_group",
        "站点分组",
        "condition",
        "list",
        "按站点配置里的「站点分组」筛选; 分组只是配置概念, 不会写到种子上; 命中任意一个即满足",
        item_kind="pattern",
        placeholder="国内",
    ),
    Plugin(
        "state",
        "状态",
        "condition",
        "list",
        "按种子当前状态筛选: 行内用 & 连接多个状态(同时满足), 不同行命中其一即可",
        item_kind="state_group",
        placeholder="is_complete&is_uploading"
    ),
    Plugin("hr", "HR 条件", "condition", "enum", "按站点 HR 管理状态筛选; 站点没配 HR 段则永远不匹配", options=HR_MODES),
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
    Plugin("seedtime", "做种时长", "condition", "str", "按已做种时长比较", placeholder="<24H"),
    Plugin("upload_ratio", "分享率", "condition", "str", "按种子当前分享率比较", placeholder=">1.5"),
    Plugin("upload_size", "总上传量", "condition", "str", "按种子累计上传量比较", placeholder=">10GiB"),
    Plugin("upload_size_today", "今日上传量", "condition", "str", "今天累计的上传量(按自然日统计, 重启也不丢)", placeholder=">10GiB"),
    Plugin("upload_size_this_week", "本周上传量", "condition", "str", "本周(周一起算)累计的上传量", placeholder=">10GiB"),
    Plugin("upload_size_this_month", "本月上传量", "condition", "str", "本月 1 号起累计的上传量", placeholder=">10GiB"),
    Plugin(
        "expr",
        "表达式",
        "condition",
        "expr", "用一行表达式自由组合种子字段与额外值: 前缀 tor.*(种子) / tracker.*(站点) / sys.*(环境), "
        "函数 freespace(路径) 等; 一层只能放一个运算符, 多的用括号分组(如 (tor.size &gt;= 10GiB) and (tor.ratio &gt; 1.5))",
        placeholder="(tor.seeding_time &gt;= 3D) and (tor.ratio &gt; 1.5)"
    ),
    Plugin(
        "freespace",
        "磁盘可用空间",
        "condition",
        "object",
        "检查指定路径的剩余空间; 路径为空或不可用时视为不匹配",
        fields=(
            Field("path", "检查路径", "path", default="", required=True, placeholder="R:/"),
            Field("amount", "可用空间条件", "compare_size", default="<100GiB", required=True, placeholder="<100GiB"),
        )
    ),
)

CHECKING_SECTION_FIELDS: Tuple[Field, ...] = (
    Field("enabled", "启用该分支", "bool", default="false", help="不启用时该分支整体跳过(日志里记跳过原因)"),
    Field(
        "mode",
        "校验方式",
        "enum",
        default="skip-checking",
        options=CHECKING_MODES,
        help="skip-checking 跳检(删种重加, 不再哈希校验); full-checking 强制完整哈希校验"
    ),
    Field("auto_start", "校验后自动开始", "bool", default="false"),
)

ACTION_PLUGINS: Tuple[Plugin, ...] = (
    Plugin(
        "add_tags",
        "添加标签",
        "action",
        "list",
        "给种子加标签(已有则跳过); 支持 ${required_seeding_time} 变量",
        item_kind="str",
        placeholder="tag-${required_seeding_time}"
    ),
    Plugin(
        "remove_tags",
        "删除标签",
        "action",
        "list",
        "从种子上删除匹配的标签; 支持 regex:/:ignore_case 与变量替换",
        item_kind="pattern",
        placeholder="regex:^tag",
        risk="匹配到的标签会从种子删除",
    ),
    Plugin(
        "add_category",
        "设置分类",
        "action",
        "object",
        "给种子设置分类; 已有分类且未开「覆盖已有分类」时跳过",
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
    Plugin("remove_category", "清空分类", "action", "bool", "清空种子的分类; 本来就没有分类时跳过"),
    Plugin("start", "开始种子", "action", "bool", "让种子开始下载/做种; 已在开始状态则跳过"),
    Plugin("stop", "暂停种子", "action", "bool", "暂停种子; 已在暂停状态则跳过"),
    Plugin("print_torrent_details", "打印种子详情", "action", "bool", "把种子详情写入日志留档(只读不改种子); 种子删除触发的规则里这是唯一允许的动作"),
    Plugin(
        "checking",
        "校验/跳检",
        "action",
        "object",
        "按参考种子判断数据是否可信: 可信则跳过校验直接重挂, 不可信则强制哈希校验",
        risk="跳检会删除种子并重新添加(期间停止做种), 请务必配置去重/冷却避免反复执行",
        fields=(
            Field(
                "basic_check",
                "参考判定方式",
                "enum",
                default="filelist",
                required=True,
                options=CHECKING_BASIC,
                help="如何确认数据可信: filelist 比对文件列表(快); piecehashes 比对分片哈希(慢但更严); custom 调用你自己的脚本"
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
            Field(
                "with_reference",
                "有参考种子",
                "object",
                default=None,
                optional=True,
                help="组内能找到已完成且可信的同内容种子(参考种子)时的处理方式",
                fields=CHECKING_SECTION_FIELDS
            ),
            Field(
                "without_reference",
                "无参考种子",
                "object",
                default=None,
                optional=True,
                help="找不到参考种子时的处理方式; 选跳检属高风险(未做哈希校验直接开始), 建议强制校验或不开该分支",
                fields=CHECKING_SECTION_FIELDS
            ),
        )
    ),
    Plugin(
        "move_to",
        "移动种子",
        "action",
        "object",
        "把种子的保存路径改为新目录(仅改 qB 里的记录, 不搬动磁盘上的文件)",
        fields=(Field("path", "目标路径", "path", default="", required=True, placeholder="R:/seeds"), )
    ),
    Plugin(
        "reannounce",
        "强制汇报",
        "action",
        "bool",
        "让 qB 立即向 tracker 汇报状态; 动作内置 10 分钟最小间隔, 未配去重时启动会告警",
        risk="频繁汇报会被站点判定为异常流量"
    ),
    Plugin(
        "upload_speed_limit",
        "上传限速",
        "action",
        "speed",
        "限制该种子的上传速度; 0 = 不限速; 奇数 KiB/s(如 2001KiB/s)视为手动限速, 本程序不覆盖",
        placeholder="1000KiB/s"
    ),
    Plugin("download_speed_limit", "下载限速", "action", "speed", "限制该种子的下载速度; 0 = 不限速", placeholder="1000KiB/s"),
)

"""schema 顶层分组: GROUPS 表(左导航分组, 顺序即表单顺序)"""
from typing import Tuple
from .fields import Field, Group, LOG_LEVELS, NOTIFY_CHANNELS, NOTIFY_LEVELS
from .hr import HR_CHECK_FIELDS
from .trackers import HR_OUTPUT_FIELDS

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
                help="auto-qb 通过 qB 的 Web UI 连接并管理种子(需在 qB 中开启 Web UI)",
                fields=(
                    Field(
                        "host",
                        "主机",
                        "str",
                        default="127.0.0.1",
                        required=True,
                        placeholder="127.0.0.1",
                        help="qB 所在机器的 IP; 本机运行保持 127.0.0.1"
                    ),
                    Field(
                        "port",
                        "端口",
                        "int",
                        default="8080",
                        required=True,
                        min=1,
                        max=65535,
                        help="qB Web UI 的端口(qB 设置 → Web UI 里可查)"
                    ),
                    Field("username", "用户名", "str", default="", help="qB Web UI 的登录用户名"),
                    Field("password", "密码", "password", default="", help="qB Web UI 的登录密码"),
                )
            ),
            Field(
                "main_tick",
                "主循环间隔",
                "time",
                default="2S",
                required=True,
                help="自动管理的心跳频率: 种子状态变化与到期的任务都按它刷新; 不能为 0",
            ),
            Field(
                "sync_interval",
                "种子状态同步间隔",
                "time",
                default="1.5S",
                help=(
                    "只刷新种子状态/速度的节拍; 比主循环更密(默认 1.5 秒, 与 qB 自带 WebUI 的 1500ms 同量级), "
                    "但不跑任务、不预取 tracker、不建搜索索引 —— 那些仍按主循环间隔, 避免 qB 请求被放大。 "
                    "大于主循环间隔时按主循环间隔生效"
                ),
            ),
            Field(
                "state_save_interval",
                "状态周期落盘间隔",
                "time",
                default="120S",
                help=(
                    "运行状态(state.json)的周期落盘间隔: 崩溃/强杀/断电等非优雅终止时最多丢这么多秒的运行期状态, "
                    "优雅退出仍立即落盘。0 = 关闭(仅优雅退出时落盘, 旧行为); 下限 30 秒 —— "
                    "状态变更频率是小时~天级, 更激进的间隔只会放大磁盘写入"
                ),
            ),
            Field(
                "max_tasks_per_tick",
                "每轮最大任务数",
                "int",
                default="20",
                min=1,
                help="一轮最多执行多少个到期的自动化任务; 太大单轮耗时长(界面/响应变钝), 保持默认即可",
            ),
            Field(
                "interval",
                "内置任务间隔",
                "time",
                default="60S",
                help="维护/全局清理/曲线等内置任务的执行周期; 以上一轮结束起算, 不会越跑越密",
            ),
            Field(
                "data_dir",
                "运行时数据目录",
                "path",
                default="auto-qb-data",
                help="运行状态、日志、跳检备份等文件的存放目录(相对程序目录或绝对路径)",
                risk="修改后需重启进程才生效",
            ),
            Field(
                "state_file",
                "状态文件",
                "path",
                default="",
                help="运行状态存档(重启后接着上次进度继续); 留空 = <data_dir>/state.json",
                risk="修改后需重启进程才生效"
            ),
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
                open=True,  # 短段不折叠(用户要求: 日志/WEB UI/通知平铺)
                fields=(
                    Field(
                        "level",
                        "日志等级",
                        "enum",
                        default="INFO",
                        options=LOG_LEVELS,
                        help="详细程度: DEBUG 最详细, CRITICAL 只记严重错误; 也是通知的基准(达到 通知.最低通知级别 的日志会推送)"
                    ),
                    Field("file", "日志文件", "path", default="", help="留空 = <data_dir>/logs/auto-qb.log"),
                    Field(
                        "max_bytes",
                        "轮转大小",
                        "size",
                        default="10MiB",
                        unit_default="MiB",
                        help="单个日志文件写满就另起新文件(保留 5 个旧备份), 防止日志无限膨胀"
                    ),
                    Field(
                        "format",
                        "日志格式",
                        "str",
                        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        help="日志行的格式模板(Python logging 格式串); 不熟悉保持默认即可",
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
                open=True,  # 短段不折叠
                fields=(
                    Field("enabled", "启用", "bool", default="false", help="启用后可在浏览器打开 主机:端口 管理种子与配置(默认关闭)"),
                    Field(
                        "host",
                        "监听地址",
                        "str",
                        default="127.0.0.1",
                        help="保持 127.0.0.1 = 仅本机可访问",
                        risk="改成 0.0.0.0 会把可暂停/删除种子的管理界面暴露给局域网其他设备",
                    ),
                    Field(
                        "port",
                        "监听端口",
                        "int",
                        default="8080",
                        min=1,
                        max=65535,
                        help="Web UI 的端口; 若与 qB Web UI 相同请改开一个"
                    ),
                    Field(
                        "token",
                        "访问密钥",
                        "password",
                        default="",
                        help="登录 Web UI 用的密钥; 留空 = 首次启动随机生成(存到 data_dir/web.token, 启动日志只提示文件路径, 密钥内容不打印)"
                    ),
                    Field(
                        "skip_local_verify",
                        "跳过本地验证",
                        "bool",
                        default="false",
                        help="本机(127.0.0.1)打开 Web UI 免输入访问密钥; 远程访问仍需密钥",
                        risk="仅对本机连接生效, 对外暴露(host 非本机)仍强制鉴权; 开启弱化本机安全边界",
                    ),
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
                open=True,  # 短段不折叠
                fields=(
                    Field("enabled", "启用", "bool", default="false", help="开启后程序消息(出错/危险情况等)按系统原生通知推送, 无需额外配置"),
                    Field(
                        "min_level",
                        "最低通知级别",
                        "enum",
                        default="WARNING",
                        options=NOTIFY_LEVELS,
                        grey_if=("enabled", "true"),
                        help="日志达到该级别才推送(WARNING = 只推警告和错误)",
                    ),
                    Field(
                        "quiet_hours",
                        "免打扰时段",
                        "str",
                        default="",
                        placeholder="23:00-08:00",
                        grey_if=("enabled", "true"),
                        help="该时段内不推送(可跨午夜); 留空 = 全天推送"
                    ),
                    Field(
                        "max_per_hour",
                        "每小时上限",
                        "int",
                        default="20",
                        min=1,
                        grey_if=("enabled", "true"),
                        help="每小时最多推送的条数, 超出丢弃(防刷屏)"
                    ),
                    Field(
                        "dedup_window",
                        "去重窗口",
                        "time",
                        default="10M",
                        grey_if=("enabled", "true"),
                        help="该时间内内容相同的通知只推第一条, 避免重复轰炸; 0 = 不去重",
                    ),
                    Field(
                        "channels",
                        "通知渠道",
                        "keyed_list",
                        default=["platform"],
                        options=NOTIFY_CHANNELS,
                        grey_if=("enabled", "true"),
                        help="当前仅支持系统原生通知(Windows/macOS/Linux)"
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
                help="自动清理仅大小写不同的重复标签(如 HHan 与 hhan 保留一个); 站点配置里可单独覆盖"
            ),
            Field(
                "skip_checking_tag",
                "跳检标签名",
                "str",
                default="zSkipChecked",
                help="跳检成功的种子会打上此标签(表示未经哈希校验); 查找跳检参考种子时会排除它们, 防止错误扩散; 留空 = 不启用",
            ),
            Field(
                "grouping",
                "辅种分组",
                "object",
                help="把指向相同文件的种子(辅种)归为一组: 统一检查缺文件, 发现异常整组暂停, 避免重复下载",
                fields=(
                    Field("enabled", "启用分组", "bool", default="true", help="开启后按组(而不是单个种子)做缺文件检查"),
                    Field(
                        "check_missing_files",
                        "启用缺文件检查",
                        "bool",
                        default="true",
                        grey_if=("enabled", "true"),
                        help="核对组内文件是否还在磁盘上; 缺失则整组暂停并打标签",
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
                help="从新种子的文件名解析集数自动打标签; 仅新增种子时触发, 集数不连续视为不可靠、不打标",
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
                help="从所有种子上摘除匹配的标签, 并从 qB 全局标签表里注销; 支持 regex:/、:ignore_case 与 @tracker_tags 引用",
                risk="标签定义一并删除, 依赖该标签的自动化(如 HR 标记)随之失效",
            ),
            Field(
                "delete_tags_if_has_no_torrents",
                "删除无种子标签",
                "pattern_list",
                default=[],
                help="只删已经没有种子在用的标签(安全清理残留定义; 仍有种子使用时不删)"
            ),
            Field("hr", "HR 全局默认", "object", help="HR 动作(加标签/分类)的全局默认值; 站点 hr 段未设置对应字段时回退到这里", fields=HR_OUTPUT_FIELDS),
        ),
        icon="i-cards",
    ),
    Group(
        "hr_check",
        "HR 在线核实",
        "部分种子 HR 站点的在线核实(取 HR 统计页 + 对账建索引)",
        fields=(
            Field(
                "hr_check",
                "在线核实",
                "object",
                default=None,
                optional=True,
                open=True,
                help="部分站点只有一部分种子受 HR 约束, 且站点不提供可机读的逐种标记 ⇒ 逐种子在线核实; "
                "未接入的站点行为完全不变",
                fields=HR_CHECK_FIELDS,
            ),
        ),
        icon="i-clock",
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
                help="根据 Traffic Monitor 统计的累计流量(当天/当月/最近 N 天)自动调 qB 全局限速; 某档限速填 0 = 该档不限速; enabled: false 整体停用(缺省启用)"
            ),
        ),
        icon="i-gauge",
    ),
    Group(
        "trackers",
        "站点",
        "站点匹配、标签、限速与 HR",
        fields=(Field("trackers", "站点列表", "trackers", default={}, help="按 tracker 域名匹配种子; 未配置的站点不做任何管理"), ),
        icon="i-globe",
    ),
    Group(
        "rules",
        "规则集",
        "条件 + 动作的自动化规则",
        fields=(
            # UI 专段: 真实配置键是动态的 "<名称>_rules"(规则集名由用户自定), 故标记 ui_only
            Field("rules", "规则集", "rules", default={}, ui_only=True, help="全部规则集(配置文件里以 _rules 结尾的段)"),
        ),
        icon="i-bolt",
    ),
)

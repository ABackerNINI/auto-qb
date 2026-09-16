"""schema 顶层分组: GROUPS 表(左导航 8 分组, 顺序即表单顺序)"""
from typing import Tuple
from .fields import Field, Group, LOG_LEVELS, NOTIFY_CHANNELS, NOTIFY_LEVELS
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
                open=True,  # 短段不折叠(用户要求: 日志/WEB UI/通知平铺)
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
                open=True,  # 短段不折叠
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
                    Field(
                        "skip_local_verify",
                        "跳过本地验证",
                        "bool",
                        default="false",
                        help="开启后本机(127.0.0.1)访问直接进入, 无需输入访问密钥",
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
                help="读取 Traffic Monitor 数据, 按 day/month/Nd 累计流量分档限速(0 = 该档不限速); enabled: false 整体停用(缺省 true)"
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

"""schema: HR 在线核实段(全局 config.hr_check 与站点 trackers.<site>.hr_check)。

对应 [memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html] 的 §7 配置设计。
本模块只管**展示元数据**; 合法性唯一入口仍是 config.validate_config, 级别唯一来源是 config/impact.py。

⚠注意两处语义容易配错, help 文案必须写明:
- `allow_window` 与 `notify.quiet_hours` **语义相反**(那个是「该时段不发」, 本项是「仅该时段取数」);
- `unknown_policy` / `verified_ttl` 分别控制「未核实怎么算」与「放行多久失效」,
  调松它们等于自愿放大漏管窗口。
"""
from typing import Tuple

from .fields import Field

#: 未核实种子的处置(与 validation.HR_CHECK_UNKNOWN_POLICIES 一致)
HR_CHECK_UNKNOWN_POLICIES: Tuple[str, ...] = ("hr", "not-hr")

#: 站点模式(与 validation.HR_CHECK_MODES 一致)
HR_CHECK_MODES: Tuple[str, ...] = ("off", "partial", "all")

#: HR 页状态档位(与 hr.model.ALL_LANES 一致)
HR_CHECK_SCOPES: Tuple[str, ...] = ("A", "B", "C", "D")

HR_CHECK_CHANNEL_FIELDS: Tuple[Field, ...] = (
    Field(
        "enabled",
        "启用取数通道",
        "bool",
        default="false",
        help="本实例是否有浏览器扩展可驱动。⚠本机有浏览器的实例推荐都启用: 抓取能力的硬边界是「本机有没有装扩展的浏览器」, "
        "多通道不会双倍访问站点(同站点靠文件锁 + 有效期复用)",
    ),
    Field(
        "port",
        "本地端点端口",
        "int",
        default="8788",
        min=1,
        max=65535,
        help="仅监听 127.0.0.1; 同机多实例必须各用不同端口(端口被占启动即报错)",
    ),
    Field(
        "token",
        "端点密钥",
        "password",
        default="",
        help="访问密钥; 留空 = 首次启动随机生成并持久化到 <data_dir>/hr.token(扩展侧需逐实例填写)",
    ),
    Field(
        "extension_id",
        "扩展 id(可选)",
        "str",
        default="",
        placeholder="abcdefghijklmnopabcdefghijklmnop",
        help="填了则只放行该扩展(32 位 a~p); 留空 = 放行任意扩展。❗真正的鉴权是 token, 本项只是第二道防线",
    ),
    Field(
        "request_timeout",
        "等扩展回传上限",
        "time",
        default="180S",
        unit_default="S",
        help="取数线程等扩展回传的上限; 超时按一次失败计。必须有 —— 否则扩展中途被关掉会让持锁的取数线程永久挂住",
    ),
)

HR_CHECK_FIELDS: Tuple[Field, ...] = (
    Field(
        "enabled",
        "启用 HR 在线核实",
        "bool",
        default="false",
        help="总开关; 默认关闭(保守默认)。开启后仍需逐站点配 trackers.<站点>.hr_check",
    ),
    Field(
        "min_torrent_interval",
        "请求最小间隔",
        "time",
        default="90S",
        unit_default="S",
        help="相邻两次站点请求的最小间隔; 抖动只向上(+0~25%), 故实测间隔恒 >= 本值。访问频度是账号安全的第一条防线",
    ),
    Field("max_torrents_per_hour", "每小时配额", "int", default="12", help="站点级独立计数; 到顶即停, 不报错"),
    Field("max_torrents_per_day", "每天配额", "int", default="60", help="站点级独立计数; 翻页与取 .torrent 同样计入"),
    Field("failure_threshold", "连续失败熔断阈值", "int", default="3", help="连续失败达该次数 -> 该站进入冷却"),
    Field("failure_cooldown", "熔断冷却时长", "time", default="12H", unit_default="H", help="冷却期间零请求"),
    Field(
        "allow_window",
        "允许取数时段",
        "str",
        default="",
        placeholder="23:00-08:00",
        help='格式 "HH:MM-HH:MM"(可跨午夜); 留空 = 全天。❗与「通知免打扰」语义相反 —— 那个是「该时段不发」, 本项是「仅该时段取数」',
    ),
    Field(
        "unknown_policy",
        "未核实种子处置",
        "enum",
        default="hr",
        options=HR_CHECK_UNKNOWN_POLICIES,
        help="未核实(首刷未完成/刷新不完备/通道静默)时怎么算: hr = 保守按 HR 管束(推荐); "
        "not-hr = 按非 HR(等于自愿放弃一重保证)。❗新鲜度闸门不受本项影响",
    ),
    Field(
        "verified_ttl",
        "放行有效期",
        "time",
        default="",
        unit_default="H",
        help="已核实「不受管束」的有效期; 留空 = 跟随该站刷新周期(推荐)。超期未获新刷新背书即回落未核实。"
        "❗调大等于放大「账号在别的客户端下载」的漏管窗口",
    ),
    Field(
        "index_retention",
        "页面快照保留时长",
        "time",
        default="30D",
        unit_default="D",
        help="HR 页行快照(仅展示用)的保留时长; 已取记录不受影响(永不重取)",
    ),
    Field("max_download_retries", "取种子重试上限", "int", default="3", help="单个 .torrent 取数失败的重试上限, 达到后冷却"),
    Field(
        "channel_silence_warn", "通道静默告警时长", "time", default="6H", unit_default="H", help="通道多久没有成功刷新就告警(浏览器长期未开/扩展被停用)"
    ),
    Field(
        "shared_dir",
        "共享目录",
        "path",
        default="",
        help="多实例共享站点数据时的目录(留空 = 落 <data_dir>/hr/)。需支持文件锁且各实例看到同一份文件; "
        "云同步盘(OneDrive/坚果云)不可用",
    ),
    Field(
        "lock_timeout",
        "抢锁等待",
        "time",
        default="0S",
        unit_default="S",
        help="抢站点锁的等待时长; 0 = 不等(拿不到锁直接等下一轮)。锁粒度 = 站点, 抓取在锁内进行",
    ),
    Field(
        "poll_interval",
        "取数线程节奏",
        "time",
        default="1M",
        unit_default="M",
        help="取数线程醒来检查的节奏, 与主循环 tick 无关(HR 粒度是小时~天, 不需要高频)",
    ),
    Field(
        "parse_missing_rate_max",
        "字段缺失率上限",
        "float",
        default="0.5",
        min=0,
        max=1,
        help="HR 页必填字段缺失率超过该值即判「页面可能改版」, 该次刷新不产生放行(防把空结果当真)",
    ),
    Field(
        "channel",
        "本地取数通道",
        "object",
        default=None,
        optional=True,
        help="浏览器扩展拉取任务/回传数据的本地端点; 未配置 = 本实例不参与取数(只读共享数据)",
        fields=HR_CHECK_CHANNEL_FIELDS,
    ),
)

SITE_HR_CHECK_FIELDS: Tuple[Field, ...] = (
    Field(
        "mode",
        "核实模式",
        "enum",
        default="off",
        options=HR_CHECK_MODES,
        help="off = 该站不启用; partial = 在线核实(未核实按全局 unknown_policy); "
        "all = 站点侧驱动 + 未核实恒受管束(全站 HR)。❗mode != off 时该站必须同时配 hr 段",
    ),
    Field(
        "adapter",
        "站点解析器",
        "str",
        default="nexusphp",
        help="HR 统计页形态; nexusphp = 标准 myhr.php 九列表格(绝大多数 PT 站)",
    ),
    Field(
        "hr_page_url",
        "HR 统计页地址",
        "str",
        default="",
        required=True,
        placeholder="https://pt.example.com/myhr.php",
        help="HR 名单来源页(账号维度的「我的 H&R」清单); mode != off 时必填",
    ),
    Field(
        "hr_page_scopes",
        "抓取档位",
        "str_list",
        default=["A", "B", "C"],
        help="要抓的状态档位: A 考察中 / B 已达标 / C 未达标 / D 已免罪。"
        "❗至少含 A+B+C —— 只抓 A 会把「已达标」的 HR 种子误当成非 HR(漏 HR); D 可加可不加(免罪视为放行)",
    ),
    Field(
        "download_path",
        "种子下载路径",
        "str",
        default="/download.php?id={id}",
        help="相对站点根, 用 {id} 代表种子编号; passkey 之类的页面参数由取数通道在页面上下文补, 不写进配置",
    ),
    Field("page_param", "翻页参数名", "str", default="page", help="翻页查询参数名(如 page -> ?hrtype=A&page=2)"),
    Field("refresh_interval", "刷新周期", "time", default="12H", unit_default="H", help="HR 页抓取周期; 放行有效期默认跟着它"),
    Field("max_pages_per_refresh", "单次翻页上限", "int", default="5", help="一次刷新最多翻几页; 到上限仍未到底 -> 本次覆盖证明不成立"),
    Field(
        "max_torrents_per_hour",
        "每小时配额(站点覆盖)",
        "int",
        default="",
        help="留空 = 回退全局 config.hr_check.max_torrents_per_hour",
    ),
)

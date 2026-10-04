"""schema: HR 在线核实段(v3 15 键口径, 计划 26-09-28-1932 §6 + 26-09-30-0240; 全局 config.hr_check + sites 子段)。

站点段沿用 26-09-27-1318 REV2 的上收口径: 站点启用/微调的唯一配置源是 hr_check.sites.<档案 id>
(键 = config/site_presets.py 的内置档案), 页面事实(adapter/页面路径/下载路径/翻页参数/清单形态)
由档案填充, 不再是可配置项。本模块只管**展示元数据**; 合法性唯一入口仍是 config.validate_config,
级别唯一来源是 config/impact.py。

WARN:注意一处语义容易配错, help 文案必须写明:
- `allow_window` 与 `notify.quiet_hours` **语义相反**(那个是「该时段不发」, 本项是「仅该时段取数」)。
"""
from typing import Tuple

from .fields import Field

HR_CHECK_CHANNEL_FIELDS: Tuple[Field, ...] = (
    Field(
        "enabled",
        "启用取数通道",
        "bool",
        default="false",
        help="本实例是否有浏览器扩展可驱动。WARN:本机有浏览器的实例推荐都启用: 抓取能力的硬边界是「本机有没有装扩展的浏览器」, "
        "多通道不会双倍访问站点(同站点靠文件锁 + 复用窗)",
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
        help="填了则只放行该扩展(32 位 a~p); 留空 = 放行任意扩展。!真正的鉴权是 token, 本项只是第二道防线",
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

#: hr_check.sites.<档案 id> 条目字段(v3: enabled + tracker 显式映射 + refresh_interval
#: + idle_refresh_interval 稳态降频, 计划 26-10-05-0555 S1)。
#: 页面事实(adapter/页面路径/下载路径/翻页参数/清单形态)由内置站点档案填充, 不再是可配置项 ——
#: 「站点接入」卡片按这里的字段表渲染微调项。
HR_CHECK_SITES_FIELDS: Tuple[Field, ...] = (
    Field(
        "enabled",
        "启用在线核实",
        "bool",
        default="false",
        help="启用即管: 判定语义硬编码(命中考察中→管束 / 终态档 B·C·D 与移出未列出→放行 / "
        "无证据→本地兜底: 达标放行·未达标管束), 没有撤退路径。!启用时该站点必须配 HR 规则段"
        "(要求做种时长等) —— 绑定按档案已知 announce 域自动映射完成, 未命中时用 tracker 显式指定",
    ),
    Field(
        "tracker",
        "绑定站点(显式指定)",
        "str",
        default="",
        help="填「站点」分区里的站点条目名, 直接指定本档案映射到哪个站点配置; 留空 = 自动映射"
        "(档案已知该站 announce 域, 在各站点 domains 里查表, 恰好一个命中即绑定)。"
        "自动映射未命中/有歧义时保存会报错, 此时必须显式填写",
    ),
    Field(
        "refresh_interval",
        "拉取间隔",
        "time",
        default="12H",
        unit_default="H",
        help="自上次健康波起, 每隔多久重新拉取一次站点清单(在线对账的节奏); 失败的档位随下一轮自然重试(无独立退避)。"
        "站点访问节奏由本值与频控(最小间隔/日额/时间窗)共同决定; 点『立即拉取』可越过本闸(频控仍生效)",
    ),
    Field(
        "idle_refresh_interval",
        "稳态拉取间隔",
        "time",
        default="24H",
        unit_default="H",
        help="本地没有义务对象(对账对象集为空)时改用的对账节奏 —— 稳态期按本间隔降频, "
        "对象集一翻非空(如新下载/本机重下)自动回退拉取间隔并在下一轮立即拉取。"
        "须 >= 拉取间隔(相等 = 等效关闭降频)",
    ),
)

HR_CHECK_FIELDS: Tuple[Field, ...] = (
    Field(
        "enabled",
        "启用 HR 在线核实",
        "bool",
        default="false",
        help="总开关; 默认关闭(保守默认)。开启后还需在下方「站点接入」卡片勾选启用具体站点",
    ),
    Field(
        "min_interval",
        "请求最小间隔",
        "time",
        default="90S",
        unit_default="S",
        help="相邻两次站点请求的最小间隔(页面与 .torrent 下载统一适用); 抖动只向上(+0~25%), "
        "故实测间隔恒 >= 本值。访问频度是账号安全的第一条防线",
    ),
    Field(
        "max_requests_per_day",
        "日额保险",
        "int",
        default="240",
        help="站点级日请求上限(页面 + 下载合计, 零点重置); 只防长跑超量, 不是节奏工具。"
        "节奏由 min_interval 与波次引擎的覆盖对象集决定",
    ),
    Field(
        "max_pages_per_wave",
        "单波页数上限",
        "int",
        default="30",
        help="安全阀: 防改版/异常导致翻页失控。到顶该档截断(截断点之前数据有效), 下波从头再翻",
    ),
    Field(
        "allow_window",
        "允许取数时段",
        "str",
        default="",
        placeholder="23:00-08:00",
        help='格式 "HH:MM-HH:MM"(可跨午夜); 留空 = 全天。!与「通知免打扰」语义相反 —— 那个是「该时段不发」, 本项是「仅该时段取数」',
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
        "reuse_window",
        "数据复用窗",
        "time",
        default="2H",
        unit_default="H",
        help="一波取完后的数据新鲜窗: 窗内直接复用不取数(多实例去重 + 界面新鲜度); 实际生效不超过拉取间隔。"
        "调大不增加站点访问, 只让数据显得更新",
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
    Field(
        "sites",
        "站点接入",
        "object",
        default=None,
        optional=True,
        help="站点启用与微调的唯一配置入口: 键 = 内置站点档案 id, 在「站点接入」卡片勾选启用;"
        "页面地址/解析器/种子下载路径/翻页参数/清单形态由档案自动处理, 配置里写这些值不再有意义。"
        "未入档案的站点不允许启用(校验期报错并给出已支持清单)",
        fields=HR_CHECK_SITES_FIELDS,
    ),
)

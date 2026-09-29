"""配置数据模型: 数据类字段默认值 = 唯一默认值来源(解析后空间, 与字段类型注解一致)

仅 errors.py 外的两个常量为非字段默认用途:
- DEFAULT_CONFIG_FILE: CLI 配置文件参数缺省(cli.argparse)
- UNLIMITED_SPEED: exporter 生成 YAML 模板的原始串占位(输出格式)
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_CONFIG_FILE = "config.yml"
UNLIMITED_SPEED = "0KiB/s"


@dataclass
class LoggingConfig:
    level: str | int = logging.INFO  # 等级名或数值; YAML 原始缺省 "INFO"
    file: str = ""
    max_bytes: int = 10 * 1024**2  # 字节; YAML 原始缺省 "10MiB"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"  # %(name)s = 来源模块


@dataclass
class QbittorrentConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    username: str = ""
    password: str = ""

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class HRRule:
    """一条 HR 规则(站点级, 已合并全局默认输出设置)

    required_seeding_time: 做种时长要求(秒)
    required_seeding_time_raw: 原始时间字符串(如 "3D"), 用于 ${required_seeding_time} 变量替换
    required_share_ratio: 分享率要求, 0 = 不要求
    extra_seeding_time: 额外做种时间(秒), 做种满 required+extra 视为 "satisfied"
    condition: ('dlratio', ratio) 或 ('dlsize', bytes) 触发条件(下载比例/下载量)
    以下为输出设置(站点覆盖全局后的最终值):
      add_tag / add_category: 满足触发条件时添加的标签/分类(支持 ${required_seeding_time})
      overwrite_category: 添加分类时是否覆盖已有分类
      add_tag_for_satisfied / add_category_for_satisfied: 做种时长已满足要求+额外时间时添加
      overwrite_category_for_satisfied: 同上, 覆盖已有分类
      exclude_tags / exclude_categories: HR 排除表(计划 26-09-28-1805) —— 命中任一格式的种子
        不纳入 HR 体系(不打标/不在线核实/规则按未触发), 优先级高于站点侧一切管束;
        站点段与全局 hr 段取并集(去重保序), 不是覆盖。匹配语法同 remove_tags(MatchPattern 单点)
    """
    required_seeding_time: int = 0
    required_seeding_time_raw: str = ""
    required_share_ratio: float = 0.0
    extra_seeding_time: int = 0
    condition: tuple = ("dlratio", 0.8)
    add_tag: str = ""
    add_category: str = ""
    overwrite_category: bool = False
    add_tag_for_satisfied: str = ""
    add_category_for_satisfied: str = ""
    overwrite_category_for_satisfied: bool = False
    exclude_tags: List[str] = field(default_factory=list)
    exclude_categories: List[str] = field(default_factory=list)


@dataclass
class HrChannelConfig:
    """本地取数通道: 浏览器扩展拉清单/回传数据的本地端点(计划 §6)

    enabled: 本实例是否有浏览器扩展可驱动; 默认 false(保守), 装上扩展后开启。
      WARN:本机有浏览器的实例推荐都启用 —— 抓取能力的硬边界是「本机有没有装扩展的浏览器」,
      而不是名额(端点只听 127.0.0.1, 浏览器只能连本机 loopback ⇒ 跨机器配了也驱动不了);
      多通道不会双倍访问站点: 同站点靠「文件锁 + 有效期复用」保证只被访问一次。
    port: 监听端口; 仅监听 127.0.0.1。同机多实例必须各用不同端口(被占 => 启动即报错)
    token: 访问密钥; 留空 = 首次启动随机生成并持久化到 <data_dir>/hr.token(同 web.token 口径)
    extension_id: 可选。填了则 CORS 只放行该扩展 id(chrome-extension://<id>); 留空 = 放行任意扩展
      origin(**真鉴权仍是 token**, origin 白名单只是第二道 —— 见计划 §6)
    request_timeout: 取数线程等扩展回传的上限(秒)。必须有: 扩展中途被关掉时, 若无上限,
      持站点锁的取数线程会永久挂住(该站再也不会刷新、锁也永不释放); 超时按一次失败计入退避燔断
    """

    enabled: bool = False
    port: int = 8788
    token: str = ""
    extension_id: str = ""
    request_timeout: float = 180.0


@dataclass
class HrCheckConfig:
    """HR 在线核实全局段(v3 波次模型 15 键口径, 计划 26-09-28-1932 §6.1 + 26-09-30-0240)

    整段缺省 = 功能关闭; 总开关 enabled 默认 false(保守默认, 黄金法则 2)。
    所有新键都必须进 validate_config 并同步 config/schema(守卫测试会查)。
    v3 删除的键(26 个): 频控双模型键(quota_model/page_rate_per_hour/page_burst/
    torrent_rate_per_hour/torrent_burst/max_pages_per_day/min_page_interval/
    max_torrents_per_hour/max_torrents_per_day/min_torrent_interval 改名)、
    max_pages_per_round/round 上限、failure_threshold/failure_cooldown(熔断删除)、
    unknown_policy(行 4 硬编码)、verified_ttl(放行永续)、index_retention/
    max_download_retries/channel_silence_warn/poll_interval/lock_timeout(常量化)、
    parse_missing_rate_max(S2 零容忍)、sites 条目的 mode/hr_page_scopes/
    max_pages_per_refresh/completed_age_limit/accept_empty_listing/auto_age_limit/
    seeding_exempt_ratio 等。
    """

    enabled: bool = False
    min_interval: float = 90.0  # 相邻两次站点请求最小间隔(秒), 页面 + 下载统一; 抖动只向上 +0~25%
    max_requests_per_day: int = 240  # 站点级日额保险(全部请求合计, 零点重置); 只防长跑超量
    max_pages_per_wave: int = 30  # 单波页数上限(安全阀: 防改版/异常导致翻页失控); 到顶该档截断
    allow_window: str = ""  # 仅该时段取数 "HH:MM-HH:MM"(可跨午夜); 空 = 全天。!与 notify.quiet_hours 语义相反
    shared_dir: str = ""  # 空 = 多实例不共享(站点文件落 <data_dir>/hr/); 多实例互通时指向同一目录
    reuse_window: float = 2 * 3600.0  # 数据复用窗(秒, 计划 26-09-30-0240): 波后窗内直接复用不取数; 生效 = min(本值, 拉取间隔)
    channel: HrChannelConfig = field(default_factory=HrChannelConfig)
    # 站点接入(计划 26-09-27-1318 REV2): 键 = 内置站点档案 id(config/site_presets.py),
    # 值 = enabled + tracker 显式映射 + refresh_interval; 站点启用/微调的唯一配置源。
    # trackers.<站点>.hr_check 只是绑定结果视图。
    sites: Dict[str, "SiteHrCheckConfig"] = field(default_factory=dict)


@dataclass
class SiteHrCheckConfig:
    """站点级在线核实参数(v3: enabled + tracker + refresh_interval 三键; 计划 §6.1)

    enabled: 启用即管 —— 判定语义硬编码(命中考察中管束 / 终态放行 / 无证据本地兜底),
    不再有 mode 分叉与 unknown_policy 撤退路径。partial/all 差异是站点事实(有没有清单页),
    归档案 listing 字段: 全站型(listing=none)不取数, 判定恒走行 4 本地兜底。
    !enabled 时该站 `hr` 段必填 —— 否则 tracker_conf.hr 为 None, check_hr_condition 恒 False,
      整站保护静默失效(配置期 fail-fast 拦下)。

    配置源在 hr_check.sites.<档案 id>; adapter / hr_page_url / download_path / page_param /
    listing 五个页面事实由内置站点档案(config/site_presets.py)填充, required_seeding_time
    由绑定站点的 hr 规则派生(超额线 3× 判据), 任何配置位置都不再接受。loaders 按
    「显式 tracker 直取 > 档案已知 announce 域默认映射查表」把档案条目派生填充到命中的
    TrackerConfig.hr_check, 下游(service / channel / parse / 锚点)只读本模型。
    """

    enabled: bool = False
    # 显式映射目标: 配置源在 hr_check.sites.<id>.tracker, 填 trackers 下的条目名(字符串相等引用,
    # 无匹配语义); 留空 = 用档案默认映射(已知 announce 域查表)。派生视图回填解析出的条目名。
    tracker: str = ""
    refresh_interval: float = 12 * 3600.0  # 拉取间隔(秒, 26-09-30-0240 改名: 原名「对账波周期」; 展示名见 schema)
    # ---- 以下全部由档案/绑定派生(配置不再接受) ----
    adapter: str = "nexusphp"  # 由站点档案填充
    hr_page_url: str = ""  # 由站点档案按 web 域派生
    download_path: str = "/download.php?id={id}"  # 由站点档案填充; passkey 由取数通道在页面上下文补
    page_param: str = "page"  # 由站点档案填充
    listing: str = "list"  # 由站点档案填充: list 清单型(取数) | none 全站型(不取数, 恒行 4 本地兜底)
    #: 要求做种时长(秒, required + extra; 由绑定站点的 hr 规则派生) —— 超额线(常量 3×)判据
    required_seeding_time: float = 0.0

    @property
    def fetchable(self) -> bool:
        """本站是否参与取数(清单型才翻页; 全站型不取数)"""
        return self.enabled and self.listing == "list"


@dataclass
class TrackerConfig:
    name: str
    domains: List[str]
    tags: List[str] = field(default_factory=list)
    remove_tags: List[str] = field(default_factory=list)  # 删除标签格式(支持正则)
    upload_speed_limit: int = 0  # 字节/秒, 0 = 不限速; YAML 原始缺省 "0KiB/s"
    download_speed_limit: int = 0  # 字节/秒, 0 = 不限速
    hr: Optional[HRRule] = None  # HR 规则(已合并全局默认输出设置), None = 无 HR 配置
    # HR 在线核实的**绑定结果视图**: 配置源在 hr_check.sites.<档案 id>, loaders 按域名交集派生填充;
    # 旧 YAML 键 trackers.<站点>.hr_check 兼容接受并等价迁移(计划 26-09-27-1318 §3.4), 不再是配置入口
    hr_check: Optional[SiteHrCheckConfig] = None
    rules: List[str] = field(default_factory=list)  # 规则引用列表, 如 ["@rule_set", "@rule_set.rule1"]
    groups: List[str] = field(default_factory=list)  # 站点分组(配置层声明, 不写种子); tracker_group 条件的匹配来源
    remove_similar_tags: bool = False  # 删除类似标签(站点覆盖全局后的值)


@dataclass
class GroupingConfig:
    """种子分组管理(辅种管理): 将指向相同文件列表的种子归为一组, 统一检查

    enabled: 启用分组检查(缺文件检查统一由分组事件驱动承担, 同组共享一次磁盘扫描)
    missing_tag: 文件丢失时整组添加的标签
    """
    enabled: bool = True
    check_missing_files: bool = True  # 启用缺文件检查
    missing_tag: str = 'MISSING'


@dataclass
class AddEpisodeTagsConfig:
    """种子添加时自动添加集数标签配置

    enabled: 总开关 (False 时整段功能不生效)
    add_tag_single: 单集模板, 含 ${episode_first} 占位 (此时 first=last), e.g. "zE${episode_first}"
    add_tag_multi: 多集模板, 含 ${episode_first}/${episode_last} 占位, e.g. "zE${episode_first}-${episode_last}"
    集数不连续视为解析不可靠, 不添加标签 (避免错标)
    """
    enabled: bool = False
    add_tag_single: str = "zE${episode_first}"
    add_tag_multi: str = "zE${episode_first}-${episode_last}"


@dataclass
class WebConfig:
    """WEB UI(辅种管理)配置

    enabled: 总开关(False 时不启动 Web 服务器, 保守默认)
    host: 监听地址 —— 默认仅本机; WARN: 显式改为 0.0.0.0 会将可删除种子的管理接口暴露到网络,
    建议配合反向代理与鉴权使用
    port: 监听端口
    token: 访问密钥(Bearer 鉴权); 留空 = 首次启动随机生成并持久化到 data_dir/web.token
    skip_local_verify: 本机(loopback)连接跳过 token 鉴权, 直接进入 —— 仅对 127.0.0.1/::1 生效,
    host 对外暴露时远端请求仍强制鉴权; 保守默认关闭(开启弱化本机安全边界)
    """
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8080
    token: str = ""
    skip_local_verify: bool = False


@dataclass
class NotifyConfig:
    """主动通知配置: 程序 ERROR 日志经平台原生通知推送(notify 模块, 零第三方依赖)

    enabled: 总开关 (False 时不挂载日志 handler, 保守默认)
    min_level: 通知最低日志级别 (INFO/WARNING/ERROR, 大小写不敏感; 默认 ERROR = 只有
      真正危险才弹窗, WARNING 仅排障 —— 想看排障消息时手动调低)
    quiet_hours: 免打扰时段 "HH:MM-HH:MM" (支持跨午夜, 如 "23:00-08:00"); 空 = 不启用;
      时段内跳过发送(含 ERROR, 仅 DEBUG 记录) —— 全屏/演示场景由 OS 专注助手管理,
      本项面向睡眠时段
    max_per_hour: 每小时通知上限, 超出丢弃(防通知风暴; 内存态, 重启重置)
    dedup_window: 相同 (来源 logger, 级别, 消息前 80 字符) 的去重窗口(秒), 0 = 不去重
    channels: 渠道列表, v1 仅支持单一 platform 渠道(平台原生, 按运行平台自动分派); 默认即 platform
    """
    enabled: bool = False
    min_level: str = "ERROR"
    quiet_hours: str = ""
    max_per_hour: int = 20
    dedup_window: float = 600.0  # 秒; YAML 原始缺省 "10M"
    channels: List[str] = field(default_factory=lambda: ["platform"])  # v1 仅平台原生单渠道


@dataclass
class CurvePoint:
    """限速曲线档位点: 该 period 内累计流量(字节)低于 threshold_bytes 的区间按 speed_bytes_per_s 限制

    全程分档覆盖语义: 每档速度用于"尚未达到本档阈值"的区间(首档覆盖低端, 末档延续),
    由 curves.curve_speed 实现。speed = 0 表示该档不限速。
    """
    threshold_bytes: int
    speed_bytes_per_s: int


@dataclass
class PeriodCurve:
    """一条限速曲线: 一个累计口径(period)下的上传/下载限速档位表

    period 已归一化: "day"(当天) / "month"(当月累计) / "Nd"(最近 N 天滚动累计)
    upload_points: 上传档位表(按阈值升序); None = 该曲线不管理上传方向
    download_points: 下载档位表(按阈值升序); None = 该曲线不管理下载方向
    """
    period: str
    upload_points: Optional[List[CurvePoint]] = None
    download_points: Optional[List[CurvePoint]] = None


@dataclass
class GlobalSpeedLimitCurve:
    """全局限速曲线配置(Traffic Monitor 数据源)

    dat_path: history_traffic.dat 路径(每行 "YYYY/MM/DD <上传KB>/<下载KB>", 单位 KB=1024B)
    curves: 多条 period 曲线(同方向多条命中时取最严限速, 见 curves.merge_direction)
    interval: 曲线任务执行间隔(秒), 对应配置 interval: 10M; None = 未指定, 回退主 interval
    enabled: 功能总开关; True(缺省) = 现行行为, False = 整体停用(曲线任务短路不动 qB, Web 端视为未启用)
    """
    dat_path: str
    curves: List[PeriodCurve]
    interval: Optional[float] = None  # 秒; None = 使用 config.interval
    enabled: bool = True  # False = 整体停用(任务短路: 不读 dat 不写 qB, 不按曲线调档)


@dataclass(frozen=True)
class PathMapEntry:
    """fs.path_map 单条映射(容器部署): 逻辑空间前缀 -> 容器挂载点

    src: qB 报回的宿主保存路径前缀(YAML 键 `from`, 如 "D:/Downloads")
    dst: 本容器的挂载点(YAML 键 `to`, 如 "/mnt/downloads", 对应 compose -v ...:/mnt/downloads)
    """
    src: str
    dst: str


@dataclass
class FsConfig:
    """文件访问(fs 段, plan 26-09-27-1407): 下载数据目录的容器部署路径映射

    path_map: 映射表; 空(默认) = 完全现状(宿主直跑 / Linux 同路径挂载), 保守默认。
    非空时文件访问层切换为 Mapped 实现: qB 报回的宿主路径前缀译成容器挂载路径再做
    syscall(映射 miss 一律「不可判定」, 绝不判「不存在」—— 见 infra/file_access.py)。
    热重载 R 级(与 data_dir 同档): 修改后需重启进程。
    """
    path_map: tuple = ()  # Tuple[PathMapEntry, ...]


@dataclass
class Config:
    """配置聚合根: 全字段默认(= Config() 即全默认实例), 由 load_config 按 YAML 覆盖构造"""

    main_tick: float = 2.0  # 主循环间隔(秒); YAML 原始缺省 "2s"
    sync_interval: float = 1.5  # 种子状态同步间隔(秒): 只刷新快照, 不跑任务 —— 与 qB 自带 WebUI(1500ms)同量级
    max_tasks_per_tick: int = 20

    state_save_interval: float = 120.0  # 状态周期落盘间隔(秒): 非优雅终止时的状态丢失窗口; 0=关闭(仅优雅退出落盘); 下限 30s 防误配置写放大

    interval: float = 60.0  # 默认任务间隔: 种子列表刷新/种子级内置功能任务的默认 interval, 秒

    data_dir: str = "auto-qb-data"  # 运行时数据主目录: state/锁/日志/跳检备份默认均派生其下(显式配 state_file/log.file 优先)

    state_file: str = "auto-qb-data/state.json"  # 状态持久化文件(规则执行历史/上传量快照); 未显式配置时由 data_dir 派生为 <data_dir>/state.json

    logging: LoggingConfig = field(default_factory=LoggingConfig)

    rules_config: dict = field(default_factory=dict)  # 规则集原始配置: {规则集名: {规则名: spec}}

    remove_similar_tags: bool = False

    # 维护任务站点 tags 部分(_add_tags/_remove_tags/_remove_similar_tags)的执行节奏
    # (计划 26-09-27-1438 D5): interval = 每个内置任务间隔执行(默认 = 迁移前行为);
    # on_change = 添加时执行一次, 之后仅在种子 tags 被外部改动时重检(HR 部分不受影响)
    maintenance_tag_mode: str = "interval"

    add_episode_tags: "AddEpisodeTagsConfig" = field(
        default_factory=AddEpisodeTagsConfig
    )  # 种子添加时自动添加集数标签(名称不含集数时从文件列表解析)

    hr: HRRule = field(default_factory=HRRule)  # 全局 HR 默认输出设置(站点 hr 段未设置时兜底)

    # 跳检(skip-checking)成功后给种子打的标签全局名: 带此标签的种子未经哈希校验, 查找参考种子时
    # 一律排除(防"未验证"经辅种参考链传播)。全局统一, 不按规则覆盖(checking 动作 spec 配同名键
    # 会被校验拒绝), 动作运行时经 ctx 直接读取本值。
    skip_checking_tag: str = "zSkipChecked"

    # 全局标签清理: 彻底删除的标签格式 / 彻底删除无种子的标签格式(均支持正则, regex: 前缀)
    delete_tags: List[str] = field(default_factory=list)
    delete_tags_if_has_no_torrents: List[str] = field(default_factory=list)

    grouping: GroupingConfig = field(default_factory=GroupingConfig)  # 种子分组管理(辅种管理)

    fs: FsConfig = field(default_factory=FsConfig)  # 文件访问(容器部署路径映射, 空 = 现状)

    web: WebConfig = field(default_factory=WebConfig)  # WEB UI(辅种管理)

    notify: NotifyConfig = field(default_factory=NotifyConfig)  # 主动通知: ERROR/WARNING 日志 -> 平台原生通知

    # HR 在线核实(部分种子 HR 站点): 取 HR 统计页 + 取 .torrent 算 infohash 对账建索引
    hr_check: HrCheckConfig = field(default_factory=HrCheckConfig)

    qbittorrent: QbittorrentConfig = field(default_factory=QbittorrentConfig)
    trackers: Dict[str, TrackerConfig] = field(default_factory=dict)

    # 全局限速曲线(Traffic Monitor): 读取 dat 流量, 按多条 period 曲线聚合, 自动设置 qB 全局速度限制
    global_speed_limit_curve: Optional[GlobalSpeedLimitCurve] = None  # None = 未启用

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


@dataclass
class TrackerConfig:
    name: str
    domains: List[str]
    tags: List[str] = field(default_factory=list)
    remove_tags: List[str] = field(default_factory=list)  # 删除标签格式(支持正则)
    upload_speed_limit: int = 0  # 字节/秒, 0 = 不限速; YAML 原始缺省 "0KiB/s"
    download_speed_limit: int = 0  # 字节/秒, 0 = 不限速
    hr: Optional[HRRule] = None  # HR 规则(已合并全局默认输出设置), None = 无 HR 配置
    rules: List[str] = field(default_factory=list)  # 规则引用列表, 如 ["@rule_set", "@rule_set.rule1"]
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
    """
    dat_path: str
    curves: List[PeriodCurve]
    interval: Optional[float] = None  # 秒; None = 使用 config.interval


@dataclass
class Config:
    """配置聚合根: 全字段默认(= Config() 即全默认实例), 由 load_config 按 YAML 覆盖构造"""

    main_tick: float = 2.0  # 主循环间隔(秒); YAML 原始缺省 "2s"
    max_tasks_per_tick: int = 20

    interval: float = 60.0  # 默认任务间隔: 种子列表刷新/种子级内置功能任务的默认 interval, 秒

    data_dir: str = "auto-qb-data"  # 运行时数据主目录: state/锁/日志/跳检备份默认均派生其下(显式配 state_file/log.file 优先)

    state_file: str = "auto-qb-data/state.json"  # 状态持久化文件(规则执行历史/上传量快照); 未显式配置时由 data_dir 派生为 <data_dir>/state.json

    logging: LoggingConfig = field(default_factory=LoggingConfig)

    rules_config: dict = field(default_factory=dict)  # 规则集原始配置: {规则集名: {规则名: spec}}

    remove_similar_tags: bool = False
    add_episode_tags: "AddEpisodeTagsConfig" = field(default_factory=AddEpisodeTagsConfig)  # 种子添加时自动添加集数标签(名称不含集数时从文件列表解析)

    hr: HRRule = field(default_factory=HRRule)  # 全局 HR 默认输出设置(站点 hr 段未设置时兜底)

    # 全局标签清理: 彻底删除的标签格式 / 彻底删除无种子的标签格式(均支持正则, regex: 前缀)
    delete_tags: List[str] = field(default_factory=list)
    delete_tags_if_has_no_torrents: List[str] = field(default_factory=list)

    grouping: GroupingConfig = field(default_factory=GroupingConfig)  # 种子分组管理(辅种管理)

    qbittorrent: QbittorrentConfig = field(default_factory=QbittorrentConfig)
    trackers: Dict[str, TrackerConfig] = field(default_factory=dict)

    # 全局限速曲线(Traffic Monitor): 读取 dat 流量, 按多条 period 曲线聚合, 自动设置 qB 全局速度限制
    global_speed_limit_curve: Optional[GlobalSpeedLimitCurve] = None  # None = 未启用

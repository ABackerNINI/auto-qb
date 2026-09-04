"""配置结构与加载: 默认常量 / 数据类 / load_config"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml, logging

from .utils import parse_bool, parse_hr_condition, parse_speed, parse_time, parse_fsize
from . import curves

DEFAULT_MAIN_TICK = "2s"
DEFAULT_MAX_TASKS_PER_TICK = 20

DEFAULT_CONFIG_FILE = "config.yml"
DEFAULT_STATE_FILE = "auto-qb-state.json"

DEFAULT_INTERVAL = "60s"
DEFAULT_REMOVE_SIMILAR_TAGS = False

# 自动添加集数标签: 种子添加时, 若名称不含集数标记则从文件列表解析集数(如 01.mkv~05.mkv -> E1-5)打标签
DEFAULT_ADD_EPISODE_TAGS = False

# 全局 HR 默认输出设置(站点 hr 段未设置时使用)
DEFAULT_HR_OUTPUT = {
    "add_tag": "",
    "add_category": "!!HR${required_seeding_time}!!",
    "overwrite_category": False,
    "add_tag_for_satisfied": "",
    "add_category_for_satisfied": "--HR${required_seeding_time}--",
    "overwrite_category_for_satisfied": False,
}

# 种子分组管理(辅种管理): 将指向相同文件列表的种子归为一组, 统一检查
DEFAULT_GROUPING_ENABLED = False
DEFAULT_GROUPING_INTERVAL = "5M"  # 分组检查间隔(拉全量文件列表开销大, 默认降频)
DEFAULT_GROUPING_MISSING_TAG = "MISSING"

UNLIMITED_SPEED = "0KiB/s"


@dataclass
class LoggingConfig:
    level: str | int = "INFO"
    file: str = ""
    max_bytes: str | int = "10MiB"
    format: str = "%(asctime)s [%(levelname)s] %(message)s"


@dataclass
class QbittorrentConfig:
    host: str
    port: int
    username: str
    password: str

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
    tags: List[str]
    remove_tags: List[str]
    upload_speed_limit: Optional[int]  # 字节/秒
    download_speed_limit: Optional[int]  # 字节/秒
    hr: Optional[HRRule] = None  # HR 规则(已合并全局默认输出设置), None = 无 HR 配置
    rules: List[str] = field(default_factory=list)  # 规则引用列表, 如 ["@rule_set", "@rule_set.rule1"]
    remove_similar_tags: bool = False  # 删除类似标签(站点覆盖全局后的值)


@dataclass
class GroupingConfig:
    """种子分组管理(辅种管理): 将指向相同文件列表的种子归为一组

    enabled: 启用分组检查(缺文件检查统一由分组事件驱动承担, 同组共享一次磁盘扫描)
    missing_tag: 文件丢失时整组添加的标签
    """
    enabled: bool = True
    check_missing_files: bool = True  # 启用缺文件检查
    missing_tag: str = 'MISSING'


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

    bat_path: history_traffic.dat 路径(每行 "YYYY/MM/DD <上传KB>/<下载KB>", 单位 KB=1024B)
    curves: 多条 period 曲线(同方向多条命中时取最严限速, 见 curves.merge_direction)
    interval: 曲线任务执行间隔(秒), 对应配置 interval: 10M; None = 未指定, 回退主 interval
    """
    bat_path: str
    curves: List[PeriodCurve]
    interval: Optional[float] = None  # 秒; None = 使用 config.interval


@dataclass
class Config:
    main_tick: float
    max_tasks_per_tick: int

    interval: float  # 默认任务间隔: 种子列表刷新/种子级内置功能任务的默认 interval, 秒

    state_file: str  # 状态持久化文件(规则执行历史/上传量快照)

    logging: LoggingConfig

    rules_config: dict  # 规则集原始配置: {规则集名: {规则名: spec}}, 来自 config 下 *_rules 段

    remove_similar_tags: bool
    add_episode_tags: bool  # 种子添加时自动添加集数标签(如 E1-5): 名称不含集数时从文件列表解析

    hr: HRRule  # 全局 HR 默认输出设置(站点 hr 段未设置时兜底; 规则字段为空)

    # 全局标签清理: 彻底删除的标签格式 / 彻底删除无种子的标签格式(均支持正则, regex: 前缀)
    delete_tags: List[str]
    delete_tags_if_has_no_torrents: List[str]

    grouping: GroupingConfig  # 种子分组管理(辅种管理)

    qbittorrent: QbittorrentConfig
    trackers: Dict[str, TrackerConfig]

    # 全局限速曲线(Traffic Monitor): 读取 dat 流量, 按多条 period 曲线聚合, 自动设置 qB 全局速度限制
    global_speed_limit_curve: Optional[GlobalSpeedLimitCurve] = None  # None = 未启用


def load_global_speed_limit_curve(spec) -> Optional[GlobalSpeedLimitCurve]:
    """解析 config.global_speed_limit_curve 段(spec 为 None/缺省 -> None, 不启用)

    fail-fast: 结构/数值/键全部在加载时校验, 任何非法抛 ValueError。
    配置样式:
        interval: 10M              # 曲线任务执行间隔(可选, 缺省用主 interval)
        traffic_source:
            - traffic_monitor:
                bat_path: ".../history_traffic.dat"
        curves:
            - curve:                # 每条 period 曲线为 curve 单项映射
                period: 1D          # day/1D | month | ND(最近 N 天)
                upload_curve:       # 阈值(parse_fsize) -> {upload_speed_limit: 速度}
                    - 10GiB: {upload_speed_limit: 6MiB/s}
                download_curve:     # 可省略(省略 = 不管理该方向)
                    - 30GiB: {download_speed_limit: 11MiB/s}
            - curve:
                period: 7D
                upload_curve: [...]
    """
    if spec is None:
        return None
    if not isinstance(spec, dict):
        raise ValueError("global_speed_limit_curve 必须是字典")
    unknown = set(spec) - {"traffic_source", "curves", "interval"}
    if unknown:
        raise ValueError(f"global_speed_limit_curve 未知键: {sorted(unknown)}")

    # interval: 曲线任务执行间隔(可选; 缺省 None = 回退主 interval)
    interval: Optional[float] = None
    if spec.get("interval") is not None:
        interval = parse_time(str(spec["interval"]))
        if interval <= 0:
            raise ValueError(f"global_speed_limit_curve.interval 必须为正时间: {spec['interval']}")

    # traffic_source: 数据源列表, 当前仅支持单个 traffic_monitor
    raw_sources = spec.get("traffic_source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("global_speed_limit_curve.traffic_source 必须是非空列表")
    if len(raw_sources) != 1:
        raise ValueError("global_speed_limit_curve.traffic_source 当前仅支持单个数据源")
    source = raw_sources[0]
    if not isinstance(source, dict):
        raise ValueError("global_speed_limit_curve.traffic_source 元素必须是字典")
    unknown = set(source) - {"traffic_monitor"}
    if unknown:
        raise ValueError(f"global_speed_limit_curve.traffic_source 不支持的来源: {sorted(unknown)}")
    if "traffic_monitor" not in source:
        raise ValueError("global_speed_limit_curve.traffic_source 仅支持 traffic_monitor 数据源")
    tm = source["traffic_monitor"]
    if not isinstance(tm, dict):
        raise ValueError("traffic_monitor 配置必须是字典")
    unknown = set(tm) - {"bat_path"}
    if unknown:
        raise ValueError(f"traffic_monitor 未知键: {sorted(unknown)}")
    bat_path = str(tm.get("bat_path", "")).strip()
    if not bat_path:
        raise ValueError("traffic_monitor 缺少 bat_path")

    # curves: 多条 period 曲线(重复 period 拒绝)
    raw_curves = spec.get("curves")
    if not isinstance(raw_curves, list) or not raw_curves:
        raise ValueError("global_speed_limit_curve.curves 必须是非空列表")

    period_curves: List[PeriodCurve] = []
    seen_periods = set()
    for i, item in enumerate(raw_curves):
        where = f"global_speed_limit_curve.curves[{i}]"
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError(f"{where} 必须为单项映射: curve: {{period/upload_curve/download_curve}}")
        (curve_key, curve_spec), = item.items()
        if curve_key != "curve":
            raise ValueError(f"{where} 仅支持键 curve, 实际: {curve_key}")
        if not isinstance(curve_spec, dict):
            raise ValueError(f"{where}.curve 必须是字典")
        where = f"{where}.curve"
        unknown = set(curve_spec) - {"period", "upload_curve", "download_curve"}
        if unknown:
            raise ValueError(f"{where} 未知键: {sorted(unknown)}")
        if "period" not in curve_spec:
            raise ValueError(f"{where} 缺少 period")
        period = curves.normalize_period(curve_spec["period"])
        if period in seen_periods:
            raise ValueError(f"{where} 重复 period: {curve_spec['period']}")
        seen_periods.add(period)
        if "upload_curve" not in curve_spec and "download_curve" not in curve_spec:
            raise ValueError(f"{where} 需配置 upload_curve 和/或 download_curve")
        upload_points = (
            _parse_curve_points(curve_spec["upload_curve"], "upload_speed_limit", f"{where}.upload_curve")
            if "upload_curve" in curve_spec else None
        )
        download_points = (
            _parse_curve_points(curve_spec["download_curve"], "download_speed_limit", f"{where}.download_curve")
            if "download_curve" in curve_spec else None
        )
        period_curves.append(PeriodCurve(period=period, upload_points=upload_points, download_points=download_points))
    return GlobalSpeedLimitCurve(bat_path=bat_path, curves=period_curves, interval=interval)


def _parse_curve_points(raw_list, direction_key: str, where: str) -> List[CurvePoint]:
    """解析 upload_curve/download_curve 列表 -> 升序 CurvePoint 列表

    每元素为单项映射: 阈值大小(parse_fsize) -> {<direction_key>: 速度(parse_speed)};
    阈值必须 > 0 且严格递增; 速度 >= 0(0 = 该档不限速)。
    """
    if not isinstance(raw_list, list) or not raw_list:
        raise ValueError(f"{where} 必须是非空列表")
    points: List[CurvePoint] = []
    prev_threshold = 0
    for j, entry in enumerate(raw_list):
        pos = f"{where}[{j}]"
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ValueError(f"{pos} 必须为单项映射: 阈值: {{{direction_key}: 速度}}")
        (threshold_str, speed_spec), = entry.items()
        threshold = parse_fsize(str(threshold_str))
        if threshold <= 0:
            raise ValueError(f"{pos} 阈值必须大于 0: {threshold_str}")
        if threshold <= prev_threshold:
            raise ValueError(f"{pos} 阈值必须严格递增: {threshold_str}")
        prev_threshold = threshold
        if not isinstance(speed_spec, dict):
            raise ValueError(f"{pos} 速度配置必须是字典")
        unknown = set(speed_spec) - {direction_key}
        if unknown:
            raise ValueError(f"{pos} 未知键: {sorted(unknown)}")
        if direction_key not in speed_spec:
            raise ValueError(f"{pos} 缺少 {direction_key}")
        speed = parse_speed(str(speed_spec[direction_key]))
        points.append(CurvePoint(threshold_bytes=threshold, speed_bytes_per_s=speed))
    return points


def load_logging_config(spec: dict) -> LoggingConfig:
    default = LoggingConfig()

    level_str = spec.get('level', default.level)

    level = getattr(logging, level_str.upper(), logging.INFO)
    file = spec.get('file', default.file)
    max_bytes = parse_fsize(spec.get('max_bytes', default.max_bytes))
    format = spec.get('format', default.format)
    return LoggingConfig(level=level, file=file, max_bytes=max_bytes, format=format)


def load_qbittorrent_config(spec: dict) -> QbittorrentConfig:
    return QbittorrentConfig(
        host=spec.get('host', '127.0.0.1'),
        port=int(spec.get('port', 8080)),
        username=spec.get('username', ''),
        password=spec.get('password', ''),
    )


def load_grouping_config(spec: dict) -> GroupingConfig:
    default = GroupingConfig()
    return GroupingConfig(
        enabled=parse_bool(spec.get("enabled", default.enabled)),
        check_missing_files=parse_bool(spec.get("check_missing_files", default.check_missing_files)),
        missing_tag=spec.get("missing_tag", default.missing_tag),
    )


def load_tracker_config(name: str, spec: dict, hr: HRRule, global_remove_similar: bool) -> TrackerConfig:
    return TrackerConfig(
        name=name,
        domains=spec["domains"],
        tags=spec.get("tags", []),
        remove_tags=spec.get("remove_tags", []),
        upload_speed_limit=parse_speed(spec.get("upload_speed_limit", UNLIMITED_SPEED)),
        download_speed_limit=parse_speed(spec.get("download_speed_limit", UNLIMITED_SPEED)),
        hr=hr,
        rules=spec.get("rules", []) or [],
        remove_similar_tags=parse_bool(spec.get("remove_similar_tags", global_remove_similar)),
    )


# TODO: optimize
def load_global_hr(spec: dict) -> HRRule:
    return HRRule(
        add_tag=spec.get("add_tag", DEFAULT_HR_OUTPUT["add_tag"]),
        add_category=spec.get("add_category", DEFAULT_HR_OUTPUT["add_category"]),
        overwrite_category=parse_bool(spec.get("overwrite_category", DEFAULT_HR_OUTPUT["overwrite_category"])),
        add_tag_for_satisfied=spec.get("add_tag_for_satisfied", DEFAULT_HR_OUTPUT["add_tag_for_satisfied"]),
        add_category_for_satisfied=spec.get(
            "add_category_for_satisfied", DEFAULT_HR_OUTPUT["add_category_for_satisfied"]
        ),
        overwrite_category_for_satisfied=parse_bool(
            spec.get("overwrite_category_for_satisfied", DEFAULT_HR_OUTPUT["overwrite_category_for_satisfied"])
        ),
    )


# TODO: optimize
def load_tracker_hr(spec: dict, global_hr: dict) -> HRRule:
    """解析站点 hr 配置段, 与全局 hr 默认输出设置合并(站点字段优先, 全局兜底)

    站点段: required_seeding_time(必填) / required_share_ratio / extra_seeding_time /
            condition(80% 或 10MiB) + 可覆盖全局的输出字段
    """
    time_raw = str(spec.get("required_seeding_time", "") or "").strip()
    if not time_raw:
        raise ValueError("hr 配置缺少 required_seeding_time")
    # 提取原始时间字符串用于变量替换: "3D" / "12H" / "1.5D"
    raw = time_raw.upper()

    # 输出设置: 站点显式设置优先, 否则用全局默认
    def out(key: str):
        return spec.get(key, global_hr.get(key, DEFAULT_HR_OUTPUT.get(key, "")))

    def out_bool(key: str):
        return parse_bool(spec.get(key, global_hr.get(key, DEFAULT_HR_OUTPUT.get(key, False))))

    return HRRule(
        required_seeding_time=parse_time(raw),
        required_seeding_time_raw=raw,
        required_share_ratio=float(spec.get("required_share_ratio", 0) or 0),
        extra_seeding_time=parse_time(str(spec.get("extra_seeding_time", "0S") or "0S")),
        condition=parse_hr_condition(spec.get("condition", "80%")),
        add_tag=out("add_tag"),
        add_category=out("add_category"),
        overwrite_category=out_bool("overwrite_category"),
        add_tag_for_satisfied=out("add_tag_for_satisfied"),
        add_category_for_satisfied=out("add_category_for_satisfied"),
        overwrite_category_for_satisfied=out_bool("overwrite_category_for_satisfied"),
    )


def load_config(config_path: str) -> Config:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    cfg = data.get("config", {})

    # qbittorrent 配置
    qb_config = load_qbittorrent_config(cfg.get("qbittorrent", {}))

    # 规则集: config 段下所有以 "_rules" 结尾的键
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules") and isinstance(v, dict)}

    global_hr = cfg.get("hr") or {}
    global_remove_similar = parse_bool(cfg.get("remove_similar_tags", DEFAULT_REMOVE_SIMILAR_TAGS))

    # Trackers 配置
    trackers = {}

    # 当trackers字段为空时, yaml会将其解析为str导致解析错误
    trackers_config = cfg.get("trackers", {})
    if not isinstance(trackers_config, dict):
        trackers_config = {}

    for name, tdata in trackers_config.items():
        hr_spec = tdata.get("hr")
        hr = load_tracker_hr(hr_spec, global_hr) if isinstance(hr_spec, dict) else None
        trackers[name] = load_tracker_config(name, tdata, hr, global_remove_similar)

    # 全局标签清理格式: @tracker_tags 引用展开为所有 tracker 配置的 tags 并集
    tracker_tags = sorted({t for tc in trackers.values() for t in tc.tags})
    delete_tags = _expand_tracker_tags_refs(cfg.get("delete_tags", []) or [], tracker_tags)
    delete_tags_if_has_no_torrents = _expand_tracker_tags_refs(
        cfg.get("delete_tags_if_has_no_torrents", []) or [], tracker_tags
    )

    return Config(
        main_tick=parse_time(cfg.get("main_tick", DEFAULT_MAIN_TICK)),
        max_tasks_per_tick=int(cfg.get("max_tasks_per_tick", DEFAULT_MAX_TASKS_PER_TICK)),
        interval=parse_time(cfg.get("interval", DEFAULT_INTERVAL)),
        state_file=cfg.get("state_file", DEFAULT_STATE_FILE),
        logging=load_logging_config(cfg.get("log", {})),
        rules_config=rules_config,
        remove_similar_tags=global_remove_similar,
        add_episode_tags=parse_bool(cfg.get("add_episode_tags", DEFAULT_ADD_EPISODE_TAGS)),
        hr=load_global_hr(global_hr),
        delete_tags=delete_tags,
        delete_tags_if_has_no_torrents=delete_tags_if_has_no_torrents,
        grouping=load_grouping_config(cfg.get("grouping", {})),
        qbittorrent=qb_config,
        trackers=trackers,
        global_speed_limit_curve=load_global_speed_limit_curve(cfg.get("global_speed_limit_curve")),
    )


def _expand_tracker_tags_refs(items: List[str], tracker_tags: List[str]) -> List[str]:
    """展开 @tracker_tags 引用: 替换为所有 tracker 配置的 tags 并集(去重保序)"""
    out: List[str] = []
    seen = set()
    for it in items or []:
        it = str(it).strip()

        ignore_case = ""
        if it.endswith(":ignore_case"):
            ignore_case = ":ignore_case"
            it = it[:-12]

        if it == "@tracker_tags":
            for tag in tracker_tags:
                tag = tag + ignore_case
                if tag not in seen:
                    seen.add(tag)
                    out.append(tag)
        elif it and it not in seen:
            seen.add(it + ignore_case)
            out.append(it + ignore_case)
    return out

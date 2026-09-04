"""配置结构与加载: 默认常量 / 数据类 / fail-fast 全量校验 / load_config

校验约定:
- 显式留空的键(空串/None)视为未配置, 走默认值(_strip_none); 必填键缺失则报错
- 校验聚合全部错误一次性报告(validate_config), 每条带配置路径(如 config.trackers.tracker1)
- 值格式复用 utils.parse_*(时间/大小/速度/布尔)单一事实来源
- 规则集 spec 的条件/动作名称经 registry 延迟导入校验(避免模块循环依赖)
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml, logging

from .utils import parse_bool, parse_hr_condition, parse_speed, parse_time, parse_fsize
from . import curves

DEFAULT_MAIN_TICK = "2s"
DEFAULT_MAX_TASKS_PER_TICK = 20


class ConfigError(ValueError):
    """配置错误(文件读取失败/YAML 解析失败/校验失败/启动期规则 spec 错误)

    继承 ValueError 以兼容既有 except ValueError 调用方; CLI 层捕获本异常输出干净
    错误信息(无堆栈)并以非零码退出, 其它类型异常(程序 bug)不在此列, 照常抛出。
    """

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


def _validate_global_speed_limit_curve(spec, errors: List[str]) -> None:
    """校验 config.global_speed_limit_curve 段(结构/键/数值), 错误聚合到 errors(带完整路径)

    配置样式见 load_global_speed_limit_curve; 解析(load_global_speed_limit_curve)假定已通过本校验。
    """
    where = "config.global_speed_limit_curve"
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    unknown = set(spec) - {"traffic_source", "curves", "interval"}
    if unknown:
        errors.append(f"{where}: 未知键: {sorted(unknown)}")

    # interval: 曲线任务执行间隔(可选; 缺省回退主 interval), 须为正时间
    if "interval" in spec:
        _try_time(spec["interval"], f"{where}.interval", errors, positive=True)

    # traffic_source: 数据源列表, 当前仅支持单个 traffic_monitor
    raw_sources = spec.get("traffic_source")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append(f"{where}.traffic_source: 必须是非空列表")
    elif len(raw_sources) != 1:
        errors.append(f"{where}.traffic_source: 当前仅支持单个数据源")
    else:
        source = raw_sources[0]
        if not isinstance(source, dict) or set(source) != {"traffic_monitor"}:
            errors.append(f"{where}.traffic_source: 仅支持单项映射 traffic_monitor: {{bat_path: ...}}")
        else:
            tm = source["traffic_monitor"]
            if not isinstance(tm, dict):
                errors.append(f"{where}.traffic_monitor: 必须是字典")
            else:
                unknown = set(tm) - {"bat_path"}
                if unknown:
                    errors.append(f"{where}.traffic_monitor: 未知键: {sorted(unknown)}")
                if not str(tm.get("bat_path", "")).strip():
                    errors.append(f"{where}.traffic_monitor: 缺少 bat_path")

    # curves: 多条 period 曲线(重复 period 拒绝)
    raw_curves = spec.get("curves")
    if not isinstance(raw_curves, list) or not raw_curves:
        errors.append(f"{where}.curves: 必须是非空列表")
        return
    seen_periods = set()
    for i, item in enumerate(raw_curves):
        cwhere = f"{where}.curves[{i}]"
        if not isinstance(item, dict) or len(item) != 1 or "curve" not in item:
            errors.append(f"{cwhere} 必须为单项映射: curve: {{period/upload_curve/download_curve}}")
            continue
        curve_spec = item["curve"]
        if not isinstance(curve_spec, dict):
            errors.append(f"{cwhere}.curve: 必须是字典")
            continue
        cwhere = f"{cwhere}.curve"
        unknown = set(curve_spec) - {"period", "upload_curve", "download_curve"}
        if unknown:
            errors.append(f"{cwhere}: 未知键: {sorted(unknown)}")
        if "period" not in curve_spec:
            errors.append(f"{cwhere}: 缺少 period")
        else:
            try:
                period = curves.normalize_period(curve_spec["period"])
            except ValueError as e:
                errors.append(f"{cwhere}.period: {e}")
            else:
                if period in seen_periods:
                    errors.append(f"{cwhere}: 重复 period: {curve_spec['period']}")
                seen_periods.add(period)
        if "upload_curve" not in curve_spec and "download_curve" not in curve_spec:
            errors.append(f"{cwhere}: 需配置 upload_curve 和/或 download_curve")
        for key, direction in (("upload_curve", "upload_speed_limit"), ("download_curve", "download_speed_limit")):
            if key in curve_spec:
                _validate_curve_points(curve_spec[key], f"{cwhere}.{key}", direction, errors)


def _validate_curve_points(raw_list, where: str, direction_key: str, errors: List[str]) -> None:
    """校验 upload_curve/download_curve 列表: 非空单项映射, 阈值 > 0 且严格递增, 速度仅含方向键"""
    if not isinstance(raw_list, list) or not raw_list:
        errors.append(f"{where}: 必须是非空列表")
        return
    prev_threshold = 0
    for j, entry in enumerate(raw_list):
        pos = f"{where}[{j}]"
        if not isinstance(entry, dict) or len(entry) != 1:
            errors.append(f"{pos} 必须为单项映射: 阈值: {{{direction_key}: 速度}}")
            continue
        threshold_str, speed_spec = next(iter(entry.items()))
        try:
            threshold = parse_fsize(str(threshold_str))
        except ValueError as e:
            errors.append(f"{pos}: {e}")
            continue
        if threshold <= 0:
            errors.append(f"{pos} 阈值必须大于 0: {threshold_str}")
        elif threshold <= prev_threshold:
            errors.append(f"{pos} 阈值必须严格递增: {threshold_str}")
        else:
            prev_threshold = threshold
        if not isinstance(speed_spec, dict):
            errors.append(f"{pos} 速度配置必须是字典")
        elif set(speed_spec) - {direction_key}:
            errors.append(f"{pos} 未知键: {sorted(set(speed_spec) - {direction_key})}")
        elif direction_key not in speed_spec:
            errors.append(f"{pos} 缺少 {direction_key}")
        else:
            _try(parse_speed, str(speed_spec[direction_key]), pos, errors)


def load_global_speed_limit_curve(spec) -> Optional[GlobalSpeedLimitCurve]:
    """解析 config.global_speed_limit_curve 段(spec 为 None/缺省 -> None, 不启用)

    先验证再解析: 结构/键/数值合法性由 _validate_global_speed_limit_curve 在 fail-fast
    校验阶段聚合完成, 此处仅做转换, 可假定配置正确(不含任何检查)。
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

    # 曲线任务执行间隔(可选; 缺省 None = 回退主 interval)
    interval: Optional[float] = parse_time(str(spec["interval"])) if "interval" in spec else None

    # 数据源: 校验已保证仅单个 traffic_monitor
    (source,) = spec["traffic_source"]
    bat_path = str(source["traffic_monitor"]["bat_path"]).strip()

    period_curves: List[PeriodCurve] = []
    for item in spec["curves"]:
        curve_spec = item["curve"]
        period_curves.append(
            PeriodCurve(
                period=curves.normalize_period(curve_spec["period"]),
                upload_points=(
                    _parse_curve_points(curve_spec["upload_curve"], "upload_speed_limit")
                    if "upload_curve" in curve_spec else None
                ),
                download_points=(
                    _parse_curve_points(curve_spec["download_curve"], "download_speed_limit")
                    if "download_curve" in curve_spec else None
                ),
            )
        )
    return GlobalSpeedLimitCurve(bat_path=bat_path, curves=period_curves, interval=interval)


def _parse_curve_points(raw_list, direction_key: str) -> List[CurvePoint]:
    """解析 upload_curve/download_curve 列表 -> CurvePoint 列表(仅转换, 合法性由校验阶段保证)

    每元素为单项映射: 阈值大小(parse_fsize) -> {<direction_key>: 速度(parse_speed)};
    阈值已保证 > 0 且严格递增; 速度 >= 0(0 = 该档不限速)。
    """
    points: List[CurvePoint] = []
    for entry in raw_list:
        threshold_str, speed_spec = next(iter(entry.items()))
        points.append(
            CurvePoint(
                threshold_bytes=parse_fsize(str(threshold_str)),
                speed_bytes_per_s=parse_speed(str(speed_spec[direction_key])),
            )
        )
    return points


def load_logging_config(spec: dict) -> LoggingConfig:
    """加载日志配置(仅转换, 合法性由 validate_config 保证)"""
    default = LoggingConfig()
    return LoggingConfig(
        level=getattr(logging, str(spec.get("level", default.level)).upper()),
        file=spec.get("file", default.file),
        max_bytes=parse_fsize(spec.get("max_bytes", default.max_bytes)),
        format=spec.get("format", default.format),
    )


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
            condition(80% 或 10MiB) + 可覆盖全局的输出字段; 合法性由 validate_config 保证。
    """
    # 原始时间字符串用于变量替换: "3D" / "12H" / "1.5D"
    raw = str(spec["required_seeding_time"]).strip().upper()

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


# ---------- fail-fast 全量配置校验 ----------

# 规则 spec 已知键(trigger 仅支持 interval, 其余触发时机规划中)
RULE_KNOWN_KEYS = {
    "enabled", "trigger", "interval", "execute_once", "cooldown", "conditions", "actions", "stop_following_rules_if"
}
EXECUTE_ONCE_VALUES = ("never", "once", "daily", "hourly")
STOP_IF_VALUES = ("conditions-met", "conditions-not-met", "action-failed", "all-actions-succeed", "always", "never")

# config 顶层已知键; single_instance_lock 为规划中预留键(README 已文档化, 暂不生效)
KNOWN_CONFIG_KEYS = {
    "qbittorrent", "main_tick", "max_tasks_per_tick", "interval", "state_file", "log",
    "remove_similar_tags", "add_episode_tags", "hr", "delete_tags", "delete_tags_if_has_no_torrents",
    "grouping", "trackers", "global_speed_limit_curve", "single_instance_lock",
}
KNOWN_LOG_KEYS = {"level", "file", "max_bytes", "format"}
KNOWN_QBITTORRENT_KEYS = {"host", "port", "username", "password"}
KNOWN_GROUPING_KEYS = {"enabled", "check_missing_files", "missing_tag"}
KNOWN_HR_KEYS = {
    "add_tag", "add_category", "overwrite_category",
    "add_tag_for_satisfied", "add_category_for_satisfied", "overwrite_category_for_satisfied",
}
KNOWN_TRACKER_KEYS = {
    "domains", "tags", "remove_tags", "upload_speed_limit", "download_speed_limit",
    "hr", "rules", "remove_similar_tags",
}
KNOWN_TRACKER_HR_KEYS = {
    "required_seeding_time", "required_share_ratio", "extra_seeding_time", "condition", *KNOWN_HR_KEYS
}


def _strip_none(value):
    """递归剔除空值(None/空串): 显式留空的键/列表项视为未配置(走默认值)

    yaml.BaseLoader 将 `key:` 留空解析为 ''(而非 None), 与显式 "" 无法区分, 统一视为未配置;
    默认值本为空串的键(如 hr.add_tag)行为不变。
    """
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None and v != ""}
    if isinstance(value, list):
        return [_strip_none(v) for v in value if v is not None and v != ""]
    return value


def _check_unknown_keys(spec: dict, known: set, where: str, errors: List[str]) -> None:
    unknown = set(spec) - set(known)
    if unknown:
        errors.append(f"{where}: 未知键 {sorted(unknown)}, 可用键: {sorted(known)}")


def _try(parse_fn, value, where: str, errors: List[str]) -> None:
    """用解析函数校验值格式(复用 utils.parse_* 单一事实来源), 失败记录错误"""
    try:
        parse_fn(value)
    except ValueError as e:
        errors.append(f"{where}: {e}")


def _try_time(value, where: str, errors: List[str], positive: bool = False) -> None:
    """时间格式校验; positive=True 时要求 > 0(如 main_tick, 防止 0 忙循环)"""
    try:
        seconds = parse_time(value)
    except ValueError as e:
        errors.append(f"{where}: {e}")
        return
    if positive and seconds <= 0:
        errors.append(f"{where}: 必须为正时间: {value}")


def _check_str_list(value, where: str, errors: List[str]) -> bool:
    """值必须是字符串列表(空列表合法); 返回是否通过"""
    if not isinstance(value, list):
        errors.append(f"{where}: 必须是列表")
        return False
    bad = [i for i, v in enumerate(value) if not isinstance(v, str) or not v.strip()]
    if bad:
        errors.append(f"{where}: 第 {bad} 项必须是非空字符串")
        return False
    return True


def _check_regex_patterns(patterns: list, where: str, errors: List[str]) -> None:
    """regex: 前缀模式须可编译(否则运行时会静默跳过匹配, 错误被掩盖)"""
    for i, pat in enumerate(patterns):
        if isinstance(pat, str) and pat.startswith("regex:"):
            try:
                re.compile(pat[6:])
            except re.error as e:
                errors.append(f"{where}[{i}]: 非法正则: {e}")


def _validate_log(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.log: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_LOG_KEYS, "config.log", errors)
    if "level" in spec:
        level = getattr(logging, str(spec["level"]).upper(), None)
        if not isinstance(level, int):
            errors.append(f"config.log.level: 非法日志等级 '{spec['level']}', 可选: DEBUG/INFO/WARNING/ERROR/CRITICAL")
    if "max_bytes" in spec:
        _try(parse_fsize, spec["max_bytes"], "config.log.max_bytes", errors)
    # file / format: 任意字符串(file 留空 = 仅控制台)


def _validate_qbittorrent(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.qbittorrent: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_QBITTORRENT_KEYS, "config.qbittorrent", errors)
    if "port" in spec:
        try:
            port = int(spec["port"])
        except (TypeError, ValueError):
            errors.append(f"config.qbittorrent.port: 必须是整数: {spec['port']}")
        else:
            if not 1 <= port <= 65535:
                errors.append(f"config.qbittorrent.port: 超出范围 1-65535: {port}")


def _validate_global_hr(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.hr: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_HR_KEYS, "config.hr", errors)
    for key in ("overwrite_category", "overwrite_category_for_satisfied"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.hr.{key}", errors)


def _validate_grouping(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.grouping: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_GROUPING_KEYS, "config.grouping", errors)
    for key in ("enabled", "check_missing_files"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.grouping.{key}", errors)


def _validate_tag_lists(cfg: dict, errors: List[str]) -> None:
    """delete_tags / delete_tags_if_has_no_torrents: 字符串列表 + regex: 前缀可编译"""
    for key in ("delete_tags", "delete_tags_if_has_no_torrents"):
        if key not in cfg:
            continue
        where = f"config.{key}"
        if _check_str_list(cfg[key], where, errors):
            _check_regex_patterns(cfg[key], where, errors)


def _check_rule_refs(refs: List[str], rules_config: dict, where: str, errors: List[str]) -> None:
    """tracker.rules 引用校验: 必须 @ 开头, 且引用的规则集/规则存在(否则运行时静默不执行)"""
    for ref in refs:
        r = str(ref).strip()
        if not r.startswith("@") or not r[1:].strip():
            errors.append(f"{where}: 规则引用必须以 @ 开头: '{ref}' (如 '@规则集' 或 '@规则集.规则名')")
            continue
        r = r[1:]
        if "." in r:
            group, rule_name = r.split(".", 1)
            group_spec = rules_config.get(group)
            if not isinstance(group_spec, dict) or rule_name not in group_spec:
                errors.append(f"{where}: 引用的规则不存在: @{r}")
        elif r not in rules_config:
            errors.append(f"{where}: 引用的规则集不存在: @{r}")


def _validate_tracker_hr(spec, where: str, errors: List[str]) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_TRACKER_HR_KEYS, where, errors)
    if not str(spec.get("required_seeding_time", "") or "").strip():
        errors.append(f"{where}: 缺少必填键 required_seeding_time(要求做种时间, 如 3D)")
    else:
        _try_time(spec["required_seeding_time"], f"{where}.required_seeding_time", errors)
    if "extra_seeding_time" in spec:
        _try_time(spec["extra_seeding_time"], f"{where}.extra_seeding_time", errors)
    if "required_share_ratio" in spec:
        _try(float, spec["required_share_ratio"], f"{where}.required_share_ratio(须为数字)", errors)
    if "condition" in spec:
        _try(parse_hr_condition, spec["condition"], f"{where}.condition(如 80% 或 10MiB)", errors)
    for key in ("overwrite_category", "overwrite_category_for_satisfied"):
        if key in spec:
            _try(parse_bool, spec[key], f"{where}.{key}", errors)


def _validate_trackers(spec, rules_config: dict, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.trackers: 必须是字典(留空表示未配置任何站点)")
        return
    for name, tdata in spec.items():
        where = f"config.trackers.{name}"
        if not isinstance(tdata, dict):
            errors.append(f"{where}: 必须是字典")
            continue
        _check_unknown_keys(tdata, KNOWN_TRACKER_KEYS, where, errors)
        # domains: 必填(无默认值), 非空字符串列表
        domains = tdata.get("domains")
        if domains is None:
            errors.append(f"{where}: 缺少必填键 domains(站点域名列表)")
        elif not (isinstance(domains, list) and domains and all(isinstance(d, str) and d.strip() for d in domains)):
            errors.append(f"{where}.domains: 必须是非空字符串列表")
        for key in ("tags", "remove_tags"):
            if key in tdata:
                if _check_str_list(tdata[key], f"{where}.{key}", errors) and key == "remove_tags":
                    _check_regex_patterns(tdata[key], f"{where}.{key}", errors)
        for key in ("upload_speed_limit", "download_speed_limit"):
            if key in tdata:
                _try(parse_speed, tdata[key], f"{where}.{key}", errors)
        if "remove_similar_tags" in tdata:
            _try(parse_bool, tdata["remove_similar_tags"], f"{where}.remove_similar_tags", errors)
        if "rules" in tdata:
            if _check_str_list(tdata["rules"], f"{where}.rules", errors):
                _check_rule_refs(tdata["rules"], rules_config, f"{where}.rules", errors)
        if "hr" in tdata:
            _validate_tracker_hr(tdata["hr"], f"{where}.hr", errors)


def _validate_rules(rules_config: dict, errors: List[str]) -> None:
    """规则集 spec 校验: 键/取值域/conditions-actions 结构; 条件与动作名称经 registry 延迟导入校验

    条件/动作 spec 值的深度校验(如 size 的比较表达式)在 Rule 构造时进行(带规则名上下文报错)。
    """
    from .rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

    for group_name, group in rules_config.items():
        gwhere = f"config.{group_name}"
        if not isinstance(group, dict):
            errors.append(f"{gwhere}: 必须是字典(规则名 -> 规则spec)")
            continue
        for rule_name, spec in group.items():
            where = f"{gwhere}.{rule_name}"
            if not isinstance(spec, dict):
                errors.append(f"{where}: 必须是字典")
                continue
            _check_unknown_keys(spec, RULE_KNOWN_KEYS, where, errors)
            if "enabled" in spec:
                _try(parse_bool, spec["enabled"], f"{where}.enabled", errors)
            for key in ("interval", "cooldown"):
                if key in spec:
                    _try_time(spec[key], f"{where}.{key}", errors)
            if "execute_once" in spec and spec["execute_once"] not in EXECUTE_ONCE_VALUES:
                errors.append(
                    f"{where}: execute_once 取值非法: '{spec['execute_once']}', 可选: {'/'.join(EXECUTE_ONCE_VALUES)}"
                )
            if "stop_following_rules_if" in spec and spec["stop_following_rules_if"] not in STOP_IF_VALUES:
                errors.append(
                    f"{where}: stop_following_rules_if 取值非法: '{spec['stop_following_rules_if']}', "
                    f"可选: {'/'.join(STOP_IF_VALUES)}"
                )
            if "trigger" in spec and spec["trigger"] != "interval":
                errors.append(f"{where}: trigger 取值非法: '{spec['trigger']}', 当前仅支持: interval")
            conds = spec.get("conditions")
            if conds is not None:
                if not isinstance(conds, list):
                    errors.append(f"{where}.conditions: 必须是列表")
                else:
                    for i, c in enumerate(conds):
                        _validate_plugin_entry(c, f"{where}.conditions[{i}]", registry.CONDITIONS, "条件", errors)
            acts = spec.get("actions")
            if acts is not None:
                if not isinstance(acts, list):
                    errors.append(f"{where}.actions: 必须是列表")
                else:
                    for i, a in enumerate(acts):
                        _validate_plugin_entry(a, f"{where}.actions[{i}]", registry.ACTIONS, "动作", errors)


def _validate_plugin_entry(entry, where: str, known: dict, kind: str, errors: List[str]) -> None:
    """conditions/actions 列表项校验: 单键字典 + 名称已注册(多键/空值会被静默丢弃, 必须报错)"""
    if not isinstance(entry, dict):
        errors.append(f"{where}: 必须是字典")
        return
    if len(entry) == 0:
        errors.append(f"{where}: 值不能为空(留空请删除该项)")
        return
    if len(entry) > 1:
        errors.append(f"{where}: 必须是单键字典: {sorted(entry)}")
        return
    name = next(iter(entry))
    if name == "ignore_next_action_error":
        _try(parse_bool, entry[name], f"{where}.{name}", errors)
    elif name not in known:
        errors.append(f"{where}: 未知{kind} '{name}', 可用: {sorted(known)}")


def validate_config(data) -> List[str]:
    """全量校验配置(结构/未知键/必填项/值格式), 返回错误列表(空 = 通过)

    - 顶层仅允许 config 键; 各段未知键一律报错(含 tracker/HR/规则 spec)
    - 必填项: tracker 的 domains、站点 hr 的 required_seeding_time; 其余键有默认值可留空
    - 值格式复用 utils.parse_*; 规则集 spec 连同条件/动作名称一并校验
    - global_speed_limit_curve 由 _validate_global_speed_limit_curve 校验(结构最复杂)
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append("配置文件为空或根节点不是字典")
        return errors
    _check_unknown_keys(data, {"config"}, "根节点", errors)
    cfg = data.get("config")
    if cfg is None:
        return errors  # 空配置: 全部使用默认值
    if not isinstance(cfg, dict):
        errors.append("config: 必须是字典")
        return errors

    # ---- config 顶层 ----
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}
    _check_unknown_keys(cfg, KNOWN_CONFIG_KEYS | set(rules_config), "config", errors)
    if "main_tick" in cfg:
        _try_time(cfg["main_tick"], "config.main_tick", errors, positive=True)
    if "max_tasks_per_tick" in cfg:
        _try(int, cfg["max_tasks_per_tick"], "config.max_tasks_per_tick(须为整数)", errors)
    if "interval" in cfg:
        _try_time(cfg["interval"], "config.interval", errors)
    if "state_file" in cfg and not str(cfg["state_file"]).strip():
        errors.append("config.state_file: 不能为空")
    if "remove_similar_tags" in cfg:
        _try(parse_bool, cfg["remove_similar_tags"], "config.remove_similar_tags", errors)
    if "add_episode_tags" in cfg:
        _try(parse_bool, cfg["add_episode_tags"], "config.add_episode_tags", errors)

    _validate_log(cfg.get("log"), errors)
    _validate_qbittorrent(cfg.get("qbittorrent"), errors)
    _validate_global_hr(cfg.get("hr"), errors)
    _validate_grouping(cfg.get("grouping"), errors)
    _validate_tag_lists(cfg, errors)
    _validate_trackers(cfg.get("trackers"), rules_config, errors)
    _validate_rules(rules_config, errors)

    gslc = cfg.get("global_speed_limit_curve")
    if gslc is not None:
        _validate_global_speed_limit_curve(gslc, errors)
    return errors


def load_config(config_path: str) -> Config:
    """加载并解析配置文件; 任何配置问题统一抛 ConfigError(文件读取/YAML 解析/校验失败)"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
    except OSError as e:
        raise ConfigError(f"配置文件读取失败: {e}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败: {e}") from e

    # 显式留空的键视为未配置(走默认值), 再全量校验(聚合全部错误一次性反馈, fail-fast)
    data = _strip_none(data)
    errors = validate_config(data)
    if errors:
        detail = "\n".join(f"  [{i + 1}] {e}" for i, e in enumerate(errors))
        raise ConfigError(f"配置校验失败({config_path}), 共 {len(errors)} 处:\n{detail}")

    cfg = data.get("config") or {}

    # qbittorrent 配置
    qb_config = load_qbittorrent_config(cfg.get("qbittorrent", {}))

    # 规则集: config 段下所有以 "_rules" 结尾的键
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}

    global_hr = cfg.get("hr") or {}
    global_remove_similar = parse_bool(cfg.get("remove_similar_tags", DEFAULT_REMOVE_SIMILAR_TAGS))

    # Trackers 配置(校验已保证 trackers/hr 为字典或未配置)
    trackers = {}
    for name, tdata in cfg.get("trackers", {}).items():
        hr = load_tracker_hr(tdata["hr"], global_hr) if "hr" in tdata else None
        trackers[name] = load_tracker_config(name, tdata, hr, global_remove_similar)

    # 全局标签清理格式: @tracker_tags 引用展开为所有 tracker 配置的 tags 并集
    tracker_tags = sorted({t for tc in trackers.values() for t in tc.tags})
    delete_tags = _expand_tracker_tags_refs(cfg.get("delete_tags", []), tracker_tags)
    delete_tags_if_has_no_torrents = _expand_tracker_tags_refs(cfg.get("delete_tags_if_has_no_torrents", []), tracker_tags)

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

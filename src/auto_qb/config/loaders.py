"""配置解析加载: load_config 入口 + 各段 load_* 函数(仅转换, 合法性由 validation.validate_config 保证)"""
import logging
from typing import List, Optional

import yaml

from .. import curves
from ..utils import parse_bool, parse_fsize, parse_hr_condition, parse_speed, parse_time
from .errors import ConfigError
from .models import (
    DEFAULT_ADD_EPISODE_TAGS,
    DEFAULT_HR_OUTPUT,
    DEFAULT_INTERVAL,
    DEFAULT_MAIN_TICK,
    DEFAULT_MAX_TASKS_PER_TICK,
    DEFAULT_REMOVE_SIMILAR_TAGS,
    DEFAULT_STATE_FILE,
    UNLIMITED_SPEED,
    Config,
    CurvePoint,
    GlobalSpeedLimitCurve,
    GroupingConfig,
    HRRule,
    LoggingConfig,
    PeriodCurve,
    QbittorrentConfig,
    TrackerConfig,
)
from .validation import validate_config, _strip_none


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


def load_global_speed_limit_curve(spec) -> Optional[GlobalSpeedLimitCurve]:
    """解析 config.global_speed_limit_curve 段(spec 为 None/缺省 -> None, 不启用)

    先验证再解析: 结构/键/数值合法性由 validation._validate_global_speed_limit_curve 在
    fail-fast 校验阶段聚合完成, 此处仅做转换, 可假定配置正确(不含任何检查)。
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

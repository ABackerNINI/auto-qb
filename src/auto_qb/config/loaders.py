"""配置解析加载: load_config 入口 + 各段 load_* 函数(仅转换, 合法性由 validation.validate_config 保证)

取值统一走 _get: 键存在 → parse(原始串); 键缺失 → dataclass 字段默认(解析后空间, 不再 parse),
默认值单一来源 = models 中的 dataclass 字段默认。
"""
import logging
from typing import List, Optional

import yaml

from .. import curves
from ..utils import parse_bool, parse_fsize, parse_hr_condition, parse_speed, parse_time
from .errors import ConfigError
from .models import (
    AddEpisodeTagsConfig,
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
from .validation import _strip_none, validate_config


def _under(data_dir: str, *parts: str) -> str:
    """把 parts 拼到数据主目录下(正斜杠风格, 去掉 data_dir 尾部斜杠; 配置空间路径统一用 /)"""
    base = str(data_dir).rstrip("/\\")
    return "/".join([base, *parts])


def _get(spec: dict, key: str, default, parse=None):
    """段内键读取统一入口: 键存在 → parse(原始串); 键缺失 → 字段默认(解析后空间, 不再 parse)"""
    if key not in spec:
        return default
    value = spec[key]
    return parse(value) if parse else value


def _get_episode_tags(spec) -> "AddEpisodeTagsConfig":
    """解析 config.add_episode_tags 段 -> AddEpisodeTagsConfig 实例(已校验, 这里仅转换)"""
    d = AddEpisodeTagsConfig()
    if not isinstance(spec, dict):
        return d
    return AddEpisodeTagsConfig(
        enabled=_get(spec, "enabled", d.enabled, parse_bool),
        add_tag_single=_get(spec, "add_tag_single", d.add_tag_single),
        add_tag_multi=_get(spec, "add_tag_multi", d.add_tag_multi),
    )


def _parse_log_level(value: str) -> int:
    """日志等级名 -> logging 数值等级(合法性由 validate_config 保证)"""
    return getattr(logging, str(value).upper())


def load_logging_config(spec: dict, default_file: str = "") -> LoggingConfig:
    d = LoggingConfig()
    return LoggingConfig(
        level=_get(spec, "level", d.level, _parse_log_level),
        # file 未配置(留空/空串, 均被 _strip_none 视为未配置) -> default_file 默认落盘; 仅代码层直接传 file="" 才是仅控制台
        file=_get(spec, "file", default_file),
        max_bytes=_get(spec, "max_bytes", d.max_bytes, parse_fsize),
        format=_get(spec, "format", d.format),
    )


def load_qbittorrent_config(spec: dict) -> QbittorrentConfig:
    d = QbittorrentConfig()
    return QbittorrentConfig(
        host=_get(spec, "host", d.host),
        port=_get(spec, "port", d.port, int),
        username=_get(spec, "username", d.username),
        password=_get(spec, "password", d.password),
    )


def load_grouping_config(spec: dict) -> GroupingConfig:
    d = GroupingConfig()
    return GroupingConfig(
        enabled=_get(spec, "enabled", d.enabled, parse_bool),
        check_missing_files=_get(spec, "check_missing_files", d.check_missing_files, parse_bool),
        missing_tag=_get(spec, "missing_tag", d.missing_tag),
    )


def load_tracker_config(name: str, spec: dict, hr: HRRule, global_remove_similar: bool) -> TrackerConfig:
    d = TrackerConfig(name=name, domains=spec["domains"])
    return TrackerConfig(
        name=name,
        domains=spec["domains"],
        tags=_get(spec, "tags", d.tags),
        remove_tags=_get(spec, "remove_tags", d.remove_tags),
        upload_speed_limit=_get(spec, "upload_speed_limit", d.upload_speed_limit, parse_speed),
        download_speed_limit=_get(spec, "download_speed_limit", d.download_speed_limit, parse_speed),
        hr=hr,
        rules=_get(spec, "rules", d.rules),
        # 站点未设置时回退全局值(运行参数, 非字段默认)
        remove_similar_tags=_get(spec, "remove_similar_tags", global_remove_similar, parse_bool),
    )


# TODO: optimize
def load_global_hr(spec: dict) -> HRRule:
    d = HRRule()
    return HRRule(
        add_tag=_get(spec, "add_tag", d.add_tag),
        add_category=_get(spec, "add_category", d.add_category),
        overwrite_category=_get(spec, "overwrite_category", d.overwrite_category, parse_bool),
        add_tag_for_satisfied=_get(spec, "add_tag_for_satisfied", d.add_tag_for_satisfied),
        add_category_for_satisfied=_get(spec, "add_category_for_satisfied", d.add_category_for_satisfied),
        overwrite_category_for_satisfied=_get(
            spec, "overwrite_category_for_satisfied", d.overwrite_category_for_satisfied, parse_bool
        ),
    )


# TODO: optimize
def load_tracker_hr(spec: dict, global_hr: dict) -> HRRule:
    """解析站点 hr 配置段, 与全局 hr 默认输出设置合并(站点字段优先, 全局兜底, 字段默认兜底全局)

    站点段: required_seeding_time(必填) / required_share_ratio / extra_seeding_time /
            condition(80% 或 10MiB) + 可覆盖全局的输出字段; 合法性由 validate_config 保证。
    """
    d = HRRule()

    # 输出设置回退链: 站点 spec -> 全局 hr 段 -> HRRule 字段默认
    def out(key: str):
        return spec.get(key, global_hr.get(key, getattr(d, key)))

    def out_bool(key: str):
        return parse_bool(spec.get(key, global_hr.get(key, getattr(d, key))))

    return HRRule(
        # 原始时间字符串用于变量替换: "3D" / "12H" / "1.5D"
        required_seeding_time=parse_time(spec["required_seeding_time"]),
        required_seeding_time_raw=str(spec["required_seeding_time"]).strip().upper(),
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
                dat_path: ".../history_traffic.dat"
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
    dat_path = str(source["traffic_monitor"]["dat_path"]).strip()

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
    return GlobalSpeedLimitCurve(dat_path=dat_path, curves=period_curves, interval=interval)


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
    d = Config()  # 全字段默认实例(默认值唯一来源: models 数据类字段)

    # 规则集: config 段下所有以 "_rules" 结尾的键
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}

    global_remove_similar = _get(cfg, "remove_similar_tags", d.remove_similar_tags, parse_bool)

    # Trackers 配置(校验已保证 trackers 为字典或未配置)
    trackers = {}
    for name, tdata in cfg.get("trackers", {}).items():
        hr = load_tracker_hr(tdata["hr"], cfg.get("hr") or {}) if "hr" in tdata else None
        trackers[name] = load_tracker_config(name, tdata, hr, global_remove_similar)

    # 全局标签清理格式: @tracker_tags 引用展开为所有 tracker 配置的 tags 并集
    tracker_tags = sorted({t for tc in trackers.values() for t in tc.tags})
    delete_tags = _expand_tracker_tags_refs(_get(cfg, "delete_tags", d.delete_tags), tracker_tags)
    delete_tags_if_has_no_torrents = _expand_tracker_tags_refs(
        _get(cfg, "delete_tags_if_has_no_torrents", d.delete_tags_if_has_no_torrents), tracker_tags
    )

    # 运行时数据主目录: 显式 state_file/log.file 优先; 未配置则派生到 data_dir 下
    data_dir = _get(cfg, "data_dir", d.data_dir)
    default_state_file = _under(data_dir, "state.json")
    default_log_file = _under(data_dir, "logs", "auto-qb.log")

    # 跳检标签全局名(动作运行时经 ctx 直接读取, 不注入动作 spec, 亦不可按规则覆盖)
    skip_checking_tag = str(_get(cfg, "skip_checking_tag", d.skip_checking_tag) or "").strip()

    return Config(
        main_tick=_get(cfg, "main_tick", d.main_tick, parse_time),
        max_tasks_per_tick=_get(cfg, "max_tasks_per_tick", d.max_tasks_per_tick, int),
        interval=_get(cfg, "interval", d.interval, parse_time),
        data_dir=data_dir,
        state_file=_get(cfg, "state_file", default_state_file),
        logging=load_logging_config(_get(cfg, "log", {}), default_file=default_log_file),
        rules_config=rules_config,
        remove_similar_tags=global_remove_similar,
        add_episode_tags=_get_episode_tags(_get(cfg, "add_episode_tags", d.add_episode_tags)),
        hr=load_global_hr(_get(cfg, "hr", {})),
        skip_checking_tag=skip_checking_tag,
        delete_tags=delete_tags,
        delete_tags_if_has_no_torrents=delete_tags_if_has_no_torrents,
        grouping=load_grouping_config(_get(cfg, "grouping", {})),
        qbittorrent=load_qbittorrent_config(_get(cfg, "qbittorrent", {})),
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

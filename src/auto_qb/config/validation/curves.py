"""全局限速曲线段校验(结构最复杂: traffic_source/curves/阶梯点)"""
from typing import List

from ... import curves
from ...infra.utils import parse_bool, parse_fsize, parse_speed
from .core import _try, _try_time


def _validate_global_speed_limit_curve(spec, errors: List[str]) -> None:
    """校验 config.global_speed_limit_curve 段(结构/键/数值), 错误聚合到 errors(带完整路径)

    配置样式见 loaders.load_global_speed_limit_curve; 解析假定已通过本校验。
    """
    where = "config.global_speed_limit_curve"
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    unknown = set(spec) - {"traffic_source", "curves", "interval", "enabled"}
    if unknown:
        errors.append(f"{where}: 未知键: {sorted(unknown)}")

    # interval: 曲线任务执行间隔(可选; 缺省回退主 interval), 须为正时间
    if "interval" in spec:
        _try_time(spec["interval"], f"{where}.interval", errors, positive=True)

    # enabled: 功能总开关(可选, 缺省 True); False = 整体停用(任务短路, Web 端视为未启用)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], f"{where}.enabled", errors)

    # traffic_source: 数据源列表, 当前仅支持单个 traffic_monitor
    raw_sources = spec.get("traffic_source")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append(f"{where}.traffic_source: 必须是非空列表")
    elif len(raw_sources) != 1:
        errors.append(f"{where}.traffic_source: 当前仅支持单个数据源")
    else:
        source = raw_sources[0]
        if not isinstance(source, dict) or set(source) != {"traffic_monitor"}:
            errors.append(f"{where}.traffic_source: 仅支持单项映射 traffic_monitor: {{dat_path: ...}}")
        else:
            tm = source["traffic_monitor"]
            if not isinstance(tm, dict):
                errors.append(f"{where}.traffic_monitor: 必须是字典")
            else:
                unknown = set(tm) - {"dat_path"}
                if unknown:
                    errors.append(f"{where}.traffic_monitor: 未知键: {sorted(unknown)}")
                if not str(tm.get("dat_path", "")).strip():
                    errors.append(f"{where}.traffic_monitor: 缺少 dat_path")

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

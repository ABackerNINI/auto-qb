"""config 各段校验器: 顶层简单段(log/qbittorrent/hr/grouping/web/notify 等)"""
import logging
from typing import List

from ...utils import parse_bool, parse_fsize, parse_hm, parse_hr_condition, parse_speed
from .core import _check_regex_patterns, _check_str_list, _check_unknown_keys, _try, _try_number, _try_time
from .rules import _check_rule_refs

KNOWN_LOG_KEYS = {"level", "file", "max_bytes", "format"}

KNOWN_QBITTORRENT_KEYS = {"host", "port", "username", "password"}

KNOWN_GROUPING_KEYS = {"enabled", "check_missing_files", "missing_tag"}

KNOWN_WEB_KEYS = {"enabled", "host", "port", "token", "skip_local_verify"}

KNOWN_NOTIFY_KEYS = {"enabled", "min_level", "quiet_hours", "max_per_hour", "dedup_window", "channels"}

# notify.channels 已知渠道(v1 仅平台原生单渠道; 多渠道按 traffic_source 同模式演进)
NOTIFY_CHANNELS = {"platform"}

NOTIFY_LEVELS = ("INFO", "WARNING", "ERROR")

KNOWN_HR_KEYS = {
    "add_tag",
    "add_category",
    "overwrite_category",
    "add_tag_for_satisfied",
    "add_category_for_satisfied",
    "overwrite_category_for_satisfied",
}

KNOWN_TRACKER_KEYS = {
    "domains",
    "tags",
    "remove_tags",
    "groups",
    "upload_speed_limit",
    "download_speed_limit",
    "hr",
    "rules",
    "remove_similar_tags",
}

KNOWN_TRACKER_HR_KEYS = {
    "required_seeding_time", "required_share_ratio", "extra_seeding_time", "condition", *KNOWN_HR_KEYS
}


def _validate_add_episode_tags(spec, errors: List[str]) -> None:
    """校验 config.add_episode_tags 段(布尔 enabled + 单集/多集模板字符串)"""
    if not isinstance(spec, dict):
        errors.append("config.add_episode_tags: 必须是字典")
        return
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.add_episode_tags.enabled", errors)
    for key in ("add_tag_single", "add_tag_multi"):
        if key in spec and (not isinstance(spec[key], str) or not spec[key].strip()):
            errors.append(f"config.add_episode_tags.{key}: 必须是非空字符串")


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
        n = _try(parse_fsize, spec["max_bytes"], "config.log.max_bytes", errors)
        # 0 在 RotatingFileHandler 语义 = 从不轮转(单文件无限增长直至磁盘写满);
        # 过小(<1MiB)则每条日志都可能触发轮转(IO 放大); 上界防轮转失去意义
        if n is not None and not 1024**2 <= n <= 1024**3:
            errors.append(f"config.log.max_bytes: 须在 1MiB-1GiB 范围内: {spec['max_bytes']}")


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
        # [0, 100] 且拦 nan/inf: 负数→立即满足(误打标)、nan→比较恒 False 永不满足(静默失效)
        _try_number(spec["required_share_ratio"], f"{where}.required_share_ratio(须为数字)", errors, min=0, max=100)
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
        for key in ("tags", "remove_tags", "groups"):
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


def _validate_web(spec, errors: List[str]) -> None:
    """校验 config.web 段(仅本机默认; token 留空 = 随机生成)"""
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.web: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_WEB_KEYS, "config.web", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.web.enabled", errors)
    if "host" in spec:
        if not isinstance(spec["host"], str) or not spec["host"].strip():
            errors.append("config.web.host: 必须是非空字符串")
    if "port" in spec:
        try:
            port = int(spec["port"])
        except (TypeError, ValueError):
            errors.append(f"config.web.port: 必须是整数: {spec['port']}")
        else:
            if not 1 <= port <= 65535:
                errors.append(f"config.web.port: 超出范围 1-65535: {port}")
    if "token" in spec and not isinstance(spec["token"], str):
        errors.append("config.web.token: 必须是字符串")
    if "skip_local_verify" in spec:
        _try(parse_bool, spec["skip_local_verify"], "config.web.skip_local_verify", errors)


def _validate_notify(spec, errors: List[str]) -> None:
    """校验 config.notify 段(主动通知); 未配置(None)合法, 走默认值"""
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.notify: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_NOTIFY_KEYS, "config.notify", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.notify.enabled", errors)
    if "min_level" in spec:
        if str(spec["min_level"]).strip().upper() not in NOTIFY_LEVELS:
            errors.append(f"config.notify.min_level: 须为 {'/'.join(NOTIFY_LEVELS)} 之一: '{spec['min_level']}'")
    if "quiet_hours" in spec:
        v = str(spec["quiet_hours"] or "").strip()
        if v and "-" in v:
            start_s, _, end_s = v.partition("-")
            for part in (start_s, end_s):
                _try(parse_hm, part, f"config.notify.quiet_hours('{v}')", errors)
        elif v:
            errors.append(f"config.notify.quiet_hours: 须为 \"HH:MM-HH:MM\" 格式(支持跨午夜): '{v}'")
    if "max_per_hour" in spec:
        try:
            n = int(spec["max_per_hour"])
        except (TypeError, ValueError):
            errors.append(f"config.notify.max_per_hour: 必须为整数: {spec['max_per_hour']}")
        else:
            if n <= 0:
                errors.append("config.notify.max_per_hour: 必须为正整数")
            elif n > 100:
                errors.append("config.notify.max_per_hour: 须 <= 100")  # 防风暴参数自身无上界则失去意义
    if "dedup_window" in spec:
        # 0 = 不去重(合法); 上限 24H: 过大 → 相同前缀的真实 ERROR 被长期压制(掩盖故障)
        _try_time(spec["dedup_window"], "config.notify.dedup_window", errors, max_s=86400)
    if "channels" in spec:
        ch = spec["channels"]
        if not isinstance(ch, list) or not ch:
            errors.append("config.notify.channels: 必须是非空列表")
        else:
            for i, item in enumerate(ch):
                if not isinstance(item, dict) or len(item) != 1:
                    errors.append(f"config.notify.channels[{i}]: 必须是单键映射(如 - platform: {{}})")
                    continue
                name = next(iter(item))
                if name not in NOTIFY_CHANNELS:
                    errors.append(f"config.notify.channels[{i}]: 未知渠道 '{name}', 可用: {sorted(NOTIFY_CHANNELS)}")

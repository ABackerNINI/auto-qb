"""fail-fast 全量配置校验: 全部正确性检查集中于此, 聚合错误一次性报告(不抛异常, 由 load_config 统一抛出)"""
import logging
import re
from typing import List

from qbittorrentapi import TorrentState

from .. import curves
from ..utils import MatchPattern, parse_bool, parse_fsize, parse_hm, parse_hr_condition, parse_speed, parse_time

# 规则 spec 已知键(trigger 仅支持 interval, 其余触发时机规划中)
RULE_KNOWN_KEYS = {
    "enabled", "trigger", "interval", "execute_once", "cooldown", "conditions", "actions", "stop_following_rules_if"
}
EXECUTE_ONCE_VALUES = ("never", "once", "daily", "hourly")
STOP_IF_VALUES = ("conditions-met", "conditions-not-met", "action-failed", "all-actions-succeed", "always", "never")
# 触发时机: interval 周期轮询 / on_torrent_added / on_torrent_deleted / on_torrent_state_enum_changed 事件触发
TRIGGER_VALUES = ("interval", "on_torrent_added", "on_torrent_deleted", "on_torrent_state_enum_changed")
# on_torrent_deleted 允许的动作白名单: 删除后种子无活现场, 现存动作几乎都对已删种子无意义,
# 仅允许"不依赖活现场"的只读/记录类动作(如 print_torrent_details)。未来通知/记录类动作加入此集合。
# 空集合 = 禁止任何动作(on_torrent_deleted 仅作语义占位)。其它触发时机不设白名单(全部动作可用)。
DELETED_TRIGGER_ALLOWED_ACTIONS = {"print_torrent_details"}

# checking 动作 spec 已知键与取值域(skip_checking_tag 为全局配置, 不按规则覆盖, 故列为未知键)
CHECKING_ACTION_KNOWN_KEYS = {"basic_check", "custom_basic_check_program_path", "with_reference", "without_reference"}
CHECKING_VALID_BASIC = ("filelist", "piecehashes", "custom")
CHECKING_VALID_MODES = ("skip-checking", "full-checking")

# config 顶层已知键
KNOWN_CONFIG_KEYS = {
    "qbittorrent",
    "main_tick",
    "max_tasks_per_tick",
    "interval",
    "data_dir",
    "state_file",
    "log",
    "remove_similar_tags",
    "add_episode_tags",
    "hr",
    "skip_checking_tag",
    "delete_tags",
    "delete_tags_if_has_no_torrents",
    "grouping",
    "notify",
    "web",
    "trackers",
    "global_speed_limit_curve",
}
KNOWN_LOG_KEYS = {"level", "file", "max_bytes", "format"}
KNOWN_QBITTORRENT_KEYS = {"host", "port", "username", "password"}
KNOWN_GROUPING_KEYS = {"enabled", "check_missing_files", "missing_tag"}
KNOWN_WEB_KEYS = {"enabled", "host", "port", "token"}
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
    "upload_speed_limit",
    "download_speed_limit",
    "hr",
    "rules",
    "remove_similar_tags",
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
    """regex: 前缀模式须可编译(经 MatchPattern 解析出主体与 ignore_case 标志后编译, 与运行时一致;
    否则运行时会静默跳过匹配, 错误被掩盖)"""
    for i, pat in enumerate(patterns):
        if isinstance(pat, str) and pat.startswith("regex:"):
            try:
                MatchPattern.parse(pat).compile()
            except re.error as e:
                errors.append(f"{where}[{i}]: 非法正则: {e}")


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

    已注册插件的 spec 深度校验也在此进行(_PLUGIN_SPEC_VALIDATORS, 如 state 的 is_* 属性、
    checking 的段结构)—— 配置正确性检查全部集中在 config 校验阶段 fail-fast,
    插件类(conditions/actions)假定配置正确, 不再自查; 尚未迁移的解析类错误
    (如 size 比较表达式的 int 解析)仍由 Rule 构造时的自然异常暴露(同为启动期 fail-fast)。
    """
    from ..rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

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
            if "trigger" in spec and spec["trigger"] not in TRIGGER_VALUES:
                errors.append(f"{where}: trigger 取值非法: '{spec['trigger']}', 可选: {'/'.join(TRIGGER_VALUES)}")
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
            # 触发时机 × 动作兼容白名单: 某触发器下不适用动作在 config 阶段直接拒绝(见 04 规则系统)
            _validate_trigger_action_compat(spec, where, errors)


def _validate_state_condition_spec(value, where: str, errors: List[str]) -> None:
    """state 条件 spec 深度校验: 每组仅接受 TorrentState 的 is_* 类别属性

    裸枚举成员名(如 UPLOADING)在枚举实例上恒真值, 必须拒绝; 非法名若放行会在
    运行时每轮抛 AttributeError 被规则引擎吞成 WARNING(掩盖配置笔误)。
    """
    values = value if isinstance(value, list) else [value]
    for v in values:
        for s in str(v).split("&"):
            if not s.startswith("is_") or not hasattr(TorrentState, s):
                errors.append(
                    f"{where}: 非法状态属性 '{s}', "
                    "可选: is_downloading/is_uploading/is_complete/is_checking/is_stopped/is_paused/is_errored"
                )


def _validate_checking_action_spec(value, where: str, errors: List[str]) -> None:
    """checking 动作 spec 深度校验: dict/已知键/basic_check/段结构/mode"""
    if not isinstance(value, dict):
        errors.append(f"{where}: checking 动作只接受 dict 配置, 旧字符串形式已移除, 请参考示例改写")
        return
    _check_unknown_keys(value, CHECKING_ACTION_KNOWN_KEYS, where, errors)
    if "basic_check" not in value:
        errors.append(f"{where}: 必须配置 basic_check")
    elif value["basic_check"] not in CHECKING_VALID_BASIC:
        errors.append(f"{where}: basic_check 取值非法: '{value['basic_check']}', 可选: {list(CHECKING_VALID_BASIC)}")
    if value.get("basic_check") == "custom" and not str(value.get("custom_basic_check_program_path") or "").strip():
        errors.append(f"{where}: basic_check=custom 时必须配置 custom_basic_check_program_path")
    for seg in ("with_reference", "without_reference"):
        if seg not in value:
            continue
        if not isinstance(value[seg], dict):
            errors.append(f"{where}.{seg}: 必须是字典")
        elif str(value[seg].get("mode", "")) not in CHECKING_VALID_MODES:
            errors.append(f"{where}.{seg}.mode 取值非法: '{value[seg].get('mode', '')}', 可选: {list(CHECKING_VALID_MODES)}")


def _validate_tags_condition_spec(value, where: str, errors: List[str]) -> None:
    """tags 条件 spec 正则校验: 列表(组间或)的每组成员内逗号分隔模式, regex: 主体须可编译
    (非字符串等类型错误由 Rule 构造时的自然异常暴露, 此处仅查正则, 与 _check_regex_patterns 同风格)"""
    groups = value if isinstance(value, list) else [value]
    for g in groups:
        if isinstance(g, str):
            _check_regex_patterns([p.strip() for p in g.split(",")], where, errors)


def _validate_pattern_list_spec(value, where: str, errors: List[str]) -> None:
    """category/trackers 条件与 remove_tags 动作 spec 正则校验: 列表或单值, 每项 regex: 主体须可编译"""
    items = value if isinstance(value, list) else [value]
    _check_regex_patterns(items, where, errors)


# 插件 spec 深度校验分发(键为插件名): 配置正确性检查全部集中在 config 校验阶段,
# 插件类(conditions/actions)假定配置正确, 不再自查
_PLUGIN_SPEC_VALIDATORS = {
    "state": _validate_state_condition_spec,
    "checking": _validate_checking_action_spec,
    "tags": _validate_tags_condition_spec,
    "category": _validate_pattern_list_spec,
    "trackers": _validate_pattern_list_spec,
    "remove_tags": _validate_pattern_list_spec,
}


def _validate_plugin_entry(entry, where: str, known: dict, kind: str, errors: List[str]) -> None:
    """conditions/actions 列表项校验: 单键字典 + 名称已注册(多键/空值会被静默丢弃, 必须报错);
    已注册名称再做 spec 深度校验(_PLUGIN_SPEC_VALIDATORS)"""
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
    else:
        deep = _PLUGIN_SPEC_VALIDATORS.get(name)
        if deep:
            deep(entry[name], f"{where}.{name}", errors)


def _validate_trigger_action_compat(spec: dict, where: str, errors: List[str]) -> None:
    """触发时机 × 动作兼容白名单(决策见 04 规则系统触发时机表)

    on_torrent_deleted: 种子删除后 store 已无该种子, ctx.torrent 为删除前快照副本,
    无"活种子"现场 —— 需操作活种子的动作(启停/校验/限速/移动/汇报都无意义,
    仅"只读打印/未来通知类"适用)。非白名单动作在 config 阶段直接拒绝。
    其它 trigger(interval/on_torrent_added/on_torrent_state_enum_changed): 现场完整, 不设限。
    """
    trigger = str(spec.get("trigger", "interval"))
    if trigger != "on_torrent_deleted":
        return
    allowed = DELETED_TRIGGER_ALLOWED_ACTIONS
    acts = spec.get("actions") or []
    for i, entry in enumerate(acts):
        if not isinstance(entry, dict) or len(entry) != 1:
            continue  # 结构错误由 _validate_plugin_entry 报, 这里不重复
        name = next(iter(entry))
        if name == "ignore_next_action_error":
            continue  # 伪动作不参与白名单
        if name not in allowed:
            errors.append(
                f"{where}.actions[{i}]: 动作 '{name}' 不适用于 trigger 'on_torrent_deleted'"
                f"(删除后种子无活现场), 允许: {sorted(allowed)}"
            )


def _validate_global_speed_limit_curve(spec, errors: List[str]) -> None:
    """校验 config.global_speed_limit_curve 段(结构/键/数值), 错误聚合到 errors(带完整路径)

    配置样式见 loaders.load_global_speed_limit_curve; 解析假定已通过本校验。
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
    if "dedup_window" in spec:
        _try_time(spec["dedup_window"], "config.notify.dedup_window", errors)
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
        _validate_add_episode_tags(cfg["add_episode_tags"], errors)

    _validate_log(cfg.get("log"), errors)
    _validate_qbittorrent(cfg.get("qbittorrent"), errors)
    _validate_global_hr(cfg.get("hr"), errors)
    _validate_grouping(cfg.get("grouping"), errors)
    _validate_notify(cfg.get("notify"), errors)
    _validate_web(cfg.get("web"), errors)
    _validate_tag_lists(cfg, errors)
    _validate_trackers(cfg.get("trackers"), rules_config, errors)
    _validate_rules(rules_config, errors)

    gslc = cfg.get("global_speed_limit_curve")
    if gslc is not None:
        _validate_global_speed_limit_curve(gslc, errors)
    return errors

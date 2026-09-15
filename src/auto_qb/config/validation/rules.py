"""规则集 spec 校验: 键/取值域/conditions-actions 结构 + 插件 spec 深度校验分发"""
from typing import List

from qbittorrentapi import TorrentState

from ...utils import parse_bool
from .core import _check_regex_patterns, _check_unknown_keys, _try, _try_time

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


def _validate_rules(rules_config: dict, errors: List[str]) -> None:
    """规则集 spec 校验: 键/取值域/conditions-actions 结构; 条件与动作名称经 registry 延迟导入校验

    已注册插件的 spec 深度校验也在此进行(_PLUGIN_SPEC_VALIDATORS, 如 state 的 is_* 属性、
    checking 的段结构)—— 配置正确性检查全部集中在 config 校验阶段 fail-fast,
    插件类(conditions/actions)假定配置正确, 不再自查; 尚未迁移的解析类错误
    (如 size 比较表达式的 int 解析)仍由 Rule 构造时的自然异常暴露(同为启动期 fail-fast)。
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

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
    "tracker_group": _validate_pattern_list_spec,
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

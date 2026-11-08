"""规则集 spec 校验: 键/取值域/conditions-actions 结构 + 插件 spec 深度校验分发"""
from dataclasses import dataclass
from typing import Any, List

from qbittorrentapi import TorrentState

from ...infra.utils import parse_bool
from ..compat import (
    ACTION_ENTRY_KEYS,
    CHOOSE_BRANCH_KEYS,
    CHOOSE_KNOWN_KEYS,
    CONDITION_COMBO_KEYS,
    CONDITION_TREE_MAX_DEPTH,
    normalize_action_entry,
    normalize_conditions,
)
from ..schema.fields import (
    # 枚举族单点(issue 26-10-11-0031): 取值域/白名单只在 schema/fields 声明, 本包引用派生
    # (W5 起 watch_fields/兼容表消费面改走 registry 派生访问器, schema 侧同名常量冻结为
    #  双跑对账基准; DELETED_ALLOWED_ACTIONS/FIELD_WATCH_ALLOWED 仍由包 __init__ 重导出)
    CHECKING_BASIC,
    CHECKING_MODES,
    EVALUATION_MODES,
    EXECUTE_ONCE,
    ON_ERROR_POLICIES,
    STATE_ATTRS,
    STOP_IF,
    TRIGGERS,
)
from .core import _check_regex_patterns, _check_unknown_keys, _is_bare_zero, _try, _try_time

# 规则 spec 已知键(watch_fields 仅 on_torrent_field_changed 触发时机下允许;
# evaluation 为 W4/D4 占位枚举位: 校验放行 all|first_match, 引擎按 all 处理)
RULE_KNOWN_KEYS = {
    "enabled",
    "trigger",
    "interval",
    "execute_once",
    "cooldown",
    "evaluation",
    "conditions",
    "actions",
    "stop_following_rules_if",
    "watch_fields",
}

# checking 动作 spec 已知键与取值域(skip_checking_tag 为全局配置, 不按规则覆盖, 故列为未知键)
CHECKING_ACTION_KNOWN_KEYS = {
    "basic_check",
    "custom_basic_check_program_path",
    "custom_basic_check_timeout",
    "recheck_fail_cooldown",
    "with_reference",
    "without_reference",
}

# checking 动作子段(with_reference / without_reference)已知键(与 schema CHECKING_SECTION_FIELDS 同键面;
# 26-10-06-0028 D-02: 子段嵌套两层拼错概率不低, 未知键必须 fail-fast 而非运行时静默缺省)
CHECKING_SECTION_KNOWN_KEYS = {"enabled", "mode", "auto_start"}

# on_error 子对象已知键(plan 26-11-01-0106 W2/G5): 取值域 ON_ERROR_POLICIES(schema/fields 单点)
ON_ERROR_KNOWN_KEYS = {"policy", "retries", "backoff"}


def _check_rule_refs(refs: List[str], rules_config: dict, where: str, errors: List[str]) -> None:
    """tracker.rules 引用校验: 必须 @ 开头, 且引用的规则集/规则存在(否则运行时静默不执行);
    同一引用重复出现判重报错(运行时按规则名去重使重复条目完全惰性, 只可能是误操作, 计划 26-10-02-1621)"""
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

    # 第二轮判重: 归一形 = str(ref).strip()(与上面逐条校验同口径, 尾随空白判重; 不折叠大小写, 规则名大小写敏感);
    # 仅 @ 开头且 @ 后非空的合法形参与判重 —— 畸形引用已在第一轮报格式错, 不叠加查重错;
    # 序号 0 基, 与 path_map 判重先例(sections.py)口径一致
    seen: dict = {}  # 归一形 -> 首现序号(判重)
    for i, ref in enumerate(refs):
        r = str(ref).strip()
        if not r.startswith("@") or not r[1:].strip():
            continue
        if r in seen:
            errors.append(f"{where}[{i}]: 规则引用重复(与第 {seen[r]} 条相同): {r}")
        else:
            seen[r] = i


@dataclass(frozen=True)
class _ExprGate:
    """表达式取值的数据源门控上下文(配置期): 数据源没配 -> 相关名字禁用"""

    traffic_configured: bool = False


def _expr_gate(data: Any) -> _ExprGate:
    """从原始配置判断数据源是否可用(顶层 traffic_source 段当前生效来源)

    WARN: 本函数跑在**traffic_source 段校验之前**(validate_config 里规则段在前), 所以必须容忍
    结构非法的 traffic_source —— 结构错误由 _validate_traffic_source 负责报错, 这里只尽力判
    "配没配"; 判不出来就按"没配"处理(最保守: 相关名字禁用)。

    按 provider 分支(R2/D20):
    - traffic_monitor -> 看 traffic_monitor.dat_path 非空(纯配置事实, 与改动前一致);
    - global_traffic_monitor -> **恒 True**: dat 路径是工具运行期报出的事实(发现指针), 配置期
      无从得知; 这里判 False 会让所有用 traffic.* 的规则在启动校验期就报"名字不可用", 把
      "工具暂时没跑"误判成"配置写错了"。缺路径在运行期由 ExprError 显式报出(见 rules/expr/env.py)。

    enabled=false 总开关(26-10-17-1737 S1/D1) -> **恒 True**: 关来源是合法的使用态, 若此时把
    traffic.* 判成"未配数据源", 用户改不动规则(保存必败)也关不掉来源自救 —— 取数停摆由运行期
    闸门承载, 校验期只判"名字存不存在"。
    """
    ts = data.get("traffic_source") if isinstance(data, dict) else None
    if not isinstance(ts, dict):
        return _ExprGate()
    # 关闭判定经 parse_bool(R4#10, 与 _validate_traffic_source 同口径): no/off/0 等价写法
    # 同算关闭 -> 恒 True; 解析失败按未关闭处理(保守: 名字仍禁用), 结构错由段校验负责报
    try:
        if parse_bool(ts.get("enabled")) is False:
            return _ExprGate(traffic_configured=True)
    except ValueError:
        pass
    provider = str(ts.get("provider") or "traffic_monitor").strip()
    if provider == "global_traffic_monitor":
        return _ExprGate(traffic_configured=True)
    tm = ts.get("traffic_monitor")
    dat_path = str(tm.get("dat_path", "") or "").strip() if isinstance(tm, dict) else ""
    return _ExprGate(traffic_configured=bool(dat_path))


def _validate_rules(rules_config: dict, errors: List[str], data: Any = None) -> None:
    """规则集 spec 校验: 键/取值域/conditions-actions 结构; 条件与动作名称经 registry 延迟导入校验

    已注册插件的 spec 深度校验也在此进行(分发表 _plugin_spec_validators 从 registry 条目
    validator 声明派生, W5/G9; 如 state 的 is_* 属性、
    checking 的段结构)—— 配置正确性检查全部集中在 config 校验阶段 fail-fast,
    插件类(conditions/actions)假定配置正确, 不再自查; 尚未迁移的解析类错误
    (如 size 比较表达式的 int 解析)仍由 Rule 构造时的自然异常暴露(同为启动期 fail-fast)。
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环
    gate = _expr_gate(data)

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
            if "interval" in spec:
                # 0 会被 TaskQueue._norm_interval 归一化成 1s → 规则决策链每秒全量跑(qB API + CPU)
                _try_time(spec["interval"], f"{where}.interval", errors, positive=True)
            if "cooldown" in spec:
                # 0 = 不冷却(合法, schema help 口径; 裸 0 特判放行, 同 R4#15 dedup_window 的调用点特判)
                if not _is_bare_zero(spec["cooldown"]):
                    _try_time(spec["cooldown"], f"{where}.cooldown", errors)
            if "execute_once" in spec and spec["execute_once"] not in EXECUTE_ONCE:
                errors.append(f"{where}: execute_once 取值非法: '{spec['execute_once']}', 可选: {'/'.join(EXECUTE_ONCE)}")
            if "stop_following_rules_if" in spec and spec["stop_following_rules_if"] not in STOP_IF:
                errors.append(
                    f"{where}: stop_following_rules_if 取值非法: '{spec['stop_following_rules_if']}', "
                    f"可选: {'/'.join(STOP_IF)}"
                )
            if "trigger" in spec and spec["trigger"] not in TRIGGERS:
                errors.append(f"{where}: trigger 取值非法: '{spec['trigger']}', 可选: {'/'.join(TRIGGERS)}")
            if "evaluation" in spec and spec["evaluation"] not in EVALUATION_MODES:
                errors.append(f"{where}: evaluation 取值非法: '{spec['evaluation']}', 可选: {'/'.join(EVALUATION_MODES)}")
            if "watch_fields" in spec:
                _validate_watch_fields(spec, where, errors)
            conds = spec.get("conditions")
            if conds is not None:
                # W3-A: normalize 已把旧扁平列表包成隐式 all 树, 校验器只认组合树
                # (防漂移铁律: 没有「读 legacy 扁平列表」的第二语义分支)
                _validate_condition_tree(conds, f"{where}.conditions", errors, gate)
            acts = spec.get("actions")
            if acts is not None:
                if not isinstance(acts, list):
                    errors.append(f"{where}.actions: 必须是列表")
                else:
                    for i, a in enumerate(acts):
                        # 动作项只认规范化后形态 {type, params}(normalize 在校验前已转换;
                        # 旧扁平单键形仅在校验器入口经单点漏斗 translate, 见 _validate_action_entry);
                        # choose 编排块(W3-B)同径分流, gate 传给 when 条件树的 expr 门控
                        _validate_action_entry(a, f"{where}.actions[{i}]", i + 1, registry.ACTIONS, errors, gate=gate)
            # 触发时机 × 动作兼容白名单: 某触发器下不适用动作在 config 阶段直接拒绝(见 04 规则系统)
            _validate_trigger_action_compat(spec, where, errors)


def _watch_fields_allowed() -> tuple:
    """on_torrent_field_changed 可监听字段取值域(W5/G10 派生): registry 条件条目 watchable_field 声明

    取值域与条件名同源 —— 可事件化的种子字段由其对应条件条目声明(v1 = tags/category);
    手写基准 FIELD_WATCH_ALLOWED(schema/fields)冻结为双跑对账锚点(test_registry_derived
    钉住派生 == 基准), 消费面已切派生。
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

    return registry.watch_fields_allowed()


def _validate_watch_fields(spec: dict, where: str, errors: List[str]) -> None:
    """watch_fields 校验(fail-fast 清单, 计划 26-09-27-1438 §06):
    仅 trigger: on_torrent_field_changed 下允许出现(其它 trigger 下出现即报错);
    必须是非空列表且逐项落在取值域(W5/G10: registry 条目 watchable_field 声明派生)。"""
    allowed = _watch_fields_allowed()
    if str(spec.get("trigger", "interval")) != "on_torrent_field_changed":
        errors.append(
            f"{where}: watch_fields 仅在 trigger: on_torrent_field_changed 下允许配置"
            f"(当前 trigger: '{spec.get('trigger', 'interval')}')"
        )
    wf = spec["watch_fields"]
    if (
        not isinstance(wf, list) or not wf or
        not all(isinstance(x, str) and x.strip() and x.strip() in allowed for x in wf)
    ):
        errors.append(f"{where}: watch_fields 必须是非空列表, 取值限: {'/'.join(allowed)}")


def _validate_state_condition_spec(value: Any, where: str, errors: List[str], gate: _ExprGate | None = None) -> None:
    """state 条件 spec 深度校验: 每组仅接受 TorrentState 的 is_* 类别属性

    gate: expr 专属的数据源门控上下文, 本校验器不消费(派生分发统一签名, W5)。
    裸枚举成员名(如 UPLOADING)在枚举实例上恒真值, 必须拒绝; 非法名若放行会在
    运行时每轮抛 AttributeError 被规则引擎吞成 WARNING(掩盖配置笔误)。
    """
    values = value if isinstance(value, list) else [value]
    for v in values:
        for s in str(v).split("&"):
            if not s.startswith("is_") or not hasattr(TorrentState, s):
                errors.append(f"{where}: 非法状态属性 '{s}', 可选: {'/'.join(STATE_ATTRS)}")


def _validate_checking_action_spec(value: Any, where: str, errors: List[str], gate: _ExprGate | None = None) -> None:
    """checking 动作 spec 深度校验: dict/已知键/basic_check/段结构/mode

    gate: expr 专属的数据源门控上下文, 本校验器不消费(派生分发统一签名, W5)。
    """
    if not isinstance(value, dict):
        errors.append(f"{where}: checking 动作只接受 dict 配置, 旧字符串形式已移除, 请参考示例改写")
        return
    _check_unknown_keys(value, CHECKING_ACTION_KNOWN_KEYS, where, errors)
    if "basic_check" not in value:
        errors.append(f"{where}: 必须配置 basic_check")
    elif value["basic_check"] not in CHECKING_BASIC:
        errors.append(f"{where}: basic_check 取值非法: '{value['basic_check']}', 可选: {list(CHECKING_BASIC)}")
    if value.get("basic_check") == "custom" and not str(value.get("custom_basic_check_program_path") or "").strip():
        errors.append(f"{where}: basic_check=custom 时必须配置 custom_basic_check_program_path")
    # 超时保险丝的档位(运行时缺省 600s): 时间串 + 正值; 0/负数/坏格式在此 fail-fast,
    # 不给运行时留「timeout=0 立即超时」或裸数字误写秒数的暗面(relocate.move_stall_timeout 同形制)
    if "custom_basic_check_timeout" in value:
        _try_time(value["custom_basic_check_timeout"], f"{where}.custom_basic_check_timeout", errors, positive=True)
    # 校验失败冷却窗口(运行时缺省 1h, 26-11-08-1717): 时间串 + 正值; 0/负数/坏格式在此
    # fail-fast, 不给运行时留「0=关闭冷却」暗面 —— 窗口只在真实校验失败后生效, 关闭它等于
    # 放回「每轮重复校验」的本 issue 形态(relocate.move_stall_timeout 同形制)
    if "recheck_fail_cooldown" in value:
        _try_time(value["recheck_fail_cooldown"], f"{where}.recheck_fail_cooldown", errors, positive=True)
    for seg in ("with_reference", "without_reference"):
        if seg not in value:
            continue
        sub = value[seg]
        if not isinstance(sub, dict):
            errors.append(f"{where}.{seg}: 必须是字典")
            continue
        # 子段键面 fail-fast(26-10-06-0028 D-02): enabled/auto_start 拼错原先校验零报错,
        # 运行时 _parse_section 全 .get 按缺省静默生效(enabled 拼错 = 分支静默不启用)
        _check_unknown_keys(sub, CHECKING_SECTION_KNOWN_KEYS, f"{where}.{seg}", errors)
        if "enabled" in sub:
            _try(parse_bool, sub["enabled"], f"{where}.{seg}.enabled", errors)
        # mode 仅在显式配置时校验(R4#12, 与上面 enabled 同款存在守卫): 未配置走 schema 默认
        # skip-checking, 不该报「取值非法: ''」把 schema 默认值变成不可达
        if "mode" in sub and str(sub["mode"]) not in CHECKING_MODES:
            errors.append(f"{where}.{seg}.mode 取值非法: '{sub['mode']}', 可选: {list(CHECKING_MODES)}")


def _validate_tags_condition_spec(value: Any, where: str, errors: List[str], gate: _ExprGate | None = None) -> None:
    """tags 条件 spec 正则校验: 列表(组间或)的每组成员内逗号分隔模式, regex: 主体须可编译
    (非字符串等类型错误由 Rule 构造时的自然异常暴露, 此处仅查正则, 与 _check_regex_patterns 同风格;
    gate = expr 专属的门控上下文, 本校验器不消费, 派生分发统一签名 W5)"""
    groups = value if isinstance(value, list) else [value]
    for g in groups:
        if isinstance(g, str):
            _check_regex_patterns([p.strip() for p in g.split(",")], where, errors)


def _validate_expr_condition_spec(value: Any, where: str, errors: List[str], gate: _ExprGate | None = None) -> None:
    """expr 条件 spec 深度校验: 非空字符串 + **配置期**完成解析与语义校验

    - 名字拼错 / 函数写错 / 类型不匹配 / 结果不是布尔, 全部在 load_config 阶段报出来 ——
      否则运行期只会静默不匹配(日志里没有任何痕迹, 极难定位)
    - **数据源门控**: 用到需要数据源的名字(如 sys.upload_today 需要 traffic_source)而配置里
      没配该数据源 -> 该名字禁用, 配置期即报错(见 env.GATED_NAMES)
    rules 包反向依赖 config, 故延迟导入(与 registry 同处理)。
    """
    from ...rules.expr import compile_expr, gated_names_in, validate
    from ...rules.expr.errors import ExprError

    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: expr 条件需要一个非空字符串表达式")
        return
    try:
        root = compile_expr(value).root
        validate(root)
    except ExprError as e:
        errors.append(f"{where}: 表达式错误: {e}")
        return
    if gate is not None and not gate.traffic_configured:
        gated = gated_names_in(root)
        if gated:
            errors.append(
                f"{where}: 取值 {'、'.join(gated)} 无数据源 —— 需在 config.traffic_source 配置当前生效来源"
                "(traffic_monitor.dat_path; 选 global_traffic_monitor 时路径由工具运行期提供, 不再配置), "
                "未配置时该值不可用"
            )


def _validate_pattern_list_spec(value: Any, where: str, errors: List[str], gate: _ExprGate | None = None) -> None:
    """category/trackers 条件与 remove_tags 动作 spec 正则校验: 列表或单值, 每项 regex: 主体须可编译

    gate: expr 专属的数据源门控上下文, 本校验器不消费(派生分发统一签名, W5)。
    """
    items = value if isinstance(value, list) else [value]
    _check_regex_patterns(items, where, errors)


# ---------------------------------------------------------------------------
# 插件 spec 深度校验分发(W5/G9 派生收口, plan 26-11-01-0106): 配置正确性检查全部集中在
# config 校验阶段, 插件类(conditions/actions)假定配置正确, 不再自查。
#
# 分发不再手工按插件名维护: 哪个插件有深度校验、用哪个校验器, 由 registry 条目的
# validator 声明派生(_plugin_spec_validators); 校验器**实现**仍单点在本模块
# (_SPEC_VALIDATOR_IMPLS, 校验逻辑集中 config 不下放插件类)。手写表冻结为
# _PLUGIN_SPEC_VALIDATORS_BASELINE 作双跑对账锚点(test_registry_derived 钉住派生 == 基准)。
# ---------------------------------------------------------------------------

# W5 冻结手写基准(双跑对账锚点, 消费面已切派生; 改派生口径须先让双跑 diff 清零)
_PLUGIN_SPEC_VALIDATORS_BASELINE = {
    "state": _validate_state_condition_spec,
    "checking": _validate_checking_action_spec,
    "tags": _validate_tags_condition_spec,
    "category": _validate_pattern_list_spec,
    "trackers": _validate_pattern_list_spec,
    "tracker_group": _validate_pattern_list_spec,
    "remove_tags": _validate_pattern_list_spec,
    # expr 原不走此表(需数据源门控上下文 gate); W5 统一进派生分发, 实现签名带 gate
    "expr": _validate_expr_condition_spec,
}

# 校验器实现单点(键 = registry 条目 validator 声明名): 校验逻辑集中在 config 校验阶段
_SPEC_VALIDATOR_IMPLS = {
    "state": _validate_state_condition_spec,
    "checking": _validate_checking_action_spec,
    "tags": _validate_tags_condition_spec,
    "pattern_list": _validate_pattern_list_spec,
    "expr": _validate_expr_condition_spec,
}


def _plugin_spec_validators() -> dict:
    """插件 spec 深度校验分发表(W5/G9 派生): 插件名 -> 校验器, 从 registry 条目 validator 声明派生

    条目 validator 声明了实现表里不存在的名字 = registry 与本模块脱节 —— KeyError 显式炸出
    (fail-fast, 守卫测试在导入期即对账, 不静默缺省)。
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

    return {e.name: _SPEC_VALIDATOR_IMPLS[e.validator] for e in registry.iter_entries() if e.validator}


def _validate_condition_tree(
    node: Any, where: str, errors: List[str], gate: _ExprGate | None = None, depth: int = 1, top: bool = True
) -> None:
    """conditions 组合树节点校验(W3-A, plan 26-11-01-0106 §3.2/G4): 只认规范化树形

    节点 = 单键 dict: 组合键 all/any(值为节点列表) / not(值为单个节点) / 条件名(叶子, 须已注册)。
    未知组合键(如 all 拼成 al)与未知条件名 fail-fast; 多键/空/非 dict 节点报结构错;
    嵌套深度超 CONDITION_TREE_MAX_DEPTH(compat 单点)拒绝 —— 防递归爆炸, 不限制真实表达力。

    R1-1 错误定位回映射: 顶层 all 的孩子序号 = 用户写的扁平列表序号(normalize 保序 1:1 包裹),
    报错坐标用「conditions[i]」扁平形; 更深的子树只可能来自用户手写的树形(或 webui 写出的
    规范形态), 坐标按树形如实报出。
    """
    if depth > CONDITION_TREE_MAX_DEPTH:
        errors.append(f"{where}: 组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层")
        return
    if not isinstance(node, dict):
        errors.append(f"{where}: 必须是字典(组合键 {'/'.join(CONDITION_COMBO_KEYS)} 或单键条件)")
        return
    if len(node) == 0:
        errors.append(f"{where}: 值不能为空(留空请删除该项)")
        return
    if len(node) > 1:
        errors.append(f"{where}: 必须是单键字典(组合键 {'/'.join(CONDITION_COMBO_KEYS)} 或单个条件名): {sorted(node)}")
        return
    key = next(iter(node))
    if key in ("all", "any"):
        children = node[key]
        if not isinstance(children, list):
            errors.append(f"{where}.{key}: 必须是列表")
            return
        for i, child in enumerate(children):
            # top + all: 顶层 all 的孩子 = 旧扁平列表条目(normalize 只对列表包 all, 保序 1:1),
            # 坐标回映射成 conditions[i](R1-1); 顶层 any 是用户手写树形, 按树形坐标如实报
            child_where = f"{where}[{i}]" if (top and key == "all") else f"{where}.{key}[{i}]"
            _validate_condition_tree(child, child_where, errors, gate, depth + 1, top=False)
    elif key == "not":
        _validate_condition_tree(node[key], f"{where}.not", errors, gate, depth + 1, top=False)
    else:
        _validate_condition_leaf(key, node[key], where, errors, gate)


def _validate_condition_leaf(
    name: str, value: Any, where: str, errors: List[str], gate: _ExprGate | None = None
) -> None:
    """条件叶子校验: 名称已注册(未注册 = 未知条件, fail-fast) + spec 深度校验分发

    gate: 表达式取值的数据源门控上下文(仅 expr 条件用, 需要看配置里数据源是否配置)
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

    if name == "ignore_next_action_error":
        # 退役键键面保留识别(W1/D1 升级检测): 误写进条件域仍按布尔校验, 引擎不消费
        _try(parse_bool, value, f"{where}.{name}", errors)
    elif name not in registry.CONDITIONS:
        errors.append(f"{where}: 未知条件 '{name}', 可用: {sorted(registry.CONDITIONS)}")
    else:
        # W5/G9: 深度校验分发从 registry 条目 validator 声明派生(expr 的数据源门控上下文
        # gate 经统一签名透传, 仅 expr 实现消费)
        deep = _plugin_spec_validators().get(name)
        if deep:
            deep(value, f"{where}.{name}", errors, gate=gate)


def _validate_action_entry(
    entry: Any,
    where: str,
    ordinal: int,
    known: dict,
    errors: List[str],
    gate: _ExprGate | None = None,
    allow_choose: bool = True
) -> None:
    """actions 列表项校验: 只认规范化后形态 {type, params, on_error}(plan 26-11-01-0106 §3.2/W2-A/W2-B)

    normalize_legacy_rules 已在载入链把旧扁平单键形/混合形翻译成规范形并注入缺省 on_error;
    直达校验器的输入(测试/程序内构造)里的扁平单键形经同一单点漏斗(config.compat.
    normalize_action_entry)翻译后按同一套逻辑校验 —— 这里没有按 legacy 键分支的第二语义,
    只有坐标翻译。

    R1-1 错误定位回映射: 报错话术用用户写的扁平坐标 —— 动作名子路径(actions[i].<动作名>)
    与「第 N 个动作」序号话术, 不暴露 params 结构路径。
    伪动作 ignore_next_action_error 键面保留识别(W1/D1 升级检测), params 仍按布尔校验;
    引擎不消费(载入层转未启用时剔除)。
    choose 编排块(W3-B, plan G6/D3)同径分流到 _validate_choose_block; allow_choose=False
    (choose 块内 then/default)时嵌套 choose 直接拒绝(编排块只允许一层, 防递归爆炸)。
    """
    if not isinstance(entry, dict):
        errors.append(f"{where}: 必须是字典")
        return
    if len(entry) == 0:
        errors.append(f"{where}: 值不能为空(留空请删除该项)")
        return
    norm = normalize_action_entry(entry)
    if isinstance(norm, dict) and "choose" in norm:
        if not allow_choose:
            errors.append(f"{where}: choose 内不允许嵌套 choose(编排块只允许一层)")
            return
        _validate_choose_block(norm, where, known, errors, gate)
        return
    if not isinstance(norm, dict) or "type" not in norm:
        errors.append(f"{where}: 第 {ordinal} 个动作必须是单键字典(旧形)或 {{type, params, on_error}}(新形): {sorted(entry)}")
        return
    name = str(norm["type"])
    if name == "ignore_next_action_error":
        _try(parse_bool, norm.get("params"), f"{where}.{name}", errors)
        return
    if name not in known:
        errors.append(f"{where}: 未知动作 '{name}', 可用: {sorted(known)}")
        return
    unknown = set(norm) - set(ACTION_ENTRY_KEYS)
    if unknown:
        errors.append(f"{where}: 未知键 {sorted(unknown)}, 可用键: {sorted(ACTION_ENTRY_KEYS)}")
        return
    if "params" not in norm:
        errors.append(f"{where}: 动作 '{name}' 缺少 params(动作参数)")
        return
    if "on_error" in norm:
        _validate_on_error(norm["on_error"], f"{where}.on_error", errors)
    deep = _plugin_spec_validators().get(name)
    if deep:
        deep(norm["params"], f"{where}.{name}", errors)


def _validate_choose_block(
    entry: dict, where: str, known: dict, errors: List[str], gate: _ExprGate | None = None
) -> None:
    """choose 编排块校验(W3-B, plan 26-11-01-0106 G6/D3): 键面/分支结构/when 条件树/then+default 动作项

    - 键面 {choose, default}(compat.CHOOSE_KNOWN_KEYS 单点), 未知键 fail-fast;
    - choose 必须是非空分支列表; 每个分支 {when, then}(compat.CHOOSE_BRANCH_KEYS 单点):
      when 必填且过 normalize_conditions 单点后按条件组合树校验(与 conditions 同款,
      expr 门控 gate 照传; 深度复用 CONDITION_TREE_MAX_DEPTH, 从 1 起独立计);
      then 必须是动作项列表(逐项 _validate_action_entry, allow_choose=False 拦嵌套);
    - default 可选, 同 then 校验; 无命中且无 default = 空操作(引擎语义), 不强制配 default。

    坐标口径: choose 块内按树形如实报(choose[i].when / choose[i].then[j])—— choose 本就是
    新写法(无 legacy 扁平坐标可回映射), 与手写条件树同口径。
    """
    unknown = set(entry) - set(CHOOSE_KNOWN_KEYS)
    if unknown:
        errors.append(f"{where}: 未知键 {sorted(unknown)}, 可用键: {sorted(CHOOSE_KNOWN_KEYS)}")
        return
    branches = entry.get("choose")
    if not isinstance(branches, list):
        errors.append(f"{where}.choose: 必须是分支列表 [{{when, then}}, ...]")
        return
    if not branches:
        errors.append(f"{where}.choose: 分支列表不能为空(无条件分支请删除整个 choose 块)")
        return
    for bi, br in enumerate(branches):
        bwhere = f"{where}.choose[{bi}]"
        if not isinstance(br, dict):
            errors.append(f"{bwhere}: 必须是字典 {{when, then}}")
            continue
        br_unknown = set(br) - set(CHOOSE_BRANCH_KEYS)
        if br_unknown:
            errors.append(f"{bwhere}: 未知键 {sorted(br_unknown)}, 可用键: {sorted(CHOOSE_BRANCH_KEYS)}")
        if "when" not in br:
            errors.append(f"{bwhere}: 缺少 when(分支条件)")
        else:
            _validate_condition_tree(normalize_conditions(br["when"]), f"{bwhere}.when", errors, gate)
        if "then" not in br:
            errors.append(f"{bwhere}: 缺少 then(命中后执行的动作项列表, 空列表 = 无操作)")
        elif not isinstance(br["then"], list):
            errors.append(f"{bwhere}.then: 必须是列表(动作项)")
        else:
            for j, a in enumerate(br["then"]):
                _validate_action_entry(a, f"{bwhere}.then[{j}]", j + 1, known, errors, gate=gate, allow_choose=False)
    if "default" in entry:
        default = entry["default"]
        if not isinstance(default, list):
            errors.append(f"{where}.default: 必须是列表(动作项)")
        else:
            for j, a in enumerate(default):
                _validate_action_entry(a, f"{where}.default[{j}]", j + 1, known, errors, gate=gate, allow_choose=False)


def _validate_on_error(value: Any, where: str, errors: List[str]) -> None:
    """动作级错误策略 on_error 校验(plan 26-11-01-0106 W2/G5): dict/已知键/三档/retries/backoff 边界

    fail-fast 聚合报错(黄金法则 4): 逐键收集全部错误而非遇错即返, 一次保存看全所有笔误。
    normalize(校验前)已对缺省 on_error 注入缺省值, 这里看到的是补齐后的形态; 缺省 policy=stop
    即现行「失败即止」, retries/backoff 仅 policy=retry 时被引擎消费(照常校验边界, 不因档位豁免)。
    """
    if not isinstance(value, dict):
        errors.append(f"{where}: 必须是字典 {{policy, retries, backoff}}")
        return
    _check_unknown_keys(value, ON_ERROR_KNOWN_KEYS, where, errors)
    if "policy" in value and value["policy"] not in ON_ERROR_POLICIES:
        errors.append(f"{where}: policy 取值非法: '{value['policy']}', 可选: {'/'.join(ON_ERROR_POLICIES)}")
    if "retries" in value:
        try:
            retries = int(value["retries"])
        except (TypeError, ValueError):
            errors.append(f"{where}: retries 必须是整数: {value['retries']}")
        else:
            if retries < 0:
                errors.append(f"{where}: retries 必须 >= 0: {retries}")
    if "backoff" in value:
        try:
            backoff = float(value["backoff"])
        except (TypeError, ValueError):
            errors.append(f"{where}: backoff 必须是数字(秒): {value['backoff']}")
        else:
            if backoff <= 0:
                errors.append(f"{where}: backoff 必须 > 0(秒): {backoff}")


def _deleted_allowed_actions() -> tuple:
    """on_torrent_deleted 允许动作白名单(W5/G11 派生): registry 动作条目 deleted_ok 声明

    兼容声明随动作注册进 registry 条目(G11「兼容声明进条目」); 手写基准
    DELETED_ALLOWED_ACTIONS(schema/fields)冻结为双跑对账锚点(test_registry_derived
    钉住派生 == 基准), 消费面已切派生。
    """
    from ...rules import registry  # 延迟导入: rules 包反向依赖 config, 顶层导入会循环

    return registry.deleted_allowed_actions()


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
    allowed = _deleted_allowed_actions()
    acts = spec.get("actions") or []
    for i, entry in enumerate(acts):
        if not isinstance(entry, dict):
            continue  # 结构错误由 _validate_action_entry 报, 这里不重复
        norm = normalize_action_entry(entry)  # 规范化形态取动作名(单点漏斗)
        if "choose" in norm:
            # choose 编排块(W3-B): 块内 then/default 的动作同样受白名单约束
            # (执行现场与顶层一致: 删除后种子无活现场, 块内动作也无意义)
            brs = norm.get("choose")
            if isinstance(brs, list):
                for bi, br in enumerate(brs):
                    if not isinstance(br, dict):
                        continue
                    thens = br.get("then")
                    if isinstance(thens, list):
                        for j, a in enumerate(thens):
                            _deleted_trigger_check_action(
                                a, allowed, f"{where}.actions[{i}].choose[{bi}].then[{j}]", errors
                            )
            defaults = norm.get("default")
            if isinstance(defaults, list):
                for j, a in enumerate(defaults):
                    _deleted_trigger_check_action(a, allowed, f"{where}.actions[{i}].default[{j}]", errors)
            continue
        name = norm.get("type")
        if not name or name == "ignore_next_action_error":
            continue  # 结构残缺交 _validate_action_entry 报; 伪动作不参与白名单
        if name not in allowed:
            errors.append(
                f"{where}.actions[{i}]: 动作 '{name}' 不适用于 trigger 'on_torrent_deleted'"
                f"(删除后种子无活现场), 允许: {sorted(allowed)}"
            )


def _deleted_trigger_check_action(a: Any, allowed: tuple, where: str, errors: List[str]) -> None:
    """on_torrent_deleted 白名单单项核对(choose 块内动作用, W3-B): 结构残缺交 _validate_action_entry 报"""
    if not isinstance(a, dict):
        return
    name = normalize_action_entry(a).get("type")
    if not name or name == "ignore_next_action_error":
        return
    if name not in allowed:
        errors.append(f"{where}: 动作 '{name}' 不适用于 trigger 'on_torrent_deleted'(删除后种子无活现场), 允许: {sorted(allowed)}")

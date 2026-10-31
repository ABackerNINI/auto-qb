"""规则兼容层: 载入规范化单点 normalize_legacy_rule(plan 26-11-01-0106 §3.2, W2-A/W2-B)

本模块是 **legacy 规则词汇的唯一容身处**(防漂移铁律): 旧扁平语法只允许在这里被翻译成
引擎/校验器唯一可见的规范化形态, 引擎(rules)与校验器(config.validation)禁止出现
「读 legacy 键」的第二语义分支 —— 避免 G4 的 hr 双语义分歧在规则引擎尺度重演。

落点钉死: config 解析后、schema 校验之前(load_config 内 _strip_none + 版本迁移之后、
validate_config 之前)—— 归一后的形态才进校验器, 校验器报错看到的已是归一形。

两条 R1 附注(设计约束, 专测钉住):
- R1① 错误定位回映射: 校验器报错话术须把归一形坐标翻回用户写的扁平坐标(如「第 2 个动作」
  而非归一后的结构路径); 本期 normalize 保序转换(列表序号 1:1 保留), 动作项报错路径继续用
  「actions[i].<动作名>」扁平坐标 + 序号话术, W3-A 组合树落地时映射在此扩展。
- R1② 命名透传: normalize 只动 conditions/actions 结构, 规则名(含复合形「组.规则」)原样
  透传 —— 它是 exec_history 去重键「规则名:hash」的前半(core/state.py:281), 命名一变去重
  窗口全部失效。⚠ 去重键的 hash 输入 = 种子 infohash(ctx.hash), **不含任何 spec 序列化**
  (core/state.py:262/281 唯一写读点)—— on_error 注入只动 actions 条目形状, 不触碰规则名
  与种子 hash 两个键输入, 去重窗口天然零重置(回归断言见 test_rule_compat)。

本期范围(W2-B, plan G5 错误策略一等化):
- 条件: 透传 + 结构锚定 —— 现行 conditions.py 消费形态(扁平单键 dict 列表)原样保留,
  W3-A 在本函数内改为包隐式 all 树(组合树), 届时引擎/校验器无须再动落点。
- 动作: 单键 dict `{name: value}` / webui 动作卡写出的混合形 `{name: value, on_error: {...}}`
  -> `{type: name, params: value, on_error: {...}}`(参数值原样透传, 引擎 create_action 收到的
  value 与旧路径逐位相同); 并对动作项**注入缺省 on_error**(schema.fields.ON_ERROR_DEFAULTS
  单点, 补齐缺省字段)—— 缺省 policy=stop 即现行「失败即止」, 行为零变化。
- 不做: stop_following_rules_if / ignore_next_action_error 的归一映射(D1 禁止, W1 载入层
  已把含键规则转未启用); `conditions: ''` 不建分支(空串经 _strip_none 载入前已整键剔除,
  与现行「无条件 = 直接过」等价, 勿在此为空串再建分支); checking 动作子段内部结构不动
  (with/without_reference、pending/resume、未知键 fail-fast 契约原样保留)。

幂等: normalize(normalize(x)) == normalize(x) —— 已规范形(含完整 on_error)原样返回,
重复载入/热重载零差异; 缺省注入只补缺失键不改已配置值。本函数对非法形状(非 dict/多键/
on_error 非 dict)不报错不丢数据, 原样透传交校验器按扁平坐标报。
"""
from typing import Any

from .schema.fields import ON_ERROR_DEFAULTS

# 动作规范化形态的键面(W2-B 扩 on_error; fail-fast 键面单点, 校验器引用)
ACTION_ENTRY_KEYS = ("type", "params", "on_error")

# 已退役伪动作名(D1): 只做容器归一, 不注入 on_error(它不被引擎消费, 注入徒增快照噪音)
_RETIRED_PSEUDO_ACTION = "ignore_next_action_error"


def normalize_action_entry(entry: Any) -> Any:
    """单个动作列表项归一(幂等): 旧形/混合形 -> `{type, params, on_error}` 规范形

    - 旧扁平单键 dict `{name: value}` -> `{type: name, params: value}`;
    - webui W2 动作卡写出的混合形 `{name: value, on_error: {...}}` -> 规范形(on_error 透传);
    - 已规范形(含 "type" 键)走缺省注入: 无 on_error 补全缺省对象, on_error 缺子键补缺省值
      (ON_ERROR_DEFAULTS 单点)—— 不深拷贝不存在的部分, 已配置值零改写; 伪动作不注入;
    - on_error 形状非法(非 dict)原样保留, 交校验器 fail-fast(本函数只做形状翻译不吞错误);
    - 非 dict / 空 dict / 无法识别的多键 dict(无 "type" 且非「单动作键 + on_error」)原样返回,
      交校验器按扁平坐标报结构错;
    - 参数值(含 checking 子段 dict)原样透传, 嵌套结构零触碰。
    """
    if isinstance(entry, dict) and "type" not in entry:
        keys = [k for k in entry if k != "on_error"]
        if len(keys) == 1:  # 旧扁平单键形 / 混合形(动作键 + 可选 on_error)
            name = keys[0]
            entry = {"type": name, "params": entry[name], **{k: v for k, v in entry.items() if k != name}}
    if isinstance(entry, dict) and "type" in entry and str(entry.get("type")) != _RETIRED_PSEUDO_ACTION:
        oe = entry.get("on_error")
        if "on_error" not in entry:
            return {**entry, "on_error": dict(ON_ERROR_DEFAULTS)}
        if isinstance(oe, dict):
            missing = {k: v for k, v in ON_ERROR_DEFAULTS.items() if k not in oe}
            if missing:
                return {**entry, "on_error": {**oe, **missing}}
    return entry


def normalize_legacy_rule(spec: Any) -> Any:
    """单条规则 spec 规范化(条件透传锚定 + 动作转规范形); 其余键(含规则名)原样透传

    返回新 dict(浅拷贝, actions 列表新建), 输入不做就地改写 —— 热重载比较与配置原内容
    (D1: 退役键原样保留供改写)都不受载入规范化影响。
    """
    if not isinstance(spec, dict):
        return spec
    out = dict(spec)
    if "actions" in spec:
        acts = spec["actions"]
        if isinstance(acts, list):
            out["actions"] = [normalize_action_entry(a) for a in acts]
    # conditions: 透传 + 结构锚定(见模块 docstring「本期范围」) —— 扁平单键 dict 列表即
    # 现行引擎消费形态, 原样保留; W3-A 的隐式 all 树在本函数这一处替换。
    return out


def normalize_legacy_rules(data: Any) -> None:
    """config 解析树就地规范化全部 `*_rules` 规则集(load_config 载入链单点, 校验之前)

    就地改写 group 内的 spec 映射(group dict 本身保留, 规则名零触碰 = R1②); 非 dict
    段/组原样跳过, 交校验器报结构错。
    """
    if not isinstance(data, dict):
        return
    cfg = data.get("config")
    if not isinstance(cfg, dict):
        return
    for key, group in cfg.items():
        if not key.endswith("_rules") or not isinstance(group, dict):
            continue
        for rule_name, spec in group.items():
            group[rule_name] = normalize_legacy_rule(spec)

"""规则兼容层: 载入规范化单点 normalize_legacy_rule(plan 26-11-01-0106 §3.2, W2-A)

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
  窗口全部失效。

本期范围(W2-A, 行为零变化):
- 条件: 透传 + 结构锚定 —— 现行 conditions.py 消费形态(扁平单键 dict 列表)原样保留,
  W3-A 在本函数内改为包隐式 all 树(组合树), 届时引擎/校验器无须再动落点。
- 动作: 单键 dict `{name: value}` -> `{type: name, params: value}`(参数值原样透传,
  引擎 create_action 收到的 value 与旧路径逐位相同)。
- 不做: stop_following_rules_if / ignore_next_action_error 的归一映射(D1 禁止, W1 载入层
  已把含键规则转未启用); `conditions: ''` 不建分支(空串经 _strip_none 载入前已整键剔除,
  与现行「无条件 = 直接过」等价, 勿在此为空串再建分支); checking 动作子段内部结构不动
  (with/without_reference、pending/resume、未知键 fail-fast 契约原样保留)。

幂等: normalize(normalize(x)) == normalize(x) —— 已规范形原样返回, 重复载入/热重载
零差异; 本函数对非法形状(非 dict/多键)不报错不丢数据, 原样透传交校验器按扁平坐标报。
"""
from typing import Any

# 动作规范化形态的键面(本期固定两键; W2-B on_error 落地时在此扩)
ACTION_ENTRY_KEYS = ("type", "params")


def normalize_action_entry(entry: Any) -> Any:
    """单个动作列表项归一(幂等): 单键 dict `{name: value}` -> `{type: name, params: value}`

    - 已规范形(含 "type" 键的多键 dict)原样返回 —— 不深拷贝, normalize 层不做值改写;
    - 非 dict / 空 dict / 多键 dict(无 "type")原样返回, 交校验器按扁平坐标报结构错
      (fail-fast 聚合报错是校验器职责, 本函数只做形状翻译不吞错误);
    - 参数值(含 checking 子段 dict)原样透传, 嵌套结构零触碰。
    """
    if isinstance(entry, dict) and len(entry) == 1 and "type" not in entry:
        name, value = next(iter(entry.items()))
        return {"type": name, "params": value}
    return entry


def normalize_legacy_rule(spec: Any) -> Any:
    """单条规则 spec 规范化(条件透传锚定 + 动作转 {type, params}); 其余键(含规则名)原样透传

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

"""规则兼容层: 载入规范化单点 normalize_legacy_rule(plan 26-11-01-0106 §3.2, W2-A/W2-B/W3-A/W3-B)

本模块是 **legacy 规则词汇的唯一容身处**(防漂移铁律): 旧扁平语法只允许在这里被翻译成
引擎/校验器唯一可见的规范化形态, 引擎(rules)与校验器(config.validation)禁止出现
「读 legacy 键」的第二语义分支 —— 避免 G4 的 hr 双语义分歧在规则引擎尺度重演。

落点钉死: config 解析后、schema 校验之前(load_config 内 _strip_none + 版本迁移之后、
validate_config 之前)—— 归一后的形态才进校验器, 校验器报错看到的已是归一形。

两条 R1 附注(设计约束, 专测钉住):
- R1-1 错误定位回映射: 校验器报错话术须把归一形坐标翻回用户写的扁平坐标(如「第 2 个动作」
  而非归一后的结构路径); 本函数保序转换(列表序号 1:1 保留), 动作项报错路径继续用
  「actions[i].<动作名>」扁平坐标 + 序号话术, 条件项报错路径继续用「conditions[i].<条件名>」
  (顶层 all 的孩子序号 = 用户写的扁平列表序号, 校验器按此回映射, W3-A 落地)。
- R1-2 命名透传: normalize 只动 conditions/actions 结构, 规则名(含复合形「组.规则」)原样
  透传 —— 它是 exec_history 去重键「规则名:hash」的前半(core/state.py:281), 命名一变去重
  窗口全部失效。WARN: 去重键的 hash 输入 = 种子 infohash(ctx.hash), **不含任何 spec 序列化**
  (core/state.py:262/281 唯一写读点)—— on_error 注入/条件建树只动 actions/conditions 条目
  形状, 不触碰规则名与种子 hash 两个键输入, 去重窗口天然零重置(回归断言见 test_rule_compat)。

条件侧(W3-A, plan G4 组合树):
- 旧扁平单键 dict 列表 -> 包一层隐式 `all:`(语义 = 现行 base.py matches 的 all(...));
  已是 dict 的(树形组合节点/单条件节点)原样透传 —— 引擎与校验器只认树形, 没有「读
  legacy 扁平列表」的第二语义分支, 防漂移铁律由本函数单点承接。
- 「逗号分组」约定(G4)**不展开**: 各条件的行内分组/OR 语义全部留在叶子内(叶子形态以
  conditions.py 现行为准, 规范化快照零差异), normalize 逐条件核对后的映射表见
  _CONDITION_GROUPING_MAP —— 组合树的 any/not 是**新增显式写法**, 不改写既有叶子语义。
- `conditions: ''` 不建分支(空串经 _strip_none 载入前已整键剔除, 与现行「无条件 = 直接过」
  等价, 勿在此为空串再建分支)。

动作侧(W2-B, plan G5 错误策略一等化):
- 单键 dict `{name: value}` / webui 动作卡写出的混合形 `{name: value, on_error: {...}}`
  -> `{type: name, params: value, on_error: {...}}`(参数值原样透传, 引擎 create_action 收到的
  value 与旧路径逐位相同); 并对动作项**注入缺省 on_error**(schema.fields.ON_ERROR_DEFAULTS
  单点, 补齐缺省字段)—— 缺省 policy=stop 即现行「失败即止」, 行为零变化。
- 不做: stop_following_rules_if / ignore_next_action_error 的归一映射(D1 禁止, W1 载入层
  已把含键规则转未启用); checking 动作子段内部结构不动(with/without_reference、
  pending/resume、未知键 fail-fast 契约原样保留)。

编排块侧(W3-B, plan G6/D3 choose 转正):
- 动作列表项可为 `{choose: [{when: <条件树节点>, then: [动作项...]}, ...], default: [动作项...](可选)}`
  —— when 与 conditions 同款组合树节点(叶子经 normalize_conditions 幂等建树, 扁平列表同样
  包隐式 all), then/default 内是普通动作项(逐项过 normalize_action_entry, 同样注入缺省
  on_error); choose 本体无 on_error(错误策略挂在块内每个动作项上, 与顶层同语义)。
- choose 是**编排块不是插件动作**: 归一后保留 `{choose: [...], default?: [...]}` 键面,
  不翻译成 {type, params} 形(引擎与校验器都按 "choose" 键识别); 嵌套约束 = choose 内
  then/default 不再允许 choose(编排块只允许一层, 防递归爆炸; 校验器 fail-fast, 引擎
  构造期同口径兜底)—— 深度防线上 choose 的 when 条件树复用 CONDITION_TREE_MAX_DEPTH
  (从 1 起独立计, 与顶层 conditions 同款)。

幂等: normalize(normalize(x)) == normalize(x) —— 已规范形(含完整 on_error / 已是树形
conditions)原样返回, 重复载入/热重载零差异; 缺省注入只补缺失键不改已配置值。本函数对
非法形状(非 dict/多键/on_error 非 dict)不报错不丢数据, 原样透传交校验器按扁平坐标报。
"""
from typing import Any

from .schema.fields import ON_ERROR_DEFAULTS

# 动作规范化形态的键面(W2-B 扩 on_error; fail-fast 键面单点, 校验器引用)
ACTION_ENTRY_KEYS = ("type", "params", "on_error")

# choose 编排块键面(W3-B, plan G6/D3): 动作列表项含 "choose" 键即编排块, 只认这两个键,
# 其它键 fail-fast(校验器引用; "choose" 键与插件动作名同层判别 —— choose 不在 ACTIONS
# 注册表里, 不可能撞名, 校验器先按 choose 分流)
CHOOSE_KNOWN_KEYS = ("choose", "default")

# choose 分支键面(W3-B): 每个分支 {when: <条件树节点>, then: [动作项...]}, when 必填
CHOOSE_BRANCH_KEYS = ("when", "then")

# 条件组合树键面(W3-A, plan G4): 规范化 conditions 的组合节点只认这三个键,
# 其它键 = 条件名(须在 rules.registry.CONDITIONS 注册, 校验器 fail-fast 未知名)
CONDITION_COMBO_KEYS = ("all", "any", "not")

# 组合树深度上限(W3-A): 每层节点计 1(组合节点与叶子同计) —— 上限只防递归爆炸/配置失控,
# 不限制真实表达力(16 层嵌套组合远超人工可维护规模)。校验器 fail-fast 与引擎构造期
# 双侧引用同一常量(本模块单点)。
CONDITION_TREE_MAX_DEPTH = 16

# 「逗号分组」逐条件映射表(W3-A, plan §3.2/G4; 以 conditions.py 现行为准逐条件核对):
# 行内分隔符/列表语义全部留在叶子内, normalize 零改写 —— 结论: 13 条件叶子一律原样透传。
# | 条件          | 现行为(conditions.py)                                    | 树形映射        |
# |---------------|----------------------------------------------------------|-----------------|
# | path          | 列表 = OR(patterns), 无行内分组                           | 叶子原样        |
# | size          | 单比较串(">=100MiB")                                     | 叶子原样        |
# | tags          | 列表 = 组间 OR; 组内 `,` 分隔 = AND(:56 split(","))       | 叶子原样(不展开)|
# | category      | 列表 = OR                                                 | 叶子原样        |
# | trackers      | 列表 = OR                                                 | 叶子原样        |
# | tracker_group | 列表 = OR                                                 | 叶子原样        |
# | state         | 列表 = 组间 OR; 组内 `&` 连接 = AND(:129 split("&"),
# |               | **非逗号** —— 与 tags 的行内分隔符不同, 勿混写)           | 叶子原样(不展开)|
# | hr            | 单模式串(condition-met/condition-not-met/satisfied);
# |               | 双语义分歧维持现状: conf None / conf.hr None 分支
# |               | (conditions.py:154-164)与表达式侧 tor.hr_satisfied
# |               | (rules/expr/env.py _hr)有意分歧, 勿单边改齐               | 叶子原样        |
# | date_time     | dict{day_of_month/day_of_week/time}, 区间 "a-b"/单值      | 叶子原样        |
# | seedtime      | 单比较串                                                  | 叶子原样        |
# | upload_ratio  | 单比较串                                                  | 叶子原样        |
# | expr          | 单表达式串                                                | 叶子原样        |
# | freespace     | dict{path, amount}                                        | 叶子原样        |
# 机读副本(逐条件枚举, 与上表一一对应): 键 = 条件名, 值 = 行内分组语义要点;
# test_rule_compat 钉「本表覆盖 registry 全部条件 + 结论均为叶子原样」, 防新增条件漏核对
CONDITION_GROUPING_MAP = {
    "path": "列表=OR(无行内分组)",
    "size": "单比较串(无分组)",
    "tags": "组内逗号=AND, 组间列表=OR",
    "category": "列表=OR",
    "trackers": "列表=OR",
    "tracker_group": "列表=OR",
    "state": "组内&=AND(非逗号), 组间列表=OR",
    "hr": "单模式串; 双语义分歧维持现状(conditions.py:154-164 vs expr/env.py _hr)",
    "date_time": "dict 区间串(无分组)",
    "seedtime": "单比较串(无分组)",
    "upload_ratio": "单比较串(无分组)",
    "expr": "单表达式串(无分组)",
    "freespace": "dict{path, amount}(无分组)",
}

# 已退役伪动作名(D1): 只做容器归一, 不注入 on_error(它不被引擎消费, 注入徒增快照噪音)
_RETIRED_PSEUDO_ACTION = "ignore_next_action_error"


def normalize_action_list(items: Any) -> Any:
    """动作项列表逐项归一(choose 的 then/default 用, W3-B): 非 list 原样透传交校验器报"""
    if not isinstance(items, list):
        return items
    return [normalize_action_entry(a) for a in items]


def normalize_choose_block(entry: dict) -> dict:
    """choose 编排块归一(W3-B, plan G6/D3; 幂等)

    - `{choose: [分支...], default?: [动作项...]}` 键面保留(choose 是编排块不是插件动作,
      不翻译成 {type, params} 形); 分支逐个归一: when 过 normalize_conditions 单点
      (扁平列表同样包隐式 all), then 过 normalize_action_list(动作项同样注入缺省 on_error);
      default 同 then。分支的未知键 / 非法形状(分支非 dict、then 非 list)原样保留,
      交校验器按 choose 坐标 fail-fast(本函数只做形状归一不吞错误);
    - choose 本体无 on_error(错误策略挂在块内动作项上); 嵌套 choose 不在此拦(交校验器
      与引擎构造期双侧拦, 与「非法形状原样透传」的容器定位一致)。

    幂等: normalize_choose_block(normalize_choose_block(x)) == normalize_choose_block(x)
    (when 建树与动作项归一都幂等, 归一一次后收敛稳定)。
    """
    out = {k: v for k, v in entry.items() if k not in CHOOSE_KNOWN_KEYS}
    branches = entry.get("choose")
    if isinstance(branches, list):
        nb = []
        for br in branches:
            if isinstance(br, dict) and ("when" in br or "then" in br):
                nbr = {}
                if "when" in br:
                    nbr["when"] = normalize_conditions(br["when"])
                if "then" in br:
                    nbr["then"] = normalize_action_list(br["then"])
                for k, v in br.items():  # 未知键原样保留, 交校验器 fail-fast
                    if k not in nbr:
                        nbr[k] = v
                nb.append(nbr)
            else:
                nb.append(br)
        out["choose"] = nb
    else:
        out["choose"] = branches  # 非 list(缺失/异形)原样透传交校验器报
    if "default" in entry:
        out["default"] = normalize_action_list(entry["default"])
    return out


def normalize_action_entry(entry: Any) -> Any:
    """单个动作列表项归一(幂等): 旧形/混合形 -> `{type, params, on_error}` 规范形

    - choose 编排块(含 "choose" 键, W3-B)走 normalize_choose_block 单点, 键面保留;
    - 旧扁平单键 dict `{name: value}` -> `{type: name, params: value}`;
    - webui W2 动作卡写出的混合形 `{name: value, on_error: {...}}` -> 规范形(on_error 透传);
    - 已规范形(含 "type" 键)走缺省注入: 无 on_error 补全缺省对象, on_error 缺子键补缺省值
      (ON_ERROR_DEFAULTS 单点)—— 不深拷贝不存在的部分, 已配置值零改写; 伪动作不注入;
    - on_error 形状非法(非 dict)原样保留, 交校验器 fail-fast(本函数只做形状翻译不吞错误);
    - 非 dict / 空 dict / 无法识别的多键 dict(无 "type" 且非「单动作键 + on_error」)原样返回,
      交校验器按扁平坐标报结构错;
    - 参数值(含 checking 子段 dict)原样透传, 嵌套结构零触碰。
    """
    if isinstance(entry, dict) and "choose" in entry:
        return normalize_choose_block(entry)
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


def normalize_conditions(conds: Any) -> Any:
    """条件侧建树单点(W3-A, plan §3.2/G4): 旧扁平单键 dict 列表 -> 包隐式 `all:` 树形

    - list(现行 legacy 形态: 单键 dict 条件的列表) -> `{"all": list(conds)}` —— 语义 =
      现行 Rule.matches 的 all(...); 列表序号 1:1 保留进 all 的孩子(R1-1 扁平坐标回映射依据);
    - dict(已是树形: 组合节点 {all/any/not} 或单条件节点)原样返回(幂等收敛);
    - 其它形状(非 list 非 dict, 如字符串/数字)原样透传交校验器报 —— normalize 不吞错误;
    - 叶子(条件 spec)零触碰: 「逗号分组」等行内语义全部留在叶内(见 CONDITION_GROUPING_MAP),
      组合树的 any/not 是新增显式写法, 不改写既有叶子语义。

    幂等: normalize_conditions(normalize_conditions(x)) == normalize_conditions(x)。
    """
    if isinstance(conds, list):
        return {"all": list(conds)}
    return conds


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
    if "conditions" in spec:
        # W3-A: 条件侧建树(隐式 all 包裹), 见 normalize_conditions / 模块 docstring
        out["conditions"] = normalize_conditions(spec["conditions"])
    return out


def normalize_legacy_rules(data: Any) -> None:
    """config 解析树就地规范化全部 `*_rules` 规则集(load_config 载入链单点, 校验之前)

    就地改写 group 内的 spec 映射(group dict 本身保留, 规则名零触碰 = R1-2); 非 dict
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

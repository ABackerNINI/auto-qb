"""test_rule_compat_mapping 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B/W3-A/W3-B)

normalize_legacy_rule 是 legacy 规则词汇的唯一容身处: 引擎/校验器只认规范化后形态,
禁止「读 legacy 键」的第二语义分支(防 G4 hr 双语义分歧重演)。本文件钉四件事:
生产 5 条规则规范化快照(金标准零差异) / 行为零变化的转换等价性 / R1 两条附注
(错误定位回映射 + 命名透传) / 旧 state 载入回归(exec_history 去重键口径不变)。

⚠ config.yml 是生产红线: 本文件**不 import、不读取**它 —— 生产 5 条规则的 spec 原样
誊写为下方 `_PRODUCTION_RULES_YAML` 夹具(来源注明, 逐字含注释誊写; config.yml 若有
改动须人工同步此夹具并重审快照)。

⚠ 快照金标准口径(W2-B 重锚定): normalize 自 W2-B 起对每个动作项注入缺省 on_error
({policy: stop, retries: 3, backoff: 60}, schema.fields.ON_ERROR_DEFAULTS 单点)——
「含缺省字段」与旧行为零变化等价(policy=stop 即现行失败即止), 快照按注入后形态重锚定。

⚠ 快照金标准口径(W3-A 再重锚定): normalize 自 W3-A 起把旧扁平条件列表包成隐式
`all:` 组合树(normalize_conditions 单点; 语义 = 现行 matches 的 all(...)), 各条件的
行内分组/逗号语义全部留在叶子内(CONDITION_GROUPING_MAP 逐条件映射表), 快照 conditions
按树形重锚定 —— 叶子逐位不变, 行为零变化。

## 测试计划(每个测试函数一条)
- test_normalize_idempotent: 幂等 —— normalize(normalize(x)) == normalize(x)(旧形输入与
  已规范形输入各验一次; 已规范形零改写, 缺 on_error 的规范形补缺省后收敛)
- test_normalize_conditions_builds_tree: 条件建树(W3-A) —— 扁平列表包隐式 all、树形 dict
  原样透传、叶子逐位零触碰; normalize_conditions 自身幂等
- test_condition_grouping_mapping: 「逗号分组」逐条件映射(W3-A/G4) —— tags 组内逗号=AND
  组间=OR、state 组内&=AND 组间=OR 等 13 条件叶子语义经建树+引擎求值与现行为逐条等价;
  hr 双语义分歧维持现状断言; CONDITION_GROUPING_MAP 覆盖 registry 全部条件
- test_condition_grouping_map_covers_registry: 映射表覆盖守卫 —— 逐条件核对表
  (CONDITION_GROUPING_MAP)与注册表条件集一致, 新增条件漏核对当场红
- test_condition_grouping_mapping_freespace: freespace 叶子映射 —— dict{path, amount} 原样,
  取数单点打桩(与 expr 侧 disk_usage_value 同口径)
- test_condition_tree_depth_limit: 组合树深度上限 —— 嵌套 <=16 层通过, >16 层 fail-fast
- test_condition_error_location_maps_back_flat: R1① 条件侧坐标回映射 —— 扁平列表条目的
  校验错报 conditions[i] 扁平坐标; 深度校验错报 conditions[i].<条件名>; 树形子树按树形
  坐标如实报出
- test_on_error_mixed_form_normalized: webui 动作卡写出的混合形 {动作键: 值, on_error: {...}}
  经单点漏斗翻译成规范形 {type, params, on_error}(载入链与直达校验器两条路一致)
- test_normalize_bulk_names_and_keys_passthrough: normalize_legacy_rules 组键/规则键与
  spec 非 conditions/actions 键零触碰(R1② 命名透传; D1: 原内容不被载入规范化改写)
- test_action_error_location_maps_back_flat: R1① 错误定位回映射 —— 结构错报「第 N 个动作 +
  actions[i]」扁平坐标; 深度校验错报 actions[i].<动作名>(不暴露 params 结构路径)
- test_validator_accepts_normalized_form: 校验器只认规范化形态 —— 直接写 {type, params} 新形
  通过校验且载入零再变换; on_error(W2-B)合法取值通过、非法子键/取值/边界 fail-fast 拒绝
- test_load_config_rules_normalized: 载入链顺序 —— load_config 后 cfg.rules_config 已是
  规范化形态(校验前归一), conditions 为隐式 all 树形(W3-A)
- test_engine_legacy_and_normalized_equivalent: 引擎消费等价 —— 旧扁平形与规范化形构造的
  Rule 动作实例同型, 执行行为一致(add_tags 同参调用)
"""

import json

import os

import tempfile

import pytest

import yaml

from auto_qb.config import ConfigError, load_config

from auto_qb.config.compat import (
    CONDITION_TREE_MAX_DEPTH,
    CONDITION_GROUPING_MAP,
    normalize_action_entry,
    normalize_conditions,
    normalize_legacy_rule,
    normalize_legacy_rules,
)

from auto_qb.config.validation import _strip_none

from auto_qb.core.modules import rules_mod

from auto_qb.core.state import StateService

from auto_qb.rules import registry

from auto_qb.rules.actions import AddTagsAction

from auto_qb.rules.base import VERDICT_ERROR, VERDICT_EXECUTED, VERDICT_NO_OP, VERDICT_RETRY, Rule

from helpers import FakeClient, FakeTorrent, make_ctx, make_manager

from rule_compat_support import (
    _checking_params,
    _default_on_error,
    _load_config_from_text,
    _load_errors,
)


def test_normalize_idempotent():
    """幂等: normalize(normalize(x)) == normalize(x); 已规范形输入原样返回零改写"""
    legacy = {
        "enabled": "true",
        "conditions": [{
            "size": ">=1MiB"
        }, {
            "path": ["/a"]
        }],
        "actions": [{
            "add_tags": ["X"]
        }, {
            "checking": _checking_params("full-checking")
        }],
    }
    once = normalize_legacy_rule(legacy)
    assert once["conditions"] == {"all": [{"size": ">=1MiB"}, {"path": ["/a"]}]}, "扁平条件列表包隐式 all(W3-A)"
    # 已规范形(含完整 on_error): 原样返回(同一内容), 且不新建 actions 列表项(身份复用)
    renorm = normalize_legacy_rule(once)
    assert renorm == once
    assert renorm["actions"][0] is once["actions"][0]
    assert renorm["actions"][1] is once["actions"][1]
    # W2-B: 缺 on_error 的规范形在第一次 normalize 即补齐缺省, 其后收敛稳定(幂等不破坏)
    bare = {"actions": [{"type": "add_tags", "params": ["X"]}]}
    filled = normalize_legacy_rule(bare)
    assert filled["actions"][0] == {"type": "add_tags", "params": ["X"], "on_error": _default_on_error()}
    assert normalize_legacy_rule(filled) == filled
    # 顶层输入非 dict / 动作项非 dict / 无法识别的多键 dict: 原样透传交校验器报
    assert normalize_legacy_rule("oops") == "oops"
    assert normalize_action_entry("oops") == "oops"
    assert normalize_action_entry({}) == {}
    assert normalize_action_entry({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_normalize_conditions_builds_tree():
    """条件建树(W3-A): 扁平列表包隐式 all; 树形 dict 原样透传; 叶子逐位零触碰; 自身幂等"""
    # 旧扁平单键 dict 列表 -> {"all": 列表}(序号 1:1 保留, R1① 扁平坐标回映射的依据)
    flat = [{"size": ">=1MiB"}, {"path": ["/a"]}]
    tree = normalize_conditions(flat)
    assert tree == {"all": flat}, "隐式 all 包裹"
    assert tree["all"] == flat, "叶子逐位零触碰(逗号分组语义留在叶内)"
    # 已是树形(dict)原样透传: 组合节点 / 单条件节点 / 非法形状都交校验器, normalize 不吞
    assert normalize_conditions({"all": [{"size": "1MiB"}]}) == {"all": [{"size": "1MiB"}]}
    assert normalize_conditions({"any": [{"size": "1MiB"}]}) == {"any": [{"size": "1MiB"}]}
    assert normalize_conditions({"not": {"size": "1MiB"}}) == {"not": {"size": "1MiB"}}
    assert normalize_conditions({"path": "/a"}) == {"path": "/a"}
    assert normalize_conditions("not-a-tree") == "not-a-tree", "非法形状原样透传交校验器报"
    # 幂等: 建树一次后收敛稳定
    assert normalize_conditions(tree) == tree
    # normalize_legacy_rule 全链: 载入规范化对 conditions 建树, 其余键零触碰
    spec = {"enabled": "true", "conditions": [{"size": ">=1MiB"}]}
    norm = normalize_legacy_rule(spec)
    assert norm["conditions"] == {"all": [{"size": ">=1MiB"}]}
    assert spec["conditions"] == [{"size": ">=1MiB"}], "输入不被就地改写"


def _mapping_rule(tmp_path, conditions, tor_kw=None, tracker_kw=None, no_tracker=False):
    """映射测试辅助: 条件叶子经真实建树漏斗(normalize_legacy_rule -> Rule)构造, 返回求值结果"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"), tracker_kw=tracker_kw)
    tor = FakeTorrent(**(tor_kw or {}))
    ctx = make_ctx(mgr, tor, FakeClient())
    if no_tracker:
        tor.tracker_conf = None  # make_ctx 只在 None 时回填, 此后置 None = 模拟未匹配站点
    spec = normalize_legacy_rule({"conditions": conditions, "actions": []})
    return Rule("g.t", spec, mgr).matches(ctx)


def test_condition_grouping_mapping(tmp_path):
    """「逗号分组」逐条件映射(W3-A/G4): 13 条件叶子语义经建树+求值与现行为逐条等价

    映射结论 = compat.CONDITION_GROUPING_MAP: 行内分隔符/列表 OR 语义全部留在叶子内,
    normalize 零改写(只承诺生产已出现形态); hr 双语义分歧维持现状不单边改齐
    (conditions.py:154-164 vs rules/expr/env.py _hr, 注释证据在叶内)。
    """
    # path: 列表=OR(无行内分组) —— 生产唯一在用条件, regex: 前缀原样
    assert _mapping_rule(tmp_path, [{"path": ["regex:^R:/", "/nope/"]}]) is True
    assert _mapping_rule(tmp_path, [{"path": ["/nope/", "/nada/"]}]) is False
    # size: 单比较串
    assert _mapping_rule(tmp_path, [{"size": ">=1MiB"}], tor_kw={"size": 100 * 1024**2}) is True
    assert _mapping_rule(tmp_path, [{"size": ">=1TiB"}], tor_kw={"size": 100 * 1024**2}) is False
    # tags: 组内逗号=AND, 组间列表=OR(叶子内语义, 不展开成 any)
    assert _mapping_rule(tmp_path, [{"tags": ["HR,low", "z"]}], tor_kw={"tags": "HR,low"}) is True
    assert _mapping_rule(tmp_path, [{"tags": ["HR,low"]}], tor_kw={"tags": "HR"}) is False, "组内逗号=AND"
    assert _mapping_rule(tmp_path, [{"tags": ["nope", "HR"]}], tor_kw={"tags": "HR"}) is True, "组间列表=OR"
    # category: 列表=OR
    assert _mapping_rule(tmp_path, [{"category": ["regex:^HR", "x"]}], tor_kw={"category": "HR"}) is True
    assert _mapping_rule(tmp_path, [{"category": ["x", "y"]}], tor_kw={"category": "HR"}) is False
    # trackers: 列表=OR(默认 manager 装配 HHan 假站点, make_ctx 已匹配)
    assert _mapping_rule(tmp_path, [{"trackers": ["nope", "HHan"]}]) is True
    assert _mapping_rule(tmp_path, [{"trackers": "nope"}]) is False
    # tracker_group: 列表=OR(站点 groups 声明)
    assert _mapping_rule(tmp_path, [{"tracker_group": ["nope", "国内"]}], tracker_kw={"groups": ["国内"]}) is True
    assert _mapping_rule(tmp_path, [{"tracker_group": "国外"}], tracker_kw={"groups": ["国内"]}) is False, "分组不符恒 False"
    # state: 组内 &=AND(非逗号), 组间列表=OR(stalledUP: is_complete/is_uploading 真, is_downloading 假)
    assert _mapping_rule(tmp_path, [{"state": ["is_complete&is_uploading", "is_downloading"]}]) is True
    assert _mapping_rule(tmp_path, [{"state": ["is_complete&is_downloading"]}]) is False, "组内 &=AND"
    assert _mapping_rule(tmp_path, [{"state": ["is_downloading", "is_uploading"]}]) is True, "组间列表=OR"
    # hr: 单模式串; 双语义分歧维持现状(conditions.py:154-164 显式分支, 勿单边改齐):
    # 分支一 tracker_conf=None(未匹配站点) —— 仅 condition-not-met 为真
    assert _mapping_rule(tmp_path, [{"hr": "condition-not-met"}], no_tracker=True) is True
    assert _mapping_rule(tmp_path, [{"hr": "condition-met"}], no_tracker=True) is False
    assert _mapping_rule(tmp_path, [{"hr": "satisfied"}], no_tracker=True) is False
    # 分支二 站点已匹配但无 HR 配置(conf.hr=None, tracker_kw 显式置空) —— 非 condition-met 全真;
    # 其中 satisfied=True 与表达式侧 tor.hr_satisfied 同场景恒 false 有意分歧(那里答「可打标/可删」
    # 达标语义, 本处答「有无义务」, 见 rules/expr/env.py _hr 注释)
    hr_none = {"hr": None}
    assert _mapping_rule(tmp_path, [{"hr": "condition-not-met"}], tracker_kw=hr_none) is True
    assert _mapping_rule(tmp_path, [{"hr": "condition-met"}], tracker_kw=hr_none) is False
    assert _mapping_rule(tmp_path, [{"hr": "satisfied"}], tracker_kw=hr_none) is True
    # date_time: dict 区间串(确定性区间: 当日/当周必在 1-31 / 1-7 内)
    assert _mapping_rule(tmp_path, [{"date_time": {"day_of_month": "1-31", "day_of_week": "1-7"}}]) is True
    assert _mapping_rule(tmp_path, [{"date_time": {"day_of_month": "32"}}]) is False
    # seedtime / upload_ratio: 单比较串
    assert _mapping_rule(tmp_path, [{"seedtime": "<24H"}], tor_kw={"seeding_time": 0}) is True
    assert _mapping_rule(tmp_path, [{"seedtime": ">24H"}], tor_kw={"seeding_time": 0}) is False
    assert _mapping_rule(tmp_path, [{"upload_ratio": "<1.5"}], tor_kw={"ratio": 0.0}) is True
    assert _mapping_rule(tmp_path, [{"upload_ratio": ">1.5"}], tor_kw={"ratio": 0.0}) is False
    # expr: 单表达式串(叶子原样, 编译/语义校验不变)
    assert _mapping_rule(tmp_path, [{"expr": "tor.size > 1MiB"}], tor_kw={"size": 100 * 1024**2}) is True


def test_condition_grouping_mapping_freespace(tmp_path, monkeypatch):
    """freespace 叶子映射: dict{path, amount} 原样; 取数单点打桩(与 expr 侧同口径)"""
    monkeypatch.setattr("auto_qb.rules.conditions.disk_usage_value", lambda p, k: 100 * 1024**3)
    assert _mapping_rule(tmp_path, [{"freespace": {"path": "R:/", "amount": ">1MiB"}}]) is True
    assert _mapping_rule(tmp_path, [{"freespace": {"path": "R:/", "amount": "<1MiB"}}]) is False


def test_condition_grouping_map_covers_registry():
    """映射表覆盖守卫: 逐条件核对表(CONDITION_GROUPING_MAP)与注册表条件集一致"""
    registered = set(registry.CONDITIONS)
    assert set(CONDITION_GROUPING_MAP) == registered, (
        "逗号分组映射表漏核对条件 —— 新增条件必须在 compat.CONDITION_GROUPING_MAP 补行内分组语义 "
        "(计划 §3.2/G4: 以 conditions.py 现行为准逐条件核对)"
    )


def test_condition_tree_depth_limit():
    """组合树深度上限(W3-A): 嵌套 <=16 层通过, >16 层 fail-fast(防递归爆炸)"""
    def nested(k: int) -> dict:
        node = {"size": ">=1MiB"}
        for _ in range(k):
            node = {"all": [node]}
        return node

    def _try_load(k: int) -> str:
        flow = yaml.safe_dump(nested(k), default_flow_style=True).strip()
        return _load_errors(
            "config:\n  my_rules:\n    r1:\n"
            f"      conditions: {flow}\n"
            "      actions:\n        - add_tags: [\"A\"]\n"
        )

    assert _try_load(CONDITION_TREE_MAX_DEPTH - 1) == "", "上限内(16 层组合节点)合法"
    err = _try_load(CONDITION_TREE_MAX_DEPTH)
    assert f"组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层" in err, err


def test_condition_error_location_maps_back_flat():
    """R1① 条件侧坐标回映射: 扁平列表条目报 conditions[i]; 树形子树按树形坐标如实报"""
    # 扁平列表条目的未知条件 -> conditions[0](不是 conditions.all[0])
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions:\n        - bogus_cond: 1\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions[0]: 未知条件 'bogus_cond'" in err, err
    assert "conditions.all" not in err, err
    # 深度校验错: 扁平坐标 conditions[i].<条件名>
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions:\n        - tags: ['regex:[x']\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions[0].tags[0]: 非法正则" in err, err
    # 用户手写树形的子树错误 -> 树形坐标如实报(那里本就是树形写法, 无扁平坐标可回映射)
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {any: [{bogus_cond: 1}]}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions.any[0]: 未知条件 'bogus_cond'" in err, err
    err = _load_errors(
        "config:\n  my_rules:\n    r1:\n"
        "      conditions: {not: {bogus_cond: 1}}\n"
        "      actions:\n        - add_tags: [\"A\"]\n"
    )
    assert "r1.conditions.not: 未知条件 'bogus_cond'" in err, err


def test_on_error_mixed_form_normalized():
    """webui 动作卡混合形 {动作键: 值, on_error: {...}} -> 规范形(单点漏斗, 载入链直达一致)"""
    mixed = {"add_tags": ["X"], "on_error": {"policy": "continue"}}
    norm = normalize_action_entry(mixed)
    assert norm == {
        "type": "add_tags",
        "params": ["X"],
        "on_error": {
            "policy": "continue",
            "retries": 3,
            "backoff": 60
        },
    }
    # 混合形 + 非 dict on_error: 容器归一照做, on_error 原样透传交校验器报
    bad = normalize_action_entry({"add_tags": ["X"], "on_error": 1})
    assert bad == {"type": "add_tags", "params": ["X"], "on_error": 1}
    # 两键但无 on_error 且非单键旧形(动作键 + 未知键): 原样透传交校验器按扁平坐标报
    assert normalize_action_entry({"add_tags": ["X"], "bogus": 1}) == {"add_tags": ["X"], "bogus": 1}
    # 只剩 on_error(动作键缺失): 原样透传交校验器报结构错
    assert normalize_action_entry({"on_error": {"policy": "stop"}}) == {"on_error": {"policy": "stop"}}
    # 混合形经真实载入链等价: load 后 actions 已是规范形且校验通过
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - add_tags: [\"M\"]\n"
        "          on_error: {policy: continue}\n"
    )
    assert cfg.rules_config["my_rules"]["r1"]["actions"] == [
        {
            "type": "add_tags",
            "params": ["M"],
            "on_error": {
                "policy": "continue",
                "retries": 3,
                "backoff": 60
            },
        }
    ]


def test_normalize_bulk_names_and_keys_passthrough():
    """R1② 命名透传: 组键/规则键与 spec 非 conditions/actions 键零触碰; 输入 spec 不被就地改写"""
    spec = {
        "enabled": "true",
        "trigger": "on_torrent_added",
        "cooldown": "5M",
        "conditions": [{
            "path": ["regex:^R:/"]
        }],
        "actions": [{
            "add_tags": ["R"]
        }],
    }
    original = json.dumps(spec, ensure_ascii=False)
    data = {"config": {"组名_rules": {"规则名": spec}}}
    normalize_legacy_rules(data)
    group = data["config"]["组名_rules"]
    assert list(group) == ["规则名"], "规则键(命名后半)不得被改写"
    norm = group["规则名"]
    assert norm["enabled"] == "true" and norm["trigger"] == "on_torrent_added" and norm["cooldown"] == "5M"
    assert norm["conditions"] == {"all": spec["conditions"]}, "conditions 建树(W3-A), 叶子逐位不变"
    assert norm["actions"] == [{"type": "add_tags", "params": ["R"], "on_error": _default_on_error()}]
    # 载入规范化不就地改写原 spec(D1: 配置原内容原样保留)
    assert json.dumps(spec, ensure_ascii=False) == original


def test_action_error_location_maps_back_flat():
    """R1① 错误定位回映射: 结构错报「第 N 个动作」+ actions[i]; 深度错报 actions[i].<动作名>"""
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - size: \">=1MiB\"\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
        "        - add_tags: [\"B\"]\n"
        "          stop: true\n",
    )
    assert "actions[1]" in err, err
    assert "第 2 个动作" in err, err
    assert "必须是单键字典" in err, err

    # 深度校验错: 归一形 params 的错误以动作名扁平坐标报出(不暴露 params 结构路径)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
        "        - checking:\n"
        "            basic_check: bogus\n",
    )
    assert "r1.actions[1].checking" in err, err
    assert "basic_check 取值非法" in err, err
    assert "params" not in err, "报错话术不得暴露归一形结构路径 params"


def test_validator_accepts_normalized_form():
    """校验器只认规范化形态: {type, params} 新形直接通过; on_error(W2-B)合法通过/非法 fail-fast"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - size: \">=1MiB\"\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params:\n"
        "            - \"NEW\"\n"
    )
    acts = cfg.rules_config["my_rules"]["r1"]["actions"]
    assert acts == [
        {
            "type": "add_tags",
            "params": ["NEW"],
            "on_error": _default_on_error()
        }
    ], "新形输入经 normalize 注入缺省 on_error(幂等收敛)"

    # on_error 合法取值(三档 + 边界值)直接通过校验
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: retry, retries: 2, backoff: 30}\n"
    )
    assert cfg.rules_config["my_rules"]["r1"]["actions"][0]["on_error"] == {
        "policy": "retry",
        "retries": "2",
        "backoff": "30",
    }, "on_error 合法取值零改写(用户配置值保留 BaseLoader 字符串标量口径, 引擎构造期 int/float 解析)"

    # 非法 policy 聚合报错(fail-fast)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: bogus}\n"
    )
    assert "policy 取值非法" in err, err
    assert "可选: stop/continue/retry" in err, err

    # retries/backoff 边界校验(负数 / 非数字 / 未知子键), 聚合一次报全
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {retries: -1, backoff: 0, bogus: 1}\n"
    )
    assert "retries 必须 >= 0" in err, err
    assert "backoff 必须 > 0" in err, err
    assert "未知键 ['bogus']" in err, err

    # on_error 整体形状错(非 dict)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: continue\n"
    )
    assert "on_error: 必须是字典" in err, err

    # retries/backoff 非数字(聚合报错)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"X\"]\n"
        "          on_error: {policy: retry, retries: abc, backoff: xyz}\n"
    )
    assert "retries 必须是整数" in err, err
    assert "backoff 必须是数字" in err, err

    # 未知动作名与未知动作项键(fail-fast 键面, 与 on_error 扩展无关的老路径守住)
    err = _load_errors("config:\n"
                       "  my_rules:\n"
                       "    r1:\n"
                       "      actions:\n"
                       "        - bogus_action: [1]\n")
    assert "未知动作 'bogus_action'" in err, err
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - type: add_tags\n"
        "          params: [\"A\"]\n"
        "          bogus: 1\n"
    )
    assert "未知键 ['bogus']" in err, err

    # 未知条件名(conditions 侧同口径)
    err = _load_errors(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      conditions:\n"
        "        - bogus_cond: 1\n"
        "      actions:\n"
        "        - add_tags: [\"A\"]\n"
    )
    assert "未知条件 'bogus_cond'" in err, err


def test_load_config_rules_normalized():
    """载入链顺序: load_config 后 cfg.rules_config 已是规范化形态(校验前归一), conditions 为隐式 all 树"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      interval: 30M\n"
        "      conditions:\n"
        "        - path:\n"
        "            - \"regex:^I:/\"\n"
        "      actions:\n"
        "        - checking:\n"
        "            basic_check: filelist\n"
    )
    spec = cfg.rules_config["my_rules"]["r1"]
    assert spec["conditions"] == {"all": [{"path": ["regex:^I:/"]}]}, "conditions 建树为隐式 all(W3-A)"
    assert spec["actions"] == [
        {
            "type": "checking",
            "params": {
                "basic_check": "filelist"
            },
            "on_error": _default_on_error()
        }
    ]


def test_engine_legacy_and_normalized_equivalent(tmp_path):
    """引擎消费等价: 旧扁平形与规范化形构造的 Rule 动作同型, 执行行为一致"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()
    tor = FakeTorrent(tags="", size=100 * 1024**2)
    ctx = make_ctx(mgr, tor, client)
    legacy = Rule("g.t", {"actions": [{"add_tags": ["X"]}]}, mgr)
    normalized = Rule("g.t", {"actions": [{"type": "add_tags", "params": ["X"]}]}, mgr)
    assert [type(a) for a in legacy.actions] == [type(a) for a in normalized.actions]
    assert all(isinstance(a, AddTagsAction) for a in (*legacy.actions, *normalized.actions))
    assert normalized.process(ctx) == VERDICT_EXECUTED
    assert ("add_tags", ["X"]) in client.calls, "规范化动作以同参执行(零行为变化)"

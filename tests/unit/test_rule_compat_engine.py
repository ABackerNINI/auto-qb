"""test_rule_compat_engine 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B/W3-A/W3-B)

normalize_legacy_rule 是 legacy 规则词汇的唯一容身处: 引擎/校验器只认规范化后形态,
禁止「读 legacy 键」的第二语义分支(防 G4 hr 双语义分歧重演)。本文件钉四件事:
生产 5 条规则规范化快照(金标准零差异) / 行为零变化的转换等价性 / R1 两条附注
(错误定位回映射 + 命名透传) / 旧 state 载入回归(exec_history 去重键口径不变)。

WARN: config.yml 是生产红线: 本文件**不 import、不读取**它 —— 生产 5 条规则的 spec 原样
誊写为下方 `_PRODUCTION_RULES_YAML` 夹具(来源注明, 逐字含注释誊写; config.yml 若有
改动须人工同步此夹具并重审快照)。

WARN: 快照金标准口径(W2-B 重锚定): normalize 自 W2-B 起对每个动作项注入缺省 on_error
({policy: stop, retries: 3, backoff: 60}, schema.fields.ON_ERROR_DEFAULTS 单点)——
「含缺省字段」与旧行为零变化等价(policy=stop 即现行失败即止), 快照按注入后形态重锚定。

WARN: 快照金标准口径(W3-A 再重锚定): normalize 自 W3-A 起把旧扁平条件列表包成隐式
`all:` 组合树(normalize_conditions 单点; 语义 = 现行 matches 的 all(...)), 各条件的
行内分组/逗号语义全部留在叶子内(CONDITION_GROUPING_MAP 逐条件映射表), 快照 conditions
按树形重锚定 —— 叶子逐位不变, 行为零变化。

## 测试计划(每个测试函数一条)
- test_combo_tree_evaluation: 组合树求值(W3-A) —— all/any/not 递归 + 嵌套 + 短路
  (all 首个 False / any 首个 True 后叶子不再求值)+ 叶子异常上抛(process 兜 verdict:error)
- test_engine_condition_tree_legacy_equivalent: 引擎等价 —— 旧扁平条件列表与规范化树形
  构造的 Rule 建树同构、求值同果(隐式 all = 现行 all(...))
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
    _Boom,
    _Fixed,
)


def _eval_rule(tmp_path, tree):
    """构造 Rule 并手动挂条件树(内存表示单测; spec 级路径由映射/载入测试覆盖)"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), FakeClient())
    rule = Rule("g.t", {"actions": []}, mgr)
    rule.condition_tree = tree
    return rule, ctx


def test_combo_tree_evaluation(tmp_path):
    """组合树求值(W3-A): all/any/not 递归 + 嵌套 + 短路 + 叶子异常上抛 -> verdict:error"""
    t1, t2, f1, f2 = _Fixed(True), _Fixed(True), _Fixed(False), _Fixed(False)
    boom = _Boom()

    # all: 全真才真; any: 一真即真; not: 取反
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", t1), ("leaf", t2)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", t1), ("leaf", f1)]))
    assert rule.matches(ctx) is False
    rule, ctx = _eval_rule(tmp_path, ("any", [("leaf", f1), ("leaf", t1)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("not", ("leaf", f1)))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("not", ("leaf", t1)))
    assert rule.matches(ctx) is False

    # 嵌套: any( all(T,T), F ) = True; all( any(F,T), F ) = False
    rule, ctx = _eval_rule(tmp_path, ("any", [("all", [("leaf", t1), ("leaf", t2)]), ("leaf", f1)]))
    assert rule.matches(ctx) is True
    rule, ctx = _eval_rule(tmp_path, ("all", [("any", [("leaf", f1), ("leaf", t1)]), ("leaf", f2)]))
    assert rule.matches(ctx) is False

    # 短路: all 首个 False 后 / any 首个 True 后, 其后叶子不再求值
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", f1), ("leaf", boom)]))
    assert rule.matches(ctx) is False and boom.calls == 0, "all 短路: False 后不再求值"
    rule, ctx = _eval_rule(tmp_path, ("any", [("leaf", t1), ("leaf", boom)]))
    assert rule.matches(ctx) is True and boom.calls == 0, "any 短路: True 后不再求值"

    # 叶子异常上抛: matches 抛 RuntimeError; process 兜成 verdict:error 本条本轮不命中(W2 语义)
    rule, ctx = _eval_rule(tmp_path, ("all", [("leaf", _Boom())]))
    with pytest.raises(RuntimeError):
        rule.matches(ctx)
    rule.actions = [AddTagsAction(["X"])]
    assert rule.process(ctx) == VERDICT_ERROR, "条件异常 -> verdict:error, 本条本轮不命中"


def test_engine_condition_tree_legacy_equivalent(tmp_path):
    """引擎等价: 旧扁平条件列表与规范化树形构造的 Rule 求值同型同果(隐式 all = 现行 all(...))"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    tor = FakeTorrent(tags="HR", size=100 * 1024**2)
    ctx = make_ctx(mgr, tor, FakeClient())
    legacy = Rule("g.t", {"conditions": [{"size": ">=1MiB"}, {"tags": "HR"}], "actions": []}, mgr)
    tree = Rule(
        "g.t",
        {
            "conditions": {
                "all": [{
                    "size": ">=1MiB"
                }, {
                    "tags": "HR"
                }]
            },
            "actions": []
        },
        mgr,
    )

    def tree_shape(node):
        """树的类型形状(叶子按插件类名比, 实例身份不比)"""
        kind, payload = node
        if kind == "leaf":
            return (kind, type(payload).__name__)
        if kind == "not":
            return (kind, tree_shape(payload))
        return (kind, [tree_shape(c) for c in payload])

    assert tree_shape(legacy.condition_tree) == tree_shape(tree.condition_tree), ("扁平形经单点漏斗建树后与手写树形同构")
    assert legacy.matches(ctx) is True and tree.matches(ctx) is True

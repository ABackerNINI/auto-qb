"""test_rule_compat_choose 测试计划: 规则兼容层(config/compat.py 载入规范化单点, plan 26-11-01-0106 §3.2 W2-A/W2-B/W3-A/W3-B)

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
- test_choose_normalize_form: choose 归一形态(W3-B) —— {choose, default} 键面保留(编排块不翻
  {type, params} 形); when 扁平列表包隐式 all; then/default 动作项注入缺省 on_error; 块级/分支级
  未知键与非 dict 分支原样透传交校验器; normalize_choose_block 幂等
- test_choose_validator_accepts_normalized_form: 校验器认 choose(W3-B) —— 合法 choose 经真实
  载入链零再变换(when 树形保留、then/default 注入缺省 on_error)
- test_choose_validator_fail_fast: choose fail-fast(W3-B) —— 块级/分支级未知键、缺 when、缺 then、
  choose 非列表、空分支列表、then/default 非 list、嵌套 choose(then 与 default 两侧)、when 内
  未知条件全部拒绝, 坐标报 choose[i].when / choose[i].then[j] 树形
- test_choose_when_depth_limit: choose 的 when 条件树深度复用 CONDITION_TREE_MAX_DEPTH ——
  <=16 层通过, >16 层 fail-fast(独立计深度, 与顶层 conditions 同口径)
- test_choose_engine_branch_dispatch: choose 引擎求值(W3-B) —— 按序求 when 首个命中执行其 then
  (后续分支短路不再求值); 无命中走 default; 无命中无 default = 空操作(no_op 语义); 与普通动作
  混排按 steps 顺序执行
- test_choose_engine_when_error: choose 的 when 求值异常 -> 整条本轮 VERDICT_ERROR(保守: 求值
  出错不误入 default), 与顶层条件异常同语义
- test_choose_engine_on_error_dispatch: choose 内动作 on_error 三档分派(W3-B, 与顶层同语义) ——
  continue 继续分支后续动作; stop 中断整条链(分支后续与块后动作都不执行, 失败动作计已执行);
  retry 挂块首断点 + retry_delay=backoff(任务级 requeue, 无 run 内 sleep)
- test_choose_nested_construction_rejected: 嵌套 choose 构造期兜底(W3-B) —— 绕过校验器直构造
  Rule 遇 then/default 内嵌套 choose 报 ConfigError(编排块只允许一层)
- test_choose_deleted_trigger_whitelist: on_torrent_deleted 白名单覆盖 choose 块内动作(W3-B) ——
  then/default 内非白名单动作同样 fail-fast
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
    _default_on_error,
    _load_config_from_text,
    _load_errors,
)


def test_choose_normalize_form():
    """choose 归一形态(W3-B): {choose, default} 键面保留(编排块不翻 {type, params} 形);
    when 扁平列表包隐式 all; then/default 动作项注入缺省 on_error; 异形原样透传; 幂等"""
    entry = {
        "choose": [{
            "when": [{
                "size": ">=1MiB"
            }],
            "then": [{
                "add_tags": ["T"]
            }]
        }, ],
        "default": [{
            "add_tags": ["D"]
        }],
    }
    norm = normalize_action_entry(entry)
    assert set(norm) == {"choose", "default"}, "choose 是编排块不是插件动作, 不翻译成 {type, params} 形"
    assert norm["choose"] == [
        {
            "when": {
                "all": [{
                    "size": ">=1MiB"
                }]
            },
            "then": [{
                "type": "add_tags",
                "params": ["T"],
                "on_error": _default_on_error()
            }],
        }
    ], "when 扁平列表包隐式 all(与 conditions 同款建树), then 注入缺省 on_error"
    assert norm["default"] == [{"type": "add_tags", "params": ["D"], "on_error": _default_on_error()}]
    assert normalize_action_entry(norm) == norm, "choose 归一幂等(归一一次后收敛稳定)"
    # 块级/分支级未知键原样保留交校验器 fail-fast(normalize 不吞错误)
    bad = normalize_action_entry({"choose": [{"when": {"size": "1MiB"}, "then": [], "bogus": 1}], "bogus2": 2})
    assert bad["bogus2"] == 2 and bad["choose"][0]["bogus"] == 1
    # 非 list choose / 非 dict 分支原样透传
    assert normalize_action_entry({"choose": "oops"})["choose"] == "oops"
    assert normalize_action_entry({"choose": [1]})["choose"] == [1]
    # 树形 when 原样透传(幂等收敛); 无 default 不造键
    tree_entry = {"choose": [{"when": {"any": [{"size": ">=1MiB"}]}, "then": []}]}
    assert normalize_action_entry(tree_entry) == {"choose": [{"when": {"any": [{"size": ">=1MiB"}]}, "then": []}]}
    assert "default" not in normalize_action_entry({"choose": []})


def test_choose_validator_accepts_normalized_form():
    """校验器认 choose(W3-B): 合法 choose 经真实载入链零再变换(when 树形保留, then/default 注入缺省)"""
    cfg = _load_config_from_text(
        "config:\n"
        "  my_rules:\n"
        "    r1:\n"
        "      actions:\n"
        "        - choose:\n"
        "            - when:\n"
        "                all:\n"
        "                  - size: \">=1MiB\"\n"
        "              then:\n"
        "                - add_tags: [\"T\"]\n"
        "                - add_tags: [\"T2\"]\n"
        "                  on_error: {policy: continue}\n"
        "            - when: {tags: HR}\n"
        "              then: []\n"
        "          default:\n"
        "            - add_tags: [\"D\"]\n"
    )
    acts = cfg.rules_config["my_rules"]["r1"]["actions"]
    assert acts == [
        {
            "choose":
                [
                    {
                        "when": {
                            "all": [{
                                "size": ">=1MiB"
                            }]
                        },
                        "then":
                            [
                                {
                                    "type": "add_tags",
                                    "params": ["T"],
                                    "on_error": _default_on_error()
                                },
                                {
                                    "type": "add_tags",
                                    "params": ["T2"],
                                    "on_error": {
                                        "policy": "continue",
                                        "retries": 3,
                                        "backoff": 60
                                    },
                                },
                            ],
                    },
                    {
                        "when": {
                            "tags": "HR"
                        },
                        "then": []
                    },
                ],
            "default": [{
                "type": "add_tags",
                "params": ["D"],
                "on_error": _default_on_error()
            }],
        }
    ], "choose 块经载入链零再变换(when 树形保留, then/default 缺省 on_error 注入)"


def test_choose_validator_fail_fast():
    """choose fail-fast(W3-B): 键面/分支结构/嵌套/when 未知条件全部拒绝, 坐标按树形如实报"""
    head = "config:\n  my_rules:\n    r1:\n      actions:\n"
    # 块级未知键
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n          bogus: 1\n")
    assert "未知键 ['bogus']" in err and "可用键: ['choose', 'default']" in err, err
    # 分支缺 when / 缺 then / 分支级未知键
    err = _load_errors(head + "        - choose: [{then: []}]\n")
    assert "choose[0]: 缺少 when" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}}]\n")
    assert "choose[0]: 缺少 then" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [], bogus: 1}]\n")
    assert "choose[0]: 未知键 ['bogus']" in err and "可用键: ['then', 'when']" in err, err
    # choose 非列表 / 空分支列表 / then 非 list / default 非 list
    err = _load_errors(head + "        - choose: oops\n")
    assert "choose: 必须是分支列表" in err, err
    err = _load_errors(head + "        - choose: []\n")
    assert "分支列表不能为空" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: oops}]\n")
    assert "choose[0].then: 必须是列表" in err, err
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n          default: oops\n")
    assert "default: 必须是列表" in err, err
    # 嵌套 choose(then 与 default 两侧)—— 编排块只允许一层
    nested = "- choose: [{when: {size: \">=1MiB\"}, then: [{choose: [{when: {size: \">=1MiB\"}, then: []}]}]}]\n"
    err = _load_errors(head + "        " + nested)
    assert "choose 内不允许嵌套 choose" in err, err
    err = _load_errors(
        head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n"
        "          default: [{choose: [{when: {size: \">=1MiB\"}, then: []}]}]\n"
    )
    assert "choose 内不允许嵌套 choose" in err, err
    # when 内未知条件 fail-fast(与 conditions 同款键面)
    err = _load_errors(head + "        - choose: [{when: {bogus_cond: 1}, then: []}]\n")
    assert "choose[0].when: 未知条件 'bogus_cond'" in err, err
    # then 内动作深度校验照常分发(未知动作同径报)
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [{bogus_action: [1]}]}]\n")
    assert "choose[0].then[0]: 未知动作 'bogus_action'" in err, err


def test_choose_when_depth_limit():
    """choose 的 when 条件树深度复用 CONDITION_TREE_MAX_DEPTH(W3-B): <=16 层通过, >16 层拒绝"""
    head = "config:\n  my_rules:\n    r1:\n      actions:\n"

    def nested(k: int) -> str:
        node = {"size": ">=1MiB"}
        for _ in range(k):
            node = {"all": [node]}
        return json.dumps(node)

    ok = _load_errors(head + f"        - choose: [{{when: {nested(CONDITION_TREE_MAX_DEPTH - 1)}, then: []}}]\n")
    assert ok == "", f"when 深度上限内合法: {ok}"
    err = _load_errors(head + f"        - choose: [{{when: {nested(CONDITION_TREE_MAX_DEPTH)}, then: []}}]\n")
    assert f"组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层" in err, err


def test_choose_engine_branch_dispatch(tmp_path):
    """choose 引擎求值(W3-B): 首个命中执行其 then(后续分支短路不再求值); 无命中走 default;
    无命中无 default = 空操作(no_op 语义); 与普通动作混排按 steps 顺序执行"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()
    tor = FakeTorrent(tags="", size=100 * 1024**2)  # >=1MiB 命中, tags 不含 HR
    ctx = make_ctx(mgr, tor, client)

    def build(branches, default=None):
        acts = [{"choose": branches}]
        if default is not None:
            acts[0]["default"] = default
        return Rule("g.t", normalize_legacy_rule({"actions": acts}), mgr)

    def block_of(rule):
        assert rule.steps[0][0] == "choose"
        return rule.steps[0][1]

    # 首个命中短路: 第二分支恒真也不再求值, 只执行第一分支 then
    b1, b2 = _Fixed(True), _Fixed(True)
    rule = build(
        [
            {
                "when": {
                    "size": ">=1MiB"
                },
                "then": [{
                    "add_tags": ["THEN1"]
                }]
            },
            {
                "when": {
                    "size": ">=1MiB"
                },
                "then": [{
                    "add_tags": ["THEN2"]
                }]
            },
        ]
    )
    blk = block_of(rule)
    blk.branches[0].tree = ("leaf", b1)
    blk.branches[1].tree = ("leaf", b2)
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert client.calls == [("add_tags", ["THEN1"])], f"首个命中分支执行且短路: {client.calls}"
    assert b2.calls == 0, "后续分支不再求值(短路)"

    # 无命中 -> default
    client.calls.clear()
    rule = build([{"when": {"size": ">=1TiB"}, "then": [{"add_tags": ["NOPE"]}]}], default=[{"add_tags": ["DEF"]}])
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert client.calls == [("add_tags", ["DEF"])], "无命中分支走 default"

    # 无命中且无 default = 空操作(no_op, 与空动作表一致)
    client.calls.clear()
    rule = build([{"when": {"size": ">=1TiB"}, "then": [{"add_tags": ["NOPE"]}]}])
    assert rule.process(ctx) == VERDICT_NO_OP, "无命中无 default = no_op"

    # 与普通动作混排: TOP -> choose(THEN) -> TAIL 顺序执行
    rule = Rule(
        "g.t",
        normalize_legacy_rule(
            {
                "actions":
                    [
                        {
                            "add_tags": ["TOP"]
                        },
                        {
                            "choose": [{
                                "when": {
                                    "size": ">=1MiB"
                                },
                                "then": [{
                                    "add_tags": ["THEN"]
                                }]
                            }]
                        },
                        {
                            "add_tags": ["TAIL"]
                        },
                    ]
            }
        ),
        mgr,
    )
    assert [s[0] for s in rule.steps] == ["action", "choose", "action"], "choose 与普通动作混排进执行步"
    client.calls.clear()
    rule.process(ctx)
    assert client.calls == [("add_tags", ["TOP"]), ("add_tags", ["THEN"]), ("add_tags", ["TAIL"])]


def test_choose_engine_when_error(tmp_path):
    """choose 的 when 求值异常(W3-B 自定口径) -> 整条本轮 VERDICT_ERROR(保守: 不误入 default)"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), FakeClient())
    rule = Rule(
        "g.t",
        normalize_legacy_rule(
            {"actions": [{
                "choose": [{
                    "when": {
                        "size": ">=1MiB"
                    },
                    "then": []
                }],
                "default": [{
                    "add_tags": ["DEF"]
                }]
            }]}
        ),
        mgr,
    )
    rule.steps[0][1].branches[0].tree = ("leaf", _Boom())
    assert rule.process(ctx) == VERDICT_ERROR, "when 求值异常 -> error, 不误入 default"


class _Fail:
    """choose on_error 分派测试用的失败动作桩(不进注册表, 直换分支内插件实例)"""

    name = "fail_stub"

    def execute(self, ctx):
        return ActionResult.fail("stub fail")


def test_choose_engine_on_error_dispatch(tmp_path):
    """choose 内动作 on_error 三档分派(W3-B, 与顶层同语义; 无第二语义分支):
    continue 继续分支后续; stop 中断整条链; retry 挂块首断点 + retry_delay"""
    from auto_qb.core.taskqueue import Task
    from auto_qb.rules.base import VERDICT_RETRY

    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    client = FakeClient()

    def build(then, default=None):
        acts = [{"choose": [{"when": {"size": ">=1MiB"}, "then": then}]}]
        if default is not None:
            acts[0]["default"] = default
        return Rule("g.t", normalize_legacy_rule({"actions": acts}), mgr)

    def branch_of(rule):
        return rule.steps[0][1].branches[0]

    ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)

    # continue: 分支内失败后续动作继续
    rule = build([{"add_tags": ["A"], "on_error": {"policy": "continue"}}, {"add_tags": ["B"]}])
    branch_of(rule).actions[0] = _Fail()
    assert rule.process(ctx) == VERDICT_EXECUTED
    assert ("add_tags", ["B"]) in client.calls, "continue 档: 分支内失败后续动作继续"

    # stop(默认): 中断整条链 —— 分支后续与块后动作都不执行; 失败动作本身计已执行
    client.calls.clear()
    rule = build([{"add_tags": ["A"]}, {"add_tags": ["B"]}], default=[{"add_tags": ["DEF"]}])
    rule.steps.append(("action", AddTagsAction(["TAIL"]), Rule._resolve_on_error(None)))
    branch_of(rule).actions[0] = _Fail()
    assert rule.process(ctx) == VERDICT_EXECUTED, "失败动作本身算已执行"
    assert ("add_tags", ["B"]) not in client.calls and ("add_tags", ["TAIL"]) not in client.calls, \
        f"stop 档中断整条链: {client.calls}"

    # retry: 挂块首断点(choose 步粒度, 续跑轮整块重新求值重新分派) + retry_delay=backoff
    client.calls.clear()
    rule = build([{"add_tags": ["A"], "on_error": {"policy": "retry", "retries": 2, "backoff": 30}}])
    branch_of(rule).actions[0] = _Fail()
    task = Task("rule", rule.name, hash=ctx.hash, store=mgr.store, interval=300)
    ctx.task = task
    assert rule.process(ctx) == VERDICT_RETRY, "choose 内 retry 同走任务级 requeue 信号"
    assert task.resume_index == 0, f"断点挂块首(choose 步索引): {task.resume_index}"
    assert task.retry_delay == 30, f"backoff 推迟意图挂 Task: {task.retry_delay}"


def test_choose_nested_construction_rejected(tmp_path):
    """嵌套 choose 构造期兜底(W3-B): 绕过校验器直构造 Rule 遇 then 内嵌套 choose 报 ConfigError"""
    mgr = make_manager(os.path.join(tmp_path, "state.json"))
    nested = {
        "choose": [{
            "when": {
                "size": ">=1MiB"
            },
            "then": [{
                "choose": [{
                    "when": {
                        "size": ">=1MiB"
                    },
                    "then": []
                }]
            }]
        }]
    }
    with pytest.raises(ConfigError, match="choose 内不允许嵌套 choose"):
        Rule("g.t", normalize_legacy_rule({"actions": [nested]}), mgr)


def test_choose_deleted_trigger_whitelist():
    """on_torrent_deleted 白名单覆盖 choose 块内动作(W3-B): then/default 内非白名单动作同样 fail-fast"""
    head = "config:\n  my_rules:\n    r1:\n      trigger: on_torrent_deleted\n      actions:\n"
    err = _load_errors(head + "        - choose: [{when: {size: \">=1MiB\"}, then: [{add_tags: [\"X\"]}]}]\n")
    assert "choose[0].then[0]: 动作 'add_tags' 不适用于 trigger 'on_torrent_deleted'" in err, err
    err = _load_errors(
        head + "        - choose: [{when: {size: \">=1MiB\"}, then: []}]\n"
        "          default: [{add_tags: [\"X\"]}]\n"
    )
    assert "default[0]: 动作 'add_tags' 不适用于 trigger 'on_torrent_deleted'" in err, err

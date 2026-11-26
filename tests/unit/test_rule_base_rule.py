"""test_rule_base_rule 测试计划: rules/base ActionResult/RuleContext/Rule

## 测试计划(每个测试函数一条)
- test_rule_basic_process: 规则基本执行流程(条件满足 -> 动作执行, verdict=executed)
- test_rule_condition_not_met: 条件未满足 -> 不执行动作(verdict=no_match)
- test_rule_execute_once_dedup: execute_once=once 去重
- test_load_retired_stop_key_disables_rule: 载入检测 stop_following_rules_if -> 规则转未启用 + warning,
  配置原内容原样保留(D1 升级路线, plan 26-11-01-0106 W1)
- test_load_retired_ignore_key_warns_equivalent: 载入检测伪动作 ignore_next_action_error -> 转未启用 +
  warning 话术含等价新写法 on_error: {policy: continue}
- test_load_retired_nested_in_choose_branches: 载入检测 choose 分支 then/default 内的嵌套伪动作 ->
  转未启用 + 嵌套剔除(issue 26-11-03-1120: 曾只扫顶层, 嵌套项通过校验后构造 Rule ConfigError)
- test_retired_detection_strip_nested_edge_shapes: 嵌套检测/剔除的边界形状 —— 非 dict 项透传、
  异形 choose/分支透传(形状报错归校验器)、多分支不短路在首分支、then 净 default 染
- test_load_retired_keys_warn_every_load: 每次载入都提示(热重载重建也再报)
- test_load_clean_rules_no_retired_warning: 无退役键的规则载入零告警且 enabled 原样(不带两键零行为变化)
- test_rule_condition_exception: 条件异常 -> verdict=error, 本条本轮跳过且话术不再宣称「停止后续规则」
- test_rule_action_failed_breaks_chain: 动作失败中断本条动作链(ignore_error 已退役拆除, 失败恒中断)
- test_rule_action_failed_stop: 动作失败 verdict=executed(失败动作计已执行), 链中断无 stop 语义
- test_rule_stop_if_never: stop 键退役: Rule 不再有 stop_if 消费面, 行为与不带键一致
- test_rule_stop_if_all_actions_succeed: 六档退役: 六档取值引擎侧全部等价(无链间控制流)
- test_rule_stop_if_conditions_not_met: conditions-not-met 退役: 条件不满足仅本条不执行
- test_rule_cooldown_dedup: cooldown 冷却期内去重
- test_rule_hourly_dedup: hourly 同小时去重
- test_rule_process_action_exception: 动作异常 -> 容错为 fail, verdict=executed
- test_rule_pseudo_action_direct_construction_rejected: 绕过载入层直接构造 Rule 遇伪动作 -> ConfigError
  (引擎不再消费 ignore_next_action_error, 载入层转未启用时才剔除)
- test_rule_daily_dedup: execute_once=daily 同日已执行 -> 去重
- test_rule_actions_skip_non_dict: actions 中非 dict 项 -> 跳过
- test_rule_multi_condition_and: 多条件 AND: 全部满足才执行, 任一不满足不执行
- test_rule_state_group_combined: 状态组合条件(is_complete&is_uploading)规则层仅对同时满足执行
- test_reannounce_without_dedup_warns: reannounce 未配去重 -> 构造期 WARNING; 配置后无告警
- test_rule_init_non_dict_condition_skipped: conditions 非 dict 项跳过 (P2-a)
- test_rule_init_bad_condition_wraps_config_error: 未知条件类型 -> ConfigError 带规则名 (P2-a)
- test_rule_init_bad_action_wraps_config_error: 未知动作名 -> ConfigError 带规则名 (P2-a)
- test_rule_process_action_skipped_not_executed: 动作 skip 不记 executed 不记历史 (P2-a)
- test_rule_condition_error_throttled_to_debug: 条件出错同因节流降 DEBUG (P2-a)
- test_rule_hourly_record_stale_date_allows_rerun: hourly 记录跨日允许再执行 (P2-a)
- test_rule_process_unknown_status_continues_without_marking
- test_rule_hourly_dedup_scope: hourly 仅「当日且同小时」去重, 跨小时/跨日均放行
- test_rule_daily_dedup_scope: daily 当日记录去重, 昨日记录放行(and→or 会让昨日也去重)
- test_rule_enabled_key_read: enabled 键名读取(显式 false 必须停用, 缺省 true)
- test_rule_once_dedup_with_record: once 有执行记录必须去重(无记录放行)
- test_rule_cooldown_sub_second_boundary: 0 < cooldown <= 1 秒的冷却同样生效
- test_rule_cooldown_bare_zero_means_no_cooldown: cooldown 裸 0(整数 0/字符串 "0")= 不冷却,
  构造期解析为 0.0 不抛错且运行时语义与 0S 一致(issue 26-11-08-0703)
- test_rule_cooldown_float_zero_means_no_cooldown: cooldown 浮点 0.0 = 不冷却(issue 26-11-08-1923,
  口径 A 谓词扩 float): 校验/构造两侧一致解析为 0.0 不裸抛, 非零浮点 3.5 校验侧照拒
- test_rule_never_not_deduped: never 有记录仍放行(对照 once 必须去重, 防 !=never 反转)
- test_rule_cooldown_expired_allows_rerun: C32 守阵 —— cooldown 合取是 and(改 or -> 冷却过期
  也不放行, 规则永久静默)
- test_rule_condition_exception_other_rules_unaffected: 条件异常 per-step 语义(G2/W2) —— 出错
  规则 verdict=error 本轮跳过, 其它规则照常执行; 全程无「停止后续规则」话术
- test_rule_evaluation_default_all_no_warning: evaluation 引擎参数(W4/D4) —— 键缺省 = all,
  零告警零行为变化
- test_rule_evaluation_first_match_placeholder_warning: evaluation=first_match 占位枚举 ——
  构造期显式 WARNING, 引擎按 all 处理(行为与 all 逐位一致)
"""

import os

import tempfile

from auto_qb.config import TrackerConfig

from auto_qb.core.modules import rules_mod

from auto_qb.rules.base import (
    VERDICT_DEDUPED,
    VERDICT_ERROR,
    VERDICT_EXECUTED,
    VERDICT_NO_MATCH,
    VERDICT_NO_OP,
    VERDICT_PENDING,
    ActionResult,
    BaseAction,
    Rule,
    RuleContext,
)

from auto_qb.rules.conditions import SizeCondition

from auto_qb.rules.actions import AddTagsAction

from auto_qb.infra import utils

from helpers import FakeClient, FakeTorrent, _hr_rule, make_ctx, make_manager


def _install_actions(rule, plugins):
    """测试注动作步(W3-B 起 process 迭代 self.steps, choose 块与普通动作同占一步):
    插件实例 -> 执行步(缺省 on_error), 取代此前直接赋 rule.actions 的注入形"""
    rule.steps = [("action", a, Rule._resolve_on_error(None)) for a in plugins]


def _load_rules(mgr, rules_config):
    """把规则配置灌进 manager 并走真实载入层 load_rules(两键检测/转未启用的被测单点)"""
    mgr.config.rules_config = rules_config
    rules = mgr.host.get("rules")
    rules.load_rules()
    return rules


class _FailingAction(BaseAction):
    """测试用: 总是失败的动作"""
    name = "fail"

    def execute(self, ctx):
        return ActionResult.fail("boom")


def test_rule_basic_process():
    """Rule 基本处理: 条件匹配执行动作, 返回 verdict=executed"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", size=100 * 1024**2)
        ctx = make_ctx(mgr, tor, client)
        rule = Rule(
            "g.test",
            {
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
            },
            mgr,
        )
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert ("add_tags", ["DONE"]) in client.calls


def test_rule_condition_not_met():
    """条件不满足: 不执行动作, verdict=no_match"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=1), client)
        rule = Rule(
            "g.test",
            {
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
            },
            mgr,
        )
        assert rule.process(ctx) == VERDICT_NO_MATCH
        assert client.calls == []


def test_rule_execute_once_dedup():
    """execute_once=once: 同一规则同一种子只执行一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", size=100 * 1024**2)
        ctx = make_ctx(mgr, tor, client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "once"}, mgr)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert ("add_tags", ["X"]) in client.calls
        # 第二次: 记录存在 -> 去重拦下
        assert rule.process(ctx) == VERDICT_DEDUPED
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_load_retired_stop_key_disables_rule():
    """载入检测 stop_following_rules_if -> 规则转未启用 + warning; 配置原内容原样保留(D1)

    变异面: 检测漏伪动作/漏规则级键、enabled 忘置 false、副本误改原配置, 任一都表现为
    退役键规则照跑(死语义复活)或配置内容被改写。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        spec = {"enabled": True, "actions": [{"add_tags": ["X"]}], "stop_following_rules_if": "never"}
        rules = _load_rules(mgr, {"g": {"r": spec}})
        rule = rules.rules[0]
        assert rule.enabled is False, "含退役键的规则载入即转未启用"
        assert rule not in rules.enabled_rules, "未启用规则不进 enabled_rules"
        assert spec["stop_following_rules_if"] == "never" and spec["enabled"] is True, \
            "配置原内容必须原样保留供改写(内存副本禁用, 不回写)"


def test_load_retired_ignore_key_warns_equivalent():
    """载入检测伪动作 ignore_next_action_error -> 转未启用 + warning 话术含等价新写法

    warning 必须给出 on_error: {policy: continue}(D1: 活键退场, 用了的用户规则停摆直到改写,
    话术不带等价写法用户无从改起); 内存副本剔除伪动作项使 Rule 构造可通过。
    """
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        spec = {
            "enabled": True,
            "actions": [{
                "ignore_next_action_error": "true"
            }, {
                "add_tags": ["X"]
            }],
        }
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.core.modules.rules_mod")
        handler = Grab(level=logging.WARNING)
        lg.addHandler(handler)
        lg.setLevel(logging.WARNING)
        try:
            rules = _load_rules(mgr, {"g": {"r": spec}})
        finally:
            lg.removeHandler(handler)
        assert rules.rules[0].enabled is False
        assert [a.name for a in rules.rules[0].actions] == ["add_tags"], \
            "载入副本须剔除伪动作项(引擎不再消费, 直接构造会 ConfigError)"
        msg = next(m for m in records if "g.r" in m)
        assert "已退役" in msg and "enabled=false" in msg, msg
        assert "on_error: {policy: continue}" in msg, f"warning 必须含等价新写法: {msg}"


def test_load_retired_nested_in_choose_branches():
    """载入检测 choose 分支 then/default 内的嵌套伪动作 -> 转未启用 + 嵌套剔除(issue 26-11-03-1120)

    退役检测/剔除曾只扫顶层 actions: choose.then 里的 ignore_next_action_error 通过校验
    (伪动作键面合法)但未被检测/剔除, 构造 Rule 按未知动作 ConfigError, 载入硬失败。
    未启用规则也照常构造 Rule, 嵌套伪动作必须真的从内存副本里剥掉。配置原内容原样保留。
    """
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        spec = {
            "enabled":
                True,
            "actions":
                [
                    {
                        "choose":
                            [
                                {
                                    "when": {
                                        "all": []
                                    },
                                    "then": [{
                                        "ignore_next_action_error": "true"
                                    }, {
                                        "add_tags": ["T"]
                                    }]
                                },
                            ],
                        "default": [{
                            "ignore_next_action_error": "true"
                        }, {
                            "add_tags": ["D"]
                        }],
                    }, {
                        "add_tags": ["X"]
                    }
                ],
        }
        # 检测单点: 嵌套伪动作同样命中(顶层无伪动作键)
        assert rules_mod.retired_control_keys_in(spec) == ("ignore_next_action_error", )
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.core.modules.rules_mod")
        handler = Grab(level=logging.WARNING)
        lg.addHandler(handler)
        lg.setLevel(logging.WARNING)
        try:
            rules = _load_rules(mgr, {"g": {"r": spec}})
        finally:
            lg.removeHandler(handler)
        assert rules.rules[0].enabled is False, "嵌套伪动作命中的规则载入即转未启用"
        assert rules.rules[0] not in rules.enabled_rules
        msg = next(m for m in records if "g.r" in m)
        assert "已退役" in msg and "on_error: {policy: continue}" in msg, msg
        # 内存副本: 嵌套伪动作剥掉(then/default 两侧), 顶层普通动作与 choose 结构保留
        rule = rules.rules[0]
        assert [a.name for a in rule.actions] == ["add_tags"], "顶层普通动作保留"
        choose_steps = [s for s in rule.steps if s[0] == "choose"]
        assert len(choose_steps) == 1, "choose 编排块保留"
        block = choose_steps[0][1]
        assert [[a.name for a in br.actions] for br in block.branches] == [["add_tags"]], \
            "分支 then 内伪动作剥掉, 普通动作保留"
        assert [a.name for a in block.default_actions] == ["add_tags"], \
            "块级 default 内伪动作剥掉, 普通动作保留"
        # 配置原内容原样保留供改写(内存副本改写, 不回写)
        assert spec["actions"][0]["choose"][0]["then"][0] == {"ignore_next_action_error": "true"}
        assert spec["enabled"] is True


def test_retired_detection_strip_nested_edge_shapes():
    """嵌套检测/剔除的边界形状(短路覆盖, issue 26-11-03-1120)

    - 非 dict 动作项: 检测跳过、剔除原样透传(与顶层容错同口径 P2-a);
    - choose 非 list / 分支非 dict / 分支无 then: 剔除侧原样透传(形状报错归校验器单点);
    - 多分支首个净第二个染: 检测不短路在首分支;
    - then 净 default 染: 检测落到块级 default 分支, 剔除剥 default。
    """
    spec = {
        "enabled":
            True,
        "actions":
            [
                "not-a-dict",
                {
                    "choose": "not-a-list"
                },
                {
                    "choose": ["not-a-dict", {
                        "when": {
                            "all": []
                        }
                    }]
                },
                {
                    "choose":
                        [
                            {
                                "when": {
                                    "all": []
                                },
                                "then": [{
                                    "add_tags": ["a"]
                                }]
                            },
                            {
                                "when": {
                                    "all": []
                                },
                                "then": [{
                                    "ignore_next_action_error": "true"
                                }]
                            },
                        ]
                },
                {
                    "choose": [{
                        "when": {
                            "all": []
                        },
                        "then": [{
                            "add_tags": ["a"]
                        }]
                    }],
                    "default": [{
                        "ignore_next_action_error": "true"
                    }]
                },
            ],
    }
    assert rules_mod.retired_control_keys_in(spec) == ("ignore_next_action_error", )
    # 顶层短路面: 多分支项在前会先命中(上面的 spec 走不到 default 分支), default 命中要单测:
    default_only = {
        "enabled":
            True,
        "actions":
            [
                {
                    "choose": [{
                        "when": {
                            "all": []
                        },
                        "then": [{
                            "add_tags": ["a"]
                        }]
                    }],
                    "default": [{
                        "ignore_next_action_error": "true"
                    }],
                }
            ],
    }
    assert rules_mod.retired_control_keys_in(default_only) == ("ignore_next_action_error", ), \
        "then 净 default 染: 检测必须落到块级 default 分支"
    assert rules_mod.retired_control_keys_in("not-a-spec") == (), "非 dict spec 检测返回空"
    stripped = rules_mod.disable_retired_rule_spec(spec)["actions"]
    assert stripped[0] == "not-a-dict", "非 dict 项原样透传"
    assert stripped[1] == {"choose": "not-a-list"}, "choose 非 list 原样透传(形状报错归校验器)"
    assert stripped[2] == {"choose": ["not-a-dict", {"when": {"all": []}}]}, "异形分支原样透传"
    b4 = stripped[3]["choose"]
    assert b4[0]["then"] == [{"add_tags": ["a"]}], "净分支零触碰"
    assert b4[1]["then"] == [], "染分支伪动作剥掉"
    assert stripped[4]["choose"][0]["then"] == [{"add_tags": ["a"]}], "default 染时 then 照常剥(净)"
    assert stripped[4]["default"] == [], "块级 default 染分支剥掉"
    # 配置原内容原样保留(内存副本改写)
    assert spec["actions"][3]["choose"][1]["then"] == [{"ignore_next_action_error": "true"}]
    assert spec["actions"][4]["default"] == [{"ignore_next_action_error": "true"}]


def test_load_retired_keys_warn_every_load():
    """每次载入都提示: 同一配置重复 load_rules(启动/热重载重建)每次都再报 warning"""
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        spec = {"enabled": True, "actions": [], "stop_following_rules_if": "always"}
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.core.modules.rules_mod")
        handler = Grab(level=logging.WARNING)
        lg.addHandler(handler)
        lg.setLevel(logging.WARNING)
        try:
            _load_rules(mgr, {"g": {"r": spec}})
            _load_rules(mgr, {"g": {"r": spec}})
        finally:
            lg.removeHandler(handler)
        hits = [m for m in records if "g.r" in m and "已退役" in m]
        assert len(hits) == 2, f"每次载入都必须提示(得 {len(hits)} 次): {records}"


def test_load_clean_rules_no_retired_warning():
    """无退役键的规则载入零告警且 enabled 原样(不带两键载入零行为变化的对照面)"""
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.core.modules.rules_mod")
        handler = Grab(level=logging.WARNING)
        lg.addHandler(handler)
        lg.setLevel(logging.WARNING)
        try:
            rules = _load_rules(
                mgr, {"g": {
                    "on": {
                        "enabled": True,
                        "actions": []
                    },
                    "off": {
                        "enabled": False,
                        "actions": []
                    }
                }}
            )
        finally:
            lg.removeHandler(handler)
        assert not records, f"无退役键不应有任何告警: {records}"
        assert [r.enabled for r in rules.rules] == [True, False], "enabled 语义不得被载入层改写"


def test_rule_condition_exception():
    """条件求值异常: verdict=error, 本条本轮跳过; 日志话术不再宣称「停止后续规则」(W1 话术修正)

    旧语义(2026-09-20 拍板「出错即停规则」)建立在「规则顺序链」上, 而现行执行模型是
    「每规则每种子独立任务」, 根本不存在「后续规则」链 —— W1 删掉死语义只保留真实半径:
    本条规则本轮不执行, 其它规则照常(plan 26-11-01-0106 G1)。
    """
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)

        class Boom:
            def match(self, ctx):
                raise RuntimeError("boom")

        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}]}, mgr)
        rule.condition_tree = ("all", [("leaf", Boom())])  # W3-A: 条件树内存表示
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.rules.base")
        handler = Grab(level=logging.DEBUG)
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
        try:
            assert rule.process(ctx) == VERDICT_ERROR
        finally:
            lg.removeHandler(handler)
        assert client.calls == [], "条件出错不得执行动作"
        err = next(m for m in records if "条件求值出错" in m and "g.test" in m)
        assert "本条规则本轮跳过" in err, f"话术必须只宣称真实半径: {err}"
        assert "停止后续规则" not in err, f"不得再宣称死语义: {err}"


def test_rule_condition_exception_other_rules_unaffected():
    """条件异常 per-step 语义(G2/W2): 出错规则 verdict=error 本轮跳过, 其它规则照常执行

    W1-A 已改话术, 本测补齐语义断言: 两规则同场, 坏条件规则 error、好规则 executed;
    全部日志里无「停止后续规则」话术(执行模型是每规则每种子独立任务, 不存在后续规则链)。
    """
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        class Boom:
            def match(self, ctx):
                raise RuntimeError("boom")

        bad = Rule("g.bad", {"actions": [{"add_tags": ["X"]}]}, mgr)
        bad.condition_tree = ("all", [("leaf", Boom())])  # W3-A: 条件树内存表示
        good = Rule("g.good", {"actions": [{"add_tags": ["Y"]}]}, mgr)
        tor = FakeTorrent(tags="")
        ctx_bad = make_ctx(mgr, tor, client)
        ctx_good = make_ctx(mgr, FakeTorrent(tags=""), client)

        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.rules.base")
        handler = Grab(level=logging.DEBUG)
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
        try:
            assert bad.process(ctx_bad) == VERDICT_ERROR, "坏条件规则: 本条本轮跳过"
            assert good.process(ctx_good) == VERDICT_EXECUTED, "他规则照常执行, 不受坏条件影响"
        finally:
            lg.removeHandler(handler)
        assert ("add_tags", ["Y"]) in client.calls and ("add_tags", ["X"]) not in client.calls
        assert any("本条规则本轮跳过" in m and "g.bad" in m for m in records), "出错规则有真实半径日志"
        assert not any("停止后续" in m for m in records), f"全程不得出现死语义话术: {records}"


def test_rule_multi_condition_and():
    """多条件 AND: 全部条件满足才执行动作; 任一不满足不执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "g.multi",
            {
                "conditions": [{
                    "size": ">=100MiB"
                }, {
                    "tags": "HHan"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
            },
            mgr,
        )
        # 全部满足 -> 执行
        ctx = make_ctx(mgr, FakeTorrent(tags="HHan", size=200 * 1024**2), client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert ("add_tags", ["DONE"]) in client.calls, f"应执行动作: {client.calls}"
        # tags 不满足 -> 不执行
        ctx2 = make_ctx(mgr, FakeTorrent(tags="OTHER", size=200 * 1024**2), client)
        assert rule.process(ctx2) == VERDICT_NO_MATCH
        # size 不满足 -> 不执行
        ctx3 = make_ctx(mgr, FakeTorrent(tags="HHan", size=50 * 1024**2), client)
        assert rule.process(ctx3) == VERDICT_NO_MATCH
        assert client.calls.count(("add_tags", ["DONE"])) == 1, "任一条件不满足不应执行动作"


def test_rule_state_group_combined():
    """状态组合条件(is_complete&is_uploading): 规则层仅对同时满足的状态执行动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "g.state",
            {
                "conditions": [{
                    "state": "is_complete&is_uploading"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
            },
            mgr,
        )
        # stalledUP: complete + uploading 均含 -> 执行
        ctx = make_ctx(mgr, FakeTorrent(state="stalledUP"), client)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert ("add_tags", ["DONE"]) in client.calls, f"stalledUP 应执行: {client.calls}"
        # pausedUP: complete 含但 uploading 不含 -> 不执行
        ctx2 = make_ctx(mgr, FakeTorrent(state="pausedUP"), client)
        assert rule.process(ctx2) == VERDICT_NO_MATCH
        # downloading: 均不含 -> 不执行
        ctx3 = make_ctx(mgr, FakeTorrent(state="downloading"), client)
        assert rule.process(ctx3) == VERDICT_NO_MATCH
        assert client.calls.count(("add_tags", ["DONE"])) == 1, "非上传完成状态不应执行"


def test_rule_action_failed_breaks_chain():
    """动作失败恒中断本条动作链(ignore_error 已随伪动作退役拆除, per-step on_error W2 引入)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule("g.chain", {"actions": []}, mgr)

        _install_actions(rule, [_FailingAction("x"), AddTagsAction(["AFTER"])])
        assert rule.process(ctx) == VERDICT_EXECUTED, "失败动作本身算已执行"
        assert ("add_tags", ["AFTER"]) not in client.calls, f"失败应中断动作链: {client.calls}"

        # 失败后允许重新执行(去重判据未触发时): 链中断只是本轮动作序列截断
        rule2 = Rule("g.chain2", {"actions": [{"add_tags": ["OK"]}]}, mgr)
        assert rule2.process(ctx) == VERDICT_EXECUTED


def test_rule_action_failed_stop():
    """动作失败: verdict=executed(失败动作计已执行), 本条动作链中断"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule(
            "g.test",
            {
                "actions": [{
                    "move_to": {
                        "path": ""
                    }
                }],  # 空 path -> fail
            },
            mgr,
        )
        assert rule.process(ctx) == VERDICT_EXECUTED


def test_rule_stop_if_never():
    """stop_following_rules_if 键已退役: 载入检测到即转未启用 + warning(D1), 引擎侧无 stop 语义"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        # 引擎侧: Rule 不再读取该键(无 stop_if 属性), 行为与不带键完全一致
        rule = Rule(
            "g.test",
            {
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
                "stop_following_rules_if": "never",
            },
            mgr,
        )
        assert not hasattr(rule, "stop_if"), "引擎不得再有 stop_if 消费面"
        assert rule.process(ctx) == VERDICT_EXECUTED


def test_rule_stop_if_all_actions_succeed():
    """stop_following_rules_if=all-actions-succeed 六档退役: 六档取值同样触发载入转未启用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        for value in (
            "conditions-met", "conditions-not-met", "action-failed", "all-actions-succeed", "always", "never"
        ):
            rule = Rule(
                "g.v",
                {
                    "actions": [{
                        "add_tags": ["A"]
                    }],
                    "stop_following_rules_if": value
                },
                mgr,
            )
            # 引擎侧六档全部等价: 只按本规则自身语义执行动作, 无任何链间控制流
            # (每档用新种子: add_tags 幂等 skip 会把 verdict 降成 no_op, 与六档等价性无关)
            fresh_ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
            assert rule.process(fresh_ctx) == VERDICT_EXECUTED, value


def test_rule_cooldown_dedup():
    """cooldown: 冷却期内同一种子不重复执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "cooldown": "1H"}, mgr)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert client.calls.count(("add_tags", ["X"])) == 1
        # 冷却期内再次执行被去重
        assert rule.process(ctx) == VERDICT_DEDUPED
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_hourly_dedup():
    """execute_once=hourly: 同小时同一种子不重复执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "hourly"}, mgr)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert rule.process(ctx) == VERDICT_DEDUPED
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_process_action_exception():
    """process: 动作 execute 抛异常 -> 容错为 fail, 规则仍按条件匹配语义停链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())

        class BoomAction:
            name = "boom"

            def execute(self, ctx):
                raise RuntimeError("boom")

        rule = Rule("g.test", {"actions": []}, mgr)
        _install_actions(rule, [BoomAction()])
        assert rule.process(ctx) == VERDICT_EXECUTED, "动作异常容错为 fail, 仍计已执行"


def test_rule_stop_if_conditions_not_met():
    """stop_following_rules_if=conditions-not-met 已退役: 条件不满足就只有本条不执行, 无停链语义"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=1), FakeClient())
        rule = Rule(
            "g.test",
            {
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
                "stop_following_rules_if": "conditions-not-met",
            },
            mgr,
        )
        assert rule.process(ctx) == VERDICT_NO_MATCH


def test_rule_daily_dedup():
    """execute_once=daily: 同日已执行 -> 去重"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "daily"}, mgr)
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert rule.process(ctx) == VERDICT_DEDUPED, "同日已执行 -> 去重"
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_actions_skip_non_dict():
    """Rule 构造: actions 列表中的非 dict 项 -> 跳过不解析"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        rule = Rule("g.test", {"actions": ["not-a-dict", {"add_tags": ["X"]}]}, mgr)
        assert len(rule.actions) == 1, "非 dict 动作项应被跳过"
        assert isinstance(rule.actions[0], AddTagsAction)


def test_reannounce_without_dedup_warns():
    """含 reannounce 动作但未配置 execute_once/cooldown -> 构造期 WARNING(封号风险提示); 配置后无告警

    不用 caplog: make_manager 的 setup_logging 会 clear root handlers(caplog 的捕获 handler 一并被清)。
    """
    import logging
    import os
    import tempfile

    from auto_qb.rules.base import Rule

    records = []

    class Grab(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    grab = Grab()
    grab.setLevel(logging.WARNING)
    base_logger = logging.getLogger("auto_qb.rules.base")
    base_logger.addHandler(grab)
    try:
        with tempfile.TemporaryDirectory() as td:
            mgr = make_manager(os.path.join(td, "state.json"))
            Rule("g.reann", {"actions": [{"reannounce": True}]}, mgr)
            Rule("g.reann2", {"actions": [{"reannounce": True}], "execute_once": "once"}, mgr)
    finally:
        base_logger.removeHandler(grab)
    assert any("封号风险" in m and "g.reann" in m for m in records), records
    assert not any("g.reann2" in m for m in records), "已配置去重不应告警"


def test_rule_init_non_dict_condition_skipped():
    """Rule 构造: conditions 中非 dict 项跳过(不崩溃不误建; P2-a 口径在树形下保持)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        rule = Rule("g.t", {"conditions": ["not-a-dict", {"size": ">=1MiB"}], "actions": []}, mgr)
        # W3-A: 扁平列表经单点漏斗包成隐式 all 树; 非 dict 项在建树时跳过, 仅剩 size 叶子
        assert rule.condition_tree[0] == "all"
        assert [kind for kind, _ in rule.condition_tree[1]] == ["leaf"]


def test_rule_init_bad_condition_wraps_config_error():
    """Rule 构造: 未知条件类型 -> ConfigError 携带规则名(包装原始异常)"""
    import pytest

    from auto_qb.config import ConfigError

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with pytest.raises(ConfigError) as ei:
            Rule("g.badcond", {"conditions": [{"no_such_cond": "x"}], "actions": []}, mgr)
        assert "g.badcond" in str(ei.value) and "no_such_cond" in str(ei.value)


def test_rule_init_bad_action_wraps_config_error():
    """Rule 构造: 未知动作名 -> ConfigError 携带规则名"""
    import pytest

    from auto_qb.config import ConfigError

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with pytest.raises(ConfigError) as ei:
            Rule("g.badact", {"actions": [{"no_such_action": True}]}, mgr)
        assert "g.badact" in str(ei.value)


def test_rule_process_action_skipped_not_executed():
    """动作返回 skip: 处理链继续但不记 executed(不记执行历史), 返回 handled=False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)  # 无标签 -> remove_tags 必 skip
        rule = Rule("g.test", {"actions": [{"remove_tags": ["nope"]}]}, mgr)
        assert rule.process(ctx) == VERDICT_NO_OP, "skip 不算 executed"
        assert not client.calls, "skip 动作不打 API"
        assert mgr.ctx.state.get_exec_record("g.test", ctx.hash) is None, "未执行不记历史"


def test_rule_condition_error_throttled_to_debug():
    """条件求值出错节流: 同因 5 分钟内第二次只 DEBUG(首次 ERROR), 不刷屏"""
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(), FakeClient())

        class Boom:
            def match(self, ctx):
                raise RuntimeError("boom-throttle")

        rule = Rule("g.test", {"actions": []}, mgr)
        rule.condition_tree = ("all", [("leaf", Boom())])  # W3-A: 条件树内存表示
        # 挂模块 logger 自建 handler(禁 caplog, 见 pitfalls/testing/log-capture.md)
        logger = logging.getLogger("auto_qb.rules.base")
        records = []

        class _Grab(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Grab(level=logging.DEBUG)
        old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            assert rule.process(ctx) == VERDICT_ERROR  # 首次: ERROR
            assert rule.process(ctx) == VERDICT_ERROR  # 同因紧邻第二次: 节流 DEBUG
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
        levels = [r.levelno for r in records if "条件求值出错" in r.getMessage()]
        assert logging.ERROR in levels, "首次必须 ERROR"
        assert logging.DEBUG in levels, "同因第二次必须降级 DEBUG"


def test_rule_hourly_record_stale_date_allows_rerun():
    """execute_once=hourly: 记录日期非当日(跨日) -> 同小时判据不拦, 允许再执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "hourly"}, mgr)
        mgr.ctx.state.record_execution("g.test", ctx.hash)  # 预置执行记录
        rec = mgr.ctx.state.get_exec_record("g.test", ctx.hash)
        rec["date"] = "2000-01-01"  # 篡改为昨日: 同小时判据失效 -> 允许再执行
        assert rule.process(ctx) == VERDICT_EXECUTED, "跨日记录不得拦下本次执行"
        assert ("add_tags", ["X"]) in client.calls


def test_rule_process_unknown_status_continues_without_marking():
    """动作返回未知状态(既非 ok/failed/skipped/pending): 后续动作照常执行, 但既不算成功也不算失败

    守的是处理链的**兜底分支**: 新增动作状态时若漏改这里, 规则会在该动作上静默中断 ——
    本条钉住「未知状态不记 executed」(verdict=no_op), 让漏改表现为可见的行为差异而不是静默截断。
    """
    from auto_qb.rules.base import ActionResult

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="test"), client)

        class _Weird:
            """只有 execute 的动作替身: 返回一个模型外的状态值"""

            name = "weird"

            def execute(self, ctx):
                return ActionResult("weird", "未知状态")

        rule = Rule("g.test", {"actions": [{"stop": True}]}, mgr)
        _install_actions(rule, [_Weird()])
        assert rule.process(ctx) == VERDICT_NO_OP, "未知状态不记 executed(既非成功也非失败)"


def test_rule_hourly_dedup_scope():
    """execute_once=hourly: 只有「当日且同小时」的记录去重, 跨小时/跨日均放行

    判据被改坏(字面量/日期键/小时键/比较方向/返回)会让 hourly 规则整段失效(每小时重复执行)
    或整段锁死(跨小时也不执行)。
    """
    from datetime import datetime

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule("g.hourly", {"actions": [{"add_tags": ["X"]}], "execute_once": "hourly"}, mgr)
        mgr.ctx.state.record_execution("g.hourly", ctx.hash)
        rec = mgr.ctx.state.get_exec_record("g.hourly", ctx.hash)
        now = datetime.now()
        rec["date"], rec["hour"] = now.date().isoformat(), now.hour
        assert rule._dedup_allowed(ctx) is False, "同一天同一小时 -> 去重"
        rec["hour"] = (now.hour + 1) % 24
        assert rule._dedup_allowed(ctx) is True, "跨小时 -> 放行"
        rec["hour"], rec["date"] = now.hour, "2000-01-01"
        assert rule._dedup_allowed(ctx) is True, "跨日 -> 放行"


def test_rule_daily_dedup_scope():
    """execute_once=daily: 当日记录去重, 昨日记录放行

    `and`→`or` 的改坏会让「昨日记录」也被当成当日 -> daily 规则永久静默。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule("g.daily", {"actions": [{"add_tags": ["X"]}], "execute_once": "daily"}, mgr)
        mgr.ctx.state.record_execution("g.daily", ctx.hash)
        rec = mgr.ctx.state.get_exec_record("g.daily", ctx.hash)
        assert rule._dedup_allowed(ctx) is False, "当日已执行 -> 去重"
        rec["date"] = "2000-01-01"
        assert rule._dedup_allowed(ctx) is True, "昨日记录 -> 放行"


def test_rule_pseudo_action_direct_construction_rejected():
    """伪动作 ignore_next_action_error 引擎不再消费: 绕过载入层直接构造 Rule -> ConfigError

    旧 ignore_next 状态机(初值/只作用一次/消费后复位)随伪动作退役删除; 载入层转未启用时
    会在内存副本里剔除伪动作项(见 test_load_retired_ignore_key_warns_equivalent), 因此只有
    绕过载入层的直构路径会撞上 —— 按未知动作 fail-fast, 不得静默吞掉。
    """
    import pytest

    from auto_qb.config import ConfigError

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with pytest.raises(ConfigError) as ei:
            Rule("g.pseudo", {"actions": [{"ignore_next_action_error": "true"}, {"add_tags": ["X"]}]}, mgr)
        assert "ignore_next_action_error" in str(ei.value) and "g.pseudo" in str(ei.value)


def test_rule_enabled_key_read():
    """enabled 键名: 显式 false 必须停用, 缺省为 true(键名漂移会让停用规则照跑)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert Rule("g.off", {"enabled": False, "actions": []}, mgr).enabled is False
        assert Rule("g.on", {"enabled": True, "actions": []}, mgr).enabled is True
        assert Rule("g.default", {"actions": []}, mgr).enabled is True


def test_rule_once_dedup_with_record():
    """execute_once=once: 无记录放行, 有记录必须去重(不得重跑)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule("g.once", {"actions": [{"add_tags": ["X"]}], "execute_once": "once"}, mgr)
        assert rule._dedup_allowed(ctx) is True, "无执行记录 -> 放行"
        mgr.ctx.state.record_execution("g.once", ctx.hash)
        assert rule._dedup_allowed(ctx) is False, "有执行记录 -> 去重"


def test_rule_cooldown_sub_second_boundary():
    """cooldown 边界: 0 < cooldown <= 1 秒的冷却同样生效

    `cooldown <= 0` 被改成 `<= 1`(或 `> 0` 改成 `> 1`)会让 0.5S 这类短冷却整段跳过,
    规则每轮重复执行。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule("g.cd", {"actions": [{"add_tags": ["X"]}], "cooldown": "0.5S"}, mgr)
        assert rule.cooldown == 0.5
        assert rule.process(ctx) == VERDICT_EXECUTED
        assert client.calls.count(("add_tags", ["X"])) == 1
        assert rule._dedup_allowed(ctx) is False, "0.5S 冷却期内必须去重"
        assert rule.process(ctx) == VERDICT_DEDUPED, "0.5S 冷却期内不得重复执行"
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_cooldown_bare_zero_means_no_cooldown():
    """cooldown 裸 0(整数 0 / 字符串 "0")= 不冷却(issue 26-11-08-0703): 构造期解析为 0.0 不抛错

    校验侧 _is_bare_zero 特判放行裸 0 后, Rule 构造期解析必须同口径(此前走裸 parse_time,
    裸 0 过了校验却在构造期抛裸 ValueError); 0 = 不冷却语义与 "0S" 写法一致。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        rule_int = Rule("g.cd0", {"actions": [{"add_tags": ["X"]}], "cooldown": 0}, mgr)
        assert rule_int.cooldown == 0.0, "整数 0(程序内构造)须解析为 0.0"
        rule_str = Rule("g.cd0s", {"actions": [{"add_tags": ["X"]}], "cooldown": "0"}, mgr)
        assert rule_str.cooldown == 0.0, "字符串裸 0 须解析为 0.0(与 '0S' 同义)"
        # 运行时语义: cooldown=0 -> 不冷却, 有执行记录仍放行(与 0S 写法一致)
        mgr.ctx.state.record_execution("g.cd0", ctx.hash)
        assert rule_int._dedup_allowed(ctx) is True, "cooldown 裸 0 = 不冷却, 有记录仍放行"


def test_rule_cooldown_float_zero_means_no_cooldown():
    """cooldown 浮点 0.0 = 不冷却(issue 26-11-08-1923, 口径 A 谓词扩 float): 构造期解析为 0.0 不裸抛

    程序内 dict 路径: 校验侧 _is_bare_zero 扩 float 0.0 后放行(此前经 parse_time 的
    empty_zero 分支同样放行, 口径不变), Rule 构造期原始值直传谓词解析为 0.0 —— 此前
    str(0.0)="0.0" 绕过特判裸抛 ValueError 绕过 ConfigError 契约。非零浮点 3.5 照走
    校验侧聚合报错(干净 ConfigError), 不得被顺手放行。
    """
    from auto_qb.config.validation import validate_config

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        # 校验/构造两侧一致: float 0.0 过校验 -> Rule 构造成功且 cooldown == 0.0
        errs = validate_config({"config": {"example_rules": {"r1": {"cooldown": 0.0, "actions": []}}}})
        assert errs == [], f"浮点 0.0 须过校验(不冷却): {errs}"
        rule_f = Rule("g.cd0f", {"actions": [{"add_tags": ["X"]}], "cooldown": 0.0}, mgr)
        assert rule_f.cooldown == 0.0, "浮点 0.0 须解析为 0.0, 不得裸抛 ValueError"
        # 运行时语义: 0.0 = 不冷却, 有执行记录仍放行
        mgr.ctx.state.record_execution("g.cd0f", ctx.hash)
        assert rule_f._dedup_allowed(ctx) is True, "cooldown 浮点 0.0 = 不冷却, 有记录仍放行"
        # 非零浮点照拒: 校验侧聚合报错(干净 ConfigError), 不放行
        errs = validate_config({"config": {"example_rules": {"r1": {"cooldown": 3.5, "actions": []}}}})
        assert "config.example_rules.r1.cooldown: 无效时间格式: 3.5" in errs, \
            "非零浮点 3.5 须被校验侧拒绝"


def test_rule_never_not_deduped():
    """execute_once=never: 有记录仍放行; 对照 once 有记录必须去重

    `== "never"` 反转成 `!= "never"` 时, 有记录的非 never 规则会在入口被整段放行(去重失效)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        never = Rule("g.never", {"actions": [{"add_tags": ["X"]}], "execute_once": "never"}, mgr)
        mgr.ctx.state.record_execution("g.never", ctx.hash)
        assert never._dedup_allowed(ctx) is True, "never 有记录仍放行"
        once = Rule("g.once", {"actions": [{"add_tags": ["Y"]}], "execute_once": "once"}, mgr)
        mgr.ctx.state.record_execution("g.once", ctx.hash)
        assert once._dedup_allowed(ctx) is False, "对照组: once 有记录必须去重"


def test_rule_cooldown_expired_allows_rerun():
    """C32 守阵: cooldown 的合取是 `and`(改成 `or` -> 有记录且 cooldown>0 时永不执行)

    记录 ts 早于 cooldown 窗口 -> 冷却已过, 必须放行; `and`→`or` 会让 `cooldown > 0` 单独成立,
    整条冷却分支恒返回 False(规则永久静默)。
    """
    from datetime import datetime

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        rule = Rule("g.cd", {"actions": [{"add_tags": ["X"]}], "cooldown": "1H"}, mgr)
        assert rule.cooldown == 3600
        mgr.ctx.state.record_execution("g.cd", ctx.hash)
        rec = mgr.ctx.state.get_exec_record("g.cd", ctx.hash)
        rec["ts"] = datetime.now().timestamp() - 7200  # 2 小时前 -> 1H 冷却早已过期
        assert rule._dedup_allowed(ctx) is True, "冷却已过期 -> 必须放行"


def test_rule_evaluation_default_all_no_warning():
    """evaluation 引擎参数(W4/D4): 键缺省 = all, 零告警零行为变化"""
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.rules.base")
        handler = Grab(level=logging.DEBUG)
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
        try:
            rule = Rule("g.ev", {"conditions": [{"size": ">=1MiB"}], "actions": [{"add_tags": ["X"]}]}, mgr)
            assert rule.evaluation == "all"
            assert rule.process(ctx) == VERDICT_EXECUTED
        finally:
            lg.removeHandler(handler)
        assert not [m for m in records if "evaluation" in m], "默认取值零告警"


def test_rule_evaluation_first_match_placeholder_warning():
    """evaluation=first_match 占位枚举(W4/D4 拍板不实现): 构造期显式 WARNING, 引擎按 all 处理
    —— 行为与 all 逐位一致(完整求值 + 全动作执行), 键位先占坑后续实现零改键面"""
    import logging

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        lg = logging.getLogger("auto_qb.rules.base")
        handler = Grab(level=logging.DEBUG)
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
        try:
            rule = Rule(
                "g.ev",
                {
                    "evaluation": "first_match",
                    "conditions": [{
                        "size": ">=1MiB"
                    }],
                    "actions": [{
                        "add_tags": ["X"]
                    }],
                },
                mgr,
            )
            assert rule.evaluation == "first_match"
            assert rule.process(ctx) == VERDICT_EXECUTED, "按 all 处理: 条件满足照常执行"
        finally:
            lg.removeHandler(handler)
        warn = next(m for m in records if "evaluation" in m)
        assert "first_match" in warn and "按 all 处理" in warn, f"占位话术: {warn}"
        assert ("add_tags", ["X"]) in client.calls

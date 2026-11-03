"""test_rules_core 测试计划: rules 框架核心逻辑(任务队列驱动架构)

规则统一为"种子级任务"(由 tracker rules 引用绑定): process_torrent 兼容入口已删除,
新增种子经 _refresh_torrents 匹配 tracker 后创建规则任务。规则核心语义
(条件评估 -> 去重 -> 动作执行)仍由 Rule.process(ctx) 承担(W1 返回值契约收口为单值
verdict), 本文件经种子绑定的规则列表逐个执行 process 验证核心逻辑(task_queue 调度细节见
test_rule_interval; stop_following_rules_if 已退役, plan 26-11-01-0106 W1)。

## 测试计划(每个测试函数一条)
- test_basic: 标签规则 + 变量替换
- test_category_auto_update_from_state: 分类按状态自动更新
- test_category_explicit_overwrite_false: 显式不覆盖分类
- test_hr_satisfied: HR 达标流程 + daily 去重(持久化后跨加载生效)
- test_stop_if_action_failed: stop 动作对已停种子幂等 skip, 后续动作仍执行
- test_dry_run: dry-run 不实际执行
- test_state_mapping: 状态条件语义判定(枚举属性名 is_*)
- test_tracker_rules_ref: tracker 规则引用 @rule_set / @rule_set.rule_name 过滤绑定; 重复引用运行时按名去重绑定恰一次(回归锁)
- test_rule_interval: 规则 interval 调度(任务队列到期才执行, interval=0 归一化每 tick)
- test_condition_tree_depth_limit: 条件组合树嵌套超上限拒绝 + 上限内恰好的嵌套放行(构造期兜底, 覆盖率第三轮 T0a)
- test_condition_tree_node_shape_guards: 条件节点必须单键字典(顶层与嵌套)/ all 必须是列表 -> ConfigError
- test_condition_tree_not_node_negation: not 孩子递归建树 + 求值取反语义(命中取反不命中)
- test_rule_conditions_non_dict_rejected: conditions 归一后非 dict(字符串透传) -> ConfigError
- test_choose_block_construction_guards: choose 分支非 dict / when 建树异常包装规则名 / then 非列表 -> ConfigError
- test_choose_step_pending_with_task: choose 分支动作 pending + 任务驱动 -> 断点记块后(si+1), VERDICT_PENDING
- test_choose_step_pending_without_task: choose 分支动作 pending 无任务(外部入口) -> 视为成功继续, VERDICT_EXECUTED
- test_choose_step_retry_requeues_block: choose 内动作 skip 后 retry 档 -> 断点记块首(si) + retry_delay 置入
- test_pick_choose_branch_without_trace: _pick_choose_branch trace=None 直调三态(命中分支/default/空操作)
- test_process_exception_traced_and_reraised: _process 未兜住异常 -> trace 记 exception 留痕后原样上抛
- test_trace_record_failure_swallowed: trace 记录失败只 DEBUG 吞掉, 不影响 verdict
"""
import os
import tempfile
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from auto_qb.config import ConfigError
from auto_qb.config.compat import CONDITION_TREE_MAX_DEPTH
from auto_qb.rules import registry
from auto_qb.rules.actions import AddCategoryAction
from auto_qb.rules.base import (
    VERDICT_EXECUTED,
    VERDICT_NO_MATCH,
    VERDICT_PENDING,
    VERDICT_RETRY,
    ActionResult,
    ChooseBlock,
    ChooseBranch,
    Rule,
)
from helpers import (
    FakeClient,
    FakeConfig,
    FakeTorrent,
    FakeTracker,
    _hr_rule,
    capture_logs,
    make_ctx,
    make_manager,
    seed_store,
)


def _run_rules(mgr, client, tor, dry_run=False):
    """按种子绑定的规则列表逐个执行 Rule.process(ctx)

    与 _handle_rule 同语义(ctx 由 make_ctx 构造: client 绑定 + tracker_conf 匹配 +
    store 对象身份直写); 返回任一规则是否执行了动作(verdict=executed/pending)。
    各规则任务是独立调度, 无跨规则控制流(stop_following_rules_if 已退役)。
    """
    # make_ctx 副作用: 设 tor.tracker_conf (首次 _match_tracker_conf). 必须先于
    # _rules_for_torrent, 否则 conf=None 直接抛 AttributeError (按项目哲学早暴露).
    make_ctx(mgr, tor, client, dry_run=dry_run)
    handled = False
    for rule in mgr.host.get("rules")._rules_for_torrent(tor):
        ctx = make_ctx(mgr, tor, client, dry_run=dry_run)
        verdict = rule.process(ctx)
        handled = handled or verdict in (VERDICT_EXECUTED, VERDICT_PENDING)
    return handled


def test_basic():
    """标签规则 + 变量替换"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file, tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", seeding_time=200000, uploaded=5 * 1024**2, ratio=0.6)
        handled = _run_rules(mgr, client, tor)
        assert handled, "add_site_tag 应处理种子"
        assert client.tags == {"HHan", "seed-3D"}, f"标签错误: {client.tags}"
        assert mgr.state.get("exec_history"), "应有执行历史"


def test_category_auto_update_from_state():
    """未设置 overwrite 时可更新此前自动设置的分类, 手动分类不覆盖"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)

        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        mgr.ctx.state.save()
        assert mgr.state["auto_categories"] == {"HASH123": "AUTO-A"}

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "AUTO-A"
        ctx2 = make_ctx(mgr2, tor, client2)
        assert AddCategoryAction({"format": "AUTO-B"}).execute(ctx2).is_ok
        assert client2.category == "AUTO-B"
        assert mgr2.state["auto_categories"]["HASH123"] == "AUTO-B"

        tor.category = "MANUAL"
        client2.calls.clear()
        assert AddCategoryAction({"format": "AUTO-C"}).execute(ctx2).is_skipped
        assert not any(call[0] == "set_category" for call in client2.calls)


def test_category_explicit_overwrite_false():
    """显式 overwrite: false 与缺省行为一致(自动分类可更新, 手动分类不覆盖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 当前分类 == 上次自动设置的分类: 显式 false 也应允许更新
        tor = FakeTorrent(category="AUTO-A")
        mgr.state["auto_categories"] = {"HASH123": "AUTO-A"}
        ctx = make_ctx(mgr, tor, client)
        result = AddCategoryAction({"format": "AUTO-B", "overwrite": False}).execute(ctx)
        assert result.is_ok, f"当前分类==上次自动设置, 显式 false 也应可更新: {result}"
        assert client.category == "AUTO-B", f"分类未更新: {client.category}"
        assert mgr.state["auto_categories"]["HASH123"] == "AUTO-B"
        # 手动分类: 不覆盖
        tor.category = "MANUAL"
        n_calls = len(client.calls)
        ctx2 = make_ctx(mgr, tor, client)
        result2 = AddCategoryAction({"format": "AUTO-C", "overwrite": False}).execute(ctx2)
        assert result2.is_skipped, f"手动分类不应被覆盖: {result2}"
        assert not any(c[0] == "set_category" for c in client.calls[n_calls:]), \
            f"不应新增 set_category: {client.calls[n_calls:]}"


def test_hr_satisfied():
    """hr satisfied 条件 + daily 去重(执行记录持久化后跨加载仍生效)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file, tracker_rules=["@example_rules.hr_done"])
        client = FakeClient()
        mgr.client = client
        # 3D@70%+12H: 需 seeding_time >= 3D + 12H
        tor = FakeTorrent(tags="HHan", seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=2.0)
        handled = _run_rules(mgr, client, tor)
        assert handled, "hr_done 应处理种子"
        assert client.category == "HR-DONE", f"分类错误: {client.category}"

        # daily 去重: 持久化执行记录, 重新加载后同一天不应重复执行
        mgr.ctx.state.save()
        client2 = FakeClient()
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules.hr_done"])  # 重新加载 state
        mgr2.client = client2
        handled2 = _run_rules(mgr2, client2, tor)
        assert handled2 is False, f"daily 去重应阻止重复执行: {client2.calls}"
        assert client2.calls == [], f"daily 去重失败: {client2.calls}"


def test_stop_if_action_failed():
    """种子已停止时 stop 动作幂等跳过(skipped 不算失败), 后续动作仍执行
    (函数名沿用历史, stop_following_rules_if 键已退役不再配置)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file, tracker_rules=["@example_rules.stop_low_ratio"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="HHan", ratio=0.1, state="stoppedDL")
        handled = _run_rules(mgr, client, tor)
        assert handled, "stop_low_ratio 应处理种子"
        assert ("stop", None) not in client.calls, f"已停止的种子不应重复 stop: {client.calls}"
        assert ("add_tags", ["low-ratio"]) in client.calls, f"应添加 low-ratio 标签: {client.calls}"


def test_dry_run():
    """dry-run 不产生任何客户端调用"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file, tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        _run_rules(mgr, client, tor, dry_run=True)
        assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"


def test_state_mapping():
    """状态条件语义: 直接用 TorrentState 枚举属性判定(pausedDL 算下载中, checkingUP 算做种中)"""
    from auto_qb.rules.conditions import StateCondition
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        ctx = make_ctx(mgr, FakeTorrent(state="stalledUP"), client)
        assert StateCondition("is_complete&is_uploading").match(ctx)
        ctx2 = make_ctx(mgr, FakeTorrent(state="pausedDL"), client)
        assert StateCondition("is_downloading").match(ctx2), "is_downloading 含暂停下载"
        assert StateCondition("is_complete").match(ctx2) is False
        ctx3 = make_ctx(mgr, FakeTorrent(state="checkingUP"), client)
        assert StateCondition("is_complete&is_uploading").match(ctx3), "is_complete 且 is_uploading 含 checkingUP"


def test_tracker_rules_ref():
    """tracker rules 引用 @rule_set / @rule_set.rule_name 过滤(种子绑定规则 = 引用解析)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        # 只引用 example_rules.add_site_tag 规则
        mgr = make_manager(state_file, tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        make_ctx(mgr, tor, client)  # 设 tor.tracker_conf 后, _rules_for_torrent 才能读
        bound = mgr.host.get("rules")._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"], \
            f"种子应只绑定被引用的规则: {[r.name for r in bound]}"
        # 重置 tags 避免第二段执行后影响第一段断言
        tor.tags = ""
        _run_rules(mgr, client, tor)
        assert client.tags == {"HHan", "seed-3D"}, f"仅应执行被引用的规则: {client.tags}"
        assert ("add_tags", ["low-ratio"]) not in client.calls, "未引用的规则不应执行"

        # 引用整个规则集
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules"])
        client2 = FakeClient()
        mgr2.client = client2
        tor.tracker_conf = None  # 强制 mgr2 重新 _match (tracker_rules 不同的 cfg)
        make_ctx(mgr2, tor, client2)
        bound = mgr2.host.get("rules")._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag", "example_rules.hr_done", "example_rules.stop_low_ratio"], \
            f"引用整个规则集: {[r.name for r in bound]}"
        tor.tags = ""
        _run_rules(mgr2, client2, tor)
        assert ("add_tags", ["low-ratio"]) in client2.calls, "引用整个规则集应包含 stop_low_ratio"

        # 重复引用回归锁(计划 26-10-02-1621): 同一 @ 引用写两遍, _resolve_refs 按规则名去重,
        # 种子绑定仍恰一次(校验层 W1 已拒收重复引用, 此处直接构造配置锁运行时去重语义不回归)
        mgr3 = make_manager(state_file, tracker_rules=["@example_rules", "@example_rules"])
        client3 = FakeClient()
        mgr3.client = client3
        tor.tracker_conf = None  # 强制 mgr3 重新 _match (tracker_rules 不同的 cfg)
        make_ctx(mgr3, tor, client3)
        bound = mgr3.host.get("rules")._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag", "example_rules.hr_done", "example_rules.stop_low_ratio"], \
            f"重复引用应去重, 每条规则绑定恰一次: {[r.name for r in bound]}"


def test_rule_interval():
    """规则 interval 调度(每条规则一个种子级任务, 到期才执行, interval=0 归一化为每 tick)"""
    from auto_qb.core.taskqueue import TaskQueue
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.trackers = {"HHan": FakeTracker("HHan", hr=_hr_rule(), rules=["@example_rules"])}
        cfg.rules_config = {
            "example_rules":
                {
                    "add_site_tag":
                        {
                            "enabled": True,
                            "conditions": [{
                                "trackers": "HHan"
                            }],
                            "actions": [{
                                "add_tags": ["HHan"]
                            }],
                        },
                    "stop_low_ratio":
                        {
                            "enabled": True,
                            "interval": "60S",
                            "conditions": [{
                                "upload_ratio": "<0.5"
                            }],
                            "actions": [{
                                "stop": True
                            }],
                        },
                }
        }
        client = FakeClient()
        mgr = make_manager(cfg=cfg, load_rules=True, client=client)
        tor = FakeTorrent(tags="", ratio=0.1, state="uploading")
        client.torrents["HASH123"] = tor  # 种子级规则任务通过 store 快照读取
        seed_store(mgr)
        # 手动任务队列路径不经 make_ctx, 需显式绑定 tracker_conf(trackers 条件依赖)
        tor.tracker_conf = mgr.config.trackers["HHan"]
        # 模拟 _create_torrent_tasks: 为种子创建规则任务(独立队列, 排除 refresh 任务干扰)
        tq = TaskQueue()
        rules = mgr.host.get("rules")._rules_for_torrent(tor)
        assert {r.name for r in rules} == {"example_rules.add_site_tag", "example_rules.stop_low_ratio"}
        now = time.time()  # 统一时间起点: add_task 与 due 使用同一 now
        for r in rules:
            tq.add_task(mgr.host.get("rules")._create_rule_task(r, tor.hash), now=now)

        # 第 1 轮: 所有规则任务初始立即到期, 均执行
        assert tq.run_due(False, now=now) == 2, "第 1 轮应全部到期"
        assert ("stop", None) in client.calls, f"第 1 轮应 stop: {client.calls}"

        # 第 2 轮(1s 后): add_site_tag(interval 归一化 1s)到期, stop_low_ratio(60s)未到期
        client.calls.clear()
        assert tq.run_due(False, now=now + 1) == 1, "第 2 轮应只到期 add_site_tag"
        assert ("stop", None) not in client.calls, f"interval 未到期不应再次 stop: {client.calls}"
        assert client.tags == {"HHan"}, f"add_site_tag 应仍执行: {client.tags}"

        # 60s 后: stop_low_ratio 到期再次执行
        # (模拟用户重新开始种子: 直接改种子对象状态即同步快照(store 内为同一对象身份)。
        #  !A 系 S3(A2): 第 1 轮的 stop 已在 own_writes 登记「停/起未回流」; 本例用**模拟时钟**
        #   推进 60s、期间并未跑同步, 故登记不会自动逐出(TTL 走真实单调钟)。生产里 sync 每 1.5s
        #   一轮、状态回流即逐出, 不会拦到 60s 后的这次 stop —— 此处补清登记即等价于那次回流。)
        tor.state = "uploading"
        mgr.store.own_writes.clear()
        client.calls.clear()
        assert tq.run_due(False, now=now + 60) >= 1, "stop_low_ratio 应到期"
        assert ("stop", None) in client.calls, f"60s 后应再次 stop: {client.calls}"


# ---------------------------------------------------------------------------
# 条件组合树 / choose 编排块守卫簇(覆盖率第三轮 T0a): 构造期 ConfigError 兜底 +
# choose 步 pending/retry 断点语义 + trace 留痕失败面。只补测试, 产品代码零改动。
# ---------------------------------------------------------------------------


class _FixedCond:
    """内存直构哑条件(测试桩, 与 _trace_cond_name 注释的「哑条件」同形): match 返回固定值"""
    def __init__(self, result):
        self.result = result

    def match(self, ctx):
        return self.result


@contextmanager
def _fake_rule_actions():
    """临时注册三个假动作(pending/skip/fail)供 choose 步断点语义用例使用

    registry 是全局面: 用完 ACTIONS/ACTION_ENTRIES 双字典同弹(与 test_registry 同纪律,
    残条目会污染派生守卫与其它用例)。
    """
    @registry.register_action
    class T0aPending:
        name = "t0a_pending"

        def __init__(self, spec):
            pass

        def execute(self, ctx):
            return ActionResult.pending("等待异步")

    @registry.register_action
    class T0aSkip:
        name = "t0a_skip"

        def __init__(self, spec):
            pass

        def execute(self, ctx):
            return ActionResult.skip("跳过")

    @registry.register_action
    class T0aFail:
        name = "t0a_fail"

        def __init__(self, spec):
            pass

        def execute(self, ctx):
            return ActionResult.fail("炸了")

    try:
        yield
    finally:
        for n in ("t0a_pending", "t0a_skip", "t0a_fail"):
            registry.ACTIONS.pop(n, None)
            registry.ACTION_ENTRIES.pop(n, None)


def test_condition_tree_depth_limit():
    """条件组合树嵌套超上限拒绝(构造期兜底); 上限内恰好的嵌套放行(守卫刻度校准)"""
    node = {"state": "is_complete"}
    for _ in range(CONDITION_TREE_MAX_DEPTH):  # 16 层 not -> 叶子落在第 17 层, 超限
        node = {"not": node}
    with pytest.raises(ConfigError, match="嵌套超过上限"):
        Rule("t0a-deep", {"conditions": node}, None)

    ok = {"state": "is_complete"}
    for _ in range(CONDITION_TREE_MAX_DEPTH - 1):  # 15 层 not -> 叶子恰在第 16 层, 放行
        ok = {"not": ok}
    rule = Rule("t0a-deep-ok", {"conditions": ok}, None)
    assert rule.condition_tree[0] == "not", "上限内嵌套应正常建树"


def test_condition_tree_node_shape_guards():
    """条件节点形状兜底: 多键字典(顶层与嵌套同拦)/ all 非列表 -> ConfigError"""
    with pytest.raises(ConfigError, match="单键字典"):
        Rule("t0a-shape", {"conditions": {"state": "is_complete", "hr": "satisfied"}}, None)
    with pytest.raises(ConfigError, match="单键字典"):
        Rule("t0a-shape", {"conditions": {"all": [{"state": "is_complete", "hr": "satisfied"}]}}, None)
    with pytest.raises(ConfigError, match="必须是列表"):
        Rule("t0a-shape", {"conditions": {"all": "not-a-list"}}, None)


def test_condition_tree_not_node_negation():
    """not 孩子递归建树 + 求值取反: 命中取反成不命中, 不命中取反成命中"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "t0a-not",
            {
                "conditions": {
                    "not": {
                        "state": "is_complete"
                    }
                },
                "actions": [{
                    "add_tags": ["t0a-not"]
                }]
            },
            mgr,
        )
        ctx_hit = make_ctx(mgr, FakeTorrent(), client)  # stalledUP: is_complete True
        assert rule.matches(ctx_hit) is False, "内层命中, not 应取反成 False"
        ctx_miss = make_ctx(mgr, FakeTorrent(state="pausedDL"), client)  # is_complete False
        assert rule.matches(ctx_miss) is True, "内层不命中, not 应取反成 True"


def test_rule_conditions_non_dict_rejected():
    """conditions 归一后非 dict(normalize 对字符串原样透传) -> ConfigError"""
    with pytest.raises(ConfigError, match="conditions 必须是组合树字典"):
        Rule("t0a-nd", {"conditions": "is_complete"}, None)


def test_choose_block_construction_guards():
    """choose 构造期兜底三分支: 分支非 dict / when 建树异常包装规则名 / then 非列表"""
    with pytest.raises(ConfigError, match=r"choose 分支\[0\]: 必须是字典"):
        Rule("t0a-ch", {"actions": [{"choose": ["junk"]}]}, None)
    with pytest.raises(ConfigError, match=r"choose 分支\[0\]\.when"):
        Rule("t0a-ch", {"actions": [{"choose": [{"when": {"no_such_cond_t0a": 1}, "then": []}]}]}, None)
    with pytest.raises(ConfigError, match=r"choose 分支\[0\]\.then: 必须是列表"):
        Rule("t0a-ch", {"actions": [{"choose": [{"when": {"state": "is_complete"}, "then": "oops"}]}]}, None)


def test_choose_step_pending_with_task():
    """choose 分支动作 pending + 任务驱动: 断点记块后(si+1), VERDICT_PENDING"""
    with tempfile.TemporaryDirectory() as td, _fake_rule_actions():
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "t0a-ch-pending",
            {"actions": [{
                "choose": [{
                    "when": {
                        "state": "is_complete"
                    },
                    "then": [{
                        "t0a_pending": None
                    }]
                }]
            }]},
            mgr,
        )
        tor = FakeTorrent()
        ctx = make_ctx(mgr, tor, client)
        task = SimpleNamespace(resume_index=None, attempt=0, retry_delay=None)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_PENDING
        assert task.resume_index == 1, "choose 步粒度: 断点记块后(si=0 -> 1)"


def test_choose_step_pending_without_task():
    """choose 分支动作 pending 无任务(外部入口, 不应发生): 视为成功继续, VERDICT_EXECUTED"""
    with tempfile.TemporaryDirectory() as td, _fake_rule_actions():
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "t0a-ch-pending2",
            {"actions": [{
                "choose": [{
                    "when": {
                        "state": "is_complete"
                    },
                    "then": [{
                        "t0a_pending": None
                    }]
                }]
            }]},
            mgr,
        )
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert rule.process(ctx) == VERDICT_EXECUTED, "无任务 pending 应按成功继续收场"


def test_choose_step_retry_requeues_block():
    """choose 内 retry(W3-B 口径): skip 动作放行到 retry 档动作 -> 断点记块首(si), retry_delay 置入 task"""
    with tempfile.TemporaryDirectory() as td, _fake_rule_actions():
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "t0a-ch-retry",
            {
                "actions":
                    [
                        {
                            "choose":
                                [
                                    {
                                        "when": {
                                            "state": "is_complete"
                                        },
                                        "then":
                                            [
                                                {
                                                    "t0a_skip": None
                                                },  # skip: 穿过整条分派链落回循环(613 假向)
                                                {
                                                    "t0a_fail": None,
                                                    "on_error": {
                                                        "policy": "retry",
                                                        "retries": 2,
                                                        "backoff": 60
                                                    }
                                                },
                                            ],
                                    }
                                ]
                        }
                    ]
            },
            mgr,
        )
        ctx = make_ctx(mgr, FakeTorrent(), client)
        task = SimpleNamespace(resume_index=None, attempt=0, retry_delay=None)
        ctx.task = task
        assert rule.process(ctx) == VERDICT_RETRY
        assert task.resume_index == 0, "choose 内 retry: 断点记块首, 续跑整块重新求值"
        assert task.retry_delay == 60.0, "retry_delay 应由 _dispatch_result 置入 task"


def test_pick_choose_branch_without_trace():
    """_pick_choose_branch trace=None 直调三态(process 恒传 trace, 无 trace 面由直调补)"""
    rule = Rule("t0a-pick", {}, None)
    hit = ChooseBlock([ChooseBranch(("leaf", _FixedCond(True)), [], [])], [], [])
    assert rule._pick_choose_branch(hit, None, "log", trace=None)[2] == 0, "命中分支返回分支序号"
    to_default = ChooseBlock([ChooseBranch(("leaf", _FixedCond(False)), [], [])], ["d-act"], [{"policy": "stop"}])
    actions, _, label = rule._pick_choose_branch(to_default, None, "log", trace=None)
    assert label == "default" and actions == ["d-act"], "无命中走 default"
    to_none = ChooseBlock([ChooseBranch(("leaf", _FixedCond(False)), [], [])], [], [])
    actions, on_errors, label = rule._pick_choose_branch(to_none, None, "log", trace=None)
    assert label is None and actions == [] and on_errors == [], "无命中且无 default = 空操作"


def test_process_exception_traced_and_reraised(monkeypatch):
    """_process 未兜住的异常: trace 记 verdict=exception 留痕后原样上抛(引擎 _run_rule 记 ERROR)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule("t0a-boom", {"actions": [{"add_tags": ["t0a-boom"]}]}, mgr)
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)

        seen = {}

        def boom(*a, **k):
            raise RuntimeError("record 炸了")

        monkeypatch.setattr(mgr.ctx.state, "record_execution", boom)
        monkeypatch.setattr(mgr.ctx.state, "record_rule_trace", lambda name, h, entry: seen.update(entry))
        with pytest.raises(RuntimeError, match="record 炸了"):
            rule.process(ctx)
        assert seen.get("verdict") == "exception", "异常路径应先留痕再上抛"
        assert "RuntimeError" in seen.get("error", ""), "异常串应进 trace.error"


def test_trace_record_failure_swallowed(monkeypatch):
    """trace 记录失败只 DEBUG 吞掉(排障辅助不反噬执行), verdict 照常返回"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        rule = Rule(
            "t0a-notrace",
            {
                "conditions": {
                    "state": "is_downloading"
                },
                "actions": [{
                    "add_tags": ["x"]
                }]
            },
            mgr,
        )
        ctx = make_ctx(mgr, FakeTorrent(), client)  # stalledUP: is_downloading False -> NO_MATCH

        def boom(*a, **k):
            raise RuntimeError("trace 写入炸了")

        monkeypatch.setattr(mgr.ctx.state, "record_rule_trace", boom)
        with capture_logs("auto_qb.rules.base") as cap:
            verdict = rule.process(ctx)
        assert verdict == VERDICT_NO_MATCH, "trace 失败不应改变 verdict"
        assert any("trace 记录失败" in m for m in cap.messages), f"应有 DEBUG 留痕: {cap.messages}"

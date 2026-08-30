"""rules/base 模块测试: ActionResult / RuleContext / Rule 处理语义"""
import os
import tempfile

from auto_qb.config import TrackerConfig
from auto_qb.rules.base import ActionResult, Rule, RuleContext
from auto_qb.rules.conditions import SizeCondition
from auto_qb.rules.actions import AddTagsAction
from helpers import FakeClient, FakeTorrent, _hr_rule, make_ctx, make_manager


def test_action_result_states():
    """ActionResult 三态与判定属性"""
    ok = ActionResult.ok("成功")
    fail = ActionResult.fail("失败")
    skip = ActionResult.skip("跳过")
    assert ok.is_ok and not ok.is_failed and not ok.is_skipped
    assert fail.is_failed and fail.message == "失败"
    assert skip.is_skipped
    assert "success" in repr(ok)


def test_rule_context_required_seeding_time():
    """RuleContext: required_seeding_time 取匹配 tracker 的 hr 原始值"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        assert ctx.required_seeding_time == "3D"
        # replace_vars 替换 ${required_seeding_time}
        assert ctx.replace_vars("seed-${required_seeding_time}") == "seed-3D"
        assert ctx.replace_vars("plain") == "plain"


def test_rule_context_tracker_urls_and_confs():
    """RuleContext: tracker_urls / matched_tracker_confs / matched_tracker_names"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.tracker_urls() == ["https://tracker.hhanclub.net/announce.php"]
        confs = ctx.matched_tracker_confs()
        assert len(confs) == 1 and confs[0].name == "HHan"
        assert ctx.matched_tracker_names() == ["HHan"]


def test_rule_context_describe():
    """RuleContext.describe: 多行描述"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        desc = ctx.describe()
        assert "种子" in desc and "HASH123" in desc and "HHan" in desc


def test_rule_context_hr_checks():
    """RuleContext: check_hr_condition / check_hr_satisfied"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.matched_tracker_confs()[0]
        # dlratio: 0.7 >= 0.7 满足
        assert ctx.check_hr_condition(conf)
        # satisfied: 需要做种 >= 3D+12H
        assert not ctx.check_hr_satisfied(conf)
        tor.seeding_time = 3 * 86400 + 12 * 3600 + 5
        assert ctx.check_hr_satisfied(conf)
        # dlsize 条件
        hr = _hr_rule(condition=("dlsize", 100 * 1024**2))
        conf2 = TrackerConfig(
            name="X",
            domains=["x.com"],
            tags=[],
            remove_tags=[],
            upload_speed_limit=None,
            download_speed_limit=None,
            hr=hr,
            rules=[],
            remove_similar_tags=False,
        )
        ctx2 = make_ctx(mgr, FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=0), client)
        assert ctx2.check_hr_condition(conf2)


def test_rule_basic_process():
    """Rule 基本处理: 条件匹配执行动作, 返回 (handled, stop)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", size=100 * 1024**2)
        ctx = make_ctx(mgr, tor, client)
        rule = Rule(
            "g.test",
            {
                "conditions": [{"size": ">=1MiB"}],
                "actions": [{"add_tags": ["DONE"]}],
                "stop_following_rules_if": "always",
            },
            mgr,
        )
        handled, stop = rule.process(ctx)
        assert handled and stop
        assert ("add_tags", ["DONE"]) in client.calls


def test_rule_condition_not_met():
    """条件不满足: 不执行动作, stop 取决于 stop_following_rules_if=conditions-met"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=1), client)
        rule = Rule(
            "g.test",
            {
                "conditions": [{"size": ">=1MiB"}],
                "actions": [{"add_tags": ["DONE"]}],
                "stop_following_rules_if": "conditions-met",
            },
            mgr,
        )
        handled, stop = rule.process(ctx)
        assert not handled and not stop
        assert client.calls == []


def test_rule_execute_once_dedup():
    """execute_once=once: 同一规则同一种子只执行一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", size=100 * 1024**2)
        ctx = make_ctx(mgr, tor, client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "once"}, mgr)
        h1, _ = rule.process(ctx)
        assert h1
        assert ("add_tags", ["X"]) in client.calls
        # 第二次: 记录存在 -> 不执行(handled=False)
        h2, _ = rule.process(ctx)
        assert not h2
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_ignore_next_action_error():
    """ignore_next_action_error=true: 忽略下一条动作错误继续执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", category=""), client)
        rule = Rule(
            "g.test",
            {"actions": [{"remove_category": ""}, {"ignore_next_action_error": "true"}, {"add_tags": ["AFTER"]}]},
            mgr,
        )
        # remove_category 空分类 skip(非 fail); 验证 ignore 标志不影响 skip
        handled, _ = rule.process(ctx)
        assert handled
        assert ("add_tags", ["AFTER"]) in client.calls


def test_rule_condition_exception():
    """条件执行异常: 返回 (False, False) 不中断规则链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(), FakeClient())

        class Boom:
            def match(self, ctx):
                raise RuntimeError("boom")

        rule = Rule("g.test", {"actions": []}, mgr)
        rule.conditions = [Boom()]
        handled, stop = rule.process(ctx)
        assert handled is False and stop is False


def test_rule_action_failed_stop():
    """stop_following_rules_if=action-failed: 动作失败时停链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        rule = Rule(
            "g.test",
            {
                "actions": [{"move_to": {"path": ""}}],  # 空 path -> fail
                "stop_following_rules_if": "action-failed",
            },
            mgr,
        )
        handled, stop = rule.process(ctx)
        assert handled and stop, "动作失败仍算处理过, 且 stop=True"

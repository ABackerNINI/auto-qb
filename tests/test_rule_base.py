"""test_rule_base 测试计划: rules/base ActionResult/RuleContext/Rule

## 测试计划(每个测试函数一条)
- test_action_result_states: ActionResult 状态语义
- test_rule_context_required_seeding_time: required_seeding_time 解析
- test_rule_context_tracker_urls_and_confs: tracker URL 与配置解析
- test_rule_context_describe: 上下文描述生成
- test_rule_context_hr_checks: HR 达标判定(做种时间/分享率)
- test_rule_basic_process: 规则基本执行流程(条件满足 -> 动作执行)
- test_rule_condition_not_met: 条件未满足 -> 不执行动作
- test_rule_execute_once_dedup: execute_once=once 去重
- test_rule_ignore_next_action_error: 忽略下一个动作错误
- test_rule_condition_exception: 条件异常 -> 不执行
- test_rule_action_failed_stop: 动作失败且 stop 配置 -> 停止
- test_rule_stop_if_never: stop_following_rules_if=never -> 不停止
- test_rule_stop_if_all_actions_succeed: 全部动作成功 -> 停止
- test_rule_cooldown_dedup: cooldown 冷却期内去重
- test_rule_hourly_dedup: hourly 同小时去重
- test_rule_context_files_cached: files() 惰性缓存只拉一次
- test_rule_context_tracker_urls_empty: 无 tracker -> 未匹配描述
- test_base_condition_init: 基类 __init__ 保存 spec(子类继承)
- test_rule_context_required_seeding_time_no_hr: 无 hr 配置 -> 空字符串
- test_rule_context_describe_tracker_error: tracker 拉取异常 -> 站点显示未知
- test_rule_context_hr_dlratio_not_met: 下载比例未达标 -> 触发/满足均 False
- test_rule_context_hr_satisfied_by_ratio: 分享率达标 -> satisfied True
- test_rule_process_action_exception: 动作异常 -> 容错为 fail 继续
- test_rule_stop_if_conditions_not_met: 未匹配且 conditions-not-met -> 停链
- test_rule_daily_dedup: execute_once=daily 同日已执行 -> 去重
- test_rule_context_hr_no_conf: tracker 无 hr 配置 -> 触发/满足均 False
- test_rule_context_hr_dlsize_not_met: dlsize 下载量未达标 -> 触发 False
- test_rule_actions_skip_non_dict: actions 中非 dict 项 -> 跳过
"""
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
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
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
                "conditions": [{
                    "size": ">=1MiB"
                }],
                "actions": [{
                    "add_tags": ["DONE"]
                }],
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
            {"actions": [{
                "remove_category": ""
            }, {
                "ignore_next_action_error": "true"
            }, {
                "add_tags": ["AFTER"]
            }]},
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
                "actions": [{
                    "move_to": {
                        "path": ""
                    }
                }],  # 空 path -> fail
                "stop_following_rules_if": "action-failed",
            },
            mgr,
        )
        handled, stop = rule.process(ctx)
        assert handled and stop, "动作失败仍算处理过, 且 stop=True"


def test_rule_stop_if_never():
    """stop_following_rules_if=never: 动作成功但不停链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
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
        handled, stop = rule.process(ctx)
        assert handled and not stop


def test_rule_stop_if_all_actions_succeed():
    """stop_following_rules_if=all-actions-succeed: 全成功停链, 有失败不停链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        # 全部成功 -> stop
        rule_ok = Rule(
            "g.ok",
            {
                "actions": [{
                    "add_tags": ["A"]
                }],
                "stop_following_rules_if": "all-actions-succeed"
            },
            mgr,
        )
        handled, stop = rule_ok.process(ctx)
        assert handled and stop
        # 有动作失败(空 path) -> 不停链
        rule_fail = Rule(
            "g.fail",
            {
                "actions": [{
                    "move_to": {
                        "path": ""
                    }
                }],
                "stop_following_rules_if": "all-actions-succeed"
            },
            mgr,
        )
        handled, stop = rule_fail.process(ctx)
        assert handled and not stop


def test_rule_cooldown_dedup():
    """cooldown: 冷却期内同一种子不重复执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "cooldown": "1H"}, mgr)
        h1, _ = rule.process(ctx)
        assert h1
        assert client.calls.count(("add_tags", ["X"])) == 1
        # 冷却期内再次执行被去重
        h2, _ = rule.process(ctx)
        assert not h2
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_hourly_dedup():
    """execute_once=hourly: 同小时同一种子不重复执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "hourly"}, mgr)
        h1, _ = rule.process(ctx)
        assert h1
        h2, _ = rule.process(ctx)
        assert not h2
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_context_files_cached():
    """RuleContext.files: 惰性缓存, 多次调用只拉取一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.files() == []
        assert ctx.files() == []
        assert client.files_calls == 1, "files 应只拉取一次(缓存)"


def test_base_condition_init():
    """BaseCondition.__init__: 子类不定义 __init__ 时继承保存 spec"""
    from auto_qb.rules.base import BaseCondition

    class C(BaseCondition):
        name = "c"

        def match(self, ctx):
            return True

    c = C({"k": "v"})
    assert c.spec == {"k": "v"}


def test_rule_context_required_seeding_time_no_hr():
    """required_seeding_time: 匹配 tracker 无 hr 配置 -> 空字符串"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        assert ctx.required_seeding_time == ""
        assert ctx.replace_vars("seed-${required_seeding_time}") == "seed-", "空值替换为空串"


def test_rule_context_describe_tracker_error():
    """describe: tracker 拉取抛异常 -> 站点显示未知(不中断)"""
    def boom(hash_):
        raise RuntimeError("tracker api failed")

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = boom
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert "未知" in ctx.describe()


def test_rule_context_hr_dlratio_not_met():
    """check_hr_condition/check_hr_satisfied: 下载比例未达标 -> 均 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=100 * 1024**2, seeding_time=999 * 86400)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.matched_tracker_confs()[0]
        assert ctx.check_hr_condition(conf) is False, "0.5 < 0.7 不满足触发条件"
        assert ctx.check_hr_satisfied(conf) is False, "触发条件不满足则 satisfied 为 False"


def test_rule_context_hr_satisfied_by_ratio():
    """check_hr_satisfied: 分享率达标即可满足, 即使做种时长不足"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": _hr_rule(required_share_ratio=1.0)})
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=0, ratio=2.0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.matched_tracker_confs()[0]
        assert ctx.check_hr_satisfied(conf), "分享率 2.0 >= 1.0 应算 satisfied"


def test_rule_process_action_exception():
    """process: 动作 execute 抛异常 -> 容错为 fail, 规则仍按条件匹配语义停链"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())

        class BoomAction:
            name = "boom"

            def __init__(self):
                self.ignore_error = False

            def execute(self, ctx):
                raise RuntimeError("boom")

        rule = Rule("g.test", {"actions": []}, mgr)
        rule.actions = [BoomAction()]
        handled, stop = rule.process(ctx)
        assert handled, "动作异常容错为 fail, handled 仍为 True"
        assert stop, "默认 stop_if=conditions-met: 条件匹配过即停链"


def test_rule_stop_if_conditions_not_met():
    """stop_following_rules_if=conditions-not-met: 未匹配时停链"""
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
        handled, stop = rule.process(ctx)
        assert not handled and stop, "未匹配且 stop_if=conditions-not-met -> (False, True)"


def test_rule_daily_dedup():
    """execute_once=daily: 同日已执行 -> 去重"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", size=100 * 1024**2), client)
        rule = Rule("g.test", {"actions": [{"add_tags": ["X"]}], "execute_once": "daily"}, mgr)
        h1, _ = rule.process(ctx)
        assert h1
        h2, _ = rule.process(ctx)
        assert not h2, "同日已执行 -> 去重"
        assert client.calls.count(("add_tags", ["X"])) == 1


def test_rule_context_tracker_urls_empty():
    """RuleContext: 无 tracker 时 matched_tracker_names 为空、describe 显示未匹配"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: []  # 无 tracker
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.tracker_urls() == []
        assert ctx.matched_tracker_confs() == []
        assert ctx.matched_tracker_names() == []
        assert "未匹配" in ctx.describe()


def test_rule_context_hr_no_conf():
    """check_hr_condition/check_hr_satisfied: tracker 无 hr 配置 -> 均 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        conf = ctx.matched_tracker_confs()[0]
        assert conf.hr is None
        assert ctx.check_hr_condition(conf) is False, "无 hr 配置不应满足触发"
        assert ctx.check_hr_satisfied(conf) is False, "无 hr 配置不应满足要求"


def test_rule_context_hr_dlsize_not_met():
    """check_hr_condition: dlsize 条件下载量未达标 -> False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_kw={"hr": _hr_rule(condition=("dlsize", 100 * 1024**2))},
        )
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=0), client)
        conf = ctx.matched_tracker_confs()[0]
        assert ctx.check_hr_condition(conf) is False, "下载量 50MiB < 100MiB 不应满足"
        assert ctx.check_hr_satisfied(conf) is False


def test_rule_actions_skip_non_dict():
    """Rule 构造: actions 列表中的非 dict 项 -> 跳过不解析"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        rule = Rule("g.test", {"actions": ["not-a-dict", {"add_tags": ["X"]}]}, mgr)
        assert len(rule.actions) == 1, "非 dict 动作项应被跳过"
        assert isinstance(rule.actions[0], AddTagsAction)

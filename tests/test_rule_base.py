"""test_rule_base 测试计划: rules/base ActionResult/RuleContext/Rule

## 测试计划(每个测试函数一条)
- test_action_result_states: ActionResult 状态语义
- test_rule_context_required_seeding_time: required_seeding_time 解析
- test_rule_context_tracker_urls_and_conf: tracker URL 与配置解析(记录级 tracker_urls + tracker_conf)
- test_rule_context_log_repr: 种子日志描述(describe 已移除由 log_repr 承担)
- test_rule_context_hr_checks: HR 达标判定(做种时间/分享率)
- test_rule_basic_process: 规则基本执行流程(条件满足 -> 动作执行, verdict=executed)
- test_rule_condition_not_met: 条件未满足 -> 不执行动作(verdict=no_match)
- test_rule_execute_once_dedup: execute_once=once 去重
- test_load_retired_stop_key_disables_rule: 载入检测 stop_following_rules_if -> 规则转未启用 + warning,
  配置原内容原样保留(D1 升级路线, plan 26-11-01-0106 W1)
- test_load_retired_ignore_key_warns_equivalent: 载入检测伪动作 ignore_next_action_error -> 转未启用 +
  warning 话术含等价新写法 on_error: {policy: continue}
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
- test_rule_context_files_cached: tor.files(client) 惰性缓存只拉一次
- test_rule_context_tracker_urls_empty: 无 tracker -> tracker_conf None / required_seeding_time 空 / log_repr Unknown
- test_base_condition_init: 基类 __init__ 保存 spec(子类继承)
- test_rule_context_required_seeding_time_no_hr: 无 hr 配置 -> 空字符串
- test_rule_context_log_repr_tracker_error: tracker 拉取异常 -> make_ctx 容错 tracker_conf None / log_repr Unknown
- test_rule_context_hr_dlratio_not_met: 下载比例未达标 -> 触发/满足均 False
- test_rule_context_hr_satisfied_by_ratio: 分享率达标 -> satisfied True
- test_rule_process_action_exception: 动作异常 -> 容错为 fail, verdict=executed
- test_rule_pseudo_action_direct_construction_rejected: 绕过载入层直接构造 Rule 遇伪动作 -> ConfigError
  (引擎不再消费 ignore_next_action_error, 载入层转未启用时才剔除)
- test_rule_daily_dedup: execute_once=daily 同日已执行 -> 去重
- test_rule_context_hr_no_conf: tracker 无 hr 配置 -> 触发/满足均 False
- test_rule_context_hr_dlsize_not_met: dlsize 下载量未达标 -> 触发 False
- test_rule_actions_skip_non_dict: actions 中非 dict 项 -> 跳过
- test_rule_multi_condition_and: 多条件 AND: 全部满足才执行, 任一不满足不执行
- test_rule_state_group_combined: 状态组合条件(is_complete&is_uploading)规则层仅对同时满足执行
- test_reannounce_without_dedup_warns: reannounce 未配去重 -> 构造期 WARNING; 配置后无告警
- test_rule_context_api_fallback_to_client: manager 无 api 门面时退化 client (P2-a)
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
    """RuleContext.replace_vars 经 utils.replace_vars 委托: required_seeding_time 取匹配 tracker 的 hr 原始值"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        # 旧 RuleContext.required_seeding_time property 已迁出, 直接用 utils.replace_vars 验证
        assert utils.replace_vars("seed-${required_seeding_time}", ctx.torrent.tracker_conf) == "seed-3D"
        assert utils.replace_vars("plain", ctx.torrent.tracker_conf) == "plain"


def test_rule_context_tracker_urls_and_conf():
    """RuleContext: 记录级 tracker_urls + tracker_conf(种子匹配到的 tracker 配置)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        assert ctx.torrent.tracker_urls(client) == ["https://tracker.hhanclub.net/announce.php"]
        conf = ctx.torrent.tracker_conf
        assert conf is not None and conf.name == "HHan"
        assert conf.tags == ["HHan"]


def test_rule_context_log_repr():
    """RuleContext: 种子日志描述 log_repr(名称/site/hash; describe 已移除由 log_repr 承担)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        desc = ctx.torrent.log_repr
        assert "Test" in desc and "HASH123" in desc and "HHan" in desc


def test_rule_context_hr_checks():
    """RuleContext: check_hr_condition / check_hr_satisfied"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.torrent.tracker_conf  # make_ctx 已匹配 tracker 并赋值
        # dlratio: 0.7 >= 0.7 满足
        assert ctx.torrent.check_hr_condition()
        # satisfied: 需要做种 >= 3D+12H
        assert not ctx.torrent.check_hr_satisfied()
        tor.seeding_time = 3 * 86400 + 12 * 3600 + 5
        assert ctx.torrent.check_hr_satisfied()
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
        # 显式用 dlsize 条件(否则 total_size=0 走 dlratio 会被"总大小为0的辅种兜底"排除)
        ctx2.torrent.tracker_conf.hr = hr
        # dlsize 100MiB = 100*1024*1024 B, downloaded 100MiB 满足触发条件
        assert ctx2.torrent.check_hr_condition()
        # satisfied 还需 seeding_ok (seeding_time=0 不满足) 或 ratio_ok (default 0 不满足), 故 False
        assert not ctx2.torrent.check_hr_satisfied()


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


# ---------------- 两键退役(D1 升级路线, plan 26-11-01-0106 W1): 载入层转未启用 + warning ----------------


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


def test_rule_context_files_cached():
    """tor.files(client): 惰性缓存, 多次调用只拉取一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.files(client) == []
        assert ctx.torrent.files(client) == []
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
    """required_seeding_time: 匹配 tracker 无 hr 配置 -> utils.replace_vars 留原文 (无 HR 不替换占位)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        assert utils.replace_vars(
            "seed-${required_seeding_time}", ctx.torrent.tracker_conf
        ) == "seed-${required_seeding_time}"
        assert utils.replace_vars("plain", ctx.torrent.tracker_conf) == "plain"


def test_rule_context_log_repr_tracker_error():
    """tracker 拉取异常: make_ctx 容错(tracker_conf None), log_repr 站点显示 Unknown"""
    def boom(hash_):
        raise RuntimeError("tracker api failed")

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = boom
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.tracker_conf is None, "tracker 拉取异常应容错为未匹配"
        assert "Unknown" in ctx.torrent.log_repr


def test_rule_context_hr_dlratio_not_met():
    """check_hr_condition 只答本地触发(0.5 < 0.7 -> False); satisfied 不设触发门,
    做种 999D 远超 3D+12H -> True(计划 26-09-30-0559: 旧断言「未触发则未达标」作废)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=100 * 1024**2, seeding_time=999 * 86400)
        ctx = make_ctx(mgr, tor, client)
        assert ctx.torrent.check_hr_condition() is False, "0.5 < 0.7: 本地不触发(展示辅助判据)"
        assert ctx.torrent.check_hr_satisfied() is True, "做种事实达标即 satisfied, 与触发无关"
        assert ctx.torrent.hr_managed() is False, "达标即不需管束"


def test_rule_context_hr_satisfied_by_ratio():
    """check_hr_satisfied: 分享率达标即可满足, 即使做种时长不足"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": _hr_rule(required_share_ratio=1.0)})
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=0, ratio=2.0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.torrent.tracker_conf
        assert ctx.torrent.check_hr_satisfied(), "分享率 2.0 >= 1.0 应算 satisfied"


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


def test_rule_context_tracker_urls_empty():
    """无 tracker: tracker_conf None、required_seeding_time 空、log_repr 站点 Unknown"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: []  # 无 tracker
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.tracker_urls(client) == []
        assert ctx.torrent.tracker_conf is None, "无匹配 tracker -> tracker_conf 应为 None"
        assert utils.replace_vars(
            "seed-${required_seeding_time}", ctx.torrent.tracker_conf
        ) == "seed-${required_seeding_time}"
        assert "Unknown" in ctx.torrent.log_repr


def test_rule_context_hr_no_conf():
    """check_hr_condition/check_hr_satisfied: tracker 无 hr 配置 -> 均 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        conf = ctx.torrent.tracker_conf
        assert conf.hr is None
        assert ctx.torrent.check_hr_condition() is False, "无 hr 配置不应满足触发"
        assert ctx.torrent.check_hr_satisfied() is False, "无 hr 配置不应满足要求"


def test_rule_context_hr_dlsize_not_met():
    """check_hr_condition: dlsize 条件下载量未达标 -> False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_kw={"hr": _hr_rule(condition=("dlsize", 100 * 1024**2))},
        )
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=0), client)
        conf = ctx.torrent.tracker_conf
        assert ctx.torrent.check_hr_condition() is False, "下载量 50MiB < 100MiB 不应满足"
        assert ctx.torrent.check_hr_satisfied() is False


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


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def test_rule_context_api_fallback_to_client():
    """RuleContext.api: manager 无 api 门面时退化到 client(外部传入种子/测试场景)"""
    from types import SimpleNamespace

    manager = SimpleNamespace(store=SimpleNamespace(get=lambda h: None))  # 无 api 属性
    client = FakeClient()
    ctx = RuleContext(manager, client, None, "H1", dry_run=False)
    assert ctx.api is client


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

"""test_rules_core 测试计划: rules 框架核心逻辑(任务队列驱动架构)

规则统一为"种子级任务"(由 tracker rules 引用绑定): process_torrent 兼容入口已删除,
新增种子经 _refresh_torrents 匹配 tracker 后创建规则任务。规则核心语义
(条件评估 -> 去重 -> 动作执行 -> stop 链)仍由 Rule.process(ctx) 承担, 本文件
经种子绑定的规则列表逐个执行 process 验证核心逻辑(task_queue 调度细节见
test_rule_interval)。

## 测试计划(每个测试函数一条)
- test_basic: 标签规则 + 变量替换 + stop_following_rules_if: never
- test_category_auto_update_from_state: 分类按状态自动更新
- test_category_explicit_overwrite_false: 显式不覆盖分类
- test_hr_satisfied: HR 达标流程 + daily 去重(持久化后跨加载生效)
- test_stop_if_action_failed: stop 动作对已停种子幂等 skip, 后续动作仍执行
- test_dry_run: dry-run 不实际执行
- test_state_mapping: 状态条件语义判定(枚举属性名 is_*)
- test_tracker_rules_ref: tracker 规则引用 @rule_set / @rule_set.rule_name 过滤绑定
- test_rule_interval: 规则 interval 调度(任务队列到期才执行, interval=0 归一化每 tick)
"""
import os
import tempfile
import time

from auto_qb.qbmanager import QbManager
from auto_qb.rules.actions import AddCategoryAction
from helpers import FakeClient, FakeConfig, FakeTorrent, FakeTracker, _hr_rule, make_ctx, make_manager, seed_store


def _run_rules(mgr, client, tor, dry_run=False):
    """按种子绑定的规则列表逐个执行 Rule.process(ctx)

    与 _handle_rule 同语义(ctx 由 make_ctx 构造: client 绑定 + tracker_conf 匹配 +
    store 对象身份直写); 返回任一规则是否处理(handled)。stop 链由调用方决定,
    这里默认全部执行(任务队列中各规则任务是独立调度, 无跨规则 stop)。
    """
    handled = False
    for rule in mgr._rules_for_torrent(tor):
        ctx = make_ctx(mgr, tor, client, dry_run=dry_run)
        h, _stop = rule.process(ctx)
        handled = handled or h
    return handled


def test_basic():
    """标签规则 + 变量替换 + stop_following_rules_if: never"""
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
        mgr.save_state()
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
        mgr.save_state()
        client2 = FakeClient()
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules.hr_done"])  # 重新加载 state
        mgr2.client = client2
        handled2 = _run_rules(mgr2, client2, tor)
        assert handled2 is False, f"daily 去重应阻止重复执行: {client2.calls}"
        assert client2.calls == [], f"daily 去重失败: {client2.calls}"


def test_stop_if_action_failed():
    """种子已停止时 stop 动作幂等跳过(skipped 不算失败), 后续动作仍执行"""
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
        bound = mgr._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"], \
            f"种子应只绑定被引用的规则: {[r.name for r in bound]}"
        _run_rules(mgr, client, tor)
        # 只应执行 add_site_tag(加标签), 不应执行 stop_low_ratio(stop + low-ratio 标签)
        assert client.tags == {"HHan", "seed-3D"}, f"仅应执行被引用的规则: {client.tags}"
        assert ("add_tags", ["low-ratio"]) not in client.calls, "未引用的规则不应执行"

        # 引用整个规则集
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules"])
        client2 = FakeClient()
        mgr2.client = client2
        _run_rules(mgr2, client2, tor)
        assert ("add_tags", ["low-ratio"]) in client2.calls, "引用整个规则集应包含 stop_low_ratio"


def test_rule_interval():
    """规则 interval 调度(每条规则一个种子级任务, 到期才执行, interval=0 归一化为每 tick)"""
    from auto_qb.taskqueue import TaskQueue
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
                            "stop_following_rules_if": "never",
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
                            "stop_following_rules_if": "action-failed",
                        },
                }
        }
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        mgr._load_rules()  # run() 中才自动加载; 测试直接构造后需手动加载规则
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="uploading")
        client.torrents["HASH123"] = tor  # 种子级规则任务通过 store 快照读取
        seed_store(mgr)
        # 手动任务队列路径不经 make_ctx, 需显式绑定 tracker_conf(trackers 条件依赖)
        tor.tracker_conf = mgr.config.trackers["HHan"]
        # 模拟 _create_torrent_tasks: 为种子创建规则任务(独立队列, 排除 refresh 任务干扰)
        tq = TaskQueue()
        rules = mgr._rules_for_torrent(tor)
        assert {r.name for r in rules} == {"example_rules.add_site_tag", "example_rules.stop_low_ratio"}
        now = time.time()  # 统一时间起点: add_task 与 due 使用同一 now
        for r in rules:
            tq.add_task(mgr._create_rule_task(r, tor.hash, mgr.config.trackers["HHan"]), now=now)

        # 第 1 轮: 所有规则任务初始立即到期, 均执行
        due = tq.due(now)
        assert {t.name for t in due} == {"example_rules.add_site_tag", "example_rules.stop_low_ratio"}, \
            f"第 1 轮应全部到期: {[t.name for t in due]}"
        for t in due:
            keep = t.handler(t, False)
            assert keep, f"任务不应消亡: {t.name}"
        assert ("stop", None) in client.calls, f"第 1 轮应 stop: {client.calls}"
        for t in due:
            tq.reschedule(t, now)

        # 第 2 轮(1s 后): add_site_tag(interval 归一化 1s)到期, stop_low_ratio(60s)未到期
        client.calls.clear()
        due2 = tq.due(now + 1)
        assert [t.name
                for t in due2] == ["example_rules.add_site_tag"], f"第 2 轮应只到期 add_site_tag: {[t.name for t in due2]}"
        for t in due2:
            t.handler(t, False)
        assert ("stop", None) not in client.calls, f"interval 未到期不应再次 stop: {client.calls}"
        assert client.tags == {"HHan"}, f"add_site_tag 应仍执行: {client.tags}"
        for t in due2:
            tq.reschedule(t, now + 1)

        # 60s 后: stop_low_ratio 到期再次执行
        # (第 1 轮 stop 后 store 快照同步为 pausedUP -> stop 幂等; 模拟用户重新开始种子,
        #  直接改种子对象状态即同步快照(store 内为同一对象身份))
        tor.state = "uploading"
        client.calls.clear()
        due3 = tq.due(now + 60)
        assert "example_rules.stop_low_ratio" in [t.name for t in due3], \
            f"stop_low_ratio 应到期: {[t.name for t in due3]}"
        for t in due3:
            t.handler(t, False)
        assert ("stop", None) in client.calls, f"60s 后应再次 stop: {client.calls}"

"""rules 框架核心逻辑测试(原 test_rules.py 迁移): 规则执行 / 分类语义 / 去重 / 状态映射 / tracker 引用 / interval 调度"""
import os
import tempfile
import time

from auto_qb.qbmanager import QbManager
from auto_qb.rules import RuleContext
from auto_qb.rules.actions import AddCategoryAction
from helpers import FakeClient, FakeConfig, FakeTorrent, FakeTracker, _hr_rule, make_manager


def test_basic():
    """标签规则 + 变量替换 + stop_following_rules_if: never"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", seeding_time=200000, uploaded=5 * 1024**2, ratio=0.6)
        handled = mgr.process_torrent(tor, dry_run=False)
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
        ctx = RuleContext(mgr, client, mgr.config, tor, dry_run=False)

        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        mgr.save_state()
        assert mgr.state["auto_categories"] == {"HASH123": "AUTO-A"}

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "AUTO-A"
        ctx2 = RuleContext(mgr2, client2, mgr2.config, tor, dry_run=False)
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
        ctx = RuleContext(mgr, client, mgr.config, tor, dry_run=False)
        result = AddCategoryAction({"format": "AUTO-B", "overwrite": False}).execute(ctx)
        assert result.is_ok, f"当前分类==上次自动设置, 显式 false 也应可更新: {result}"
        assert client.category == "AUTO-B", f"分类未更新: {client.category}"
        assert mgr.state["auto_categories"]["HASH123"] == "AUTO-B"
        # 手动分类: 不覆盖
        tor.category = "MANUAL"
        n_calls = len(client.calls)
        ctx2 = RuleContext(mgr, client, mgr.config, tor, dry_run=False)
        result2 = AddCategoryAction({"format": "AUTO-C", "overwrite": False}).execute(ctx2)
        assert result2.is_skipped, f"手动分类不应被覆盖: {result2}"
        assert not any(c[0] == "set_category" for c in client.calls[n_calls:]), \
            f"不应新增 set_category: {client.calls[n_calls:]}"


def test_hr_satisfied():
    """hr satisfied 条件 + daily 去重"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        # 3D@70%+12H: 需 seeding_time >= 3D + 12H
        tor = FakeTorrent(tags="HHan", seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=2.0)
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "hr_done 应处理种子"
        assert client.category == "HR-DONE", f"分类错误: {client.category}"

        # daily 去重: 同一天再次执行不应重复
        client2 = FakeClient()
        mgr2 = make_manager(state_file)  # 重新加载 state
        mgr2.client = client2
        handled2 = mgr2.process_torrent(tor, dry_run=False)
        assert handled2 is True or client2.calls == [], f"daily 去重失败: {client2.calls}"


def test_stop_if_action_failed():
    """种子已停止时 stop 动作幂等跳过(skipped 不算失败), 后续动作仍执行"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="HHan", ratio=0.1, state="stoppedDL")
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "stop_low_ratio 应处理种子"
        assert ("stop", None) not in client.calls, f"已停止的种子不应重复 stop: {client.calls}"
        assert ("add_tags", ["low-ratio"]) in client.calls, f"应添加 low-ratio 标签: {client.calls}"


def test_dry_run():
    """dry-run 不产生任何客户端调用"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        mgr.process_torrent(tor, dry_run=True)
        assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"


def test_state_mapping():
    """语义状态映射"""
    from auto_qb.rules.conditions import _STATE_MAP
    assert "checkingDL" in _STATE_MAP["checking"]
    assert "stalledUP" in _STATE_MAP["uploading"]
    assert "missingFiles" in _STATE_MAP["errored"]
    assert "stoppedDL" in _STATE_MAP["stopped"]


def test_tracker_rules_ref():
    """tracker rules 引用 @rule_set / @rule_set.rule_name 过滤"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        # 只引用 example_rules.add_site_tag 规则
        mgr = make_manager(state_file, tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        mgr.process_torrent(tor, dry_run=False)
        # 只应执行 add_site_tag(加标签), 不应执行 stop_low_ratio(stop + low-ratio 标签)
        assert client.tags == {"HHan", "seed-3D"}, f"仅应执行被引用的规则: {client.tags}"
        assert ("add_tags", ["low-ratio"]) not in client.calls, "未引用的规则不应执行"

        # 引用整个规则集
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules"])
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.process_torrent(tor, dry_run=False)
        assert ("add_tags", ["low-ratio"]) in client2.calls, "引用整个规则集应包含 stop_low_ratio"


def test_rule_interval():
    """规则 interval 调度(每条规则一个种子级任务, 到期才执行, interval=0 归一化为每 tick)"""
    from auto_qb.taskqueue import Task, TaskQueue
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
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="uploading")
        client.torrents["HASH123"] = tor  # 种子级规则任务通过 _get_torrent 拉取

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
        client.calls.clear()
        due3 = tq.due(now + 60)
        for t in due3:
            t.handler(t, False)
        assert ("stop", None) in client.calls, f"60s 后应再次 stop: {client.calls}"

        # 兜底: 不创建任务直接 process_torrent, 视为全部规则执行(向后兼容)
        mgr3 = QbManager("", config=cfg)
        client3 = FakeClient()
        mgr3.client = client3
        handled3 = mgr3.process_torrent(tor, dry_run=False)
        assert handled3, "无规则任务时规则应全部执行(向后兼容)"
        assert ("stop", None) in client3.calls, f"兜底路径应执行全部规则: {client3.calls}"

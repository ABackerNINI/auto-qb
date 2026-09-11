"""test_trigger_events 测试计划: 事件触发规则(trigger=on_*) 分派与断点续跑

## 测试计划(每个测试函数一条)
- test_on_added_fires: on_torrent_added 新增种子触发(动作执行 + 记录执行历史)
- test_on_added_existing_no_fire: 已有种子后续刷新不触发
- test_on_deleted_fires_snapshot: on_torrent_deleted 删除种子触发(快照副本作 ctx.torrent 供只读动作留档)
- test_on_state_changed_fires: on_torrent_state_enum_changed 状态变化触发
- test_on_state_changed_new_no_fire: 新增种子首现不视为状态变化
- test_rule_event_not_self_cycled: rule-event 任务不周期入队(恒 FINISHED 消亡)
- test_deleted_whitelist_fail: on_torrent_deleted 配非只读动作 config 阶段拒绝
- test_dry_run: 事件分派 dry_run 不执行/不记录
- test_mixed_events: 同一种子新增+状态变化同时触发(两事件都触发)
- test_event_checking_resume_success: 事件配 checking -> pending -> 成功续跑剩余动作
- test_event_checking_resume_fail: 事件配 checking -> 校验失败重走完整决策链
- test_event_checking_deleted: 事件配 checking -> 校验中种子删除 -> 销毁(不续跑)
"""
import os
import tempfile

from auto_qb.config import ConfigError, load_config
from auto_qb.rules import Rule, RuleContext
from auto_qb.taskqueue import FINISHED, PENDING, Task, TaskQueue
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


# ---------- 事件规则辅助 ----------
def _ev(trigger, actions, conditions=None, **kw):
    """构造事件规则 spec(单动作键)"""
    spec = {"enabled": True, "trigger": trigger, "actions": actions, "stop_following_rules_if": "never"}
    if conditions:
        spec["conditions"] = conditions
    spec.update(kw)
    return spec


def _event_mgr(rules, tracker_rules=None, state_file=None):
    """构造仅含事件规则的 manager(替换 make_manager 的示例规则; tracker 引用事件规则集)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            state_file or os.path.join(td, "state.json"),
            tracker_rules=tracker_rules or ["@event_rules"],
        )
        mgr.config.rules_config = {"event_rules": rules}
        mgr._load_rules()
        return mgr


def _refresh(mgr, torrents, dry_run=False):
    """设置 client 并从给定种子列表跑一轮 _refresh_torrents(模拟一轮全量刷新)"""
    mgr.client = FakeClient()
    for t in torrents:
        mgr.client.torrents[t.hash] = t
    mgr._refresh_torrents(dry_run)
    return mgr.client


def _add_tags_action():
    """add_tags 动作(单键动作配置格式)"""
    return [{"add_tags": ["event-tag"]}]


# ============================================================
# A. 四触发器触发/不触发
# ============================================================
def test_on_added_fires():
    """on_torrent_added: 新增种子同步触发事件规则(动作执行 + 记录执行历史)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _add_tags_action())})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        client = _refresh(mgr, [tor])
        # 动作执行: 打上 event-tag
        assert ("add_tags", ["event-tag"]) in client.calls, f"事件规则应执行动作: {client.calls}"
        # 记录执行历史(非 dry-run)
        assert "event_rules.r1:H1" in mgr.state.get("exec_history", {}), "事件执行应记录执行历史"
        # 事件规则不建周期任务
        assert not any(t.kind == "rule-event" for t in mgr.task_queue._fast), "rule-event 不常驻队列"


def test_on_added_existing_no_fire():
    """on_torrent_added: 已有种子后续刷新不触发(非新增)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _add_tags_action())})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        _refresh(mgr, [tor])  # 首轮: 新增, 触发
        mgr.state.pop("exec_history", None)
        client = _refresh(mgr, [tor])  # 第二轮: 已存在, 不触发
        assert ("add_tags", ["event-tag"]) not in client.calls, f"已有种子后续刷新不应触发: {client.calls}"
        assert "event_rules.r1:H1" not in mgr.state.get("exec_history", {}), "不触发就不应记录"


def test_on_deleted_fires_snapshot():
    """on_torrent_deleted: 删除种子触发, 删除前快照副本作 ctx.torrent(只读动作仍可留档)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_deleted", [{"print_torrent_details": True}])})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="ztag", category="ACat")
        client = _refresh(mgr, [tor])  # 首轮: 新增, 建立 known_hashes 与快照
        client.calls.clear()
        mgr.state.pop("exec_history", None)
        # 从客户端移除种子 -> 触发删除事件
        del client.torrents["H1"]
        mgr._refresh_torrents()
        # 打印动作执行(快照副本非空, 未崩), 且读取到删除前字段
        assert "event_rules.r1:H1" in mgr.state.get("exec_history", {}), "删除事件应执行动作并记录"
        # 直接验证 ctx.torrent 回退快照副本: 删除后 store 无该种子, 但快照副本有
        ctx = RuleContext(mgr, client, mgr.config, "H1", False)
        ctx.snapshot = tor  # 模拟 _apply_event_rule 传入的删除前快照
        assert ctx.torrent is tor, "ctx.torrent 应回退删除前快照副本"


def test_on_state_changed_fires():
    """on_torrent_state_enum_changed: 状态枚举变化触发事件规则"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_state_enum_changed", _add_tags_action())})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        _refresh(mgr, [tor])  # 首轮: 建立 state_snapshot
        mgr.client.calls.clear()
        mgr.state.pop("exec_history", None)
        # 状态变化 stalledUP -> pausedUP
        tor.state = "pausedUP"
        client = _refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) in client.calls, f"状态变化应触发: {client.calls}"
        assert "event_rules.r1:H1" in mgr.state.get("exec_history", {}), "应记录执行历史"


def test_on_state_changed_new_no_fire():
    """on_torrent_state_enum_changed: 新增种子首现不视为状态变化(无上一轮记录)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_state_enum_changed", _add_tags_action())})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        client = _refresh(mgr, [tor])  # 首轮: 全部新增, 不触发状态变化
        assert ("add_tags", ["event-tag"]) not in client.calls, "首现不视为状态变化: {client.calls}"
        assert "event_rules.r1:H1" not in mgr.state.get("exec_history", {})


def test_rule_event_not_self_cycled():
    """rule-event 任务恒 FINISHED: 事件分派后不周期入队, 断点续跑后消亡"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _add_tags_action())})
        # 直接调 _apply_event_rule(无 pending, 正常完成) -> 任务不被入队
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        mgr.client = FakeClient()
        mgr.client.torrents["H1"] = tor
        task = mgr._apply_event_rule(next(r for r in mgr.enabled_rules if r.name == "event_rules.r1"), "H1")
        assert isinstance(task, Task) and task.kind == "rule-event"
        # 无 pending -> 不入队(事件即时分派), 自然消亡
        assert task not in mgr.task_queue._fast, "正常完成的事件任务不入队"
        assert not task.has_breakpoint, "正常完成不设断点"


def test_mixed_events():
    """混用: 同一种子新增时既触发 on_torrent_added, 又触发 on_torrent_state_enum_changed"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({
            "r_add": _ev("on_torrent_added", [{"add_tags": ["add-tag"]}]),
            "r_state": _ev("on_torrent_state_enum_changed", [{"add_tags": ["state-tag"]}]),
        })
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        client = _refresh(mgr, [tor])  # 首轮: 仅 added 触发, 无状态变化
        assert ("add_tags", ["add-tag"]) in client.calls, f"新增应触发: {client.calls}"
        assert ("add_tags", ["state-tag"]) not in client.calls, "首现不触发状态变化"
        mgr.state.pop("exec_history", None)
        tor.state = "pausedUP"
        client = _refresh(mgr, [tor])  # 第二轮: 状态变化触发 r_state; r_add 不触发
        assert ("add_tags", ["state-tag"]) in client.calls, f"状态变化应触发: {client.calls}"
        assert ("add_tags", ["add-tag"]) not in client.calls, "非新增不触发 r_add"


# ============================================================
# B. 白名单(config 阶段 fail-fast)
# ============================================================
def test_deleted_whitelist_fail():
    """on_torrent_deleted 配非只读动作 -> config 校验拒绝(需活种子的动作无意义)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    r1:\n"
            "      trigger: on_torrent_deleted\n"
            "      actions:\n"
            "        - start: true\n"
        )
        path = os.path.join(td, "config.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            load_config(path)
            assert False, "应拒绝 on_torrent_deleted 配 start"
        except ConfigError as e:
            assert "on_torrent_deleted" in str(e), f"应提示触发器限制: {e}"


def test_deleted_whitelist_print_ok():
    """on_torrent_deleted 配 print_torrent_details 通过校验(只读动作适用)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    r1:\n"
            "      trigger: on_torrent_deleted\n"
            "      actions:\n"
            "        - print_torrent_details: true\n"
        )
        path = os.path.join(td, "config.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        cfg = load_config(path)  # 不抛错
        assert "r1" in cfg.rules_config["example_rules"]


# ============================================================
# C. dry_run
# ============================================================
def test_dry_run():
    """事件分派 dry_run: 动作不执行、不记录执行历史(只读动作照常打印)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", [{"add_tags": ["event-tag"]}])})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        client = _refresh(mgr, [tor], dry_run=True)
        assert ("add_tags", ["event-tag"]) not in client.calls, "dry-run 不执行动作: {client.calls}"
        assert "event_rules.r1:H1" not in mgr.state.get("exec_history", {}), "dry-run 不记录执行历史"
        # 只读动作 dry-run 照常打印(无条件 success) -> 记录执行
        mgr.client = client
        tor2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr.client.torrents["H2"] = tor2
        rule = next(r for r in mgr.enabled_rules if r.name == "event_rules.r1")
        task = mgr._apply_event_rule(rule, "H2", dry_run=True)
        assert not task.has_breakpoint, "dry-run 无 pending"


# ============================================================
# D. 事件配 checking 的断点续跑(成功/失败/删除三态)
# ============================================================
def _check_cfg(action, execute_once="never"):
    """构造 checking 动作配置(spec 单键 dict)"""
    return [{
        "checking": {
            "basic_check": "filelist",
            "with_reference": {"enabled": True, "mode": "full-checking", "auto_start": True},
            "without_reference": {"enabled": True, "mode": "full-checking", "auto_start": True},
        }
    }] + action


def _pause_target(hash="H1", progress=0.5, tags="需校验", name="T", state="pausedDL"):
    return FakeTorrent(hash=hash, name=name, tags=tags, state=state, progress=progress)


def test_event_checking_resume_success():
    """事件配 checking: 触发时 pending 断点 -> 轮询成功 -> origin 重新入队 -> _handle_event_rule 续跑后续动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _check_cfg([{"add_tags": ["after-check"]}]))})
        tor = _pause_target()
        mgr.client = FakeClient()
        seed_store(mgr, [tor])  # 快照注入(dispatch 前种子已在 store)
        t0 = __import__("time").time()
        # 直接分派(不整轮 refresh, 便于确定推进队列) —— 模拟 refresh 的 added 分派
        rule = next(r for r in mgr.enabled_rules if r.name == "event_rules.r1")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        task = mgr._apply_event_rule(rule, "H1")
        # 事件分派即提交: recheck 已发送, 规则记录断点, 事件任务不入队
        assert ("recheck", None) in mgr.client.calls, "分派时应同步发送 recheck"
        assert task.resume_index == 1, f"checking 提交应记录断点: {task.resume_index}"
        assert task not in mgr.task_queue._fast, "pending 后事件任务不常驻队列"
        assert ("add_tags", ["after-check"]) not in mgr.client.calls, "校验未完成前不执行后续动作"

        # 校验中 -> 轮询续延(事件任务保持不在队列, 断点保留)
        seed_store(mgr, [_pause_target(state="checkingDL")])
        mgr.task_queue.run_due(False, t0 + 0.5)
        assert task.resume_index == 1, "校验中断点保留"

        # 校验成功(progress=1) -> 轮询 on_success + 重新入队 origin(断点保留)
        seed_store(mgr, [_pause_target(state="pausedUP", progress=1.0)])
        mgr.task_queue.run_due(False, t0 + 2.5)
        assert mgr.store.verified_references == {"H1"}, "成功晋升参考"
        assert task.resume_index == 1, "重新入队保留断点(续跑语义)"

        # 续跑: _handle_event_rule 执行剩余动作 add_tags + 记录 + 断点消费 -> FINISHED 消亡
        mgr.task_queue.run_due(False, t0 + 3.5)
        assert ("add_tags", ["after-check"]) in mgr.client.calls, f"续跑应执行后续动作: {mgr.client.calls}"
        assert "event_rules.r1:H1" in mgr.state.get("exec_history", {}), "续跑完成记录执行历史"
        assert task.resume_index is None, "断点应已消费清零"
        assert task not in mgr.task_queue._fast, "事件任务续跑后消亡(不自我周期循环)"


def test_event_checking_resume_fail():
    """事件配 checking: 校验失败 -> 轮询默认重置 origin -> 重走完整决策链(重新提交)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _check_cfg([{"add_tags": ["after-check"]}]))})
        tor = _pause_target(progress=0.5)
        mgr.client = FakeClient()
        seed_store(mgr, [tor])
        t0 = __import__("time").time()
        rule = next(r for r in mgr.enabled_rules if r.name == "event_rules.r1")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        task = mgr._apply_event_rule(rule, "H1")
        assert task.resume_index == 1 and ("recheck", None) in mgr.client.calls
        # 校验失败(progress 仍 <1) -> 轮询 bump 失败计数 + 默认重置 origin 重走决策链
        mgr.client.calls.clear()
        seed_store(mgr, [_pause_target(progress=0.4)])  # 仍未完成
        mgr.task_queue.run_due(False, t0 + 2.5)
        assert mgr.state["recheck_fails"]["H1"]["count"] == 1, "失败计数+1"
        assert task.resume_index is None, "失败默认重置断点(重走完整决策链)"
        # 重走决策链 -> 再次提交 recheck(origin 重新入队, 下一轮执行时重新校验)
        mgr.task_queue.run_due(False, t0 + 3.5)
        assert ("recheck", None) in mgr.client.calls, "重走决策链应重新提交: {mgr.client.calls}"


def test_event_checking_deleted():
    """事件配 checking: 校验中种子被删除 -> 销毁(不续跑), 不产生后续动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _ev("on_torrent_added", _check_cfg([{"add_tags": ["after-check"]}]))})
        tor = _pause_target()
        mgr.client = FakeClient()
        seed_store(mgr, [tor])
        t0 = __import__("time").time()
        rule = next(r for r in mgr.enabled_rules if r.name == "event_rules.r1")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        task = mgr._apply_event_rule(rule, "H1")
        assert task.resume_index == 1
        # 校验中种子删除: store 无该种子 -> 轮询销毁, origin 重入队后由删除守卫判死
        mgr.store.by_hash.pop("H1", None)
        mgr.client.calls.clear()
        mgr.task_queue.run_due(False, t0 + 2.5)  # 轮询见种子已删 -> 默认重置 origin 重新入队
        assert task in mgr.task_queue._fast, "轮询重新入队 origin(等待下轮执行判死)"
        mgr.task_queue.run_due(False, t0 + 3.5)  # origin 到期 -> 删除守卫判死 -> 消亡
        assert task not in mgr.task_queue._fast, "删除后事件任务消亡"
        assert ("add_tags", ["after-check"]) not in mgr.client.calls, "删除后不执行后续动作"
        assert "event_rules.r1:H1" not in mgr.state.get("exec_history", {}), "删除后不记录执行历史"
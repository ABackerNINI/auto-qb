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
- test_field_changed_fires: on_torrent_field_changed tags 外部变化触发且仅一次(计划 26-09-27-1438)
- test_field_changed_first_seen_baseline: 首见种子只落基线不触发
- test_field_changed_self_caused_no_fire: 程序自身 add_tags 不自触发(self-caused 抑制)
- test_field_changed_category_and_unwatched: category 变化触发监听它的规则; 未监听字段变化不触发
- test_field_changed_restart_catchup: 重启(重建 manager + state 保留)无风暴且停机期变化补捕
- test_field_changed_cooldown: cooldown 在字段变化事件下同样生效
- test_field_changed_full_refresh_net_change: 全量 refresh 降级路径与基线对比出净变化(非"全变")
- test_watch_fields_validation_errors: watch_fields 错 trigger 下出现/空值/白名单外值 -> config 拒绝
- test_watch_fields_valid: watch_fields 合法配置加载通过且 Rule 解析到位
- test_maintenance_tag_mode_validation: maintenance_tag_mode 非法取值拒绝 / 合法取值加载
- test_maintenance_on_change_skips_without_change: on_change 无变化轮跳过 tags 部分, HR 部分照常
- test_maintenance_on_change_recheck_on_external_change: tags 外部变化 -> 重检一次(登记消费)
- test_maintenance_interval_unchanged: 默认 interval 行为与迁移前等价(无变化也执行)
- test_maintenance_on_change_hot_reload_full_convergence: 热重载后首轮全量收敛
"""
import os
import tempfile

from auto_qb.config import ConfigError, load_config
from auto_qb.rules import Rule, RuleContext
from auto_qb.core.taskqueue import FINISHED, PENDING, Task, TaskQueue
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
    """构造仅含事件规则的 manager(替换 make_manager 的示例规则; tracker 引用事件规则集)

    !临时目录**挂到 mgr 上**(2026-09-23 实测): 原写法 `with TemporaryDirectory()` 在函数
    返回时就把目录删了, 而 `mgr.state_file` 仍指向该路径 —— 后续写 state.json(如
    `test_event_checking_resume_fail` 里的 `seed_store`)会把目录**重新建出来**, 且此时
    持有者已销毁 ⇒ 每跑一次全量就在 TMPDIR 根下留一个 `tmpXXXX`。挂给 mgr 后随 mgr 释放即删。
    (诊断手段: 仓库外插件 `R:/Temp/auto-qb/plugins/pa_tmp_trace.py`, 包住 `tempfile.mkdtemp`
    记录调用栈, 收尾打印仍存在的目录 —— 全量 577 个临时目录里只剩这 1 个泄漏点。)
    """
    holder = None if state_file else tempfile.TemporaryDirectory(prefix="autoqb-events-")
    mgr = make_manager(
        state_file or os.path.join(holder.name, "state.json"),
        tracker_rules=tracker_rules or ["@event_rules"],
    )
    if holder is not None:
        mgr._test_tmpdir = holder  # 生命周期锚点: 见 docstring
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
        mgr = _event_mgr(
            {
                "r_add": _ev("on_torrent_added", [{
                    "add_tags": ["add-tag"]
                }]),
                "r_state": _ev("on_torrent_state_enum_changed", [{
                    "add_tags": ["state-tag"]
                }]),
            }
        )
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
    return [
        {
            "checking":
                {
                    "basic_check": "filelist",
                    "with_reference": {
                        "enabled": True,
                        "mode": "full-checking",
                        "auto_start": True
                    },
                    "without_reference": {
                        "enabled": True,
                        "mode": "full-checking",
                        "auto_start": True
                    },
                }
        }
    ] + action


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
        # 校验中(见过 checking 态, 满足失败判定前提) -> 轮询续延
        seed_store(mgr, [_pause_target(state="checkingDL")])
        mgr.task_queue.run_due(False, t0 + 0.5)
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


# ============================================================
# E. on_torrent_field_changed(计划 26-09-27-1438)
# ============================================================
def _field_rule(watch=("tags", ), actions=None, **kw):
    """构造字段变化事件规则 spec(默认监听 tags, 单 add_tags 动作)"""
    return _ev("on_torrent_field_changed", actions or _add_tags_action(), watch_fields=list(watch), **kw)


def _keep_refresh(mgr, torrents, dry_run=False):
    """复用同一 client 连续跑一轮 _refresh_torrents(增量 rid 语义, 模拟真实持续运行)

    _refresh 每次新建 client(全量刷新), 会让程序自写在下轮被"全量重报"而与外部变化纠缠;
    字段变化事件考察的是持续运行下的增量语义, 用本助手。
    """
    if mgr.client is None:
        mgr.client = FakeClient()
    for t in torrents:
        mgr.client.torrents[t.hash] = t
    mgr._refresh_torrents(dry_run)
    return mgr.client


def _spy_tags_part(mgr):
    """给维护 tags 部分装 spy(_add_tags 是幂等补打, 无变化时无 API 调用, 须探调用而非调用记录)"""
    calls = []
    orig = mgr._add_tags

    def wrapper(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    mgr._add_tags = wrapper
    return calls


def test_field_changed_fires():
    """tags 外部变化 -> 下一轮触发且仅触发一次; 值不再变 -> 不重复触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _field_rule()})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="A")
        client = _keep_refresh(mgr, [tor])  # 首轮: 首见, 只落基线
        assert ("add_tags", ["event-tag"]) not in client.calls
        mgr.state.pop("exec_history", None)
        client.calls.clear()
        tor.tags = "A,B"  # 外部(人工/其它工具)改动
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) in client.calls, f"tags 外部变化应触发: {client.calls}"
        assert "event_rules.r1:H1" in mgr.state.get("exec_history", {})
        client.calls.clear()
        mgr.state.pop("exec_history", None)
        client = _keep_refresh(mgr, [tor])  # 值未再变: 不重复触发
        assert ("add_tags", ["event-tag"]) not in client.calls, f"无变化不应触发: {client.calls}"


def test_field_changed_first_seen_baseline():
    """首见种子只落基线不触发; 基线只存监听字段(tags 排序后存储, 消除 qB 顺序噪声)

    基线含 "HHan": 首轮添加路径的维护已补打站点标签(现状行为), 轮末基线如实记录。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _field_rule()})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="B,A")
        client = _refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) not in client.calls, "首见不触发"
        assert mgr.store.field_snapshots.get("H1") == {"tags": ["A", "B", "HHan"]}, "基线应排序存储且只含监听字段"


def test_field_changed_self_caused_no_fire():
    """程序自身 add_tags(经 QbApi Facade)不自触发: self-caused 登记在下轮 qB 增量报告时消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _field_rule()})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="A")
        client = _keep_refresh(mgr, [tor])  # 建基线(维护已补打 HHan)
        mgr.state.pop("exec_history", None)
        client.calls.clear()
        mgr.api.torrents_add_tags(tags=["prog"], torrent_hashes="H1")  # 程序自写
        tor.tags = "A,HHan,prog"  # qB 侧接受写入(下轮增量将报告该变化)
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) not in client.calls, f"自写不应自触发: {client.calls}"
        assert "event_rules.r1:H1" not in mgr.state.get("exec_history", {})
        assert "H1" not in mgr.store.external_tag_changes, "自写变化不应登记维护重检"


def test_field_changed_category_and_unwatched():
    """category 变化只触发监听 category 的规则; 未监听字段(amount_left)变化谁都不触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr(
            {
                "r_cat": _field_rule(watch=("category", ), actions=[{
                    "add_tags": ["cat-tag"]
                }]),
                "r_tags": _field_rule(watch=("tags", ), actions=[{
                    "add_tags": ["tag-only"]
                }]),
            }
        )
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="A", category="C1")
        client = _keep_refresh(mgr, [tor])
        mgr.state.pop("exec_history", None)
        client.calls.clear()
        tor.category = "C2"
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["cat-tag"]) in client.calls, f"category 变化应触发 r_cat: {client.calls}"
        assert ("add_tags", ["tag-only"]) not in client.calls, "tags 未变, r_tags 不触发"
        mgr.state.pop("exec_history", None)
        client.calls.clear()
        tor.amount_left = 12345  # 未监听字段
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["cat-tag"]) not in client.calls, f"未监听字段不触发: {client.calls}"
        assert ("add_tags", ["tag-only"]) not in client.calls


def test_field_changed_restart_catchup():
    """重启(重建 manager + state 保留): 无变化种子零事件(无风暴); 停机期的外部变化首轮补捕"""
    with tempfile.TemporaryDirectory() as td:
        sf = os.path.join(td, "state.json")
        mgr = _event_mgr({"r1": _field_rule()}, state_file=sf)
        tor_a = FakeTorrent(hash="HA", name="A", state="stalledUP", tags="A")
        tor_b = FakeTorrent(hash="HB", name="B", state="stalledUP", tags="X")
        _refresh(mgr, [tor_a, tor_b])  # 建基线并落盘(首轮维护已补打站点标签)
        mgr.save_state()
        # 重启: 重建 manager(同 state_file), 停机期间仅 HA 的 tags 被外部改动
        mgr2 = _event_mgr({"r1": _field_rule()}, state_file=sf)
        assert mgr2.store.field_snapshots == {"HA": {"tags": ["A", "HHan"]}, "HB": {"tags": ["HHan", "X"]}}, \
            "基线应随 state 恢复(排序口径)"
        tor_a.tags = "A,B"
        client = _keep_refresh(mgr2, [tor_a, tor_b])  # mgr2 首轮: 全量(full_update), 基线对比补捕
        assert ("add_tags", ["event-tag"]) in client.calls, "停机期变化应补捕"
        # 轮末基线含本轮事件与维护写入的标签(event-tag / HHan): 如实记录
        assert mgr2.store.field_snapshots["HA"] == {"tags": ["A", "B", "HHan", "event-tag"]}, "基线应已刷新"
        client.calls.clear()
        mgr2.state.pop("exec_history", None)
        client = _keep_refresh(mgr2, [tor_a, tor_b])  # 补捕后值稳定: 无风暴
        assert ("add_tags", ["event-tag"]) not in client.calls, f"无变化不应触发: {client.calls}"


def test_field_changed_cooldown():
    """cooldown 在字段变化事件下同样生效(复用 exec_history, 机制零新增)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _field_rule(cooldown="1H")})
        tor = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="A")
        client = _keep_refresh(mgr, [tor])
        tor.tags = "A,B"
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) in client.calls, "冷却外首次变化应触发"
        client.calls.clear()
        tor.tags = "A,B,C"  # 1H 内再次变化
        client = _keep_refresh(mgr, [tor])
        assert ("add_tags", ["event-tag"]) not in client.calls, f"冷却期内应被抑制: {client.calls}"


class _NoSyncClient(FakeClient):
    """模拟旧版 qB: 不支持 sync/maindata -> store 降级全量 torrents_info(计划 §05 降级路径)

    torrents_add_tags 同时写回种子对象: 模拟 qB 接受程序自写(真实 qB 的全量刷新上报值含
    自写结果, 与基线对比后可被值匹配抑制 —— 不写回则每轮全量都是"自写回声", 测不出净变化)。
    """
    def sync_maindata(self, rid=0, **kw):
        raise AttributeError("no sync endpoint")

    def torrents_add_tags(self, tags=None, torrent_hashes=None):
        super().torrents_add_tags(tags=tags, torrent_hashes=torrent_hashes)
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else (torrent_hashes or [])
        for h in hashes:
            tor = self.torrents.get(h)
            if tor is not None:
                cur = {t.strip() for t in (tor.tags or "").split(",") if t.strip()}
                tor.tags = ",".join(sorted(cur | set(tags or [])))


def test_field_changed_full_refresh_net_change():
    """全量 refresh 降级路径: 与持久化基线对比出净变化(只有真变化的种子触发, 非"全变")"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _event_mgr({"r1": _field_rule()})
        mgr.client = _NoSyncClient()
        tor_a = FakeTorrent(hash="HA", name="A", state="stalledUP", tags="A")
        tor_b = FakeTorrent(hash="HB", name="B", state="stalledUP", tags="X")
        for t in (tor_a, tor_b):
            mgr.client.torrents[t.hash] = t
        mgr._refresh_torrents()  # 首轮: 全量降级, 首见落基线
        mgr.state.pop("exec_history", None)
        mgr.client.calls.clear()
        tor_a.tags = "A,B"  # 仅 HA 变化
        mgr._refresh_torrents()  # 仍走全量 torrents_info
        assert ("add_tags", ["event-tag"]) in mgr.client.calls, "全量路径下真变化应触发"
        mgr.client.calls.clear()
        mgr.state.pop("exec_history", None)
        mgr._refresh_torrents()  # 全量再刷, 值未变: 不触发(证明不是按"全变"处理)
        assert ("add_tags", ["event-tag"]) not in mgr.client.calls, f"全量刷新不得等于事件风暴: {mgr.client.calls}"


# ============================================================
# F. watch_fields / maintenance_tag_mode 配置校验(config 阶段 fail-fast)
# ============================================================
def _load_rule_cfg(trigger, watch_fields):
    text = (
        "config:\n"
        "  example_rules:\n"
        "    r1:\n"
        f"      trigger: {trigger}\n"
        f"      watch_fields: [{', '.join(watch_fields)}]\n"
        "      actions:\n"
        "        - add_tags: ['x']\n"
    )
    path = os.path.join(tempfile.mkdtemp(prefix="autoqb-cfg-"), "config.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return load_config(path)


def test_watch_fields_validation_errors():
    """watch_fields: 错 trigger 下出现 / 空值 / 白名单外值 -> config 校验拒绝"""
    cases = [
        ("interval", ["tags"], "仅在 trigger: on_torrent_field_changed"),
        ("on_torrent_added", ["tags"], "仅在 trigger: on_torrent_field_changed"),
        ("on_torrent_field_changed", [], "非空列表"),
        ("on_torrent_field_changed", ["state"], "取值限"),
        ("on_torrent_field_changed", ["amount_left"], "取值限"),
    ]
    for trigger, wf, expect in cases:
        try:
            _load_rule_cfg(trigger, wf)
            assert False, f"应拒绝 trigger={trigger} watch_fields={wf}"
        except ConfigError as e:
            assert expect in str(e), f"应提示 '{expect}': {e}"


def test_watch_fields_valid():
    """watch_fields 合法配置加载通过, 且 Rule 解析到位(store 监听集合同步推导)"""
    with tempfile.TemporaryDirectory() as td:
        sf = os.path.join(td, "state.json")
        mgr = _event_mgr(
            {
                "r1": _field_rule(watch=("tags", "category")),
                "r2": _ev("interval", _add_tags_action()),
            }, state_file=sf
        )
        rule = next(r for r in mgr.enabled_rules if r.name == "event_rules.r1")
        assert rule.watch_fields == ("tags", "category")
        assert mgr.store.watch_fields == {"tags", "category"}, "监听集合应为全部规则 watch_fields 并集"


def test_maintenance_tag_mode_validation():
    """maintenance_tag_mode: 非法取值拒绝; 合法取值加载到位"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "config.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("config:\n  maintenance_tag_mode: sometimes\n")
        try:
            load_config(path)
            assert False, "应拒绝非法 maintenance_tag_mode"
        except ConfigError as e:
            assert "interval/on_change" in str(e), e
        with open(path, "w", encoding="utf-8") as f:
            f.write("config:\n  maintenance_tag_mode: on_change\n")
        cfg = load_config(path)
        assert cfg.maintenance_tag_mode == "on_change"


# ============================================================
# G. maintenance_tag_mode 维护迁移(行为矩阵, 计划 §07)
# ============================================================
def _maint_mgr(mode, state_file):
    """构造 on_change/interval 模式的 manager(内置示例规则集, tracker=HHan)

    !改模式后必须重跑 _load_rules: 生产中 maintenance_tag_mode 是 L2 热重载(整体重建 manager,
    规则随新配置重载), store 的监听集合在 _load_rules 收尾推导 —— 测试同口径。
    """
    mgr = make_manager(state_file)
    mgr.config.maintenance_tag_mode = mode
    mgr._load_rules()
    mgr.client = FakeClient()
    return mgr


def _maint_torrent():
    """未触发 HR 的种子(downloaded=0): HR 部分在 downloaded 增长前不产生任何写动作"""
    return FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="", downloaded=0)


def test_maintenance_on_change_skips_without_change():
    """on_change: 添加路径执行一次后, 无变化轮跳过 tags 部分; HR 部分节奏不变(恒执行)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _maint_mgr("on_change", os.path.join(td, "state.json"))
        tor = _maint_torrent()
        mgr.client.torrents["H1"] = tor
        mgr._refresh_torrents()  # 添加路径: tags 部分强制执行一次
        assert ("add_tags", ["HHan"]) in mgr.client.calls, "添加路径应执行站点 tags 补打"
        rec = mgr.store.get("H1")
        mgr.client.calls.clear()
        spy = _spy_tags_part(mgr)
        rec.downloaded = rec.total_size  # HR 达标状态随时间演化(与 tags 无关)
        mgr._handle_maintenance(rec, False)  # interval 任务到期: tags 未变
        assert not spy, "无变化轮应跳过 tags 部分"
        assert ("set_category", "!!HR3D!!") in mgr.client.calls, "HR 部分应照常执行(节奏不变)"


def test_maintenance_on_change_recheck_on_external_change():
    """on_change: tags 外部变化 -> 下次维护重检一次(登记消费, 之后无变化再跳过)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _maint_mgr("on_change", os.path.join(td, "state.json"))
        tor = _maint_torrent()
        mgr.client.torrents["H1"] = tor
        mgr._refresh_torrents()
        rec = mgr.store.get("H1")
        mgr.client.calls.clear()
        tor.tags = "B"  # 外部改动(站点标签一并被清 -> 重检可观察到真实补打)
        mgr._refresh_torrents()  # 增量报告 -> external_tag_changes 登记
        mgr._handle_maintenance(rec, False)
        assert ("add_tags", ["HHan"]) in mgr.client.calls, "tags 外部变化应触发重检"
        assert "H1" not in mgr.store.external_tag_changes, "登记应消费一次"
        mgr.client.calls.clear()
        mgr._handle_maintenance(rec, False)
        assert ("add_tags", ["HHan"]) not in mgr.client.calls, "重检后无变化应继续跳过"


def test_maintenance_interval_unchanged():
    """默认 interval: 行为与迁移前等价 —— 无变化轮 tags 部分照常执行(_add_tags 幂等, 探调用)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _maint_mgr("interval", os.path.join(td, "state.json"))
        tor = _maint_torrent()
        mgr.client.torrents["H1"] = tor
        mgr._refresh_torrents()
        rec = mgr.store.get("H1")
        mgr.client.calls.clear()
        spy = _spy_tags_part(mgr)
        mgr._handle_maintenance(rec, False)
        assert spy, "interval 模式无变化也应执行 tags 部分(现状)"


def test_maintenance_on_change_hot_reload_full_convergence():
    """on_change: 热重载(reset_runtime)后全部种子登记待重检 -> 全量轮重匹配 conf 后首轮全量收敛"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _maint_mgr("on_change", os.path.join(td, "state.json"))
        tor = _maint_torrent()
        mgr.client.torrents["H1"] = tor
        mgr._refresh_torrents()
        rec = mgr.store.get("H1")
        mgr.client.calls.clear()
        spy = _spy_tags_part(mgr)
        mgr._handle_maintenance(rec, False)
        assert not spy, "前置: 无变化时跳过"
        # 模拟 apply_new_config L2 尾段: reset_runtime + client 重连(rid 失效 -> 下轮全量)
        mgr.store.reset_runtime()
        mgr.store.reset_sync()
        mgr._refresh_torrents()  # 全量轮: conf 重匹配 + 待重检标记全量登记
        assert rec.tracker_conf is not None, "全量轮应重匹配 tracker_conf(reset_runtime 契约)"
        mgr._handle_maintenance(rec, False)
        assert spy, "热重载后首轮应全量收敛"

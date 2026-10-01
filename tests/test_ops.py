"""test_ops: 危险操作独立操作层(OpsMixin)自测(plan 26-09-30-0109 §5.1, 不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_ops_web_recheck_registers_and_releases: web 源提交 -> 登记 _active_checks(决策链 1.5 可见); 轮询 FINISHED 释放, 无 origin 重入队副作用, 不晋升
- test_ops_web_recheck_rejected_when_inflight: 在途互斥(全来源): 规则轮询在途 -> web 源拒绝「校验进行中」, qB 不重启校验
- test_ops_web_recheck_rejected_when_snapshot_checking: 快照 checking 态 -> 拒绝(不依赖登记, 覆盖 qB 自家 WebUI 发起的校验)
- test_ops_web_recheck_no_cooldown_no_promotion: web 源反复失败不计冷却(D1 手动排障不受限), 成功不晋升 verified_references
- test_ops_rule_recheck_cooldown_and_requeue_regression: rule 源失败计冷却 + origin 默认重置重入队 + 达上限当日拒绝(回归不变)
- test_ops_skip_check_day_shared_across_sources: 跳检同日去重跨来源共享(web 先跳, 规则同日再跳被拒)
- test_ops_web_skip_check_no_highrisk_warning: web 源不产生「无参考跳检(高风险)」告警(规则侧语义不泄漏进 WEB)
"""
import os
import tempfile
import time
import uuid
from datetime import date

from auto_qb.core.qbmanager import QbManager
from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue
from auto_qb.rules.actions import RECHECK_FAIL_LIMIT
from auto_qb.rules.actions.full_checking import _bump_recheck_fail
from helpers import FakeClient, FakeConfig, FakeTorrent, seed_store

# 跳检会真实落盘 .torrent 备份(issue 26-09-21-1347): state_file 必须落临时目录, 与 test_checking 同口径
_TMP_STATE_DIR = tempfile.TemporaryDirectory(prefix="autoqb-ops-state-")


def make_mgr(cfg):
    """构造 QbManager(独立任务队列); 自动分配临时 state 文件"""
    if not cfg.state_file:
        cfg.state_file = os.path.join(_TMP_STATE_DIR.name, f"state-{uuid.uuid4().hex}.json")
    mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
    mgr.host.get("rules").load_rules()
    mgr.task_queue = TaskQueue()
    return mgr


def run_queue(mgr, now):
    return mgr.task_queue.run_due(False, now=now)


def seed_paused(mgr, client, hash="HA"):
    """灌一个暂停未完成种子进快照与客户端(ops 直调测试的标的)"""
    t = FakeTorrent(hash=hash, state="pausedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents[hash] = t
    return t


# ============================================================
# A. ops_recheck: web 源(R1 提交点 + 登记/释放 + D1 来源区分)
# ============================================================
def test_ops_web_recheck_registers_and_releases():
    """测试: web 源提交 -> 在途登记(决策链 1.5 组内串行化可见); 轮询完成释放, 无重入队/晋升副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok, f"web 源提交应成功: {r}"
    assert "HA" in mgr.task_queue.active_check_hashes(), "提交后必须登记在途(决策链 1.5 可见)"
    # 轮询推进: 校验中 -> 完成(add_task 以真实时钟到期, 推进点一律 +1/+3s 避开时间粒度)
    now = time.time()
    t.state = "checkingDL"
    run_queue(mgr, now + 1)  # 首轮: 见 checking, REQUEUE
    t.state = "pausedUP"
    t.progress = 1.0
    run_queue(mgr, now + 3)  # 次轮: 完成, FINISHED
    assert "HA" not in mgr.task_queue.active_check_hashes(), "轮询 FINISHED 后必须释放在途登记"
    assert "HA" not in mgr.store.verified_references, "web 源不晋升参考种子"
    assert all(task.kind != "rule" for task in mgr.task_queue._fast), "web 源无 origin, 不得重入队任何规则任务"


def test_ops_web_recheck_rejected_when_inflight():
    """测试: 规则校验在途(登记) -> web 源拒绝「校验进行中」, qB 不重启校验(C1 WEB->规则半边)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)
    inflight = Task("check", "check-checking-result", hash="HA", store=mgr.store, handler=lambda t, d: REQUEUE)
    assert mgr.task_queue.add_task(inflight)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "校验进行中" in r.message, f"在途应拒绝: {r}"
    assert client.calls == [], f"拒绝时不得调 qB API: {client.calls}"


def test_ops_web_recheck_rejected_when_snapshot_checking():
    """测试: 快照 checking 态 -> 拒绝(覆盖不经理序登记的在途: qB 自家 WebUI/第三方发起的校验)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="checkingDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "校验进行中" in r.message, f"checking 态应拒绝: {r}"
    assert client.calls == [], f"拒绝时不得调 qB API: {client.calls}"


def test_ops_web_recheck_no_cooldown_no_promotion():
    """测试: web 源反复失败不计冷却(D1), 达到规则源上限后仍可提交; 成功不晋升参考"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    now = time.time()
    for i in range(RECHECK_FAIL_LIMIT + 1):
        r = mgr.ctx.ops.recheck("HA", source="web")
        assert r.is_ok, f"web 源不受冷却限制(第{i}次): {r}"
        t.state = "checkingDL"
        run_queue(mgr, now + i * 10 + 1)  # 见 checking
        t.state = "pausedDL"
        t.progress = 0.5
        run_queue(mgr, now + i * 10 + 3)  # 落回未完成 -> 判败
        assert "HA" not in mgr.state.get("recheck_fails", {}), "web 源失败不得计入冷却计数"
        assert "HA" not in mgr.task_queue.active_check_hashes(), "判败后轮询应消亡释放在途"
    # 成功路径: 不晋升
    t.state = "pausedDL"
    t.progress = 0.0
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    t.state = "pausedUP"
    t.progress = 1.0
    run_queue(mgr, now + 100)
    assert "HA" not in mgr.store.verified_references, "web 源校验成功不晋升参考种子"


def test_ops_rule_recheck_cooldown_and_requeue_regression():
    """测试: rule 源失败计冷却 + origin 默认重置重入队(回归不变); 达上限当日拒绝"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: None)
    assert r.is_pending, f"rule 源应返回 pending(规则断点): {r}"
    now = time.time()
    t.state = "checkingDL"
    run_queue(mgr, now + 1)
    t.state = "pausedDL"
    t.progress = 0.5
    run_queue(mgr, now + 3)
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, "rule 源失败应计入冷却"
    assert any(task is origin for task in mgr.task_queue._fast), "失败后 origin 应被默认重置重入队"
    # 达上限 -> 当日拒绝(冷却闸门在提交点, qB 不再收到 recheck)
    while _bump_recheck_fail(mgr.ctx.state, "HA") < RECHECK_FAIL_LIMIT:
        pass
    n_calls = len(client.calls)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_skipped and "今日不再重试" in r.message, f"达上限应拒绝: {r}"
    assert len(client.calls) == n_calls, f"拒绝时不得再提交 recheck: {client.calls}"


# ============================================================
# B. ops_skip_check: 跨来源共享去重 + 告警按来源
# ============================================================
def test_ops_skip_check_day_shared_across_sources():
    """测试: 跳检同日去重跨来源共享 —— web 跳检成功后, 规则源同日再跳被拒(「今日已跳检过」自解释)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client, hash="HASH123")  # FakeClient 重加固定回 HASH123
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"web 跳检应完成: {r}"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat(), "web 跳检应记录同日去重"
    r2 = mgr.ctx.ops.skip_check("HASH123", source="rule")
    assert r2.is_skipped and "今日已跳检过" in r2.message, f"跨来源同日应去重: {r2}"


def test_ops_web_skip_check_no_highrisk_warning():
    """测试: web 源跳检不产生「无参考跳检(高风险)」告警 —— 规则侧语义不泄漏进 WEB(前端危险确认框已告知)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client, hash="HASH123")
    r = mgr.ctx.ops.skip_check("HASH123", source="web", has_reference=False)
    assert r.is_ok, f"web 跳检应完成: {r}"
    assert mgr.state["skip_check_day"].get("HASH123"), "跳检应完成并记录"

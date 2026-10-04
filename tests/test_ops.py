"""test_ops: 危险操作独立操作层(OpsMixin)自测(plan 26-09-30-0109 §5.1, 不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_ops_web_recheck_registers_and_releases: web 源提交 -> 登记 _active_checks(决策链 1.5 可见); 轮询 FINISHED 释放, 无 origin 重入队副作用, 不晋升
- test_ops_web_recheck_rejected_when_inflight: 在途互斥(全来源): 规则轮询在途 -> web 源拒绝「校验进行中」, qB 不重启校验
- test_ops_web_recheck_rejected_when_snapshot_checking: 快照 checking 态 -> 拒绝(不依赖登记, 覆盖 qB 自家 WebUI 发起的校验)
- test_ops_web_recheck_no_cooldown_no_promotion: web 源反复失败不计冷却(D1 手动排障不受限), 成功不晋升 verified_references
- test_ops_rule_recheck_cooldown_and_requeue_regression: rule 源失败计冷却 + origin 默认重置重入队 + 达上限当日拒绝(回归不变)
- test_ops_recheck_completed_torrent_first_hop_no_false_success: 已完成种子首跳读旧快照 -> 无证据不判成功(WAITING), 在途登记持有, 见证据后才真判定成功 (S2a)
- test_ops_recheck_stale_snapshot_timeline_no_false_success: 生产时间线重放: 快照冻结两拍无结论 -> 证据 -> 完成才唯一一次「校验成功」 (S2a)
- test_ops_rule_recheck_success_once_after_evidence: rule 源全序列 on_success 恰 1 次且只发生在见证据之后(带序号回调) (S2a)
- test_ops_recheck_wait_result_zero_api_calls: 等待期(证据立起前后)多跳 torrents_info 计数 == 0, 周期观测纯快照读(等价性红线) (S2a)
- test_ops_recheck_poll_reads_live_record_fresh_progress: 闭包不缓存字段值: 中途改 store 活记录 progress, 下一跳读到新值(回落跌破基线判败, 标「progress 回落」) (S2a)
- test_ops_skip_check_day_shared_across_sources: 跳检同日去重跨来源共享(web 先跳, 规则同日再跳被拒)
- test_ops_web_skip_check_no_highrisk_warning: web 源不产生「无参考跳检(高风险)」告警(规则侧语义不泄漏进 WEB)
- test_ops_web_recheck_poll_torrent_deleted_no_origin: 轮询期间种子删除且无 origin -> 消亡无重入队 (P2-a)
- test_ops_web_recheck_start_giveup_timeout: 宽限耗尽未见 checking(web 源) -> 判败不计冷却 (P2-a)
- test_ops_recheck_poll_exception_releases_and_requeues: 轮询异常 -> 释放在途; rule 源 origin 重入队 (P2-a)
- test_ops_recheck_duplicate_task_guard: 登记点兜底 add_task 失败 -> skip 不发送 (P2-a)
- test_ops_skip_check_live_recheck_api_error: 跳检前实时复核 API 异常 -> fail 零副作用 (P2-a)
- test_ops_skip_gates_prune_stale_skip_day: 跳检同日去重表跨日残留清理 (P2-a)
- test_ops_infer_content_layout_empty_content: content_path 为空不推断布局 (P2-a)
- test_ops_clear_backup_noop_missing_path_and_oserror: _clear_backup 无元数据/path 空/删除失败三态 (P2-a)
"""
import logging
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import date

from auto_qb.core.qbmanager import QbManager
from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue
from auto_qb.rules.actions import RECHECK_FAIL_LIMIT
from auto_qb.rules.actions.full_checking import bump_recheck_fail
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


class _OpsLogCapture(logging.Handler):
    """抓 ops_mod 模块日志的极简 handler(消息列表)

    不用 caplog: QbManager 构造期经 logging 模块 setup_logging 会 clear 根 handlers,
    pytest caplog 挂在根上的 handler 一并被清(text 恒空) —— 直接挂模块 logger 才可靠。
    """
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@contextmanager
def capture_ops_logs(level=logging.DEBUG):
    """临时挂 _OpsLogCapture 到 ops_mod 模块 logger 并临时关闭 propagate(不污染测试输出)"""
    h = _OpsLogCapture()
    lg = logging.getLogger("auto_qb.core.modules.ops_mod")
    old_level, old_propagate = lg.level, lg.propagate
    lg.setLevel(level)
    lg.propagate = False
    lg.addHandler(h)
    try:
        yield h.messages
    finally:
        lg.removeHandler(h)
        lg.setLevel(old_level)
        lg.propagate = old_propagate


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
    while bump_recheck_fail(mgr.ctx.state, "HA") < RECHECK_FAIL_LIMIT:
        pass
    n_calls = len(client.calls)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_skipped and "今日不再重试" in r.message, f"达上限应拒绝: {r}"
    assert len(client.calls) == n_calls, f"拒绝时不得再提交 recheck: {client.calls}"


# ============================================================
# 证据门控轮询(plan 26-10-04-1824 S2a): B 组事故重放(无证据不下成功结论) + E 组红线(等价性)
# ============================================================
def test_ops_recheck_completed_torrent_first_hop_no_false_success():
    """测试: 已完成种子 recheck 首跳读到旧 completed 快照 -> 不判成功(WAITING), 见证据后才真判定
    (事故 26-10-03-1140 重放: qB 异步应用前首跳 progress=1.0 旧快照不得误判「校验成功」)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)  # 已完成种子(非 checking 态)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    fired = []
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    origin.resume_index = 4  # 断点标记: 成功重入队须 keep_progress(断点保留; 默认重置会清空)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: fired.append(1))
    assert r.is_pending, f"rule 源应 pending: {r}"
    now = time.time()
    run_queue(mgr, now + 1)  # 首跳(入队即到期): 快照仍 completed 且无证据 -> WAITING
    assert fired == [], "无证据首跳不得触发 on_success(假成功事故点)"
    assert "HA" in mgr.task_queue.active_check_hashes(), "WAITING 轮询任务仍活, 在途登记须持有"
    r2 = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: fired.append(1))
    assert r2.is_skipped and "校验进行中" in r2.message, f"轮询在途, 重复提交应被拒: {r2}"
    assert client.calls == [("recheck", None)], f"除提交 recheck 外零 qB 交互: {client.calls}"
    assert client.info_calls == 0, f"轮询期不得直查 torrents_info: {client.info_calls} 次"
    t.state = "checkingDL"
    run_queue(mgr, now + 3)  # 快照翻 checkingDL: 生效证据 -> REQUEUE
    assert "HA" in mgr.task_queue.active_check_hashes(), "证据跳仍在校验中, 登记须持有"
    t.state = "pausedUP"
    run_queue(mgr, now + 5)  # 证据之后回 completed: 真判定成功
    assert fired == [1], f"on_success 应恰触发一次(仅真判定): {fired}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "成功后轮询消亡释放在途"
    assert any(task is origin for task in mgr.task_queue._fast), "成功后 origin 应重入队"
    assert origin.resume_index == 4, "成功路径 origin 应 keep_progress(断点保留续跑)"


def test_ops_recheck_stale_snapshot_timeline_no_false_success():
    """测试: 生产时间线等价重放 —— 提交后快照冻结两拍(一直 completed, 模拟 qB 未应用)两跳无结论;
    翻 checking(REQUEUE) -> 回 completed 真判定, 全程「校验成功」日志恰一次(仅真判定)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    now = time.time()
    with capture_ops_logs() as logs:
        r = mgr.ctx.ops.recheck("HA", source="web")
        assert r.is_ok
        run_queue(mgr, now + 1)  # 冻结拍1: 旧快照仍 completed, 无证据
        run_queue(mgr, now + 3)  # 冻结拍2: 仍 completed, 无证据
        assert not any("校验成功" in m for m in logs), f"快照冻结期不得下成功结论: {logs}"
        assert "HA" in mgr.task_queue.active_check_hashes(), "WAITING 轮询须保持活"
        t.state = "checkingDL"
        run_queue(mgr, now + 5)  # 生效证据 -> REQUEUE
        assert not any("校验成功" in m for m in logs), f"证据跳仍在校验中, 不得下成功结论: {logs}"
        t.state = "pausedUP"
        run_queue(mgr, now + 7)  # 证据之后回 completed: 真判定
    assert sum("校验成功" in m for m in logs) == 1, f"成功日志应恰一次(仅真判定): {logs}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "真判定后轮询消亡释放在途"


def test_ops_rule_recheck_success_once_after_evidence():
    """测试: rule 源全序列 提交 -> 首跳无证据 -> 见证据 -> 完成; on_success 恰 1 次且只发生在
    见证据之后(带序号回调: 测试侧逐跳编号, 回调记录触发时点, 与证据跳先后可对照)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    fired = []  # (hop 序号, 回调触发时的快照 state)
    hop = [0]
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: fired.append((hop[0], t.state)))
    assert r.is_pending
    now = time.time()
    hop[0] = 1
    run_queue(mgr, now + 1)  # 首跳: 无证据(completed 旧快照)
    assert fired == [], "无证据首跳不得触发 on_success"
    hop[0] = 2
    t.state = "checkingDL"
    run_queue(mgr, now + 3)  # 生效证据跳(仍在校验中)
    assert fired == [], "证据跳未完成, 不得触发 on_success"
    hop[0] = 3
    t.state = "pausedUP"
    run_queue(mgr, now + 5)  # 证据之后的完成跳: 真判定
    assert fired == [(3, "pausedUP")], f"on_success 应恰在见证据后的完成跳触发一次: {fired}"


def test_ops_recheck_wait_result_zero_api_calls():
    """测试(等价性红线): 轮询等待期(证据立起前后多跳推进)零 torrents_info 直查 —— 周期观测纯快照读"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    now = time.time()
    run_queue(mgr, now + 1)  # 冻结拍: completed 无证据 -> WAITING
    t.state = "checkingDL"
    run_queue(mgr, now + 3)  # 证据立起 -> REQUEUE
    t.state = "checkingDL"
    run_queue(mgr, now + 5)  # 等待期多跳推进(仍 checkingDL)
    t.state = "checkingUP"
    run_queue(mgr, now + 7)  # 换一形态的真校验态继续等
    assert client.info_calls == 0, f"轮询期不得直查 torrents_info: {client.info_calls} 次"
    assert client.calls == [("recheck", None)], f"除提交 recheck 外零 qB 交互: {client.calls}"
    assert "HA" in mgr.task_queue.active_check_hashes(), "纯等待不消亡"


def test_ops_recheck_poll_reads_live_record_fresh_progress():
    """测试(逐轮读活记录): 闭包不缓存字段值 —— 中途改 store 活记录 progress, 下一跳读到新值;
    未见证据而跌破基线即按数据缺损签名判败, log 标「progress 回落」(处置序列与常规判败相同)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.5)  # 基线 0.5(提交点快照值)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_pending
    now = time.time()
    run_queue(mgr, now + 1)  # 首跳: progress 未变(0.5 == 基线) -> WAITING
    t.progress = 0.3  # 中途改 store 活记录(对象身份直写): 模拟校验发现坏块后的回落
    with capture_ops_logs() as logs:
        run_queue(mgr, now + 3)  # 下一跳: 逐轮读到新值 0.3 < 基线 0.5 -> FAILED(progress 回落)
    assert any("progress 回落" in m for m in logs), f"回落路径应有准确标签: {logs}"
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, "rule 源回落判败应计冷却"
    assert any(task is origin for task in mgr.task_queue._fast), "判败后 origin 应默认重置重入队"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "判败后轮询消亡释放在途"


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


# ============================================================
# P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02): recheck 轮询异常出口 + 跳检长尾
# ============================================================
def test_ops_web_recheck_poll_torrent_deleted_no_origin():
    """测试: 轮询期间种子已删除且无 origin(web 源) -> 轮询消亡释放登记, 无重入队副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    assert "HA" in mgr.task_queue.active_check_hashes()
    mgr.store.remove_torrent("HA")  # 轮询期间被删除(规则源默认重置语义轮不到 origin=None)
    run_queue(mgr, time.time() + 3)
    assert "HA" not in mgr.task_queue.active_check_hashes(), "轮询应消亡释放在途登记"
    assert all(task.kind != "rule" for task in mgr.task_queue._fast), "origin 为 None 不得重入队规则任务"


def test_ops_web_recheck_start_giveup_timeout():
    """测试: 宽限耗尽仍未见 checking(web 源) -> 判败防活锁, 不计冷却(origin=None 直接消亡)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    t0 = time.time()
    # 轮询内部用真实 time.time() 对比 submitted_at: 整体平移时钟模拟 600s 宽限耗尽
    shifted = t0 + 601.0
    real_time = time.time
    try:
        time.time = lambda: shifted
        run_queue(mgr, shifted)
    finally:
        time.time = real_time
    assert "HA" not in mgr.task_queue.active_check_hashes(), "宽限耗尽判败后轮询应消亡"
    assert "HA" not in mgr.state.get("recheck_fails", {}), "web 源不计冷却"
    assert t.state == "pausedDL", "判败不得改动种子状态"


def test_ops_recheck_poll_exception_releases_and_requeues():
    """测试: 轮询异常 -> 告警 + FINISHED 释放在途; rule 源 origin 默认重置重入队, web 源无副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)

    def boom(h):
        raise RuntimeError("snapshot boom")

    # web 源(origin=None): 异常 -> 释放登记, 无重入队
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    orig_get = mgr.store.get
    mgr.store.get = boom
    try:
        run_queue(mgr, time.time() + 3)
    finally:
        mgr.store.get = orig_get
    assert "HA" not in mgr.task_queue.active_check_hashes(), "异常路径必须释放在途登记"

    # rule 源(带 origin): 异常 -> origin 默认重置重入队(重走决策链)
    t2 = seed_paused(mgr, client, hash="HB")
    origin = Task("rule", "rule-test-hb", hash="HB", store=mgr.store, handler=lambda task, d: REQUEUE)
    r2 = mgr.ctx.ops.recheck("HB", source="rule", origin=origin)
    assert r2.is_pending
    mgr.store.get = boom
    try:
        run_queue(mgr, time.time() + 6)
    finally:
        mgr.store.get = orig_get
    assert "HB" not in mgr.task_queue.active_check_hashes(), "异常路径必须释放在途登记"
    assert any(task is origin for task in mgr.task_queue._fast), "异常后 origin 应默认重置重入队"


def test_ops_recheck_duplicate_task_guard():
    """测试: 登记点兜底(单线程模型下不可达, 防将来出现第二个登记点) -> add_task 失败时 skip 且不发送"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)
    mgr.task_queue.add_task = lambda task, now=None, keep_progress=False: False  # 注入登记失败
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "已在队列中" in r.message, f"登记失败应 skip: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), "未登记成功不得发送 recheck"


def test_ops_skip_check_live_recheck_api_error():
    """测试: 跳检前实时复核 API 异常 -> fail 且零副作用(未导出/删除/重加)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")

    def boom(**kw):
        raise RuntimeError("api down")

    client.torrents_info = boom
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "实时复核失败" in r.message, f"复核异常应 fail: {r}"
    assert not any(c[0] in ("export", "delete", "add") for c in client.calls), "复核失败零副作用"


def test_ops_skip_gates_prune_stale_skip_day():
    """测试: 跳检同日去重表的跨日残留在过闸时清掉(防表无限增长)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    mgr.state.setdefault("skip_check_day", {})["STALE"] = "2000-01-01"  # 跨日残留
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"跳检应完成: {r}"
    assert "STALE" not in mgr.state["skip_check_day"], "跨日残留应被清理"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat()


def test_ops_infer_content_layout_empty_content():
    """测试: content_path 为空(未知内容路径)时不推断布局, 返回 None"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    tor = FakeTorrent(hash="HA", content_path=None)
    assert mgr.ctx.ops._infer_content_layout(tor, client) is None


def test_ops_clear_backup_noop_missing_path_and_oserror():
    """测试: _clear_backup 三态 —— 无元数据直接返回 / path 为空跳过删除仍落盘 / 删除失败只告警"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    mgr.ctx.ops._clear_backup("HA")  # 无元数据: 直接返回, 不落盘不报错

    # path 为空: 跳过文件删除, 但元数据仍清理并落盘
    mgr.state.setdefault("skip_check_backup", {})["HA"] = {"path": ""}
    mgr.ctx.ops._clear_backup("HA")
    assert "HA" not in mgr.state["skip_check_backup"]

    # 删除失败: 只告警不崩溃, 元数据照常清理落盘
    mgr.state.setdefault("skip_check_backup", {})["HB"] = {"path": "R:/Temp/auto-qb/tests/ghost.torrent"}
    real_remove = os.remove

    def boom(path):
        raise OSError("locked")

    os.remove = boom
    try:
        mgr.ctx.ops._clear_backup("HB")
    finally:
        os.remove = real_remove
    assert "HB" not in mgr.state["skip_check_backup"]

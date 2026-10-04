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
- test_ops_recheck_wait_result_zero_api_calls: 提交完成后的等待期(证据立起前后)多跳零 torrents_info 直查 —— 提交点实时复核 1 次属 P1 合法提交成本, 不计窗口; 周期观测纯快照读(等价性红线) (S2a/P1)
- test_ops_recheck_poll_reads_live_record_fresh_progress: 闭包不缓存字段值: 中途改 store 活记录 progress, 下一跳读到新值(回落跌破基线判败, 标「progress 回落」) (S2a)
- test_ops_recheck_giveup_arbitration_extends_grace: 超宽限 + 仲裁直查见真校验态(快照滞后) -> 延长一次宽限不判败, 快照跟上后正常 SUCCESS, 仲裁直查恰 1 次(提交点实时复核另计 1 次) (S2b/P1)
- test_ops_recheck_giveup_arbitration_not_checking_fails: 超宽限 + 仲裁直查见非校验态 -> 判败序列不变(冷却 +1 / origin 重入队), 日志报真实等待时长 (S2b)
- test_ops_recheck_giveup_arbitration_api_error_fails: 超宽限 + 仲裁直查异常 -> fail-closed 同判败不走外层异常路径; D5 延期后第二次宽限耗尽不再直查直接判败 (S2b)
- test_ops_recheck_live_recheck_rejects_when_client_checking: 快照非 checking + live checkingDL(qB 自家 WebUI 刚发起) -> skip 拒绝(实时复核), 未发送 recheck 未登记 (P1)
- test_ops_recheck_live_recheck_rejects_when_gone: live 空(快照仍在) -> skip(R2 同族文案), 未发送 recheck 未登记 (P1)
- test_ops_recheck_live_recheck_error_fails_closed: 提交点实时复核 API 异常 -> fail-closed 拒绝提交(零副作用), 未发送 recheck 未登记 (P1)
- test_ops_recheck_baseline_from_live_truth: 基线取 live 真值: 快照 0.5 / live 0.9 -> 快照跟齐后不均匀期回落 0.8 按 0.9 判 FAILED「progress 回落」(旧快照基线 0.5 下 0.8 会判 WAITING) (P1)
- test_ops_skip_check_day_shared_across_sources: 跳检同日去重跨来源共享(web 先跳, 规则同日再跳被拒)
- test_ops_web_skip_check_no_highrisk_warning: web 源不产生「无参考跳检(高风险)」告警(规则侧语义不泄漏进 WEB)
- test_ops_web_recheck_poll_torrent_deleted_no_origin: 轮询期间种子删除且无 origin -> 消亡无重入队 (P2-a)
- test_ops_web_recheck_start_giveup_timeout: 宽限耗尽仲裁直查见非校验态(web 源, S2b 补 live 应答) -> 判败不计冷却 (P2-a)
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
    assert client.info_calls == 0, f"在途拒绝在实时复核之前, 不得付 live 调用成本: {client.info_calls}"


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
    assert client.info_calls == 0, f"快照拒绝在实时复核之前, 不得付 live 调用成本: {client.info_calls}"


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
    info_calls_at_submit = client.info_calls  # 提交点实时复核(P1): 恰 1 次 live, 属提交成本非等待期
    assert info_calls_at_submit == 1, f"提交点实时复核恰 1 次: {client.info_calls}"
    now = time.time()
    run_queue(mgr, now + 1)  # 首跳(入队即到期): 快照仍 completed 且无证据 -> WAITING
    assert fired == [], "无证据首跳不得触发 on_success(假成功事故点)"
    assert "HA" in mgr.task_queue.active_check_hashes(), "WAITING 轮询任务仍活, 在途登记须持有"
    r2 = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: fired.append(1))
    assert r2.is_skipped and "校验进行中" in r2.message, f"轮询在途, 重复提交应被拒: {r2}"
    assert client.calls == [("recheck", None)], f"除提交 recheck 外零 qB 交互: {client.calls}"
    assert client.info_calls == info_calls_at_submit, f"轮询期不得直查 torrents_info: {client.info_calls} 次"
    t.state = "checkingDL"
    run_queue(mgr, now + 3)  # 快照翻 checkingDL: 生效证据 -> REQUEUE
    assert "HA" in mgr.task_queue.active_check_hashes(), "证据跳仍在校验中, 登记须持有"
    t.state = "pausedUP"
    run_queue(mgr, now + 5)  # 证据之后回 completed: 真判定成功
    assert fired == [1], f"on_success 应恰触发一次(仅真判定): {fired}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "成功后轮询消亡释放在途"
    assert any(task is origin for task in mgr.task_queue._fast), "成功后 origin 应重入队"
    assert origin.resume_index == 4, "成功路径 origin 应 keep_progress(断点保留续跑)"
    assert client.info_calls == info_calls_at_submit, f"整个等待期零直查: {client.info_calls}"


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
    """测试(等价性红线): 提交完成后的等待期(证据立起前后多跳推进)零 torrents_info 直查 ——
    周期观测纯快照读。提交点实时复核 1 次是 P1 的合法提交成本, 以 recheck() 返回后的
    info_calls 为基线, 断言后续整个 WAIT_RESULT 阶段零增长(计划 §09 E 口径)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    client.torrents["HA"] = t
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok
    info_calls_at_submit = client.info_calls  # 提交点实时复核(P1): 记为等待期零增长断言的基线
    assert info_calls_at_submit == 1, f"提交点实时复核恰 1 次: {client.info_calls}"
    now = time.time()
    run_queue(mgr, now + 1)  # 冻结拍: completed 无证据 -> WAITING
    t.state = "checkingDL"
    run_queue(mgr, now + 3)  # 证据立起 -> REQUEUE
    t.state = "checkingDL"
    run_queue(mgr, now + 5)  # 等待期多跳推进(仍 checkingDL)
    t.state = "checkingUP"
    run_queue(mgr, now + 7)  # 换一形态的真校验态继续等
    assert client.info_calls == info_calls_at_submit, \
        f"等待期(提交完成之后)不得直查 torrents_info: {client.info_calls} 次"
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
# C. 启动超时仲裁直查(plan 26-10-04-1824 S2b, D5): 判「启动超时」前对 qB 一次性单 hash 直查
# ============================================================
def test_ops_recheck_giveup_arbitration_extends_grace():
    """测试: 超宽限 + 仲裁直查见真校验态(快照滞后看不见) -> 延长一次宽限继续纯快照观测, 不判败;
    快照跟上后走正常 SUCCESS 序列。直查次数: 提交点实时复核 1 次(P1 提交成本) + 仲裁直查恰
    1 次 = 全程 2 次(仲裁后观测零 API, 等价性红线)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)  # store 快照与 live 同为 pausedDL: 提交点实时复核放行(P1)
    fired = []
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin, on_success=lambda: fired.append(1))
    assert r.is_pending, f"rule 源应 pending: {r}"
    # 提交后 qB 应用 recheck 开检而快照同步线冻结看不见: live 真值翻 checkingDL(与快照分离)
    client.torrents["HA"] = FakeTorrent(hash="HA", state="checkingDL")
    now = time.time()
    real_time = time.time
    try:
        time.time = lambda: now + 601.0  # 整体平移时钟模拟 600s 宽限耗尽
        with capture_ops_logs() as logs:
            run_queue(mgr, now + 601.0)  # 宽限耗尽: 仲裁直查见 checkingDL -> 延长一次宽限
    finally:
        time.time = real_time
    assert any("延长一次宽限" in m and "601s" in m for m in logs), f"应有延长日志且报真实已等时长: {logs}"
    assert not any("校验启动超时" in m for m in logs), f"延期不得判败: {logs}"
    assert "HA" in mgr.task_queue.active_check_hashes(), "延期后轮询须存活"
    assert not any(task is origin for task in mgr.task_queue._fast), "延期不判败, origin 不得重入队"
    assert client.info_calls == 2, f"提交点 live 1 次 + 仲裁直查恰 1 次: {client.info_calls}"
    # 快照跟上(此后观测零 API): 证据闩 -> 完成, 正常 SUCCESS 序列
    t.state = "checkingDL"
    run_queue(mgr, now + 603.0)  # 快照翻 checkingDL: 生效证据 -> REQUEUE
    assert "HA" in mgr.task_queue.active_check_hashes(), "证据跳仍在校验中, 登记须持有"
    t.state = "pausedUP"
    t.progress = 1.0
    run_queue(mgr, now + 605.0)  # 证据之后回 completed: 真判定成功
    assert fired == [1], f"延期后应走正常 SUCCESS 序列: {fired}"
    assert any(task is origin for task in mgr.task_queue._fast), "成功后 origin 应重入队"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "成功后轮询消亡释放在途"
    assert client.info_calls == 2, f"仲裁后快照观测仍零 API: {client.info_calls}"


def test_ops_recheck_giveup_arbitration_not_checking_fails():
    """测试: 超宽限 + 仲裁直查见非校验态(快照与 qB 真值一致, 确未开检) -> 判败序列不变
    (rule 源冷却计数 +1 / origin 默认重置重入队), 日志报真实等待时长(非固定宽限常量)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)  # store 快照与 live 应答同为 pausedDL(非真校验态)
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_pending, f"rule 源应 pending: {r}"
    now = time.time()
    real_time = time.time
    try:
        time.time = lambda: now + 601.0
        with capture_ops_logs() as logs:
            run_queue(mgr, now + 601.0)  # 宽限耗尽: 仲裁直查见 pausedDL -> 判败
    finally:
        time.time = real_time
    assert any("校验启动超时" in m and "601s" in m for m in logs), f"应判启动超时且报真实时长: {logs}"
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, "直查未见校验态: 判败序列不变(冷却 +1)"
    assert any(task is origin for task in mgr.task_queue._fast), "判败后 origin 应默认重置重入队"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "判败后轮询消亡释放在途"
    assert client.info_calls == 2, f"提交点 live 1 次(P1) + 仲裁直查恰 1 次: {client.info_calls}"


def test_ops_recheck_giveup_arbitration_api_error_fails():
    """测试: 超宽限 + 仲裁直查 API 异常 -> 与「未见」同判 fail-closed 判败(异常分支内吃掉,
    不走「校验轮询异常」外层路径); D5 仲裁恰 1 次: 直查延期后第二次宽限耗尽不再直查直接判败"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    # ---- 第 1 段: 直查异常 -> 判败序列原样(冷却 +1 / origin 重入队 / 真实时长日志) ----
    t = seed_paused(mgr, client)
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_pending, f"rule 源应 pending: {r}"
    direct = []

    def boom(torrent_hashes=None, **kw):
        direct.append(torrent_hashes)
        raise RuntimeError("api down")

    client.torrents_info = boom
    now = time.time()
    real_time = time.time
    try:
        time.time = lambda: now + 601.0
        with capture_ops_logs() as logs:
            run_queue(mgr, now + 601.0)  # 宽限耗尽: 仲裁直查抛异常 -> 分支内吃掉, 按未见判败
    finally:
        time.time = real_time
    assert len(direct) == 1, f"仲裁直查应恰一次: {direct}"
    assert not any("校验轮询异常" in m for m in logs), f"异常须分支内吃掉, 不走外层路径: {logs}"
    assert any("仲裁直查失败" in m for m in logs), f"直查异常应有独立告警: {logs}"
    assert any("校验启动超时" in m and "601s" in m for m in logs), f"应判启动超时且报真实时长: {logs}"
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, "直查异常与未见同判: 冷却 +1"
    assert any(task is origin for task in mgr.task_queue._fast), "判败后 origin 应默认重置重入队"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "判败后轮询消亡释放在途"
    # ---- 第 2 段(D5): 直查见真校验态延期一次, 第二次宽限耗尽不再直查直接判败 ----
    t2 = seed_paused(mgr, client, hash="HB")
    origin2 = Task("rule", "rule-test-hb", hash="HB", store=mgr.store, handler=lambda task, d: REQUEUE)
    del client.torrents_info  # 撤销第 1 段异常桩: 提交点实时复核(P1)恢复走默认桩(client.torrents 真值 pausedDL)
    r2 = mgr.ctx.ops.recheck("HB", source="rule", origin=origin2)
    assert r2.is_pending, f"rule 源应 pending: {r2}"
    live_calls = []

    def flaky_info(torrent_hashes=None, **kw):
        client.info_calls += 1
        live_calls.append(torrent_hashes)
        if len(live_calls) > 1:  # D5 违约(第二次直查)在此炸出, 判定却仍 fail-closed -> 靠计数断言抓
            raise RuntimeError("D5 violation: second direct query")
        return [FakeTorrent(hash="HB", state="checkingDL")]  # qB 真值在校验(快照看不见)

    client.torrents_info = flaky_info
    info_calls_before = client.info_calls
    now2 = time.time()
    try:
        time.time = lambda: now2 + 601.0
        with capture_ops_logs() as logs2:
            run_queue(mgr, now2 + 601.0)  # 第一次宽限耗尽: 仲裁直查见 checkingDL -> 延长一次
            time.time = lambda: now2 + 1202.0
            run_queue(mgr, now2 + 1202.0)  # 第二次宽限耗尽: 不再直查, 直接判败(D5)
    finally:
        time.time = real_time
    assert len(live_calls) == 1, f"D5: 直查不得超一次: {live_calls}"
    assert client.info_calls - info_calls_before == 1, f"D5: 直查计数恰 +1: {client.info_calls}"
    assert sum("延长一次宽限" in m for m in logs2) == 1, f"延期只发生一次: {logs2}"
    assert any("校验启动超时" in m and "601s" in m for m in logs2), f"第二次宽限耗尽应直接判败: {logs2}"
    assert not any("校验轮询异常" in m for m in logs2), f"不得走外层异常路径: {logs2}"
    assert mgr.state["recheck_fails"]["HB"]["count"] == 1, "第二次宽限耗尽应判败计冷却"
    assert any(task is origin2 for task in mgr.task_queue._fast), "判败后 origin2 应默认重置重入队"
    assert "HB" not in mgr.task_queue.active_check_hashes(), "判败后轮询消亡释放在途"
    assert t2.state == "pausedDL", "判败不得改动种子状态"


# ============================================================
# D. recheck 提交点实时复核 + live 基线(plan 26-10-04-1824 P1): 与跳检 R2 同款保护范式
# ============================================================
def test_ops_recheck_live_recheck_rejects_when_client_checking():
    """测试: 快照非 checking + live checkingDL(qB 自家 WebUI 刚发起, 快照窗口内不可见) ->
    skip 拒绝(实时复核), 未发送 recheck、未登记任务(拒绝发生在登记之前, 零登记副作用)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)  # 快照: pausedDL(非 checking)
    client.torrents["HA"] = FakeTorrent(hash="HA", state="checkingDL")  # live 真值: 已在校验
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "校验进行中" in r.message and "实时复核" in r.message, f"live checking 应拒绝: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), f"不得发送 recheck: {client.calls}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "拒绝不得留下在途登记"


def test_ops_recheck_live_recheck_rejects_when_gone():
    """测试: live 空(种子已从客户端移除, 快照尚在) -> skip(R2 同族文案), 未发送 recheck、未登记"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])  # 快照仍在; client.torrents 留空 = qB 侧已无(live 空)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "种子已被移除" in r.message, f"live 空应放弃: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), f"不得发送 recheck: {client.calls}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "放弃不得留下在途登记"


def test_ops_recheck_live_recheck_error_fails_closed():
    """测试: 提交点实时复核 API 异常 -> fail-closed 拒绝提交(零副作用: 未登记未发送)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client)

    def boom(**kw):
        raise RuntimeError("api down")

    client.torrents_info = boom
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_failed and "提交前实时复核失败(未执行任何变更)" in r.message, f"复核异常应 fail: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), f"不得发送 recheck: {client.calls}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "fail-closed 不得留下在途登记"


def test_ops_recheck_baseline_from_live_truth():
    """测试(P1 基线来源替换): 快照 progress=0.5 与 live=0.9 不一致 -> 基线取 live 真值 0.9;
    快照跟齐后不均匀期回落到 0.8(无生效证据) -> 0.8 < 0.9 判 FAILED「progress 回落」。
    反向对照(断言写期望值, 不真跑旧路径): 若基线仍取旧快照值 0.5, 0.8 属「上行」会判
    WAITING 继续等 —— 回落证据将被漏判"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.5)  # store 快照: 0.5(滞后于 qB)
    seed_store(mgr, [t])
    client.torrents["HA"] = FakeTorrent(hash="HA", state="pausedDL", progress=0.9)  # live 真值: 0.9
    origin = Task("rule", "rule-test", hash="HA", store=mgr.store, handler=lambda task, d: REQUEUE)
    r = mgr.ctx.ops.recheck("HA", source="rule", origin=origin)
    assert r.is_pending, f"提交应成功: {r}"
    assert client.info_calls == 1, f"提交点实时复核恰 1 次 live 调用: {client.info_calls}"
    now = time.time()
    t.progress = 0.9  # 快照跟上 live 真值(== 基线, 非回落) -> WAITING
    run_queue(mgr, now + 1)
    t.progress = 0.8  # 不均匀期回落(校验发现坏块的签名); 快照仍无生效证据
    with capture_ops_logs() as logs:
        run_queue(mgr, now + 3)
    assert any("progress 回落" in m for m in logs), f"应按 live 基线 0.9 判回落: {logs}"
    assert mgr.state["recheck_fails"]["HA"]["count"] == 1, "回落判败应计冷却"
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
    """测试: 宽限耗尽仍未见 checking(web 源) -> 仲裁直查见非校验态(live 应答 = 暂停种子)判败
    防活锁, 不计冷却(origin=None 直接消亡); 判败原语义保持(S2b)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client)  # client.torrents["HA"] = t: 仲裁直查的 live 应答(pausedDL 非校验态)
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
    assert client.info_calls == 2, f"提交点 live 1 次(P1) + 仲裁直查恰一次(fail-closed 落判败): {client.info_calls}"


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

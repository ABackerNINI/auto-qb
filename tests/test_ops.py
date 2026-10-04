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
- test_ops_web_recheck_poll_torrent_deleted_no_origin: 轮询期间种子删除且无 origin -> 消亡无重入队副作用 (P2-a)
- test_ops_web_recheck_start_giveup_timeout: 宽限耗尽仲裁直查见非校验态(web 源, S2b 补 live 应答) -> 判败不计冷却 (P2-a)
- test_ops_recheck_poll_exception_releases_and_requeues: 轮询异常 -> 释放在途; rule 源 origin 重入队 (P2-a)
- test_ops_recheck_duplicate_task_guard: 登记点兜底 add_task 失败 -> skip 不发送 (P2-a)
- test_ops_skip_check_live_recheck_api_error: 跳检前实时复核 API 异常 -> fail 零副作用 (P2-a)
- test_ops_skip_gates_prune_stale_skip_day: 跳检同日去重表跨日残留清理 (P2-a)
- test_ops_infer_content_layout_empty_content: content_path 为空不推断布局 (P2-a)
- test_ops_clear_backup_noop_missing_path_and_oserror: _clear_backup 无元数据/path 空/删除失败三态 (P2-a)

跳检闸门扩展(plan 26-10-05-0314 S1b-1: 三分流 detail 单点 + force + 预检):
- test_skip_gates_rejects_completed: T1 已完成(做种态 p=1)拒, 文案含「已完成」, 零副作用
- test_skip_gates_rejects_active: T2 活跃中拒, 文案含「活跃」与「暂停」出路, 零副作用
- test_skip_gates_predicate_edge_states: T2b 边缘态逐态钉死 = state_enum.is_stopped 现有语义(同 checking.py:88 谓词)
- test_skip_gates_allows_paused_incomplete: T3 暂停未完成放行(辅种主场景, 防过严回归)
- test_skip_gates_rejects_group_downloading: T4 组内有活跃下载成员拒, 文案含「组内/下载」
- test_skip_gates_allows_group_all_paused: T5 组内全暂停/未归组放行(放行面锁)
- test_skip_check_rejects_inflight_recheck: T6 同 hash 校验在途拒, 文案含「校验中」, 零副作用
- test_skip_check_filelist_precondition_blocks: T7 文件缺失/路径不可判定拒(带 check_filelist 描述与 fs.path_map 出路), 未导出未删除
- test_skip_gates_rejects_group_checking_inflight: T16 组内其它成员校验在途(G7, case 2)两半各一例: 队列登记 / 快照 is_checking(用户手动 recheck, G5 队列视野外); 在途清空后放行; 零副作用 (S1b-2)
- test_skip_gates_rejects_group_check_failed: T17 组内成员校验失败推断(G8, case 1): 正样本文案带成员+出路; 负样本三例(映射不一致 / 记录指向已完成成员自愈不参与 / 非当日); 只读自愈不 pop; 零副作用 (S1b-2)
- test_skip_gates_detail_classification: T18 detail 三态归类 + 执行路径与 detail 首个未过闸门同源断言 + G7/G8 归类(G8 blocked 短路 filelist / G7 force 不短路)
- test_skip_check_force_semantics: T19 force 仅豁越 cls=force(G5/G7)并留 WARNING+INFO 审计; blocked(G3/G6/G8/filelist)一律硬拒; 签名缺省 False
- test_skip_check_precheck_readonly: T20 预检只读(state 深比对不变/去重表不写入不 prune/零写 API/种子零变动)+ gone 判定
"""
import copy
import inspect
import logging
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

from auto_qb.core.modules.ops_mod import OpsModule
from auto_qb.core.qbmanager import QbManager
from auto_qb.core.taskqueue import REQUEUE, Task, TaskQueue
from auto_qb.rules.actions import RECHECK_FAIL_LIMIT
from auto_qb.rules.actions.full_checking import bump_recheck_fail
from helpers import FakeClient, FakeConfig, FakeTorrent, capture_logs, seed_store

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


@contextmanager
def capture_ops_logs(level=logging.DEBUG):
    """ops_mod 模块日志消息捕获 —— 统一实现已上移 helpers.capture_logs(issue 26-10-04-2311),
    本地只保消息列表形状, 既有用例零改动。不用 caplog 的原因见 capture_logs docstring。"""
    with capture_logs("auto_qb.core.modules.ops_mod", level) as cap:
        yield cap.messages


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


# ============================================================
# E. 跳检闸门扩展(plan 26-10-05-0314 S1b-1): 三分流 detail 单点 + force 语义 + 只读预检
#    谓词单点在 ops._skip_gates_detail; 规则侧决策链 0/1 恒先于 ops 调用, 新闸门对规则源等价 no-op
# ============================================================
def wire_group(mgr, key, *hashes):
    """把若干 hash 直写进 store 分组索引(group_has_downloading 的判定数据源)"""
    for h in hashes:
        mgr.store.member_to_key[h] = key
    mgr.store.groups[key] = list(hashes)


def seed_inflight(mgr, hash_):
    """登记一个在途校验(active_check_hashes 的判定数据源, 即 G5 的视野)"""
    task = Task("check", "check-checking-result", hash=hash_, store=mgr.store, handler=lambda t, d: REQUEUE)
    assert mgr.task_queue.add_task(task)


def test_skip_gates_rejects_completed():
    """测试(T1): 已完成种子(做种态 p=1)跳检被拒, 文案含「已完成」; 零副作用(无去重记录/无备份/无写 API)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="pausedUP", progress=1.0)  # 做种态 p=1 -> 落 G3
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "已完成" in r.message, f"已完成应被拒: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"


def test_skip_gates_rejects_active():
    """测试(T2): 活跃中(下载中, 非 stopped 且 p<1)跳检被拒, 文案含「活跃」与「暂停」出路; 零副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stalledDL", progress=0.5)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "活跃" in r.message and "暂停" in r.message, f"活跃中应被拒且给出路: {r}"
    assert client.calls == [], f"拒绝零副作用: {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"


def test_skip_gates_predicate_edge_states():
    """测试(T2b, 口径锁): 边缘态逐态钉死 —— G3/G4 判定就是 state_enum.is_stopped and progress < 1.0
    (逐字同 checking.py:88), 不发明 WEB 特有口径: p=1 无论状态落 G3; p<1 非 stopped 落 G4;
    p<1 stopped 放行"""
    from qbittorrentapi import TorrentState

    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ops = mgr.ctx.ops
    stopped_states = ["pausedDL", "stoppedDL", "pausedUP", "stoppedUP"]
    non_stopped_states = [
        "downloading",
        "metaDL",
        "forcedDL",
        "forcedMetaDL",
        "stalledDL",
        "queuedDL",
        "checkingDL",
        "checkingResumeData",
        "uploading",
        "forcedUP",
        "stalledUP",
        "queuedUP",
        "allocating",
        "moving",
        "error",
        "missingFiles",
        "unknown",
    ]
    # 钉死测试自己的状态清单与枚举语义一致(清单漂移即红, 防用例口径失真)
    for s in stopped_states:
        assert TorrentState(s).is_stopped, f"{s} 应 is_stopped"
    for s in non_stopped_states:
        assert not TorrentState(s).is_stopped, f"{s} 应非 is_stopped"

    def g6_may_cofire(state):  # store.group_has_downloading 对未归组种子判自身(S1a 语义, 下载中谓词)
        ts = TorrentState(state)
        return ts.is_downloading and not ts.is_stopped and not ts.is_checking

    for state in non_stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=0.0)
        seed_store(mgr, [t])
        vs = ops._skip_gates_detail("HA", t)
        expected = ["G4"] + (["G6"] if g6_may_cofire(state) else [])
        assert [v.gate for v in vs] == expected, f"{state} p=0 应落 G4(非 stopped): {vs}"
        assert all(v.cls == "blocked" for v in vs), f"G4/G6 是 case 1 硬闸: {vs}"
    for state in stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=0.0)
        seed_store(mgr, [t])
        assert ops._skip_gates_detail("HA", t) == [], f"{state} p=0 应放行(stopped 且 p<1): 同规则侧口径"
    for state in non_stopped_states + stopped_states:
        t = FakeTorrent(hash="HA", state=state, progress=1.0)
        seed_store(mgr, [t])
        vs = ops._skip_gates_detail("HA", t)
        expected = ["G3"] + (["G6"] if g6_may_cofire(state) else [])
        assert [v.gate for v in vs] == expected, f"{state} p=1 应落 G3(已完成无论状态, 做种态同): {vs}"


def test_skip_gates_allows_paused_incomplete():
    """测试(T3, 放行面锁): 暂停未完成(stoppedDL p=0)闸门全过且整条跳检成功 —— 辅种主场景防过严回归"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HASH123", state="stoppedDL", progress=0.0)
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t
    assert mgr.ctx.ops._skip_gates_detail("HASH123", t) == [], "暂停未完成应过全部闸门(辅种主场景)"
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_ok, f"暂停未完成应放行完成跳检: {r}"


def test_skip_gates_rejects_group_downloading():
    """测试(T4): 组内有活跃下载成员跳检被拒(共享物理文件被写, 跳检标全部块有效 = 脏数据), 文案含「组内/下载」"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="downloading", progress=0.3)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "组内" in r.message and "下载" in r.message, f"组内有下载应被拒: {r}"
    assert client.calls == [], f"拒绝零副作用: {client.calls}"


def test_skip_gates_allows_group_all_paused():
    """测试(T5, 放行面锁): 组内全暂停/已完成放行; 未归组(单种子)放行"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="stoppedUP", progress=1.0)  # 组内做种态不是「下载中」
    hc = FakeTorrent(hash="HC", state="pausedDL", progress=0.0)  # 未归组
    seed_store(mgr, [ha, hb, hc])
    wire_group(mgr, "K", "HA", "HB")
    ops = mgr.ctx.ops
    assert ops._skip_gates_detail("HA", ha) == [], "组内全暂停/已完成应放行"
    assert ops._skip_gates_detail("HC", hc) == [], "未归组应放行"
    assert ops._skip_gates("HC", hc) is None, "执行路径全过应返回 None"


def test_skip_check_rejects_inflight_recheck():
    """测试(T6): 同 hash 校验在途(队列登记)跳检被拒 —— 跳检删种会杀死在途校验; 文案含「校验中」;
    零副作用(不删种/无备份/无去重记录)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    seed_inflight(mgr, "HASH123")
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "校验中" in r.message, f"在途校验应拒绝: {r}"
    assert not any(c[0] in ("export", "delete", "add") for c in client.calls), f"拒绝零副作用: {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"


def test_skip_check_filelist_precondition_blocks():
    """测试(T7): 前置文件检查并入执行链(R2 之后、导出之前) —— 文件缺失 is_failed 带 check_filelist
    描述且未导出未删除; 路径不可判定(映射 miss)保守 blocked 且文案自带「修 fs.path_map 配置」出路"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    client.files = [SimpleNamespace(name="missing.bin", size=123)]  # 磁盘上不存在 -> check_filelist 报缺失
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "前置文件检查未通过" in r.message and "文件缺失: missing.bin" in r.message, \
        f"文件缺失应带 check_filelist 描述拒绝: {r}"
    assert not any(c[0] in ("export", "delete", "add") for c in client.calls), \
        f"文件缺失零副作用(未导出未删除, R2 与文件检查都在不可逆步骤前): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"

    # 映射 miss(存在性不可判定): 保守 blocked, 出路文案指向 fs.path_map 配置
    from auto_qb.infra import file_access as fa_mod

    class _UndeterminedFA:
        def exists(self, path):
            return fa_mod.UNDETERMINED

    real_get = fa_mod.get_file_access
    fa_mod.get_file_access = lambda: _UndeterminedFA()  # ops_mod.file_access 是同一模块对象, 单点替换即生效
    try:
        r2 = mgr.ctx.ops.skip_check("HASH123", source="web")
    finally:
        fa_mod.get_file_access = real_get
    assert r2.is_failed and "路径不可判定" in r2.message and "修正 fs.path_map 配置" in r2.message, \
        f"映射 miss 应保守 blocked 且给出路: {r2}"


# ============================================================
# E2. 组内镜像闸门(plan 26-10-05-0314 S1b-2): G7 镜像决策链 1.5 others_checking /
#     G8 镜像决策链 1.6 四要件(假失败自愈只读变体) —— 谓词逐字同规则侧, 规则源零变化
# ============================================================
def test_skip_gates_rejects_group_checking_inflight():
    """测试(T16): 组内其它成员 full-checking 在途(G7, case 2)拒 —— 两半视野各一例:
    队列登记(active_check_hashes, 规则发起)与 store 快照 is_checking(用户手动 recheck,
    G5 的队列视野看不见它); 文案含「校验中」; 在途清空后放行; 零副作用"""
    # 半 1: 队列登记半(规则发起的校验经 recheck 在途登记可见)
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    seed_inflight(mgr, "HB")
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "校验中" in r.message, f"组员在途(队列登记)应拒: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"
    # 在途清空后放行(detail 空表 + 整条跳检成功)
    mgr.task_queue = TaskQueue()
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "在途清空后应过全部闸门"
    r2 = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r2.is_ok, f"在途清空后跳检应放行完成: {r2}"

    # 半 2: store 快照 is_checking 半(用户手动 recheck: 队列无登记, 只在快照可见)
    mgr_b = make_mgr(FakeConfig())
    client_b = FakeClient()
    mgr_b.client = client_b
    ha_b = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb_b = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr_b, [ha_b, hb_b])
    client_b.torrents["HASH123"] = ha_b
    client_b.torrents["HB"] = hb_b
    wire_group(mgr_b, "K", "HASH123", "HB")
    hb_b.state = "checkingDL"
    assert "HB" not in mgr_b.task_queue.active_check_hashes(), "半 2 前提: 队列无登记(G5 视野外)"
    vs = mgr_b.ctx.ops._skip_gates_detail("HASH123", ha_b)
    assert [v.gate for v in vs] == ["G7"], f"快照 is_checking 半应只落 G7: {vs}"
    r3 = mgr_b.ctx.ops.skip_check("HASH123", source="web")
    assert r3.is_failed and "校验中" in r3.message, f"组员在途(快照)应拒: {r3}"
    hb_b.state = "pausedDL"
    assert mgr_b.ctx.ops._skip_gates_detail("HASH123", ha_b) == [], "快照退出校验态后应放行"


def test_skip_gates_rejects_group_check_failed():
    """测试(T17): 组内成员校验失败推断(G8, case 1) —— 其它成员当日 recheck_fails>0 且文件映射一致
    -> 拒, 文案含「校验失败」与 full-checking 出路; 负样本三例: 文件映射不一致放行 / 记录指向
    已完成成员放行(假失败自愈不参与) / 非当日放行; G8 路径不 pop 记录(只读自愈, 清理归规则侧);
    零副作用"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr, [ha, hb])
    client.torrents["HASH123"] = ha
    client.torrents["HB"] = hb
    wire_group(mgr, "K", "HASH123", "HB")
    key = mgr.store.member_to_key["HASH123"]
    mgr.store.group_sizes.setdefault(key, {})["HASH123"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 1}
    fails_before = copy.deepcopy(mgr.state["recheck_fails"])

    # 正样本: G8 blocked, 文案带成员 hash8 与出路
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "校验失败" in r.message and "文件映射一致" in r.message, f"组员当日失败应拒: {r}"
    assert "HB" in r.message and "full-checking" in r.message, f"文案应带成员与出路: {r}"
    assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "拒绝不得写同日去重"
    assert not mgr.state.get("skip_check_backup"), "拒绝不得留备份元数据"
    assert mgr.state["recheck_fails"] == fails_before, "G8 路径不得改写 recheck_fails(零副作用)"

    # 负样本 1: 文件映射不一致(组内大小有差异, 校验的是不同数据) -> 不推断, 放行
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 200}
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "映射不一致应放行"
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}

    # 负样本 2: 记录指向已完成成员(假失败自愈: 与数据无关) -> 不参与推断, 且不 pop(只读变体)
    hb.state, hb.progress = "pausedUP", 1.0
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "已完成成员的失败记录应自愈放行"
    assert "HB" in mgr.state["recheck_fails"], \
        "G8 只读自愈不得 pop 记录(规则侧 full_checking.py:146 会 pop, 清理归规则侧与次日重置)"

    # 负样本 3: 非当日(次日重置口径) -> 放行
    hb.state, hb.progress = "pausedDL", 0.0
    mgr.state["recheck_fails"]["HB"] = {"date": "2000-01-01", "count": 1}
    assert mgr.ctx.ops._skip_gates_detail("HASH123", ha) == [], "非当日记录应放行"


def test_skip_gates_detail_classification():
    """测试(T18): _skip_gates_detail 三态归类 —— G5/G7->force; G3/G4/G6/G8/filelist/partial/dedup
    -> blocked; 全过->空; 执行路径 _skip_gates 与 detail 首个未过闸门一致(同源断言, 防两套谓词漂移;
    dedup 沿用 skip 形态、其余 fail 形态)。G7/G8(S1b-2)归入: G8 blocked 短路 filelist / G7 force 不短路"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    ops = mgr.ctx.ops
    today = date.today().isoformat()

    def fresh(state, progress, hash_):
        t = FakeTorrent(hash=hash_, state=state, progress=progress)
        seed_store(mgr, [t])
        return t

    def gates(hash_, t):
        return [(v.gate, v.cls) for v in ops._skip_gates_detail(hash_, t)]

    # G3 已完成(做种态) -> blocked
    t = fresh("pausedUP", 1.0, "G3HA")
    assert gates("G3HA", t) == [("G3", "blocked")]
    # G4 活跃中 -> blocked(p=0 不触发 partial; 未归组下载态并发命中 G6, 自身即下载方, S1a 语义)
    t = fresh("downloading", 0.0, "G4HB")
    assert gates("G4HB", t) == [("G4", "blocked"), ("G6", "blocked")]
    # G5 同 hash 校验在途 -> force(case 2; G7 组内在途同归 force)
    t = fresh("pausedDL", 0.0, "G5HC")
    seed_inflight(mgr, "G5HC")
    assert gates("G5HC", t) == [("G5", "force")]
    r = ops._skip_gates("G5HC", t)
    assert r.is_failed and "校验中" in r.message, f"force 类闸门缺省仍硬拒: {r}"
    # G6 组内活跃下载 -> blocked
    t = fresh("pausedDL", 0.0, "G6HD")
    hb = FakeTorrent(hash="G6HE", state="downloading", progress=0.3)
    seed_store(mgr, [t, hb])
    wire_group(mgr, "K6", "G6HD", "G6HE")
    assert gates("G6HD", t) == [("G6", "blocked")]
    # G7 组内其它成员校验在途 -> force(队列登记半); force 类不短路 filelist(缺失文件先设:
    # 文件列表是记录级惰性缓存, 首次 filelist 即定型, 之后改 client.files 不影响已缓存记录)
    t = fresh("pausedDL", 0.0, "G7HJ")
    hb7 = FakeTorrent(hash="G7HK", state="pausedDL", progress=0.0)
    seed_store(mgr, [t, hb7])
    wire_group(mgr, "K7", "G7HJ", "G7HK")
    seed_inflight(mgr, "G7HK")
    client.files = [SimpleNamespace(name="x.bin", size=1)]  # filelist 若真跑必 fail
    assert gates("G7HJ", t) == [("G7", "force"), ("filelist", "blocked")], \
        "G7 是 force 类, filelist 不得被短路(force 豁越后 case 1 硬闸仍须真跑)"
    client.files = []
    t2 = fresh("pausedDL", 0.0, "G7HN")  # 新记录: 旧记录已把缺失文件缓存进惰性列表, 换记录钉纯 G7 归类
    seed_store(mgr, [t2, hb7])
    wire_group(mgr, "K7", "G7HN", "G7HK")
    assert gates("G7HN", t2) == [("G7", "force")]
    mgr.task_queue = TaskQueue()  # 清在途登记, 换快照半: 用户手动 recheck(队列无登记)
    hb7.state = "checkingDL"
    assert gates("G7HN", t2) == [("G7", "force")]
    hb7.state = "pausedDL"
    # G8 组内成员校验失败推断 -> blocked(同映射 + 当日失败计数); blocked 短路 filelist
    t = fresh("pausedDL", 0.0, "G8HL")
    hb8 = FakeTorrent(hash="G8HM", state="pausedDL", progress=0.0)
    seed_store(mgr, [t, hb8])
    wire_group(mgr, "K8", "G8HL", "G8HM")
    key8 = mgr.store.member_to_key["G8HL"]
    mgr.store.group_sizes.setdefault(key8, {})["G8HL"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key8]["G8HM"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["G8HM"] = {"date": today, "count": 1}
    client.files = [SimpleNamespace(name="x.bin", size=1)]  # filelist 若真跑必 fail
    fc8 = client.files_calls
    assert gates("G8HL", t) == [("G8", "blocked")], "G8 blocked 应短路 filelist(结论已注定)"
    assert client.files_calls == fc8, "G8 未过时 filelist 不得真跑(短路省 files API)"
    client.files = []
    # partial 部分下载 -> blocked(既有闸门并入 detail, 语义文案零变化)
    t = fresh("pausedDL", 0.5, "PRTF")
    assert gates("PRTF", t) == [("partial", "blocked")]
    # dedup 同日去重 -> blocked(既有闸门并入 detail; 执行路径沿用 skip 形态)
    t = fresh("pausedDL", 0.0, "DDPHG")
    mgr.state.setdefault("skip_check_day", {})["DDPHG"] = today
    assert gates("DDPHG", t) == [("dedup", "blocked")]
    r = ops._skip_gates("DDPHG", t)
    assert r.is_skipped and r.message == ops._skip_gates_detail("DDPHG", t)[0].text, \
        f"执行路径 dedup 应沿用 skip 形态且文案同源: {r}"
    # filelist 前置文件检查 -> blocked(排最后)
    t = fresh("pausedDL", 0.0, "FLHH")
    client.files = [SimpleNamespace(name="x.bin", size=1)]
    assert gates("FLHH", t) == [("filelist", "blocked")]
    client.files = []
    # 全过 -> 空列表; 执行路径 None
    t = fresh("pausedDL", 0.0, "OKHI")
    assert gates("OKHI", t) == []
    assert ops._skip_gates("OKHI", t) is None
    # 同源断言(混合场景): 活跃部分下载 -> detail 按固定顺序(G4 -> G6 -> partial), 执行路径取首个
    t = fresh("downloading", 0.5, "MXHJ")
    vs = ops._skip_gates_detail("MXHJ", t)
    assert [(v.gate, v.cls) for v in vs] == [("G4", "blocked"), ("G6", "blocked"), ("partial", "blocked")], \
        f"固定顺序: {vs}"
    r = ops._skip_gates("MXHJ", t)
    assert r.is_failed and r.message == vs[0].text, f"执行路径应取首个未过闸门(同源): {r} vs {vs[0]}"


def test_skip_check_force_semantics():
    """测试(T19): force 语义 —— force=True 仅豁越 cls=force 的未过闸门(G5/G7: WARNING 降级 +
    INFO 审计后放行成功); cls=blocked(G3/G6/G8/filelist)即使 force=True 仍硬拒带原文案;
    缺省 force=False 全拒(T6 已覆盖); 规则侧调用点不传 force 由签名缺省证明(零变化不变式)"""
    # G5 场景 force=True: 豁越放行成功, 留 WARNING(闸门降级) + INFO(审计: hash + 闸门)
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")
    seed_inflight(mgr, "HASH123")
    with capture_logs("auto_qb.core.modules.ops_mod", logging.DEBUG) as cap:
        r = mgr.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r.is_ok, f"force=True 应豁越 G5 放行: {r}"
    warns = [x.getMessage() for x in cap.records if x.levelname == "WARNING"]
    audits = [x.getMessage() for x in cap.records if x.levelname == "INFO"]
    assert any("force 豁越跳检闸门 G5" in m for m in warns), f"豁越闸门应留 WARNING: {warns}"
    assert any("force 审计" in m and "G5" in m and "HASH123" in m for m in audits), \
        f"豁越应留 INFO 审计(hash+闸门): {audits}"
    assert mgr.state["skip_check_day"]["HASH123"] == date.today().isoformat(), "豁越后跳检应真实完成"

    # G3 已完成 + force=True: case 1 硬拒带原文案
    mgr2 = make_mgr(FakeConfig())
    client2 = FakeClient()
    mgr2.client = client2
    t2 = FakeTorrent(hash="HASH123", state="pausedUP", progress=1.0)
    seed_store(mgr2, [t2])
    client2.torrents["HASH123"] = t2
    r2 = mgr2.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r2.is_failed and "已完成" in r2.message, f"blocked 闸门对 force 硬拒: {r2}"

    # G6 组内下载 + force=True: 仍硬拒
    mgr3 = make_mgr(FakeConfig())
    client3 = FakeClient()
    mgr3.client = client3
    ha = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb = FakeTorrent(hash="HB", state="downloading", progress=0.3)
    seed_store(mgr3, [ha, hb])
    client3.torrents["HASH123"] = ha
    client3.torrents["HB"] = hb
    wire_group(mgr3, "K", "HASH123", "HB")
    r3 = mgr3.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r3.is_failed and "组内" in r3.message, f"G6 对 force 硬拒: {r3}"

    # filelist + force=True: 仍硬拒(证据缺失不给 force)
    mgr4 = make_mgr(FakeConfig())
    client4 = FakeClient()
    mgr4.client = client4
    seed_paused(mgr4, client4, hash="HASH123")
    client4.files = [SimpleNamespace(name="missing.bin", size=1)]
    r4 = mgr4.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r4.is_failed and "前置文件检查未通过" in r4.message, f"filelist 对 force 硬拒: {r4}"

    # 缺省 force=False: G5 场景硬拒(与上面 force=True 成对照)
    mgr5 = make_mgr(FakeConfig())
    client5 = FakeClient()
    mgr5.client = client5
    seed_paused(mgr5, client5, hash="HASH123")
    seed_inflight(mgr5, "HASH123")
    r5 = mgr5.ctx.ops.skip_check("HASH123", source="web")
    assert r5.is_failed and "校验中" in r5.message, f"缺省 force=False 应硬拒: {r5}"

    # G7 组内校验在途 + force=True: 豁越放行(与 G5 同款, WARNING 降级 + INFO 审计)
    mgr6 = make_mgr(FakeConfig())
    client6 = FakeClient()
    mgr6.client = client6
    ha6 = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb6 = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr6, [ha6, hb6])
    client6.torrents["HASH123"] = ha6
    client6.torrents["HB"] = hb6
    wire_group(mgr6, "K", "HASH123", "HB")
    seed_inflight(mgr6, "HB")
    with capture_logs("auto_qb.core.modules.ops_mod", logging.DEBUG) as cap6:
        r6 = mgr6.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r6.is_ok, f"force=True 应豁越 G7 放行: {r6}"
    warns6 = [x.getMessage() for x in cap6.records if x.levelname == "WARNING"]
    audits6 = [x.getMessage() for x in cap6.records if x.levelname == "INFO"]
    assert any("force 豁越跳检闸门 G7" in m for m in warns6), f"G7 豁越应留 WARNING: {warns6}"
    assert any("force 审计" in m and "G7" in m and "HASH123" in m for m in audits6), \
        f"G7 豁越应留 INFO 审计(hash+闸门): {audits6}"

    # G8 组内校验失败推断 + force=True: case 1 仍硬拒带原文案
    mgr7 = make_mgr(FakeConfig())
    client7 = FakeClient()
    mgr7.client = client7
    ha7 = FakeTorrent(hash="HASH123", state="pausedDL", progress=0.0)
    hb7 = FakeTorrent(hash="HB", state="pausedDL", progress=0.0)
    seed_store(mgr7, [ha7, hb7])
    client7.torrents["HASH123"] = ha7
    client7.torrents["HB"] = hb7
    wire_group(mgr7, "K", "HASH123", "HB")
    key7 = mgr7.store.member_to_key["HASH123"]
    mgr7.store.group_sizes.setdefault(key7, {})["HASH123"] = {"movie.mkv": 100}
    mgr7.store.group_sizes[key7]["HB"] = {"movie.mkv": 100}
    mgr7.state.setdefault("recheck_fails", {})["HB"] = {"date": date.today().isoformat(), "count": 1}
    r7 = mgr7.ctx.ops.skip_check("HASH123", source="web", force=True)
    assert r7.is_failed and "校验失败" in r7.message and "full-checking" in r7.message, \
        f"G8 对 force 硬拒带原文案: {r7}"
    assert client7.calls == [], f"G8 硬拒零副作用: {client7.calls}"

    # 规则侧零变化证明: 签名缺省 False, 规则调用点(skip_checking.py)不传即零变化
    assert inspect.signature(OpsModule.skip_check).parameters["force"].default is False


def test_skip_check_precheck_readonly():
    """测试(T20): 预检只读 —— 调用前后 ops.state 深比对不变(skip_check_day 不写入不 prune)、
    零写 API(mock 断言仅只读面)、种子零变动; 回执字段命名对齐 S2 形状; gone 判定文案「已不在客户端」"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = seed_paused(mgr, client, hash="HASH123")  # ok 样本
    t2 = FakeTorrent(hash="HDONE", state="pausedUP", progress=1.0)  # blocked 样本(G3)
    seed_store(mgr, [t, t2])
    client.torrents["HDONE"] = t2
    mgr.state.setdefault("skip_check_day", {})["STALE"] = "2000-01-01"  # prune 若误入 detail 此处必红
    before = copy.deepcopy(mgr.state)
    info_before, files_before = client.info_calls, client.files_calls

    results = mgr.ctx.ops.skip_check_precheck(["HASH123", "HDONE", "HMISSING"])

    # 回执形状(S2 将包成 {results, summary}; 单 hash: hash/name/cls/reasons)
    assert [x["hash"] for x in results] == ["HASH123", "HDONE", "HMISSING"]
    assert results[0]["cls"] == "ok" and results[0]["reasons"] == [] and results[0]["name"] == "Test"
    assert results[1]["cls"] == "blocked", f"已完成样本应 blocked: {results[1]}"
    assert results[1]["reasons"][0]["gate"] == "G3" and "已完成" in results[1]["reasons"][0]["text"]
    assert results[2]["cls"] == "blocked" and results[2]["reasons"][0]["gate"] == "gone"
    assert "已不在客户端" in results[2]["reasons"][0]["text"], f"gone 文案 T21 依赖: {results[2]}"

    # 只读面: 零写 API; 预检不拉 live(info_calls 不增); files_calls 恰 +1(HDONE 被 G3 短路 filelist)
    assert client.calls == [], f"预检不得调任何写 API: {client.calls}"
    assert client.info_calls == info_before, f"预检不得直查 torrents_info: {client.info_calls}"
    assert client.files_calls - files_before == 1, \
        f"filelist 仅对无 blocked 闸门的样本运行(短路省成本): {client.files_calls}"

    # state 深比对不变: 去重表不写入、不 prune(执行路径专属副作用不得泄入预检)
    assert mgr.state == before, f"预检后 state 必须逐字节不变: {mgr.state}"
    assert mgr.state["skip_check_day"]["STALE"] == "2000-01-01", "跨日残留不得被预检清理(零副作用铁律)"

    # 种子零变动
    assert t.state == "pausedDL" and t.progress == 0.0 and t2.state == "pausedUP" and t2.progress == 1.0
    assert client.torrents["HASH123"] is t and client.torrents["HDONE"] is t2

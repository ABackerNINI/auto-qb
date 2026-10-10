"""test_hr_queue 测试计划: 任务队列(端点线程与取数线程的唯一交接面)

## 测试计划(每个测试函数一条)
- test_put_dedups_same_url: 同一 (站点, 类型, URL) 重复 put 复用同一条任务(不重复派发)
- test_take_batch_marks_dispatched_once: 派发过的任务不再重复给(扩展不会拿到同一条两次)
- test_take_batch_respects_limit: 单批上限生效
- test_submit_accepts_only_dispatched_task: 未派发 / 未登记的任务 id -> False(防伪造注入)
- test_wait_returns_result_and_consumes_it: 等待方被唤醒拿到结果, 结果被取走(不堆积)
- test_wait_timeout_retires_task: 超时 -> None 并作废任务; 之后晚到的回传被拒
- test_submit_rejects_foreign_host: 回传 URL 域名与任务不符 -> 拒(结果不入表)
- test_ttl_expires_task: 假时钟推进超过 TTL -> 任务作废(扩展拿到任务后就死了不永久占用)
- test_stats_and_pending_are_observable: 观测口径(outstanding/results/pending)
- test_abort_clears_task: 显式放弃单条等待
- test_cancel_all_wakes_waiters: 叫停 -> 等待方立刻醒来(不等满超时), 表清空且晚到回传被拒
- test_resume_clears_cancel: 恢复后能重新正常等回传(重启/热重载靠它)

### P1 覆盖率提升轮: 结果 TTL 长尾
- test_ttl_expires_unclaimed_results: 没人取走的回执超 TTL 清空
- test_received_at_missing_does_not_crash_expiry: received_at=0 按当下起算不立刻过期

### R17 变异审计补测(队列边界与防伪造)
- test_queue_initial_cancel_reason_is_empty: 初始叫停原因为空串(区分「被叫停」与「正常」)
- test_queue_put_defaults_and_task_id_length: put 的 scope/tid 默认值 + task_id 固定 16 位
- test_queue_take_batch_limit_one: 单批上限 1 生效(下界 max(1, limit))
- test_queue_cancel_all_default_reason_and_epoch_bumps: cancel_all 默认原因 + 每次推代 +=1
- test_queue_resume_epoch_bumps: resume 每次推代 +=1
- test_queue_abort_unknown_id_is_noop: abort 未登记 id 不抛(出错清理路径可能拿到作废 id)
- test_queue_abort_drops_stored_result: abort 同时清掉已回传结果
- test_queue_submit_fills_missing_url_from_task: 回传缺 URL 用任务原 URL 补齐(or 回落)
- test_queue_submit_clears_outstanding: 回传入账后 outstanding 清掉
- test_queue_ttl_boundary_exact_is_kept: TTL 严格 >(恰到期不作废), 任务与结果两侧
- test_queue_small_clock_values_still_work: 假时钟 0..1 之间的小值不被当「未派发」
- test_queue_expire_uses_small_dispatched_at: 小派发时刻也参与 TTL 作废
- test_queue_wait_aborts_on_epoch_change_without_retiring: 代变即放弃等待但不作废任务
- test_queue_wait_zero_timeout_returns_immediately: timeout<=0 不阻塞(预算下界 0 而非 1)
- test_queue_wait_blocks_for_sub_second_timeout: timeout 在 (0,1] 秒也要真的等到点
"""
import threading
import time

from auto_qb.hr.channel import TASK_PAGE, TASK_TORRENT, HrResult
from auto_qb.hr.queue import HrTaskQueue
from hr_helpers import Clock

URL = "https://pt.example.com/myhr.php?hrtype=A"
DL = "https://pt.example.com/download.php?id=313852"


def test_put_dedups_same_url():
    queue = HrTaskQueue()
    first = queue.put("pt.example.com", TASK_PAGE, URL)
    second = queue.put("pt.example.com", TASK_PAGE, URL)
    assert first.task_id == second.task_id
    assert len(queue.take_batch()) == 1, "同一 URL 只派发一条"


def test_take_batch_marks_dispatched_once():
    queue = HrTaskQueue()
    queue.put("pt.example.com", TASK_PAGE, URL)
    first = queue.take_batch()
    assert len(first) == 1
    assert first[0].dispatched_at > 0, "派发时刻要记下来(TTL 与排障都靠它)"
    assert queue.take_batch() == [], "已派发的任务不再重复给(扩展正在取, 或上次那轮没回来)"


def test_take_batch_respects_limit():
    queue = HrTaskQueue()
    for page in range(1, 5):
        queue.put("pt.example.com", TASK_PAGE, f"{URL}&page={page}")
    assert len(queue.take_batch(limit=2)) == 2
    assert len(queue.take_batch(limit=2)) == 2, "上一批只派了 2 条, 剩下的接着派"
    assert queue.take_batch() == [], "四条都已派发"


def test_submit_accepts_only_dispatched_task():
    queue = HrTaskQueue()
    assert queue.submit(HrResult(task_id="ghost", ok=False)) is False, "没登记过的 id 一律拒"
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    assert queue.submit(HrResult(task_id=task.task_id, ok=False)) is False, "还没派发出去, 不接受"
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is True


def test_wait_returns_result_and_consumes_it():
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"<html/>"))
    got = queue.wait(task.task_id, 1.0)
    assert got is not None and got.body == b"<html/>"
    assert queue.stats()["results"] == 0, "结果被取走后不残留"


def test_wait_timeout_retires_task():
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_TORRENT, DL)
    queue.take_batch()
    assert queue.wait(task.task_id, 0.05) is None
    assert queue.pending() == 0, "超时即作废"
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=DL, body=b"z")) is False, "晚到的回传被拒"


def test_submit_rejects_foreign_host():
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url="https://evil.example.com/myhr.php")) is False
    assert queue.stats()["results"] == 0
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"ok")) is True


def test_ttl_expires_task():
    clock = Clock()
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    clock.advance(11.0)
    assert queue.pending() == 0, "超过 TTL 的任务作废(下一轮重排)"
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL)) is False


def test_stats_and_pending_are_observable():
    queue = HrTaskQueue()
    assert queue.stats() == {"outstanding": 0, "results": 0}
    queue.put("pt.example.com", TASK_PAGE, URL)
    assert queue.pending() == 1
    queue.take_batch()
    assert queue.pending() == 1, "派发出去还没回来, 仍算未完成"


def test_abort_clears_task():
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    queue.abort(task.task_id)
    assert queue.pending() == 0
    assert queue.wait(task.task_id, 0.05) is None


def test_cancel_all_wakes_waiters():
    """取数线程正阻塞等扩展回传时, 关停必须能立刻叫醒它(否则白等 request_timeout 且持着站点锁)"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    got = {}

    def waiter():
        got["result"] = queue.wait(task.task_id, 30.0)  # 本用例只该等毫秒级

    thread = threading.Thread(target=waiter, daemon=True)
    thread.start()
    for _ in range(100):
        if queue.pending() == 1:
            break
        threading.Event().wait(0.01)
    queue.cancel_all("停止中")
    thread.join(2.0)
    assert not thread.is_alive(), "等待方必须被立刻叫醒"
    assert got["result"] is None
    assert queue.cancel_reason == "停止中", "要能区分「被叫停」与「超时」(前者不该计入失败)"
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is False, "叫停后一切回传都拒"


def test_resume_clears_cancel():
    queue = HrTaskQueue()
    queue.cancel_all("停止中")
    assert queue.cancel_reason
    queue.resume()
    assert queue.cancel_reason == "", "重启后必须能重新正常等回传"
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"ok"))
    got = queue.wait(task.task_id, 1.0)
    assert got is not None and got.body == b"ok"


# ==================== P1 覆盖率提升轮: 结果 TTL 长尾 ====================


def test_ttl_expires_unclaimed_results():
    """已回传但没人取走的结果超 TTL 也清掉(两个方向都会自然到期, 不无限堆积)"""
    clock = Clock()
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"<html/>")) is True
    assert queue.stats()["results"] == 1
    clock.advance(11.0)
    stats = queue.stats()
    assert stats["results"] == 0, "没人取走的回执超 TTL 清空(经 stats 的 _expire_locked 生效)"


def test_received_at_missing_does_not_crash_expiry():
    """received_at 缺失(0)的回执按「当下」起算, 不立刻过期也不除零"""
    clock = Clock()
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    result = HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")
    result.received_at = 0.0
    assert queue.submit(result) is True
    clock.advance(5.0)
    assert queue.stats()["results"] == 1, "received_at=0 视为刚收到"


# ==================== R17 变异审计补测: 队列边界与防伪造 ====================


def test_queue_initial_cancel_reason_is_empty():
    """初始叫停原因为空串(调用方据此区分「被叫停」与「正常/超时」)"""
    assert HrTaskQueue().cancel_reason == ""


def test_queue_put_defaults_and_task_id_length():
    """put 默认 scope 空串 / tid 0; task_id 固定 16 位十六进制"""
    task = HrTaskQueue().put("pt.example.com", TASK_PAGE, URL)
    assert task.scope == "" and task.tid == 0
    assert len(task.task_id) == 16


def test_queue_take_batch_limit_one():
    """单批上限下界是 max(1, limit): limit=1 只派一条"""
    queue = HrTaskQueue()
    for page in (1, 2):
        queue.put("pt.example.com", TASK_PAGE, f"{URL}&page={page}")
    assert len(queue.take_batch(limit=1)) == 1


def test_queue_cancel_all_default_reason_and_epoch_bumps():
    """cancel_all 默认原因「已停止」; 每次叫停推进代 +=1(等待方据此识别叫停)"""
    queue = HrTaskQueue()
    queue.cancel_all()
    assert queue.cancel_reason == "已停止"
    assert queue._epoch == 1
    queue.cancel_all()
    assert queue._epoch == 2, "每次叫停都要推代(不是置 1 / 减 1 / 加 2)"


def test_queue_resume_epoch_bumps():
    """resume 每次推代 +=1(与 cancel_all 对称)"""
    queue = HrTaskQueue()
    queue.resume()
    queue.resume()
    assert queue._epoch == 2


def test_queue_abort_unknown_id_is_noop():
    """abort 对未登记的 id 不抛 KeyError(出错清理路径可能拿到已作废的 id)"""
    HrTaskQueue().abort("ghost")


def test_queue_abort_drops_stored_result():
    """abort 同时清掉已回传的结果(否则结果表留垃圾)"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is True
    assert queue.stats()["results"] == 1
    queue.abort(task.task_id)
    assert queue.stats()["results"] == 0


def test_queue_submit_fills_missing_url_from_task():
    """回传没带 URL 时用派发任务的原 URL 补齐(or 回落, 不是置 None / and 短路成空)"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url="", body=b"x")) is True
    got = queue.wait(task.task_id, 0.5)
    assert got is not None and got.url == URL


def test_queue_submit_clears_outstanding():
    """回传入账后 outstanding 要清掉(否则任务永久占位)"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is True
    assert queue.pending() == 0


def test_queue_ttl_boundary_exact_is_kept():
    """TTL 判定是严格 >(恰好到期不作废): 任务侧与结果侧都要"""
    clock = Clock()
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    queue.put("pt.example.com", TASK_PAGE, f"{URL}&page=2")
    queue.take_batch()
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is True
    clock.advance(10.0)  # 恰好 TTL
    assert queue.pending() == 1, "恰好到期不作废(严格 >)"
    assert queue.stats()["results"] == 1, "结果侧同样严格 >"


def test_queue_small_clock_values_still_work():
    """假时钟给 0..1 之间的小值: 派发标记与「未派发」闸都不能把 0.5 当 0"""
    clock = Clock(start=0.5)
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    assert len(queue.take_batch()) == 1
    assert queue.take_batch() == [], "派发过(0.5)不再重复派"
    assert queue.submit(HrResult(task_id=task.task_id, ok=True, url=URL, body=b"x")) is True, "0.5 是有效派发时刻"


def test_queue_expire_uses_small_dispatched_at():
    """小派发时刻(0.5)也参与 TTL 作废(不被「> 1」漏掉)"""
    clock = Clock(start=0.5)
    queue = HrTaskQueue(now_fn=clock, ttl=10.0)
    queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()  # dispatched_at = 0.5
    clock.advance(11.0)
    assert queue.pending() == 0


def test_queue_wait_aborts_on_epoch_change_without_retiring():
    """等待期间「代」变了且任务仍在 -> 放弃等待, 但**不**作废任务(epoch 分支不 pop)"""
    clock = Clock()
    queue = HrTaskQueue(now_fn=clock, ttl=100.0)
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    real_expire = queue._expire_locked
    calls = {"n": 0}

    def bump_epoch_once():
        if calls["n"] == 0:
            queue.resume()  # 只推代, 不清 outstanding(模拟 resume 竞态)
        calls["n"] += 1
        return real_expire()

    queue._expire_locked = bump_epoch_once
    assert queue.wait(task.task_id, 0.05) is None
    assert queue.pending() == 1, "代变即放弃等待, 但任务不作废(epoch 分支不 pop)"


def test_queue_wait_zero_timeout_returns_immediately():
    """timeout<=0 -> 不阻塞(等待预算下界是 max(0.0, timeout))"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    t0 = time.monotonic()
    assert queue.wait(task.task_id, 0.0) is None
    assert time.monotonic() - t0 < 0.5, "0 超时不得阻塞(变异会白等 1s)"


def test_queue_wait_blocks_for_sub_second_timeout():
    """timeout 在 (0,1] 秒区间也要真的等到点(等待预算不是「小于 1 秒就立即返回」)"""
    queue = HrTaskQueue()
    task = queue.put("pt.example.com", TASK_PAGE, URL)
    queue.take_batch()
    t0 = time.monotonic()
    assert queue.wait(task.task_id, 0.2) is None
    assert time.monotonic() - t0 >= 0.15, "0.2s 超时要真的等到点(变异会立即返回)"

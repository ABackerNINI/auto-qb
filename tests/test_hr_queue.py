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
"""
import threading

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

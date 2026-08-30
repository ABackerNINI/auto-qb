"""test_taskqueue 测试计划: 双任务队列

## 测试计划(每个测试函数一条)
- test_task_queue_schedule: 按 next_run 时间调度到期任务
- test_task_ordering: 堆排序按到期时间出队
- test_task_repr: Task 字符串表示
- test_submit_check_dedup: 校验任务去重
- test_poll_slow_flow: 慢速队列正常流转(pending -> waiting -> done)
- test_poll_slow_send_error: 慢速发送错误处理
- test_poll_slow_timeout: 慢速超时处理
- test_task_state_transitions: 任务状态迁移
- test_shutdown_blocks_submit: 关闭后拒绝提交
- test_add_tasks: add_tasks 批量入队立即到期
"""
import time

from auto_qb.taskqueue import DONE, PENDING, RUNNING, WAITING, Task, TaskQueue


def test_task_queue_schedule():
    """快速队列: 到期弹出 / interval<=0 归一化 / reschedule 按 interval 重入 / remove_torrent"""
    tq = TaskQueue(executor_workers=0)
    now = time.time()
    tq.add_task(Task("rule", "every_tick", interval=0), now=now)
    tq.add_task(Task("rule", "interval60", interval=60), now=now)
    due = tq.due(now)
    assert {t.name for t in due} == {"every_tick", "interval60"}, f"due={[t.name for t in due]}"
    assert [t for t in due if t.name == "every_tick"][0].interval == 1, "interval<=0 应归一化为 1"
    for t in due:
        tq.reschedule(t, now)
    assert [t.name for t in tq.due(now + 59)] == ["every_tick"], "59s 时只有 every_tick 到期"
    assert [t.name for t in tq.due(now + 60)] == ["interval60"], "60s 时 interval60 到期"
    tq.add_task(Task("torrent", "maintenance", torrent_hash="H1", interval=60), now=now)
    tq.remove_torrent("H1")
    assert tq.due(now + 61) == [], "remove_torrent 后任务应被移除"
    tq.shutdown()


def test_task_ordering():
    """Task.__lt__ 按 next_run 排序(堆结构依赖)"""
    t1 = Task("rule", "a", next_run=10)
    t2 = Task("rule", "b", next_run=5)
    t3 = Task("rule", "c", next_run=10)
    assert t2 < t1
    assert not t1 < t2
    assert not t1 < t3  # next_run 相同 -> 不比较(保持稳定)


def test_task_repr():
    t = Task("rule", "add_site_tag", torrent_hash="H1")
    assert repr(t) == "Task(rule, add_site_tag, H1, pending)"
    t.state = RUNNING
    assert "running" in repr(t)


def test_submit_check_dedup():
    """submit_check: 同一种子已有等待任务则忽略(返回 False)"""
    tq = TaskQueue(executor_workers=0)
    sent = []

    def send():
        sent.append(1)
        return "ok"

    assert tq.submit_check("H1", send) is True
    assert tq.submit_check("H1", send) is False, "同 hash 重复提交应被忽略"
    assert len(sent) == 1, "重复提交不应再次发送"
    tq.shutdown()


def test_poll_slow_flow():
    """poll_slow: 消费 result_q -> is_done 轮询 -> 完成出队并回调"""
    tq = TaskQueue(executor_workers=0)
    state = {"done": False}
    done_calls = []

    def send():
        return "recheck-sent"

    def is_done(h):
        return state["done"]

    def done_cb(task):
        done_calls.append(task.torrent_hash)

    tq.submit_check("H1", send, done_cb=done_cb)
    # 第 1 轮: 异步结果未回传 -> 不完成
    assert tq.poll_slow(is_done) == []
    assert tq.pending_slow() == ["H1"]
    # 第 2 轮: 请求已确认发出(sent), 但校验未完成
    assert tq.poll_slow(is_done) == []
    # 校验完成 -> 出队 + 回调
    state["done"] = True
    completed = tq.poll_slow(is_done)
    assert [t.torrent_hash for t in completed] == ["H1"]
    assert done_calls == ["H1"]
    assert tq.pending_slow() == []
    tq.shutdown()


def test_poll_slow_send_error():
    """发送失败: 任务立即完成并带 send_error"""
    tq = TaskQueue(executor_workers=0)

    def send():
        raise RuntimeError("send failed")

    tq.submit_check("H1", send)
    # 同步模式: 发送即回传结果, 一轮内完成
    completed = tq.poll_slow(lambda h: False)
    assert [t.torrent_hash for t in completed] == ["H1"]
    assert isinstance(completed[0].send_error, RuntimeError)
    tq.shutdown()


def test_poll_slow_timeout():
    """校验超时: timeout 到期强制完成"""
    tq = TaskQueue(executor_workers=0)
    done_calls = []

    def send():
        return "ok"

    tq.submit_check("H1", send, done_cb=lambda t: done_calls.append(t.torrent_hash), timeout=5)
    tq.poll_slow(lambda h: False)  # sent
    completed = tq.poll_slow(lambda h: False, now=time.time() + 10)  # 超时
    assert [t.torrent_hash for t in completed] == ["H1"]
    assert isinstance(completed[0].send_error, TimeoutError)
    assert done_calls == ["H1"]
    tq.shutdown()


def test_task_state_transitions():
    """任务状态流转: pending -> running(due) -> pending(reschedule) / waiting -> done(poll)"""
    tq = TaskQueue(executor_workers=0)
    now = time.time()
    t = Task("rule", "x", interval=60)
    assert t.state == PENDING
    tq.add_task(t, now=now)
    due = tq.due(now)
    assert due[0].state == RUNNING
    tq.reschedule(due[0], now)
    assert due[0].state == PENDING
    # 慢速队列状态
    tq2 = TaskQueue(executor_workers=0)
    tq2.submit_check("H1", lambda: None)
    assert tq2._slow["H1"].state == WAITING
    tq2.poll_slow(lambda h: True)
    assert tq2._slow == {}  # 已完成出队
    tq2.shutdown()


def test_shutdown_blocks_submit():
    """shutdown 后 submit_check 返回 False"""
    tq = TaskQueue(executor_workers=0)
    tq.shutdown()
    assert tq.submit_check("H1", lambda: None) is False


def test_add_tasks():
    """add_tasks: 批量入队, 全部立即到期"""
    tq = TaskQueue(executor_workers=0)
    now = time.time()
    tq.add_tasks([Task("rule", "a", interval=0), Task("rule", "b", interval=60)], now=now)
    assert {t.name for t in tq.due(now)} == {"a", "b"}
    tq.shutdown()

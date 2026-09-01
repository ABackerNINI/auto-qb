"""test_taskqueue 测试计划: 单任务队列

## 测试计划(每个测试函数一条)
- test_task_queue_schedule: 按 next_run 时间调度到期任务
- test_task_ordering: 堆排序按到期时间出队
- test_task_repr: Task 字符串表示
- test_task_state_transitions: 任务状态迁移(pending -> running -> pending)
- test_add_tasks: add_tasks 批量入队立即到期
- test_add_check_task_dedup: 校验轮询任务去重
- test_defer_resume: 让位/恢复(resume)语义: defer 不入队 -> resume 同一实例重新入队
- test_defer_resume_cb: resume 触发一次性完成处理(resume_cb)
- test_task_died_releases_check: 任务消亡释放校验标记
- test_remove_torrent_clears_active_check: 删除种子清理队列与校验标记
- test_remove_torrent_clears_deferred: 删除种子清理让位任务
"""
import time

from auto_qb.taskqueue import DEFERRED, PENDING, RUNNING, Task, TaskQueue


def test_task_queue_schedule():
    """队列: 到期弹出 / interval<=0 归一化 / reschedule 按 interval 重入 / remove_torrent"""
    tq = TaskQueue()
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


def test_task_state_transitions():
    """任务状态流转: pending -> running(due) -> pending(reschedule)"""
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", interval=60)
    assert t.state == PENDING
    tq.add_task(t, now=now)
    due = tq.due(now)
    assert due[0].state == RUNNING
    tq.reschedule(due[0], now)
    assert due[0].state == PENDING


def test_add_tasks():
    """add_tasks: 批量入队, 全部立即到期"""
    tq = TaskQueue()
    now = time.time()
    tq.add_tasks([Task("rule", "a", interval=0), Task("rule", "b", interval=60)], now=now)
    assert {t.name for t in tq.due(now)} == {"a", "b"}


def test_add_check_task_dedup():
    """add_check_task: 同一种子已有在途校验则忽略(返回 False); 消亡后可再次提交"""
    tq = TaskQueue()
    now = time.time()

    def poll(t, d):
        return False

    assert tq.add_check_task(Task("check", "check-checking-result", torrent_hash="H1", handler=poll), now=now) is True
    assert tq.add_check_task(Task("check", "check-checking-result", torrent_hash="H1", handler=poll), now=now) is False, \
        "同 hash 重复提交应被忽略"
    assert len(tq._fast) == 1, "重复提交不应重复入队"
    # 任务执行后消亡 -> 释放标记 -> 可再次提交
    due = tq.due(now)
    tq.task_died(due[0])
    assert tq.add_check_task(Task("check", "check-checking-result", torrent_hash="H1", handler=poll), now=now) is True, \
        "消亡后应可再次提交"


def test_defer_resume():
    """resume 语义: defer 让位(不入队不消亡) -> resume 恢复(同一实例重新入队, 跨轮保留) """
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", torrent_hash="H1", interval=2.0)
    tq.add_task(t, now=now)
    due = tq.due(now)
    assert due[0] is t, "due 弹出的是同一实例"
    tq.defer(t)
    assert t.state == DEFERRED, "让位后状态应为 deferred"
    assert t in tq._deferred, "让位任务应挂起到 _deferred"
    assert tq.due(now + 100) == [], "让位任务不入队, 不应到期"
    tq.resume(t, now)
    assert t.state == PENDING, "恢复后应重新入队"
    assert t not in tq._deferred, "恢复后应移出让位集合"
    again = tq.due(now + 2.0)
    assert again == [t], "恢复应复用同一实例"
    assert again[0].run_count == 1, "run_count 应跨轮累加"


def test_defer_resume_cb():
    """resume: 触发 resume_cb(一次性完成处理, 清空不重复触发)"""
    tq = TaskQueue()
    now = time.time()
    fired = []
    t = Task("rule", "x", torrent_hash="H1", interval=2.0)
    tq.add_task(t, now=now)
    tq.defer(tq.due(now)[0])
    t.resume_cb = lambda: fired.append(1)
    tq.resume(t, now)
    assert fired == [1], "resume 应触发 resume_cb"
    # 再次让位+恢复: resume_cb 已清空, 不重复触发
    tq.defer(tq.due(now + 2.0)[0])
    tq.resume(t, now)
    assert fired == [1], "resume_cb 一次性, 不应重复触发"


def test_task_died_releases_check():
    """task_died: check 任务消亡释放在途标记; 非 check 任务无副作用"""
    tq = TaskQueue()
    now = time.time()
    tq.add_check_task(Task("check", "check-checking-result", torrent_hash="H1"), now=now)
    assert tq._active_checks == {"H1"}
    due = tq.due(now)
    tq.task_died(due[0])
    assert tq._active_checks == set(), "check 任务消亡应释放标记"
    tq.task_died(Task("rule", "x", torrent_hash="H9"))
    assert tq._active_checks == set(), "非 check 任务不应有副作用"


def test_remove_torrent_clears_active_check():
    """remove_torrent: 删除种子移除队列任务并释放校验标记"""
    tq = TaskQueue()
    now = time.time()
    tq.add_check_task(Task("check", "check-checking-result", torrent_hash="H1", interval=60), now=now)
    tq.add_task(Task("rule", "r", torrent_hash="H1", interval=60), now=now)
    tq.remove_torrent("H1")
    assert tq.due(now + 61) == [], "队列任务应全部移除"
    assert tq._active_checks == set(), "校验标记应释放"


def test_remove_torrent_clears_deferred():
    """remove_torrent: 删除种子清理让位任务(防止泄漏) """
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", torrent_hash="H1", interval=60)
    tq.add_task(t, now=now)
    tq.defer(tq.due(now)[0])
    assert t in tq._deferred
    tq.remove_torrent("H1")
    assert tq._deferred == set(), "删除种子应清理让位任务"
    assert tq.due(now + 61) == [], "不应有任务残留"

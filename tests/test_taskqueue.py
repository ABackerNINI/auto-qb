"""test_taskqueue 测试计划: 单任务队列(生命周期只有 add_task/run_due 两个动词)

## 测试计划(每个测试函数一条)
- test_task_queue_schedule: 到期执行/interval<=0 归一化/按 interval 重入队
- test_task_ordering: 堆排序按到期时间出队
- test_task_repr: Task 字符串表示
- test_task_state_transitions: 状态迁移(pending -> running -> pending)
- test_add_tasks: 批量入队立即到期
- test_add_check_dedup: check 任务自动登记在途, 重复提交返回 False, 消亡后可再提交
- test_run_due_requeues_on_true: handler True -> 按 interval 重入队(run_count 累加)
- test_run_due_dies_on_false: handler False -> 消亡不重入, check 在途登记释放
- test_run_due_exception_caught: handler 异常被捕获, 视为 REQUEUE 重入队
- test_add_task_resets_by_default: add_task 默认重置断点(下次从头执行)
- test_add_task_keep_progress: keep_progress=True 显式保存进度(断点保留续跑)
- test_run_due_requeue_resets: 周期收尾重入队默认重置(不携带上一轮断点)
- test_reset_clears_breakpoint: Task.reset() 显式重置执行位置
- test_deleted_torrent_tasks_die_naturally: 已删种子任务到期自然消亡并释放在途登记
"""
import time

from auto_qb.taskqueue import FINISHED, PENDING, REQUEUE, RUNNING, Task, TaskQueue


def test_task_queue_schedule():
    """run_due: 到期执行 / interval<=0 归一化 / 按 interval 重入队"""
    tq = TaskQueue()
    now = time.time()
    tq.add_task(Task("rule", "every_tick", interval=0), now=now)
    tq.add_task(Task("rule", "interval60", interval=60), now=now)
    assert tq.run_due(now=now) == 2, "两个任务立即到期"
    every = [t for t in tq._fast if t.name == "every_tick"][0]
    assert every.interval == 1, "interval<=0 应归一化为 1"
    assert tq.run_due(now=now + 59) == 1, "59s 时只有 every_tick 到期"
    assert tq.run_due(now=now + 60) == 2, "60s 时两者都到期"


def test_task_ordering():
    """Task.__lt__ 按 next_run 排序(堆结构依赖)"""
    t1 = Task("rule", "a", next_run=10)
    t2 = Task("rule", "b", next_run=5)
    t3 = Task("rule", "c", next_run=10)
    assert t2 < t1
    assert not t1 < t2
    assert not t1 < t3  # next_run 相同 -> 不比较(保持稳定)


def test_task_repr():
    t = Task("rule", "add_site_tag", hash="H1")
    assert repr(t) == "Task(rule, add_site_tag, H1, pending)"
    t.state = RUNNING
    assert "running" in repr(t)


def test_task_state_transitions():
    """状态流转: pending -> running(run_due 执行中) -> pending(收尾重入队)"""
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", interval=60)
    assert t.state == PENDING
    tq.add_task(t, now=now)
    seen = []
    t.handler = lambda task, d: seen.append(task.state) or REQUEUE
    tq.run_due(now=now)
    assert seen == [RUNNING], "执行时状态应为 running"
    assert t.state == PENDING, "收尾重入队后回 pending"


def test_add_tasks():
    """add_tasks: 批量入队, 全部立即到期执行"""
    tq = TaskQueue()
    now = time.time()
    ran = []
    tq.add_tasks(
        [
            Task("rule", "a", interval=0, handler=lambda t, d: ran.append("a") or REQUEUE),
            Task("rule", "b", interval=60, handler=lambda t, d: ran.append("b") or REQUEUE),
        ],
        now=now,
    )
    assert tq.run_due(now=now) == 2
    assert ran == ["a", "b"]


def test_add_check_dedup():
    """add_task: check 任务自动登记在途, 同种子重复提交返回 False; 消亡后可再次提交"""
    tq = TaskQueue()
    now = time.time()
    assert tq.add_task(Task("check", "c", hash="H1", handler=lambda t, d: FINISHED), now=now) is True
    assert tq.add_task(Task("check", "c", hash="H1", handler=lambda t, d: FINISHED), now=now) is False, \
        "同 hash 重复提交应被丢弃"
    assert tq.active_check_hashes() == {"H1"}
    assert tq.run_due(now=now) == 1, "仅首次提交的任务在队列中"
    assert tq.active_check_hashes() == set(), "handler False 消亡应释放在途登记"
    assert tq.add_task(Task("check", "c", hash="H1", handler=lambda t, d: FINISHED), now=now) is True, \
        "消亡后应可再次提交"


def test_run_due_requeues_on_true():
    """handler True -> 按 interval 重入队, run_count 累加"""
    tq = TaskQueue()
    now = time.time()
    runs = []
    t = Task("rule", "x", hash="H1", interval=60, handler=lambda task, d: runs.append(1) or REQUEUE)
    tq.add_task(t, now=now)
    assert tq.run_due(now=now) == 1 and runs == [1]
    assert t.run_count == 1, "重入队应累加 run_count"
    assert tq.run_due(now=now + 59) == 0, "未到期不执行"
    assert tq.run_due(now=now + 60) == 1, "interval 到期再执行"
    assert t.run_count == 2


def test_run_due_dies_on_false():
    """handler False -> 消亡不重入; check 在途登记释放; 非 check 任务消亡无副作用"""
    tq = TaskQueue()
    now = time.time()
    t = Task("check", "c", hash="H1", interval=60, handler=lambda task, d: FINISHED)
    tq.add_task(t, now=now)
    assert tq.active_check_hashes() == {"H1"}
    assert tq.run_due(now=now) == 1
    assert tq.active_check_hashes() == set(), "消亡应释放在途登记"
    assert tq.run_due(now=now + 60) == 0, "消亡任务不应重入"
    tq.add_task(Task("rule", "r", hash="H9", interval=60, handler=lambda task, d: FINISHED), now=now)
    assert tq.run_due(now=now) == 1
    assert tq.active_check_hashes() == set(), "非 check 任务消亡不应有副作用"


def test_run_due_exception_caught():
    """handler 异常被捕获并视为 True 重入队(主循环不中断)"""
    tq = TaskQueue()
    now = time.time()

    def boom(task, d):
        raise RuntimeError("boom")

    t = Task("rule", "x", interval=60, handler=boom)
    tq.add_task(t, now=now)
    assert tq.run_due(now=now) == 1
    assert t.run_count == 1, "异常任务应照常重入队"


def test_add_task_resets_by_default():
    """add_task 默认重置任务: 断点清空, 下次从头执行"""
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", hash="H1", interval=60)
    t.resume_index = 3
    tq.add_task(t, now=now)
    assert t.resume_index is None, "默认入队应重置断点"


def test_add_task_keep_progress():
    """add_task(keep_progress=True): 显式保存进度, 断点保留续跑"""
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", hash="H1", interval=60)
    t.resume_index = 1
    tq.add_task(t, now=now, keep_progress=True)
    assert t.resume_index == 1, "显式保存进度应保留断点"


def test_run_due_requeue_resets():
    """run_due 周期收尾重入队默认重置: 下一轮从头执行(不携带上一轮断点)"""
    tq = TaskQueue()
    now = time.time()
    t = Task("rule", "x", hash="H1", interval=60)
    t.resume_index = 1
    tq.add_task(t, now=now, keep_progress=True)
    tq.run_due(now=now)
    assert t.resume_index is None, "周期收尾重入队应默认重置"


def test_reset_clears_breakpoint():
    """Task.reset(): 显式重置执行位置, 下次执行重走完整流程"""
    t = Task("rule", "x", hash="H1")
    t.resume_index = 3
    t.reset()
    assert t.resume_index is None, "reset 应清除断点"


def test_deleted_torrent_tasks_die_naturally():
    """已删种子任务到期自然消亡(handler 检测种子缺失返回 False)并释放在途登记 —— 替代 remove_torrent"""
    tq = TaskQueue()
    now = time.time()
    tq.add_task(Task("check", "c", hash="H1", interval=60, handler=lambda t, d: FINISHED), now=now)
    tq.add_task(Task("rule", "r", hash="H1", interval=60, handler=lambda t, d: FINISHED), now=now)
    assert tq.run_due(now=now) == 2
    assert tq.active_check_hashes() == set()
    assert tq.run_due(now=now + 60) == 0, "消亡后不应有残留"

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
- test_run_due_defer_gate_defers_then_resumes: defer_gate 命中 -> 本轮不执行、重入堆下一轮再判; 放行后执行(A 系 S2 D-1)
- test_run_due_defer_gate_does_not_consume_budget: 让位者不占 max_tasks 预算 —— 整组让位时同 tick 无关任务仍被执行(issue 26-10-30-0616)
- test_run_due_defer_scan_bounded: 让位扫描面上界 —— 让位者远超上界时不把整条队列扫穿(跳过不等于执行)
- test_add_task_resets_by_default: add_task 默认重置断点(下次从头执行)
- test_add_task_keep_progress: keep_progress=True 显式保存进度(断点保留续跑)
- test_run_due_requeue_resets: 周期收尾重入队默认重置(不携带上一轮断点)
- test_reset_clears_breakpoint: Task.reset() 显式重置执行位置
- test_deleted_torrent_tasks_die_naturally: 已删种子任务到期自然消亡并释放在途登记
- test_has_task_lookup: (kind,name,hash) 三元组判重 —— 命中 / 任一字段不同不命中
- test_has_named_lookup: has_named=internal+无 hash 特例转发 —— 同名命中 / 名不同 / 带 hash / 非 internal 不命中
- test_named_lookup: named 按名取全局任务 —— 命中返回同一对象 / 缺失与形态不符返回 None
- test_query_helpers_empty_queue: 空队列下 has_task/has_named/named/active_check_age 的反向对照
- test_active_check_age_lookup: active_check_age —— 未登记 None / 登记后非负且量级有界 / 消亡释放回 None
"""
import time

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, RUNNING, Task, TaskQueue, _DEFER_SCAN_FACTOR


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


def test_run_due_defer_gate_defers_then_resumes():
    """守阵(A 系 S2 D-1): defer_gate 命中 -> 本轮不执行、以 next_run=now 重入堆下一轮再判; 放行后执行

    红验: 去掉 run_due 里的 defer_gate 分支(无条件执行) -> 首次 run_due 即执行, `ran == []` 断言红。
    """
    tq = TaskQueue()
    now = time.time()
    ran = []
    t = Task("rule", "r", hash="H1", interval=60, handler=lambda task, dry: ran.append(task.hash) or FINISHED)
    tq.add_task(t, now=now)
    blocked = {"on": True}

    def gate(task):
        return "让位(测试)" if blocked["on"] else None

    assert tq.run_due(now=now, defer_gate=gate) == 0, "让位者不计入返回的执行数(issue 26-10-30-0616)"
    assert ran == [], "命中 defer_gate 本轮不执行"
    assert t in tq._fast and t.state == PENDING, "命中者重入堆(下一轮再判), 不是消亡"
    blocked["on"] = False
    tq.run_due(now=now, defer_gate=gate)
    assert ran == ["H1"], "判据放行后照常执行(有界: 不会永久让位)"


def test_run_due_defer_gate_does_not_consume_budget():
    """守阵(issue 26-10-30-0616): 让位者**不占 max_tasks 预算** —— 同组任务整组让位时同 tick 无关任务仍被执行

    场景: 组级 own_write(整组停 / size 一致性停种)把同批同组任务整批让位; 它们若不占名额,
    预算才留给真正能做事的任务 —— 否则组成员数 >= max_tasks 时无关任务一路饿到 own_write TTL 退出。

    红验: 把 run_due 退回「先 _pop_due(now, max_tasks) 再逐个过闸」-> 3 个让位任务吃满
    budget=3, 排在其后的 FX 本轮不被弹出, `ran == ["FX"]` 断言红。
    """
    tq = TaskQueue()
    now = time.time()
    ran = []
    for i in range(3):  # 同组任务: 更早到期(堆序在前), 全部命中 defer
        tq.add_task(
            Task(
                "rule", f"g{i}", hash=f"G{i}", interval=60, handler=lambda task, dry: ran.append(task.hash) or FINISHED
            ),
            now=now - 1,
        )
    tq.add_task(
        Task("rule", "free", hash="FX", interval=60, handler=lambda task, dry: ran.append(task.hash) or FINISHED),
        now=now,
    )

    def gate(task):
        return "让位(测试)" if task.hash.startswith("G") else None

    assert tq.run_due(now=now, max_tasks=3, defer_gate=gate) == 1, "让位者不占名额, 预算留给真正执行的任务"
    assert ran == ["FX"], "整组让位时同 tick 的无关任务不应被饿死"
    assert {t.hash for t in tq._fast} == {"G0", "G1", "G2"}, "让位者重入堆待下一 tick 再判"


def test_run_due_defer_scan_bounded():
    """守阵(issue 26-10-30-0616): 让位扫描面有上界 —— 让位者铺满时一轮 tick 不把整条队列扫穿

    让位是「跳过」不是「执行」: 预算放开给跳过面后必须有界(上界 max_tasks * _DEFER_SCAN_FACTOR),
    否则整组让位(组成员可达数百)会让一轮 tick 把全队列遍历一遍。

    红验: 去掉 _pop_due 的 scan_cap 判据(让位扫描无界) -> 排在队尾的 FX 被扫到并执行,
    `ran == []` 断言红。
    """
    tq = TaskQueue()
    now = time.time()
    ran = []
    cap = _DEFER_SCAN_FACTOR + 20
    for i in range(cap):  # 远超扫描上界的一整组让位任务
        tq.add_task(
            Task(
                "rule", f"g{i}", hash=f"G{i}", interval=60, handler=lambda task, dry: ran.append(task.hash) or FINISHED
            ),
            now=now - 1,
        )
    tq.add_task(
        Task("rule", "free", hash="FX", interval=60, handler=lambda task, dry: ran.append(task.hash) or FINISHED),
        now=now,
    )

    assert tq.run_due(now=now, max_tasks=1, defer_gate=lambda task: "让位(测试)" if task.hash != "FX" else None) == 0, \
        "扫描上界内全是让位者 -> 本轮无执行(不把队尾任务一并扫出)"
    assert ran == [], "让位者本轮一律不执行"
    assert len(tq._fast) == cap + 1, "所有任务仍在队列中(让位者未消亡)"


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


def test_has_task_lookup():
    """has_task: (kind, name, hash) 三元组判重 —— 命中返回 True, 任一字段不同返回 False

    种子级任务幂等判据(issue 26-10-01-2147): 两个创建入口共用, 语义错了重复入队无守阵。

    红验: 三元组比较的任一 `==` 被变异(`and` 短路破坏) -> 「字段不同」断言红。
    """
    tq = TaskQueue()
    now = time.time()
    tq.add_task(Task("rule", "r", hash="H1"), now=now)
    assert tq.has_task("rule", "r", "H1") is True, "三元组全匹配应命中"
    assert tq.has_task("rule", "r", "H2") is False, "hash 不同不应命中"
    assert tq.has_task("rule", "x", "H1") is False, "name 不同不应命中"
    assert tq.has_task("check", "r", "H1") is False, "kind 不同不应命中"


def test_has_named_lookup():
    """has_named: 全局任务(internal + 无 hash)幂等判据 —— 同名命中; 名不同/带 hash/非 internal 不命中

    模块任务自注册守卫(kernel-module-refactor P3): 重复注册必须无副作用, 判据太宽
    (把带 hash 的种子级同名任务也算上)会误拦, 太窄(漏 internal 无 hash 形态)会漏拦。

    红验: has_task("internal", name, "") 的实参被变异(kind/hash 换值) -> 「形态不符」断言红。
    """
    tq = TaskQueue()
    now = time.time()
    tq.add_task(Task("internal", "kernel", handler=lambda t, d: REQUEUE), now=now)
    assert tq.has_named("kernel") is True, "internal+无 hash 同名应命中"
    assert tq.has_named("other") is False, "名不同不应命中"
    tq.add_task(Task("internal", "tagged", hash="H9", handler=lambda t, d: REQUEUE), now=now)
    assert tq.has_named("tagged") is False, "internal 带 hash 不是全局任务形态, 不应命中"
    tq.add_task(Task("rule", "kernel", hash="H1"), now=now)
    assert tq.has_named("kernel") is True, "同名 rule 任务不应干扰 internal 判据"


def test_named_lookup():
    """named: 按名取全局任务(internal + 无 hash), 唯一用途是就地改节奏 —— 命中返回同一对象, 否则 None

    红验: `not t.hash` / `kind == "internal"` 被翻转 -> 返回错误对象或 None, `is` 身份断言红。
    """
    tq = TaskQueue()
    now = time.time()
    internal = Task("internal", "kernel", payload="v1", handler=lambda t, d: REQUEUE)
    tq.add_task(internal, now=now)
    assert tq.named("kernel") is internal, "应返回队列中的同一对象(就地改节奏的前提)"
    assert tq.named("missing") is None, "查无此名返回 None"
    tq.add_task(Task("internal", "tagged", hash="H9", handler=lambda t, d: REQUEUE), now=now)
    assert tq.named("tagged") is None, "internal 带 hash 不是全局任务形态"
    tq.add_task(Task("rule", "kernel", hash="H1"), now=now)
    assert tq.named("kernel") is internal, "同名 rule 任务不应被误返回"


def test_query_helpers_empty_queue():
    """查询四件套在空队列下的反向对照: 一律「未命中」语义"""
    tq = TaskQueue()
    assert tq.has_task("rule", "r", "H1") is False, "空队列 has_task 应为 False"
    assert tq.has_named("kernel") is False, "空队列 has_named 应为 False"
    assert tq.named("kernel") is None, "空队列 named 应为 None"
    assert tq.active_check_age("H1") is None, "空队列 active_check_age 应为 None"


def test_active_check_age_lookup():
    """active_check_age: 在途登记时长(monotonic, 供 TTL 泄漏判据) —— 未登记 None / 登记后有界非负 / 消亡释放回 None

    红验: `time.monotonic() - ts` 被变异(减号换加号) -> 时长爆到 monotonic 量级, 上界断言红;
    `ts is None` 分支被翻转 -> 未登记时返回 None 断言红。
    """
    tq = TaskQueue()
    assert tq.active_check_age("H1") is None, "未登记返回 None"
    now = time.time()
    tq.add_task(Task("check", "c", hash="H1", interval=60, handler=lambda t, d: REQUEUE), now=now)
    age = tq.active_check_age("H1")
    assert age is not None, "登记后应有时长"
    assert isinstance(age, float) and 0.0 <= age < 60, "时长应为秒级小值(非负且远小于 TTL 量级)"
    tq.run_due(now=now)
    assert tq.active_check_age("H1") is not None, "handler REQUEUE 重入队不释放登记"
    dying = Task("check", "c2", hash="H2", interval=60, handler=lambda t, d: FINISHED)
    tq.add_task(dying, now=now)
    tq.run_due(now=now)
    assert tq.active_check_age("H2") is None, "消亡应释放在途登记"

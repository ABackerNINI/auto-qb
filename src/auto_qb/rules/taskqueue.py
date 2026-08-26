"""双任务队列模型: 快速队列(规则扫描任务, interval 调度) + 慢速队列(异步校验任务, 主循环轮询)

线程安全设计(最大程度确保线程安全):
- 主循环线程是唯一修改任务队列结构与 state_file 的线程
- 异步工作线程(ThreadPoolExecutor 单线程)仅执行"发送请求"类回调(send_fn, 如 torrents_recheck),
  结果通过线程安全队列 result_q 回传主循环; 不触碰任务队列, 不写 state_file
- 队列结构由 RLock 保护(防御性加锁, 实际只有主循环线程访问)
"""
import heapq
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("auto-qb.rules")

# 任务状态
PENDING = "pending"  # 快速队列排队中(等待到期)
RUNNING = "running"  # 已被主循环取出执行
WAITING = "waiting"  # 慢速队列: 异步请求已发出, 等待客户端完成
DONE = "done"  # 已完成


class Task:
    """一个任务. kind: rule(规则扫描, 快速队列) / check(异步校验, 慢速队列)"""
    __slots__ = (
        "uid",
        "kind",
        "name",
        "torrent_hash",
        "next_run",
        "interval",
        "state",
        "run_count",
        "created_at",
        "payload",
        "result",
        "send_error",
        "sent",
        "timeout",
    )

    def __init__(
        self,
        kind: str,
        name: str,
        torrent_hash: str = "",
        next_run: float = 0.0,
        interval: float = 0.0,
        payload: Any = None,
        timeout: float = 0.0
    ):
        self.uid = f"{kind}:{name}:{torrent_hash}:{time.monotonic_ns()}"
        self.kind = kind
        self.name = name
        self.torrent_hash = torrent_hash
        self.next_run = next_run  # epoch 秒, 到期才执行(快速队列)
        self.interval = interval  # 规则执行间隔, 0 = 每轮
        self.state = PENDING
        self.run_count = 0
        self.created_at = time.time()
        self.payload = payload  # check 任务: done_cb(主循环线程调用)
        self.result = None  # 异步发送回调的返回值
        self.send_error = None  # check 任务: 异步发送失败原因
        self.sent = False  # check 任务: 请求已确认发出(可开始轮询)
        self.timeout = timeout  # check 任务: 轮询超时, 0 = 不限

    def __lt__(self, other):
        return self.next_run < other.next_run

    def __repr__(self) -> str:
        return f"Task({self.kind}, {self.name}, {self.torrent_hash}, {self.state})"


class TaskQueue:
    """双任务队列

    - fast: 最小堆(时间优先), 存放规则扫描任务, 按 next_run 到期弹出
    - slow: 以 torrent_hash 为键的字典, 存放异步校验任务, 由主循环 poll_slow 轮询完成

    executor_workers=0 时同步执行发送回调(测试/无异步场景), 其余用单线程线程池。
    """
    def __init__(self, executor_workers: int = 1):
        self._lock = threading.RLock()
        self._fast: List[Task] = []  # heapq: 仅存 interval>0 的规则任务
        self._always: Dict[str, Task] = {}  # interval<=0 的规则任务: 恒活跃, 不进时间堆
        self._slow: Dict[str, Task] = {}  # torrent_hash -> Task
        self._result_q: "queue.Queue[Task]" = queue.Queue()  # 异步线程 -> 主循环
        self._executor: Optional[ThreadPoolExecutor] = (
            ThreadPoolExecutor(max_workers=executor_workers, thread_name_prefix="taskq")
            if executor_workers > 0 else None
        )
        self._shutdown = False

    # ---------- 快速队列: 规则任务 ----------

    def schedule_rule(self, rule_name: str, interval: float, now: float = None):
        """注册/更新规则任务: interval<=0 恒活跃(不进时间堆); 其余立即到期(下一轮参与扫描)"""
        now = time.time() if now is None else now
        with self._lock:
            if interval <= 0:
                self._always.setdefault(rule_name, Task("rule", rule_name, next_run=now, interval=0))
                return
            for t in self._fast:
                if t.kind == "rule" and t.name == rule_name:
                    t.next_run = now
                    t.interval = interval
                    heapq.heapify(self._fast)
                    return
            heapq.heappush(self._fast, Task("rule", rule_name, next_run=now, interval=interval))

    def due_rules(self, now: float = None) -> List[Task]:
        """弹出到期规则任务(仅 interval>0 的任务在堆中; interval<=0 的由调用方每轮恒执行)"""
        now = time.time() if now is None else now
        due = []
        with self._lock:
            while self._fast and self._fast[0].next_run <= now:
                task = heapq.heappop(self._fast)
                task.state = RUNNING
                due.append(task)
        return due

    def reschedule(self, task: Task, now: float = None):
        """规则任务执行完毕: 按 interval 重新入队"""
        now = time.time() if now is None else now
        task.run_count += 1
        task.state = PENDING
        task.next_run = now + task.interval
        with self._lock:
            heapq.heappush(self._fast, task)

    # ---------- 慢速队列: 异步校验任务 ----------

    def submit_check(
        self,
        torrent_hash: str,
        send_fn: Callable[[], Any],
        done_cb: Callable[["Task"], None] = None,
        timeout: float = 0.0
    ) -> bool:
        """提交异步校验任务: 同一种子已有等待任务则忽略(返回 False)

        send_fn 在异步工作线程执行(仅发送请求, 如 torrents_recheck), 完成经 result_q 回传;
        done_cb 由主循环在轮询到校验完成时调用(主循环线程, 可安全写 state_file)。
        """
        with self._lock:
            if self._shutdown or torrent_hash in self._slow:
                return False
            task = Task("check", "check", torrent_hash=torrent_hash, payload=done_cb, timeout=timeout)
            task.state = WAITING
            self._slow[torrent_hash] = task
        # 锁外提交: 异步线程不触碰队列结构
        if self._executor is not None:
            self._executor.submit(self._run_send, task, send_fn)
        else:
            self._run_send(task, send_fn)  # 同步模式(测试)
        return True

    def _run_send(self, task: Task, send_fn: Callable[[], Any]):
        """异步工作线程: 仅执行发送请求回调; 不触碰队列/state_file, 结果经 result_q 回传"""
        try:
            task.result = send_fn()
        except Exception as e:
            task.send_error = e
        self._result_q.put(task)

    def poll_slow(self, is_done: Callable[[str], bool], now: float = None) -> List[Task]:
        """主循环轮询慢速队列(每 tick 调用一次):
        1. 消费 result_q 确认请求已发出(发送失败的任务立即完成)
        2. 对已发出请求的任务调用 is_done(hash) 判断客户端是否完成(如退出 checking 状态)
        3. 完成的(含超时)调用 done_cb 并从慢速队列移除
        """
        now = time.time() if now is None else now
        completed = []
        with self._lock:
            # 1. 消费异步线程回传
            while True:
                try:
                    task = self._result_q.get_nowait()
                except queue.Empty:
                    break
                task.sent = True
            # 2. 轮询等待中的任务
            for task in list(self._slow.values()):
                if task.send_error is not None:
                    completed.append(task)
                    continue
                if not task.sent:
                    continue  # 请求尚未确认发出, 下一轮再查
                if task.timeout > 0 and now - task.created_at > task.timeout:
                    task.send_error = TimeoutError(f"校验超时({task.timeout}s)")
                    completed.append(task)
                    continue
                try:
                    if is_done(task.torrent_hash):
                        completed.append(task)
                except Exception as e:
                    logger.debug(f"轮询校验状态异常({task.torrent_hash}): {e}")
            # 3. 完成的任务出队(回调在锁外执行, 避免死锁)
            for task in completed:
                self._slow.pop(task.torrent_hash, None)
                task.state = DONE
        for task in completed:
            done_cb = task.payload
            if done_cb:
                try:
                    done_cb(task)
                except Exception as e:
                    logger.warning(f"校验完成回调异常({task.torrent_hash}): {e}")
        return completed

    def pending_slow(self) -> List[str]:
        """等待校验完成的种子 hash 列表"""
        with self._lock:
            return list(self._slow.keys())

    def shutdown(self, wait: bool = True):
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
        if self._executor is not None:
            self._executor.shutdown(wait=wait)

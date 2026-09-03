"""单任务队列模型: 时间优先最小堆, 所有任务(含校验结果轮询)统一调度

线程模型:
- 主循环线程是唯一修改任务队列与 state_file 的线程, 无需加锁
- 校验结果轮询任务(check)由规则动作创建, 经 add_check_task 去重登记(_active_checks);
  handler 按 interval 到期执行; 触发校验的规则任务经 defer 让位(不入队不消亡),
  由轮询任务在完成后 resume(校验成功, 触发 resume_cb 完成处理)或 reschedule(失败)恢复
"""
import heapq
import logging
import time
from typing import Any, Callable, List, Set

from .config import TrackerConfig

logger = logging.getLogger(__name__)

# 任务状态
PENDING = "pending"  # 排队中(等待到期)
RUNNING = "running"  # 已被主循环取出执行
DEFERRED = "deferred"  # 让位: 不入队不消亡, 由外部决定恢复(resume)或重新调度(reschedule)

# handler 返回 False = 任务不重新入队(自然消亡, 如种子已被删除)
Handler = Callable[["Task", bool], bool]


class Task:
    """一个任务. kind: refresh(种子列表刷新) / rule(规则扫描) / torrent(种子级内置功能) / check(校验结果轮询)"""
    __slots__ = (
        "uid",
        "kind",
        "name",
        "hash",
        "tracker_conf",
        "next_run",
        "interval",
        "state",
        "resume_cb",
        "resume_index",
        "run_count",
        "created_at",
        "payload",
        "handler",
    )

    def __init__(
        self,
        kind: str,
        name: str,
        hash: str = "",
        tracker_conf: TrackerConfig = None,
        next_run: float = 0.0,
        interval: float = 0.0,
        payload: Any = None,
        handler: Handler = None,
    ):
        self.uid = f"{kind}:{name}:{hash}:{time.monotonic_ns()}"
        self.kind = kind
        self.name = name
        self.hash = hash
        self.tracker_conf = tracker_conf
        self.next_run = next_run  # epoch 秒, 到期才执行
        self.interval = interval  # 任务执行间隔, 秒(<=0 归一化为 1: 每 tick 级别)
        self.state = PENDING
        self.resume_cb = None  # 让位任务恢复时触发的完成处理(一次性, 由 defer/resume 使用)
        self.resume_index = None  # 规则任务断点(下一个要执行的动作索引); resume(校验成功)保留 -> 续跑, reschedule(失败)前清空 -> 重走完整决策链
        self.run_count = 0
        self.created_at = time.time()
        self.payload = payload  # 可选: 任务附带数据(自定义)
        self.handler = handler  # 主循环执行任务时调用: handler(task, dry_run) -> bool(False=不重入)

    def __lt__(self, other):
        return self.next_run < other.next_run

    def __repr__(self) -> str:
        return f"Task({self.kind}, {self.name}, {self.hash}, {self.state})"


class TaskQueue:
    """单任务队列(时间优先堆)

    - 所有任务(种子刷新/规则/种子级内置/校验结果轮询)统一按 next_run 到期弹出执行;
      每个任务有内置 interval, 执行后由主循环按 interval 重新入队
    - 校验结果轮询任务(check)经 add_check_task 去重登记(_active_checks),
      handler 返回 False 时由主循环调 task_died 释放在途标记
    - 让位(resume 语义): 规则任务执行 full-checking 后经 defer 挂起(_deferred, 不入队不消亡),
      由轮询任务在完成后 resume(校验成功, 触发 resume_cb 完成处理)或 reschedule(失败)恢复
    - 无锁: 仅主循环线程修改队列结构
    """
    def __init__(self):
        self._fast: List[Task] = []  # heapq: 所有按时间调度的任务
        self._active_checks: Set[str] = set()  # 在途校验 hash 集合(去重)
        self._deferred: Set[Task] = set()  # 让位任务: 不入队不消亡, 等待恢复

    # ---------- 快速队列: 通用任务 ----------

    @staticmethod
    def _norm_interval(interval: float) -> float:
        """interval<=0 归一化为 1s(每 tick 级别): 每个任务都有内置 interval"""
        return max(1.0, float(interval))

    def add_task(self, task: Task, now: float = None):
        """加入队列; 新任务立即到期(next_run=now, 下一 tick 执行)"""
        now = time.time() if now is None else now
        task.interval = self._norm_interval(task.interval)
        task.next_run = now
        heapq.heappush(self._fast, task)

    def add_tasks(self, tasks: List[Task], now: float = None):
        for t in tasks:
            self.add_task(t, now)

    def due(self, now: float = None, max: int = 0) -> List[Task]:
        """弹出所有到期任务(按 next_run 时间优先), max设置弹出的最大数量"""
        now = time.time() if now is None else now
        due = []
        while (max <= 0 or len(due) < max) and self._fast and self._fast[0].next_run <= now:
            task = heapq.heappop(self._fast)
            task.state = RUNNING
            due.append(task)
        return due

    def reschedule(self, task: Task, now: float = None):
        """任务执行完毕且需继续: 按任务内置 interval 重新入队

        resume 语义: 复用同一 Task 实例(uid/resume_cb/payload/handler/run_count 跨轮保留),
        非从头重新执行。让位任务(经 defer 挂起)由 reschedule 恢复时自动移出让位集合。
        """
        now = time.time() if now is None else now
        self._deferred.discard(task)
        task.run_count += 1
        task.state = PENDING
        task.next_run = now + task.interval
        heapq.heappush(self._fast, task)

    def remove_torrent(self, hash: str):
        """种子被删除: 移除该种子在队列中的所有任务(含让位任务), 并释放在途校验标记"""
        before = len(self._fast)
        self._fast = [t for t in self._fast if t.hash != hash]
        if len(self._fast) != before:
            heapq.heapify(self._fast)
        self._deferred = {t for t in self._deferred if t.hash != hash}
        self._active_checks.discard(hash)

    # ---------- 让位/恢复(resume 语义) ----------

    def defer(self, task: Task):
        """任务让位: 不入队不消亡(从调度中挂起), 由外部决定恢复(resume)或重新调度(reschedule)

        典型场景: 规则任务执行 full-checking 后让位, 由校验结果轮询任务在完成后
        调用 resume(校验成功)或 reschedule(失败/种子删除)恢复它。
        """
        task.state = DEFERRED
        self._deferred.add(task)

    def resume(self, task: Task, now: float = None):
        """恢复让位任务: 触发 resume_cb(一次性完成处理)后按任务内置 interval 重新入队

        resume 语义: 让位任务此前由 defer() 挂起, 恢复时先执行其完成处理
        (如校验通过后的晋升/自动开始/记录执行), 然后重新进入调度。
        """
        now = time.time() if now is None else now
        self._deferred.discard(task)
        cb, task.resume_cb = task.resume_cb, None
        try:
            if cb:
                cb()
        except Exception as e:
            logger.error(f"任务恢复回调异常({task.kind}:{task.name} {task.hash}): {e}")
        task.run_count += 1
        task.state = PENDING
        task.next_run = now + task.interval
        heapq.heappush(self._fast, task)

    # ---------- 校验结果轮询任务 ----------

    def add_check_task(self, task: Task, now: float = None) -> bool:
        """登记校验结果轮询任务: 同一种子已有在途校验则忽略(返回 False)

        任务立即入队(next_run=now), 首轮到期时由 handler 发送 recheck 请求;
        handler 返回 False(完成/消亡)时由主循环调 task_died 释放在途标记。
        """
        if task.hash in self._active_checks:
            return False
        self._active_checks.add(task.hash)
        self.add_task(task, now)
        return True

    def task_died(self, task: Task):
        """任务消亡(handler 返回 False): 释放校验在途标记(如有) """
        if task.kind == "check":
            self._active_checks.discard(task.hash)

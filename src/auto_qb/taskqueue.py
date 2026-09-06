"""单任务队列模型: 时间优先最小堆, 所有任务(含校验结果轮询)统一调度

线程模型:
- 主循环线程是唯一修改任务队列与 state_file 的线程, 无需加锁
- 生命周期只有两个动词: add_task 入队 / run_due 到期执行+收尾
  - handler 返回 REQUEUE -> 按 interval 重入队(周期任务)
  - handler 返回 FINISHED -> 本轮不重入: 消亡(kind=="check" 释放在途登记), 或由其子任务
    负责重新入队(推迟执行, 如 full-checking 校验期间规则任务让出队列)
- 断点(resume_index)语义: add_task 默认重置任务(下次从头执行), 仅 keep_progress=True
  显式保存进度(下次从断点续跑); 重走完整流程由子任务以默认 add_task 触发
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

# handler 返回值语义(替代裸 True/False):
REQUEUE = True  # 按 interval 重新入队(周期任务继续)
FINISHED = False  # 本轮不重入: 任务消亡(kind=="check" 释放在途登记), 或由其子任务负责重新入队
Handler = Callable[["Task", bool], bool]


class Task:
    """一个任务. kind: refresh(种子列表刷新) / rule(规则扫描) / torrent(种子级内置功能) /
    internal(全局内置) / check(校验结果轮询) / check-wait(组内校验等待)"""
    __slots__ = (
        "uid",
        "kind",
        "name",
        "hash",
        "tracker_conf",
        "next_run",
        "interval",
        "state",
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
        self.resume_index = None  # 规则任务断点(下一个要执行的动作索引); 默认记住位置, 重新入队后继续
        self.run_count = 0
        self.created_at = time.time()
        self.payload = payload  # 可选: 任务附带数据(自定义)
        self.handler = handler  # 主循环执行任务时调用: handler(task, dry_run) -> REQUEUE/FINISHED

    def __lt__(self, other):
        return self.next_run < other.next_run

    def reset(self):
        """显式重置执行位置: 下次执行重走完整流程(规则任务=重走完整决策链)

        与 process() 的自然消费(正常完成后清零)并列的清除入口;
        add_task 默认重置, 仅 keep_progress=True 时保留断点。
        """
        self.resume_index = None

    @property
    def has_breakpoint(self) -> bool:
        """是否存在未消费的断点(pending 异步等待中, 等待子任务重新入队恢复/续跑)"""
        return self.resume_index is not None

    @property
    def log_tag(self) -> str:
        """统一任务日志标识: kind:name[#hash8]"""
        h = f"#{self.hash[:8]}" if self.hash else ""
        return f"{self.kind}:{self.name}{h}"

    def __repr__(self) -> str:
        return f"Task({self.kind}, {self.name}, {self.hash}, {self.state})"


class TaskQueue:
    """单任务队列(时间优先堆): 生命周期只有 入队(add_task) 与 到期执行收尾(run_due) 两个动词

    - 所有任务(种子刷新/规则/种子级内置/校验结果轮询)统一按 next_run 到期弹出执行;
      handler 返回 REQUEUE 按 interval 重入队, 返回 FINISHED 消亡(kind=="check" 释放在途登记)
    - 校验结果轮询任务(check)入队时自动登记在途(_active_checks), 重复登记丢弃并返回
      False; 消亡时释放 —— 组内校验串行化闸门经 active_check_hashes() 感知
    - 推迟执行不在队列挂起: 规则任务 handler 返回 FINISHED 让出队列, 由其子任务(轮询)
      在完成后按情况重新入队(keep_progress=True 断点续跑 / 默认重置重走)
    - 无锁: 仅主循环线程修改队列结构
    """
    def __init__(self):
        self._fast: List[Task] = []  # heapq: 所有按时间调度的任务
        self._active_checks: Set[str] = set()  # 在途校验 hash 集合(去重)

    # ---------- 入队 ----------

    @staticmethod
    def _norm_interval(interval: float) -> float:
        """interval<=0 归一化为 1s(每 tick 级别): 每个任务都有内置 interval"""
        return max(1.0, float(interval))

    def add_task(self, task: Task, now: float = None, keep_progress: bool = False) -> bool:
        """入队; 新任务立即到期(next_run=now, 下一次 run_due 执行)。返回是否入队成功。

        kind=="check" 自动登记在途(_active_checks): 同一种子已有在途校验时丢弃并返回
        False(调用方据此 skip), 否则登记并入队返回 True。

        断点语义: 默认重置任务(resume_index 清空, 下次从头执行); keep_progress=True 显式
        保存任务进度(断点保留, 下次从断点续跑) —— 仅供等待异步完成的子任务恢复 origin 使用。
        """
        if not keep_progress:
            task.resume_index = None
        if task.kind == "check":
            if task.hash in self._active_checks:
                return False
            self._active_checks.add(task.hash)
        now = time.time() if now is None else now
        task.interval = self._norm_interval(task.interval)
        task.next_run = now
        task.state = PENDING
        heapq.heappush(self._fast, task)
        return True

    def add_tasks(self, tasks: List[Task], now: float = None):
        for t in tasks:
            self.add_task(t, now)

    def active_check_hashes(self) -> Set[str]:
        """在途校验 hash 集合快照(已提交 full-checking 且轮询任务未结束, 消亡时释放)

        组内校验串行化闸门(rules/actions 决策链 1.5)使用: recheck 为透传不写快照,
        同 tick 内后执行成员只能靠此登记感知其它成员的校验在途。
        """
        return set(self._active_checks)

    # ---------- 到期执行 + 收尾 ----------

    def run_due(self, dry_run: bool = False, now: float = None, max_tasks: int = 0) -> int:
        """执行所有到期任务并收尾(主循环 tick 的队列唯一入口)。返回执行的任务数。

        先快照到期任务再逐个执行: 执行中途新入队的任务(如轮询子任务重新入队的
        规则任务)留到下一次 run_due, 避免同批重入导致未校验即误判失败。
        收尾: handler 返回 REQUEUE -> 按 interval 重入队(默认重置断点); FINISHED ->
        消亡(不入队, kind=="check" 释放在途登记)。
        """
        now = time.time() if now is None else now
        due = self._pop_due(now, max_tasks)
        for task in due:
            task.state = RUNNING
            if self._run_one(task, dry_run):
                self._requeue(task, now)
            elif task.kind == "check":
                self._active_checks.discard(task.hash)  # 消亡: 释放在途登记
        return len(due)

    def _pop_due(self, now: float, max_tasks: int) -> List[Task]:
        """弹出所有到期任务(按 next_run 时间优先), max_tasks 限制弹出数量"""
        due = []
        while (max_tasks <= 0 or len(due) < max_tasks) and self._fast and self._fast[0].next_run <= now:
            task = heapq.heappop(self._fast)
            task.state = RUNNING
            due.append(task)
        return due

    def _run_one(self, task: Task, dry_run: bool) -> bool:
        """执行任务 handler, 捕获异常; 返回 REQUEUE(周期继续)或 FINISHED(消亡/移交子任务)"""
        try:
            if task.handler:
                return bool(task.handler(task, dry_run))
        except Exception as e:
            logger.error(f"任务[{task.log_tag}] | 执行异常: {e}", exc_info=True)
        return REQUEUE

    def _requeue(self, task: Task, now: float):
        """周期任务收尾: 默认重置断点后按任务内置 interval 重新入队(下一轮从头执行)"""
        task.resume_index = None
        task.run_count += 1
        task.state = PENDING
        task.next_run = now + task.interval
        heapq.heappush(self._fast, task)

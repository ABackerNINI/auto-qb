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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from ..torrents import TorrentStore

logger = logging.getLogger(__name__)

# 任务状态
PENDING = "pending"  # 排队中(等待到期)
RUNNING = "running"  # 已被主循环取出执行

# 让位扫描上界系数(见 _pop_due): 让位任务不占可执行预算, 但"跳过"的扫描面必须有界 ——
# 以 max_tasks 的倍数封顶, 免得整组让位时一轮 tick 把整条队列扫穿(让位是跳过不是执行)。
_DEFER_SCAN_FACTOR = 5

# handler 返回值语义(替代裸 True/False):
REQUEUE = True  # 按 interval 重新入队(周期任务继续)
FINISHED = False  # 本轮不重入: 任务消亡(kind=="check" 释放在途登记), 或由其子任务负责重新入队
Handler = Callable[["Task", bool], bool]


class Task:
    """一个任务. kind: refresh(种子列表刷新) / rule(规则扫描) / rule-event(事件触发规则的一次性任务,
    作 origin 被轮询子任务 add_task 重新入队续跑, 恒 FINISHED 不自我周期循环) / torrent(种子级内置功能) /
    internal(全局内置) / check(校验结果轮询) / check-wait(组内校验等待)"""
    __slots__ = (
        "uid",
        "kind",
        "name",
        "hash",
        "_store",
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
        store: "TorrentStore | None" = None,
        next_run: float = 0.0,
        interval: float = 0.0,
        payload: Any = None,
        handler: Handler = None,
    ):
        self.uid = f"{kind}:{name}:{hash}:{time.monotonic_ns()}"
        self.kind = kind
        self.name = name
        self.hash = hash
        self._store = store
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

    @property
    def torrent(self):
        """从 store 查找种子(始终最新; 种子已删除返回 None)"""
        return self._store.get(self.hash) if self._store else None

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
        # 在途校验登记: hash -> 登记时刻(monotonic)。集合语义(成员即"在途")+ 时刻供
        # 闸门判泄漏(active_check_age / checking_meta.INFLIGHT_TTL): 登记只在轮询任务
        # FINISHED 时释放, 任务被异常丢弃时登记会永久残留并挡住 G5/G7
        self._active_checks: Dict[str, float] = {}

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
            self._active_checks[task.hash] = time.monotonic()
        now = time.time() if now is None else now
        task.interval = self._norm_interval(task.interval)
        task.next_run = now
        task.state = PENDING
        heapq.heappush(self._fast, task)
        return True

    def add_tasks(self, tasks: List[Task], now: float = None):
        for t in tasks:
            self.add_task(t, now)

    def has_task(self, kind: str, name: str, hash: str) -> bool:
        """队列中是否已有同 (kind, name, hash) 的任务(种子级任务幂等判据)

        种子级任务唯一创建点 rules._create_torrent_tasks 与 full_round 补建
        (issue 26-10-01-2147)共用本判据: 任一入口重复入队都无副作用(黄金法则 1)。
        队列本身只对 check 任务去重(见 add_task), 其余任务靠调用方经这里查重。
        """
        return any(t.kind == kind and t.name == name and t.hash == hash for t in self._fast)

    def has_named(self, name: str) -> bool:
        """队列中是否已有同名全局任务(kind=internal 且不带 hash)

        模块任务自注册的幂等守卫(plan kernel-module-refactor P3): 重复注册(重复 start /
        重复 queue_rebuilt 相位)按黄金法则 1 必须无副作用 —— 判据单点在 has_task, 本方法
        是全局任务(internal+无 hash)形态的特例转发, 与种子级同名任务(如内置 maintenance
        带 hash)不混淆。
        """
        return self.has_task("internal", name, "")

    def named(self, name: str) -> Optional[Task]:
        """按名取全局任务(internal + 无 hash); 没有则 None

        唯一消费方是「已在队列的任务**就地**改节奏」(traffic_snapshot.apply 的 refresh_interval
        热更新): 队列是 next_run 排序的堆, 增删任务要维护堆序, 而 interval 只在收尾 requeue
        时被读 —— 就地改只影响下一次排期, 不动堆结构。!不要用它做"改任务身份/换 handler"。
        """
        for t in self._fast:
            if t.kind == "internal" and t.name == name and not t.hash:
                return t
        return None

    def active_check_hashes(self) -> Set[str]:
        """在途校验 hash 集合快照(已提交 full-checking 且轮询任务未结束, 消亡时释放)

        组内校验串行化闸门(rules/actions 决策链 1.5)使用: recheck 为透传不写快照,
        同 tick 内后执行成员只能靠此登记感知其它成员的校验在途。
        """
        return set(self._active_checks)

    def active_check_age(self, hash: str) -> Optional[float]:
        """该 hash 在途登记的时长(秒, monotonic); 未登记 -> None

        闸门侧 TTL 判据(checking_meta.INFLIGHT_TTL): 登记只在轮询任务 FINISHED 时释放,
        任务被异常丢弃(队列重建等)时登记会残留 —— 时长超 TTL 由调用方判为泄漏并忽略。
        """
        ts = self._active_checks.get(hash)
        return None if ts is None else max(0.0, time.monotonic() - ts)

    # ---------- 到期执行 + 收尾 ----------

    def run_due(self, dry_run: bool = False, now: float = None, max_tasks: int = 0, defer_gate=None) -> int:
        """执行所有到期任务并收尾(主循环 tick 的队列唯一入口)。返回**实际执行**的任务数。

        先快照到期任务再逐个执行: 执行中途新入队的任务(如轮询子任务重新入队的
        规则任务)留到下一次 run_due, 避免同批重入导致未校验即误判失败。
        收尾: handler 返回 REQUEUE -> 按 interval 重入队(默认重置断点); FINISHED ->
        消亡(不入队, kind=="check" 释放在途登记)。

        defer_gate(A 系 26-10-13-0540 S2 的 D-1 队列级闸门): 可选回调 task -> 原因字符串
        (命中)/None(放行)。命中者**本轮不执行、也不占 max_tasks 预算**(issue 26-10-30-0616),
        以 next_run=now 重新入堆(下一次 run_due 立即再判, 不等任务自身 interval)—— 目标
        hash/其组刚被自有停/起时, task 线全体消费让位, 等快照回流后下一 tick 再决策。
        有界性由 own_writes 的逐出/TTL 给出(不依赖外部条件): 逐出或 TTL 到期后 defer_gate
        返回 None, 任务照常执行(不会饿死)。

        返回数只统计**真正执行**的任务: 让位者既没做事也没消耗 qB 请求预算, 计进返回数会
        让上面的速率语义(20 个/2s)在 own_write 窗口内失真(整组让位时窗口内接近空转)。
        """
        now = time.time() if now is None else now
        due, deferred = self._pop_due(now, max_tasks, defer_gate)
        for task in due:
            if self._run_one(task, dry_run):
                self._requeue(task, now)
            elif task.kind == "check":
                self._active_checks.pop(task.hash, None)  # 消亡: 释放在途登记
        # 让位者在执行批次之后统一回填: 预算结算期间它们不在堆里, 不会被本轮重复弹出过闸
        for task in deferred:
            heapq.heappush(self._fast, task)
        return len(due)

    def _pop_due(self, now: float, max_tasks: int, defer_gate=None) -> Tuple[List[Task], List[Task]]:
        """弹出到期任务(按 next_run 时间优先), 返回 (可执行批次, 让位批次)

        max_tasks 只约束**可执行**名额 —— 让位者不占预算(issue 26-10-30-0616): 组级
        own_write(整组停 / size 一致性停种)会把同批同组任务整组让位, 若它们照旧各占一个
        名额, 组成员数 >= max_tasks 时同 tick 的无关任务一个都轮不到、一路饿到 own_write
        TTL 退出, 速率语义(max_tasks/2s)在该窗口失真。

        两个有界性: ① 让位者本轮**先留在堆外**(由 run_due 在执行批次后回填), 否则
        next_run=now 的它们会被本轮再次弹出、重复过闸; ② 扫描面以 max_tasks *
        _DEFER_SCAN_FACTOR 封顶 —— 让位是"跳过"不是"执行", 不能让一轮 tick 把整条队列
        扫穿。max_tasks<=0 表示不限(沿用内部语义, 与 config 侧的 >=1 校验无关)。
        """
        due: List[Task] = []
        deferred: List[Task] = []
        scan_cap = 0 if max_tasks <= 0 else max_tasks * _DEFER_SCAN_FACTOR
        while (
            (max_tasks <= 0 or len(due) < max_tasks) and (scan_cap <= 0 or len(due) + len(deferred) < scan_cap) and
            self._fast and self._fast[0].next_run <= now
        ):
            task = heapq.heappop(self._fast)
            task.state = RUNNING
            if defer_gate is not None:
                reason = defer_gate(task)
                if reason:
                    task.state = PENDING
                    task.next_run = now  # 下一 run_due 再判(deferral 语义 = 让位下一 tick)
                    deferred.append(task)
                    logger.debug(f"任务[{task.log_tag}] | deferral 让位(下一 tick 重判): {reason}")
                    continue
            due.append(task)
        return due, deferred

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

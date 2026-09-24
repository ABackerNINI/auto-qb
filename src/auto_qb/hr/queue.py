"""取数任务队列: 端点线程与取数线程之间的**唯一**交接面(计划 §6/§8 · M2)。

线程边界(硬约束, 见 AGENTS.md 黄金法则 5 与计划 §8):

- **端点线程只入队** —— 它把扩展回传的结果塞进本对象, 不碰 store / 任务队列 / state_file / hr 文件;
- **取数线程** 经 `ChannelFetcher` 调 `put()` 发任务、`wait()` 收结果, 其余时间在锁内干自己的活;
- 本模块只有一把 `threading.Condition` 保护两张内存表, **零文件 I/O、零网络 I/O**。

两道防伪造/防呆线:
1. **只接受「确实派发出去且还没回过」的任务 id** —— 任意网页 JS 或过期回传进来的结果一律拒
   (返回 False, 端点据此回 400), 不入任何状态;
2. 回传若带 URL, 域名必须与派发的任务一致 —— 防「拿 A 任务的结果冒充 B 任务」。
"""
import logging
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from .channel import MAX_BATCH, HrResult, HrTask, host_of

logger = logging.getLogger(__name__)

#: 任务派发后多久没回传就作废(扩展拿到任务后浏览器被杀 / 断网): 等下一轮重排, 不永久占用
DEFAULT_TASK_TTL = 240.0


class HrTaskQueue:
    """派发式任务队列: 扩展来拉 -> 拿走 -> 回传 -> 唤醒等待方"""
    def __init__(
        self, *, now_fn: Callable[[], float] = time.time, ttl: float = DEFAULT_TASK_TTL, name: str = ""
    ) -> None:
        self._now = now_fn
        self._ttl = ttl
        self._name = name or "hr"
        self._cond = threading.Condition()
        #: 已发起但还没回传的任务: task_id -> HrTask(含派发时刻)
        self._outstanding: Dict[str, Tuple[HrTask, float]] = {}
        #: 已回传、等待取数线程取走的结果: task_id -> HrResult
        self._results: Dict[str, HrResult] = {}
        #: 被显式叫停的原因(空 = 正常); 见 cancel_all
        self._cancel_reason = ""
        self._epoch = 0

    # ---------- 取数线程侧 ----------

    def put(self, site: str, kind: str, url: str, *, scope: str = "", tid: int = 0) -> HrTask:
        """登记一条任务(重复 URL 不重复登记: 同一轮里重排只复用同一条)"""
        with self._cond:
            self._expire_locked()
            for task, _at in self._outstanding.values():
                if task.site == site and task.kind == kind and task.url == url:
                    return task
            task = HrTask(task_id=uuid.uuid4().hex[:16], kind=kind, url=url, site=site, scope=scope, tid=tid)
            self._outstanding[task.task_id] = (task, 0.0)
            return task

    def wait(self, task_id: str, timeout: float) -> Optional[HrResult]:
        """等回传; 超时返回 None 并**就地作废**该任务(晚到的回传会被 submit 拒掉, 不会堆积)

        等待预算用**真实单调时钟**(time.monotonic), 不用注入的 now_fn —— 注入的假时钟只服务
        TTL 与频控(测试可自由推进), 若混进阻塞预算会让"时间不动"的假时钟把等待无限拉长。

        被 `cancel_all` 叫停时同样返回 None(调用方据 `cancel_reason` 区分"被叫停"与"超时")。
        """
        deadline = time.monotonic() + max(0.0, timeout)
        with self._cond:
            epoch = self._epoch
            while True:
                got = self._results.pop(task_id, None)
                if got is not None:
                    return got
                # ❗叫停标记优先于一切: 包括"叫停之后才发起的等待" —— 否则关停时线程又新发一条
                # 任务, 就得白等满 request_timeout(默认 180s), 而且一直持着站点锁。
                if self._cancel_reason:
                    return None
                self._expire_locked()
                if task_id not in self._outstanding or self._epoch != epoch:
                    return None
                left = deadline - time.monotonic()
                if left <= 0:
                    self._outstanding.pop(task_id, None)
                    return None
                self._cond.wait(left)

    def abort(self, task_id: str) -> None:
        """放弃等待单条任务(仅测试与出错清理用): 作废该任务, 晚到的回传将被拒"""
        with self._cond:
            self._outstanding.pop(task_id, None)
            self._results.pop(task_id, None)

    # ---------- 叫停 / 恢复 ----------

    def cancel_all(self, reason: str = "") -> None:
        """作废全部未完成任务并叫醒所有等待方(**停止取数线程前必须调**)。

        为什么必须有这个口: 取数线程能阻塞等扩展回传最多 `channel.request_timeout`(默认 180s),
        而它此时**正持着站点锁** —— 若不叫停, 一次正常关停会白等到超时(该站点在此期间不可用,
        进程退出也慢 3 分钟)。
        """
        with self._cond:
            self._cancel_reason = reason or "已停止"
            self._epoch += 1
            self._outstanding.clear()
            self._results.clear()
            self._cond.notify_all()

    def resume(self) -> None:
        """清除叫停标记(重启取数线程时调)"""
        with self._cond:
            self._cancel_reason = ""
            self._epoch += 1

    @property
    def cancel_reason(self) -> str:
        """被叫停的原因(空 = 正常); 取数通道据此把"等待中断"与"等超时"分开上报"""
        return self._cancel_reason

    # ---------- 端点线程侧 ----------

    def take_batch(self, limit: int = MAX_BATCH) -> List[HrTask]:
        """把待派发任务交给扩展(标记派发时刻; 过期任务先清掉)"""
        with self._cond:
            self._expire_locked()
            now = self._now()
            out: List[HrTask] = []
            for task_id, (task, dispatched_at) in list(self._outstanding.items()):
                if dispatched_at > 0:
                    continue  # 已派发过(说明扩展正在取, 或上次那轮没回来) —— 不重复派
                task.dispatched_at = now
                self._outstanding[task_id] = (task, now)
                out.append(task)
                if len(out) >= max(1, limit):
                    break
            return out

    def submit(self, result: HrResult) -> bool:
        """收一条回传; 不匹配(未派发 / 已作废 / 域名不符)返回 False"""
        with self._cond:
            got = self._outstanding.get(result.task_id)
            if got is None:
                return False
            task, dispatched_at = got
            if dispatched_at <= 0:
                # 还没经 take_batch 交给扩展就收到的回传是不可能的 —— 拒掉(比只校验存在性更严)
                logger.warning(f"HR 取数通道 | 丢弃未派发任务的回传: {result.task_id}")
                return False
            if result.url and host_of(result.url) != host_of(task.url):
                logger.warning(f"HR 取数通道 | 丢弃域名不符的回传: 任务 {task.url} vs 回传 {result.url}")
                return False
            result.received_at = self._now()
            result.url = result.url or task.url
            self._outstanding.pop(result.task_id, None)
            self._results[result.task_id] = result
            self._cond.notify_all()
            return True

    # ---------- 观测 ----------

    def pending(self) -> int:
        """仍在等回传的任务数"""
        with self._cond:
            self._expire_locked()
            return len(self._outstanding)

    def stats(self) -> Dict[str, int]:
        with self._cond:
            self._expire_locked()
            return {"outstanding": len(self._outstanding), "results": len(self._results)}

    def _expire_locked(self) -> None:
        """清掉超期未回传的任务与没人取走的结果(TTL 内两个方向都会自然到期)"""
        now = self._now()
        for task_id, (_task, dispatched_at) in list(self._outstanding.items()):
            if dispatched_at > 0 and now - dispatched_at > self._ttl:
                self._outstanding.pop(task_id, None)
        for task_id, result in list(self._results.items()):
            if now - (result.received_at or now) > self._ttl:
                self._results.pop(task_id, None)


__all__ = ["DEFAULT_TASK_TTL", "HrTaskQueue"]

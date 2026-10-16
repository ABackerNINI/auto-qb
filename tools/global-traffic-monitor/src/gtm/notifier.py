"""通知: 阈值事件向存活订阅者推送 (S4 实现).

采样循环内累计「距上次事件的上下行合计变化」, >= 阈值 (默认 100 MiB) 时:
  1. 先确保文件已落盘 (读者届时必读到新值);
  2. 事件号 +1, 构造事件体 {event_id, day, up_bytes, down_bytes, total_bytes, ts};
  3. 向所有存活订阅者 POST (超时 3s, 失败记 WARNING 不阻断)。
启动/崩溃恢复后首帧落盘补发一次 (事件号接续)。

订阅方以事件号去重 + 冷却 (auto-qb 侧 notify_cooldown_s 默认 600s) 收敛,
重复投递/突发连续事件不重复刷新。

**推送不占采样循环** (计划 §04 S4 出口判据): notify() 在采样线程里只做「落盘 ->
事件号 +1 -> 取订阅者快照 -> 派发」, 真正的网络等待在**独立守护线程**里做
(每订阅者一线程, 互不干扰) —— 假死端点不会拖慢采样节拍, 也不会拖慢其它订阅者;
推送线程只做 HTTP POST, 不碰 state.json / 任务队列, 不破坏「单写线程」假设
(黄金法则 5)。

阈值累计基数 = 当日上下行合计累计 (result.day_total_bytes) 相对**上次事件**的差;
跨天 (day_rolled) 把基数重置为新日的 0 —— 不产生跨天伪事件。基数不落盘: 重启后
从当前值重新起算, 首帧的 catch_up 补发负责让订阅者立刻刷新 (计划 §04 S4)。

事件体字段是计划 §04 S4 的拍板结论 (六个键, 不多不少): 订阅方按 event_id 单调
去重, 其余字段仅作日志/展示。
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from typing import TYPE_CHECKING, Callable, Mapping, Optional

if TYPE_CHECKING:
    from gtm.config import ConfigHolder
    from gtm.sampler import SampleResult
    from gtm.storage import Storage

logger = logging.getLogger("gtm.notifier")

# 在途推送线程上限 (防御性): 阈值被配成极小 + 订阅者多时, 事件频率可能高于推送
# 完成速度; 达上限即跳过本轮派发并 WARNING —— 订阅者靠慢轮询兜底, 不静默堆积线程。
DEFAULT_MAX_INFLIGHT_PUSHES = 32


def http_push(endpoint: str, token: str, event: Mapping[str, object], timeout_s: float) -> None:
    """生产推送单点: stdlib urllib POST JSON + Bearer token (失败即抛, 调用方兜)。

    与 auto-qb 接收面 (S7) 的约定: 订阅时登记的 token 即接收端的鉴权 token, 推送
    以 `Authorization: Bearer <token>` 出示; 非 2xx 由 urlopen 抛 HTTPError。
    """
    body = json.dumps(event, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "Content-Length": str(len(body)),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        response.read()


class Notifier:
    """阈值通知器 (S4): 累计变化 >= 阈值 -> 事件号 +1 -> 向存活订阅者推送。

    调用契约: notify() 由**采样线程**单线程调用 (黄金法则 5), 内部派发到守护线程;
    阈值/超时/租约参数每轮从 ConfigHolder 现读 —— PUT /config 热重载即时生效。
    """
    def __init__(
        self,
        storage: "Storage",
        config_holder: "ConfigHolder",
        *,
        pusher: Optional[Callable[[str, str, Mapping[str, object], float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
        max_inflight: int = DEFAULT_MAX_INFLIGHT_PUSHES,
    ) -> None:
        self._storage = storage
        self._config_holder = config_holder
        self._push = pusher or http_push
        self._clock = clock or time.time
        self._max_inflight = max_inflight
        self._lock = threading.Lock()
        self._inflight: set[threading.Thread] = set()
        self._last_total: Optional[int] = None
        self._closed = False

    # ---- 阈值判定 (采样线程) ----

    def notify(self, result: "SampleResult", *, catch_up: bool = False) -> Optional[dict[str, object]]:
        """单次采样后调用: 判定是否发事件; 发则先落盘、事件号 +1、异步派发推送。

        返回本次事件体 (未触发 -> None; 生产不依赖返回值, 供测试与日志)。

        基数推进纪律: `_last_total` **只在事件派发成功后**推进 —— 若随每个样本推进,
        「距上次事件的累计变化」就退化成单样本 delta, 缓慢但持续的流量永远攒不到阈值
        (计划 §04 S4 的语义是**累计**变化)。派发路径抛错 (如 state 落盘失败) 时基数
        不动 -> 阈值窗口保留, 下一轮重试 (与「单轮失败不杀守护进程」同纪律)。
        """
        total = result.day_total_bytes
        baseline_reset = self._last_total is None or result.day_rolled or total < self._last_total
        if baseline_reset:
            # 首个样本 / 跨天 / 累计回退 (不该发生): 基数归位, 不产生事件
            self._last_total = total
        if not catch_up and (
            baseline_reset or (total - self._last_total) < self._config_holder.current.notify_threshold_bytes
        ):
            return None
        event = self._emit(result)
        self._last_total = total
        return event

    def _emit(self, result: "SampleResult") -> dict[str, object]:
        """发一次事件: 落盘 -> 租约剔除 -> 事件号 +1 -> 派发 (派发在守护线程)。"""
        config = self._config_holder.current
        # ① 先确保文件已落盘: dat 可能正处节流窗口 (Δ<1MiB 且 <30s), 读者届时必读到新值
        try:
            self._storage.flush()
        except Exception:
            logger.exception("通知前置落盘失败 (仍继续推送: 订阅者亦可慢轮询读到旧值)")
        # ② 租约懒剔除 (与控制面请求入口同纪律) 后取订阅者快照
        try:
            removed = self._storage.prune_expired_subscribers(self._clock(), config.lease_ttl_s)
            if removed:
                logger.info("通知前剔除过期订阅者: %s", ", ".join(removed))
        except Exception:
            logger.exception("通知前租约剔除失败 (按现有注册表继续)")
        subscribers = self._storage.subscribers
        # ③ 事件号 +1 (落盘: 重启后接续, 不回到 0)
        event: dict[str, object] = {
            "event_id": self._storage.bump_event_id(),
            "day": result.day.isoformat(),
            "up_bytes": result.day_up_bytes,
            "down_bytes": result.day_down_bytes,
            "total_bytes": result.day_total_bytes,
            "ts": round(self._clock(), 3),
        }
        self._dispatch(event, subscribers, config.notify_timeout_s)
        return event

    # ---- 派发 (守护线程; 不占采样循环) ----

    def _dispatch(
        self,
        event: Mapping[str, object],
        subscribers: Mapping[str, Mapping[str, object]],
        timeout_s: float,
    ) -> None:
        if not subscribers:
            logger.info(
                "通知事件 #%s | day=%s total=%s, 无存活订阅者, 跳过推送", event["event_id"], event["day"], event["total_bytes"]
            )
            return
        with self._lock:
            if self._closed:
                logger.warning("通知器已关闭, 事件 #%s 不派发", event["event_id"])
                return
            if len(self._inflight) >= self._max_inflight:
                logger.warning("在途推送线程已达上限 %d, 事件 #%s 跳过派发 (订阅者靠慢轮询兜底)", self._max_inflight, event["event_id"])
                return
            for sub_id, entry in subscribers.items():
                thread = threading.Thread(
                    target=self._push_one,
                    args=(sub_id, entry, event, timeout_s),
                    name=f"gtm-notify-{sub_id}",
                    daemon=True,
                )
                # 先登记再 start (持锁): 线程结束时才可能摘除自己 —— 保证 _inflight 恒为
                # 「已登记」集合 (wait_idle/上限判据不会看到未启动的线程); 子线程若在
                # finally 里撞锁, 只是等本函数放锁, 不会死锁 (本函数不 join 任何线程)。
                self._inflight.add(thread)
                thread.start()
        logger.info(
            "通知事件 #%s | day=%s up=%s down=%s total=%s -> %d 订阅者 (超时 %ss)",
            event["event_id"],
            event["day"],
            event["up_bytes"],
            event["down_bytes"],
            event["total_bytes"],
            len(subscribers),
            timeout_s,
        )

    def _push_one(
        self,
        sub_id: str,
        entry: Mapping[str, object],
        event: Mapping[str, object],
        timeout_s: float,
    ) -> None:
        """单订阅者推送 (守护线程内): 失败只记 WARNING, 不重试 (慢轮询兜底)。"""
        endpoint = str(entry.get("endpoint", ""))
        token = str(entry.get("token", ""))
        try:
            self._push(endpoint, token, event, timeout_s)
            logger.info("通知推送成功 | 事件 #%s -> %s (id=%s)", event["event_id"], endpoint, sub_id)
        except Exception as e:
            logger.warning("通知推送失败 (不重试, 订阅者慢轮询兜底) | 事件 #%s endpoint=%s: %s", event["event_id"], endpoint, e)
        finally:
            with self._lock:
                self._inflight.discard(threading.current_thread())

    # ---- 生命周期 (测试 / 优雅退出) ----

    @property
    def pending_pushes(self) -> int:
        """在途推送线程数 (测试与日志用)。"""
        with self._lock:
            return len(self._inflight)

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """等在途推送结束; 返回是否已全部结束 (超时返回 False)。"""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                threads = list(self._inflight)
            if not threads:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            for thread in threads:
                thread.join(timeout=remaining)

    def close(self, timeout: float = 5.0) -> None:
        """优雅退出: 置关闭标志 (此后事件不再派发) + 有界等待在途推送。"""
        with self._lock:
            self._closed = True
        if not self.wait_idle(timeout):
            logger.warning("退出时仍有 %d 个推送线程在途 (守护线程, 随进程退出)", self.pending_pushes)

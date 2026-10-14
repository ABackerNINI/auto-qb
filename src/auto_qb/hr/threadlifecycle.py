"""hr 线程生命周期骨架(issue 26-10-11-0240 · dup-code-audit): 取数线程与端点共用骨架.

取数线程(worker)与端点线程(server)各写一套「幂等启动 + stop/join(timeout) + 退出/未退出日志」的
线程生命周期骨架 —— 本模块把骨架单点定义: 机制差异(取数线程用 Condition 置停止位, 端点用 shutdown)通过 request_stop 回调注入,
骨架(线程起 / join+timeout / 按退出/未退出记日志 / 句柄清或留)只写这里 —— 不各自一遍.

!叫停口纪律不在本骨架里而是在调用方stop里: cancel_all / shutdown要先,再join——否则一次正常关停要白等到满超时,
期间该站点锁死、进程退出也被拖住(见 pitfalls/backend/concurrency.md).
"""
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HrThreadHandle:
    """daemon 线程句柄: 幂等启动 + stop(请求停 -> join(timeout) -> 按退出/未退出记日志)"""

    __slots__ = ("_thread", )

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None

    @property
    def started(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, target: Callable[[], None], name: str) -> bool:
        """幂等启动: 线程已在跑则 False(调用方跳过启动日志); 否则起 daemon 线程并 True"""
        if self._thread is not None and self._thread.is_alive():
            return False
        self._thread = threading.Thread(target=target, name=name, daemon=True)
        self._thread.start()
        return True

    def stop(
        self,
        *,
        log: logging.Logger,
        subject: str,
        timeout: float,
        request_stop: Optional[Callable[[], None]] = None,
        stuck_note: str = "",
    ) -> bool:
        """请求停 -> join(timeout) -> 按退出/未退出记日志; 返回是否已退出

        未退出时句柄仍留线程(否则再也停不掉); 已退出时清.
        """
        if request_stop is not None:
            request_stop()
        thread = self._thread
        self._thread = None
        if thread is None:
            return True
        thread.join(timeout)
        if thread.is_alive():
            self._thread = thread
            log.error(f"{subject}在 {timeout:g}s 内未退出{stuck_note}")
            return False
        log.info(f"{subject}已停止")
        return True


__all__ = ["HrThreadHandle"]

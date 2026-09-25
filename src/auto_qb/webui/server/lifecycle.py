"""uvicorn 启停: WebServerHandle / start_web_server / stop_web_server(整段平移).

热重载重启同端口必须先 stop_web_server 等线程退出, 否则 Errno 10048(见 stop_web_server)。
"""
import asyncio
import errno
import logging
import os
import threading
import time
from typing import Any, Optional

import uvicorn

from .common import ensure_web_token
from .factory import create_app

logger = logging.getLogger("auto_qb.web")

WEB_STOP_TIMEOUT = 5.0
WEB_START_TIMEOUT = 5.0

# 网络波动噪音的节流窗口(秒): 窗口内只记首条, 末尾附被抑制条数
NET_NOISE_WINDOW = 60.0

# 判定"对端断开 / 网络波动"的异常集合 —— 这类不是本项目的 bug, 不该以 ERROR 级 traceback 出现
_NET_NOISE_EXCEPTIONS = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
_NET_NOISE_ERRNOS = frozenset(
    {
        errno.ECONNRESET,
        errno.ECONNABORTED,
        errno.EPIPE,
        errno.ESHUTDOWN,
        errno.ENOTCONN,
        errno.EHOSTDOWN,
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
        errno.ENETDOWN,
    }
)
# Windows 只给 winerror(10054 = 远程主机强迫关闭), errno 可能缺失或映射不到上面这些
_NET_NOISE_WINERRORS = frozenset({10051, 10053, 10054, 10057, 10058, 10060, 10064, 10065})

# 节流状态(只在 WEB 事件循环线程内读写: 单循环 + 重启前必 wait, 无需加锁)
_noise_state = {"at": 0.0, "suppressed": 0}


def _is_network_fluctuation(exc: Any) -> bool:
    """是否为"对端断开/网络波动"型异常(非程序 bug)"""
    if not isinstance(exc, OSError):
        return False
    if isinstance(exc, _NET_NOISE_EXCEPTIONS):
        return True
    if getattr(exc, "winerror", None) in _NET_NOISE_WINERRORS:
        return True
    return exc.errno in _NET_NOISE_ERRNOS


def _log_network_noise(exc: BaseException) -> None:
    """网络波动: 单行 INFO + 窗口节流(避免 SSE 重连 / 关页面刷屏)"""
    now = time.monotonic()
    suppressed = _noise_state["suppressed"]
    if now - _noise_state["at"] < NET_NOISE_WINDOW:
        _noise_state["suppressed"] = suppressed + 1
        return
    _noise_state["at"] = now
    _noise_state["suppressed"] = 0
    tail = f"(窗口内另有 {suppressed} 条同类已抑制)" if suppressed else ""
    logger.info(f"WEB 连接被对端中断(客户端关闭/网络波动, 非故障): {exc}{tail}")


def _web_loop_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """WEB 事件循环异常处理器: 网络波动降级为 INFO 日志, 其余照旧交给默认处理器

    背景(2026-09-24 实测): Windows ProactorEventLoop 下客户端(浏览器关页面 / SSE 重连 / 网络抖动)
    断开时, asyncio 在 `_ProactorBasePipeTransport._call_connection_lost` 里调 `sock.shutdown`,
    抛 `ConnectionResetError [WinError 10054]`, 被 asyncio 默认处理器以 ERROR + 整段 traceback 打到日志,
    看着像崩溃, 实为正常断连。这里把它降级成一行 INFO; **其它异常一律不吞**, 交给默认处理器。
    """
    exc = context.get("exception")
    if _is_network_fluctuation(exc):
        _log_network_noise(exc)
        return
    loop.default_exception_handler(context)


class _QuietLoopConfig(uvicorn.Config):
    """uvicorn.Config 子类: 给服务事件循环挂上 _web_loop_exception_handler

    uvicorn ≥0.36 用 `Server.run(..., loop_factory=config.get_loop_factory())` 创建循环 ——
    循环在 `asyncio.run` 内部才诞生, 服务线程里 `asyncio.get_event_loop()` 拿不到它,
    所以只能从 `get_loop_factory`(替代旧 `setup_event_loop` 的官方扩展点)注入。
    """
    def get_loop_factory(self):
        base = super().get_loop_factory()

        def _factory():
            loop = base() if base is not None else asyncio.new_event_loop()
            loop.set_exception_handler(_web_loop_exception_handler)
            return loop

        return _factory


class WebServerHandle:
    """WEB 服务器句柄(uvicorn 独立线程)

    stop() 仅请求退出(异步: uvicorn 主循环每 0.1s 才读一次 should_exit, 随后才关闭监听套接字);
    wait() 等待服务线程真正退出。**重启同端口必须 stop 后 wait**, 否则新服务 bind 报
    Errno 10048(每个套接字地址只允许使用一次)。
    """

    __slots__ = ("server", "thread")

    def __init__(self, server: uvicorn.Server, thread: threading.Thread) -> None:
        self.server = server
        self.thread = thread

    def stop(self) -> None:
        """请求停止(返回时服务仍在退出中, 需 wait() 确认已释放端口)"""
        self.server.should_exit = True

    def wait(self, timeout: Optional[float] = None) -> bool:
        """等待服务线程退出; 返回是否已退出(False = 超时仍在运行)"""
        self.thread.join(timeout)
        return not self.thread.is_alive()

    @property
    def started(self) -> bool:
        """监听是否已就绪(uvicorn 在 create_server 成功后置位)"""
        return bool(self.server.started)


def _run_server(server: uvicorn.Server) -> None:
    """服务线程入口: 把 uvicorn 的失败退出记进日志

    bind 失败时 uvicorn 走 sys.exit(STARTUP_FAILURE), 而 SystemExit 在非主线程被 threading
    静默吞掉(只剩 uvicorn 自己那行无时间戳的 ERROR), 日志上看不出"WEB UI 已经死了"。
    这里就地记录(含异常链: OSError -> SystemExit)后不再上抛 —— 上抛同样被吞, 只会多一份噪音。
    """
    try:
        server.run()
    except BaseException:
        logger.error("WEB UI 服务异常退出(端口被占用/监听失败?)", exc_info=True)


def _wait_until_started(handle: WebServerHandle, timeout: float) -> bool:
    """等待监听就绪: server.started 置位即成功; 线程提前退出(启动失败)/超时返回 False"""
    deadline = time.monotonic() + timeout
    while not handle.started:
        if not handle.thread.is_alive():
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)
    return True


def start_web_server(manager) -> WebServerHandle:
    """启动 WEB 服务器(独立线程); 返回句柄(stop()/wait())

    就绪(或确认失败)后才打日志: 起线程后立即打印会掩盖 bind 失败(端口被占用时依然显示"已启动")。
    """
    manager._web_token = ensure_web_token(manager)
    app = create_app(manager)
    config = _QuietLoopConfig(
        app,
        host=manager.config.web.host,
        port=manager.config.web.port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_run_server, args=(server, ), name="auto-qb-web", daemon=True)
    thread.start()
    handle = WebServerHandle(server, thread)
    if _wait_until_started(handle, WEB_START_TIMEOUT):
        # 生命周期消息按 INFO 记(pitfalls/ops/alert-levels.md: 启动类不许用 WARNING, 否则 notify
        # 开启时每次启动都弹通知; 监听地址本身在消息文本里, 0.0.0.0 的暴露面由配置 UI 的 risk 提示兜底)
        logger.info(
            f"WEB UI 已启动: http://{manager.config.web.host}:{manager.config.web.port} "
            f"(密钥见 {os.path.join(os.path.dirname(manager.state_file) or '.', 'web.token')})"
        )
    else:
        logger.error(
            f"WEB UI 启动失败: {manager.config.web.host}:{manager.config.web.port} 无法监听"
            "(端口被占用? 详见上方 uvicorn 错误)"
        )
    return handle


def stop_web_server(handle: WebServerHandle, timeout: float = WEB_STOP_TIMEOUT) -> bool:
    """请求停止并等待服务线程退出; 返回是否已退出(False = 超时仍在运行, 调用方自行决定)

    热重载重启(host/port 变更)必须先走本函数: 只 handle.stop() 就立刻启新服务,
    旧服务的监听套接字尚未释放 -> Errno 10048。
    """
    handle.stop()
    if handle.wait(timeout):
        return True
    logger.warning(f"WEB UI 旧服务在 {timeout:g}s 内未退出, 仍尝试重启(监听套接字通常已释放)")
    return False

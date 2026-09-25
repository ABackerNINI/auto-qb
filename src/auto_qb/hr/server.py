"""本地取数端点(计划 §6/§8 · M2): 扩展 ⇄ 后端 的唯一网络面, **只听 127.0.0.1**。

职责与边界(硬约束):

- 三个端点: `GET /api/hr/tasks` 给扩展「当前可取的清单」, `POST /api/hr/result` 收回传,
  `GET /api/hr/sites` 给选项页「需要授权的站点清单」(只读辅助, 同样过 token + origin 两道关);
- 端点线程**只入队** —— 除了内存队列它什么都不碰: 不写 state_file / hr 站点文件 / 任务队列,
  也不解析页面(解析在取数线程, 见 service.py); 因此「任意网页 JS 打端点」最坏只能污染一条
  待解析的结果, 而那条结果还得先通过「任务 id 确实派发过 + 域名一致」两道关;
- 鉴权: 无 token / token 不符 ⇒ **401 且不写任何状态**; 非扩展 origin ⇒ 403(纵深防御);
  真鉴权是 token —— origin 白名单只是第二道(扩展 id 未必定得住, 见计划 §6);
- URL 白名单(SSRF)在**下发任务时**卡死(见 channel.UrlPolicy), 端点本身不接受任何 URL 入参。

❗`allow_reuse_address = False`: Windows 上 `SO_REUSEADDR` 允许**抢绑**已在监听的端口, 会让
  「同机多实例配了同一个 port ⇒ 启动 fail-fast」这条守卫失效; 关掉它才是真的独占。
"""
import json
import logging
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from typing import Any, Callable, Dict, Optional, Set, Tuple

from .channel import (
    API_RESULT,
    API_SITES,
    API_TASKS,
    DEFAULT_POLL_HINT,
    MAX_BODY_BYTES,
    ORIGIN_HEADER,
    TOKEN_HEADER,
    ChannelStatus,
    HrChannelBindError,
    HrChannelError,
    decode_json,
    origin_allowed,
    parse_results,
)
from .queue import HrTaskQueue

logger = logging.getLogger(__name__)

ENDPOINT_STOP_TIMEOUT = 5.0
_JSON = "application/json; charset=utf-8"


class _LoopbackServer(ThreadingHTTPServer):
    """单机端点: 线程池处理 + 严格独占端口(见模块 docstring)"""
    daemon_threads = True
    #: ❗关掉地址复用: Windows 上它会允许第二个进程抢绑同一端口, 端口占用就检测不出来了
    allow_reuse_address = False

    def server_bind(self) -> None:  # type: ignore[override]
        """只绑地址, **不查 FQDN**

        HTTPServer.server_bind 会调 socket.getfqdn(可能触发一次 DNS 解析/反向查询);
        本端点只服务 127.0.0.1, 不需要主机名, 而那次查询在无网/弱网机器上会抱几秒 ——
        启动期不应为它付出代价。
        """
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class HrEndpointHandle:
    """端点句柄: stop() 请求退出, wait() 等线程真正退出(重启同端口必须先 wait)"""

    __slots__ = ("server", "thread", "port")

    def __init__(self, server: _LoopbackServer, thread: threading.Thread, port: int) -> None:
        self.server = server
        self.thread = thread
        self.port = port

    @property
    def started(self) -> bool:
        return self.thread.is_alive()

    def stop(self) -> None:
        self.server.shutdown()

    def wait(self, timeout: Optional[float] = None) -> bool:
        self.thread.join(timeout)
        return not self.thread.is_alive()


class HrChannelServer:
    """本地端点(纯逻辑可单测: 路由与鉴权在 `route()`, HTTP 层只是薄适配)"""
    def __init__(
        self,
        *,
        queue: HrTaskQueue,
        token: str,
        port: int = 8788,
        host: str = "127.0.0.1",
        extension_id: str = "",
        poll_hint: float = DEFAULT_POLL_HINT,
        now_fn: Callable[[], float] = time.time,
        sites_fn: Optional[Callable[[], List[Tuple[str, str]]]] = None,
    ) -> None:
        self.queue = queue
        self.token = token
        self.host = host
        self.port = int(port)
        self.extension_id = extension_id
        self.poll_hint = poll_hint
        #: 返回 [(站点名, 匹配模式), ...] —— 每次请求现读(不是构造时快照): 热重载加了站点
        #: 不改变端点监听身份(不重绑), 构造期快照会把新站点漏在授权清单外面。
        self.sites_fn = sites_fn
        self._now = now_fn
        self._state_lock = threading.Lock()
        self._last_contact_ts = 0.0
        self._origins: Set[str] = set()
        self._handle: Optional[HrEndpointHandle] = None

    # ---------- 生命周期 ----------

    def start(self) -> HrEndpointHandle:
        """启动监听; 端口被占 ⇒ 抛 HrChannelBindError(不静默降级, 见计划 §7)"""
        handler = self._make_handler()
        try:
            server = _LoopbackServer((self.host, self.port), handler)
        except OSError as e:
            raise HrChannelBindError(
                f"HR 取数通道端点无法监听 {self.host}:{self.port} ({e}) —— 端口被占用? "
                "同机多实例必须各用不同的 hr_check.channel.port"
            ) from e
        thread = threading.Thread(target=server.serve_forever, name="auto-qb-hr-channel", daemon=True)
        thread.start()
        self._handle = HrEndpointHandle(server, thread, server.server_address[1])
        # INFO 而非 WARNING: 本仓 WARNING 以上会被推成系统通知, 而「端点起来了」是预期内的事
        logger.info(f"HR 取数通道端点已启动: http://{self.host}:{self._handle.port}(仅监听本机回环, 需 token 鉴权)")
        return self._handle

    def stop(self, timeout: float = ENDPOINT_STOP_TIMEOUT) -> bool:
        """停止监听并等线程退出(重启同端口必须先走这里)"""
        handle = self._handle
        self._handle = None
        if handle is None:
            return True
        handle.stop()
        ok = handle.wait(timeout)
        try:
            handle.server.server_close()
        except OSError:  # 关闭失败不影响"已停止服务"的事实
            logger.debug("HR 取数通道端点关闭套接字时报错(忽略)", exc_info=True)
        if ok:
            logger.info("HR 取数通道端点已停止")
        else:
            logger.warning(f"HR 取数通道端点在 {timeout:g}s 内未退出")
        return ok

    @property
    def started(self) -> bool:
        return self._handle is not None and self._handle.started

    @property
    def last_contact_ts(self) -> float:
        with self._state_lock:
            return self._last_contact_ts

    def status(self, *, enabled: bool = True) -> ChannelStatus:
        """自检快照(不含密钥内容)"""
        with self._state_lock:
            contact, origins = self._last_contact_ts, sorted(self._origins)
        listening = self.started
        bound_port = self._handle.port if self._handle is not None else self.port
        return ChannelStatus(
            enabled=enabled,
            listening=listening,
            port=bound_port,
            endpoint=f"http://{self.host}:{bound_port}{API_TASKS}",
            last_contact_ts=contact,
            pending=self.queue.pending(),
            extensions_seen=origins,
            note="" if listening else "端点未在监听",
        )

    # ---------- 路由(纯逻辑, 不碰 socket) ----------

    def route(self, method: str, path: str, headers: Any, body: bytes = b"") -> Tuple[int, Dict[str, str], bytes]:
        """HTTP 请求 -> (状态码, 响应头, 响应体)。鉴权与白名单全在这里, 便于直接钉死。"""
        origin = _header(headers, ORIGIN_HEADER)
        cors: Dict[str, str] = {}
        if not origin_allowed(origin, self.extension_id):
            # 非扩展 origin(普通网页 JS): 拒; 不给 CORS 头, 让浏览器也读不回响应
            logger.warning(f"HR 取数通道 | 拒绝非白名单 origin: {origin or '(空)'}")
            return 403, {}, _json({"error": "origin not allowed"})
        if origin:
            cors["Access-Control-Allow-Origin"] = origin
            cors["Vary"] = "Origin"
        route_path = path.split("?", 1)[0]
        if method == "OPTIONS":
            return 204, {
                **cors,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": f"{TOKEN_HEADER}, Content-Type",
                "Access-Control-Max-Age": "600",
            }, b""

        if not self._token_ok(_header(headers, TOKEN_HEADER)):
            # ❗401 之前不写任何状态(不记接触、不入队、不落盘)
            logger.warning(f"HR 取数通道 | 鉴权失败({method} {route_path}), 已拒绝且未写任何状态")
            return 401, {**cors, "WWW-Authenticate": "X-Hr-Token"}, _json({"error": "unauthorized"})

        self._note_contact(origin)

        if method == "GET" and route_path == API_TASKS:
            return 200, cors, self._tasks_response()
        if method == "GET" and route_path == API_SITES:
            return 200, cors, self._sites_response()
        if method == "POST" and route_path == API_RESULT:
            if len(body) > MAX_BODY_BYTES:
                return 413, cors, _json({"error": "body too large"})
            return self._result_response(body, cors)
        return 404, cors, _json({"error": "not found"})

    def _tasks_response(self) -> bytes:
        tasks = self.queue.take_batch()
        return _json(
            {
                "tasks": [t.to_json() for t in tasks],
                "next_poll_s": self.poll_hint,
                "server_time": round(self._now(), 3),
            }
        )

    def _sites_response(self) -> bytes:
        """需要授权的站点清单(扩展选项页勾选用的只读辅助, 不碰任何状态)。

        sites_fn 抛异常(如配置热重载窗口)不该打死端点线程: 回 200 + 空清单 + error,
        扩展把 error 原样亮给用户, 下一轮点一下就好。
        """
        sites: List[Dict[str, str]] = []
        error = ""
        if self.sites_fn is not None:
            try:
                for site, origin in self.sites_fn():
                    if site and origin:
                        sites.append({"site": site, "origin": origin})
            except Exception as e:
                logger.warning(f"HR 取数通道 | 生成站点授权清单失败: {e}", exc_info=True)
                error = f"站点清单生成失败: {e}"
        return _json({"sites": sites, "error": error, "server_time": round(self._now(), 3)})

    def _result_response(self, body: bytes, cors: Dict[str, str]) -> Tuple[int, Dict[str, str], bytes]:
        try:
            results = parse_results(decode_json(body))
        except HrChannelError as e:
            logger.warning(f"HR 取数通道 | 回传体无法解析, 已丢弃: {e}")
            return 400, cors, _json({"error": str(e)})
        accepted = rejected = 0
        for result in results:
            if self.queue.submit(result):
                accepted += 1
            else:
                rejected += 1
        if accepted == 0:
            # 全部被拒(任务 id 没派发过 / 已作废 / 域名不符) —— 不入任何状态
            return 400, cors, _json({"accepted": 0, "rejected": rejected, "error": "no matching task"})
        if rejected:
            logger.warning(f"HR 取数通道 | 本批回传有 {rejected} 条不匹配任务, 已丢弃")
        return 200, cors, _json({"accepted": accepted, "rejected": rejected})

    # ---------- 内部 ----------

    def _token_ok(self, given: str) -> bool:
        """常数时间比较(避免用比较耗时反推密钥); 未配置 token 时一律拒"""
        return bool(given) and bool(self.token) and secrets.compare_digest(given, self.token)

    def _note_contact(self, origin: str) -> None:
        """记一次通道接触(静默告警的判据); 只成功鉴权的请求会走到这里"""
        with self._state_lock:
            self._last_contact_ts = self._now()
            if origin:
                self._origins.add(origin)

    def _make_handler(self):
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "auto-qb-hr/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 (基类签名)
                logger.debug("HR 端点 %s - %s", self.address_string(), fmt % args)

            def do_GET(self) -> None:  # noqa: N802 (基类签名)
                self._dispatch("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._dispatch("POST")

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._dispatch("OPTIONS")

            def _dispatch(self, method: str) -> None:
                length = _content_length(self.headers)
                if length > MAX_BODY_BYTES:
                    self._safe_respond(413, {}, _json({"error": "body too large"}))
                    return
                body = self.rfile.read(length) if length else b""
                try:
                    status, headers, payload = outer.route(method, self.path, self.headers, body)
                except Exception as e:  # 端点线程绝不因单请求异常退出
                    logger.error(f"HR 取数通道 | 处理 {method} {self.path} 异常: {e}", exc_info=True)
                    status, headers, payload = 500, {}, _json({"error": "internal error"})
                self._safe_respond(status, headers, payload)

            def _safe_respond(self, status: int, headers: Dict[str, str], payload: bytes) -> None:
                """写响应; 客户端半路断开(BrokenPipe)不该冒泡成 traceback —— 那是常态不是故障"""
                try:
                    self._respond(status, headers, payload)
                except (ConnectionError, OSError) as e:
                    logger.debug(f"HR 取数通道 | 响应写失败(客户端已断开): {e}")

            def _respond(self, status: int, headers: Dict[str, str], payload: bytes) -> None:
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Type", _JSON)
                self.send_header("Content-Length", str(len(payload)))
                # 每请求关闭: 端点每 5 分钟才被拉一次, 长连接没有收益, 却会在监听套接字上
                # 留下半开连接(影响重启时的独占绑定)
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                if payload:
                    self.wfile.write(payload)

        return _Handler


def _header(headers: Any, name: str) -> str:
    """取头值(兼容 dict 与 email.message.Message; 大小写不敏感)"""
    if headers is None:
        return ""
    get = getattr(headers, "get", None)
    if callable(get):
        got = get(name)
        if got:
            return str(got)
    try:
        items = headers.items()
    except AttributeError:
        return ""
    lowered = name.lower()
    for key, value in items:
        if str(key).lower() == lowered:
            return str(value)
    return ""


def _content_length(headers: Any) -> int:
    try:
        return max(0, int(_header(headers, "Content-Length") or 0))
    except ValueError:
        return 0


def _json(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


__all__ = ["ENDPOINT_STOP_TIMEOUT", "HrChannelServer", "HrEndpointHandle"]

"""控制面: 本地 HTTP 服务 (S3 实现).

stdlib ThreadingHTTPServer, 强制绑定回环地址 (config 校验层限定 127.0.0.0/8 与 ::1,
默认 127.0.0.1; 端口默认 0 = 内核分配随机端口, 可配; 占用即 fail-fast)。鉴权 Bearer
token: 首次启动原子生成 monitor.token (临时文件 + 重命名), 比对用 compare_digest
(照 auto-qb auth.py 模式)。

端点:
  GET  /status       采样状态、当日累计、末事件号、订阅者数、文件路径、配置回显
  PUT  /config       全量校验 -> 原子写 config.yml -> 热重载 (last-writer-wins)
  POST /subscribe    {endpoint, token} 注册订阅 (租约 last_heartbeat + lease_ttl)
  POST /heartbeat    {id} 心跳续租 (订阅方每 60s)
  POST /unsubscribe  {id} 注销
  POST /autostart    {action: install|uninstall} 幂等注册/卸载开机自启 (S6: 供
                     auto-qb 设置页开关; 在工具进程内跑 installer, sys.executable
                     = 装了 gtm 的 venv python, 即自启项要指向的解释器; 成功回写工具
                     config autostart —— 自启意图的唯一裁决权, S14/D13)
  POST /shutdown    请求优雅退出 (26-10-17-1737 S3: 供 auto-qb 设置页「停止工具」代理):
                     **先回 200 再触发停止** —— 响应已在路上, 退出走 cmd_run 的 finally
                     (最终落盘 + 释放锁 + 停控制面 + 删发现指针), 对调用方表现为
                     「200 之后连接自然断开」。未绑定 stop_event (非 run 装配) -> 200 + WARNING。

租约: last_heartbeat + lease_ttl (默认 180s) 过期剔除 —— 懒剔除 (每个已鉴权
请求入口先 prune; S4 notifier 迭代前同样先 prune), 无后台清扫线程: 请求驱动
即保证 /status 计数准确, 少一条常驻线程的生命周期管理面。

Windows 绑定语义 (坑档 platform-fs / web): HTTPServer 默认 allow_reuse_address
= 1 在 Windows 映射为**抢占式** SO_REUSEADDR —— 端口被别的进程监听时 bind 仍
会成功 (静默双监听, 流量随机分流) ⇒ Windows 上必须关掉才能「占用即 fail-fast」;
POSIX 上 SO_REUSEADDR 只绕 TIME_WAIT 不抢监听 ⇒ 保留 True 便于重启。

发现指针 (S12 / D6): bind 成功后把 {schema, version, pid, started_at, host, port,
data_dir, token_path, exe_path, autostart_registered, autostart_error} (字段见计划 §05)
原子写进用户级指针目录 endpoint.json, 优雅退出 (stop / atexit) 删除 —— auto-qb 据此
发现工具 (免配端口、免端口漂移); 写入失败只 WARNING 不阻断服务 (§09)。
`autostart_error` 是 2026-10-17 追加的可选字段 (issue 26-10-17-1455): 启动期注册失败的
原因, 成功/未尝试为 null; schema 不升版 —— 旧读者忽略未知键, 新读者 `.get` 得 None。
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import secrets
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlsplit

from gtm import __version__
from gtm.config import ConfigHolder, config_to_payload, save_config, validate_payload
from gtm.installer import AutostartError, UnsupportedPlatformError, build_installer
from gtm.sampler import Sampler
from gtm.storage import ENDPOINT_SCHEMA, Storage, atomic_write_text, endpoint_path, remove_endpoint, write_endpoint

logger = logging.getLogger("gtm.server")

# 请求体上限 (1 MiB): config/订阅载荷都是小 JSON, 上限防内存滥用
_MAX_BODY_BYTES = 1 * 1024 * 1024

# token 强度: urlsafe(32) = 256 bit (与 auto-qb 事件票据同族但更长 —— 控制面是
# 常驻密钥, 不是一次性票据)
_TOKEN_BYTES = 32


class TokenManager:
    """monitor.token: 首次启动原子生成, 之后加载; compare_digest 比对.

    生成 = secrets.token_urlsafe(32) 经 atomic_write_text (同目录 tmp + fsync +
    replace) 落盘 —— 并发读者 (auto-qb 设置页读 token 路径) 只见完整文件。
    文件已存在则原样加载 (重启不换密钥, 订阅方缓存的密钥不失效)。
    """
    def __init__(self, path: str) -> None:
        self.path = path
        self._token: Optional[str] = None
        self._lock = threading.Lock()

    def token(self) -> str:
        """获取工具密钥 (首次调用时生成并落盘; 线程安全)."""
        if self._token is None:
            with self._lock:
                if self._token is None:
                    self._token = self._load_or_generate()
        return self._token

    def _load_or_generate(self) -> str:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            if existing:
                return existing
        except FileNotFoundError:
            pass
        except OSError:
            # 读失败不当成"不存在" —— 直接抛, 让启动 fail-fast (静默换密钥会让
            # 已订阅方全部 401, 比启动失败更难排查)
            raise
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        atomic_write_text(self.path, token + "\n")
        logger.info("已生成控制面密钥 %s (首次启动)", self.path)
        return token

    def verify(self, presented: Optional[str]) -> bool:
        """比对 (空值直接 False; compare_digest 防时序侧信道, 照 auto-qb auth.py)."""
        if not presented:
            return False
        return secrets.compare_digest(presented, self.token())


def _valid_endpoint(endpoint: Any) -> bool:
    """订阅端点合法性: http(s) URL 且带主机名 (S4 notifier 将向其 POST)."""
    if not isinstance(endpoint, str) or not endpoint.strip():
        return False
    try:
        parts = urlsplit(endpoint.strip())
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


class ControlServer:
    """控制面服务: ThreadingHTTPServer + 请求分发 + 鉴权闸 + 租约懒剔除.

    start() 绑定并起 serve_forever 守护线程 —— 端口占用/绑定失败抛 OSError 由
    调用方 fail-fast (计划 §03 S3: 占用即 fail-fast); stop() 关闭并回收线程。
    /status 直读 sampler 引用 (采样线程持有的活对象; 整数字段读取原子, 字段间
    不强求同一快照 —— 单调计数, 交叉读到的仍是一致的历史值)。
    """
    def __init__(
        self,
        storage: Storage,
        sampler: Sampler,
        config_holder: ConfigHolder,
        token_manager: TokenManager,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        started_at: Optional[float] = None,
        installer_factory: Optional[Callable[[str], Any]] = None,
        endpoint_file: Optional[str] = None,
        autostart_error: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        self.storage = storage
        self.sampler = sampler
        self.config_holder = config_holder
        self.token_manager = token_manager
        self.host = host
        self.port = port
        self._started_at = started_at if started_at is not None else time.time()
        # 自启后端工厂 (S6 /autostart): 默认 = 真 installer; 单测注入替身以 hermetic
        self._installer_factory = installer_factory or build_installer
        # 启动期自启注册的失败原因 (S14/D13): 注册发生在 server 起来之前, 那时没有指针
        # 可写, 故由调用方把原因带进来, 写指针时一起落盘 (None = 没失败/没尝试)
        self._autostart_error = autostart_error
        # 发现指针路径 (S12/D6): 默认用户级目录; 单测注入 tmp 路径保持 hermetic
        self._endpoint_file = endpoint_file or endpoint_path()
        # 优雅退出信号 (26-10-17-1737 S3): POST /shutdown 置位; 由 cmd_run 把主循环的
        # stop_event 交进来 (退出仍走既有 finally: 最终落盘 + 释放锁 + 停控制面 + 删指针)。
        # None = 非 run 装配(单测/复用场景), /shutdown 仍回 200 但不置位(只 WARNING)。
        self._stop_event = stop_event
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        # config.yml 双 HTTP 线程写点的串行化锁 (与 storage._state_lock 同族的单写防护):
        # PUT /config 全量覆盖与 POST /autostart 读-改-写 (基于旧 Config 快照整份回写) 并发
        # 交叠会丢更新 —— 读到旧快照后他人写入的新参数被整份覆盖回去。save_config +
        # holder.replace 的临界区一律持锁; 锁内无网络/无重活, 不长占。
        self._config_write_lock = threading.Lock()

    @property
    def config_path(self) -> str:
        return os.path.join(self.storage.data_dir, "config.yml")

    # ---- 生命周期 ----

    def start(self) -> None:
        """绑定 + 起守护线程 serve_forever. 端口占用/绑定失败 -> OSError (fail-fast).

        启动即生成/加载密钥 (不惰性): monitor.token 必须在监听前存在 —— 订阅方
        (auto-qb WebUI) 从文件读密钥再来鉴权, 惰性生成会鸡生蛋 (没文件读不出
        密钥, 没密钥的请求又触不发生成的路径之外)。首启原子生成, 重启原样加载。

        Windows: 关掉抢占式 SO_REUSEADDR 才 fail-fast (见模块 docstring);
        POSIX: 保留 True 绕 TIME_WAIT, 重启友好。
        """
        self.token_manager.token()  # 首启原子生成 / 重启加载 (失败即抛, 启动 fail-fast)

        class _Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = not sys.platform.startswith("win")

        self._httpd = _Server((self.host, self.port), _Handler)
        self._httpd.control_server = self  # type: ignore[attr-defined]  # handler 反向引用单点
        self.port = self._httpd.server_address[1]  # port=0 时取实际绑定端口
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="gtm-http", daemon=True)
        self._thread.start()
        self._write_endpoint()  # bind 成功后写发现指针 (S12/D6)
        logger.info("控制面已监听 http://%s:%d (鉴权 Bearer token)", self.host, self.port)

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._remove_endpoint()  # 优雅退出删发现指针 (幂等)

    # ---- 发现指针 (S12 / D6) ----

    def _write_endpoint(self) -> None:
        """bind 成功后原子写发现指针 endpoint.json (字段见计划 §05)。

        写入失败只 WARNING 不 fail-fast (§09): 指针目录不可写时工具仍服务,
        auto-qb 侧退化为「直接探默认端口」; 指针是发现便利, 不是运行前提。
        成功后注册 atexit —— 硬退出 (未走 stop) 也尽力删指针 (D6/D7)。
        """
        payload = {
            "schema": ENDPOINT_SCHEMA,
            "version": __version__,
            "pid": os.getpid(),
            "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "host": self.host,
            "port": self.port,
            "data_dir": os.path.abspath(self.storage.data_dir),
            "token_path": os.path.abspath(self.token_manager.path),
            "exe_path": sys.executable,
            "autostart_registered": self._autostart_registered(),
            "autostart_error": self._autostart_error,
        }
        try:
            written = write_endpoint(payload, path=self._endpoint_file)
        except OSError as e:
            logger.warning("发现指针写入失败 (不阻断服务): %s", e)
            return
        atexit.register(self._remove_endpoint)
        logger.info("发现指针已写: %s (pid=%d, port=%d)", written, payload["pid"], self.port)

    def _remove_endpoint(self) -> None:
        remove_endpoint(path=self._endpoint_file)

    def _autostart_registered(self) -> bool:
        """自启是否已注册 (§05 指针字段): 现货态探测, 供 auto-qb 设置页读开关 (D13/D19)。

        平台不支持 / 查询失败 / 替身后端无该能力一律按未注册 (该字段是诊断便利,
        不能反过来影响服务启动)。自启意图的裁决 (工具 config autostart) 由 S14 落定:
        run --autostart 只在 config autostart=true 时注册, POST /autostart 回写该键。
        """
        try:
            backend = self._installer_factory(self.storage.data_dir)
            probe = getattr(backend, "is_registered", None)
            return bool(probe()) if callable(probe) else False
        except Exception as e:  # noqa: BLE001 - 动态探测, 任何失败都必须降级而非拖垮启动
            logger.debug("自启注册状态查询失败 (按未注册): %s", e)
            return False

    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ---- 请求分发 (handler 线程调用; 注册表经 Storage 同锁路径) ----

    def handle(self, handler: "_Handler") -> None:
        """按 (method, path) 分发; 鉴权闸前置 (401 短路, 不进端点)."""
        auth = handler.headers.get("Authorization") or ""
        presented = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""
        if not presented:
            self._send(handler, 401, {"error": "invalid token"})
            return
        if not self.token_manager.verify(presented):
            logger.warning("鉴权失败: 密钥不匹配")
            self._send(handler, 401, {"error": "invalid token"})
            return
        self._prune_leases()
        path = urlsplit(handler.path).path
        if handler.command == "GET" and path == "/status":
            return self._status(handler)
        if handler.command == "PUT" and path == "/config":
            return self._put_config(handler)
        if handler.command == "POST" and path == "/subscribe":
            return self._subscribe(handler)
        if handler.command == "POST" and path == "/heartbeat":
            return self._heartbeat(handler)
        if handler.command == "POST" and path == "/unsubscribe":
            return self._unsubscribe(handler)
        if handler.command == "POST" and path == "/autostart":
            return self._autostart(handler)
        if handler.command == "POST" and path == "/shutdown":
            return self._shutdown(handler)
        self._send(handler, 404, {"error": f"unknown endpoint: {handler.command} {path}"})

    def _prune_leases(self) -> tuple[str, ...]:
        """租约懒剔除 (每个已鉴权请求入口调用; 有剔除时日志可见)."""
        ttl = self.config_holder.current.lease_ttl_s
        removed = self.storage.prune_expired_subscribers(time.time(), ttl)
        if removed:
            logger.info("租约过期剔除订阅者: %s", ", ".join(removed))
        return removed

    # ---- 端点 ----

    def _status(self, handler: "_Handler") -> None:
        config = self.config_holder.current
        self._send(
            handler,
            200,
            {
                "ok": True,
                "day": self.sampler.day.isoformat() if self.sampler.day else None,
                "day_up_bytes": self.sampler.day_up_bytes,
                "day_down_bytes": self.sampler.day_down_bytes,
                "day_total_bytes": self.sampler.day_total_bytes,
                "last_event_id": self.storage.last_event_id,
                "subscriber_count": len(self.storage.subscribers),
                "lease_ttl_s": config.lease_ttl_s,
                "heartbeat_interval_s": config.heartbeat_interval_s,
                "sample_interval": config.sample_interval,
                "http_host": config.http_host,
                "http_port": config.http_port,
                "paths":
                    {
                        "dat": self.storage.dat_path,
                        "state": self.storage.state_path,
                        "config": self.config_path,
                        "token": self.token_manager.path,
                    },
                "config": config_to_payload(config),
                "uptime_s": round(time.time() - self._started_at, 3),
            },
        )

    def _put_config(self, handler: "_Handler") -> None:
        body, err = self._read_json(handler)
        if err is not None:
            return self._send(handler, 400, {"error": err})
        assert body is not None
        if not isinstance(body, dict):
            return self._send(handler, 400, {"error": "配置载荷必须是 JSON 对象"})
        config, errors = validate_payload(body)
        if config is None:
            return self._send(handler, 400, {"ok": False, "errors": list(errors)})
        with self._config_write_lock:
            save_config(self.config_path, config)
            self.config_holder.replace(config)
        logger.info("配置热重载: %s", self.config_path)
        self._send(handler, 200, {"ok": True, "config": config_to_payload(config)})

    def _subscribe(self, handler: "_Handler") -> None:
        body, err = self._read_json(handler)
        if err is not None:
            return self._send(handler, 400, {"error": err})
        assert body is not None
        if not isinstance(body, dict):
            return self._send(handler, 400, {"error": "订阅载荷必须是 JSON 对象"})
        endpoint = body.get("endpoint")
        token = body.get("token")
        if not _valid_endpoint(endpoint):
            return self._send(handler, 400, {"error": "endpoint 必须是带主机名的 http(s) URL"})
        if not isinstance(token, str) or not token.strip():
            return self._send(handler, 400, {"error": "token 必须是非空字符串 (S4 推送时出示)"})
        sub_id = secrets.token_hex(8)
        self.storage.upsert_subscriber(sub_id, endpoint.strip(), token.strip())
        config = self.config_holder.current
        logger.info("订阅注册: id=%s endpoint=%s", sub_id, endpoint.strip())
        self._send(
            handler,
            200,
            {
                "ok": True,
                "id": sub_id,
                "lease_ttl_s": config.lease_ttl_s,
                "heartbeat_interval_s": config.heartbeat_interval_s
            },
        )

    def _heartbeat(self, handler: "_Handler") -> None:
        body, err = self._read_json(handler)
        if err is not None:
            return self._send(handler, 400, {"error": err})
        assert body is not None
        if not isinstance(body, dict):
            return self._send(handler, 400, {"error": "心跳载荷必须是 JSON 对象"})
        sub_id = body.get("id")
        if not isinstance(sub_id, str) or not sub_id:
            return self._send(handler, 400, {"error": "id 必须是非空字符串"})
        if not self.storage.touch_subscriber(sub_id):
            return self._send(handler, 404, {"error": "unknown subscriber id"})
        ttl = self.config_holder.current.lease_ttl_s
        self._send(handler, 200, {"ok": True, "lease_ttl_s": ttl, "expires_in_s": ttl})

    def _unsubscribe(self, handler: "_Handler") -> None:
        body, err = self._read_json(handler)
        if err is not None:
            return self._send(handler, 400, {"error": err})
        assert body is not None
        if not isinstance(body, dict):
            return self._send(handler, 400, {"error": "注销载荷必须是 JSON 对象"})
        sub_id = body.get("id")
        if not isinstance(sub_id, str) or not sub_id:
            return self._send(handler, 400, {"error": "id 必须是非空字符串"})
        if not self.storage.remove_subscriber(sub_id):
            return self._send(handler, 404, {"error": "unknown subscriber id"})
        logger.info("订阅注销: id=%s", sub_id)
        self._send(handler, 200, {"ok": True})

    # ---- 工具 ----

    def _autostart(self, handler: "_Handler") -> None:
        """自启开关 (S6): 幂等注册/卸载开机自启 (供 auto-qb 设置页开关消费).

        action: install -> register(); uninstall -> unregister()。data_dir 取本进程
        的 storage.data_dir (与 run 一致) —— **不信任请求体**: 注册项里写死的就是它,
        外部传别的目录只会让注册项与真实运行目录不一致。

        在工具进程内跑 installer, sys.executable 即装了 gtm 的 venv python (自启项
        要指向的解释器), 无需调用方知道该路径。

        S14/D13 回写: 成功后把工具 config `autostart` 置为 (install=True / uninstall=False)
        并原子落盘 + 热换 ConfigHolder —— 该键是自启的**唯一裁决权**: 用户经这里关过之后,
        即便再被拉起 (run --autostart) 也判 false 而 no-op, 不被自动装回。写成失败态
        (false) 与写成成功态同样重要, 故 install 与 uninstall 都回写 (幂等 no-op 也回写,
        因为开关结果仍是「已关」)。config 落盘/热换失败由外层 handler 兜成 500, 调用方
        据退出码判成败 (注册本身已成功, 但裁决权没落定 = 开关状态不可信)。

        错误映射 (供设置页开关判成败): 载荷非法 400 / 平台不支持 501 / 平台命令失败
        或前置条件缺失 500; 幂等 no-op 也是 200 (结果 action 区分 registered/skipped/
        unregistered/absent)。
        """
        body, err = self._read_json(handler)
        if err is not None:
            return self._send(handler, 400, {"error": err})
        assert body is not None
        if not isinstance(body, dict):
            return self._send(handler, 400, {"error": "自启载荷必须是 JSON 对象"})
        action = str(body.get("action") or "").strip()
        if action not in ("install", "uninstall"):
            return self._send(handler, 400, {"error": "action 必须是 install 或 uninstall"})
        try:
            backend = self._installer_factory(self.storage.data_dir)
            result = backend.register() if action == "install" else backend.unregister()
        except UnsupportedPlatformError as e:
            return self._send(handler, 501, {"error": str(e)})
        except AutostartError as e:
            return self._send(handler, 500, {"error": str(e)})
        # 读-改-写整段持 _config_write_lock: 快照读取若在锁外, 与并发 PUT /config
        # 交叠时旧快照整份回写会丢更新 (issue 26-10-30-0624 T-01)
        with self._config_write_lock:
            new_config = replace(self.config_holder.current, autostart=(action == "install"))
            save_config(self.config_path, new_config)
            self.config_holder.replace(new_config)
        logger.info("自启 %s: %s (config autostart=%s)", action, result.message, new_config.autostart)
        self._send(handler, 200, {"ok": True, "action": result.action, "message": result.message})

    def _shutdown(self, handler: "_Handler") -> None:
        """优雅退出 (26-10-17-1737 S3): 先回 200, 再置位 stop_event.

        顺序是契约: 响应先上 wire (wfile 直写 socket, 无缓冲), 调用方 (auto-qb 代理端点)
        拿到 200 时进程可能已在退出路上 —— 退出走 cmd_run 的既有 finally (最终落盘 +
        释放单实例锁 + 停控制面 + 删发现指针), 与本端点无关, 这里只发信号。
        请求体不读 (空 POST 即可); 鉴权闸在 handle() 前置, 无 token 到不了这里。
        """
        self._send(handler, 200, {"ok": True, "message": "正在停止 global-traffic-monitor"})
        if self._stop_event is None:
            # 非 run 装配 (单测/复用): 没有主循环可停 —— 不静默, 记一条便于排障
            logger.warning("POST /shutdown: 未绑定 stop_event, 仅返回 200 未触发退出")
            return
        logger.info("收到停止请求 (POST /shutdown), 优雅退出")
        self._stop_event.set()

    def _read_json(self, handler: "_Handler") -> tuple[Optional[Any], Optional[str]]:
        """读请求体并解析 JSON (上限 _MAX_BODY_BYTES; 坏 JSON -> (None, 错误))."""
        try:
            length = int(handler.headers.get("Content-Length") or 0)
        except ValueError:
            return None, "Content-Length 非法"
        if length <= 0:
            return None, "请求体为空"
        if length > _MAX_BODY_BYTES:
            return None, f"请求体过大 (>{_MAX_BODY_BYTES} 字节)"
        raw = handler.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, f"JSON 解析失败: {e}"

    def _send(self, handler: "_Handler", code: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


class _Handler(BaseHTTPRequestHandler):
    """请求 handler: 全部分发回 ControlServer.handle; 日志走 gtm logger.

    server 上的 control_server 属性由 ControlServer.start() 绑定 (实例级).
    """

    server: Any  # start() 绑定 control_server 属性的 ThreadingHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - stdlib 命名
        self._dispatch()

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        try:
            self.server.control_server.handle(self)
        except Exception:
            logger.exception("控制面请求处理异常: %s %s", self.command, self.path)
            try:
                self.server.control_server._send(self, 500, {"error": "internal error"})
            except Exception:
                pass

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib 签名
        logger.debug("HTTP %s - %s", self.address_string(), format % args)

"""本地 TCP 代理 —— 产品进程与测试 qB 实例(36596)之间的转发+记录件(RM02 引入)。

只服务 RM02(节拍观测 / 断连注入), 别长成通用 HTTP 解析器。三个设计点:

1. **只做字节转发 + 最小请求切分**: 客户端方向按 HTTP 请求边界切开是为了记
   「请求时间戳 + 路径」(节拍观测的外部可观测面), 服务端方向盲拷 —— 不解析响应。
2. **cut()/restore() 是断连注入口**(RM02-07): cut 后新连接照常 accept 但**立即关闭**
   (记录 probe 事件), 存活连接全部掐断 —— 产品看到的不是"连不上"(listener 还在),
   而是"一连上就被掐", 与 qB 宕机同效且不碰 qB 进程; 掐断期间的重连尝试
   (connect())会以 probe 事件留痕, 退避节奏由此外部可观测。
3. **端口纪律与 lib/app.py 同口径**: listen 端口由调用方用 app.free_port() 取
   (39000-39999 段, 会话内不复用, 裸 bind 探空), 本模块不做探空。
"""
from __future__ import annotations

import re
import socket
import threading
import time

# qB WebUI 校验 Host 头(实测 2026-10-31: Host 端口与自身监听端口不一致 -> 401 Unauthorized,
# 连 /auth/login 都拒) —— 转发前把 Host 头统一改写成目标实例的 host:port
_HOST_RE = re.compile(rb"(?i)(Host:)[^\r\n]*")


class TcpProxy:
    """单线程 accept + 每连接双线程 relay 的本机代理。收尾必须 stop()。"""

    def __init__(self, target_port: int, port: int, host: str = "127.0.0.1"):
        self.host = host
        self.port = port
        self.target = ("127.0.0.1", target_port)
        self._events: list[dict] = []          # {"ts", "kind": req|probe, "path"?}
        self._ev_lock = threading.Lock()
        self._conns: list[tuple[socket.socket, socket.socket]] = []
        self._conn_lock = threading.Lock()
        self._listener: socket.socket | None = None
        self._cut = False
        self._running = False

    # ---------- 生命周期 ----------

    def start(self) -> None:
        if self._running:
            return
        srv = socket.socket()
        srv.bind((self.host, self.port))
        srv.listen(16)
        self._listener = srv
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        self._cut = False
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
        self._close_all()
        # 给 relay 线程一拍收尾, 防止端口/句柄拖到下一条用例
        time.sleep(0.1)

    def cut(self) -> None:
        """断连注入: 掐掉全部存活连接; 之后的新连接 accept 即关(记 probe)。"""
        self._cut = True
        self._close_all()

    def restore(self) -> None:
        self._cut = False

    def _close_all(self) -> None:
        with self._conn_lock:
            pairs = list(self._conns)
            self._conns.clear()
        for c, s in pairs:
            for sock in (c, s):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass

    # ---------- 转发 ----------

    def _accept_loop(self) -> None:
        while self._running:
            try:
                c, _addr = self._listener.accept()
            except OSError:
                return
            if self._cut or not self._running:
                with self._ev_lock:
                    self._events.append({"ts": time.time(), "kind": "probe"})
                try:
                    c.close()
                except OSError:
                    pass
                continue
            threading.Thread(target=self._handle, args=(c,), daemon=True).start()

    def _handle(self, c: socket.socket) -> None:
        s = socket.socket()
        try:
            s.connect(self.target)
        except OSError:
            try:
                c.close()
            except OSError:
                pass
            return
        pair = (c, s)
        with self._conn_lock:
            if not self._running or self._cut:
                for sock in pair:
                    try:
                        sock.close()
                    except OSError:
                        pass
                return
            self._conns.append(pair)
        threading.Thread(target=self._relay, args=(s, c), daemon=True).start()
        try:
            self._pipe_requests(c, s)
        except OSError:
            pass  # 对端被 _drop 关掉(响应先结束/cut/stop)是常态, 别把线程栈刷进 stderr
        finally:
            self._drop(pair)

    def _pipe_requests(self, c: socket.socket, s: socket.socket) -> None:
        """客户端方向: 切请求边界 -> 记事件 -> 原样转发(keep-alive 循环)"""
        buf = b""
        while self._running and not self._cut:
            while b"\r\n\r\n" not in buf:
                chunk = c.recv(65536)
                if not chunk:
                    return
                buf += chunk
            head, rest = buf.split(b"\r\n\r\n", 1)
            lines = head.split(b"\r\n")
            first = lines[0].decode("latin1", "replace").split(" ")
            path = first[1] if len(first) >= 2 else ""
            clen = 0
            for ln in lines[1:]:
                k, _, v = ln.partition(b":")
                if k.strip().lower() == b"content-length":
                    try:
                        clen = int(v.strip())
                    except ValueError:
                        clen = 0
            while len(rest) < clen:
                chunk = c.recv(65536)
                if not chunk:
                    return
                rest += chunk
            with self._ev_lock:
                self._events.append({"ts": time.time(), "kind": "req", "path": path})
            host_new = f"{self.target[0]}:{self.target[1]}".encode()
            head, n = _HOST_RE.subn(rb"\1 " + host_new, head, count=1)
            if n == 0:  # 无 Host 头(HTTP/1.0)则补一个
                head = head + b"\r\nHost: " + host_new
            s.sendall(head + b"\r\n\r\n" + rest[:clen])
            buf = rest[clen:]

    def _relay(self, src: socket.socket, dst: socket.socket) -> None:
        """服务端方向盲拷; EOF/错误即整对关闭(客户端方向线程随之退出)"""
        try:
            while True:
                chunk = src.recv(65536)
                if not chunk:
                    return
                dst.sendall(chunk)
        except OSError:
            pass
        finally:
            self._drop((dst, src))

    def _drop(self, pair: tuple[socket.socket, socket.socket]) -> None:
        with self._conn_lock:
            if pair in self._conns:
                self._conns.remove(pair)
        for sock in pair:
            try:
                sock.close()
            except OSError:
                pass

    # ---------- 观测面 ----------

    def events(self) -> list[dict]:
        with self._ev_lock:
            return list(self._events)

    def requests(self) -> list[tuple[float, str]]:
        return [(e["ts"], e.get("path", "")) for e in self.events() if e["kind"] == "req"]

    def sync_times(self) -> list[float]:
        """sync/maindata 请求时间戳序列(同步线节拍观测用)"""
        return [ts for ts, path in self.requests() if "/api/v2/sync/maindata" in path]

    def probes(self) -> list[float]:
        """被掐断期间的重连尝试时刻(accept 即关的连接)"""
        return [e["ts"] for e in self.events() if e["kind"] == "probe"]

    def wait_requests(self, n: int, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if len(self.requests()) >= n:
                return True
            time.sleep(0.2)
        return False

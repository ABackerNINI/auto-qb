"""伪 tracker —— 让构造种子在「做种中但零流量」状态下被 qB 正常对待。

默认返回**零 peer**: qB announce 成功后无对端可连 ⇒ 状态 stalledUP、速率恒 0。
L2 需要真流量时把 `peers` 设成对端实例的 (ip, listen_port) 即可 —— 两端都只打这个本地 tracker,
所以流量不出网卡, 也不需要任何真实站点。

每次 announce 都记进 `announces`, 用例用它断言「qB 真的来报到了」(否则 stalledUP 可能只是没 announce)。
"""
from __future__ import annotations

import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import bencode
from .net import local_host


class _Handler(BaseHTTPRequestHandler):
    tracker: "FakeTracker" = None  # type: ignore[assignment]

    def log_message(self, fmt, *args):  # 静音: 默认会往 stderr 刷每一条请求
        pass

    def do_GET(self):
        if not self.path.startswith("/announce"):
            self.send_error(404)
            return
        raw_query = self.path.split("?", 1)[1].encode("latin-1") if "?" in self.path else b""
        rec = {"ts": time.time(), "ip": self.client_address[0]}
        for chunk in raw_query.split(b"&"):
            if not chunk:
                continue
            key, _, val = chunk.partition(b"=")
            key = urllib.parse.unquote_to_bytes(key.replace(b"+", b" ")).decode("latin-1")
            if key == "info_hash":
                rec["info_hash"] = urllib.parse.unquote_to_bytes(val.replace(b"+", b" ")).hex()
            elif key in ("port", "event", "uploaded", "downloaded", "left"):
                rec[key] = urllib.parse.unquote_to_bytes(val).decode("latin-1")
        self.tracker.announces.append(rec)
        try:
            own_port = int(rec.get("port", 0))
        except ValueError:
            own_port = None
        body = bencode.encode({"interval": self.tracker.interval,
                               "peers": self.tracker.peers_payload(exclude_port=own_port)})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FakeTracker:
    def __init__(self, interval: int = 5, peers: list[tuple[str, int]] | None = None, bind: str = "0.0.0.0"):
        self.interval = interval
        self.peers: list[tuple[str, int]] = list(peers or [])
        self.announces: list[dict] = []
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.port = 0
        self.bind = bind

    def peers_payload(self, exclude_port: int | None = None):
        """返回 peer 列表; **排除请求者自己**(真实 tracker 就是这么做的)。

        两个实例在同一台机器上 ⇒ 同一个 IP, 只有 listen_port 不同。若不排除自己,
        种子会拿到「自己的地址」并尝试连自己, 而 qB 默认 enable_multi_connections_from_same_ip=false
        (libtorrent allow_multiple_connections_per_ip=false), 同一 IP 只允许一条连接,
        于是真正的 leech 连进来时会被挤掉 —— 现场就是 conn=1 → 0 且零字节(plan §02 D5)。
        """
        peers = [(ip, port) for ip, port in self.peers if port != exclude_port]
        if not peers:
            return b""  # 零 peer 用紧凑格式的空串; 有 peer 用字典列表(可读性优先, qB 两种都收)
        return [{"ip": ip, "port": port} for ip, port in peers]

    @property
    def url(self) -> str:
        return f"http://{local_host()}:{self.port}/announce"

    def start(self) -> "FakeTracker":
        handler = type("_BoundHandler", (_Handler,), {"tracker": self})
        self._httpd = ThreadingHTTPServer((self.bind, 0), handler)
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def count(self, infohash: str | None = None) -> int:
        if infohash is None:
            return len(self.announces)
        return sum(1 for a in self.announces if a.get("info_hash") == infohash)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

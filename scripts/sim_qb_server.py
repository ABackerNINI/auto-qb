"""sim_qb HTTP 外壳: Handler / SimServer / 工作根校验(从 sim_qb.py 原样搬迁)"""
from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from sim_qb_core import *  # noqa: F401,F403

# ---------- HTTP ----------


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SimQb/1.0"

    def log_message(self, *a):
        pass

    # 参数合并: POST 的 rid/hashes 等常在 body(form), GET 在 query —— 只解析 query 会恒得 rid=0
    def _params(self) -> dict:
        raw = self.path or ""
        if self.command in ("POST", "PUT"):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                try:
                    body = self.rfile.read(n).decode("utf-8", "replace")
                except Exception:
                    body = ""
                raw = raw + ("&" if "?" in raw else "?") + body
        query = urlparse(raw).query
        if not query and "?" in raw:
            query = raw.split("?", 1)[-1]
        return {k: v[0] for k, v in parse_qs(query).items()}

    def _route(self) -> str:
        p = urlparse(self.path).path
        return p.strip("/").replace("api/v2/", "")

    def _json(self, obj, status=200):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _text(self, s: str, status=200):
        b = s.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _trace(self, route, params, status, size):
        sim = self.server.sim
        sim.stats["requests"] += 1
        sim.stats["endpoint_hits"][route] = sim.stats["endpoint_hits"].get(route, 0) + 1
        try:
            with open(os.path.join(sim.run_dir, "trace.jsonl"), "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "m": self.command,
                            "e": route,
                            "p": {
                                k: (v[:120] if isinstance(v, str) else v)
                                for k, v in params.items()
                            },
                            "s": status,
                            "b": size,
                        },
                        ensure_ascii=False
                    ) + "\n"
                )
        except OSError:
            pass

    def do_HEAD(self):
        if self.server.sim._abort:
            self.close_connection = True
            return
        self._text("")

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def _dispatch(self):
        sim = self.server.sim
        if sim._abort:
            self.close_connection = True
            return
        # 人为延迟(默认 0): 让假 qB 表现得像**真机上有负载的 qB**。
        # 没有它, 本地每个请求 ~0.5ms => `_build_search_index` 一轮 500 次文件 API 只要 250ms,
        # 主循环永远不饱和 => "命令排队 wait_ms" 恒为 0 => 真机上"点了要等 2-4s"这类缺陷
        # **在本地永远复现不出来**(与「桩服务是瞬时的 => 顺序型缺陷测不出」同一类, 但在后端)。
        if sim.latency_ms:
            time.sleep(sim.latency_ms / 1000.0)
        route = self._route()
        params = self._params()

        if route == "auth/login":
            self._trace(route, {}, 200, 3)
            return self._text("Ok.")
        if route in ("app/webapiVersion", "app/version", "app/preferences"):
            v = {"app/webapiVersion": "2.11", "app/version": "v5.2.3", "app/preferences": {}}[route]
            self._trace(route, params, 200, len(str(v)))
            return self._text(v) if isinstance(v, str) else self._json(v)

        if route in WRITE_ENDPOINTS:
            if sim.args.read_only:
                sim.apply_write(route, params)  # 记账但不改变状态
                self._trace(route, params, 403, 0)
                return self._json({"error": "read-only sim"}, status=403)
            try:
                sim.apply_write(route, params)
            except BoundaryViolation as e:
                self._trace(route, params, 403, 0)
                return self._json({"error": str(e)}, status=403)
            self._trace(route, params, 200, 2)
            return self._text("Ok.")

        # 读端点
        if route == "sync/maindata":
            # 录播档: 按 --latency-mode 注入延迟(recorded = 用录到的真实 rtt), 替代 --latency-ms 常数近似
            if sim.corpus_mode:
                sim.sleep_replay_latency()
            out = sim.sync_maindata(int(params.get("rid") or 0))
            b = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            self._trace(route, {"rid": params.get("rid")}, 200, len(b))
            return
        if route == "torrents/info":
            self._trace(route, params, 200, 0)
            # 语料档: 走**实况状态**(流状态 + 已到期 overlay)。它与 sync/maindata 的差异正是
            # issue 26-09-20-2145 要复现的"真值尚未落地"。合成档沿用原样(无 overlay)。
            if sim.corpus_mode:
                return self._json([sim._live(h) for h in sim.torrents])
            return self._json([sim._public(t) for t in sim.torrents.values()])
        if route == "torrents/files":
            t = sim.torrents.get(params.get("hash"))
            if sim.corpus_mode:
                # 语料档: 用**录下来的** files —— 归组 key 与缺文件扫描的唯一来源, 不再现场合成
                out = [dict(f) for f in (t.get("_files_raw") or [])] if t else []
                self._trace(route, params, 200, 0)
                return self._json(out)
            out = (
                [
                    {
                        "index": i,
                        "name": r,
                        "size": t["_file_size"],
                        "progress": 1.0,
                        "priority": 0,
                        "is_seed": True,
                    } for i, r in enumerate(t["_rel_files"])
                ] if t else []
            )
            self._trace(route, params, 200, 0)
            return self._json(out)
        if route == "torrents/trackers":
            t = sim.torrents.get(params.get("hash"))
            if sim.corpus_mode:
                out = [dict(x) for x in (t.get("_trackers_raw") or [])] if t else []
                self._trace(route, params, 200, 0)
                return self._json(out)
            out = (
                [
                    {
                        "url": t["tracker"],
                        "status": 2,
                        "tier": 0,
                        "num_peers": 0,
                        "num_seeds": 0,
                        "num_leeches": 0,
                        "num_downloaded": 0,
                        "msg": "",
                    }
                ] if t else []
            )
            self._trace(route, params, 200, 0)
            return self._json(out)
        # ---- 计划 §09 补齐的三个路由: 语料档必须实现, 否则 auto-qb 走到的路径会 404 ----
        if route == "sync/torrentPeers":
            h = params.get("hash")
            peers = (sim.corpus.peers.get(h, []) if (sim.corpus_mode and sim.corpus) else [])
            self._trace(route, params, 200, 0)
            return self._json({"rid": 0, "peers": {str(i): p for i, p in enumerate(peers)}, "peers_removed": {}})
        if route == "torrents/pieceHashes":
            # ! 严格模式(rules/actions/checking.py:145-154)把候选与目标的 piece hash **逐项比对**;
            # 按内容集合(排序后的 相对路径+大小)确定性派生, 同组成员天然共享同一列表, 与真机语义一致。
            # 若按 hash 各自随机, 同组成员互不相等 => 严格模式判据恒假(比不测更糟)。
            t = sim.torrents.get(params.get("hash"))
            if t is None:
                self._trace(route, params, 200, 0)
                return self._json([])
            pairs = [(str(f.get("name", "")), int(f.get("size") or 0)) for f in (t.get("_files_raw") or [])]
            if not pairs:
                pairs = [(r, int(t.get("_file_size") or 0)) for r in (t.get("_rel_files") or [])]
            out = piece_hashes_of(pairs)
            self._trace(route, params, 200, 0)
            return self._json(out)
        if route == "torrents/export":
            t = sim.torrents.get(params.get("hash"))
            if t is None:
                self._trace(route, params, 404, 0)
                return self._json({"error": "torrent not found"}, status=404)
            blob = minimal_bencode(str(t.get("name", "x")), int(t.get("size") or 0))
            self.send_response(200)
            self.send_header("Content-Type", "application/x-bittorrent")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
            self._trace(route, params, 200, len(blob))
            return
        if route == "_fsmock/state":
            # FS mock 的时间源(计划 §07 硬条件3.): 由播放器给出"当前磁盘状态", mock 按秒拉取
            payload = sim.fsmock_state()
            self._trace(route, params, 200, 0)
            return self._json(payload)
        if route == "torrents/tags":
            self._trace(route, params, 200, 0)
            return self._json(sorted(sim.tags))
        if route == "torrents/categories":
            self._trace(route, params, 200, 0)
            return self._json({c: {"name": c, "savePath": ""} for c in sorted(sim.categories)})
        if route in ("transfer/info", "transfer/uploadLimit", "transfer/downloadLimit"):
            v = {"transfer/info": sim.server_state(), "transfer/uploadLimit": 0, "transfer/downloadLimit": 0}[route]
            self._trace(route, params, 200, 0)
            return self._json(v)

        self._trace(route, params, 404, 0)
        return self._json({"error": f"unknown endpoint: {route}"}, status=404)


class SimServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, sim):
        self.sim = sim
        super().__init__(addr, Handler)

    def handle_error(self, request, client_address):
        """auto-qb 被终止时连接会被重置 —— 这是预期收尾, 不打栈回溯(否则淹没统计层)"""
        import socket
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, socket.timeout)):
            return
        super().handle_error(request, client_address)


# ---------- B1: 工作根校验 ----------


def prepare_root(root: str) -> tuple[str, str | None]:
    """校验/准备工作根; 返回 (实际 root, fallback 原因或 None)

    B1: 不得是盘根目录; 必须是新建空目录, 或含哨兵 .auto-qb-sim-root 的既有目录。
    """
    drive = os.path.splitdrive(os.path.abspath(root))[0]
    if not drive or os.path.abspath(root) == drive + os.sep:
        raise BoundaryViolation(f"B1: --root 不得是盘根目录: {root}")
    if os.path.exists(root):
        if not os.path.isdir(root):
            raise BoundaryViolation(f"B1: --root 不是目录: {root}")
        if os.listdir(root) and not os.path.exists(os.path.join(root, SENTINEL)):
            raise BoundaryViolation(f"B1: --root 已存在且非空, 但缺哨兵 {SENTINEL} —— 拒绝在非仿真目录上跑删除场景: {root}")
    else:
        try:
            os.makedirs(root, exist_ok=True)
        except OSError as e:
            return None, f"root 不可创建({e}), 回退临时目录"
        with open(os.path.join(root, SENTINEL), "w", encoding="utf-8") as f:
            f.write("auto-qb sim root\n")
    return root, None


def fallback_root() -> str:
    import tempfile
    d = os.path.join(tempfile.gettempdir(), "auto-qb-sim")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, SENTINEL), "w", encoding="utf-8") as f:
        f.write("auto-qb sim root (fallback)\n")
    return d

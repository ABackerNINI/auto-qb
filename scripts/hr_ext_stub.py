#!/usr/bin/env python
"""HR 扩展选项页验收桩服务(dev-only): 模拟 hr-fetch-proxy 后端(发现端点 + 双数据端点)。

用途: 计划 26-10-16-0214 §06 真机验收(V1 实例表状态列 / V2 重测全部 / V7 图标四态外框)——
在 Chrome 里加载已解压扩展后, 选项页「① 连接后端」对着这套可控的后端:
默认两个实例(一个正常 = 绿 / 一个 401 = 红), POST /control 实时翻转 ok/401/down,
停用效果立刻在实例表状态列与工具栏图标上看到。桩**不连任何真实站点**:
GET /api/hr/tasks 恒回空任务清单(无任务 = 取数通道的正常稳态), /api/hr/refresh 恒回受理。

协议形态与真后端同源(路径/鉴权头/字段名见守阵 test_protocol_matches_backend):
- 发现端点 127.0.0.1:18788(与扩展默认发现地址一致, 同机零配置):
  GET  /api/hr/discover      -> {"instances": [{id, name, endpoint, token}], "server_time"}
- 数据端点(两个 OS 随机空闲端口, 发现应答里带回):
  GET  /api/hr/tasks         -> 200 {"tasks": [], "next_poll_s": 60} / 401 {"error": ...} / down=断连
  POST /api/hr/refresh       -> 200 {"requested": []}
  POST /api/hr/result        -> 200 {"ok": true}
  GET  /api/hr/sites         -> 200 {"sites": [{"site", "origin"}]}
- 控制面(只在发现端口):
  GET  /control              -> 当前实例与模式
  POST /control {"port": N, "mode": "ok"|"401"|"down"} -> 实时翻转(验收 V1 用)

用法:
    uv run python scripts/hr_ext_stub.py
    curl http://127.0.0.1:18788/control
    curl -X POST http://127.0.0.1:18788/control -H "Content-Type: application/json" ^
         -d "{\"port\": <数据端口>, \"mode\": \"down\"}"     # Git Bash 里引号转义同 bash
停止: Ctrl+C。端口被占会一行报错并退出(可用 scripts/port_kill.py -- 18788 清理)。
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

#: 桩实例的固定 token(发现应答带回, 数据端点据此鉴权; 401 演示走模式翻转而非 token 不符)
TOKEN_A = "stub-token-ok"
TOKEN_B = "stub-token-bad"
MODES = ("ok", "401", "down")
#: 两个数据端点的初始模式: A=正常(绿) / B=401(token 或来源被拒, 红)
_INITIAL_MODES = {TOKEN_A: "ok", TOKEN_B: "401"}

_state_lock = threading.Lock()
_state = {"modes": dict(_INITIAL_MODES), "ports": {}}  # ports: token -> 数据端口


def _log(msg: str) -> None:
    print(f"[stub] {msg}", flush=True)


class _Handler(BaseHTTPRequestHandler):
    server_version = "HrExtStub/1.0"

    def log_message(self, fmt, *args):  # noqa: A003 - 基类签名; 走自己的 _log
        pass

    # ---------- 应答工具 ----------

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _drop(self) -> None:
        """down 模式: 不应答直接断连 —— 浏览器 fetch 拿到 TypeError: Failed to fetch(与「端点没在监听」同形)"""
        self.close_connection = True

    # ---------- 路由 ----------

    def do_GET(self):  # noqa: N802 - 基类签名
        port = self.server.server_port
        if port == _state["discovery_port"]:
            if self.path == "/api/hr/discover":
                return self._discover()
            if self.path == "/control":
                return self._control_get()
            return self._json(404, {"error": "not found"})
        return self._data_route("GET")

    def do_POST(self):  # noqa: N802 - 基类签名
        port = self.server.server_port
        if port == _state["discovery_port"] and self.path == "/control":
            return self._control_post()
        if port == _state["discovery_port"]:
            return self._json(404, {"error": "not found"})
        return self._data_route("POST")

    # ---------- 发现端点 ----------

    def _discover(self) -> None:
        instances = [
            {
                "id": "stub-a",
                "name": "桩A(正常)",
                "endpoint": f"http://127.0.0.1:{_state['ports'][TOKEN_A]}",
                "token": TOKEN_A
            },
            {
                "id": "stub-b",
                "name": "桩B(401红)",
                "endpoint": f"http://127.0.0.1:{_state['ports'][TOKEN_B]}",
                "token": TOKEN_B
            },
        ]
        _log(f"发现应答 -> {len(instances)} 个实例")
        self._json(200, {"instances": instances, "server_time": round(time.time(), 3)})

    def _control_get(self) -> None:
        with _state_lock:
            insts = [
                {
                    "name": "桩A(正常)",
                    "port": _state["ports"][TOKEN_A],
                    "mode": _state["modes"][TOKEN_A],
                    "token": TOKEN_A
                },
                {
                    "name": "桩B(401红)",
                    "port": _state["ports"][TOKEN_B],
                    "mode": _state["modes"][TOKEN_B],
                    "token": TOKEN_B
                },
            ]
        self._json(200, {"discovery_port": _state["discovery_port"], "instances": insts})

    def _control_post(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:  # noqa: BLE001 - 控制面随手用, 坏输入一行回绝
            return self._json(400, {"ok": False, "error": f"bad json: {e}"})
        port = payload.get("port")
        mode = str(payload.get("mode") or "")
        with _state_lock:
            token = next((t for t, p in _state["ports"].items() if p == port), None)
            if token is None:
                return self._json(404, {"ok": False, "error": f"没有端口 {port} 的实例"})
            if mode not in MODES:
                return self._json(400, {"ok": False, "error": f"mode 须为 {MODES}"})
            _state["modes"][token] = mode
            _log(f"控制面: 端口 {port} 模式 -> {mode}")
        return self._control_get()

    # ---------- 数据端点 ----------

    def _data_route(self, method: str) -> None:
        port = self.server.server_port
        with _state_lock:
            token = next((t for t, p in _state["ports"].items() if p == port), None)
            mode = _state["modes"].get(token, "ok") if token else "ok"
        if self.path == "/api/hr/tasks" and method == "GET":
            given = str(self.headers.get("X-Hr-Token") or "")
            if mode == "down":
                _log(f"数据端口 {port}: tasks(down) -> 断连")
                return self._drop()
            if mode == "401" or given != token:
                _log(f"数据端口 {port}: tasks -> 401(mode={mode}, token {'对' if given == token else '不对'})")
                return self._json(401, {"error": "unauthorized"})
            _log(f"数据端口 {port}: tasks -> 200 无任务")
            return self._json(200, {"tasks": [], "next_poll_s": 60})
        if self.path == "/api/hr/refresh" and method == "POST":
            self._drain_body()
            _log(f"数据端口 {port}: refresh -> 受理")
            return self._json(200, {"requested": []})
        if self.path == "/api/hr/result" and method == "POST":
            self._drain_body()
            _log(f"数据端口 {port}: result -> 受理")
            return self._json(200, {"ok": True})
        if self.path == "/api/hr/sites" and method == "GET":
            _log(f"数据端口 {port}: sites -> 1 个站点")
            return self._json(200, {"sites": [{"site": "pt.btschool.club", "origin": "https://pt.btschool.club"}]})
        return self._json(404, {"error": "not found"})

    def _drain_body(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
        except Exception:  # noqa: BLE001 - 桩不因坏请求体崩
            pass


def _serve(server: ThreadingHTTPServer) -> None:
    try:
        server.serve_forever()
    except Exception:  # noqa: BLE001 - 关闭路径统一走 shutdown
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="HR 扩展选项页验收桩服务(dev-only)")
    ap.add_argument("--discovery-port", type=int, default=18788, help="发现端点端口(默认 18788, 与扩展默认发现地址一致)")
    args = ap.parse_args()

    servers = []
    try:
        disc = ThreadingHTTPServer(("127.0.0.1", args.discovery_port), _Handler)
    except OSError as e:
        print(
            f"[stub] 发现端口 {args.discovery_port} 绑不上({e}) —— 先 scripts/port_kill.py -- {args.discovery_port} 清理占用",
            file=sys.stderr
        )
        return 1
    _state["discovery_port"] = args.discovery_port
    servers.append(disc)

    ports = []
    for token in (TOKEN_A, TOKEN_B):
        data = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)  # OS 随机空闲端口
        _state["ports"][token] = data.server_port
        ports.append(data.server_port)
        servers.append(data)

    threads = [threading.Thread(target=_serve, args=(s, ), daemon=True) for s in servers]
    for t in threads:
        t.start()

    print("=" * 72)
    print(f"[stub] 发现端点: http://127.0.0.1:{args.discovery_port}  (扩展「发现地址」默认即此, 点「立即发现」)")
    print(f"[stub] 实例 A(正常/绿): http://127.0.0.1:{ports[0]}  token={TOKEN_A}  mode=ok")
    print(f"[stub] 实例 B(401/红):  http://127.0.0.1:{ports[1]}  token={TOKEN_B}  mode=401")
    print("[stub] 控制面: GET  http://127.0.0.1:%d/control 看状态" % args.discovery_port)
    print('[stub]         POST /control {"port": %d, "mode": "ok|401|down"} 实时翻转(演示 V1)' % ports[0])
    print("[stub] 验收路径: chrome://extensions 加载本仓 extensions/hr-fetch-proxy -> 选项页「① 连接后端」")
    print("[stub] V1 停用演示: 把某实例切 down/401 -> 点「重测全部」或等 1 分钟轮询, 实例表状态列变橙/红")
    print("[stub] V7 图标演示: 连接正常=绿框; 发现地址改到 127.0.0.1:19999 再发现 -> 红框 + 角标 !")
    print("=" * 72, flush=True)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        for s in servers:
            s.shutdown()
        for s in servers:
            s.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

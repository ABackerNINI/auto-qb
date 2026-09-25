"""test_hr_server 测试计划: 本地取数端点(127.0.0.1 监听 + token 鉴权 + origin/URL 边界)

分两层测:
① `route()` 纯逻辑层 —— 鉴权与白名单全部在这里, 直接调不碰 socket, 判据最稳;
② 真 HTTP 层 —— 起真监听用 urllib 打一轮(含 401/403 与端口冲突 fail-fast),
   确认薄适配层(头解析 / Content-Length / 状态码)真的通。

## 测试计划(每个测试函数一条)
- test_route_rejects_missing_token: 无 token -> 401, 且不记接触、不派任务、不写任何状态
- test_route_rejects_wrong_token: token 不符 -> 401(常数时间比较)
- test_route_rejects_web_origin: 普通网页 origin -> 403 且不给 CORS 头(纵深防御)
- test_route_tasks_returns_batch_with_token: 带 token GET 拿到任务清单 + CORS 回显 origin
- test_route_sites_lists_configured_sites: 带 token GET /api/hr/sites 拿到站点授权清单(空 origin 条目丢弃)
- test_route_sites_same_gates_as_tasks: 站点清单与任务清单同一道门(无 token 401 / 网页 origin 403 / 不算接触)
- test_route_sites_survives_sites_fn_error: sites_fn 抛异常 -> 200 + 空清单 + error(不打死端点线程)
- test_route_sites_empty_when_no_sites_fn: 未接 sites_fn 时空清单不报错(向后兼容)
- test_route_result_accepted_and_wakes_waiter: 带 token POST 结果 -> 唤醒等待方
- test_route_result_unknown_task_is_400: 未派发过的任务 -> 400 且不入任何状态(防伪造注入)
- test_route_result_malformed_is_400: 畸形 JSON / 畸形结果 -> 400 不崩
- test_route_result_oversize_is_413: 超限请求体 -> 413
- test_route_options_preflight: OPTIONS 预检返回允许的方法与头
- test_route_unknown_path_is_404: 未登记路径 404
- test_token_never_echoed: 响应体里绝不出现 token
- test_contact_recorded_only_after_auth: 只有鉴权通过的请求才算「通道接触」(静默判据)
- test_http_roundtrip_over_loopback: 真 HTTP: 拉清单 -> 回传 -> 后端拿到内容
- test_http_requires_token: 真 HTTP 无 token -> HTTPError 401
- test_port_conflict_fails_fast: 同端口第二个端点启动即抛 HrChannelBindError(不静默降级)
- test_stop_releases_port: 停止后同一端口能再次启动(重启不残留)
- test_status_reports_bound_port_and_contacts: 自检快照(实际绑定端口/接触时间/扩展 origin)
- test_http_connection_header_closes: 每请求关闭连接(不在监听套接字上留半开连接)
- test_handler_survives_broken_connection: 客户端半路断开不打死端点线程, 后续请求照常
- test_threads_do_not_leak_on_stop: 停止后端点线程真的退出(不残留)
"""
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection

import pytest

from auto_qb.hr.channel import API_RESULT, API_SITES, API_TASKS, TOKEN_HEADER, HrChannelBindError
from auto_qb.hr.queue import HrTaskQueue
from auto_qb.hr.server import HrChannelServer

TOKEN = "t" * 64
ORIGIN = "chrome-extension://" + "a" * 32
URL = "https://pt.example.com/myhr.php?hrtype=A"
DL = "https://pt.example.com/download.php?id=313852"


def make_server(*, queue=None, token=TOKEN, extension_id="", now_fn=time.time, sites_fn=None):
    return HrChannelServer(
        queue=queue or HrTaskQueue(),
        token=token,
        port=0,
        extension_id=extension_id,
        now_fn=now_fn,
        sites_fn=sites_fn,
    )


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ---------- ① 纯逻辑路由 ----------


def test_route_rejects_missing_token():
    server = make_server()
    server.queue.put("pt.example.com", "page", URL)
    status, headers, body = server.route("GET", API_TASKS, {}, b"")
    assert status == 401
    assert "Access-Control-Allow-Origin" not in headers
    assert b"unauthorized" in body
    assert server.last_contact_ts == 0.0, "401 不算通道接触(否则静默告警会被刷没)"
    assert server.queue.pending() == 1, "未鉴权的请求不得动队列"


def test_route_rejects_wrong_token():
    server = make_server()
    status, _headers, _body = server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
    assert status == 401


def test_route_rejects_web_origin():
    server = make_server()
    status, headers, _body = server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": "https://evil.example.com"})
    assert status == 403, "任意网页 JS 不得碰端点"
    assert "Access-Control-Allow-Origin" not in headers
    assert server.last_contact_ts == 0.0


def test_route_tasks_returns_batch_with_token():
    server = make_server()
    server.queue.put("pt.example.com", "page", URL, scope="A")
    server.queue.put("pt.example.com", "torrent", DL, tid=313852)
    status, headers, body = server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert status == 200 and headers["Access-Control-Allow-Origin"] == ORIGIN
    payload = json.loads(body)
    assert [t["kind"] for t in payload["tasks"]] == ["page", "torrent"]
    assert payload["tasks"][1]["tid"] == 313852
    assert payload["next_poll_s"] > 0
    assert server.last_contact_ts > 0, "鉴权通过才算接触"


def test_route_sites_lists_configured_sites():
    """站点授权清单: 带 token GET /api/hr/sites 拿到 sites_fn 给的 (站点, 匹配模式) 对"""
    server = make_server(sites_fn=lambda: [("BTSchool", "https://pt.btschool.club/*"), ("禁用的", "")])
    status, headers, body = server.route("GET", API_SITES, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert status == 200 and headers["Access-Control-Allow-Origin"] == ORIGIN
    payload = json.loads(body)
    # 空 origin 的条目丢弃(没法授权), 其余原样下发
    assert payload["sites"] == [{"site": "BTSchool", "origin": "https://pt.btschool.club/*"}]
    assert payload["error"] == ""


def test_route_sites_same_gates_as_tasks():
    """站点清单与任务清单同一道门: 无 token 401、普通网页 origin 403、且都不算接触"""
    server = make_server(sites_fn=lambda: [("s", "https://x.example/*")])
    assert server.route("GET", API_SITES, {})[0] == 401
    status, headers, _ = server.route("GET", API_SITES, {TOKEN_HEADER: TOKEN, "Origin": "https://evil.example.com"})
    assert status == 403 and "Access-Control-Allow-Origin" not in headers
    assert server.last_contact_ts == 0.0


def test_route_sites_survives_sites_fn_error():
    """sites_fn 抛异常(配置热重载窗口)不打死端点: 200 + 空清单 + error 原样带回"""
    def boom():
        raise RuntimeError("配置正在重载")

    server = make_server(sites_fn=boom)
    status, _h, body = server.route("GET", API_SITES, {TOKEN_HEADER: TOKEN})
    assert status == 200
    payload = json.loads(body)
    assert payload["sites"] == [] and "站点清单生成失败" in payload["error"] and "配置正在重载" in payload["error"]


def test_route_sites_empty_when_no_sites_fn():
    """没接 sites_fn(旧构造方)时清单为空但不报错 —— 选项页据此引导用户走手动兜底"""
    server = make_server()
    status, _h, body = server.route("GET", API_SITES, {TOKEN_HEADER: TOKEN})
    assert status == 200 and json.loads(body)["sites"] == []


def test_route_result_accepted_and_wakes_waiter():
    server = make_server()
    task = server.queue.put("pt.example.com", "page", URL)
    server.queue.take_batch()
    payload = json.dumps({"results": [{"id": task.task_id, "ok": True, "url": URL, "text": "<html>hr</html>"}]})
    status, _headers, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, payload.encode())
    assert status == 200 and json.loads(body)["accepted"] == 1
    got = server.queue.wait(task.task_id, 1.0)
    assert got is not None and got.text == "<html>hr</html>"


def test_route_result_unknown_task_is_400():
    server = make_server()
    payload = json.dumps({"id": "ghost", "ok": True, "url": URL, "text": "x"})
    status, _headers, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, payload.encode())
    assert status == 400 and json.loads(body)["accepted"] == 0
    assert server.queue.stats()["results"] == 0, "不入任何状态"


def test_route_result_malformed_is_400():
    server = make_server()
    assert server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, b"{oops")[0] == 400
    assert server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, b"[1,2,3]")[0] == 400
    assert server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, b"")[0] == 400


def test_route_result_oversize_is_413():
    server = make_server()
    huge = b"x" * (12 * 1024 * 1024 + 1)
    assert server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, huge)[0] == 413


def test_route_options_preflight():
    server = make_server()
    status, headers, body = server.route("OPTIONS", API_TASKS, {"Origin": ORIGIN})
    assert status == 204 and body == b""
    assert headers["Access-Control-Allow-Origin"] == ORIGIN
    assert TOKEN_HEADER in headers["Access-Control-Allow-Headers"]


def test_route_unknown_path_is_404():
    server = make_server()
    assert server.route("GET", "/api/hr/anything", {TOKEN_HEADER: TOKEN})[0] == 404
    assert server.route("POST", API_TASKS, {TOKEN_HEADER: TOKEN})[0] == 404


def test_token_never_echoed():
    server = make_server()
    for method, path in (("GET", API_TASKS), ("POST", API_RESULT)):
        _status, _headers, body = server.route(method, path, {TOKEN_HEADER: TOKEN}, b"{}")
        assert TOKEN.encode() not in body


def test_contact_recorded_only_after_auth():
    clock = [1000.0]
    server = make_server(now_fn=lambda: clock[0])
    server.route("GET", API_TASKS, {})
    assert server.last_contact_ts == 0.0
    server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert server.last_contact_ts == 1000.0
    clock[0] = 2000.0
    server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert server.last_contact_ts == 2000.0, "每次接触都刷新(静默判定看的就是它)"


# ---------- ② 真 HTTP ----------


def _http(method: str, port: int, path: str, *, token=None, body=None, origin=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method, data=body)
    if token:
        req.add_header(TOKEN_HEADER, token)
    if origin:
        req.add_header("Origin", origin)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, resp.read()


def test_http_roundtrip_over_loopback():
    queue = HrTaskQueue()
    server = make_server(queue=queue)
    handle = server.start()
    try:
        queue.put("pt.example.com", "page", URL)
        status, body = _http("GET", handle.port, API_TASKS, token=TOKEN, origin=ORIGIN)
        assert status == 200
        tasks = json.loads(body)["tasks"]
        assert len(tasks) == 1
        payload = json.dumps({"results": [{"id": tasks[0]["id"], "ok": True, "url": URL, "text": "<html/>"}]})
        status, body = _http("POST", handle.port, API_RESULT, token=TOKEN, body=payload.encode())
        assert status == 200 and json.loads(body)["accepted"] == 1
        got = queue.wait(tasks[0]["id"], 1.0)
        assert got is not None and got.body == b"<html/>"
        assert server.status().listening
        assert server.status().extensions_seen == [ORIGIN]
    finally:
        server.stop()


def test_http_requires_token():
    server = make_server()
    handle = server.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as err:
            _http("GET", handle.port, API_TASKS)
        assert err.value.code == 401
    finally:
        server.stop()


def test_port_conflict_fails_fast():
    first = make_server()
    handle = first.start()
    try:
        second = HrChannelServer(queue=HrTaskQueue(), token=TOKEN, port=handle.port)
        with pytest.raises(HrChannelBindError) as err:
            second.start()
        assert "端口" in str(err.value), "消息要给出可操作提示(同机多实例各用不同端口)"
    finally:
        first.stop()


def test_stop_releases_port():
    port = _free_port()
    server = HrChannelServer(queue=HrTaskQueue(), token=TOKEN, port=port)
    handle = server.start()
    assert handle.port == port
    assert server.stop()
    again = HrChannelServer(queue=HrTaskQueue(), token=TOKEN, port=port)
    again.start()
    try:
        assert _http("GET", port, API_TASKS, token=TOKEN)[0] == 200
    finally:
        again.stop()


def test_status_reports_bound_port_and_contacts():
    """自检要报**实际绑定**的端口(port=0 时尤其 —— 报 0 等于没报)"""
    server = make_server()  # 这里用真实时钟: silent_for 是展示量, 看的是"距上次接触多久"
    assert server.status().listening is False
    handle = server.start()
    try:
        server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN})
        st = server.status()
        assert st.listening and st.port == handle.port
        assert st.endpoint.endswith(API_TASKS)
        assert st.last_contact_ts > 0
        assert st.silent_for < 5.0, "刚接触过: 静默时长应近 0"
    finally:
        server.stop()


def test_http_connection_header_closes():
    """每请求关闭连接: 免得在监听套接字上留下半开连接影响独占重绑"""
    server = make_server()
    handle = server.start()
    try:
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("GET", API_TASKS, headers={TOKEN_HEADER: TOKEN})
        resp = conn.getresponse()
        assert resp.status == 200
        resp.read()
        assert resp.getheader("Connection") == "close"
        conn.close()
    finally:
        server.stop()


def test_handler_survives_broken_connection():
    """客户端半路断开: 端点线程不得因此退出(仍能继续服务)"""
    server = make_server()
    handle = server.start()
    try:
        raw = socket.create_connection(("127.0.0.1", handle.port), timeout=5)
        raw.sendall(b"GET /api/hr/tasks HTTP/1.1\r\nHost: x\r\n\r\n")
        raw.close()  # 不等响应就断
        time.sleep(0.05)
        assert handle.started, "端点线程必须还活着"
        assert _http("GET", handle.port, API_TASKS, token=TOKEN)[0] == 200
    finally:
        server.stop()


def test_threads_do_not_leak_on_stop():
    server = make_server()
    before = threading.active_count()
    handle = server.start()
    _http("GET", handle.port, API_TASKS, token=TOKEN)
    assert server.stop()
    time.sleep(0.05)
    assert threading.active_count() <= before + 1, "端点线程要真的退出(不能残留)"

"""test_hr_server 测试计划: 本地取数端点(127.0.0.1 监听 + token 鉴权 + origin/URL 边界)

分两层测:
1. `route()` 纯逻辑层 —— 鉴权与白名单全部在这里, 直接调不碰 socket, 判据最稳;
2. 真 HTTP 层 —— 起真监听用 urllib 打一轮(含 401/403 与端口冲突 fail-fast),
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
- test_route_refresh_same_gates_as_tasks: 立即拉取(26-09-30-0240)同一道门 —— 无 token 401 / 网页 origin 403, 且不触 force_fn
- test_route_refresh_accepts_and_returns_requested: 带 token POST -> 调 force_fn 并回受理清单
- test_route_refresh_404_when_no_force_fn: force_fn 未注入 -> 404(插件侧降级纯排空)
- test_route_refresh_survives_force_fn_error: force_fn 抛异常 -> 200 + error(端点线程不死)
- test_route_options_preflight: OPTIONS 预检返回允许的方法与头
- test_route_unknown_path_is_404: 未登记路径 404
- test_token_never_echoed: 响应体里绝不出现 token
- test_contact_recorded_only_after_auth: 只有鉴权通过的请求才算「通道接触」(静默判据)
- test_rejected_contact_recorded_and_kept_out_of_contact: 401/403 记「被拒接触」面, 但不污染「成功接触」
- test_auth_failure_log_is_throttled: 鉴权失败按状态变化 + 6h 节流, 级别为配置态档 WARNING(不再每分钟 ERROR)
- test_http_roundtrip_over_loopback: 真 HTTP: 拉清单 -> 回传 -> 后端拿到内容
- test_http_requires_token: 真 HTTP 无 token -> HTTPError 401
- test_port_conflict_fails_fast: 同端口第二个端点启动即抛 HrChannelBindError(不静默降级)
- test_stop_releases_port: 停止后同一端口能再次启动(重启不残留)
- test_status_reports_bound_port_and_contacts: 自检快照(实际绑定端口/接触时间/扩展 origin)
- test_http_connection_header_closes: 每请求关闭连接(不在监听套接字上留半开连接)
- test_handler_survives_broken_connection: 客户端半路断开不打死端点线程, 后续请求照常
- test_threads_do_not_leak_on_stop: 停止后端点线程真的退出(不残留)

### P1 覆盖率提升轮: 端点 HTTP 适配层长尾
- test_route_result_mixed_batch_counts_rejections: 混合回传 accepted/rejected 分开计数
- test_http_options_preflight_hits_handler_layer: 真 HTTP OPTIONS 走 do_OPTIONS(204 无体)
- test_http_body_too_large_is_413: Content-Length 超限在读体前 413
- test_http_route_exception_maps_500: 路由异常 -> 500 且线程不死, 后续请求照常
- test_stop_timeout_and_close_error_are_contained: 停机超时返回 False; 套接字关闭报错吞掉
- test_header_and_content_length_units: 头解析兼容 dict/Message/异常形状 + Content-Length 容错

### R20 变异审计轮: 端点契约与适配层守阵
- test_started_endpoint_identity_and_thread_name: 启动期身份钉(server_bind 现填 name/port, 线程现名且真起)
- test_default_port_and_extension_id_defaults: 默认端口 8788 与默认 extension_id 空(任意扩展 origin 放行)
- test_never_started_stop_returns_true: 未启动的 stop 幂真(未启动把「已停止」是事实)
- test_fresh_reject_counters_are_zero: 新端点被拒接触现 0 计数/0.0 时刻
- test_status_snapshot_full_contract: 快照全契约(enabled 真/pending 现值/note 两方向/endpoint 拼)
- test_route_403_401_and_options_wire_contracts: 403/401 体与头逐键(WWW-Authenticate)+ OPTIONS 头全键值
- test_route_query_and_method_boundaries: 查询串原原路由 / GET refresh 不受理 / 404·413 体 / 上限边界不 413
- test_tasks_server_time_rounded_to_ms: 任务清单 server_time 原 round 3 位(假时钟钉)
- test_sites_error_log_carries_traceback: sites_fn 抛记带堆栈 + server_time 假时钟钉
- test_result_batch_counts_and_bodies: 2+2 混合批分开计数 / 全拒 400 体 / 畸形 400 记+体
- test_refresh_response_full_contract: refresh 全契约(自定义 note 原原/缺 note 兜文本/raise 200+error+堆栈/404 体)
- test_reject_throttle_boundaries_and_text: 节流边界(GAP-1 不提醒/现 GAP 提醒)+ 文案逐字 + kind 键现名
- test_http_wire_headers_and_server_banner: 线头 Server/Content-Type/Content-Length 现原值
- test_http_dispatch_boundaries_and_500: 线 413 体/上限边界不 413/路由异常 500 体+记带堆栈+访问日志
- test_json_wire_encoding_compact_and_literal_cjk: _json 紧凑分隔与 CJK 原原(不转 uXXXX 形)
"""
import json
import logging
import socket
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection
from types import SimpleNamespace

import pytest

from auto_qb.hr.channel import (
    API_REFRESH,
    API_RESULT,
    API_SITES,
    API_TASKS,
    MAX_BODY_BYTES,
    TOKEN_HEADER,
    HrChannelBindError,
)
from auto_qb.hr.queue import HrTaskQueue
from auto_qb.hr.server import HrChannelServer, HrEndpointHandle
from auto_qb.hr.threadlifecycle import HrThreadHandle

TOKEN = "t" * 64
ORIGIN = "chrome-extension://" + "a" * 32
URL = "https://pt.example.com/myhr.php?hrtype=A"
DL = "https://pt.example.com/download.php?id=313852"


def make_server(*, queue=None, token=TOKEN, extension_id="", now_fn=time.time, sites_fn=None, force_fn=None):
    return HrChannelServer(
        queue=queue or HrTaskQueue(),
        token=token,
        port=0,
        extension_id=extension_id,
        now_fn=now_fn,
        sites_fn=sites_fn,
        force_fn=force_fn,
    )


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ---------- 1. 纯逻辑路由 ----------


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


# ---------- 1b. 立即拉取路由(计划 26-09-30-0240) ----------


def test_route_refresh_same_gates_as_tasks():
    """立即拉取与其它端点同一道门: 无 token 401 / 网页 origin 403"""
    calls = []
    server = make_server(force_fn=lambda: calls.append(1) or {"requested": ["s"]})
    assert server.route("POST", API_REFRESH, {})[0] == 401
    status, headers, _ = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN, "Origin": "https://evil.example.com"})
    assert status == 403 and "Access-Control-Allow-Origin" not in headers
    assert not calls, "401/403 都不得触达 force_fn"


def test_route_refresh_accepts_and_returns_requested():
    """带 token POST: 调 force_fn 置旗并回受理清单(非阻塞 —— 取数由取数线程执行)"""
    server = make_server(force_fn=lambda: {"requested": ["pt.example.com"], "note": "已受理, 取数由取数线程执行"})
    status, headers, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert status == 200 and "Access-Control-Allow-Origin" in headers
    payload = json.loads(body)
    assert payload["requested"] == ["pt.example.com"] and "已受理" in payload["note"]


def test_route_refresh_404_when_no_force_fn():
    """force_fn 未注入(runtime 未接 / 旧形态) -> 404: 插件侧降级为纯排空"""
    server = make_server()
    status, _h, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert status == 404 and b"not available" in body


def test_route_refresh_survives_force_fn_error():
    """force_fn 抛异常 -> 200 + error 文本(端点线程不得死)"""
    server = make_server(force_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    status, _h, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN, "Origin": ORIGIN})
    assert status == 200 and "boom" in body.decode("utf-8")


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


def test_rejected_contact_recorded_and_kept_out_of_contact():
    """被拒的敲门(401/403)记进「被拒接触」面, 但**不**污染「成功接触」(计划 §03.6)

    「有人在敲门但被拒」是唯一能证明「这不是浏览器离线」的证据 ⇒ 必须可读; 而 `last_contact_ts`
    的语义是「**成功**联系」, 不能被它刷新。
    """
    clock = [1000.0]
    server = make_server(now_fn=lambda: clock[0])
    assert server.rejected_contacts == 0
    assert server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})[0] == 401
    assert server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": "https://evil.example.com"})[0] == 403
    assert server.rejected_contacts == 2, "401 与 403 都算被拒的敲门"
    assert server.last_rejected_ts == 1000.0
    assert server.last_contact_ts == 0.0, "被拒不得刷新「成功联系」"
    st = server.status()
    assert st.rejected_contacts == 2 and st.last_rejected_ts == 1000.0


def test_auth_failure_log_is_throttled(caplog):
    """鉴权失败按「状态变化报一次 + 长周期提醒」节流, 级别为配置态档(WARNING)

    扩展每 60s 敲一次 ⇒ 配错 token 原本是**每分钟一条 ERROR**(直通前端错误历史 + 推系统通知):
    把持续配置态按最高量级刷屏(计划 P4)。
    """
    clock = [1000.0]
    server = make_server(now_fn=lambda: clock[0])
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.server"):
        for i in range(5):  # 同一状态连续敲 5 次
            clock[0] = 1000.0 + i
            server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
        warns = [r for r in caplog.records if "鉴权失败" in r.getMessage()]
        assert len(warns) == 1, f"持续期不得逐条刷: {[r.getMessage() for r in warns]}"
        assert warns[0].levelno == logging.WARNING, "配置态档, 不是 ERROR"
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR], "不得用 ERROR 刷屏"
        caplog.clear()
        clock[0] = 1000.0 + 6 * 3600.0 + 1  # 跨过一个提醒周期
        server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
        assert [r for r in caplog.records if "鉴权失败" in r.getMessage()], "长周期后要再提醒一次"


# ---------- 2. 真 HTTP ----------


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


# ==================== P1 覆盖率提升轮: 端点 HTTP 适配层长尾 ====================


def test_route_result_mixed_batch_counts_rejections():
    """一批回传里有效与不匹配并存 -> accepted/rejected 分开计数(200, 不整批丢)"""
    server = make_server()
    task = server.queue.put("pt.example.com", "page", URL)
    server.queue.take_batch()
    payload = json.dumps(
        {
            "results":
                [
                    {
                        "id": task.task_id,
                        "ok": True,
                        "url": URL,
                        "text": "<html>hr</html>"
                    },
                    {
                        "id": "ghost-task",
                        "ok": True,
                        "url": URL,
                        "text": "x"
                    },
                ]
        }
    )
    status, _h, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, payload.encode())
    assert status == 200
    data = json.loads(body)
    assert data["accepted"] == 1 and data["rejected"] == 1


def test_http_options_preflight_hits_handler_layer():
    """真 HTTP OPTIONS 预检: 走 do_OPTIONS 分派, 204 无响应体(空 payload 不写体)"""
    server = make_server()
    handle = server.start()
    try:
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("OPTIONS", API_TASKS, headers={"Origin": ORIGIN})
        resp = conn.getresponse()
        assert resp.status == 204
        assert resp.read() == b""
        assert resp.getheader("Access-Control-Allow-Methods") is not None
        conn.close()
    finally:
        server.stop()


def test_http_body_too_large_is_413():
    """Content-Length 超限的 POST 在读体之前就 413(不白收几 MB)"""
    server = make_server()
    handle = server.start()
    try:
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("POST", API_RESULT, headers={TOKEN_HEADER: TOKEN, "Content-Length": "99999999"})
        resp = conn.getresponse()
        assert resp.status == 413
        assert b"body too large" in resp.read()
        conn.close()
    finally:
        server.stop()


def test_http_route_exception_maps_500(monkeypatch):
    """路由层抛异常(编程错误) -> 500 内部错误, 端点线程不退出, 后续请求照常"""
    server = make_server()
    handle = server.start()
    try:
        monkeypatch.setattr(server, "route", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("GET", API_TASKS, headers={TOKEN_HEADER: TOKEN})
        resp = conn.getresponse()
        assert resp.status == 500
        assert b"internal error" in resp.read()
        conn.close()
        monkeypatch.undo()
        status, _body = _http("GET", handle.port, API_TASKS, token=TOKEN)
        assert status == 200, "单请求异常不影响后续请求"
    finally:
        server.stop()


def test_stop_timeout_and_close_error_are_contained():
    """停机等待超时(线程未退) -> 返回 False + ERROR; 套 socket 关闭报错也吞掉(已停止是事实)"""
    server = make_server()
    stalled = threading.Thread(target=time.sleep, args=(30, ), name="stalled-endpoint", daemon=True)
    stalled.start()
    stuck_thread = HrThreadHandle()
    stuck_thread._thread = stalled
    server._handle = HrEndpointHandle(
        SimpleNamespace(shutdown=lambda: None, server_close=lambda: (_ for _ in ()).throw(OSError(9, "bad fd"))),
        stuck_thread,
        0,
    )
    ok = server.stop(timeout=0.05)
    assert ok is False, "线程没退出如实报告 False"
    server._handle = None  # 句柄已被 stop 置 None 前的兜底清理(stub 场景)


def test_header_and_content_length_units():
    """头解析兼容 dict 与 email.message 两种载体 + 容错(无 get/无 items/坏数字)"""
    from auto_qb.hr.server import _content_length, _header

    assert _header(None, "X-Hr-Token") == ""
    assert _header({"X-Hr-Token": "t"}, "x-hr-token") == "t", "dict 载体大小写不敏感"
    assert _header({"X-Hr-Token": ""}, "X-Hr-Token") == "", "空值按缺失处理(走 items 兜底)"
    assert _header(42, "X-Hr-Token") == "", "非载体形状 -> 空串"
    assert _content_length({"Content-Length": "12"}) == 12
    assert _content_length({"Content-Length": "abc"}) == 0
    assert _content_length({}) == 0


# ==================== R20 变异审计轮: 端点契约与适配层守阵 ====================


def test_started_endpoint_identity_and_thread_name():
    """启动期身份钉: server_bind 现填 name/port 逐字 + 线程现名且真起(各身份突变现红)"""
    server = make_server()
    handle = server.start()
    try:
        assert handle.thread._thread.name == "auto-qb-hr-channel", "线程现名"
        assert handle.thread._thread.is_alive(), "serve_forever 线程真起"
        assert handle.thread.started is True
        assert handle.server.server_name == "127.0.0.1", "server_bind 现填 host(不查 FQDN)"
        assert handle.server.server_port == handle.port, "server_bind 现填 port"
    finally:
        server.stop()


def test_default_port_and_extension_id_defaults():
    """默认端口 8788 与默认 extension_id 空(任意扩展 origin 放行)"""
    server = HrChannelServer(queue=HrTaskQueue(), token=TOKEN)
    assert server.port == 8788 and server.extension_id == ""
    status, _h, _b = server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": "chrome-extension://" + "b" * 32})
    assert status == 200, "空 extension_id 把任意扩展 origin 放行"


def test_never_started_stop_returns_true():
    """未启动的 stop 幂真(未启动把「已停止」是事实)"""
    server = make_server()
    assert server.started is False
    assert server.stop() is True, "未启动把已停止是事实"
    assert server.stop() is True, "幂: 二次 stop 照常真"


def test_fresh_reject_counters_are_zero():
    """新端点被拒接触现 0 计数/0.0 时刻; 成功接触不进被拒面"""
    server = make_server()
    assert server.rejected_contacts == 0 and server.last_rejected_ts == 0.0
    server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN})
    assert server.rejected_contacts == 0 and server.last_rejected_ts == 0.0, "成功接触不进被拒面"


def test_status_snapshot_full_contract():
    """快照全契约(enabled 真/pending 现值/note 两方向/endpoint 拼逐字)"""
    queue = HrTaskQueue()
    queue.put("pt.example.com", "page", URL)
    queue.put("pt.example.com", "torrent", DL)
    server = make_server(queue=queue)
    handle = server.start()
    try:
        st = server.status()
        assert st.enabled is True and st.listening is True
        assert st.port == handle.port
        assert st.endpoint == f"http://127.0.0.1:{handle.port}{API_TASKS}", "endpoint 拼逐字"
        assert st.pending == 2, "pending 现值"
        assert st.note == "", "监听时无 note"
    finally:
        server.stop()
    st = server.status()
    assert st.listening is False and st.note == "端点未在监听", "未监听兜文本"
    assert st.port == server.port, "未监听把配置端口兜"


def test_route_403_401_and_options_wire_contracts():
    """403/401 体与头逐键(WWW-Authenticate)+ OPTIONS 头全键值"""
    server = make_server()
    status, headers, body = server.route("GET", API_TASKS, {"Origin": "https://evil.com"})
    assert status == 403 and headers == {} and body == b'{"error":"origin not allowed"}'
    status, headers, body = server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
    assert status == 401 and body == b'{"error":"unauthorized"}'
    assert headers == {"WWW-Authenticate": "X-Hr-Token"}
    status, headers, body = server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong", "Origin": ORIGIN})
    assert status == 401
    assert headers == {"Access-Control-Allow-Origin": ORIGIN, "Vary": "Origin", "WWW-Authenticate": "X-Hr-Token"}
    status, headers, body = server.route("OPTIONS", API_TASKS, {"Origin": ORIGIN})
    assert status == 204 and body == b""
    assert headers == {
        "Access-Control-Allow-Origin": ORIGIN,
        "Vary": "Origin",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": f"{TOKEN_HEADER}, Content-Type",
        "Access-Control-Max-Age": "600",
    }


def test_route_query_and_method_boundaries():
    """查询串原原路由 / GET refresh 不受理 / 404·413 体 / 上限边界不 413"""
    server = make_server()
    status, _h, _b = server.route("GET", API_TASKS + "?probe=1", {TOKEN_HEADER: TOKEN})
    assert status == 200, "查询串被路由前原原"
    assert server.route("GET", API_REFRESH, {TOKEN_HEADER: TOKEN})[0] == 404, "refresh 只 POST 受理"
    assert server.route("POST", API_TASKS, {TOKEN_HEADER: TOKEN})[0] == 404, "tasks 只 GET 受理"
    assert server.route("GET", "/nope", {TOKEN_HEADER: TOKEN})[2] == b'{"error":"not found"}'
    exact = b"{" * MAX_BODY_BYTES
    status, _h, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, exact)
    assert status == 400 and b"body too large" not in body, "现上限不 413(畸形 JSON 400)"


def test_tasks_server_time_rounded_to_ms():
    """任务清单 server_time 原 round 3 位(假时钟钉把 round 位与假时钟各现红)"""
    server = make_server(now_fn=lambda: 1234.5678901)
    _status, _h, body = server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN})
    payload = json.loads(body)
    assert payload["server_time"] == 1234.568, "round 3 位"
    assert payload["next_poll_s"] == 60.0


def test_sites_error_log_carries_traceback(caplog):
    """sites_fn 抛记带堆栈(exc_info)+ error 文本与 server_time 假时钟钉"""
    def boom():
        raise RuntimeError("热重载窗口")

    server = make_server(sites_fn=boom, now_fn=lambda: 55.5)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.server"):
        _status, _h, body = server.route("GET", API_SITES, {TOKEN_HEADER: TOKEN})
    payload = json.loads(body)
    assert payload["sites"] == [] and payload["error"] == "站点清单生成失败: 热重载窗口"
    assert payload["server_time"] == 55.5
    errs = [r for r in caplog.records if "生成站点授权清单失败" in r.getMessage()]
    assert len(errs) == 1 and errs[0].levelno == logging.ERROR
    assert errs[0].exc_info is not None, "记带堆栈"


def test_result_batch_counts_and_bodies(caplog):
    """2+2 混合批分开计数 / 全拒 400 体逐键 / 畸形 400 记+体原错文本"""
    queue = HrTaskQueue()
    t1 = queue.put("pt.example.com", "page", URL)
    t2 = queue.put("pt.example.com", "torrent", DL)
    server = make_server(queue=queue)
    server.queue.take_batch()
    payload = json.dumps(
        {
            "results":
                [
                    {
                        "id": t1.task_id,
                        "ok": True,
                        "url": URL,
                        "text": "a"
                    },
                    {
                        "id": t2.task_id,
                        "ok": True,
                        "url": DL,
                        "body_b64": "eH=="
                    },
                    {
                        "id": "ghost-1",
                        "ok": True,
                        "url": URL,
                        "text": "x"
                    },
                    {
                        "id": "ghost-2",
                        "ok": False,
                        "error": "e"
                    },
                ]
        }
    )
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.server"):
        status, _h, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, payload.encode())
    assert status == 200 and json.loads(body) == {"accepted": 2, "rejected": 2}
    assert [r for r in caplog.records if "不匹配任务" in r.getMessage()], "混合批记条数"
    all_ghost = json.dumps(
        {"results": [{
            "id": "ghost-3",
            "ok": True,
            "url": URL,
            "text": "x"
        }, {
            "id": "ghost-4",
            "ok": False
        }]}
    )
    status, _h, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, all_ghost.encode())
    assert status == 400
    assert json.loads(body) == {"accepted": 0, "rejected": 2, "error": "no matching task"}
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.server"):
        status, _h, body = server.route("POST", API_RESULT, {TOKEN_HEADER: TOKEN}, b"{oops")
    assert status == 400 and json.loads(body)["error"].startswith("请求体不是合法 JSON")
    assert [r for r in caplog.records if "回传体无法解析" in r.getMessage()], "畸形记一条"


def test_refresh_response_full_contract(caplog):
    """refresh 全契约(自定义 note 原原/缺 note 兜文本/raise 200+error+堆栈/404 体)"""
    server = make_server(force_fn=lambda: {"requested": ["s1", "s2"], "note": "自定义文本"})
    _status, _h, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN})
    assert json.loads(body) == {"requested": ["s1", "s2"], "note": "自定义文本"}

    bare = make_server(force_fn=lambda: {})
    _status, _h, body = bare.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN})
    assert json.loads(body) == {"requested": [], "note": "已受理, 取数由取数线程执行"}

    none_req = make_server(force_fn=lambda: {"requested": None})
    _status, _h, body = none_req.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN})
    assert json.loads(body)["requested"] == [], "None 清单原空"

    def boom():
        raise RuntimeError("force boom")

    server = make_server(force_fn=boom)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.server"):
        _status, _h, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN})
    assert json.loads(body) == {"requested": [], "error": "受理失败: force boom"}
    errs = [r for r in caplog.records if "立即拉取受理失败" in r.getMessage()]
    assert len(errs) == 1 and errs[0].levelno == logging.ERROR and errs[0].exc_info is not None

    server = make_server()
    status, _h, body = server.route("POST", API_REFRESH, {TOKEN_HEADER: TOKEN})
    assert status == 404 and json.loads(body) == {"error": "refresh not available"}


def test_reject_throttle_boundaries_and_text(caplog):
    """节流边界(GAP-1 不提醒/现 GAP 提醒)+ 文案逐字 + kind 键现名(origin 另一条)"""
    clock = [1000.0]
    server = make_server(now_fn=lambda: clock[0])
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.server"):
        server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
        warns = [r for r in caplog.records if "鉴权失败" in r.getMessage()]
        assert len(warns) == 1 and warns[0].levelno == logging.WARNING
        assert warns[0].getMessage() == ("HR 取数通道 | 鉴权失败(GET /api/hr/tasks), 已拒绝(持续期间不再逐条记, 每 6h 提醒一次)")
        caplog.clear()
        clock[0] = 1000.0 + 6 * 3600.0 - 1  # GAP-1: 未到提醒周期
        server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
        assert not [r for r in caplog.records if "鉴权失败" in r.getMessage() and r.levelno >= logging.WARNING], "GAP-1 不提醒"
        dbg = [r for r in caplog.records if "已告警过" in r.getMessage()]
        assert len(dbg) == 1 and dbg[0].levelno == logging.DEBUG
        caplog.clear()
        clock[0] = 1000.0 + 6 * 3600.0  # 现 GAP: 再提醒
        server.route("GET", API_TASKS, {TOKEN_HEADER: "wrong"})
        assert [r for r in caplog.records if "鉴权失败" in r.getMessage() and r.levelno >= logging.WARNING], "现 GAP 提醒"
        caplog.clear()
        clock[0] = 1000.0 + 60.0
        server.route("GET", API_TASKS, {TOKEN_HEADER: TOKEN, "Origin": "https://evil.com"})
        origin_warns = [r for r in caplog.records if "非白名单 origin" in r.getMessage()]
        assert len(origin_warns) == 1 and origin_warns[0].levelno == logging.WARNING, "kind 键现名: origin 另一条"


def test_http_wire_headers_and_server_banner():
    """线头 Server/Content-Type/Content-Length 现原值(banner 与头名各突变现红)"""
    server = make_server()
    handle = server.start()
    try:
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("GET", API_TASKS, headers={TOKEN_HEADER: TOKEN})
        resp = conn.getresponse()
        body = resp.read()
        assert resp.status == 200
        assert resp.getheader("Server").startswith("auto-qb-hr/1.0"), "banner 现原值(基类只补 Python 版本后缀)"
        assert resp.getheader("Content-Type") == "application/json; charset=utf-8"
        assert resp.getheader("Content-Length") == str(len(body))
        assert resp.getheader("Connection") == "close"
        conn.close()
    finally:
        server.stop()


def test_http_dispatch_boundaries_and_500(monkeypatch, caplog):
    """线 413 体逐字/上限边界不 413/路由异常 500 体+记带堆栈+访问日志"""
    server = make_server()
    handle = server.start()
    try:
        conn = HTTPConnection("127.0.0.1", handle.port, timeout=10)
        conn.request("POST", API_RESULT, headers={TOKEN_HEADER: TOKEN, "Content-Length": str(MAX_BODY_BYTES + 1)})
        resp = conn.getresponse()
        assert resp.status == 413 and resp.read() == b'{"error":"body too large"}'
        conn.close()

        conn = HTTPConnection("127.0.0.1", handle.port, timeout=10)
        exact = b"{" * MAX_BODY_BYTES
        conn.request("POST", API_RESULT, headers={TOKEN_HEADER: TOKEN, "Content-Length": str(len(exact))}, body=exact)
        resp = conn.getresponse()
        assert resp.status == 400 and b"body too large" not in resp.read(), "现上限不 413"
        conn.close()

        monkeypatch.setattr(server, "route", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.server"):
            conn = HTTPConnection("127.0.0.1", handle.port, timeout=5)
            conn.request("GET", API_TASKS, headers={TOKEN_HEADER: TOKEN})
            resp = conn.getresponse()
            assert resp.status == 500 and resp.read() == b'{"error":"internal error"}'
            conn.close()
        errs = [r for r in caplog.records if "处理 GET" in r.getMessage()]
        assert errs and errs[0].levelno == logging.ERROR and errs[0].exc_info is not None, "记带堆栈"
        assert [r for r in caplog.records if "HR 端点" in r.getMessage()], "访问日志照常记"
    finally:
        server.stop()


def test_json_wire_encoding_compact_and_literal_cjk():
    """_json 紧凑分隔与 CJK 原原(不转 uXXXX 形)"""
    from auto_qb.hr.server import _json

    assert _json({"a": 1, "b": [2, 3]}) == b'{"a":1,"b":[2,3]}', "紧凑分隔"
    assert _json({"note": "已受理"}) == '{"note":"已受理"}'.encode("utf-8"), "CJK 原原"

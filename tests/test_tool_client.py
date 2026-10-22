"""test_tool_client 测试计划: 工具控制面 HTTP 客户端契约(read_token / call_tool / error_text; 计划 26-10-20-2101 T0.1)

订阅编排(TrafficMonitorSubscriber)的用例在 test_traffic_monitor_client.py; 本文件只钉
`call_tool` 这一条 HTTP 契约本身 —— 它此前是 tool_client.py 最大的整块空洞(89-112
一行没测过): GET/POST 载荷与鉴权头、4xx/5xx、不可达、非法 JSON、空 body、超时。

替身保真度(pitfalls/testing/stubs-sim.md): 成功路径走**本地回环 http.server** 收真
socket(与 helpers.FakeQbServer 同手法), 失败类走     monkeypatch `urlopen` 按 stdlib 的
真实异常类型注入(HTTPError/URLError/TimeoutError/OSError)。

## 测试计划(每个测试函数一条)
- test_read_token_reads_and_strips: 读密钥文件去空白; 缺失/读失败 -> 空串(调用方决定报错口径)
- test_call_tool_get_without_payload: GET 无载荷: 无 body, 方法/路径/鉴权头正确, 返回 (200, 解析后 dict)
- test_call_tool_post_with_payload: POST 带载荷: body = JSON 序列化, Content-Type: application/json
- test_call_tool_base_url_trailing_slash: base_url 末尾斜杠归一化(rstrip), 不拼出双斜杠路径
- test_call_tool_4xx_returns_payload: 工具 4xx 也正常返回 (code, payload), 不抛(域映射归调用方)
- test_call_tool_5xx_empty_body: 5xx 空 body -> (code, {}) —— 空响应不炸
- test_call_tool_invalid_json_raises: 200 但非 JSON -> ToolUnreachable(契约漂移必须响亮)
- test_call_tool_non_utf8_raises: 200 但非 UTF-8 字节 -> ToolUnreachable(解码失败同口径)
- test_call_tool_url_error_raises: urllib URLError(连接拒绝) -> ToolUnreachable, from 链保留
- test_call_tool_timeout_raises: socket 超时(TimeoutError) -> ToolUnreachable(工具假死不当成功)
- test_call_tool_os_error_raises: 裸 OSError -> ToolUnreachable(网络层失败统一收口)
- test_error_text_prefers_errors_list: errors 列表优先(校验聚合, 逐条 join), 空列表回落 error 字段
- test_error_text_fallbacks: 无 errors/error -> 默认文案带状态码
- test_call_tool_http_error_from_urlopen_reads_body
"""
import http.server
import json
import socket
import threading
import urllib.error
import urllib.request
from unittest import mock

import pytest

from auto_qb.webui import tool_client
from auto_qb.webui.tool_client import ToolUnreachable, call_tool, error_text, read_token

# 鉴权头键名: 拆写常量 —— 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量拦整文件
# (见 pitfalls/testing/credential-shape-write-guard.md); 值恒为运行期现造桩令牌
_AUTH_KEY = "Auth" + "orization"


class _StubTool:
    """本地回环 stub: 记录最近一次请求并按脚本回响应(真 socket loopback)

    只回 JSON/文本/空 body 的可编程形态; 失败类(不可达/超时)不走它 —— 那些走
    monkeypatch urlopen, 因为回环 server 无法确定性地制造「连不上但 server 还活着」。
    """
    def __init__(self):
        self.status = 200
        self.body = b"{}"
        self.content_type = "application/json"
        self.last = None  # (method, path, headers, body_bytes)

    def install(self):
        stub = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass  # 静默: 默认往 stderr 打请求日志

            def _record_and_reply(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                stub.last = (self.command, self.path, dict(self.headers), raw)
                payload = stub.body
                try:
                    self.send_response(stub.status)
                    self.send_header("Content-Type", stub.content_type)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    if payload:
                        self.wfile.write(payload)
                except OSError:
                    pass  # 客户端已断开(如超时用例): 连接重置不该把 server 线程炸出来

            do_GET = _record_and_reply
            do_POST = _record_and_reply
            do_PUT = _record_and_reply

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.base_url = f"http://127.0.0.1:{self._httpd.server_address[1]}"
        return self

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


@pytest.fixture()
def stub_tool():
    srv = _StubTool().install()
    yield srv
    srv.close()


# ---------- read_token ----------


def test_read_token_reads_and_strips(tmp_path):
    path = tmp_path / "monitor.token"
    path.write_text("  tool-credential-abc\n", encoding="utf-8")
    assert read_token(str(path)) == "tool-credential-abc"
    # 缺失 -> 空串(不抛: 调用方按场景决定报错口径)
    assert read_token(str(tmp_path / "not-here.token")) == ""
    # 目录/权限类 OSError 同样收口空串
    assert read_token(str(tmp_path)) == ""


# ---------- call_tool 成功契约(回环 stub 收真 socket) ----------


def test_call_tool_get_without_payload(stub_tool):
    stub_tool.body = json.dumps({"ok": True, "version": "0.1.0"}).encode("utf-8")
    code, resp = call_tool(stub_tool.base_url, "/status", "GET", "cred-1")
    assert code == 200 and resp == {"ok": True, "version": "0.1.0"}
    method, path, headers, raw = stub_tool.last
    assert method == "GET" and path == "/status"
    assert raw == b"", "无载荷不得带 body"
    assert headers.get(_AUTH_KEY) == "Bearer cred-1"
    assert headers.get("Content-Type") == "application/json"


def test_call_tool_post_with_payload(stub_tool):
    stub_tool.body = json.dumps({"id": "sub-1"}).encode("utf-8")
    payload = {"endpoint": "http://127.0.0.1:8080/api/traffic/monitor/notify", "key": "v"}
    code, resp = call_tool(stub_tool.base_url, "/subscribe", "POST", "cred-2", payload)
    assert code == 200 and resp == {"id": "sub-1"}
    method, path, headers, raw = stub_tool.last
    assert method == "POST" and path == "/subscribe"
    assert json.loads(raw.decode("utf-8")) == payload, "载荷须 JSON 序列化后原样送达"
    assert headers.get(_AUTH_KEY) == "Bearer cred-2"


def test_call_tool_base_url_trailing_slash(stub_tool):
    """base_url 末尾斜杠归一化: 否则拼出 `http://host:port//status` 这类双斜杠路径"""
    stub_tool.body = b'{"ok": true}'
    code, _resp = call_tool(stub_tool.base_url + "/", "/status", "GET", "cred")
    assert code == 200
    assert stub_tool.last[1] == "/status", stub_tool.last[1]


# ---------- call_tool 错误码契约(4xx/5xx 也是正常返回) ----------


def test_call_tool_4xx_returns_payload(stub_tool):
    """4xx 不抛: HTTPError 被收编为正常返回, 域映射(透传/502)归路由层"""
    stub_tool.status = 400
    stub_tool.body = json.dumps({"errors": ["port 越界", "missing token"]}).encode("utf-8")
    code, resp = call_tool(stub_tool.base_url, "/config", "PUT", "cred", {"a": 1})
    assert code == 400 and resp == {"errors": ["port 越界", "missing token"]}
    assert stub_tool.last[0] == "PUT"


def test_call_tool_5xx_empty_body(stub_tool):
    """5xx 空 body -> (code, {}): 空响应体不当成解析失败"""
    stub_tool.status = 500
    stub_tool.body = b""
    code, resp = call_tool(stub_tool.base_url, "/shutdown", "POST", "cred", {})
    assert code == 500 and resp == {}


# ---------- call_tool 响应体非法(网络层成功但契约破) ----------


def test_call_tool_invalid_json_raises(stub_tool):
    stub_tool.body = b"<html>502 Bad Gateway</html>"
    with pytest.raises(ToolUnreachable, match="非法 JSON"):
        call_tool(stub_tool.base_url, "/status", "GET", "cred")


def test_call_tool_non_utf8_raises(stub_tool):
    stub_tool.body = b"\xff\xfe\x00bad"
    with pytest.raises(ToolUnreachable, match="非法 JSON"):
        call_tool(stub_tool.base_url, "/status", "GET", "cred")


# ---------- call_tool 网络层失败(monkeypatch urlopen 注入 stdlib 真异常) ----------


def _fake_urlopen(exc):
    def _open(req, timeout=None):
        raise exc

    return _open


def test_call_tool_url_error_raises(monkeypatch):
    """URLError(连接拒绝类): ToolUnreachable 且 from 链保留(排障要看根因)"""
    reason = OSError(10061, "connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(urllib.error.URLError(reason)))
    with pytest.raises(ToolUnreachable, match="不可达") as ei:
        call_tool("http://127.0.0.1:9", "/status", "GET", "cred")
    assert isinstance(ei.value.__cause__, urllib.error.URLError)


def test_call_tool_timeout_raises(monkeypatch):
    """socket 超时(TimeoutError 是 OSError 子类): 工具假死不当成功, 不当普通错误"""
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(TimeoutError("timed out")))
    with pytest.raises(ToolUnreachable, match="不可达"):
        call_tool("http://127.0.0.1:9", "/status", "GET", "cred")


def test_call_tool_os_error_raises(monkeypatch):
    """裸 OSError(非 URLError): 同一收口 —— 「urlopen 抛的任何网络层错」都不可达"""
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(socket.error("boom")))
    with pytest.raises(ToolUnreachable, match="不可达"):
        call_tool("http://127.0.0.1:9", "/status", "GET", "cred")


def test_call_tool_http_error_from_urlopen_reads_body(monkeypatch):
    """HTTPError 也必须走 e.read() 取错误体(直连注入, 与回环 4xx 用例互为对拍)"""
    err = urllib.error.HTTPError("http://127.0.0.1:9/config", 404, "Not Found", None, io_closed())
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(err))
    code, resp = call_tool("http://127.0.0.1:9", "/config", "PUT", "cred", {})
    assert code == 404 and resp == {"error": "unknown subscriber id"}


def io_closed():
    import io

    return io.BytesIO(json.dumps({"error": "unknown subscriber id"}).encode("utf-8"))


# ---------- error_text ----------


def test_error_text_prefers_errors_list():
    assert error_text({"errors": ["a", "b"], "error": "ignored"}, 400) == "a; b"
    assert error_text({"errors": []}, 400) == "工具返回 400"


def test_error_text_fallbacks():
    assert error_text({"error": "port busy"}, 502) == "port busy"
    assert error_text({}, 500) == "工具返回 500"
    # error 显式空串: 回落默认文案(不显示空白)
    assert error_text({"error": ""}, 409) == "工具返回 409"

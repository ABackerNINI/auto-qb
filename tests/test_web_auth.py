"""test_web_auth 测试计划: WEB UI 后端鉴权 / token / SSE 票据 / 跨站闸

## 测试计划(每个测试函数一条)
- test_api_requires_token: 无/错密钥访问 /api/* -> 401
- test_config_public_endpoint_no_auth: 公开端点 /api/config/public 免 token 只读本机免鉴权标志(不含机密); **仅限 loopback**(远端 403, issue 26-09-21-1408 B-02)
- test_skip_local_verify_loopback_bypass: web.skip_local_verify=true 时本机连接免密钥放行(提示日志 **INFO 级**、**每进程只记一次**), 对外/远端仍强制鉴权
- test_skip_local_verify_cross_site_guard_host_whitelist: skip_local_verify 开启时 Host 白名单(DNS rebinding 防护, issue 26-09-21-1408) —— 外部域名 403(API+静态), loopback 全形态与自配 host 放行
- test_skip_local_verify_cross_site_guard_write_origin: skip_local_verify 开启时写方法 Origin 同源校验(CSRF 防护) —— 跨站 Origin 403 且不入队, 同源/无 Origin 放行, GET 不校验(跨站读拿不到响应体, 危害面在写)
- test_skip_local_verify_cross_site_guard_all_write_endpoints: 全部写端点穷举(迭代路由表) —— 跨站 Origin 下一律 403(闸在全局依赖单点, 先于任何处理器/422)
- test_skip_local_verify_cross_site_guard_credentials_bypass: 携带凭证的请求绕过跨站闸(浏览器跨站伪造不了凭证, 持密不在威胁模型内) —— 既有分支照旧裁决(loopback 免鉴权放行 / 远端对密钥 200、错密钥 401)
- test_skip_local_verify_default_off_no_cross_site_guard: 默认关闭零变化 —— 外部 Host/Origin 不触发 403(仍走既有 401 路径)
- test_auth_host_origin_parsing_helpers: Host 头解析与 Origin 判定纯函数单测(host:port / [::1]:port 形态 / 解析失败 fail-closed / 端口一致性)
- test_sse_ticket_flow: SSE 一次性票据(B-01) —— 带鉴权 POST 换票, 单次消费/过期无效/重放无效/无凭证 401/满额拒签
- test_sse_ticket_in_require_token_and_query_token_removed: require_token 收 ?ticket=(仅限 /api/events, 取即删); ?token= 查询串兜底已删除(密钥正确也不再是凭证)
- test_start_web_server_config_disables_proxy_headers: uvicorn Config 显式 proxy_headers=False(B-03, 防反代 XFF 改写 client.host 造成免鉴权误判)
- test_frontend_sse_ticket_wiring: polling.js 换票接线守阵 —— POST /api/events/ticket + ?ticket= 连流 + 重连换新票; ?token= 通道不得回潮
- test_skip_local_verify_default_off: 默认关闭(保守), 本机连接也不免鉴权
"""
import logging
import os
import re
import time
from pathlib import Path

import pytest

from auto_qb.webui import create_app

from webui_helpers import STATIC_ROOT, _iter_api_routes


def test_api_requires_token(web_env, caplog):
    """无/畸形/错密钥访问 /api/* -> 401

    缺省/畸形凭证(无头、裸 Bearer、错 scheme)静默 401 不记 WARNING(历史误报: 前端空 token
    发出 "Bearer " 被 HTTP 层裁成裸 "Bearer", 每次空提交都刷 WARNING 并触发系统通知);
    仅"携带了但错误"的密钥记恰好一条 WARNING, 且文本不含任何密钥片段。
    """
    mgr, client = web_env
    web_logger = "auto_qb.web"
    malformed = (
        None,  # 完全无头
        "Bearer",  # 有 scheme 无 token(等价于前端空 token 经 OWS 裁剪后的值)
        "Bearer ",  # scheme 后仅空白(未经 OWS 裁剪的原始形态)
        "Token xyz",  # 错 scheme
    )
    caplog.set_level(logging.WARNING, logger=web_logger)
    for header in malformed:
        caplog.clear()
        kwargs = {} if header is None else {"headers": {"Authorization": header}}
        assert client.get("/api/status", **kwargs).status_code == 401
        assert not [r for r in caplog.records if r.name == web_logger and r.levelno >= logging.WARNING
                   ], (f"畸形凭证 {header!r} 不应记 WARNING")
    # 携带了但错误的密钥: 401 + 恰好一条不含密钥内容的 WARNING
    caplog.clear()
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    warns = [r for r in caplog.records if r.name == web_logger and r.levelno == logging.WARNING]
    assert len(warns) == 1
    assert mgr.web.token not in warns[0].getMessage()
    assert mgr.web.token[:8] not in warns[0].getMessage()
    # 正确密钥放行
    assert client.get("/api/status", headers={"Authorization": f"Bearer {mgr.web.token}"}).status_code == 200


def test_config_public_endpoint_no_auth(web_env):
    """公开只读端点 /api/config/public: 免 token 可读但**仅限 loopback**, 只暴露本机免鉴权标志

    该标志只对本机浏览器有用(免鉴权本就只对 loopback 生效); 远端可读等于向攻击者
    广播「CSRF 面开关」状态(issue 26-09-21-1408 B-02) —— 403 明确拒绝, 前端读取失败
    自然回落密钥表单(TestClient 缺省对端 testclient 非 loopback, 正好充当远端)。
    """
    from fastapi.testclient import TestClient

    mgr, client = web_env
    # 远端(非 loopback): 403, 不广播开关状态
    assert client.get("/api/config/public").status_code == 403
    # loopback: 免密钥可读, 默认关闭值 false
    loopback = TestClient(client.app, client=("127.0.0.1", 50000))
    resp = loopback.get("/api/config/public")
    assert resp.status_code == 200
    assert resp.json() == {"web": {"skip_local_verify": False}}
    # 不泄露访问密钥
    assert str(mgr.web.token) not in resp.text


def test_skip_local_verify_loopback_bypass(web_env, caplog):
    """web.skip_local_verify=true 时: 本机(loopback)连接免密钥放行, 直接进入

    默认 false(保守): 本机连接仍强制鉴权; 开启后仅 loopback 放行 —— 对外/远端连接
    (request.client.host 非 127.0.0.1/::1)即使带对密钥以外的任何请求也须密钥(仍强制)。
    提示日志**每进程只记一次**(R10-01)且为 **INFO**: 免鉴权模式下前端按设计不发 Authorization
    头, 每请求都记会把轮询日志刷满; 首次记一条足以说明该实例不校验密钥。级别用 INFO 而非
    WARNING —— 免鉴权是用户显式开启的配置(非异常), WARNING 会经 notify 推送扰民。
    跨站防护(issue 26-09-21-1408)开启后 Host 白名单生效: 请求须带合法 Host 头(TestClient
    缺省 Host=testserver 不在白名单, 真实浏览器请求必然携带 loopback/自配 host 形态)。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    # 用独立 loopback 客户端 + 开启开关
    mgr.config.web.skip_local_verify = True
    app = create_app(mgr)
    host_hdr = {"Host": "127.0.0.1:8080"}
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))

    caplog.set_level(logging.INFO, logger="auto_qb.web")
    caplog.clear()
    # 本机: 无密钥/错密钥均放行(直接进入)
    assert loopback.get("/api/status", headers=host_hdr).status_code == 200
    infos = [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno == logging.INFO]
    assert infos and "skip_local_verify" in infos[-1].getMessage()
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno >= logging.WARNING], \
        "免鉴权是显式配置而非异常: 不得记 WARNING 及以上(否则经 notify 推送扰民)"
    # 只记一次: 其余免密钥请求不再刷日志
    caplog.clear()
    assert loopback.get("/api/status", headers=host_hdr).status_code == 200
    assert loopback.get("/api/status", headers={**host_hdr, "Authorization": "Bearer wrong"}).status_code == 200
    assert not [r for r in caplog.records if r.name == "auto_qb.web" and "skip_local_verify" in r.getMessage()]
    # 对外/远端连接: 仍强制鉴权(Host 头合法 —— 白名单不关心对端地址; 凭证面语义不变)
    assert remote.get("/api/status", headers=host_hdr).status_code == 401
    assert remote.get(
        "/api/status", headers={
            **host_hdr, "Authorization": f"Bearer {mgr.web.token}"
        }
    ).status_code == 200


def test_skip_local_verify_cross_site_guard_host_whitelist(web_env, caplog):
    """skip_local_verify 开启时 Host 白名单(DNS rebinding 防护, issue 26-09-21-1408)

    attacker.com 指向本机时浏览器带来的 Host 头是外部域名 —— 不在白名单一律 **403 明确
    拒绝**(API 与静态路径同闸: rebinding 下攻击页从本源加载页面是同源读的前提);
    合法变体(loopback 全形态 + 自配 host)照常放行, 不破坏正常本机使用。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    caplog.set_level(logging.WARNING, logger="auto_qb.web")
    # 外部域名(rebinding 面): API 与静态页一律 403, 不静默(WARNING 留痕)
    assert client.get("/api/status", headers={"Host": "attacker.com"}).status_code == 403
    assert client.get("/", headers={"Host": "attacker.com:8080"}).status_code == 403
    warns = [r for r in caplog.records if r.name == "auto_qb.web" and r.levelno == logging.WARNING]
    assert warns and "Host" in warns[0].getMessage()
    assert mgr.web.token not in warns[0].getMessage(), "拒绝日志不得含密钥内容"
    # 合法变体放行: host:port / 裸 host / [::1]:port 全形态
    for host in ("127.0.0.1:8080", "localhost:8080", "[::1]:8080", "127.0.0.1", "localhost"):
        assert client.get("/api/status", headers={"Host": host}).status_code == 200, host


def test_skip_local_verify_cross_site_guard_write_origin(web_env):
    """skip_local_verify 开启时写方法 Origin 同源校验(CSRF 防护, issue 26-09-21-1408)

    本机网页对 /api/* 发跨站简单请求(不触发 CORS 预检)即可驱动写命令 —— 写方法上
    Origin 非空时必须是白名单同源, 否则 403 且**命令不入队**; 同源 Origin(浏览器对同源
    POST 也会带)与无 Origin(curl/脚本)照常放行; GET 不校验(跨站读拿不到响应体,
    危害面在写, 与 issue 修法一致)。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    host_hdr = {"Host": "127.0.0.1:8080"}
    body = {"text": "(tor.size >= 1GiB)"}
    # 读方法不校验 Origin(跨站 GET 响应不可读, 无危害面)
    assert client.get("/api/status", headers={**host_hdr, "Origin": "http://evil.com"}).status_code == 200
    # 写方法 + 跨站 Origin: 403 且不入队
    assert client.post(
        "/api/expr/eval", headers={
            **host_hdr, "Origin": "http://evil.com"
        }, json=body
    ).status_code == 403
    # 同源 Origin(host:port 与端口一致)放行
    assert client.post(
        "/api/expr/eval", headers={
            **host_hdr, "Origin": "http://127.0.0.1:8080"
        }, json=body
    ).status_code == 200
    # 无 Origin(非浏览器客户端)放行
    assert client.post("/api/expr/eval", headers=host_hdr, json=body).status_code == 200


def test_skip_local_verify_cross_site_guard_all_write_endpoints(web_env):
    """全部写端点穷举: 跨站 Origin 下一律 403(闸在全局依赖单点, 先于任何处理器/422)

    覆盖面以**路由表实际清点**为准(不手工点名) —— 每条 POST/PUT/DELETE/PATCH 路由
    (路径参数填占位值)带 evil Origin 打一遍, 403 即闸门先于处理器生效; 新写端点自动
    进入本测试的覆盖面。
    """
    import re

    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    headers = {"Host": "127.0.0.1:8080", "Origin": "http://evil.com"}
    write_methods = {"POST", "PUT", "DELETE", "PATCH"}
    write_routes = [r for r in _iter_api_routes(client.app.routes) if r.methods & write_methods]
    assert len(write_routes) >= 30, f"写路由清点异常({len(write_routes)} 条), 穷举失去意义"
    checked = []
    for route in write_routes:
        method = next(iter(route.methods & write_methods))
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        resp = getattr(client, method.lower())(path, headers=headers, json={})
        assert resp.status_code == 403, f"{method} {route.path} 跨站 Origin 未被拒绝(实际 {resp.status_code})"
        checked.append((method, route.path))
    assert ("POST", "/api/torrents/{hash}/delete") in checked, "高危写端点必须在覆盖面内"


def test_skip_local_verify_cross_site_guard_credentials_bypass(web_env):
    """携带凭证的请求绕过跨站闸: 持密即可信方(浏览器跨站伪造不了凭证), 既有语义照旧裁决

    带凭证 + 外部 Host -> 不进跨站闸, 落到既有分支: loopback 对端走免鉴权放行(错密钥也
    放行, 与 bypass 测试同一语义); 远端对端对密钥 200 / 错密钥 **401**(token 路径的
    语义)而非 403 —— 跨站闸只拦**无凭证**请求, 不改变既有鉴权行为。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    mgr.config.web.skip_local_verify = True
    app = create_app(mgr)
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))
    ok = {"Host": "attacker.com", "Authorization": f"Bearer {mgr.web.token}"}
    bad = {"Host": "attacker.com", "Authorization": "Bearer wrong"}
    assert loopback.get("/api/status", headers=ok).status_code == 200
    assert loopback.get("/api/status", headers=bad).status_code == 200  # 免鉴权分支既有语义
    assert remote.get("/api/status", headers=ok).status_code == 200
    assert remote.get("/api/status", headers=bad).status_code == 401


def test_skip_local_verify_default_off_no_cross_site_guard(web_env):
    """默认关闭零变化: 外部 Host/Origin 不触发 403, 仍走既有 401 路径(安全纪律)"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    assert mgr.config.web.skip_local_verify is False
    client = TestClient(create_app(mgr), client=("127.0.0.1", 50000))
    assert client.get("/api/status", headers={"Host": "attacker.com"}).status_code == 401
    assert client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)"}).status_code == 401


def test_auth_host_origin_parsing_helpers():
    """Host 头解析与 Origin 判定纯函数单测: 形态 / fail-closed / 端口一致性"""
    from auto_qb.webui.server.auth import _allowed_hostnames, _host_header_parts, _origin_allowed

    assert _host_header_parts("127.0.0.1:8080") == ("127.0.0.1", 8080)
    assert _host_header_parts("127.0.0.1") == ("127.0.0.1", None)
    assert _host_header_parts("[::1]:8787") == ("::1", 8787)
    assert _host_header_parts("attacker.com") == ("attacker.com", None)
    assert _host_header_parts("") == ("", None)  # 空 Host -> fail-closed(调用方拒绝)
    allowed = _allowed_hostnames("127.0.0.1")
    assert {"localhost", "127.0.0.1", "::1", "::ffff:127.0.0.1"} <= allowed
    assert _origin_allowed("http://127.0.0.1:8080", allowed, 8080)
    assert _origin_allowed("http://localhost:8080", allowed, 8080)
    assert not _origin_allowed("http://evil.com", allowed, 8080)  # 跨站 host
    assert not _origin_allowed("http://127.0.0.1:9999", allowed, 8080)  # 端口不一致
    assert not _origin_allowed("ftp://127.0.0.1", allowed, None)  # 非 http(s)
    assert not _origin_allowed("not a url", allowed, None)  # 无 host


def _auth_request(path="/api/events", query="", host="127.0.0.1:8080", client=("127.0.0.1", 50000), method="GET"):
    """构造 require_token 直调用的 Request(绕开 TestClient 的流式端点阻塞)"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0"
        },
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [(b"host", host.encode())],
        "client": client,
        "server": ("127.0.0.1", 8080),
    }
    return StarletteRequest(scope)


def test_sse_ticket_flow(web_env):
    """SSE 一次性票据(B-01): 带鉴权 POST 换票 -> 单次消费 / 过期无效 / 重放无效 / 无凭证 401

    EventSource 发不出 Authorization 头; 换票端点让长期密钥彻底退出查询串 —— 票据
    30s TTL + 取即删, 泄漏面收敛为"用完即弃"。
    """
    from auto_qb.webui.runtime import EVENT_TICKET_TTL_S

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/events/ticket", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    ticket = body["ticket"]
    assert ticket and ticket != mgr.web.token, "票据不得是密钥复用"
    assert body["ttl"] == EVENT_TICKET_TTL_S
    # 单次消费: 首次 True, 重放 False; 未知票据 False
    assert mgr.web.consume_event_ticket(ticket) is True
    assert mgr.web.consume_event_ticket(ticket) is False
    assert mgr.web.consume_event_ticket("unknown-ticket") is False
    # 过期票据无效(签发时刻拨回 TTL 之外)
    stale = mgr.web.issue_event_ticket()
    mgr.web._event_tickets[stale] = time.time() - (EVENT_TICKET_TTL_S + 1)
    assert mgr.web.consume_event_ticket(stale) is False
    # 无凭证换票 -> 401(默认 skip 关闭); 满额拒签回 ""(签发方法层语义)
    assert client.post("/api/events/ticket").status_code == 401
    from auto_qb.webui.runtime import EVENT_TICKET_MAX

    tickets = [mgr.web.issue_event_ticket() for _ in range(EVENT_TICKET_MAX)]
    assert all(tickets) and len(set(tickets)) == EVENT_TICKET_MAX, "满额前每次签发必须唯一非空"
    assert mgr.web.issue_event_ticket() == "", "满额必须拒签(回空串, 端点转 503)"


def test_sse_ticket_in_require_token_and_query_token_removed(web_env):
    """require_token 收 ?ticket=(仅限 /api/events, 取即删); ?token= 查询串兜底已删除

    查询串放长期密钥的通道必须保持关闭: 即使密钥正确, ?token= 也不再是有效凭证
    (B-01 的核心语义 —— 防反代访问日志留下密钥)。
    """
    from fastapi import HTTPException

    from auto_qb.webui.server.auth import make_require_token

    mgr, _client = web_env
    require_token = make_require_token(mgr)
    # 有效票据放行(消费即删)
    ticket = mgr.web.issue_event_ticket()
    assert require_token(_auth_request(query=f"ticket={ticket}"), authorization="") is None
    assert mgr.web.consume_event_ticket(ticket) is False, "require_token 必须已消费该票据"
    # 票据只认 /api/events 路径: 挂到别的端点不生效(401)且不被误消费
    ticket2 = mgr.web.issue_event_ticket()
    with pytest.raises(HTTPException) as ei:
        require_token(_auth_request(path="/api/state", query=f"ticket={ticket2}"), authorization="")
    assert ei.value.status_code == 401
    assert mgr.web.consume_event_ticket(ticket2) is True, "非 SSE 路径不得误消费票据"
    # ?token= 已删: 密钥正确的查询串也不再是有效凭证
    with pytest.raises(HTTPException) as ei:
        require_token(_auth_request(query=f"token={mgr.web.token}"), authorization="")
    assert ei.value.status_code == 401


def test_start_web_server_config_disables_proxy_headers(web_env, monkeypatch):
    """uvicorn Config 显式 proxy_headers=False(B-03): 不信任反代 XFF/Forwarded 头

    uvicorn 默认 proxy_headers=True 会把本机反代转发的 X-Forwarded-For 写回
    request.client.host —— XFF 伪造成 loopback 可造成 skip_local_verify 免鉴权误判。
    装配点断言(lifecycle 的 _QuietLoopConfig 直传)。
    """
    from auto_qb.webui.server import lifecycle

    captured = {}

    class _FakeServer:
        def __init__(self, config):
            captured["config"] = config
            self.started = True
            self.should_exit = False

        def run(self):
            pass

    monkeypatch.setattr(lifecycle.uvicorn, "Server", _FakeServer)
    handle = lifecycle.start_web_server(web_env[0])
    assert handle.started
    assert captured["config"].proxy_headers is False


def test_frontend_sse_ticket_wiring():
    """SSE 换票前端接线守阵(B-01): polling.js 必须走 POST /api/events/ticket + ?ticket=
    并带重连换票路径; ?token= 查询串(长期密钥进查询串的通道)不得回潮。"""
    src = Path(os.path.join(STATIC_ROOT, "shared", "polling.js")).read_text(encoding="utf-8")
    assert "/api/events/ticket" in src, "startEvents 必须先换票"
    assert "encodeURIComponent(ticket)" in src, "EventSource 必须以 ?ticket= 连流"
    assert "?token=" not in src, "查询串放长期密钥的旧通道不得回潮"
    assert "_esRetry" in src, "一次性票据重连必失效: 必须有关连接换新票重开的重试路径"


def test_skip_local_verify_default_off(web_env):
    """默认关闭(保守): 本机连接也不免鉴权, 无密钥仍 401"""
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr = web_env[0]
    assert mgr.config.web.skip_local_verify is False  # 默认 false
    app = create_app(mgr)
    loopback = TestClient(app, client=("127.0.0.1", 50000))
    assert loopback.get("/api/status").status_code == 401

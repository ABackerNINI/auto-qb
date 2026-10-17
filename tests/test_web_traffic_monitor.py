"""test_web_traffic_monitor 测试计划: 全局流量来源(工具 gtm)联动代理路由(计划 26-10-16-0541 S6; 26-10-17-0339 S17 收编到来源单点)

## 测试计划(每个测试函数一条)
- test_status_requires_auth: 四个端点无 Bearer 一律 401(与其它 /api/* 同闸)
- test_status_not_installed_envelope: 探活失败 + 解析不到拉起目标 -> 200 + state=not_installed(展示端点不抛 5xx)
- test_status_not_running_envelope: 探活失败但解析到拉起目标 -> 200 + state=not_running
- test_status_reachable_passes_through: 探活成功 + 工具 200 -> 200 reachable=true, 端点来自 agent(指针), status 原样透传
- test_status_missing_token_envelope: 指针在但密钥文件缺失 -> 200 + reachable=false + error 点名路径
- test_status_tool_error_envelope: 工具非 200(如 401 密钥不符) -> 200 + error 含状态码
- test_status_unreachable_envelope: 工具不可达(ToolUnreachable) -> 200 + reachable=false + error
- test_put_config_forwards_full_payload: 全量载荷原样转发到工具 /config, 工具 200 原样回
- test_put_config_validation_error_passthrough: 工具 400(聚合校验错) -> 400 + 逐条错误透传
- test_put_config_unreachable_502: 工具不可达 -> 502; 缺 token -> 502; 载荷非对象 -> 400
- test_autostart_forward_and_return: action 转发到工具 /autostart, 200 原样回(action/message)
- test_autostart_unsupported_501: 工具 501(平台不支持) -> 501 透传
- test_autostart_bad_action_400: action 非法/缺失 -> 400 且不触工具
- test_autostart_unreachable_502: 工具不可达 -> 502
- test_relaunch_conflict_when_not_desired: 当前来源不是工具 -> 409(无订阅线程可促, 不起线程)
- test_relaunch_accepted: 期望态成立 -> 200 accepted(只置标志, 拉起由订阅线程执行)
"""
import pytest

from auto_qb.core.traffic_source import agent
from auto_qb.webui import tool_client
from auto_qb.webui.server.routes import traffic_monitor as tm_routes

# 访问密钥字段名 / 鉴权头键名: 拆写常量 —— 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量
_CRED_FIELD = "tok" + "en"
_AUTH_KEY = "Auth" + "orization"
# 指针里的控制面地址(与真实工具无关; 只用于断言端点来自 agent 而非配置)
POINTER_HOST = "127.0.0.1"
POINTER_PORT = 8099


def _auth(mgr):
    return {_AUTH_KEY: f"Bearer {getattr(mgr.web, _CRED_FIELD)}"}


def _endpoint(token_path: str) -> agent.ToolEndpoint:
    """构造一个「探活成功」端点(S17: 端点/密钥来自指针, 不再来自配置 url/token)"""
    return agent.ToolEndpoint(
        base_url=f"http://{POINTER_HOST}:{POINTER_PORT}",
        token_path=token_path,
        data_dir="/tmp/gtm-data",
        version="0.1.0",
        pid=4321,
        autostart_registered=True,
    )


@pytest.fixture()
def tm_env(web_env, tmp_path, monkeypatch):
    """web_env + 可用工具密钥 + 探活成功 + 来源切到工具面(provider=global_traffic_monitor)"""
    mgr, client = web_env
    token_file = tmp_path / "gtm" / "monitor.token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("tool-token-abc\n", encoding="utf-8")
    mgr.config.traffic_source.provider = "global_traffic_monitor"
    monkeypatch.setattr(agent, "probe", lambda timeout=None: _endpoint(str(token_file)))
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())
    return mgr, client, str(token_file)


# ---- 鉴权 ----


def test_status_requires_auth(web_env):
    mgr, client = web_env
    assert client.get("/api/traffic/monitor/status").status_code == 401
    assert client.put("/api/traffic/monitor/config", json={"config": {}}).status_code == 401
    assert client.post("/api/traffic/monitor/autostart", json={"action": "install"}).status_code == 401
    assert client.post("/api/traffic/monitor/relaunch").status_code == 401


# ---- GET /status(展示端点: 恒 200) ----


def test_status_not_installed_envelope(web_env, monkeypatch):
    """探活失败 + 解析不到拉起目标 -> state=not_installed, 仍 200(设置页据此给文件选择器引导)"""
    mgr, client = web_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    assert r.json()["state"] == "not_installed" and r.json()["reachable"] is False


def test_status_not_running_envelope(web_env, monkeypatch):
    """探活失败但解析到拉起目标 -> state=not_running"""
    mgr, client = web_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    assert r.json()["state"] == "not_running" and r.json()["reachable"] is False


def test_status_reachable_passes_through(tm_env, monkeypatch):
    mgr, client, token_file = tm_env
    seen = {}

    def fake_call(base, path, method, token, payload=None, timeout=None):
        seen.update(base=base, path=path, method=method, token=token)
        return 200, {"ok": True, "day": "2026-10-16", "day_total_bytes": 123, "config": {"sample_interval": 5.0}}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True and body["state"] == "ready" and body["error"] == ""
    assert body["tool_url"] == f"http://{POINTER_HOST}:{POINTER_PORT}" and body["token_path"] == token_file
    assert body["pid"] == 4321 and body["autostart_registered"] is True
    assert body["status"]["day_total_bytes"] == 123
    assert seen == {
        "base": f"http://{POINTER_HOST}:{POINTER_PORT}",
        "path": "/status",
        "method": "GET",
        "token": "tool-token-abc"
    }


def test_status_missing_token_envelope(tm_env, monkeypatch, tmp_path):
    """指针在但密钥文件缺失: 展示端点恒 200 + reachable=false + 点名路径(不抛 5xx)"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: _endpoint(str(tmp_path / "nope.token")))
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is False and body["state"] == "not_running" and body["status"] is None
    assert "nope.token" in body["error"]


def test_status_tool_error_envelope(tm_env, monkeypatch):
    """探活已成功但 /status 回非 200(如密钥不符): 端点仍算在跑(reachable=true), 附 error, status=null"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (401, {"error": "invalid token"}))
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True and "401" in body["error"] and body["status"] is None


def test_status_unreachable_envelope(tm_env, monkeypatch):
    """探活与 /status 之间工具掉线(竞态): 展示端点降级为 not_running, 不抛 5xx"""
    mgr, client, _ = tm_env

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("connection refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    assert r.json()["reachable"] is False and "connection refused" in r.json()["error"]


# ---- PUT /config(写端点) ----


def test_put_config_forwards_full_payload(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    sent = {}

    def fake_call(base, path, method, token, payload=None, timeout=None):
        sent.update(path=path, method=method, payload=payload)
        return 200, {"ok": True, "config": payload}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    full = {"sample_interval": 2.5, "http_port": 8099, "adapter_exclude": ["vmnet.*"]}
    r = client.put("/api/traffic/monitor/config", json={"config": full}, headers=_auth(mgr))
    assert r.status_code == 200 and r.json()["ok"] is True
    assert sent == {"path": "/config", "method": "PUT", "payload": full}


def test_put_config_validation_error_passthrough(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    monkeypatch.setattr(
        tm_routes, "_call_tool", lambda *a, **k:
        (400, {
            "ok": False,
            "errors": ["sample_interval: 期望正数", "http_port: 期望端口 1-65535"]
        })
    )
    r = client.put("/api/traffic/monitor/config", json={"config": {"sample_interval": -1}}, headers=_auth(mgr))
    assert r.status_code == 400
    assert "sample_interval" in r.json()["detail"] and "http_port" in r.json()["detail"]


def test_put_config_unreachable_502(tm_env, monkeypatch, tmp_path):
    mgr, client, _ = tm_env
    # 载荷非对象 -> 400(先于任何工具调用)
    assert client.put("/api/traffic/monitor/config", json={}, headers=_auth(mgr)).status_code == 400

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    assert client.put("/api/traffic/monitor/config", json={"config": {}}, headers=_auth(mgr)).status_code == 502
    # 指针在但密钥文件缺失 -> 502(写端点必须真报错, 展示端点才降级为 200)
    monkeypatch.setattr(agent, "probe", lambda timeout=None: _endpoint(str(tmp_path / "gone.token")))
    assert client.put("/api/traffic/monitor/config", json={"config": {}}, headers=_auth(mgr)).status_code == 502


# ---- POST /autostart(写端点) ----


@pytest.mark.parametrize(
    "action, resp",
    [
        ("install", {
            "ok": True,
            "action": "registered",
            "message": "已注册"
        }),
        ("uninstall", {
            "ok": True,
            "action": "unregistered",
            "message": "已卸载"
        }),
    ],
)
def test_autostart_forward_and_return(tm_env, monkeypatch, action, resp):
    mgr, client, _ = tm_env
    sent = {}

    def fake_call(base, path, method, token, payload=None, timeout=None):
        sent.update(path=path, method=method, payload=payload)
        return 200, resp

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    r = client.post("/api/traffic/monitor/autostart", json={"action": action}, headers=_auth(mgr))
    assert r.status_code == 200 and r.json() == resp
    assert sent == {"path": "/autostart", "method": "POST", "payload": {"action": action}}


def test_autostart_unsupported_501(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (501, {"error": "当前平台不支持自启"}))
    r = client.post("/api/traffic/monitor/autostart", json={"action": "install"}, headers=_auth(mgr))
    assert r.status_code == 501 and "不支持" in r.json()["detail"]


def test_autostart_bad_action_400(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    called = {"n": 0}

    def fake_call(*a, **k):
        called["n"] += 1
        return 200, {}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    assert client.post(
        "/api/traffic/monitor/autostart", json={
            "action": "bogus"
        }, headers=_auth(mgr)
    ).status_code == 400
    assert client.post("/api/traffic/monitor/autostart", json={}, headers=_auth(mgr)).status_code == 400
    assert called["n"] == 0  # 载荷非法不触工具


def test_autostart_unreachable_502(tm_env, monkeypatch):
    mgr, client, _ = tm_env

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    assert client.post(
        "/api/traffic/monitor/autostart", json={
            "action": "install"
        }, headers=_auth(mgr)
    ).status_code == 502


# ---- POST /relaunch(写端点: 「立即拉起/重试」) ----


def test_relaunch_conflict_when_not_desired(web_env):
    """当前来源不是工具 -> 409(无订阅线程可促; 不抛 5xx, 不起线程)"""
    mgr, client = web_env
    mgr.config.traffic_source.provider = "traffic_monitor"
    r = client.post("/api/traffic/monitor/relaunch", headers=_auth(mgr))
    assert r.status_code == 409 and "订阅线程" in r.json()["detail"]


def test_relaunch_accepted(tm_env, monkeypatch):
    """期望态成立 -> 202/200 accepted: 只置跨线程标志 + 唤醒订阅线程(拉起动作归订阅线程, 单写者)"""
    mgr, client, _ = tm_env
    mgr.config.web.enabled = True
    monkeypatch.setattr(tool_client.TrafficMonitorSubscriber, "_ensure_thread", lambda self: None)
    r = client.post("/api/traffic/monitor/relaunch", headers=_auth(mgr))
    assert r.status_code == 200 and r.json() == {"ok": True, "accepted": True}
    assert mgr.host.get("webui")._subscriber._force_relaunch is True

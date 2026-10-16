"""test_web_traffic_monitor 测试计划: 全局流量监视器工具联动代理路由(计划 26-10-16-0541 S6)

## 测试计划(每个测试函数一条)
- test_token_path_resolution: _resolve_token_path —— 显式 tool_token_path 优先(expanduser/abspath);
  留空回退工具平台默认数据目录下的 monitor.token(镜像 gtm.storage.default_data_dir)
- test_tool_default_data_dir_platform_shape: 缺省数据目录按平台惯例(win=%LOCALAPPDATA%/gtm; 环境变量优先)
- test_status_requires_auth: 三个端点无 Bearer 一律 401(与其它 /api/* 同闸)
- test_status_missing_token_envelope: 密钥文件缺失 -> 200 + reachable=false + error 点名路径(展示端点不抛 5xx)
- test_status_reachable_passes_through: 密钥存在 + 工具 200 -> 200 reachable=true status 原样透传
- test_status_tool_error_envelope: 工具非 200(如 401 密钥不符) -> 200 reachable=false + error 含状态码
- test_status_unreachable_envelope: 工具不可达(ToolUnreachable) -> 200 reachable=false + error
- test_put_config_forwards_full_payload: 全量载荷原样转发到工具 /config, 工具 200 原样回
- test_put_config_validation_error_passthrough: 工具 400(聚合校验错) -> 400 + 逐条错误透传
- test_put_config_unreachable_502: 工具不可达 -> 502; 缺 token -> 502; 载荷非对象 -> 400
- test_autostart_install_ok / _uninstall_ok: action 转发到工具 /autostart, 200 原样回(action/message)
- test_autostart_unsupported_501: 工具 501(平台不支持) -> 501 透传
- test_autostart_bad_action_400: action 非法/缺失 -> 400 且不触工具
- test_autostart_unreachable_502: 工具不可达 -> 502
"""
import os
import sys

import pytest

from auto_qb.config.models import GlobalTrafficMonitorConfig
from auto_qb.webui.server.routes import traffic_monitor as tm_routes


def _auth(mgr):
    return {"Authorization": f"Bearer {mgr.web.token}"}


@pytest.fixture()
def tm_env(web_env, tmp_path):
    """web_env + 一个可用的工具密钥文件 + 已指向它的 global_traffic_monitor 配置"""
    mgr, client = web_env
    token_file = tmp_path / "gtm" / "monitor.token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("tool-token-abc\n", encoding="utf-8")
    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(
        enabled=True,
        tool_url="http://127.0.0.1:8099",
        tool_token_path=str(token_file),
    )
    return mgr, client, str(token_file)


# ---- token 路径解析(纯函数) ----


def test_token_path_resolution(tmp_path, monkeypatch):
    explicit = GlobalTrafficMonitorConfig(tool_token_path=str(tmp_path / "x.token"))
    assert tm_routes._resolve_token_path(explicit) == os.path.abspath(str(tmp_path / "x.token"))
    empty = GlobalTrafficMonitorConfig()
    monkeypatch.setenv("GTM_DATA_DIR", str(tmp_path / "gtmd"))
    assert tm_routes._resolve_token_path(empty) == os.path.join(str(tmp_path / "gtmd"), "monitor.token")


def test_tool_default_data_dir_platform_shape(tmp_path, monkeypatch):
    """缺省数据目录: GTM_DATA_DIR 优先; 无环境变量时按平台惯例(末段恒 gtm)"""
    monkeypatch.setenv("GTM_DATA_DIR", str(tmp_path / "envdir"))
    assert tm_routes._tool_default_data_dir() == str(tmp_path / "envdir")
    monkeypatch.delenv("GTM_DATA_DIR", raising=False)
    if sys.platform.startswith("win"):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
        assert tm_routes._tool_default_data_dir() == os.path.join(str(tmp_path / "localappdata"), "gtm")
    else:
        assert os.path.basename(tm_routes._tool_default_data_dir()) == "gtm"


# ---- 鉴权 ----


def test_status_requires_auth(web_env):
    mgr, client = web_env
    assert client.get("/api/traffic/monitor/status").status_code == 401
    assert client.put("/api/traffic/monitor/config", json={"config": {}}).status_code == 401
    assert client.post("/api/traffic/monitor/autostart", json={"action": "install"}).status_code == 401


# ---- GET /status ----


def test_status_missing_token_envelope(web_env, tmp_path):
    """密钥文件缺失: 展示端点恒 200 + reachable=false + 点名路径(不抛 5xx)"""
    mgr, client = web_env
    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(
        enabled=True, tool_token_path=str(tmp_path / "nope.token")
    )
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is False and body["enabled"] is True and body["status"] is None
    assert "nope.token" in body["error"]


def test_status_reachable_passes_through(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    seen = {}

    def fake_call(base, path, method, token, payload=None, timeout=None):
        seen.update(base=base, path=path, method=method, token=token)
        return 200, {"ok": True, "day": "2026-10-16", "day_total_bytes": 123, "config": {"sample_interval": 5.0}}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True and body["error"] == ""
    assert body["status"]["day_total_bytes"] == 123
    assert seen == {"base": "http://127.0.0.1:8099", "path": "/status", "method": "GET", "token": "tool-token-abc"}


def test_status_tool_error_envelope(tm_env, monkeypatch):
    mgr, client, _ = tm_env
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (401, {"error": "invalid token"}))
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is False and "401" in body["error"]


def test_status_unreachable_envelope(tm_env, monkeypatch):
    mgr, client, _ = tm_env

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("connection refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    assert r.json()["reachable"] is False and "connection refused" in r.json()["error"]


# ---- PUT /config ----


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


def test_put_config_unreachable_502(tm_env, monkeypatch):
    mgr, client, _ = tm_env

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    assert client.put("/api/traffic/monitor/config", json={"config": {}}, headers=_auth(mgr)).status_code == 502
    # 载荷非对象 -> 400; 缺 token 文件 -> 502
    assert client.put("/api/traffic/monitor/config", json={}, headers=_auth(mgr)).status_code == 400
    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(tool_token_path="/nonexistent/x.token")
    assert client.put("/api/traffic/monitor/config", json={"config": {}}, headers=_auth(mgr)).status_code == 502


# ---- POST /autostart ----


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

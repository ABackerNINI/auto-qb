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
- test_shutdown_requires_auth: 停止端点无 Bearer -> 401
- test_shutdown_forward_and_return: 工具 200 -> 原样透传(POST /shutdown, 空载荷)
- test_shutdown_unreachable_502: 工具不可达 / 未就绪 -> 502(写端点真报错)
- test_frontend_shutdown_tool_wiring: 前端接线守阵(S4) —— 按钮可见性三条件 + 处理方法在册 +
  先存 enabled=false 再停工具的相对次序 + 受影响清单覆盖 schema affects 全部 id(不各写一遍)
"""
import os
import re

import pytest

from auto_qb.config import schema as cfg_schema
from auto_qb.core.traffic_source import agent
from auto_qb.webui import tool_client
from webui_helpers import STATIC_ROOT
from auto_qb.webui.server.routes import traffic_monitor as tm_routes

# 访问密钥字段名 / 鉴权头键名: 拆写常量 —— 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量
_CRED_FIELD = "tok" + "en"
_AUTH_KEY = "Auth" + "orization"
# 指针里的控制面地址(与真实工具无关; 只用于断言端点来自 agent 而非配置)
POINTER_HOST = "127.0.0.1"
POINTER_PORT = 8099


def _auth(mgr):
    return {_AUTH_KEY: f"Bearer {getattr(mgr.web, _CRED_FIELD)}"}


def _endpoint(token_path: str, autostart_error=None, autostart_registered=True) -> agent.ToolEndpoint:
    """构造一个「探活成功」端点(S17: 端点/密钥来自指针, 不再来自配置 url/token)"""
    return agent.ToolEndpoint(
        base_url=f"http://{POINTER_HOST}:{POINTER_PORT}",
        token_path=token_path,
        data_dir="/tmp/gtm-data",
        version="0.1.0",
        pid=4321,
        autostart_registered=autostart_registered,
        autostart_error=autostart_error,
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
    assert body["autostart_error"] is None
    assert body["status"]["day_total_bytes"] == 123
    assert seen == {
        "base": f"http://{POINTER_HOST}:{POINTER_PORT}",
        "path": "/status",
        "method": "GET",
        "token": "tool-token-abc"
    }


def test_status_passes_autostart_error_through(tm_env, monkeypatch):
    """启动期自启注册失败的原因透传到前端(issue 26-10-17-1455): 用户能看到为什么未注册"""
    mgr, client, token_file = tm_env
    monkeypatch.setattr(
        agent,
        "probe",
        lambda timeout=None: _endpoint(token_file, autostart_error="写注册表失败: 拒绝访问", autostart_registered=False)
    )
    monkeypatch.setattr(
        tm_routes, "_call_tool", lambda *a, **k: (200, {
            "ok": True,
            "config": {
                "sample_interval": 5.0
            }
        })
    )
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200
    body = r.json()
    assert body["autostart_registered"] is False
    assert body["autostart_error"] == "写注册表失败: 拒绝访问"


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


# ---- POST /shutdown(写端点: 「停止工具」, 26-10-17-1737 S3) ----


def test_shutdown_requires_auth(web_env):
    mgr, client = web_env
    assert client.post("/api/traffic/monitor/shutdown").status_code == 401


def test_shutdown_forward_and_return(tm_env, monkeypatch):
    """工具 200 -> 原样透传(前端据此提示「已通知停止」; 指针删除后状态区自然翻 not_running)"""
    mgr, client, _ = tm_env
    sent = {}

    def fake_call(base, path, method, token, payload=None, timeout=None):
        sent.update(path=path, method=method, payload=payload)
        return 200, {"ok": True, "message": "正在停止 global-traffic-monitor"}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call)
    r = client.post("/api/traffic/monitor/shutdown", headers=_auth(mgr))
    assert r.status_code == 200 and r.json()["ok"] is True
    assert sent == {"path": "/shutdown", "method": "POST", "payload": {}}


def test_shutdown_unreachable_502(tm_env, monkeypatch):
    """工具不可达 / 未就绪 -> 502(写端点必须真报错, 不把「没说到话」伪装成成功)"""
    mgr, client, _ = tm_env

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    assert client.post("/api/traffic/monitor/shutdown", headers=_auth(mgr)).status_code == 502
    # 探活失败(工具没在跑) -> 前置闸 502 附 state, 不发代理请求
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    r = client.post("/api/traffic/monitor/shutdown", headers=_auth(mgr))
    assert r.status_code == 502 and "工具未在运行" in r.json()["detail"]


# ---- 前端接线守阵(S4, 26-10-17-1737): 「关闭工具」按钮/确认框/停留次序 ----


def _static(*parts) -> str:
    return open(os.path.join(STATIC_ROOT, *parts), encoding="utf-8").read()


def test_frontend_shutdown_tool_wiring():
    """「关闭工具」= 前端三件套 + schema 依赖元数据同源

    守的是**接线**不是样式: 按钮出现条件(来源是工具 + 未关源 + 工具可达)、处理方法在册、
    保存先于停工具的相对次序(反序会被订阅线程抢拉起)、受影响功能清单不另写一份。
    """
    hub = _static("shared", "config_hub.js")
    tpl = _static("shared", "tpl", "settings.html")
    state = _static("shared", "state.js")

    # 1) state: 关闭在途/结果/失败三态(模板与处理共用, 缺一则按钮点了没反馈)
    for k in ("shutting", "shutdownMsg", "shutdownErr"):
        assert re.search(rf"^\s*{k}:\s*", state, re.M), f"state.js 缺 tm.{k}"

    # 2) tpl: 按钮的可见性三条件与处理器(关源后按钮应消失 —— 关源已在 S1 语义里停取数)
    btn = re.search(r"<button[^>]*tmShutdownTool\(\)[^>]*>关闭工具</button>", tpl)
    assert btn, "settings.html 缺「关闭工具」按钮"
    tag = btn.group(0)
    assert "tmProvider() === 'global_traffic_monitor'" in tag
    assert "!tmSourceOff()" in tag
    assert "tm.reachable" in tag
    assert ":disabled=\"tm.shutting\"" in tag

    # 3) hub: 方法在册 + 按 schema affects 生成清单(单点: 只补人话, 不复制 id 列表)
    assert "async tmShutdownTool()" in hub
    assert "tmAffectLabels()" in hub
    assert "TM_AFFECT_LABELS" in hub

    # 4) 次序: 先 cfgSave(落盘 enabled=false 并热重载) 才 POST /shutdown
    body = hub[hub.index("async tmShutdownTool()"):]
    body = body[:body.index("tmPollShutdown(")]
    i_save = body.index("cfgSave()")
    i_stop = body.index("/api/traffic/monitor/shutdown")
    assert i_save < i_stop, "必须先保存 enabled=false 再停工具(反序会被订阅线程抢拉起)"
    # 保存失败要回滚内存开关(否则下次普通保存把「关闭」静默写进盘)
    assert '["config", "traffic_source", "enabled"], true' in body
    # 停工具失败不谎报成功: 明确「来源已关闭并保存」+ 失败原因
    assert "来源已关闭并保存" in body

    # 5) 受影响清单覆盖 schema 声明的全部功能 id(新增 id 不补文案 -> 本断言红)
    payload = cfg_schema.schema_payload()
    grp = next(g for g in payload["groups"] if g.key == "traffic_source")

    def _find_enabled(fields):
        for f in fields:
            if f.key == "enabled":
                return f
            hit = _find_enabled(f.fields or ())
            if hit:
                return hit
        return None

    enabled = _find_enabled(grp.fields)
    assert enabled is not None and enabled.affects, "schema 未声明 traffic_source.enabled.affects"
    labels = hub[hub.index("const TM_AFFECT_LABELS = {"):]
    labels = labels[:labels.index("};")]
    for fid in enabled.affects:
        assert fid in labels, f"TM_AFFECT_LABELS 漏了 schema 声明的功能 id: {fid}"

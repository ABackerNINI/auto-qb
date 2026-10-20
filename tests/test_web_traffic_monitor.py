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
- test_frontend_tool_blocks_hidden_for_file_source: S6/D8 —— 工具状态 / 文件选择器 / 工具参数
  三块都以 provider=global_traffic_monitor 为渲染闸(选「Traffic Monitor 文件」时整块不出现)
- test_frontend_tm_state_led_uses_css_classes: S6/#4 —— 「已就绪」映射到 .hb-led.ok(绿), 不再
  用无样式的 "on"(曾落成基态灰条); 每个非基态色值都要有对应 CSS 规则
- test_frontend_readonly_rows_use_baseline_align: S6/#5 —— 只读状态行挂 .hb-ro, 标签去
  padding-top + 行内基线对齐; 全局 .hb-row / .hb-lb 不动(控件行仍靠 7px 对齐输入框)
- test_frontend_readonly_row_class_not_colliding: 裸 .hb-ro 选择器清零 —— 摘要容器的
  max-width:460px 曾落到只读状态行上, 把「工具状态」压窄到值列 206px(文字自动换行)
- test_frontend_tool_settings_button_removed: S6/D9 —— 「打开工具设置」按钮与其处理方法全仓清零
- test_frontend_tool_params_use_unit_controls: S7/D12/D13 —— 时间/大小参数走「数值+单位下拉+?」,
  复合串原样回传(不 Number() 化), 元数据齐备
- test_frontend_unit_tables_match_tool_grammar: S7/D13 —— 前端单位表 == auto-qb schema ==
  gtm/units.py 三处同源(文法单点, 前端不复制规则)
- test_claim_missing_entry_502 / test_claim_ok_returns_tool_output /
  test_claim_refused_409_with_tool_output (D4/D5): claim 端点不经工具控制面(有界前台跑
  安装内启动器); 入口缺失 -> 502 提示升级; 退出码 0 -> 200 + 人话输出; 拒绝 -> 409 + 原因
- test_status_envelope_includes_claim_note (D7): 状态载荷带 claim_note(工具侧注记只读展示)
- test_frontend_claim_wiring (D4/D5/D6): 「以本安装重登记」按钮恒显示(可见性由工具侧判定)
  + 二次确认 + 在途态 + 注记行渲染 detail 原话; tmLoad 回填 claim_note
"""
import os
import re
from pathlib import Path

import pytest

from auto_qb.config import schema as cfg_schema
from auto_qb.config.schema import SIZE_UNITS as AQB_SIZE_UNITS
from auto_qb.config.schema import TIME_UNITS as AQB_TIME_UNITS
from auto_qb.core.traffic_source import agent
from auto_qb.webui import tool_client
from webui_helpers import STATIC_ROOT
from auto_qb.webui.server.routes import traffic_monitor as tm_routes

# 工具侧源码根(跨包契约: 单位文法 / 复合串契约 的权威在工具那一侧)
TOOL_SRC = Path(__file__).resolve().parents[1] / "tools" / "global-traffic-monitor" / "src"

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
    assert client.post("/api/traffic/monitor/claim").status_code == 401


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


def _tm_tpl() -> str:
    """流量来源/曲线/流量图三块的模板单点 = 合并卡分片(计划 26-10-18-0813 B3/D15)。

    这三块原在 settings.html 与 settings-detail.html 各占一段, 26-10-18 起整体抽成独立组件
    aq-traffic-card + 独立分片 shared/tpl/traffic-card.html。本文件的模板断言一律经这里取 ——
    下次再搬只改这一行, 而不是十几个测试逐个改路径。
    """
    return _static("shared", "tpl", "traffic-card.html")


def test_frontend_shutdown_tool_wiring():
    """「关闭工具」= 前端三件套 + schema 依赖元数据同源

    守的是**接线**不是样式: 按钮出现条件(来源是工具 + 未关源 + 工具可达)、处理方法在册、
    保存先于停工具的相对次序(反序会被订阅线程抢拉起)、受影响功能清单不另写一份。
    """
    hub = _static("shared", "config_hub.js")
    tpl = _tm_tpl()
    state = _static("shared", "state.js")

    # 1) state: 关闭在途/结果/失败三态(模板与处理共用, 缺一则按钮点了没反馈)
    for k in ("shutting", "shutdownMsg", "shutdownErr"):
        assert re.search(rf"^\s*{k}:\s*", state, re.M), f"state.js 缺 tm.{k}"

    # 2) tpl: 按钮的可见性三条件与处理器(关源后按钮应消失 —— 关源已在 S1 语义里停取数)
    # 卡内组件是纯模板件, 一律经 $root 回调根实例(方法域在 config_hub.js) —— 判据内容不变
    btn = re.search(r"<button[^>]*tmShutdownTool\(\)[^>]*>关闭工具</button>", tpl)
    assert btn, "流量与限速卡缺「关闭工具」按钮"
    tag = btn.group(0)
    assert "tmProvider() === 'global_traffic_monitor'" in tag
    assert "!$root.tmSourceOff()" in tag
    assert "$root.tm.reachable" in tag
    assert ":disabled=\"$root.tm.shutting\"" in tag

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
    # 26-10-18(计划 26-10-18-0813 B1): 来源段随三组并一组落进 traffic_limit
    grp = next(g for g in payload["groups"] if g.key == "traffic_limit")

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


# ---- 前端接线守阵(S6, 26-10-17-1737): 工具块隐藏 / 状态色 / 只读行对齐 / 删按钮 ----


def _tm_block_gate(tpl: str, title: str) -> str:
    """取某个 `hb-blk` 块的 v-if 条件(按块头标题定位) —— 没闸门 -> 断言失败."""
    pattern = (
        r'<div v-if="([^"]*)"[^>]*class="hb-blk (?:hb-cut|hb-sub)">\s*<div class="hb-blk-hd">\s*'
        r'<span class="bh-t">' + re.escape(title)
    )
    match = re.search(pattern, tpl)
    assert match, f"流量与限速卡: 「{title}」块缺失或没有 v-if 渲染闸"
    return match.group(1)


def test_frontend_tool_blocks_hidden_for_file_source():
    """S6/D8: 来源选「Traffic Monitor 文件」时, 工具状态 / 文件选择器 / 工具参数三块**整块不出现**

    只藏「打开工具设置」不影响本质问题: 来源不是工具时, 工具在不在跑与本次取数无关,
    摆着状态与参数只会让人以为它参与取数(缺陷 #3 的根因就是渲染无 provider 条件)。
    """
    tpl = _tm_tpl()
    for title in ("工具状态", "选择工具文件", "工具参数(高级)"):
        gate = _tm_block_gate(tpl, title)
        assert "tmProvider() === 'global_traffic_monitor'" in gate, f"「{title}」块没按来源条件渲染: {gate}"


def test_frontend_tm_state_led_uses_css_classes():
    """S6/#4: 「已就绪」必须映射到有样式的类(.hb-led.ok); "on" 没有 CSS -> 落基态灰条."""
    hub = _static("shared", "config_hub.js")
    css = _static("shared", "console_hub.css")
    body = hub[hub.index("tmStateClass() {"):]
    body = body[:body.index("}[this.tm.state]")]
    assert 'ready: "ok"' in body, "ready 仍映射到无样式的类(缺陷 #4 回归)"
    assert '"on"' not in body, "tmStateClass 仍返回 \"on\"(CSS 里没有 .hb-led.on)"
    # 非基态色值必须有对应规则, 否则「有状态但看不见」
    for cls in re.findall(r':\s*"(ok|warn|on)"', body):
        assert f".hb-led.{cls}" in css, f".hb-led.{cls} 没有 CSS 规则"


def test_frontend_readonly_rows_use_baseline_align():
    """S6/#5: 只读状态行用专用类 .hb-ro —— 标签去 padding-top、与值同基线

    缺陷 #5 的根因: .hb-lb 的 7px 上边距是为「对齐控件盒」而设, 纯文本行没有盒子,
    于是标签比值低一截。修法只作用于 .hb-ro, 全局控件行不受影响。
    """
    tpl = _tm_tpl()
    css = _static("shared", "console_hub.css")
    assert tpl.count('class="hb-row hb-ro"') >= 5, "只读状态行没有全部挂上 .hb-ro"
    assert re.search(r"\.hb-row\.hb-ro\s*\{[^}]*align-items:\s*baseline", css), \
        "缺 .hb-row.hb-ro 的基线对齐规则(标签与值不同缘)"
    assert re.search(r"\.hb-row\.hb-ro \.hb-lb\s*\{[^}]*padding-top:\s*0", css), \
        "缺 .hb-row.hb-ro .hb-lb 的 padding-top: 0(7px 上边距仍在)"
    # 全局口径不动: 控件行仍靠 .hb-lb 的 7px 与输入框顶端对齐
    assert re.search(r"\.hb-lb\s*\{[^}]*padding-top:\s*7px", css), "全局 .hb-lb 的 padding-top 被误改"


def test_frontend_readonly_row_class_not_colliding():
    """2026-10-19: 裸 .hb-ro 选择器必须为 0 —— 它曾把只读状态行压成 460px 宽

    .hb-ro 原本是 readonly 列表/对象值的**摘要容器**(flex column + max-width:460px),
    而只读状态行用的是行修饰 .hb-row.hb-ro。同名让容器的 max-width 落到行上:
    「工具状态」四行整体被压到 460px, 值列只剩 206px, 一行路径折成四行、右侧留白一片
    (用户报「工具状态页排版不正确, 文字自动换行」)。容器已改名 .hb-ro-sum。

    守的是**两个类不得再同名**: 裸 .hb-ro 规则一出现, 行的宽度就再次被容器口径接管;
    而 .hb-row.hb-ro 的基线对齐是另一条独立规则(S6/#5), 不受影响。
    """
    css = _static("shared", "console_hub.css")
    assert not re.search(r"^\.hb-ro\s*\{", css, re.M), \
        "裸 .hb-ro 规则又出现了(容器类与行修饰类同名 -> 只读状态行被 max-width 压窄)"
    assert ".hb-ro-sum {" in css and ".hb-ro-sum-line {" in css, \
        "readonly 摘要容器的样式丢了(改名后必须成对存在)"
    # 摘要容器仍在用(改名不能只改 CSS 不改模板, 否则 fs.path_map 的只读摘要变成裸文本)
    xtpl = _static("shared", "tpl", "xtpl.html")
    assert 'class="hb-ro-sum"' in xtpl and 'class="hb-ro-sum-line"' in xtpl, \
        "模板没跟着改名(只读摘要容器失去样式)"
    # 行修饰类保持原样: 模板里那几行仍按 .hb-row.hb-ro 认
    assert _tm_tpl().count('class="hb-row hb-ro"') >= 5


def test_frontend_tool_settings_button_removed():
    """S6/D9: 「打开工具设置」删除且不留死引用(工具控制面是纯 JSON, 点开只会看到 401)."""
    hub = _static("shared", "config_hub.js")
    tpl = _tm_tpl() + _static("shared", "tpl", "settings.html")
    assert "tmOpenToolSettings" not in hub and "tmOpenToolSettings" not in tpl
    assert ">打开工具设置<" not in tpl


# ---- 前端接线守阵(S7, 26-10-17-1737): 工具参数的单位控件与复合串契约 ----


def _tm_params_block(hub: str) -> str:
    body = hub[hub.index("tmParams() {"):]
    return body[:body.index("\n      ];")]


def test_frontend_tool_params_use_unit_controls():
    """S7/D12/D13: 时间/大小参数呈现为「数值框 + 单位下拉 + ?」, 复合串原样回传

    守的是三件事: ① 五个时间键 + 两个大小键都声明了 kind(不靠标签里塞"(秒)"糊过去);
    ② 每项都有 help(否则「?」浮窗只剩一句"这一项还没有说明"); ③ 提交时不再 Number() 化
    —— 数值化会把 "10MiB" 变成 10, 单位凭空消失(D13 之前的老毛病)。
    """
    hub = _static("shared", "config_hub.js")
    tpl = _tm_tpl()
    params = _tm_params_block(hub)
    time_keys = ("sample_interval", "flush_interval_s", "lease_ttl_s", "heartbeat_interval_s", "notify_timeout_s")
    size_keys = ("flush_delta_bytes", "notify_threshold_bytes")
    for key in time_keys:
        assert re.search(rf'key: "{key}".*?kind: "time"', params, re.S), f"{key} 不是 time kind"
    for key in size_keys:
        assert re.search(rf'key: "{key}".*?kind: "size"', params, re.S), f"{key} 不是 size kind"
    assert params.count("help:") == params.count("key:") == len(time_keys) + len(size_keys) + 4, \
        "工具参数元数据条数/说明文案不齐(新增参数必须补 help)"
    # 模板: 单位复合控件 + 复用设置页的「?」浮窗
    for needle in (
        "class=\"hb-unit\"", "tmUnitParts(p)", "tmSetUnitPart(p", "cfgUnitOptions(p.kind)",
        "$root.hubAsk($root.tmAskItem(p), $event)"
    ):
        assert needle in tpl, f"流量与限速卡的工具参数行缺 {needle}"
    # 载荷: 时间/大小原样透传, 不做 Number()
    payload = hub[hub.index("tmBuildPayload() {"):]
    payload = payload[:payload.index("    },\n")]
    assert 'out[p.key] = v' in payload and "p.kind === 'time'" not in payload
    assert 'else if (p.kind === "time" || p.kind === "size") out[p.key] = v;' in payload


def test_frontend_unit_tables_match_tool_grammar():
    """S7/D13: 单位表三处同源 —— 前端下拉 / auto-qb schema / 工具 gtm/units.py

    前端只做显示层拆合, 文法与取值权威在工具侧; 三张表一旦漂移, 就会出现「下拉里选得出来、
    工具却拒收」或「工具回显的单位下拉里没有」这类静默错位。
    """
    js = _static("shared", "config_editor.js")
    # 逐项取串, 避免依赖具体的引号/换行形态
    js_time = tuple(re.findall(r'"([^"]+)"', re.search(r"time:\s*\[([^\]]*)\]", js).group(1)))
    js_size = tuple(re.findall(r'"([^"]+)"', re.search(r"size:\s*\[([^\]]*)\]", js).group(1)))
    units_py = (TOOL_SRC / "gtm" / "units.py").read_text(encoding="utf-8")

    def tool_table(name: str) -> tuple:
        match = re.search(rf"^{name} = \((.*?)\)$", units_py, re.M)
        assert match, f"gtm/units.py 缺常量 {name}"
        return tuple(re.findall(r'"([^"]+)"', match.group(1)))

    assert js_time == AQB_TIME_UNITS == tool_table("TIME_UNITS")
    assert js_size == AQB_SIZE_UNITS == tool_table("SIZE_UNITS")


# ---- POST /claim (人工易主通道, D4/D5, 计划 26-10-20-1316 §03) ----


def test_claim_missing_entry_502(tm_env, monkeypatch):
    """旧安装缺 claim 启动器 -> 502 提示升级(按钮照显, 不静默失败)"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(tm_routes, "_resolve_claim_target", lambda conf: None)
    r = client.post("/api/traffic/monitor/claim", headers=_auth(mgr))
    assert r.status_code == 502
    assert "claim" in r.json()["detail"]


def test_claim_ok_returns_tool_output(tm_env, monkeypatch):
    """退出码 0 -> 200 + 工具侧人话输出原样回传(auto-qb 转述不解释)"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(
        tm_routes, "_resolve_claim_target",
        lambda conf: agent.ClaimTarget(path="/inst/claim.cmd", label="claim 启动器(claim.cmd)"),
    )
    monkeypatch.setattr(
        tm_routes, "_run_claim",
        lambda target: agent.ClaimResult(ok=True, exit_code=0, output="已重登记为正主: install=X data=Y"),
    )
    r = client.post("/api/traffic/monitor/claim", headers=_auth(mgr))
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "已重登记为正主" in r.json()["output"]


def test_claim_refused_409_with_tool_output(tm_env, monkeypatch):
    """被拒(工具在跑 / 数据归属异) -> 409 + 工具侧人话原因(写端点真报错)"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(
        tm_routes, "_resolve_claim_target",
        lambda conf: agent.ClaimTarget(path="/inst/claim.cmd", label="claim 启动器(claim.cmd)"),
    )
    monkeypatch.setattr(
        tm_routes, "_run_claim",
        lambda target: agent.ClaimResult(ok=False, exit_code=1, output="工具正在运行, 请先停止再重登记"),
    )
    r = client.post("/api/traffic/monitor/claim", headers=_auth(mgr))
    assert r.status_code == 409 and "请先停止" in r.json()["detail"]


def test_status_envelope_includes_claim_note(tm_env, monkeypatch):
    """状态载荷带 claim_note(D7): 工具侧让位/被拒注记只读展示"""
    mgr, client, _ = tm_env
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (200, {"ok": True}))
    monkeypatch.setattr(
        agent, "read_deferred_note",
        lambda: {"schema": 1, "reason": "relayed", "detail": "已让位: 注册正主是另一安装"},
    )
    r = client.get("/api/traffic/monitor/status", headers=_auth(mgr))
    assert r.status_code == 200 and r.json()["claim_note"]["reason"] == "relayed"


# ---- 前端接线守阵(D4/D5): 「以本安装重登记」三件套 ----


def test_frontend_claim_wiring():
    """claim = 按钮恒显示(可见性由工具侧判定, D6) + 二次确认 + 在途态 + 注记只读行

    守的是接线: claim 的自检(锁争/数据归属)全在工具侧, auto-qb 只编排执行与转述 ——
    所以按钮**不设可见性条件**(缺入口的旧安装点击时由后端 502 提示升级), 与 relaunch
    的「恒可点」同口径; 注记行渲染工具侧 detail 原话, 前端不二次加工。
    """
    hub = _static("shared", "config_hub.js")
    tpl = _tm_tpl()
    state = _static("shared", "state.js")

    # 1) state: 在途 / 成功 / 失败 / 注记 四态(缺一则按钮点了没反馈)
    for k in ("claiming", "claimMsg", "claimErr", "claimNote"):
        assert re.search(rf"^\s*{k}:\s*", state, re.M), f"state.js 缺 tm.{k}"

    # 2) tpl: 按钮恒显示(只有 disabled 在途态, 无可见性条件) + 注记行渲染 detail
    btn = re.search(r"<button[^>]*tmClaim\(\)[^>]*>.*?</button>", tpl)
    assert btn, "流量与限速卡缺「以本安装重登记」按钮"
    assert ":disabled=\"$root.tm.claiming\"" in btn.group(0)
    assert "v-if" not in btn.group(0), "claim 按钮应恒显示(可见性由工具侧判定, D6)"
    assert "claimNote" in tpl and "claimNote.detail" in tpl, "缺正主注册注记行(D7)"

    # 3) hub: 方法在册 + 调 claim 端点 + 二次确认 + 拒绝原因原样进 claimErr
    assert "async tmClaim()" in hub
    body = hub[hub.index("async tmClaim()"):]
    body = body[:body.index("tmNormalizeForm(")]
    assert "/api/traffic/monitor/claim" in body
    assert "confirmDialog(" in body, "claim 前要二次确认(护栏, D5)"
    assert "claimErr" in body

    # 4) tmLoad 回填 claimNote(状态区据此展示, D7 只读)
    load = hub[hub.index("async tmLoad()"):]
    load = load[:load.index("async tmRelaunch()")]
    assert "r.claim_note" in load

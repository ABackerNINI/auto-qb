"""test_web_traffic_monitor_notify 测试计划: 全局流量监视器通知接收面(计划 26-10-16-0541 S7)

## 测试计划(每个测试函数一条)
- test_notify_requires_auth: 无 Bearer 一律 401(与其它 /api/* 同闸; 对话方是工具进程, 不是浏览器)
- test_notify_path_is_client_constant: 路由路径与 webui/tool_client.NOTIFY_PATH 同源(订阅时登记给
  工具的 endpoint 尾巴必须就是这条路由 —— 两处各写一份必然漂移)
- test_notify_validates_six_keys: 事件体六键逐个校验 -> 400 且逐条点名缺/坏键, 且不投递任何命令
- test_notify_queues_refresh_and_wakes: 合法事件 -> 200 refresh_queued + 命令入队(event_id/day)+ 唤醒主循环
- test_notify_duplicate_event_skipped: 同一事件号重复投递 -> 第二次 skipped/duplicate, 不重复投递
- test_notify_cooldown_window_then_release: 冷却窗口内新事件号也被拦(skipped/cooldown); 冷却归零后放行
- test_notify_disabled_no_enqueue: 联动总开关关 -> action=disabled, 不投递命令(保守默认)
- test_notify_gate_is_per_app_instance: 接收闸状态 per app 实例(同一 manager 再建 app 事件号归零)
"""
import pytest

from auto_qb.config.models import GlobalTrafficMonitorConfig
from auto_qb.webui import tool_client
from webui_helpers import _iter_api_routes

# 鉴权头键名 / 访问密钥字段名: 拆写常量 —— 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量
# 拦整文件(见 pitfalls/testing/credential-shape-write-guard.md), 键名拆写是 2026-10-15 用户
# 拍板的收敛样板; 值恒为夹具里运行期读到的桩值
_AUTH_KEY = "Auth" + "orization"
_CRED_FIELD = "tok" + "en"

EVENT = {"event_id": 3, "day": "2026-10-16", "up_bytes": 1024, "down_bytes": 2048, "total_bytes": 3072, "ts": 1.0e9}


def _auth(mgr):
    return {_AUTH_KEY: f"Bearer {getattr(mgr.web, _CRED_FIELD)}"}


@pytest.fixture()
def tm_env(web_env):
    """web_env + 已启用的 global_traffic_monitor 段(冷却缺省 600s)"""
    mgr, client = web_env
    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(enabled=True)
    return mgr, client


def _drain_commands(mgr):
    """取走命令队列里的全部 (cmd, payload)"""
    out = []
    while not mgr.web.commands.empty():
        out.append(mgr.web.commands.get_nowait())
    return out


def _post(client, mgr, payload):
    return client.post(tool_client.NOTIFY_PATH, json=payload, headers=_auth(mgr))


# ---- 鉴权 / 路径同源 ----


def test_notify_requires_auth(web_env):
    mgr, client = web_env
    assert client.post(tool_client.NOTIFY_PATH, json=EVENT).status_code == 401


def test_notify_path_is_client_constant(web_env):
    """路由路径 == 订阅客户端登记给工具的 endpoint 尾巴(单点, 不许两处各写一份)"""
    _mgr, client = web_env
    paths = {(next(iter(r.methods - {"HEAD"})), r.path) for r in _iter_api_routes(client.app.routes)}
    assert ("POST", tool_client.NOTIFY_PATH) in paths


# ---- 校验 / 投递 ----


def test_notify_validates_six_keys(tm_env):
    """六键逐个校验: 缺键/坏形状 -> 400 逐条点名, 且一个命令都不投"""
    mgr, client = tm_env
    for bad in (
        {},
        {
            **EVENT, "event_id": -1
        },
        {
            **EVENT, "day": ""
        },
        {
            **EVENT, "total_bytes": -5
        },
        {
            **EVENT, "up_bytes": "1024"
        },
        {
            **EVENT, "ts": 0
        },
        {
            **EVENT, "event_id": True
        },
    ):
        r = _post(client, mgr, bad)
        assert r.status_code == 400, f"应拒: {bad}"
    assert _drain_commands(mgr) == []


def test_notify_queues_refresh_and_wakes(tm_env):
    """合法事件 -> 200 refresh_queued: 命令进主循环队列(带 event_id/day)并唤醒主循环"""
    mgr, client = tm_env
    mgr._wake_calls.clear()
    r = _post(client, mgr, EVENT)
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "refresh_queued" and body["event_id"] == EVENT["event_id"] and body["cmd_id"]
    queued = _drain_commands(mgr)
    assert [c for c, _ in queued] == ["refresh_traffic"]
    payload = queued[0][1]
    assert payload["event_id"] == EVENT["event_id"] and payload["day"] == EVENT["day"]
    assert payload["cmd_id"] == body["cmd_id"]
    assert mgr._wake_calls, "刷新命令必须唤醒主循环(否则要等下个节拍)"


def test_notify_duplicate_event_skipped(tm_env):
    """同一事件号重复投递: 第二次 skipped/duplicate, 不重复投递命令"""
    mgr, client = tm_env
    assert _post(client, mgr, EVENT).json()["action"] == "refresh_queued"
    second = _post(client, mgr, EVENT).json()
    assert second["action"] == "skipped" and second["reason"] == "duplicate"
    assert [c for c, _ in _drain_commands(mgr)] == ["refresh_traffic"]


def test_notify_cooldown_window_then_release(tm_env):
    """冷却窗口内的新事件号也被拦(cooldown); 冷却归零后立即放行"""
    mgr, client = tm_env
    assert _post(client, mgr, EVENT).json()["action"] == "refresh_queued"
    later = {**EVENT, "event_id": EVENT["event_id"] + 1}
    body = _post(client, mgr, later).json()
    assert body["action"] == "skipped" and body["reason"] == "cooldown"

    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(enabled=True, notify_cooldown_s=0.0)
    assert _post(client, mgr, later).json()["action"] == "refresh_queued"


def test_notify_disabled_no_enqueue(tm_env):
    """联动总开关关(缺省): action=disabled 且不投递命令(保守默认, 黄金法则 2)"""
    mgr, client = tm_env
    mgr.config.global_traffic_monitor = GlobalTrafficMonitorConfig(enabled=False)
    body = _post(client, mgr, EVENT).json()
    assert body["action"] == "disabled" and "enabled=false" in body["reason"]
    assert _drain_commands(mgr) == []


def test_notify_gate_is_per_app_instance(tm_env):
    """接收闸 per app 实例: 同一 manager 重建 app 后事件号基线归零(与 auth 的「只记一次」同款)"""
    from auto_qb.webui import create_app

    mgr, client = tm_env
    assert _post(client, mgr, EVENT).json()["action"] == "refresh_queued"
    assert _post(client, mgr, EVENT).json()["action"] == "skipped"
    fresh = create_app(mgr)  # 新 app 实例 = 新闸(状态不提升为模块级全局)
    from fastapi.testclient import TestClient

    assert _post(TestClient(fresh), mgr, EVENT).json()["action"] == "refresh_queued"

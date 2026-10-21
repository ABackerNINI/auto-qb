"""test_web_traffic_monitor_notify 测试计划: 全局流量监视器通知接收面(计划 26-10-16-0541 S7)

## 测试计划(每个测试函数一条)
- test_notify_requires_auth: 无 Bearer / 错 Bearer 一律 401(与其它 /api/* 同闸; 对话方是工具进程, 不是浏览器)
  —— 错 Bearer 分支覆盖密钥比较(只测「没带」时, 比较分支被绕过也照样绿, S9 鉴权绕过红验实测)
- test_notify_path_is_client_constant: 路由路径与 webui/tool_client.NOTIFY_PATH 同源(订阅时登记给
  工具的 endpoint 尾巴必须就是这条路由 —— 两处各写一份必然漂移)
- test_notify_validates_six_keys: 事件体六键逐个校验 -> 400 且逐条点名缺/坏键, 且不投递任何命令
- test_notify_queues_refresh_and_wakes: 合法事件 -> 200 refresh_queued + 命令入队(event_id/day/累计载荷)+ 唤醒主循环
- test_notify_duplicate_event_skipped: 同一事件号重复投递 -> 第二次 skipped/duplicate, 不重复投递
- test_notify_no_throttle_every_new_event_patches: 26-10-21 改制(读盘即副作用, 事件零读盘直达):
  无冷却窗口, 连续新事件号个个放行; 命令只带载荷(up/down_bytes), 不触发任何读盘
- test_notify_stale_day_skipped: 非当日事件(跨天/时钟偏差) -> skipped/stale_day, 不投递命令(兜底读盘覆盖)
- test_notify_command_execution_patches_snapshot: 端到端(接收面 -> 命令 -> 主循环执行体):
  事件把 day 行补丁进快照, 执行体一次读盘都没有
- test_notify_disabled_no_enqueue: 联动总开关关 -> action=disabled, 不投递命令(保守默认)
- test_notify_disabled_when_source_off: 来源总开关关(S1/D1) -> action=disabled, 不投递命令
- test_notify_gate_is_per_app_instance: 接收闸状态 per app 实例(同一 manager 再建 app 事件号归零)
- test_notify_refresh_logs_at_debug: 放行补丁的接收面日志恒 DEBUG(高频链路, INFO 会刷屏; 26-10-18 降级)
"""
import logging
from datetime import date

import pytest

from auto_qb.webui import tool_client
from helpers import capture_logs
from webui_helpers import _iter_api_routes

# 鉴权头键名 / 访问密钥字段名: 拆写常量 —— 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量
# 拦整文件(见 pitfalls/testing/credential-shape-write-guard.md), 键名拆写是 2026-10-15 用户
# 拍板的收敛样板; 值恒为夹具里运行期读到的桩值
_AUTH_KEY = "Auth" + "orization"
_CRED_FIELD = "tok" + "en"


# day 动态取今天: 26-10-21 起端点只补丁当日事件(非当日 -> skipped/stale_day), 硬编码过去日期
# 会让所有正向用例被当日判据拦下。
# ⚠ 必须**调用时求值**(工厂), 不能在模块导入时算成常量 —— 服务端在请求时才读 date.today()
# 判当日; 全量套件 23:59 收集 / 00:00 后执行时, 导入时算的 day 对服务端就是「非当日」,
# 6 条正向用例全假红(2026-10-22 跨日窗口抖动; 坑档 pitfalls/testing/flaky-midnight-daycount.md)。
# overrides 供校验 / 陈旧日等变体用例复用同一契约。
def _event(**overrides):
    return {
        "event_id": 3,
        "day": date.today().isoformat(),
        "up_bytes": 1024,
        "down_bytes": 2048,
        "total_bytes": 3072,
        "ts": 1.0e9,
        **overrides,
    }


def _auth(mgr):
    return {_AUTH_KEY: f"Bearer {getattr(mgr.web, _CRED_FIELD)}"}


@pytest.fixture()
def tm_env(web_env):
    """web_env + 来源切到工具面(provider=global_traffic_monitor)

    S17 起「联动是否启用」不再有独立 enabled 键 —— 单一开关是 traffic_source.provider。
    26-10-21 起通知无冷却(事件零读盘直达补丁), 闸门只剩事件号去重。
    """
    mgr, client = web_env
    mgr.config.traffic_source.provider = "global_traffic_monitor"
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
    assert client.post(tool_client.NOTIFY_PATH, json=_event()).status_code == 401
    # 带了 Bearer 但值不对: 必须也 401 —— 只测「没带」会漏掉密钥比较分支(该分支被绕过时前一行照样绿)
    wrong = {_AUTH_KEY: "Bearer " + "wrong-credential"}
    assert client.post(tool_client.NOTIFY_PATH, json=_event(), headers=wrong).status_code == 401


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
        _event(event_id=-1),
        _event(day=""),
        _event(total_bytes=-5),
        _event(up_bytes="1024"),
        _event(ts=0),
        _event(event_id=True),
    ):
        r = _post(client, mgr, bad)
        assert r.status_code == 400, f"应拒: {bad}"
    assert _drain_commands(mgr) == []


def test_notify_queues_refresh_and_wakes(tm_env):
    """合法事件 -> 200 refresh_queued: 命令进主循环队列(带 event_id/day + 累计载荷)并唤醒主循环

    26-10-21 起命令带 up_bytes/down_bytes: 主循环据此零读盘补丁(publish_event), 不再读盘。
    """
    mgr, client = tm_env
    mgr._wake_calls.clear()
    ev = _event()
    r = _post(client, mgr, ev)
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "refresh_queued" and body["event_id"] == ev["event_id"] and body["cmd_id"]
    queued = _drain_commands(mgr)
    assert [c for c, _ in queued] == ["refresh_traffic"]
    payload = queued[0][1]
    assert payload["event_id"] == ev["event_id"] and payload["day"] == ev["day"]
    assert payload["up_bytes"] == ev["up_bytes"] and payload["down_bytes"] == ev["down_bytes"]
    assert payload["cmd_id"] == body["cmd_id"]
    assert mgr._wake_calls, "补丁命令必须唤醒主循环(否则要等下个节拍)"


def test_notify_duplicate_event_skipped(tm_env):
    """同一事件号重复投递: 第二次 skipped/duplicate, 不重复投递命令"""
    mgr, client = tm_env
    ev = _event()
    assert _post(client, mgr, ev).json()["action"] == "refresh_queued"
    second = _post(client, mgr, ev).json()
    assert second["action"] == "skipped" and second["reason"] == "duplicate"
    assert [c for c, _ in _drain_commands(mgr)] == ["refresh_traffic"]


def test_notify_no_throttle_every_new_event_patches(tm_env):
    """26-10-21 改制(用户拍板「读盘本身就是副作用, 事件基本无副作用应立即刷新」):

    无冷却窗口 —— 每个新事件号都立即投递载荷补丁(命令只带 up/down_bytes, 主循环零读盘),
    连续新事件号个个放行; 旧冷却键 notify_cooldown_s 已退役, 改成 0 或 24H 行为不变。
    """
    mgr, client = tm_env
    for step in (0, 1, 2):
        e = _event(event_id=3 + step)
        assert _post(client, mgr, e).json()["action"] == "refresh_queued"
    assert [c for c, _ in _drain_commands(mgr)] == ["refresh_traffic"] * 3

    mgr.config.traffic_source.global_traffic_monitor.notify_cooldown_s = 86400.0
    fourth = _event(event_id=6)
    assert _post(client, mgr, fourth).json()["action"] == "refresh_queued"
    assert [c for c, _ in _drain_commands(mgr)] == ["refresh_traffic"]


def test_notify_stale_day_skipped(tm_env):
    """非当日事件(跨天边界 / 时钟偏差): skipped/stale_day, 不投递命令也不读盘

    那天的累计文件里早有, 由 refresh_interval 兜底读盘覆盖 —— 事件路径保持零读盘。
    """
    mgr, client = tm_env
    stale = _event(event_id=99, day="1999-01-01")
    body = _post(client, mgr, stale).json()
    assert body["action"] == "skipped" and body["reason"] == "stale_day"
    assert _drain_commands(mgr) == []


def test_notify_command_execution_patches_snapshot(tmp_path, monkeypatch):
    """执行体(真 manager, 主循环命令线): 载荷命令 -> 快照 day 行被补丁, 一次读盘都没有

    路由 -> 队列的载荷形状由 test_notify_queues_refresh_and_wakes 钉死; 这里把同款命令
    (与 consume_commands 的传参形态一致: 剥掉 cmd_id)投进队列并**真的消费**, 覆盖
    「执行体 -> 模块补丁」链路。读盘打桩成 raise: 执行体若退回读文件(旧形态), 这条直接红
    —— 「读盘本身就是副作用」的判据钉在整条链路上, 不止模块单测。
    """
    from helpers import make_manager

    import auto_qb.core.modules.traffic_snapshot_mod as tsm

    def _boom(*_a, **_k):
        raise AssertionError("事件路径执行体不许读盘(读盘本身就是副作用)")

    monkeypatch.setattr(tsm, "read_source_rows", _boom)
    mgr = make_manager(str(tmp_path / "state.json"))
    ev = _event()
    mgr.web.commands.put(
        (
            "refresh_traffic",
            {
                "event_id": ev["event_id"],
                "day": ev["day"],
                "up_bytes": ev["up_bytes"],
                "down_bytes": ev["down_bytes"],
                "cmd_id": "t1",
            },
        )
    )

    mgr.web.consume_commands()  # 主循环命令线: 排队 -> 执行 -> 回执

    rows = {p["period"]: (p["up"], p["down"]) for p in mgr.web.traffic_view["periods"]}
    assert rows["day"] == (ev["up_bytes"], ev["down_bytes"]), "事件累计必须补丁进 day 行"


def test_notify_disabled_no_enqueue(tm_env):
    """来源未指向工具(provider=traffic_monitor): action=disabled 且不投递命令(保守默认, 黄金法则 2)"""
    mgr, client = tm_env
    mgr.config.traffic_source.provider = "traffic_monitor"
    body = _post(client, mgr, _event()).json()
    assert body["action"] == "disabled" and "provider != global_traffic_monitor" in body["reason"]
    assert _drain_commands(mgr) == []


def test_notify_disabled_when_source_off(tm_env):
    """来源总开关关(S1/D1, 26-10-17-1737): action=disabled 且不投递命令(关源停一切取数)

    判定优先于 provider: 关源时 provider 指向工具也不触发刷新。
    """
    mgr, client = tm_env
    mgr.config.traffic_source.enabled = False
    body = _post(client, mgr, _event()).json()
    assert body["action"] == "disabled" and "enabled=false" in body["reason"]
    assert _drain_commands(mgr) == []


def test_notify_gate_is_per_app_instance(tm_env):
    """接收闸 per app 实例: 同一 manager 重建 app 后事件号基线归零(与 auth 的「只记一次」同款)"""
    from auto_qb.webui import create_app

    mgr, client = tm_env
    ev = _event()
    assert _post(client, mgr, ev).json()["action"] == "refresh_queued"
    assert _post(client, mgr, ev).json()["action"] == "skipped"
    fresh = create_app(mgr)  # 新 app 实例 = 新闸(状态不提升为模块级全局)
    from fastapi.testclient import TestClient

    assert _post(TestClient(fresh), mgr, ev).json()["action"] == "refresh_queued"


def test_notify_refresh_logs_at_debug(tm_env):
    """放行补丁的接收面日志恒 DEBUG: 阈值事件随流量密度来, INFO 会刷屏(26-10-18 用户要求降级)

    与 skipped 分支同口径(本就 DEBUG): 放行/拦下都只在 DEBUG 可见。日志捕获走
    helpers.capture_logs —— QbManager 构造链会清 root handlers, caplog 在这类用例里恒空。
    """
    mgr, client = tm_env
    ev = _event()
    with capture_logs("auto_qb.web") as cap:
        r = _post(client, mgr, ev)
    assert r.status_code == 200
    pairs = list(zip(cap.records, cap.messages))  # helper 契约: 两列表同序
    flood = [(rec, msg) for rec, msg in pairs if "已投递今日流量补丁" in msg]
    assert flood, "放行补丁必须留下 DEBUG 轨迹(排障时看得到事件号/累计值)"
    assert all(rec.levelno == logging.DEBUG for rec, _ in flood)
    assert not any(rec.levelno == logging.INFO and "全局流量监视器通知" in msg for rec, msg in pairs), \
        "接收面放行日志不得再记 INFO(刷屏根源)"

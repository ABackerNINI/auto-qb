"""test_traffic_monitor_client 测试计划: 全局流量监视器订阅客户端 + 通知触发的流量快照刷新(计划 26-10-16-0541 S7 / 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_desired_gates: 期望订阅态三道闸(来源 provider / WEBUI 未启用 / 访问密钥未就绪)
  —— 任一不满足即不订阅, 原因文案可读
- test_endpoint_is_loopback_notify_path: 登记给工具的回调 endpoint = 本机回环 + 本实例端口 + 通知路径
- test_register_stores_id_and_heartbeat_interval: 探活通过 -> 注册成功, 记住工具给的订阅 id 与心跳周期, 载荷带回调 endpoint 与回调凭证
- test_registered_pass_only_heartbeats: 已注册且注册键未变 -> 只心跳, 不重复注册
- test_reg_key_change_reregisters: 端口变化(注册键之一) -> 先注销旧 id 再按新键注册
- test_heartbeat_unknown_id_reregisters: 工具回 404(注册表丢了 / 租约过期) -> 本轮立刻重新注册
- test_desired_false_unregisters_and_stops: 来源切走 -> 注销并返回 False(线程据此收线), 不再发心跳
- test_not_ready_launches_and_backs_off: 工具不可达 -> 触发一次拉起(可注入动作)且本轮不进控制面;
  退避窗口内不重复拉起(S16/D14)
- test_register_failure_warns_once: 注册被拒 -> 同一原因只 WARNING 一次, 之后降 DEBUG(不刷屏)
- test_stop_is_bounded_when_tool_hangs: 工具假死时 stop() 仍在有界超时内返回(关停不被工具拖住); 超时后**保留线程引用**(二次 stop 能补 join, 不会双订阅)
- test_thread_lifecycle_sync_then_stop: sync 起订阅线程并完成注册; stop 收线前注销订阅
- test_thread_self_terminates_when_disabled: 来源中途切走 + sync -> 线程读到期望态为假, 注销后自行退出
- test_refresh_traffic_view_republishes_readonly: 只读刷新: 历史行 + 各周期累计重算发布, state/limit 沿用, 不读不写 qB 限速
- test_refresh_traffic_view_skips: 曲线未启用 / dat 缺失 / 无有效行 -> 不发布(返回 False), 快照保持原样
- test_refresh_traffic_command_drained: `refresh_traffic` 已进命令表且经主循环 drain 执行后快照刷新(回执 ok)
- test_end_to_end_notify_then_state_shows_fresh_traffic: 端到端(进程内): 真端点 -> 命令队列 -> 真 handler -> 快照刷新 -> /api/state 与 /api/traffic/history 两取数位可见
- test_mock_config_section_starts_no_thread: 桩配置(MagicMock 段)不得被当成「已联动」起订阅线程 —— 不等/恒等类型判据守阵
"""
import io
import json
import logging
import threading
import time
from datetime import date
from unittest import mock

import pytest

from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
from auto_qb.core.traffic_source import agent
from auto_qb.webui import tool_client
from helpers import make_manager

GIB = 1024**3
MIB = 1024**2
# 工具发现指针(D6/S16): 订阅方向不再读配置里的 url/token —— 端点/密钥全部来自这里
POINTER_HOST = "127.0.0.1"
POINTER_PORT = 8099
# 本实例 WEB 访问密钥字段名: 拆写常量, 读写都走它 —— 工作区写入判据把「凭据键名 + 赋值形态」
# 当凭据字面量拦整文件(见 pitfalls/testing/credential-shape-write-guard.md), 键名拆写是
# 2026-10-15 用户拍板的收敛样板; 值恒为桩里现造的运行期变量, 与本仓凭据无关
_CRED_FIELD = "tok" + "en"
# 订阅载荷里回调凭证的键名(同上, 键名拆写)
_CALLBACK_KEY = _CRED_FIELD
# 鉴权头键名(同上, 键名拆写)
_AUTH_KEY = "Auth" + "orization"

# ---------- 构造辅助 ----------


def _points(pairs):
    """[(阈值GiB, 限速MiB/s)] -> CurvePoint 列表"""
    return [CurvePoint(threshold_bytes=int(g * GIB), speed_bytes_per_s=int(v * MIB)) for g, v in pairs]


def _pc(period: str, up=None, down=None) -> PeriodCurve:
    return PeriodCurve(period=period, upload_points=up, download_points=down)


def _dat_text(rows) -> str:
    """rows: [(date, 上传字节, 下载字节)] -> dat 文本(单位 KB, 与 curves.parse_history_dat 同口径)"""
    lines = ['lines: "30"']
    for d, up_b, down_b in rows:
        lines.append(f"{d:%Y/%m/%d} {up_b // 1024}/{down_b // 1024}")
    return "\n".join(lines)


def _write_credential_file(tmp_path) -> str:
    """写一个假的工具密钥文件(值仅用于断言透传, 与真工具无关)"""
    path = tmp_path / "gtm" / "monitor.token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("tool-credential-abc\n", encoding="utf-8")
    return str(path)


def _write_pointer(tmp_path, monkeypatch, *, token_path: str, schema=agent.ENDPOINT_SCHEMA) -> str:
    """写发现指针 endpoint.json 并把 agent 的指针路径重定向到它(S16)

    指针是订阅方向唯一的端点/密钥来源(D6); 载荷字段名与工具侧 gtm 的写出契约一致。
    """
    path = tmp_path / "pointer" / agent.ENDPOINT_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": schema,
        "version": "0.1.0",
        "pid": 4321,
        "started_at": "2026-10-17T00:00:00+08:00",
        "host": POINTER_HOST,
        "port": POINTER_PORT,
        "data_dir": str(tmp_path / "gtm"),
        "token_path": token_path,
        "exe_path": "",
        "autostart_registered": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(path))
    return str(path)


def _wait_until(pred, timeout: float = 3.0) -> bool:
    """轮询等待条件成立(线程用例; 命中即返回 True, 超时返回最后一次判定)"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


def _sub_threads():
    """存活的订阅线程; stop / 自行收线之后应为空"""
    return [t for t in threading.enumerate() if t.name == "auto-qb-gtm-sub"]


class _LogCapture:
    """捕获指定 logger 的输出(自建 handler; 不用 caplog —— QbManager 构造会清 root handlers)

    判据见 pitfalls/testing/log-capture.md: 断言日志一律走「给目标 logger 挂 handler」。
    """
    def __init__(self, name, level=logging.DEBUG):
        self._logger = logging.getLogger(name)
        self._level = level
        self.buf = io.StringIO()

    def __enter__(self):
        handler = logging.StreamHandler(self.buf)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        self._logger.addHandler(handler)
        self._handler = handler
        self._old_level, self._old_propagate = self._logger.level, self._logger.propagate
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        return self.buf

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._old_level)
        self._logger.propagate = self._old_propagate
        return False


class _FakeTool:
    """工具控制面替身: 记录 (path, payload) 调用并按脚本回响应(可注入异常 / 挂起)

    探活(`GET /status`)恒 200 —— 订阅编排只在 agent 探活成功后才进控制面(S16), 故所有
    「已注册 / 已心跳」用例都要它先过探活这一关。
    """
    def __init__(self):
        self.calls = []
        self.sub_seq = 0
        self.heartbeat_codes = []  # 依次出队的响应码(用尽则 200)
        self.subscribe_code = None  # 非 None 则 /subscribe 直接回该码(模拟被拒)
        self.raise_exc = None
        self.hang = None  # threading.Event: 置位前阻塞在调用里(模拟工具假死)
        self.launches = []  # 记录 agent 的拉起动作(注入的假动作, 真拉起会触 sidefx 越界)

    def __call__(self, base_url, path, method, credential, payload=None, timeout=None):
        self.calls.append((path, dict(payload or {})))
        if self.hang is not None:
            self.hang.wait(5.0)
        if self.raise_exc is not None:
            raise self.raise_exc
        if path == "/status":
            return 200, {"ok": True, "version": "0.1.0"}
        if path == "/subscribe":
            self.sub_seq += 1
            if self.subscribe_code is not None:
                return self.subscribe_code, {"error": "not allowed"}
            return 200, {
                "ok": True,
                "id": f"sub-{self.sub_seq}",
                "heartbeat_interval_s": 60,
            }
        if path == "/heartbeat":
            code = self.heartbeat_codes.pop(0) if self.heartbeat_codes else 200
            return (200, {"ok": True}) if code == 200 else (code, {"error": "unknown subscriber id"})
        if path == "/unsubscribe":
            return 200, {"ok": True}
        raise AssertionError(f"意外路径: {path}")

    def paths(self):
        return [p for p, _ in self.calls]

    def payloads(self, path):
        return [payload for p, payload in self.calls if p == path]


@pytest.fixture()
def sub_env(tmp_path, monkeypatch):
    """订阅客户端环境: 真 manager(替身配置) + 假工具控制面 + 假拉起动作 -> (mgr, sub, tool)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.web.enabled = True
    mgr.config.web.port = 8080
    setattr(mgr.web, _CRED_FIELD, "web-credential-1")
    # S16: 是否联动只看顶层来源段的 provider; 端点与密钥来自发现指针(D6), 不再读配置 url/token
    mgr.config.traffic_source.provider = "global_traffic_monitor"
    _write_pointer(tmp_path, monkeypatch, token_path=_write_credential_file(tmp_path))
    tool = _FakeTool()
    monkeypatch.setattr(tool_client, "call_tool", tool)
    # !真实拉起会 Popen(工具启动器) —— sidefx 的 POPEN 白名单只放行 node 与临时 wrapper,
    # 单测必须注入假动作(agent 的模块级单点), 否则触发越界
    monkeypatch.setattr(agent, "launch_tool", lambda target: tool.launches.append(target))
    return mgr, tool_client.TrafficMonitorSubscriber(mgr), tool


# ---------- 期望态与注册键 ----------


def test_desired_gates(sub_env):
    """期望订阅态三道闸: 来源 provider / WEBUI 启用 / 访问密钥就绪"""
    mgr, sub, _tool = sub_env
    assert sub._desired() == (True, "")
    mgr.config.traffic_source.provider = "traffic_monitor"
    assert sub._desired() == (False, "当前流量来源不是全局流量监视器(traffic_source.provider != global_traffic_monitor)")
    mgr.config.traffic_source.provider = "global_traffic_monitor"
    mgr.config.web.enabled = False
    assert sub._desired() == (False, "WEB UI 未启用(通知端点不存在)")
    mgr.config.web.enabled = True
    setattr(mgr.web, _CRED_FIELD, "")
    assert sub._desired() == (False, "WEB 访问密钥未就绪")


def test_endpoint_is_loopback_notify_path(sub_env):
    """回调 endpoint = 本机回环 + 本实例 WEB 端口 + 通知路径(工具与 WebUI 必须同机)"""
    mgr, sub, _tool = sub_env
    mgr.config.web.port = 8787
    assert sub._endpoint() == f"http://127.0.0.1:8787{tool_client.NOTIFY_PATH}"


# ---------- 一轮收敛(直接驱动 _pass, 不起线程) ----------


def test_register_stores_id_and_heartbeat_interval(sub_env):
    """探活通过 -> 注册成功: 记住订阅 id 与心跳周期; 载荷带回调 endpoint 与回调凭证"""
    mgr, sub, tool = sub_env
    assert sub._pass() is True
    assert tool.paths() == ["/status", "/subscribe"]
    payload = tool.payloads("/subscribe")[0]
    assert payload["endpoint"] == f"http://127.0.0.1:8080{tool_client.NOTIFY_PATH}"
    assert payload[_CALLBACK_KEY] == getattr(mgr.web, _CRED_FIELD)
    assert sub._sub_id == "sub-1"
    assert sub._heartbeat_s == 60.0


def test_registered_pass_only_heartbeats(sub_env):
    """已注册且注册键未变 -> 只心跳续租, 不重复注册"""
    _mgr, sub, tool = sub_env
    sub._pass()
    assert sub._pass() is True
    assert tool.paths() == ["/status", "/subscribe", "/status", "/heartbeat"]
    assert tool.payloads("/heartbeat")[0]["id"] == "sub-1"


def test_reg_key_change_reregisters(sub_env):
    """端口变化(注册键之一) -> 先注销旧 id 再按新键注册"""
    mgr, sub, tool = sub_env
    sub._pass()
    mgr.config.web.port = 8081
    assert sub._pass() is True
    assert tool.paths() == ["/status", "/subscribe", "/status", "/unsubscribe", "/subscribe"]
    assert tool.payloads("/unsubscribe")[0]["id"] == "sub-1"
    assert sub._sub_id == "sub-2"


def test_heartbeat_unknown_id_reregisters(sub_env):
    """工具回 404(注册表丢了 / 租约过期) -> 本轮立刻重新注册"""
    _mgr, sub, tool = sub_env
    sub._pass()
    tool.heartbeat_codes = [404]
    assert sub._pass() is True
    assert tool.paths() == ["/status", "/subscribe", "/status", "/heartbeat", "/subscribe"]
    assert sub._sub_id == "sub-2"


def test_desired_false_unregisters_and_stops(sub_env):
    """来源切走 -> 注销并返回 False(线程据此收线), 不再发心跳"""
    mgr, sub, tool = sub_env
    sub._pass()
    mgr.config.traffic_source.provider = "traffic_monitor"
    assert sub._pass() is False
    assert tool.paths() == ["/status", "/subscribe", "/unsubscribe"]
    assert sub._sub_id == ""


def test_not_ready_launches_and_backs_off(sub_env):
    """工具不可达 -> 触发一次拉起(可注入动作)且本轮不进控制面; 退避窗口内不重复拉起(S16/D14)"""
    _mgr, sub, tool = sub_env
    tool.raise_exc = tool_client.ToolUnreachable("connection refused")
    assert sub._pass() is True  # 期望态仍为真 -> 线程继续, 等下轮
    assert len(tool.launches) == 1, "工具缺席应触发一次拉起"
    target = tool.launches[0]
    assert target.is_exe is False and target.path.endswith("launch.cmd" if agent.is_windows() else "launch.sh")
    assert tool.paths() == ["/status"], f"未就绪不得进控制面: {tool.paths()}"
    assert sub._wait_s == tool_client._NOT_READY_POLL_S, "未就绪应短轮询等探活"
    assert sub._sub_id == ""
    assert sub._pass() is True  # 探活窗口内 -> 不重复拉起
    assert len(tool.launches) == 1, f"等待窗口内重复拉起了: {len(tool.launches)}"


def test_register_failure_warns_once(sub_env):
    """注册被拒: 同一原因只 WARNING 一次(逐轮 WARNING 会刷屏), 之后降 DEBUG"""
    _mgr, sub, tool = sub_env
    tool.subscribe_code = 500
    with _LogCapture("auto_qb.webui.tool_client") as buf:
        sub._pass()
        sub._pass()
    text = buf.getvalue()
    assert text.count("WARNING") == 1, f"同一原因应只 WARNING 一次, 实测: {text}"
    assert "注册订阅被拒" in text


def test_stop_is_bounded_when_tool_hangs(sub_env):
    """工具假死时 stop() 仍在有界超时内返回(关停不被工具拖住); 超时后保留引用待补 join"""
    _mgr, sub, tool = sub_env
    hang = threading.Event()
    tool.hang = hang
    sub.sync()  # 起线程: 它会阻塞在假死调用里
    try:
        assert _wait_until(lambda: tool.paths() == ["/status"]), "线程未发起探活调用"
        t0 = time.monotonic()
        with _LogCapture("auto_qb.webui.tool_client") as buf:
            sub.stop(timeout=0.05)
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, f"stop 被工具拖住: {elapsed:.2f}s"
        assert "未退出" in buf.getvalue()
        # !超时后引用不许摘: 摘了就再也没人能 join 它, 而 sync() 会误以为无线程再起一条
        # (双订阅双心跳) —— 参见实现里 stop() 的注释
        assert sub._thread is not None and sub._thread.is_alive()
    finally:
        hang.set()  # 放行挂起调用, 让线程收尾(不污染后续用例)
        sub.stop(timeout=3.0)
        assert _wait_until(lambda: not _sub_threads()), "释放假死后订阅线程未收线"


# ---------- 线程生命周期 ----------


def test_thread_lifecycle_sync_then_stop(sub_env):
    """sync 起订阅线程并完成注册; stop 收线前把订阅注销掉"""
    _mgr, sub, tool = sub_env
    sub.sync()
    assert _wait_until(lambda: "/subscribe" in tool.paths()), "sync 后线程未注册"
    assert sub._thread is not None and sub._thread.is_alive()
    sub.stop()
    assert _wait_until(lambda: "/unsubscribe" in tool.paths()), "stop 未注销订阅"
    assert _wait_until(lambda: not _sub_threads()), "订阅线程未退出"


def test_thread_self_terminates_when_disabled(sub_env):
    """来源中途切走 + sync -> 线程读到期望态为假, 注销后自行退出(不必等 stop)"""
    mgr, sub, tool = sub_env
    sub.sync()
    assert _wait_until(lambda: "/subscribe" in tool.paths())
    mgr.config.traffic_source.provider = "traffic_monitor"
    sub.sync()
    assert _wait_until(lambda: "/unsubscribe" in tool.paths()), "切走来源后未注销"
    assert _wait_until(lambda: not _sub_threads()), "订阅线程未自行退出"


# ---------- 只读刷新(speed_curve 模块 + WEB 命令) ----------


def _refresh_env(tmp_path, monkeypatch, *, enabled=True, dat_name="history_traffic.dat", write_dat=True, qb_calls=None):
    """构造可刷新的环境 -> (mgr, dat 路径, qB 限速调用记录器)

    qB 的限速读写被替身为记录器(lambda 里 append): 「只读刷新」的守阵据此断言一次调用都没有。
    write_dat=False 用于造「dat 缺失」形态(只给路径不落文件)。
    """
    calls = qb_calls if qb_calls is not None else []
    mgr = make_manager(str(tmp_path / "state.json"))
    dat_path = tmp_path / dat_name
    if write_dat:
        dat_path.write_text(_dat_text([(date.today(), 3 * MIB, 5 * MIB)]), encoding="utf-8")
    mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
        curves=[_pc("day", up=_points([(1, 1)])),
                _pc("month", down=_points([(1, 2)]))],
        enabled=enabled,
    )
    # 数据源在顶层 traffic_source 段(S15): 直接注入 FakeConfig, 等价于 load_config 后的形态
    mgr.config.traffic_source.traffic_monitor.dat_path = str(dat_path)
    monkeypatch.setattr(mgr.api, "set_global_speed_limits", lambda **kw: calls.append(("set", kw)))
    monkeypatch.setattr(
        mgr.api, "get_global_speed_limits", lambda: calls.append(("get", {})) or {
            "upload_limit": 0,
            "download_limit": 0
        }
    )
    mgr.web.traffic_view = {
        "state": "ok",
        "periods": [],
        "history": [],
        "ts": 1.0,
        "date": "1970-01-01",
        "limit": {
            "target": {
                "up": 1,
                "down": 2
            },
            "actual": {
                "up": 1,
                "down": 2
            },
            "reasons": []
        },
    }
    return mgr, str(dat_path), calls


def test_refresh_traffic_view_republishes_readonly(tmp_path, monkeypatch):
    """只读刷新: 历史行 + 各周期累计重算发布; state/limit 沿用; **不读不写 qB 限速**"""
    mgr, _dat, qb_calls = _refresh_env(tmp_path, monkeypatch)
    mod = mgr.host.get("speed_curve")

    assert mod.refresh_traffic_view() is True

    view = mgr.web.traffic_view
    today = date.today().isoformat()
    assert view["history"] == [{"date": today, "up": 3 * MIB, "down": 5 * MIB}]
    assert [(p["period"], p["up"], p["down"])
            for p in view["periods"]] == [("day", 3 * MIB, 5 * MIB), ("month", 3 * MIB, 5 * MIB)]
    assert view["date"] == today and view["ts"] > 1.0
    # 沿用上次快照: 状态与限速字段一字不动(本刷新不查档、不写 qB)
    assert view["state"] == "ok"
    assert view["limit"] == {"target": {"up": 1, "down": 2}, "actual": {"up": 1, "down": 2}, "reasons": []}
    assert qb_calls == [], f"只读刷新不得碰 qB 限速: {qb_calls}"


def test_refresh_traffic_view_skips(tmp_path, monkeypatch):
    """曲线未启用 / dat 缺失 / 无有效行 -> 不发布(返回 False), 快照保持原样"""
    mgr, _dat, qb_calls = _refresh_env(tmp_path, monkeypatch, enabled=False)
    before = dict(mgr.web.traffic_view)
    assert mgr.host.get("speed_curve").refresh_traffic_view() is False
    assert mgr.web.traffic_view == before

    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch, dat_name="not-there.dat", write_dat=False)
    assert mgr.host.get("speed_curve").refresh_traffic_view() is False
    assert mgr.web.traffic_view["history"] == []

    empty = tmp_path / "empty.dat"
    empty.write_text('lines: "0"\n', encoding="utf-8")
    mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(curves=[_pc("day", up=_points([(1, 1)]))])
    mgr.config.traffic_source.traffic_monitor.dat_path = str(empty)
    assert mgr.host.get("speed_curve").refresh_traffic_view() is False
    assert mgr.web.traffic_view["history"] == []
    assert qb_calls == []


def test_refresh_traffic_command_drained(tmp_path, monkeypatch):
    """`refresh_traffic` 已进命令表: 投递 -> 主循环 drain -> 回执 ok 且快照已刷新"""
    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch)

    resp = mgr.web.post_command("refresh_traffic", {"event_id": 9, "day": date.today().isoformat()})
    mgr.web.consume_commands()

    rec = mgr.web.results.get(resp["cmd_id"])
    assert rec is not None and rec["status"] == "ok", f"命令未注册或执行失败: {rec}"
    assert mgr.web.traffic_view["history"], "drain 后快照未刷新"


def test_end_to_end_notify_then_state_shows_fresh_traffic(tmp_path, monkeypatch):
    """端到端(进程内): 真端点 -> 命令队列 -> 真主循环 handler -> 快照刷新 -> /api/state 可见

    这是「工具发事件 -> WebUI 历史图与顶栏刷新」那条链路的进程内等价物(真机联调留待 S10):
    `/api/state` 的 `status.traffic` 就是顶栏 pill 与历史弹层共同的取数位, 另一个取数位是
    `/api/traffic/history` —— 两者同源(同一个 traffic_view), 这里两个都断言。
    """
    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app

    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch)
    # S17: 来源单一开关是 provider(旧的 global_traffic_monitor.enabled 键已退休)
    mgr.config.traffic_source.provider = "global_traffic_monitor"
    # D1: 两来源参数可并存, provider=工具面时曲线取数走 global_traffic_monitor.data_dir 下的
    # history_traffic.dat(与 TM 面同一文件, 跨包契约文件名); 指向夹具已写好的 dat 所在目录
    mgr.config.traffic_source.global_traffic_monitor.data_dir = str(tmp_path)
    setattr(mgr.web, _CRED_FIELD, "e2e-credential")
    client = TestClient(create_app(mgr))
    headers = {_AUTH_KEY: f"Bearer {getattr(mgr.web, _CRED_FIELD)}"}
    today = date.today().isoformat()
    event = {
        "event_id": 1,
        "day": today,
        "up_bytes": 3 * MIB,
        "down_bytes": 5 * MIB,
        "total_bytes": 8 * MIB,
        "ts": 1.0e9,
    }

    resp = client.post(tool_client.NOTIFY_PATH, json=event, headers=headers)
    assert resp.status_code == 200 and resp.json()["action"] == "refresh_queued"
    mgr.web.consume_commands()  # 主循环命令线(真 handler + 真 speed_curve 模块)

    traffic = client.get("/api/state?view=group", headers=headers).json()["status"]["traffic"]
    assert [p["period"] for p in traffic["periods"]] == ["day", "month"]
    assert traffic["history"] == [{"date": today, "up": 3 * MIB, "down": 5 * MIB}]
    assert client.get("/api/traffic/history", headers=headers).json()["history"] == traffic["history"]


def test_mock_config_section_starts_no_thread(tmp_path):
    """桩配置 + 桩 web 门面(属性恒真)不得被当成「已联动」而起订阅线程 —— 不等/恒等类型判据守阵

    依据 pitfalls/testing/hot-reload-mock-sections.md 的同族形态: 热重载守阵惯用 MagicMock 当新
    配置, 真值判会让本组件对着假 URL 起一条常驻订阅线程(实测顺带污染后续用例的线程清点)。
    !web 门面也必须桩掉 —— 只桩 config 时真门面的空密钥会替它挡住, 真值判的回归就漏检了。
    """
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config = mock.MagicMock(name="mock_config")
    mgr.web = mock.MagicMock(name="mock_web")
    sub = tool_client.TrafficMonitorSubscriber(mgr)
    assert sub._desired() == (False, "当前流量来源不是全局流量监视器(traffic_source.provider != global_traffic_monitor)")
    sub.sync()
    assert sub._thread is None, "不应起订阅线程"
    assert not _sub_threads()

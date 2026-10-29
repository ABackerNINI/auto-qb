"""test_traffic_monitor_client 测试计划: 全局流量监视器订阅客户端 + 通知触发的流量快照刷新(计划 26-10-16-0541 S7 / 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_desired_gates: 期望订阅态三道闸(来源 provider / WEBUI 未启用 / 访问密钥未就绪)
  —— 任一不满足即不订阅, 原因文案可读
- test_desired_gates_source_off: 总开关闸(S1/D1, 26-10-17-1737): traffic_source.enabled=false
  -> 不订阅(首行闸), _pass 不发任何控制面请求; 开回来自动恢复
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
- test_snapshot_refresh_republishes_readonly: 只读刷新: 历史行 + 各周期累计重算发布, limit 段一字不动, 不读不写 qB 限速
- test_snapshot_refresh_ignores_curve_config_marks_stale_when_unavailable: 曲线未启用也照发历史(A1);
  dat 缺失 / 无有效行 -> 返回 False 且 source 段转 stale(history 清空), limit 段仍沿用
- test_snapshot_refresh_source_off_publishes_off: 来源总开关关(S1/D1) -> 通知刷新不跳过,
  发布 off 快照(上一份可能是 ok 旧数据), 不读 dat 不碰 qB
- test_refresh_traffic_command_drained: `refresh_traffic` 已进命令表且经主循环 drain 执行后快照刷新(回执 ok)
- test_source_signature_tracks_source_keys: 切源指纹只认 enabled/provider/文件来源路径三位, 无关段不进指纹, 缺段桩配置取默认(S8)
- test_reload_config_source_change_refreshes_immediately: 切源即刷新 —— 热重载换来源后同一 drain 内快照即为新来源数据(不等 interval), 不碰 qB(S8)
- test_reload_config_source_off_publishes_off: 总开关关闭保存后立即转 off 关闭态(S8)
- test_reload_config_unchanged_source_does_not_refresh: 无关配置保存不触发刷新(指纹相等不投递)(S8)
- test_end_to_end_notify_then_state_shows_fresh_traffic: 端到端(进程内): 真端点 -> 命令队列 -> 真 handler ->
  事件零读盘补丁 day 行(26-10-21) + 兜底读盘补 month/历史 -> /api/state 与 /api/traffic/history 两取数位可见
- test_mock_config_section_starts_no_thread: 桩配置(MagicMock 段)不得被当成「已联动」起订阅线程 —— 不等/恒等类型判据守阵
- test_register_token_missing_then_unreachable_then_no_id: _register 三态(密钥缺失/不可达/缺 id)只记错不抛不置 sub_id(P0-T0.1)
- test_register_missing_id_in_response: 200 缺 id -> 不进心跳态(下轮重试)
- test_heartbeat_failure_branches_return_still_valid: _heartbeat 不可达/被拒(非 404) -> 一律 True(租约兜底不当失效)
- test_unregister_defensive_and_failure_branches: _unregister 缺 reg_tool 跳过 / 密钥不可读跳过 / 不可达静默
- test_unregister_rejected_by_tool_records_only: 注销被拒(409)只记 INFO 不抛
- test_pass_force_relaunch_consumed_by_thread: force_relaunch 只本轮生效(读到即清并转 agent)
- test_heartbeat_interval_fallback_on_bad_value: 心跳周期缺/非数值/<=1s 回落缺省(防节拍归零紧循环)
- test_ensure_thread_idempotent_when_alive: _ensure_thread 幂等(线程已存活时复用同一条, 不重复起)(P2-T2.5)
- test_run_survives_pass_and_unregister_exceptions: 主循环容错(单轮异常不杀线程 / 收线注销异常只记 WARNING)(P2-T2.5)
- test_clear_error_logs_recovery_info: 失败后恢复补 INFO 且清记忆, 无失败记忆时零日志(P2-T2.5)
  ⚠ 本轮修三处**假绿**(P2-T2.5): `_FAKE_EP.token_path` 是空串, 而 `_register`/`_heartbeat`/`_unregister`
    第一步都是 `read_token(...)` —— 「不可达 / 200 缺 id / 注销不可达」三类断言实际走的是
    「密钥不可读」早退分支, 目标分支从未执行。已改用 `_ep_with_token(tmp_path)`(真读得到密钥的端点),
    并补 `tool.paths()` 断言确保请求真的发出。
"""
import io
import json
import logging
import threading
import time
from datetime import date
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
from auto_qb.core.traffic_source import agent
from auto_qb.webui import tool_client
from helpers import dat_text, make_manager, wait_until, write_credential_file

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
    _write_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
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


def test_desired_gates_source_off(sub_env):
    """总开关闸(S1/D1, 26-10-17-1737): traffic_source.enabled=false -> 不订阅(首行闸)"""
    mgr, sub, tool = sub_env
    assert sub._desired() == (True, "")
    mgr.config.traffic_source.enabled = False
    want, why = sub._desired()
    assert want is False and "enabled=false" in why
    # _pass 走期望态为假分支: 不发任何控制面请求(不探活不注册), 返回 False(该收线)
    assert sub._pass() is False
    assert tool.paths() == []
    # 开回来自动恢复(不重配别的)
    mgr.config.traffic_source.enabled = True
    assert sub._desired() == (True, "")


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
        assert wait_until(lambda: tool.paths() == ["/status"], poll=0.01), "线程未发起探活调用"
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
        assert wait_until(lambda: not _sub_threads(), poll=0.01), "释放假死后订阅线程未收线"


# ---------- 线程生命周期 ----------


def test_thread_lifecycle_sync_then_stop(sub_env):
    """sync 起订阅线程并完成注册; stop 收线前把订阅注销掉"""
    _mgr, sub, tool = sub_env
    sub.sync()
    assert wait_until(lambda: "/subscribe" in tool.paths(), poll=0.01), "sync 后线程未注册"
    assert sub._thread is not None and sub._thread.is_alive()
    sub.stop()
    assert wait_until(lambda: "/unsubscribe" in tool.paths(), poll=0.01), "stop 未注销订阅"
    assert wait_until(lambda: not _sub_threads(), poll=0.01), "订阅线程未退出"


def test_thread_self_terminates_when_disabled(sub_env):
    """来源中途切走 + sync -> 线程读到期望态为假, 注销后自行退出(不必等 stop)"""
    mgr, sub, tool = sub_env
    sub.sync()
    assert wait_until(lambda: "/subscribe" in tool.paths(), poll=0.01)
    mgr.config.traffic_source.provider = "traffic_monitor"
    sub.sync()
    assert wait_until(lambda: "/unsubscribe" in tool.paths(), poll=0.01), "切走来源后未注销"
    assert wait_until(lambda: not _sub_threads(), poll=0.01), "订阅线程未自行退出"


# ---------- 只读刷新(speed_curve 模块 + WEB 命令) ----------


def _point_at(data_dir, monkeypatch) -> None:
    """造一份只读发现指针(D6): 取数路径解析读它, 不探活 —— 端到端测试无需起工具进程

    R2/D20: 工具来源的 dat 路径只有这一个来源; 配置里不再有 data_dir 可指。
    """
    path = data_dir / agent.ENDPOINT_FILE_NAME
    path.write_text(
        json.dumps(
            {
                "schema": agent.ENDPOINT_SCHEMA,
                "host": POINTER_HOST,
                "port": POINTER_PORT,
                "token_path": str(data_dir / "monitor.token"),
                "data_dir": str(data_dir),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(path))


def _refresh_env(tmp_path, monkeypatch, *, enabled=True, dat_name="history_traffic.dat", write_dat=True, qb_calls=None):
    """构造可刷新的环境 -> (mgr, dat 路径, qB 限速调用记录器)

    qB 的限速读写被替身为记录器(lambda 里 append): 「只读刷新」的守阵据此断言一次调用都没有。
    write_dat=False 用于造「dat 缺失」形态(只给路径不落文件)。
    """
    calls = qb_calls if qb_calls is not None else []
    mgr = make_manager(str(tmp_path / "state.json"))
    dat_path = tmp_path / dat_name
    if write_dat:
        dat_path.write_text(dat_text([(date.today(), 3 * MIB, 5 * MIB)]), encoding="utf-8")
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
    # 上一份快照(新契约形状, 26-10-18-0813 A2): 曲线已发布过一轮 -> limit 有目标/实读
    mgr.web.traffic_view = {
        "state": "ok",
        "periods": [],
        "history": [],
        "ts": 1.0,
        "date": "1970-01-01",
        "source": {
            "state": "ok",
            "reasons": []
        },
        "limit": {
            "target": {
                "up": 1,
                "down": 2
            },
            "actual": {
                "up": 1,
                "down": 2
            },
            "reasons": [],
            "state": "ok",
        },
    }
    return mgr, str(dat_path), calls


def test_snapshot_refresh_republishes_readonly(tmp_path, monkeypatch):
    """只读刷新: 历史行 + 各周期累计重算发布; limit 段一字不动; **不读不写 qB 限速**

    26-10-18-0813 A4/A5: 通知触发的刷新改指 `traffic_snapshot.refresh()` —— 它 own 来源段,
    曲线段由曲线模块写, 所以这里的判据是「写了 source/periods/history, 没碰 limit」。
    """
    mgr, _dat, qb_calls = _refresh_env(tmp_path, monkeypatch)
    mod = mgr.host.get("traffic_snapshot")

    assert mod.refresh() is True

    view = mgr.web.traffic_view
    today = date.today().isoformat()
    assert view["history"] == [{"date": today, "up": 3 * MIB, "down": 5 * MIB}]
    assert [(p["period"], p["up"], p["down"])
            for p in view["periods"]] == [("day", 3 * MIB, 5 * MIB), ("month", 3 * MIB, 5 * MIB)]
    assert view["date"] == today and view["ts"] > 1.0
    assert view["source"] == {"state": "ok", "reasons": []}
    # 段隔离(D10): 来源刷新**不得**动曲线那段(限速浮层的目标/实读值原样保留)
    assert view["limit"] == {
        "target": {
            "up": 1,
            "down": 2
        },
        "actual": {
            "up": 1,
            "down": 2
        },
        "reasons": [],
        "state": "ok",
    }
    assert view["state"] == "ok"  # 派生值: 两段皆 ok
    assert qb_calls == [], f"只读刷新不得碰 qB 限速: {qb_calls}"


def test_snapshot_refresh_ignores_curve_config_marks_stale_when_unavailable(tmp_path, monkeypatch):
    """曲线未启用也照发历史(A1 解耦判据); dat 缺失 / 无有效行 -> 返回 False 且 source 转 stale"""
    # 曲线关掉: 来源侧照刷新 —— 这正是「没配曲线也能看历史图」的落点, 与曲线是否 enabled 无关
    mgr, _dat, qb_calls = _refresh_env(tmp_path, monkeypatch, enabled=False)
    assert mgr.host.get("traffic_snapshot").refresh() is True
    assert mgr.web.traffic_view["history"] == [{"date": date.today().isoformat(), "up": 3 * MIB, "down": 5 * MIB}]
    assert qb_calls == []

    # dat 缺失: 返回 False(没有新数据), 但快照必须显式转 stale —— 不能停在上一份 ok 旧数据上
    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch, dat_name="not-there.dat", write_dat=False)
    assert mgr.host.get("traffic_snapshot").refresh() is False
    view = mgr.web.traffic_view
    assert view["source"]["state"] == "stale" and view["state"] == "stale"
    # 历史行清空; periods 保留固定两行(值归零) —— 形状稳定, 前端不必为 stale 特判行数
    assert view["history"] == []
    assert [(p["period"], p["up"], p["down"]) for p in view["periods"]] == [("day", 0, 0), ("month", 0, 0)]
    # stale 只是来源段的事: 曲线段仍是上一轮写的值
    assert view["limit"]["state"] == "ok" and view["limit"]["target"] == {"up": 1, "down": 2}

    # 无有效行(只有表头): 同 stale 口径
    empty = tmp_path / "empty.dat"
    empty.write_text('lines: "0"\n', encoding="utf-8")
    mgr.config.traffic_source.traffic_monitor.dat_path = str(empty)
    assert mgr.host.get("traffic_snapshot").refresh() is False
    assert mgr.web.traffic_view["source"]["state"] == "stale"
    assert mgr.web.traffic_view["history"] == []


def test_snapshot_refresh_source_off_publishes_off(tmp_path, monkeypatch):
    """来源总开关关(S1/D1, 26-10-17-1737): 通知到达时来源已关 -> 发布 off 快照(不跳过)

    上一份快照可能还是 ok(旧数据): 必须显式翻成 off, 与曲线任务口径一致; 返回 False
    (没有新数据可发), 不碰 qB 限速。limit 段一并复位 disabled(来源关了没有"命中目标"可言)。
    """
    mgr, _dat, qb_calls = _refresh_env(tmp_path, monkeypatch)
    mgr.config.traffic_source.enabled = False
    assert mgr.host.get("traffic_snapshot").refresh() is False

    view = mgr.web.traffic_view
    assert view["state"] == "off"
    assert view["source"]["state"] == "off"
    assert view["source"]["reasons"][0]["code"] == "source_off"
    assert view["history"] == [] and view["periods"] == []  # 不读 dat
    assert view["limit"] == {
        "target": {
            "up": None,
            "down": None
        },
        "actual": {
            "up": None,
            "down": None
        },
        "reasons": [],
        "state": "disabled"
    }
    assert qb_calls == []


def test_refresh_traffic_command_drained(tmp_path, monkeypatch):
    """`refresh_traffic` 已进命令表: 投递 -> 主循环 drain -> 回执 ok 且快照已刷新"""
    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch)

    resp = mgr.web.post_command("refresh_traffic", {"event_id": 9, "day": date.today().isoformat()})
    mgr.web.consume_commands()

    rec = mgr.web.results.get(resp["cmd_id"])
    assert rec is not None and rec["status"] == "ok", f"命令未注册或执行失败: {rec}"
    assert mgr.web.traffic_view["history"], "drain 后快照未刷新"


def test_source_signature_tracks_source_keys():
    """切源指纹(1737-S8): 只认 enabled / provider / 文件来源路径三位 —— 曲线等无关段不进指纹

    指纹是「热重载前后各算一次再相等比较」的判据, 因此必须**只由配置事实构成**(工具来源的
    dat 路径是运行时指针, 算进来会让无关保存偶发触发刷新); 缺段的桩配置按「默认开启 + 文件
    来源 + 空路径」处理, 不抛。
    """
    from types import SimpleNamespace

    from auto_qb.core.traffic_source import paths

    def cfg(**kw):
        """config 形状: 来源全在顶层 traffic_source 段里(S15 起不再有独立 global_traffic_monitor 段)"""
        return SimpleNamespace(
            traffic_source=SimpleNamespace(
                enabled=kw.get("enabled", True),
                provider=kw.get("provider", "traffic_monitor"),
                traffic_monitor=SimpleNamespace(dat_path=kw.get("dat_path", "D:/tm/history_traffic.dat")),
            ),
            # 与本指纹无关的段: 改它不得影响判定(否则「保存任意配置都刷新」)
            global_speed_limit_curve=SimpleNamespace(interval=kw.get("interval", 600.0)),
        )

    base = paths.source_signature(cfg())
    assert base == (True, "traffic_monitor", "D:/tm/history_traffic.dat")
    assert paths.source_signature(cfg(enabled=False)) != base
    assert paths.source_signature(cfg(provider="global_traffic_monitor")) != base
    assert paths.source_signature(cfg(dat_path="E:/other/history_traffic.dat")) != base
    # 无关段变化 / 空白路径去空格: 指纹不变(等价)
    assert paths.source_signature(cfg(dat_path="  D:/tm/history_traffic.dat  ")) == base
    assert paths.source_signature(SimpleNamespace()) == (True, "traffic_monitor", "")


def test_reload_config_source_change_refreshes_immediately(tmp_path, monkeypatch):
    """切源即刷新(1737-S8 主判据): 热重载换了来源 -> **同一个 drain 内**快照就是新来源的数据

    复现#7/#8: 旧实现只在曲线任务到点(约 10min)时才重读, 保存完历史图仍是旧来源数据。断言用
    快照的 ts 前进 + history 逐行对齐新来源, 且全程不碰 qB 限速(只读刷新)。
    """
    mgr, _dat_file, qb_calls = _refresh_env(tmp_path, monkeypatch)
    tool_dir = tmp_path / "tool-data"
    tool_dir.mkdir()
    (tool_dir / "history_traffic.dat").write_text(dat_text([(date.today(), 9 * MIB, 1 * MIB)]), encoding="utf-8")
    _point_at(tool_dir, monkeypatch)  # 工具来源的数据目录(取数只读指针, 不探活)
    ts_before = mgr.web.traffic_view["ts"]

    def _apply(_cfg):
        # 等价于用户把来源切到工具后保存: 新配置对象落到 ctx.config, 指纹随之变化
        mgr.config.traffic_source.provider = "global_traffic_monitor"

    mgr.apply_new_config = _apply
    mgr.web.commands.put(("reload_config", {"config": object()}))
    mgr.web.consume_commands()

    view = mgr.web.traffic_view
    assert view["ts"] > ts_before, "切源后必须立即重发快照(不等曲线 interval)"
    assert view["history"] == [{"date": date.today().isoformat(), "up": 9 * MIB, "down": 1 * MIB}]
    assert qb_calls == [], f"切源触发的刷新不得碰 qB 限速: {qb_calls}"


def test_reload_config_source_off_publishes_off(tmp_path, monkeypatch):
    """切源即刷新(1737-S8 验收二): 总开关关闭保存后 -> 立即转 off 关闭态(不等曲线任务)"""
    mgr, _dat_file, qb_calls = _refresh_env(tmp_path, monkeypatch)

    def _apply(_cfg):
        mgr.config.traffic_source.enabled = False

    mgr.apply_new_config = _apply
    mgr.web.commands.put(("reload_config", {"config": object()}))
    mgr.web.consume_commands()

    assert mgr.web.traffic_view["state"] == "off"
    assert mgr.web.traffic_view["history"] == []  # 关源不读 dat
    assert qb_calls == []


def test_reload_config_unchanged_source_does_not_refresh(tmp_path, monkeypatch):
    """无关配置保存不得触发刷新: 指纹相等即不投递(快照引用原样, 一次读盘都不发生)"""
    mgr, _dat_file, _calls = _refresh_env(tmp_path, monkeypatch)
    snap = mgr.web.traffic_view

    mgr.apply_new_config = lambda _cfg: None  # 来源段没变(只有别的段改了)
    mgr.web.commands.put(("reload_config", {"config": object()}))
    mgr.web.consume_commands()

    # 快照整体替换语义(单写线程原子换引用): 没刷新就是**同一个对象**
    assert mgr.web.traffic_view is snap
    assert mgr.web.commands.empty(), "指纹相等时不得投递 refresh_traffic"


def test_end_to_end_notify_then_state_shows_fresh_traffic(tmp_path, monkeypatch):
    """端到端(进程内): 事件 -> 载荷补丁(零读盘) + 兜底读盘 -> /api/state 两取数位可见

    这是「工具发事件 -> WebUI 历史图与顶栏刷新」那条链路的进程内等价物(真机联调留待 S10):
    `/api/state` 的 `status.traffic` 就是顶栏 pill 与限速浮层的取数位(periods + source/limit
    段), 另一个取数位是 `/api/traffic/history` —— 两者同源(同一个 traffic_view), 这里两个都断言。

    26-10-21 改制(用户拍板「读盘本身就是副作用, 事件基本无副作用应立即刷新」)后链路分两段:
    事件路径**零读盘** —— 命令把六键自带的当日权威累计补丁进 periods 的 day 行(顶栏 pill 的
    取数位); month 行与历史行仍由文件读盘派生(refresh_interval 兜底节拍; 生产首拍即跑,
    冷启动竞态实际不存在)。本用例把两段都走一遍: 先事件补丁, 再模拟一次兜底读盘(任务执行体)。

    A5 载荷瘦身: 轮询响应里**没有** `history`(几百行每轮回传是纯浪费), 历史行只走专用端点 ——
    本用例同时守住这条边界, 否则「顺手把 history 塞回去」不会被任何断言拦住。
    """
    from fastapi.testclient import TestClient

    from auto_qb.core.taskqueue import Task
    from auto_qb.webui import create_app

    mgr, _dat, _calls = _refresh_env(tmp_path, monkeypatch)
    # S17: 来源单一开关是 provider(旧的 global_traffic_monitor.enabled 键已退休)
    mgr.config.traffic_source.provider = "global_traffic_monitor"
    # R2/D20: 工具来源的 dat 路径来自**发现指针**(配置里已无 data_dir); 这里造一份指向夹具
    # dat 所在目录的指针 —— 取数只读指针、不探活, 故无需起工具进程
    _point_at(tmp_path, monkeypatch)
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
    mgr.web.consume_commands()  # 主循环命令线(真 handler + 真 traffic_snapshot 模块)

    # 第一段(事件路径): day 行已是事件自带累计; month 行等兜底读盘补(冷启动竞态, 生产不存在)
    traffic = client.get("/api/state?view=group", headers=headers).json()["status"]["traffic"]
    assert [(p["period"], p["up"], p["down"]) for p in traffic["periods"]] == [("day", 3 * MIB, 5 * MIB)]
    assert traffic["source"]["state"] == "ok"
    assert "history" not in traffic, "A5: 轮询载荷不得再带 history"

    # 第二段(兜底读盘, 生产首拍即跑): 补齐 month 行 + 历史行
    mod = mgr.host.get("traffic_snapshot")
    mod.handle_traffic_snapshot(Task("internal", "traffic_snapshot_refresh", interval=600), dry_run=False)

    traffic = client.get("/api/state?view=group", headers=headers).json()["status"]["traffic"]
    assert [p["period"] for p in traffic["periods"]] == ["day", "month"]
    assert traffic["source"]["state"] == "ok"
    assert "history" not in traffic, "A5: 轮询载荷不得再带 history"

    expected = [{"date": today, "up": 3 * MIB, "down": 5 * MIB}]
    history = client.get("/api/traffic/history", headers=headers).json()["history"]
    assert history == expected


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


# ---------- P0-T0.1: 订阅客户端控制面动作的失败/防御分支 ----------

_FAKE_EP = agent.ToolEndpoint(
    base_url=f"http://{POINTER_HOST}:{POINTER_PORT}",
    token_path="",
    data_dir="",
    version="0.1.0",
    pid=4321,
    autostart_registered=True,
    autostart_error=None,
)


def _ep_with_token(tmp_path, **kw) -> "agent.ToolEndpoint":
    """带**可读密钥**的端点替身 —— 「分支真抵达」的前提(pitfalls/testing/unreached-branch-guard.md)

    坑(本轮实测): `_FAKE_EP.token_path` 是空串, 而 `_register` / `_heartbeat` / `_unregister`
    第一件事都是 `read_token(...)`, 读不到就**早退**。于是「工具不可达 / 200 缺 id / 注销被拒」
    这三类断言虽然通过, 走的却是「密钥不可读」那条路 —— 目标分支从未执行(假绿)。
    本助手给出真读得到密钥的端点, 让异常/被拒分支真正抵达。
    """
    return agent.ToolEndpoint(
        base_url=kw.get("base_url", _FAKE_EP.base_url),
        token_path=write_credential_file(tmp_path),
        data_dir="",
    )


def test_register_token_missing_then_unreachable_then_no_id(sub_env, tmp_path):
    """_register 三态: 密钥缺失只记错不抛 / 不可达只记错不抛 / 200 缺 id 同口径"""
    _mgr, sub, tool = sub_env
    ep = agent.ToolEndpoint(
        base_url=_FAKE_EP.base_url,
        token_path="/nonexistent/monitor.token",
        data_dir="",
    )
    # 密钥文件缺失 -> 记错(不注册, 不抛)
    sub._register(ep)
    assert sub._sub_id == "" and tool.paths() == []
    # 不可达 -> ToolUnreachable 收编为记错(密钥可读, 确保走的是"不可达"而不是"密钥缺失"早退)
    ep2 = _ep_with_token(tmp_path)
    tool.raise_exc = tool_client.ToolUnreachable("refused")
    sub._register(ep2)
    assert sub._sub_id == ""
    assert tool.paths() == ["/subscribe"], "必须真的发出注册请求才谈得上不可达"


def test_register_missing_id_in_response(sub_env, tmp_path):
    """200 但响应缺 id: 记错且不置 sub_id(下轮重试, 不进入心跳态)"""
    _mgr, sub, tool = sub_env
    # 工具侧 200 但不回 id: 经 _FakeTool 的默认脚本改一件
    real_call = tool.__call__

    def no_id(base, path, method, credential, payload=None, timeout=None):
        if path == "/subscribe":
            tool.calls.append((path, dict(payload or {})))
            return 200, {"ok": True}
        return real_call(base, path, method, credential, payload, timeout)

    tool_client.call_tool, _saved = no_id, tool_client.call_tool
    try:
        sub._register(_ep_with_token(tmp_path))
        assert sub._sub_id == ""
        assert tool.paths() == ["/subscribe"], "密钥可读, 必须真的打到 /subscribe 才谈得上缺 id"
    finally:
        tool_client.call_tool = _saved


def test_heartbeat_failure_branches_return_still_valid(sub_env, tmp_path):
    """_heartbeat 三态: 密钥缺失 / 不可达 / 被拒(非 404) -> 一律 True(租约兜底, 不当失效)"""
    _mgr, sub, tool = sub_env
    sub._pass()  # 先注册
    assert sub._sub_id == "sub-1"
    ep = _ep_with_token(tmp_path)
    tool.raise_exc = tool_client.ToolUnreachable("refused")
    assert sub._heartbeat(ep) is True, "工具不可达不算失效(180s 租约给三次机会)"
    assert "/heartbeat" in tool.paths(), "必须真的发心跳才谈得上不可达"
    tool.raise_exc = None
    tool.heartbeat_codes = [500]
    assert sub._heartbeat(ep) is True, "被拒只记错, 不立刻重注册"
    # 密钥不可读: 跳过本轮心跳但**仍算订阅有效**(不因此重注册, 也不发请求)
    before = len(tool.calls)
    assert sub._heartbeat(agent.ToolEndpoint(base_url=_FAKE_EP.base_url, token_path="", data_dir="")) is True
    assert len(tool.calls) == before, "密钥不可读不得发心跳请求"


def test_unregister_defensive_and_failure_branches(sub_env, tmp_path):
    """_unregister 防御/失败分支: 缺 reg_tool 寻址跳过 / 密钥不可读跳过 / 不可达静默 / 非 200-404 被拒"""
    _mgr, sub, tool = sub_env
    # sub_id 在但 reg_tool  None(同生同灭被破坏的纯防御路径)
    sub._sub_id, sub._reg_tool = "sub-x", None
    sub._unregister("测试")
    assert tool.paths() == [], "缺注册时寻址信息不得发注销请求"
    # 密钥不可读 -> 跳过
    sub._sub_id, sub._reg_tool = "sub-x", ("http://127.0.0.1:9", "/nonexistent/token")
    sub._unregister("测试")
    assert tool.paths() == []
    # 不可达 -> 静默(租约兜底); 密钥可读, 确保走的是"不可达"而不是"密钥不可读"早退
    sub._sub_id, sub._reg_tool = "sub-x", (f"http://127.0.0.1:{POINTER_PORT}", write_credential_file(tmp_path))
    tool.raise_exc = tool_client.ToolUnreachable("refused")
    sub._unregister("测试")
    assert sub._sub_id == ""
    assert "/unsubscribe" in tool.paths(), "必须真的发注销请求才谈得上不可达"
    # 工具回 409(拒绝注销)只记 INFO 不抛的场景由 test_unregister_rejected_by_tool_records_only 直驱


def test_unregister_rejected_by_tool_records_only(sub_env):
    """注销被拒(工具回 409): 只记 INFO 不抛; 404 等价于已注销"""
    _mgr, sub, tool = sub_env
    sub._pass()
    assert sub._sub_id == "sub-1"
    # 走工具替身的 /unsubscribe 分支: 默认 200; 改为 409 需替换脚本
    real_call = tool.__call__

    def rejected(base_, path, method, credential, payload=None, timeout=None):
        if path == "/unsubscribe":
            return 409, {"error": "unknown id"}
        return real_call(base_, path, method, credential, payload, timeout)

    tool_client.call_tool, _saved = rejected, tool_client.call_tool
    try:
        with _LogCapture("auto_qb.webui.tool_client") as buf:
            sub._unregister("测试被拒")
        assert "注销被拒" in buf.getvalue()
    finally:
        tool_client.call_tool = _saved


def test_pass_force_relaunch_consumed_by_thread(sub_env):
    """force_relaunch 只在本轮生效: _pass 读到即清并转 agent(不跨轮残留)"""
    mgr, sub, tool = sub_env
    # 不起真线程: 避免订阅线程抢先把标志消费掉(标志生命周期在本测试内断言)
    real_ensure = tool_client.TrafficMonitorSubscriber._ensure_thread
    tool_client.TrafficMonitorSubscriber._ensure_thread = lambda self: None
    try:
        assert sub.request_relaunch() is True
        assert sub._force_relaunch is True
        sub._pass()
        assert sub._force_relaunch is False, "立即拉起标志必须本轮消费掉"
        assert len(tool.launches) == 0, "探活成功时不触发拉起"
    finally:
        tool_client.TrafficMonitorSubscriber._ensure_thread = real_ensure


def test_heartbeat_interval_fallback_on_bad_value():
    """心跳周期取值: 缺/非数值/<=1s 一律回落缺省(防响应格式变化把节拍打成 0 紧循环)"""
    assert tool_client._heartbeat_interval({}) == tool_client._DEFAULT_HEARTBEAT_S
    assert tool_client._heartbeat_interval({"heartbeat_interval_s": "abc"}) == tool_client._DEFAULT_HEARTBEAT_S
    assert tool_client._heartbeat_interval({"heartbeat_interval_s": 0.5}) == tool_client._DEFAULT_HEARTBEAT_S
    assert tool_client._heartbeat_interval({"heartbeat_interval_s": 45}) == 45.0


def test_ensure_thread_idempotent_when_alive(sub_env):
    """_ensure_thread 幂等: 线程已存活时再调**不重复起**(否则每次 sync 都多一条订阅线程)"""
    _mgr, sub, _tool = sub_env
    try:
        sub._ensure_thread()
        first = sub._thread
        assert first is not None and first.is_alive()
        sub._ensure_thread()
        assert sub._thread is first, "已存活必须复用同一条线程"
    finally:
        sub.stop()


def test_run_survives_pass_and_unregister_exceptions(sub_env, monkeypatch):
    """订阅线程主循环的两条容错: 单轮异常不杀线程(下轮重试) / 收线注销异常只记 WARNING

    与工具侧「单轮落盘失败不杀守护进程」同纪律: 订阅是长期后台件, 一轮异常就退线等于
    一次网络抖动永久失去流量快照。`_run` 同步直调(不真起线程), 保证断言的是循环本身。
    """
    _mgr, sub, _tool = sub_env
    seen = []

    def _pass():
        seen.append(1)
        if len(seen) == 1:
            raise RuntimeError("单轮异常")
        return False

    monkeypatch.setattr(sub, "_pass", _pass)
    monkeypatch.setattr(sub, "_wake", SimpleNamespace(wait=lambda s: None, clear=lambda: None))

    def _boom(reason):
        raise RuntimeError("注销异常")

    monkeypatch.setattr(sub, "_unregister", _boom)
    sub._stop.clear()
    sub._run()  # 首轮异常 -> want=True 继续; 次轮 False 收线
    assert len(seen) == 2, "单轮异常后必须再跑一轮(不杀线程)"


def test_clear_error_logs_recovery_info(sub_env):
    """失败后恢复: 清失败记忆并补一条 INFO(失败不静默消失); 无失败记忆时零日志"""
    _mgr, sub, _tool = sub_env
    sub._last_error = "工具不可达"
    with _LogCapture("auto_qb.webui.tool_client") as buf:
        sub._clear_error()
    assert "已恢复" in buf.getvalue() and "工具不可达" in buf.getvalue()
    assert sub._last_error == ""
    with _LogCapture("auto_qb.webui.tool_client") as buf2:
        sub._clear_error()
    assert buf2.getvalue() == "", "无失败记忆时不得再记"

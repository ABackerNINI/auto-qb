"""gtm 控制面守阵: POST /autostart / 配置回写 / 写临界区 / shutdown(从 test_server.py 原样搬迁)"""
from __future__ import annotations

import datetime
import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from types import SimpleNamespace
from typing import Optional

import pytest

from gtm.__main__ import _run_loop
from gtm.config import Config, ConfigHolder, load_config
from gtm.installer import AutostartError, AutostartResult, UnsupportedPlatformError
from gtm.sampler import Sampler
from gtm.server import ControlServer, TokenManager
from gtm.storage import ENDPOINT_SCHEMA, Storage, write_endpoint

from server_support import *  # noqa: F401,F403

# ---- POST /autostart (S6: 自启开关; 工具进程内跑 installer, 替身注入) ----


class FakeBackend:
    """替身自启后端: 记录 register/unregister 调用; 返回可配结果或抛可配异常."""
    def __init__(self, result: Optional[AutostartResult] = None, exc: Optional[Exception] = None):
        self._result = result
        self._exc = exc
        self.calls: list[str] = []

    def register(self) -> AutostartResult:
        self.calls.append("register")
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result

    def unregister(self) -> AutostartResult:
        self.calls.append("unregister")
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


def _factory_recording(backend: FakeBackend):
    """返回 (factory, seen): factory 记录收到的 data_dir, 恒返回同一 backend 替身."""
    seen: list[str] = []

    def factory(data_dir: str) -> FakeBackend:
        seen.append(data_dir)
        return backend

    return factory, seen


def test_autostart_install_calls_register_with_process_data_dir(tmp_path) -> None:
    """install -> backend.register(); factory 收到的 data_dir = 本进程 storage.data_dir
    (不信任请求体 —— 注册项写死的就是进程数据目录)."""
    backend = FakeBackend(result=AutostartResult("registered", "已注册计划任务 gtm-autostart"))
    factory, seen = _factory_recording(backend)
    server, storage, sampler, holder, token = make_server(tmp_path, installer_factory=factory)
    try:
        status, payload = http(
            server,
            "POST",
            "/autostart",
            body={
                "action": "install",
                "data_dir": "/evil/elsewhere"
            },
            token=token.token()
        )
        assert status == 200 and payload == {"ok": True, "action": "registered", "message": "已注册计划任务 gtm-autostart"}
        assert backend.calls == ["register"]
        # factory 另被 start() 写发现指针时探 autostart_registered 调过一次; 两次都收进程 data_dir,
        # 请求体里的 /evil/elsewhere 从未出现 (被忽略)
        assert set(seen) == {storage.data_dir}
    finally:
        server.stop()


def test_autostart_uninstall_calls_unregister(tmp_path) -> None:
    backend = FakeBackend(result=AutostartResult("unregistered", "已卸载"))
    factory, _ = _factory_recording(backend)
    server, *_rest, token = make_server(tmp_path, installer_factory=factory)
    try:
        status, payload = http(server, "POST", "/autostart", body={"action": "uninstall"}, token=token.token())
        assert status == 200 and payload["action"] == "unregistered"
        assert backend.calls == ["unregister"]
    finally:
        server.stop()


def test_autostart_idempotent_noop_is_success(tmp_path) -> None:
    """幂等 no-op (skipped / absent) 也是 200 —— 期望态已达成, 开关不该报错."""
    for act, action_name in (("install", "skipped"), ("uninstall", "absent")):
        backend = FakeBackend(result=AutostartResult(action_name, "no-op"))
        factory, _ = _factory_recording(backend)
        server, *_rest, token = make_server(tmp_path / act, installer_factory=factory)
        try:
            status, payload = http(server, "POST", "/autostart", body={"action": act}, token=token.token())
            assert status == 200 and payload["action"] == action_name
        finally:
            server.stop()


def test_autostart_unsupported_platform_501(tmp_path) -> None:
    backend = FakeBackend(exc=UnsupportedPlatformError("当前平台不支持自启"))
    factory, _ = _factory_recording(backend)
    server, *_rest, token = make_server(tmp_path, installer_factory=factory)
    try:
        status, payload = http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())
        assert status == 501 and "不支持" in payload["error"]
    finally:
        server.stop()


def test_autostart_command_failure_500(tmp_path) -> None:
    backend = FakeBackend(exc=AutostartError("schtasks 失败 (rc=1)"))
    factory, _ = _factory_recording(backend)
    server, *_rest, token = make_server(tmp_path, installer_factory=factory)
    try:
        status, payload = http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())
        assert status == 500 and "schtasks" in payload["error"]
    finally:
        server.stop()


def test_autostart_bad_action_400(tmp_path) -> None:
    backend = FakeBackend(result=AutostartResult("registered", "x"))
    factory, _ = _factory_recording(backend)
    server, *_rest, token = make_server(tmp_path, installer_factory=factory)
    try:
        assert http(server, "POST", "/autostart", body={"action": "bogus"}, token=token.token())[0] == 400
        assert http(server, "POST", "/autostart", body={}, token=token.token())[0] == 400
        assert backend.calls == []  # 载荷非法 -> 不触后端
    finally:
        server.stop()


def test_autostart_requires_token(tmp_path) -> None:
    backend = FakeBackend(result=AutostartResult("registered", "x"))
    factory, _ = _factory_recording(backend)
    server, *_rest = make_server(tmp_path, installer_factory=factory)
    try:
        assert http(server, "POST", "/autostart", body={"action": "install"}, token=None)[0] == 401
        assert backend.calls == []
    finally:
        server.stop()


# ---- POST /autostart 回写 config autostart (S14/D13: 裁决权落定) ----


def test_autostart_install_writes_back_config_true(tmp_path) -> None:
    """S14/D13: install 成功把 config autostart 置 true 并落盘 —— run --autostart 据此注册."""
    backend = FakeBackend(result=AutostartResult("registered", "已注册"))
    factory, _ = _factory_recording(backend)
    server, storage, _sampler, holder, token = make_server(
        tmp_path, config=Config(autostart=False), installer_factory=factory
    )
    try:
        assert http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())[0] == 200
        assert holder.current.autostart is True  # 热换后的活配置
        loaded, errors = load_config(os.path.join(storage.data_dir, "config.yml"))
        assert errors == () and loaded.autostart is True  # 已原子落盘
    finally:
        server.stop()


def test_autostart_uninstall_writes_back_config_false(tmp_path) -> None:
    """S14/D13: uninstall 成功置 autostart=false —— 用户关过后, 再被拉起也不装回."""
    backend = FakeBackend(result=AutostartResult("unregistered", "已卸载"))
    factory, _ = _factory_recording(backend)
    server, storage, _sampler, holder, token = make_server(tmp_path, installer_factory=factory)
    try:
        assert http(server, "POST", "/autostart", body={"action": "uninstall"}, token=token.token())[0] == 200
        assert holder.current.autostart is False
        loaded, errors = load_config(os.path.join(storage.data_dir, "config.yml"))
        assert errors == () and loaded.autostart is False
    finally:
        server.stop()


def test_autostart_failure_leaves_config_untouched(tmp_path) -> None:
    """失败态不落半截裁决权: 注册失败 (500) 时 config autostart 保持原值 (仍为默认 true)."""
    backend = FakeBackend(exc=AutostartError("schtasks 失败 (rc=1)"))
    factory, _ = _factory_recording(backend)
    server, *_rest, holder, token = make_server(tmp_path, installer_factory=factory)
    try:
        assert http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())[0] == 500
        assert holder.current.autostart is True  # 未被改成 false
    finally:
        server.stop()


class StatefulAutostartBackend:
    """替身自启后端 (issue 26-10-31-0537): is_registered 跟随 register/unregister 翻转 ——
    现货态探测随之变, 供验证控制面操作后指针 autostart 字段即时 patch."""
    def __init__(self, registered: bool):
        self.registered = registered

    def is_registered(self) -> bool:
        return self.registered

    def register(self) -> AutostartResult:
        self.registered = True
        return AutostartResult("registered", "已注册")

    def unregister(self) -> AutostartResult:
        self.registered = False
        return AutostartResult("unregistered", "已卸载")


def test_autostart_uninstall_patches_pointer_immediately(tmp_path) -> None:
    """26-10-31-0537 回归: uninstall 成功后指针 autostart_registered 即时回写 false,
    不再等到工具下次重启才自愈; 其余指针字段不被 patch 破坏."""
    backend = StatefulAutostartBackend(registered=True)
    server, *_rest, token = make_server(tmp_path, installer_factory=lambda data_dir: backend)
    try:
        pointer = tmp_path / "endpoint.json"
        before = json.loads(pointer.read_text(encoding="utf-8"))
        assert before["autostart_registered"] is True  # 前提: start() 现货态探到已注册
        status, payload = http(server, "POST", "/autostart", body={"action": "uninstall"}, token=token.token())
        assert status == 200 and payload["action"] == "unregistered"
        after = json.loads(pointer.read_text(encoding="utf-8"))
        assert after["autostart_registered"] is False  # 即时回写真值 (修复前停在 true)
        assert after["autostart_error"] is None
        assert after["port"] == server.port and after["pid"] == before["pid"]  # 其余字段原样保留
    finally:
        server.stop()


def test_autostart_install_patches_pointer_and_clears_error(tmp_path) -> None:
    """26-10-31-0537 对称面: install 成功后指针即时回写 true, 启动期 autostart_error 已过时一并清空."""
    backend = StatefulAutostartBackend(registered=False)
    reason = "启动期注册失败: 拒绝访问"
    server, *_rest, token = make_server(tmp_path, installer_factory=lambda data_dir: backend, autostart_error=reason)
    try:
        pointer = tmp_path / "endpoint.json"
        before = json.loads(pointer.read_text(encoding="utf-8"))
        assert before["autostart_registered"] is False and before["autostart_error"] == reason
        status, payload = http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())
        assert status == 200 and payload["action"] == "registered"
        after = json.loads(pointer.read_text(encoding="utf-8"))
        assert after["autostart_registered"] is True
        assert after["autostart_error"] is None
    finally:
        server.stop()


def test_autostart_pointer_patch_failure_only_warns(tmp_path, caplog) -> None:
    """指针 patch 读失败 (指针损坏, 坏 JSON) 只 WARNING, 不阻断响应 —— 开关成败已由
    config 回写与 200 裁决. 指针缺失 (FileNotFoundError) 则静默幂等 (无 patch 对象)."""
    backend = StatefulAutostartBackend(registered=True)
    server, *_rest, token = make_server(tmp_path, installer_factory=lambda data_dir: backend)
    try:
        pointer = tmp_path / "endpoint.json"
        pointer.write_text("{not json", encoding="utf-8")  # 运行中指针被外力损坏 -> 读抛 ValueError
        status, payload = http(server, "POST", "/autostart", body={"action": "uninstall"}, token=token.token())
        assert status == 200 and payload["action"] == "unregistered"
        assert any("patch 失败" in r.getMessage() for r in caplog.records)
        # 缺失形态: 删掉指针后再开关一次, 不报错不补写 (patch 不是 create)
        caplog.clear()
        os.remove(pointer)
        status, _ = http(server, "POST", "/autostart", body={"action": "uninstall"}, token=token.token())
        assert status == 200
        assert not pointer.exists()
        assert not any("patch" in r.getMessage() for r in caplog.records)
    finally:
        server.stop()


def test_config_writes_serialized_put_and_autostart(tmp_path, monkeypatch) -> None:
    """T-01: PUT /config 与 POST /autostart 的落盘临界区互斥 (_config_write_lock).

    复刻丢更新交叠: /autostart 持锁读旧快照后在 save_config 内阻塞, 期间并发 PUT /config
    只能在锁外等待 —— autostart 的「旧快照 + autostart 位」整份回写先落, PUT 的全量
    覆盖后落, 刚改的参数不被还原。无锁时该交叠会让 sample_interval 回落 5S。
    """
    import gtm.server as server_module

    real_save = server_module.save_config
    calls: list[Config] = []
    entered = threading.Event()  # autostart 已持锁进入 save_config
    allow = threading.Event()

    def fake_save(path: str, config: Config) -> None:
        calls.append(config)
        if len(calls) == 1:
            entered.set()
            assert allow.wait(timeout=5)
        real_save(path, config)

    monkeypatch.setattr(server_module, "save_config", fake_save)
    backend = FakeBackend(result=AutostartResult("registered", "已注册"))
    factory, _ = _factory_recording(backend)
    server, storage, _sampler, holder, token = make_server(tmp_path, installer_factory=factory)
    try:
        t_auto = threading.Thread(
            target=lambda: http(server, "POST", "/autostart", body={"action": "install"}, token=token.token())
        )
        t_auto.start()
        assert entered.wait(timeout=5)
        put_results: list[tuple[int, dict]] = []
        t_put = threading.Thread(
            target=lambda: put_results.
            append(http(server, "PUT", "/config", body={"sample_interval": "9S"}, token=token.token()))
        )
        t_put.start()
        allow.set()
        t_auto.join(timeout=5)
        t_put.join(timeout=5)
        assert put_results and put_results[0][0] == 200
        # 落盘顺序: autostart (旧快照 + autostart 位) 先, PUT 全量后 —— 参数不丢
        assert len(calls) == 2
        assert calls[0].sample_interval == 5.0 and calls[0].autostart is True
        assert calls[1].sample_interval == 9.0
        # 终态两侧一致: 热换的活配置 + 磁盘文件都保住 PUT 的参数
        assert holder.current.sample_interval == 9.0 and holder.current.autostart is True
        loaded, errors = load_config(os.path.join(storage.data_dir, "config.yml"))
        assert errors == () and loaded.sample_interval == 9.0 and loaded.autostart is True
    finally:
        server.stop()


def test_put_config_rejects_non_loopback_http_host(tmp_path) -> None:
    """T-02 端点面: PUT /config 写非回环 http_host -> 400 (回环承诺由校验层兑现)."""
    server, *_rest, holder, token = make_server(tmp_path)
    try:
        status, payload = http(server, "PUT", "/config", body={"http_host": "0.0.0.0"}, token=token.token())
        assert status == 400
        assert any("回环" in e for e in payload["errors"])
        assert holder.current.http_host == "127.0.0.1"  # 旧配置不被半截覆盖
    finally:
        server.stop()


# ---- POST /shutdown (26-10-17-1737 S3: 优雅退出信号) ----


def test_shutdown_returns_200_then_sets_stop_event(tmp_path) -> None:
    """POST /shutdown: 先回 200, 再置位 stop_event (退出走 cmd_run 既有 finally).

    响应先上 wire 是契约: 客户端拿到 200 时事件可能已置位 —— 两者都断言, 且服务在
    置位后仍可再服务一个请求 (收尾在调用方, 不在本端点)。
    """
    stop = threading.Event()
    server, *_rest = make_server(tmp_path, stop_event=stop)
    try:
        assert not stop.is_set()
        status, payload = http(server, "POST", "/shutdown", token=server.token_manager.token())
        assert status == 200 and payload["ok"] is True
        assert stop.is_set()
        # 置位不自杀: 控制面仍能响应 (真正的退出由 cmd_run 的 finally 收尾)
        assert http(server, "GET", "/status", token=server.token_manager.token())[0] == 200
    finally:
        server.stop()


def test_shutdown_without_stop_event_still_200(tmp_path) -> None:
    """未绑定 stop_event (非 run 装配): /shutdown 仍回 200, 不置位不抛 (只 WARNING)."""
    server, *_rest = make_server(tmp_path)
    try:
        status, payload = http(server, "POST", "/shutdown", token=server.token_manager.token())
        assert status == 200 and payload["ok"] is True
    finally:
        server.stop()


def test_shutdown_wakes_run_loop(tmp_path) -> None:
    """端到端(进程内): stop_event 置位 -> _run_loop 的 stop_event.wait 即时醒, 不空等采样间隔."""
    stop = threading.Event()
    server, storage, sampler, holder, token = make_server(tmp_path, stop_event=stop)
    try:
        done = threading.Event()

        def loop():
            _run_loop(storage, sampler, holder, stop, None)  # 无 notifier: 只验停止响应
            done.set()

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        time.sleep(0.2)  # 让循环跑起来 (采样间隔 5s, 未停止时会睡满)
        assert not done.is_set()
        http(server, "POST", "/shutdown", token=token.token())
        assert done.wait(2.0), "stop_event 置位后 _run_loop 未在 2s 内退出 (停止信号没生效?)"
    finally:
        server.stop()

"""S3 控制面守阵: 鉴权 / 端点 / 租约 / 配置热重载 / 端口冲突 fail-fast.
+ S6 自启开关端点 POST /autostart (工具进程内跑 installer, 替身注入).
+ S12 发现指针: bind 成功后写 endpoint.json (字段/删除) + 抢输锁不占端口.
+ S13 随机端口 (config http_port 0 -> 回填真实端口并记指针) + endpoint 子命令 (读指针).
+ S14 POST /autostart 成功回写工具 config autostart (自启意图唯一裁决权).
+ 26-10-17-1737 S3 POST /shutdown: 先回 200 再置位 stop_event (优雅退出信号), 鉴权同闸;
  未绑定 stop_event 仍 200; _run_loop 对置位即时响应 (不空等采样间隔).
+ T-01/T-02 (issue 26-10-30-0624): config 写临界区互斥 (PUT /config 与 /autostart 串行化,
  /autostart 读-改-写不丢并发 PUT 的参数); PUT /config 拒绝非回环 http_host.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S3, S6, S12).
全部用例 hermetic: tmp_path 数据目录 + 端口 0 (系统分配) + 注入计数器,
不碰真实网卡、不占固定端口、不跑真实 HTTP 之外的网络; 锁/发现指针 (gtm.storage)
与正主指针 (gtm.identity) 双命名空间同址注入 tmp (不碰真实用户级指针目录;
tests/conftest.py autouse 守阵对每个用例做真实目录前后快照, 落文件即红),
installer 替身注入 (不跑真实 schtasks/systemctl).
"""

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

# ---- 替身 ----

TODAY = datetime.date(2026, 10, 16)
FIXED_NOW = datetime.datetime(2026, 10, 16, 12, 0, 0)


class FakeNic(SimpleNamespace):
    pass


def make_counters(start: int = 1_000_000):
    """单调递增计数器替身 (每次读 +1024 字节 up, +512 down)."""
    state = {"v": start}
    calls = {"n": 0}

    def counters() -> dict:
        calls["n"] += 1
        state["v"] += 1024
        return {"eth0": FakeNic(bytes_sent=state["v"], bytes_recv=state["v"] // 2)}

    return counters, calls


def make_stats() -> dict:
    return {"eth0": SimpleNamespace(isup=True)}


class _NoAutostartBackend:
    """替身自启后端 (S12): 未注册 —— start() 写发现指针探测 autostart_registered 时不碰真实 installer."""
    def is_registered(self) -> bool:
        return False


def _no_autostart_factory(data_dir: str) -> _NoAutostartBackend:
    return _NoAutostartBackend()


def make_server(
    tmp_path,
    *,
    port: int = 0,
    config: Optional[Config] = None,
    counters_start: int = 1_000_000,
    installer_factory=None,
    autostart_error: Optional[str] = None,
    stop_event: Optional[threading.Event] = None,
    endpoint_file: Optional[str] = None,
):
    """完整控制面装配 (锁已持有; 返回 (server, storage, sampler, holder, token)).

    sampler 挂注入计数器替身 (每次 +1024 up / +512 down) 与固定时钟 —— 全部
    用例 hermetic, 不碰真实网卡。installer_factory 注入自启后端替身 (S6 /autostart);
    S12 起 start() 写发现指针会探测 autostart_registered, 默认也走替身 (不跑真 schtasks)。
    锁路径与发现指针均注入 tmp_path (S12/D8): 不碰真实用户级指针目录。
    stop_event (26-10-17-1737 S3): 传入则绑给 ControlServer —— POST /shutdown 置位它
    (优雅退出信号); 不传 = 未绑定形态 (/shutdown 仍回 200 但不置位, 只 WARNING)。
    endpoint_file: 覆盖发现指针路径 (默认 tmp_path/endpoint.json); 传不可写路径可验
    「指针写失败只 WARNING 不阻断服务」(§09)。
    """
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))
    storage.acquire_lock()
    counters, calls = make_counters(counters_start)
    sampler = Sampler(clock=lambda: FIXED_NOW, counters_provider=counters, stats_provider=make_stats)
    holder = ConfigHolder(config or Config())
    token = TokenManager(str(tmp_path / "monitor.token"))
    server = ControlServer(
        storage,
        sampler,
        holder,
        token,
        port=port,
        installer_factory=installer_factory or _no_autostart_factory,
        endpoint_file=endpoint_file or str(tmp_path / "endpoint.json"),
        autostart_error=autostart_error,
        stop_event=stop_event,
    )
    server.start()
    return server, storage, sampler, holder, token


def http(server: ControlServer, method: str, path: str, body=None, token: Optional[str] = None):
    """真实 HTTP 请求 (urllib); 返回 (status, payload_dict)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(server.url() + path, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ---- TokenManager ----


def test_token_first_start_generates_file(tmp_path) -> None:
    tm = TokenManager(str(tmp_path / "monitor.token"))
    tok = tm.token()
    assert len(tok) >= 32  # urlsafe(32) -> 43 字符
    assert (tmp_path / "monitor.token").read_text(encoding="utf-8").strip() == tok


def test_token_reload_same_across_restart(tmp_path) -> None:
    p = str(tmp_path / "monitor.token")
    first = TokenManager(p).token()
    second = TokenManager(p).token()
    assert first == second  # 重启不换密钥 (订阅方缓存不失效)


def test_token_verify() -> None:
    """verify 语义: 对 -> True; 错/空/None -> False (不走落盘路径)."""
    tm = TokenManager.__new__(TokenManager)  # 只验比对逻辑, 不触发生成落盘
    tm._token = "abc123"
    assert tm.verify("abc123") is True
    assert tm.verify("wrong") is False
    assert tm.verify("") is False
    assert tm.verify(None) is False


def test_token_generated_at_startup_before_any_request(tmp_path) -> None:
    """启动即生成密钥 (非惰性): 监听前 monitor.token 已存在 —— 订阅方读文件取密钥
    再来鉴权, 惰性生成会鸡生蛋 (S3 真机冒烟实测坑)."""
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        assert (tmp_path / "monitor.token").exists()
        assert token.token() == (tmp_path / "monitor.token").read_text(encoding="utf-8").strip()
    finally:
        server.stop()


# ---- 鉴权闸 (计划 S3 出口: 无 token/错 token 单测) ----


def test_status_without_token_401(tmp_path) -> None:
    server, *_ = make_server(tmp_path)
    try:
        assert http(server, "GET", "/status", token=None)[0] == 401
    finally:
        server.stop()


def test_status_wrong_token_401(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        assert http(server, "GET", "/status", token="wrong-token")[0] == 401
        assert http(server, "GET", "/status", token=token.token())[0] == 200
    finally:
        server.stop()


def test_auth_required_on_all_write_endpoints(tmp_path) -> None:
    server, *_ = make_server(tmp_path)
    try:
        assert http(server, "PUT", "/config", body={}, token=None)[0] == 401
        assert http(server, "POST", "/subscribe", body={}, token=None)[0] == 401
        assert http(server, "POST", "/shutdown", token=None)[0] == 401
    finally:
        server.stop()


# ---- GET /status ----


def test_status_fields(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        # 先采两帧: 首帧 baseline (delta 0), 次帧 up +1024 / down +512
        result = sampler.sample_once()
        storage.record(result, sampler.snapshot())
        result = sampler.sample_once()
        storage.record(result, sampler.snapshot())
        status, payload = http(server, "GET", "/status", token=token.token())
        assert status == 200 and payload["ok"] is True
        assert payload["day"] == "2026-10-16"
        assert payload["day_up_bytes"] == 1024 and payload["day_down_bytes"] == 512
        assert payload["day_total_bytes"] == 1536
        assert payload["last_event_id"] == 0
        assert payload["subscriber_count"] == 0
        assert payload["paths"]["dat"] == storage.dat_path
        assert payload["paths"]["state"] == storage.state_path
        # 配置回显是复合串 (S7/D13: 盘上与契约只留 "30S"/"10MiB" 形态)
        assert payload["config"]["sample_interval"] == "5S"
        assert payload["config"]["flush_delta_bytes"] == "1MiB"
        assert payload["config"]["http_port"] == 0  # 端口/地址仍是原形态
    finally:
        server.stop()


# ---- PUT /config (热重载) ----


def test_put_config_valid_hot_reload(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        status, payload = http(
            server, "PUT", "/config", body={
                "sample_interval": 2.5,
                "http_port": 9100
            }, token=token.token()
        )
        assert status == 200 and payload["ok"] is True
        assert holder.current.sample_interval == 2.5  # 热重载即时生效
        assert holder.current.http_port == 9100
        # 落盘: 重载验证 (last-writer-wins)
        reloaded, errors = load_config(str(tmp_path / "config.yml"))
        assert errors == () and reloaded is not None
        assert reloaded.sample_interval == 2.5
        # /status 回显也已是新值
        assert http(server, "GET", "/status", token=token.token())[1]["sample_interval"] == 2.5
    finally:
        server.stop()


def test_put_config_invalid_aggregates_and_keeps_old(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        status, payload = http(
            server,
            "PUT",
            "/config",
            body={
                "sample_interval": True,
                "unknown_key": 1,
                "http_port": 99999
            },
            token=token.token(),
        )
        assert status == 400 and payload["ok"] is False
        assert len(payload["errors"]) == 3  # 聚合一次报齐
        assert holder.current == Config()  # 旧配置不动
        assert not (tmp_path / "config.yml").exists()  # 无效载荷不落盘
    finally:
        server.stop()


def test_put_config_bad_json_400(tmp_path) -> None:
    server, *_ = make_server(tmp_path)
    try:
        req = urllib.request.Request(
            server.url() + "/config",
            method="PUT",
            data=b"{not json",
            headers={
                "Authorization": f"Bearer {server.token_manager.token()}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        assert status == 400
    finally:
        server.stop()


# ---- 订阅生命周期 ----


def test_subscribe_heartbeat_unsubscribe(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        tok = token.token()
        status, payload = http(
            server, "POST", "/subscribe", body={
                "endpoint": "http://127.0.0.1:9000/n",
                "token": "t"
            }, token=tok
        )
        assert status == 200 and payload["id"]
        assert payload["lease_ttl_s"] == 180.0 and payload["heartbeat_interval_s"] == 60.0
        sub_id = payload["id"]
        assert len(storage.subscribers) == 1
        # 心跳续租
        assert http(server, "POST", "/heartbeat", body={"id": sub_id}, token=tok)[0] == 200
        # 未知 id
        assert http(server, "POST", "/heartbeat", body={"id": "nope"}, token=tok)[0] == 404
        assert http(server, "POST", "/unsubscribe", body={"id": "nope"}, token=tok)[0] == 404
        # 注销
        assert http(server, "POST", "/unsubscribe", body={"id": sub_id}, token=tok)[0] == 200
        assert len(storage.subscribers) == 0
    finally:
        server.stop()


def test_subscribe_validates_payload(tmp_path) -> None:
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        tok = token.token()
        assert http(server, "POST", "/subscribe", body={"endpoint": "not-a-url", "token": "t"}, token=tok)[0] == 400
        assert http(server, "POST", "/subscribe", body={"endpoint": "http://h/x", "token": ""}, token=tok)[0] == 400
        assert http(server, "POST", "/nope", body={}, token=tok)[0] == 404
        assert len(storage.subscribers) == 0
    finally:
        server.stop()


def test_unknown_endpoint_404(tmp_path) -> None:
    server, *_ = make_server(tmp_path)
    try:
        assert http(server, "GET", "/nope", token=server.token_manager.token())[0] == 404
    finally:
        server.stop()


# ---- 租约剔除 (计划 S3 出口单测) ----


def test_lease_prune_expired_and_keep_fresh(tmp_path) -> None:
    """注入 now: 超租约的剔除, 未超的保留 (Storage 层直接验剔除逻辑)."""
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))
    storage.acquire_lock()
    storage.upsert_subscriber("old", "http://h/1", "t")
    storage.upsert_subscriber("fresh", "http://h/2", "t")
    # 把 old 的 last_heartbeat 拨回过去
    storage._subscribers["old"]["last_heartbeat"] = 0.0  # noqa: SLF001 - 测试拨钟
    removed = storage.prune_expired_subscribers(now=10_000.0, lease_ttl_s=180.0)
    assert removed == ("old", )
    assert set(storage.subscribers) == {"fresh"}
    # 无过期时零写盘: 文件 mtime 不变语义由下一次写盘体现, 此处验返回空
    assert storage.prune_expired_subscribers(now=10_001.0, lease_ttl_s=180.0) == ()


def test_lease_prune_lazy_on_status_request(tmp_path) -> None:
    """懒剔除: 过期订阅在下一个 /status 请求入口被剔除 (计数即时准确)."""
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        tok = token.token()
        status, payload = http(server, "POST", "/subscribe", body={"endpoint": "http://h/1", "token": "t"}, token=tok)
        sub_id = payload["id"]
        assert http(server, "GET", "/status", token=tok)[1]["subscriber_count"] == 1
        # 拨回心跳时间 -> 超过租约
        storage._subscribers[sub_id]["last_heartbeat"] = 0.0  # noqa: SLF001 - 测试拨钟
        assert http(server, "GET", "/status", token=tok)[1]["subscriber_count"] == 0
        assert storage.subscribers == {}
    finally:
        server.stop()


# ---- 注册表重启续存 ----


def test_registry_survives_restart(tmp_path) -> None:
    """注册表落 state.json: 重启 (新 Storage 实例) 后订阅仍在 (计划 S3: 注册表落 state.json)."""
    storage = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))
    storage.acquire_lock()
    storage.upsert_subscriber("s1", "http://h/1", "t")
    storage.release_lock()
    storage2 = Storage(str(tmp_path), lock_path=str(tmp_path / "instance.lock"))
    storage2.acquire_lock()
    try:
        storage2.recover(Sampler())
        assert set(storage2.subscribers) == {"s1"}
        assert storage2.subscribers["s1"]["endpoint"] == "http://h/1"
    finally:
        storage2.release_lock()


# ---- 端口冲突 fail-fast (计划 S3 出口实测点; 单测用端口 0 分配后的实占端口) ----


def test_port_conflict_fails_fast(tmp_path) -> None:
    server_a, *_ = make_server(tmp_path / "a")
    server_b, *_ = make_server(tmp_path / "b")
    try:
        # 第二个实例直接抢 server_a 已占端口 -> 绑定即 OSError (fail-fast)
        with pytest.raises(OSError):
            ControlServer(
                Storage(str(tmp_path / "c"), lock_path=str(tmp_path / "c.lock")),
                Sampler(),
                ConfigHolder(Config()),
                TokenManager(str(tmp_path / "c" / "monitor.token")),
                host=server_a.host,
                port=server_a.port,
                endpoint_file=str(tmp_path / "c" / "endpoint.json"),
            ).start()
    finally:
        server_a.stop()
        server_b.stop()


# ---- 发现指针 (S12): bind 后写 endpoint.json / 退出删除 / 抢输不占端口 ----


def test_endpoint_written_on_start_with_fields(tmp_path) -> None:
    """S12/D6: bind 成功后原子写 endpoint.json, 字段见计划 §05."""
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        pointer = tmp_path / "endpoint.json"
        assert pointer.is_file()
        payload = json.loads(pointer.read_text(encoding="utf-8"))
        assert payload["schema"] == ENDPOINT_SCHEMA
        assert payload["port"] == server.port
        assert payload["host"] == "127.0.0.1"
        assert payload["pid"] == os.getpid()
        assert payload["data_dir"] == os.path.abspath(str(tmp_path))
        assert payload["token_path"] == os.path.abspath(str(tmp_path / "monitor.token"))
        assert payload["autostart_registered"] is False
        assert payload["autostart_error"] is None  # 没尝试/没失败 -> null (issue 26-10-17-1455)
        assert payload["version"] and payload["exe_path"] and payload["started_at"]
    finally:
        server.stop()


def test_endpoint_removed_on_stop(tmp_path) -> None:
    """S12/D6: 优雅退出 (stop) 删发现指针 —— 退出后指针消失."""
    server, *_rest = make_server(tmp_path)
    pointer = tmp_path / "endpoint.json"
    assert pointer.is_file()
    server.stop()
    assert not pointer.exists()


def test_endpoint_autostart_registered_reflects_backend(tmp_path) -> None:
    """S12: autostart_registered 反映 installer 现货态 (已注册 -> true, 供 auto-qb 设置页)."""
    class _Registered:
        def is_registered(self) -> bool:
            return True

    server, *_rest = make_server(tmp_path, installer_factory=lambda data_dir: _Registered())
    try:
        payload = json.loads((tmp_path / "endpoint.json").read_text(encoding="utf-8"))
        assert payload["autostart_registered"] is True
    finally:
        server.stop()


def test_endpoint_carries_autostart_error_from_startup(tmp_path) -> None:
    """S14 追加 (issue 26-10-17-1455): 启动期注册失败的原因落进指针, 用户能看到「为什么未注册」."""
    reason = "写注册表 HKCU\\...\\Run 失败: 拒绝访问"
    server, *_rest = make_server(tmp_path, autostart_error=reason)
    try:
        payload = json.loads((tmp_path / "endpoint.json").read_text(encoding="utf-8"))
        assert payload["autostart_error"] == reason
        assert payload["autostart_registered"] is False
    finally:
        server.stop()


def test_losing_instance_locks_out_before_binding_port(tmp_path, monkeypatch, capsys) -> None:
    """S12/D8: 抢输锁的第二个进程 fail-fast —— 不绑端口 (端口零占用)、不写发现指针."""
    from gtm import __main__ as cli

    ptr = tmp_path / "ptr"
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    # 身份层另持一份 pointer_dir 引用 (gtm.identity), 不同址重定向会把 primary.json 写进真实目录
    monkeypatch.setattr("gtm.identity.pointer_dir", lambda: str(ptr))
    data_dir = tmp_path / "data"
    holder = Storage(str(data_dir))
    holder.acquire_lock()  # 模拟已运行实例占锁 (锁锚点已被 monkeypatch 指到 tmp)

    start_calls: list[int] = []
    real_start = ControlServer.start

    def spy_start(self) -> None:  # noqa: ANN001 - 替身签名
        start_calls.append(1)
        real_start(self)

    monkeypatch.setattr(ControlServer, "start", spy_start)
    rc = cli.cmd_run(SimpleNamespace(data_dir=str(data_dir)))
    assert rc == 1
    assert "已持有锁" in capsys.readouterr().err  # 确证走的是抢输锁路径 (非更早返回)
    assert start_calls == []  # 未绑端口 = 端口零占用
    assert not (ptr / "endpoint.json").exists()  # 未写发现指针
    holder.release_lock()


# ---- 随机端口与 endpoint 子命令 (S13 / D9) ----


def test_random_port_two_starts_differ_and_recorded_in_pointer(tmp_path) -> None:
    """S13/D9: 连续两次启动端口不同 (内核分配), 且各自被发现指针正确记录."""
    s1, *_ = make_server(tmp_path / "a")
    s2, *_ = make_server(tmp_path / "b")
    try:
        assert s1.port != 0 and s2.port != 0  # 回填了真实端口 (非请求值 0)
        assert s1.port != s2.port
        p1 = json.loads((tmp_path / "a" / "endpoint.json").read_text(encoding="utf-8"))
        p2 = json.loads((tmp_path / "b" / "endpoint.json").read_text(encoding="utf-8"))
        assert p1["port"] == s1.port and p1["host"] == s1.host
        assert p2["port"] == s2.port and p2["host"] == s2.host
    finally:
        s1.stop()
        s2.stop()


def test_endpoint_subcommand_prints_pointer_fields(tmp_path, monkeypatch, capsys) -> None:
    """S13: endpoint 子命令读发现指针打印 host:port + token_path + data_dir, 输出与实际一致."""
    from gtm import __main__ as cli

    ptr = tmp_path / "ptr"
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    write_endpoint(
        {
            "schema": ENDPOINT_SCHEMA,
            "version": "9.9.9",
            "pid": 4242,
            "started_at": "2026-10-17T03:39:00+08:00",
            "host": "127.0.0.1",
            "port": 51234,
            "data_dir": "D:/gtm/data",
            "token_path": "D:/gtm/data/monitor.token",
            "exe_path": "D:/gtm/gtm.exe",
            "autostart_registered": True,
        }
    )
    assert cli.main(["endpoint"]) == 0
    captured = capsys.readouterr()
    assert "http://127.0.0.1:51234" in captured.out
    assert "token_path: D:/gtm/data/monitor.token" in captured.out
    assert "data_dir: D:/gtm/data" in captured.out
    assert captured.err == ""  # schema 已知 -> 无告警


def test_endpoint_subcommand_missing_pointer_exits_1(tmp_path, monkeypatch, capsys) -> None:
    """S13: 工具未运行 (指针缺失) -> 报错退出 1, 不猜端口."""
    from gtm import __main__ as cli

    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(tmp_path / "nope"))
    assert cli.main(["endpoint"]) == 1
    err = capsys.readouterr().err
    assert "未找到发现指针" in err and "未在运行" in err


def test_endpoint_subcommand_corrupt_pointer_exits_1(tmp_path, monkeypatch, capsys) -> None:
    """S13: 指针损坏 (坏 JSON) -> 报错退出 1 (不静默打印空字段)."""
    from gtm import __main__ as cli

    ptr = tmp_path / "ptr"
    ptr.mkdir()
    (ptr / "endpoint.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    assert cli.main(["endpoint"]) == 1
    assert "损坏" in capsys.readouterr().err


def test_endpoint_subcommand_unknown_schema_warns_but_prints(tmp_path, monkeypatch, capsys) -> None:
    """S13/§05: 未知 schema 只告警 (不猜字段), 已知字段仍照常打印."""
    from gtm import __main__ as cli

    ptr = tmp_path / "ptr"
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    write_endpoint(
        {
            "schema": 99,
            "host": "127.0.0.1",
            "port": 50000,
            "token_path": "D:/x/monitor.token",
            "data_dir": "D:/x",
        }
    )
    assert cli.main(["endpoint"]) == 0
    captured = capsys.readouterr()
    assert "schema=99" in captured.err and "不符" in captured.err
    assert "http://127.0.0.1:50000" in captured.out


# ---- 热重载不丢采样 (计划 S3 出口: 真循环 + 并发 PUT) ----


def test_hot_reload_does_not_drop_sampling(tmp_path) -> None:
    """真 _run_loop + 并发 PUT /config: 重载前后采样持续 (无丢帧/无死循环/线程存活)."""
    server, storage, sampler, holder, token = make_server(tmp_path, config=Config(sample_interval=0.02))
    counters, calls = make_counters()
    sampler._counters_provider = counters  # noqa: SLF001 - 独立计数替身, 断言采样帧数
    stop = threading.Event()
    loop = threading.Thread(target=_run_loop, args=(storage, sampler, holder, stop), daemon=True)
    loop.start()
    try:
        time.sleep(0.15)
        before = calls["n"]
        assert before >= 3  # 循环真的在跑
        # 热重载: 改采样间隔 + 适配器过滤 (loop 下轮即生效)
        status, _ = http(
            server,
            "PUT",
            "/config",
            body={
                "sample_interval": 0.05,
                "adapter_exclude": ["vmnet.*"]
            },
            token=token.token()
        )
        assert status == 200
        assert holder.current.sample_interval == 0.05
        time.sleep(0.3)
        after = calls["n"]
        assert after > before  # 重载后继续采样, 没丢
        assert loop.is_alive()  # 循环线程没被重载杀掉 (非法过滤器曾致线程猝死, 已修)
        assert sampler.day_total_bytes > 0
    finally:
        stop.set()
        loop.join(timeout=3)
        server.stop()
        storage.release_lock()


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


# ---- 路由守卫矩阵 (26-10-21 覆盖率门禁 P1-T1.2) ----
#
# 5 条写路由 x 两类坏载荷 (非 JSON 对象 / 读不出体), 加上 _read_json 的四类边界
# (Content-Length 非法 / 空体 / 超限 / 坏字节) 与 _dispatch 的 500 兜底 —— 这些出口
# 此前一行都没走过。全部用**真实 socket** 发原始请求: urllib 拼不出坏 Content-Length
# 与非 UTF-8 体, 而这正是要守的形态。


def raw_request(
    server: ControlServer,
    method: str,
    path: str,
    body: bytes = b"",
    *,
    token: Optional[str] = None,
    content_length: Optional[str] = None,
) -> tuple[int, bytes]:
    """发一条原始 HTTP 请求 (绕过 urllib 的规范化), 返回 (状态码, 原始响应字节)."""
    lines = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{server.port}", "Content-Type: application/json"]
    if token is not None:
        lines.append(f"Authorization: Bearer {token}")
    if content_length is not None:
        lines.append(f"Content-Length: {content_length}")
    elif body:
        lines.append(f"Content-Length: {len(body)}")
    lines.append("Connection: close")
    payload = "\r\n".join(lines).encode("ascii") + b"\r\n\r\n" + body
    with socket.create_connection((server.host, server.port), timeout=5) as sock:
        sock.sendall(payload)
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    return int(raw.split(b" ")[1]), raw


WRITE_ROUTES = [
    ("PUT", "/config"),
    ("POST", "/subscribe"),
    ("POST", "/heartbeat"),
    ("POST", "/unsubscribe"),
    ("POST", "/autostart"),
]


@pytest.mark.parametrize("method,path", WRITE_ROUTES)
def test_non_object_payload_400_on_every_write_route(tmp_path, method, path) -> None:
    """5 条写路由的「载荷必须是 JSON 对象」守卫: JSON 合法但顶层是数组 -> 400."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, payload = http(server, method, path, body=[1, 2], token=token.token())
        assert status == 400
        assert "必须是 JSON 对象" in payload["error"]
    finally:
        server.stop()


@pytest.mark.parametrize("method,path", WRITE_ROUTES)
def test_empty_body_400_on_every_write_route(tmp_path, method, path) -> None:
    """5 条写路由的空体守卫: Content-Length 0 -> 400 「请求体为空」(不进端点逻辑)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, raw = raw_request(server, method, path, token=token.token(), content_length="0")
        assert status == 400
        assert "请求体为空" in json.loads(raw.split(b"\r\n\r\n", 1)[1])["error"]
    finally:
        server.stop()


def test_read_json_invalid_content_length_400(tmp_path) -> None:
    """Content-Length 非整数: 400 「Content-Length 非法」(不抛到 _dispatch 变 500)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, raw = raw_request(server, "POST", "/subscribe", token=token.token(), content_length="abc")
        assert status == 400
        assert "Content-Length 非法" in json.loads(raw.split(b"\r\n\r\n", 1)[1])["error"]
    finally:
        server.stop()


def test_read_json_oversized_body_400(tmp_path) -> None:
    """请求体超过 1 MiB 上限: 400 「请求体过大」—— 不读体, 直接拒 (防内存滥用)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, raw = raw_request(
            server, "POST", "/subscribe", token=token.token(), content_length=str(1024 * 1024 + 1)
        )
        assert status == 400
        assert "请求体过大" in json.loads(raw.split(b"\r\n\r\n", 1)[1])["error"]
    finally:
        server.stop()


def test_read_json_broken_json_400(tmp_path) -> None:
    """坏 JSON: 400 「JSON 解析失败」(带底层原因, 便于调用方排障)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, raw = raw_request(server, "POST", "/subscribe", b"{not json", token=token.token())
        assert status == 400
        assert "JSON 解析失败" in json.loads(raw.split(b"\r\n\r\n", 1)[1])["error"]
    finally:
        server.stop()


def test_read_json_non_utf8_body_400(tmp_path) -> None:
    """非 UTF-8 字节: 与坏 JSON 同一条出口 (UnicodeDecodeError 一并兜住, 不 500)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, raw = raw_request(server, "POST", "/subscribe", b"\xff\xfe\x00", token=token.token())
        assert status == 400
        assert "JSON 解析失败" in json.loads(raw.split(b"\r\n\r\n", 1)[1])["error"]
    finally:
        server.stop()


def test_dispatch_unhandled_exception_returns_500(tmp_path) -> None:
    """端点处理函数抛错: _dispatch 兜成 500 (单请求失败不拖垮控制面, 后续请求照常)."""
    server, *_rest, token = make_server(tmp_path)

    def boom(handler):
        raise RuntimeError("端点实现炸了")

    try:
        server.handle = boom  # 实例级覆盖: _Handler._dispatch 取的就是这个引用
        status, payload = http(server, "GET", "/status", token=token.token())
        assert status == 500 and payload["error"] == "internal error"
        del server.handle  # 还原后控制面仍可用
        assert http(server, "GET", "/status", token=token.token())[0] == 200
    finally:
        server.stop()


def test_stop_is_idempotent(tmp_path) -> None:
    """stop() 可重复调用 (httpd / thread 都已回收): 第二次是 no-op, 不抛."""
    server, *_rest = make_server(tmp_path)
    server.stop()
    server.stop()
    assert server._httpd is None and server._thread is None


def test_endpoint_write_failure_only_warns(tmp_path, caplog) -> None:
    """发现指针写失败 (父路径是普通文件): 只 WARNING, 服务照常监听 (§09 指针是便利不是前提)."""
    blocker = tmp_path / "blocker"
    blocker.write_text("我是文件, 不是目录", encoding="utf-8")
    bad = str(blocker / "endpoint.json")  # makedirs 在父路径上抛 NotADirectoryError
    with caplog.at_level("WARNING", logger="gtm.server"):
        server, *_rest, token = make_server(tmp_path, endpoint_file=bad)
    try:
        assert "发现指针写入失败" in caplog.text
        assert http(server, "GET", "/status", token=token.token())[0] == 200
    finally:
        server.stop()


def test_autostart_probe_failure_degrades_to_unregistered(tmp_path, caplog) -> None:
    """自启探测抛错 (替身后端不听话): 按「未注册」降级写指针, 不拖垮启动."""
    def broken_factory(data_dir: str):
        raise RuntimeError("探测不了")

    with caplog.at_level("DEBUG", logger="gtm.server"):
        server, *_rest = make_server(tmp_path, installer_factory=broken_factory)
    try:
        pointer = json.loads((tmp_path / "endpoint.json").read_text(encoding="utf-8"))
        assert pointer["autostart_registered"] is False
        assert "自启注册状态查询失败" in caplog.text
    finally:
        server.stop()


@pytest.mark.parametrize("endpoint", [None, "", "   ", 123])
def test_subscribe_rejects_missing_or_non_string_endpoint(tmp_path, endpoint) -> None:
    """endpoint 缺失/空白/非字符串: 400 (不落到 urlsplit, 不给 notifier 埋假端点)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, payload = http(
            server, "POST", "/subscribe", body={
                "endpoint": endpoint,
                "token": "t"
            }, token=token.token()
        )
        assert status == 400 and "endpoint" in payload["error"]
    finally:
        server.stop()


def test_subscribe_rejects_unparsable_endpoint(tmp_path) -> None:
    """urlsplit 解析不了 (坏 IPv6 字面量): 400 而不是 500 (ValueError 就地兜住)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, payload = http(
            server, "POST", "/subscribe", body={
                "endpoint": "http://[::1",
                "token": "t"
            }, token=token.token()
        )
        assert status == 400 and "endpoint" in payload["error"]
    finally:
        server.stop()


@pytest.mark.parametrize("path", ["/heartbeat", "/unsubscribe"])
@pytest.mark.parametrize("bad_id", [None, "", 123])
def test_heartbeat_and_unsubscribe_reject_bad_id(tmp_path, path, bad_id) -> None:
    """id 缺失/空/非字符串: 400 (心跳与注销同一判据, 不把 None 当订阅号)."""
    server, *_rest, token = make_server(tmp_path)
    try:
        status, payload = http(server, "POST", path, body={"id": bad_id}, token=token.token())
        assert status == 400 and "id 必须是非空字符串" in payload["error"]
    finally:
        server.stop()


# ---- TokenManager 边界 (密钥文件是控制面的唯一凭据, 读失败不许静默换钥) ----


def test_token_empty_file_regenerates(tmp_path) -> None:
    """密钥文件存在但为空 (被截断/写了一半): 重新生成而不是拿空串当密钥."""
    path = tmp_path / "monitor.token"
    path.write_text("\n", encoding="utf-8")
    tok = TokenManager(str(path)).token()
    assert len(tok) >= 32
    assert path.read_text(encoding="utf-8").strip() == tok


def test_token_read_oserror_propagates(tmp_path) -> None:
    """读密钥遇 OSError: 直接上抛让启动 fail-fast —— 静默换钥会让已订阅方全部 401."""
    path = tmp_path / "monitor.token"
    path.mkdir()  # 路径是目录 -> open 抛 IsADirectoryError (OSError)
    with pytest.raises(OSError):
        TokenManager(str(path)).token()


def test_token_concurrent_first_call_generates_once(tmp_path) -> None:
    """并发首调只生成一次 (双检锁内层): 第二个线程拿到同一个密钥, 不再落盘第二次."""
    tm = TokenManager(str(tmp_path / "monitor.token"))
    started = threading.Event()
    release = threading.Event()
    generated: list[str] = []

    def slow_generate() -> str:
        started.set()
        release.wait(2.0)
        generated.append("tok")
        return "tok"

    tm._load_or_generate = slow_generate  # noqa: SLF001 - 只替换生成步骤, 保留锁结构
    first = threading.Thread(target=tm.token, daemon=True)
    first.start()
    assert started.wait(2.0)
    second = threading.Thread(target=tm.token, daemon=True)
    second.start()
    time.sleep(0.05)  # 让第二个线程卡在锁上 (外层 None 已判过)
    release.set()
    first.join(timeout=3)
    second.join(timeout=3)
    assert tm.token() == "tok"
    assert generated == ["tok"]  # 只生成一次

"""S3 控制面守阵: 鉴权 / 端点 / 租约 / 配置热重载 / 端口冲突 fail-fast.
+ S6 自启开关端点 POST /autostart (工具进程内跑 installer, 替身注入).
+ S12 发现指针: bind 成功后写 endpoint.json (字段/删除) + 抢输锁不占端口.
+ S13 随机端口 (config http_port 0 -> 回填真实端口并记指针) + endpoint 子命令 (读指针).
+ S14 POST /autostart 成功回写工具 config autostart (自启意图唯一裁决权).
+ 26-10-17-1737 S3 POST /shutdown: 先回 200 再置位 stop_event (优雅退出信号), 鉴权同闸;
  未绑定 stop_event 仍 200; _run_loop 对置位即时响应 (不空等采样间隔).
+ T-01/T-02 (issue 26-10-30-0624): config 写临界区互斥 (PUT /config 与 /autostart 串行化,
  /autostart 读-改-写不丢并发 PUT 的参数); PUT /config 拒绝非回环 http_host.
+ 26-10-31-0537: POST /autostart 成功后 patch 发现指针 autostart 字段 (卸载/注册即时回写真值,
  UI 开关不再漂移到重启); patch 失败只 WARNING 不阻断响应.
+ S7 (T27): GET /status 透传最近一轮越界记录 last_spike (无越界为 null; 既有字段不变).

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

from server_support import *  # noqa: F401,F403

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


def test_status_last_spike_passthrough(tmp_path) -> None:
    """T27 (S7): /status 透出最近一轮越界记录; 无越界为 null, 既有字段不变."""
    server, storage, sampler, holder, token = make_server(tmp_path)
    try:
        status, payload = http(server, "GET", "/status", token=token.token())
        assert status == 200 and payload["last_spike"] is None

        sampler.sample_once(5.0, 1)  # 首轮只立基线
        sampler._last_mono -= 1.0  # 上一轮时间基线推回 1s: 次轮 1024B / 1s > 1B/s
        result = sampler.sample_once(5.0, 1)
        assert sampler.last_spike is not None and result.day_up_bytes == 1024

        status, payload = http(server, "GET", "/status", token=token.token())
        assert status == 200 and payload["last_spike"] == sampler.last_spike
        assert payload["last_spike"]["items"][0]["nic"] == "eth0"
        # 既有字段语义零改动 (只追加新键)
        assert payload["ok"] is True and payload["day_up_bytes"] == 1024
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

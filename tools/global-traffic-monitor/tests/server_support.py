"""gtm 控制面守阵共享替身(从 test_server.py 原样搬迁)"""
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

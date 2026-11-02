"""gtm 控制面守阵: 路由守卫矩阵 / TokenManager 边界(从 test_server.py 原样搬迁)"""
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

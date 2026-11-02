"""tests/_test_ports.py(端口单点)的回归阵(计划 26-11-02-0657 §02.7)。

## 测试计划
- test_free_port_single_source: `_free_port`/`free_port` 定义全仓库唯一, 别处不得复制实现
- test_returns_free_port: 返回的端口立即可绑
- test_retry_on_occupied_candidate: 占住首个候选 → 重试后拿到另一个可用端口
- test_exhausted_raises: 候选全被抢(monkeypatch) → RuntimeError 响亮失败
"""
from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

import _test_ports as tp

REPO = Path(__file__).resolve().parent.parent


def test_free_port_single_source():
    """_free_port/free_port 定义全仓库唯一(tests/_test_ports.py), 别处不得复制实现。"""
    offenders: list[str] = []
    pat = re.compile(r"def\s+(_free_port|free_port)\s*\(")
    for p in REPO.rglob("*.py"):
        if ".venv" in p.parts or ".git" in p.parts or "tests-real" in p.parts:
            continue  # tests-real/lib/app.py 是实机轨自己的段内分配器(语义不同), 不属于本单点口径
        if p.samefile(REPO / "tests" / "_test_ports.py") or p.samefile(Path(__file__)):
            continue
        try:
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(p))
        except OSError:
            continue
    assert not offenders, f"端口实现散落: {offenders}"


def test_returns_free_port():
    port = tp.free_port()
    with socket.socket() as s:
        s.bind(("127.0.0.1", port))  # 立即可绑即证据


def test_retry_on_occupied_candidate():
    """先占住第一个候选端口, free_port 必须绕过它拿到另一个可用端口。"""
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    occupied = holder.getsockname()[1]
    try:
        port = tp.free_port()
    finally:
        holder.close()
    assert port != occupied
    with socket.socket() as s:
        s.bind(("127.0.0.1", port))


def test_exhausted_raises(monkeypatch):
    """回绑自验恒失败(模拟窗口内必被抢) → RuntimeError, 不静默返回坏端口。"""
    calls = {"n": 0}

    class _FakeSock:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def bind(self, addr):
            calls["n"] += 1
            if calls["n"] % 2 == 0:  # 每次回绑(第 2/4/6 次)都"被抢"
                raise OSError(10048, "occupied")

        def getsockname(self):
            return ("127.0.0.1", 40000 + calls["n"])

    monkeypatch.setattr(tp.socket, "socket", lambda *a, **k: _FakeSock())
    with pytest.raises(RuntimeError, match="连续 3 次"):
        tp.free_port()
    assert calls["n"] == tp.RETRIES * 2  # 每次取号+回绑各一次 bind

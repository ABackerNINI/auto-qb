"""tests/_test_ports.py(端口单点)的回归阵(计划 26-11-02-0657 §02.7)。

## 测试计划
- test_free_port_single_source: `_free_port`/`free_port` 定义全仓库唯一, 别处不得复制实现
- test_returns_free_port: 返回的端口立即可绑
- test_retry_on_occupied_candidate: 占住首个候选 → 重试后拿到另一个可用端口
- test_exhausted_raises: 候选全被抢(monkeypatch) → RuntimeError 响亮失败
- test_hold_run_returns_bindable_run: `hold_run(3)` 返回连号三位、当场真占住、放掉后仍可绑
- test_hold_run_discards_run_whose_offset_is_refused: 纯合成 socket 注入 10013, 整段有一位被拒 ⇒ 整段丢弃换基址, 不交坏段(不碰真实端口, 断言不受并行抢口影响)
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


def test_hold_run_returns_bindable_run():
    """hold_run(3): 连号三位、持有期间真占住、放掉后每位仍可绑。"""
    base, socks = tp.hold_run(3)
    try:
        assert [s.getsockname()[1] for s in socks] == [base, base + 1, base + 2]
        with pytest.raises(OSError), socket.socket() as probe:
            probe.bind(("127.0.0.1", base + 1))  # 持有中 ⇒ 外人绑不上
    finally:
        for s in socks:
            s.close()
    for port in (base, base + 1, base + 2):
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))


def test_hold_run_discards_run_whose_offset_is_refused(monkeypatch):
    """整段有一位被拒(排除段 10013 / 独占 10048 同形) ⇒ 整段丢弃换基址, 不把坏段交给调用方。

    第一次尝试的**第二位** bind 抛 10013(与 base+1 落 Windows 排除段同形); 若实现只验基址,
    坏段就会原样返回, 调用方显式 bind 时炸(issue 26-11-06-0330)。断言落在「丢弃」这个动作上:
    第一次尝试建出来的 socket 必须全部被关掉, 返回的必须是第二次尝试的完整段。

    这里用**纯合成 socket**: 除注入点外不再走真实网络。旧版把真实 socket 当底板, 全量并行下
    别的 worker 抢口 / 排除段会让 hold_run 多重试一轮, 「恰好 2 次尝试」的断言被环境噪声打红
    (issue 26-11-10-0456); 更隐蔽的是第一次尝试若因真实端口失败, 注入根本不触发, 用例会假绿。
    真绑/持有语义由 test_hold_run_returns_bindable_run 用真实 socket 覆盖, 两用例分工不重叠。
    """
    state = {"attempt": 0, "seq": 0}
    attempts: dict[int, list] = {}

    class _FakeSock:
        """合成 socket: 端口由桩分配, 不创建真实 socket、不做真实 bind。"""
        def __init__(self):
            self.port: int | None = None
            self.closed = False

        def bind(self, addr):
            if addr[1] == 0:  # 取号 socket: 新一次尝试开始, 桩分配确定性基址(每次不同)
                state["attempt"] += 1
                state["seq"] = 0
                self.port = 41000 + state["attempt"] * 10
            else:
                self.port = addr[1]
            state["seq"] += 1
            attempts.setdefault(state["attempt"], []).append(self)
            # 取号(seq 1) + 基址(seq 2) + 第二位(seq 3) ⇒ 在第二位被拒
            if state["attempt"] == 1 and state["seq"] == 3:
                raise OSError(10013, "以一种访问权限不允许的方式做了一个访问套接字的尝试")
            return None

        def getsockname(self):
            return ("127.0.0.1", self.port)

        def close(self):
            self.closed = True

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()
            return False

    monkeypatch.setattr(tp.socket, "socket", _FakeSock)
    base, socks = tp.hold_run(3)
    try:
        assert state["attempt"] == 2, "第二位被拒 ⇒ 必须整段丢弃并换基址重来一次"
        assert len(attempts[1]) == 3, "拒绝必须落在第一次尝试的第二位(取号/基址/第二位)"
        assert not any(s in attempts[1] for s in socks), "返回的段不能来自被丢弃的第一次尝试(不交坏段)"
        assert [s.getsockname()[1] for s in socks] == [base, base + 1, base + 2]
        assert all(s.closed for s in attempts[1]), "被拒那段的 socket 必须整段关掉(不泄漏、不交坏段)"
        assert not any(s.closed for s in socks), "返回的段必须仍然持有"
    finally:
        for s in socks:
            s.close()

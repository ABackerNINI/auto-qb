"""tests/_test_ports.py(端口单点)的回归阵(计划 26-11-02-0657 §02.7)。

## 测试计划
- test_free_port_single_source: `_free_port`/`free_port` 定义全仓库唯一, 别处不得复制实现
- test_returns_free_port: 返回的端口立即可绑
- test_retry_on_occupied_candidate: 占住首个候选 → 重试后拿到另一个可用端口
- test_exhausted_raises: 候选全被抢(monkeypatch) → RuntimeError 响亮失败
- test_hold_run_returns_bindable_run: `hold_run(3)` 返回连号三位、当场真占住、放掉后仍可绑
- test_hold_run_discards_run_whose_offset_is_refused: 纯合成 socket 注入 10013, 整段有一位被拒 ⇒ 整段丢弃换基址, 不交坏段(不碰真实端口, 断言不受并行抢口影响)
- test_http_server_exclusive_bind_and_roundtrip: `http_server` 单点行为 —— 独占 bind(同端口再绑被拒)、真回环请求往返、不查 FQDN
- test_http_server_single_point: tests/ 下禁裸 ThreadingHTTPServer 直建, 假服一律走单点(Windows SO_REUSEADDR 双绑假红, issue 26-11-11-0114; 豁免 bind 扫描器夹具 test_flaky_timing_guards.py 的字面量测试数据)
"""
from __future__ import annotations

import http.client
import http.server
import re
import socket
import threading
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


def test_http_server_exclusive_bind_and_roundtrip():
    """http_server 单点行为三面: 独占 bind / 真回环往返 / 启动期零 DNS。

    独占口径(allow_reuse_address=False)是本单点的存在理由: Windows 上 SO_REUSEADDR 允许
    抢绑已监听端口, 并行下假服双绑 ⇒ 连接串线 ⇒ ConnectionError(被中止) 假红
    (issue 26-11-11-0114)。属性断言是红验: 回潮成 True 即红; 纯 socket 再绑被拒是行为面
    佐证(独占在场 ⇒ 端口真被占住, 与 hold_run 的持有语义同形)。
    """
    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A003 - 基类签名; 静默
            pass

        def do_GET(self):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = tp.http_server(_Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        port = srv.server_address[1]
        assert srv.allow_reuse_address is False, "独占 bind 是单点的存在理由, 回潮即双绑假红"
        assert srv.request_queue_size >= tp.HTTP_SERVER_BACKLOG, "backlog 必须 ≥ 单点常量(默认 5 并发下会满)"
        assert srv.server_name == "127.0.0.1", "server_bind 不查 FQDN(启动期零 DNS)"
        with pytest.raises(OSError), socket.socket() as probe:
            probe.bind(("127.0.0.1", port))  # 独占在场 ⇒ 外人(不带 REUSEADDR)绑不上
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.request("GET", "/probe")
            assert conn.getresponse().read() == b"ok", "真回环请求必须正常往返"
        finally:
            conn.close()
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


def test_http_server_single_point():
    """tests/ 下禁裸 ThreadingHTTPServer 直建实例 —— 测试假服一律走 _test_ports.http_server。

    本文件 docstring 与注释刻意写成不含「ThreadingHTTPServer + 紧邻左括号」的形态:
    守卫也扫本文件自身, 措辞撞上模式就会被迫整文件自豁免, 将来文件里混进真实裸实例
    反而逃过扫描(nit, 评审 26-11-11-0114 修复轮 2)。
    裸 ThreadingHTTPServer 继承 HTTPServer.allow_reuse_address=1(SO_REUSEADDR), Windows 上
    允许抢绑已监听端口; -n 8 并行下各 worker 的假服都带 REUSEADDR, bind(0) 可能拿到同一端口
    双绑, 客户端连接被递给别人的假服/已关闭的 socket ⇒ ConnectionError 假红(issue
    26-11-11-0114)。生产侧同款口径与论述: src/auto_qb/hr/server.py::_EndpointServer。
    """
    offenders: list[str] = []
    pat = re.compile(r"(?:http\.server\.)?ThreadingHTTPServer\s*\(")
    # 唯一豁免: test_flaky_timing_guards.py —— bind 扫描器的夹具文件, ThreadingHTTPServer
    # 构造位片段是字符串字面量里的合成源码(测试数据), 不是真实实例化(与
    # test_free_port_single_source 对 tests-real 的豁免同口径)。本文件与 _test_ports.py
    # 不豁免: 措辞已避开命中模式, 守卫能扫自身才不留自豁免盲区。
    exempt = REPO / "tests" / "test_flaky_timing_guards.py"
    for p in (REPO / "tests").rglob("*.py"):
        if p.samefile(exempt):
            continue
        try:
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(p))
        except OSError:
            continue
    assert not offenders, f"tests/ 下裸 ThreadingHTTPServer 实例化(应走 _test_ports.http_server): {offenders}"

"""tests/_test_ports.py(端口单点)的回归阵(计划 26-11-02-0657 §02.7)。

## 测试计划
- test_free_port_single_source: `_free_port`/`free_port` 定义全仓库唯一, 别处不得复制实现
- test_returns_free_port: 返回的端口立即可绑
- test_retry_on_occupied_candidate: 占住首个候选 → 重试后拿到另一个可用端口
- test_exhausted_raises: 候选全被抢(monkeypatch) → RuntimeError 响亮失败
- test_hold_run_returns_bindable_run: `hold_run(3)` 返回连号三位、基址落私用段、当场真占住、放掉后仍可绑
- test_hold_run_discards_run_whose_offset_is_refused: 纯合成 socket 注入 10013, 整段有一位被拒 ⇒ 整段丢弃重画随机基址, 不交坏段(不碰真实端口, 断言不受并行抢口影响)
- test_hold_run_width_guard_rejects_oversized_count: count 超出私用段宽度 ⇒ 任何 socket 创建前 RuntimeError(零网络)
- test_hold_run_redraws_with_new_random_base: 重画必须重新抽取随机基址(randint 定序桩, 「提出循环每轮重绑同基址」的坏实现判红)
- test_hold_run_exhausted_retries_raises: RETRIES 轮恒拒全败 ⇒ RuntimeError 且重画轮数 == RETRIES(与 free_port 耗尽钉面对称)
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
    """hold_run(3): 基址落私用段、连号三位、持有期间真占住、放掉后每位仍可绑。"""
    base, socks = tp.hold_run(3)
    try:
        assert tp.HOLD_RUN_PORT_LO <= base and base + 2 <= tp.HOLD_RUN_PORT_HI, \
            "基址必须落私用段(脱离 bind(0) 分配前沿, issue 26-11-20-0320)"
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
    """整段有一位被拒(排除段 10013 / 独占 10048 同形) ⇒ 整段丢弃重画随机基址, 不把坏段交给调用方。

    第一次尝试的**第二位** bind 抛 10013(与 base+1 落 Windows 排除段同形); 若实现只验基址,
    坏段就会原样返回, 调用方显式 bind 时炸(issue 26-11-06-0330)。断言落在「丢弃重画」上:
    第一次尝试建出来的 socket 必须全部被关掉, 返回的必须是第二次尝试的完整段。

    这里用**纯合成 socket**: 除注入点外不再走真实网络。hold_run 的基址是私用段随机数(不再有
    bind(0) 取号 socket), 尝试边界改由 close 事件判定: hold_run 被拒后必须整段 close, 合成
    socket 在 close 里置「已见关闭」标记, 下一次 bind 即视为新尝试开头。注入点只看「本尝试
    第几次 bind」, 与真实端口状态完全解耦(同款教训见 issue 26-11-10-0456: 真实端口噪声会
    改变尝试次数, 「恰好 2 次尝试」的断言会被并行抢口打红)。真绑/持有语义由
    test_hold_run_returns_bindable_run 用真实 socket 覆盖, 两用例分工不重叠。
    """
    state = {"attempt": 1, "seq": 0, "saw_close": False}  # 首次 bind 即第 1 次尝试(无前置 close)
    attempts: dict[int, list] = {}

    class _FakeSock:
        """合成 socket: 不创建真实 socket、不做真实 bind。"""
        def __init__(self):
            self.port: int | None = None
            self.closed = False

        def bind(self, addr):
            if state["saw_close"]:  # 上次尝试被整段丢弃 ⇒ 本次 bind 是新尝试开头
                state["attempt"] += 1
                state["seq"] = 0
                state["saw_close"] = False
            state["seq"] += 1
            self.port = addr[1]
            attempts.setdefault(state["attempt"], []).append(self)
            # 基址(seq 1) + 第二位(seq 2) ⇒ 在第二位被拒
            if state["attempt"] == 1 and state["seq"] == 2:
                raise OSError(10013, "以一种访问权限不允许的方式做了一个访问套接字的尝试")
            return None

        def getsockname(self):
            return ("127.0.0.1", self.port)

        def close(self):
            self.closed = True
            state["saw_close"] = True

    monkeypatch.setattr(tp.socket, "socket", _FakeSock)
    base, socks = tp.hold_run(3)
    try:
        assert state["attempt"] == 2, "第二位被拒 ⇒ 必须整段丢弃并重画基址再来一次"
        assert len(attempts[1]) == 2, "拒绝必须落在第一次尝试的第二位(基址/第二位)"
        assert not any(s in attempts[1] for s in socks), "返回的段不能来自被丢弃的第一次尝试(不交坏段)"
        assert [s.getsockname()[1] for s in socks] == [base, base + 1, base + 2]
        assert all(s.closed for s in attempts[1]), "被拒那段的 socket 必须整段关掉(不泄漏、不交坏段)"
        assert not any(s.closed for s in socks), "返回的段必须仍然持有"
    finally:
        for s in socks:
            s.close()


def test_hold_run_width_guard_rejects_oversized_count():
    """count 超出私用段宽度 ⇒ 任何 socket 创建前 RuntimeError(零网络, guard 回潮即红)。"""
    with pytest.raises(RuntimeError, match="超出私用段宽度"):
        tp.hold_run(tp.HOLD_RUN_PORT_HI - tp.HOLD_RUN_PORT_LO + 2)


def test_hold_run_redraws_with_new_random_base(monkeypatch):
    """重画必须重新抽取随机基址 —— randint 提出循环(每轮重绑同一基址)的坏实现在此判红。

    注入仍只落在第 1 次尝试的第二位(与 discards 用例同款合成 socket); randint 桩按序返回
    两个不同基址, 断言 2 次尝试恰触发 2 次抽取(每轮一次)且第二次尝试的整段端口来自第二次
    抽取值。「每轮换新随机基址」是承重面(模块 docstring/常量注释/坑档三处), 不得只钉
    「重画」不钉「重画出新值」。
    """
    state = {"draws": []}

    def _fake_randint(lo, hi):
        assert (lo, hi) == (tp.HOLD_RUN_PORT_LO, tp.HOLD_RUN_PORT_HI - 3 + 1), "抽取区间按 count 收缩"
        state["draws"].append((lo, hi))
        return (21000, 21999)[min(len(state["draws"]) - 1, 1)]

    class _FakeSock:
        """纯合成 socket: 零真实 bind, 第一次尝试(基址 21000)的第二位被拒。"""
        def __init__(self):
            self.port: int | None = None
            self.closed = False

        def bind(self, addr):
            self.port = addr[1]
            if self.port == 21000 + 1:
                raise OSError(10013, "refused")

        def close(self):
            self.closed = True

    monkeypatch.setattr(tp.random, "randint", _fake_randint)
    monkeypatch.setattr(tp.socket, "socket", _FakeSock)
    base, socks = tp.hold_run(3)
    try:
        assert len(state["draws"]) == 2, "2 次尝试 ⇒ 恰 2 次抽取(每轮一次; 提出循环的坏实现只抽 1 次)"
        assert base == 21999 and [s.port for s in socks] == [21999, 22000, 22001], \
            "第二次尝试整段来自第二次抽取的新基址(不是重绑第一次的基址)"
    finally:
        for s in socks:
            s.close()


def test_hold_run_exhausted_retries_raises(monkeypatch):
    """RETRIES 轮重画全败(恒拒) ⇒ RuntimeError 响亮失败, 重画轮数 == RETRIES。

    与 free_port 的 test_exhausted_raises 对称; 本批改了耗尽文案(加私用段区间), 钉住 match
    防文案回退时守阵静默失效。
    """
    state = {"created": 0}

    class _DeadSock:
        def __init__(self):
            state["created"] += 1
            self.closed = False

        def bind(self, addr):
            raise OSError(10048, "occupied")

        def close(self):
            self.closed = True

    monkeypatch.setattr(tp.socket, "socket", _DeadSock)
    with pytest.raises(RuntimeError, match=f"连续 {tp.RETRIES} 次"):
        tp.hold_run(3)
    assert state["created"] == tp.RETRIES, "每轮恰建 1 个 socket(基址位即拒), RETRIES 轮 = RETRIES 个"


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

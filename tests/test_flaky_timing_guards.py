r"""flaky 治理五类守阵: 裸 sleep / waitForTimeout / 裸取时 / bind 位固定口 / route.fetch 收尾兜底接线
(计划 26-11-05-0118 S1; 第 5 类补于 issue 26-11-13-0234 —— 收尾竞态属同族时序 flaky)

时序类 flaky 的防回归闸门 —— 前四类违例模式各配一个扫描器, 存量全进白名单单点
tests/flaky_allowlist.py(带理由, 机器可清点), 守阵做**两侧对账**:
- 新增侧: 扫描出的违例白名单没覆盖 -> 红(新增即红, S2/S3/S4 期间违例只许减不许涨);
- 失效侧: 白名单条目在对应文件已扫不到 / 条数下降 -> 红(清理后必须回来删条目, 白名单只减不涨)。

扫描器口径:
- 1. tests/ 裸 time.sleep: AST 实调用(替换方法上的 patch 字符串与注释提及不算);
- 2. e2e/*.mjs page.waitForTimeout(...): 文本按行(Playwright 头号反模式, S4 换 expect 系);
- 3. src/ 裸 time.time()/time.monotonic[_ns](): AST 实调用(含 from time import 的裸名),
  src/auto_qb/infra/clock.py 路径豁免 —— 那是取时单点本体, 不是违例;
- 4. tests/ 绑定调用位的非 0 字面端口: AST 首个位置参数二元组的端口位(下标 1) —— 拦截面 =
  `.bind(` 方法位 + 构造位绑定族(socketserver 服务族含 HTTP/Threading 变体 + socket.create_server;
  26-11-11-0114: 只拦 .bind( 时 ThreadingHTTPServer(("h", 18788)) 这类构造位不经 .bind(, 可静默绕过)。
  配置值位的固定端口字面量(断言/构造参数)不拦, 只拦真去 bind 的位(碰撞面, 见
  pitfalls/testing/fixed-port-test-collision.md; 子类化改名再实例化与关键字实参位(server_address=(...))属
  静态扫描盲区, 撞上即进白名单带理由)。
  双向禁绑(计划 26-11-10-0515 S5): 生产带 18788 与测试带 28788 都在拦截面内(扫描器拦一切
  非 0 字面, 两带天然同拦; 活性探针两带各探一份, 防「只拦某一侧」的退化), 桩脚本在 scripts/ 不受限。
- 5. e2e/*.spec.mjs 含 route.fetch 调用位却未接线 installRouteCleanup: **硬要求, 无白名单**
  (机制: 桩回调内 await(route.fetch 等)是飞行物, 用例结束时仍在飞的回调其 route 调用报
  "Test ended" 被记成用例失败 —— 断言本体全绿的收尾假红; 兜底 = e2e/lib/route-cleanup.mjs
  的 file 级 afterEach `unrouteAll({ behavior: 'ignoreErrors' })`, 见
  pitfalls/testing/route-callback-teardown-race.md)。文本级扫描(mjs 不进 AST, 同 2. 的口径),
  两侧取噪声方向相反的安全侧: 违例侧看原文按 `route.fetch\s*\(` 调用位判(注释提及也算,
  先取响应再 await 的分离形态同拦)—— 误报只会逼着装兜底; 接线侧剥注释后判**文件顶层**
  (行首无缩进)的调用形态 `installRouteCleanup\s*\(` —— import 单独在场不算接线(把调用注释掉
  ≠ 接线, 防「注释掉临时关闸」), describe 内缩进调用也不算(afterEach 只覆盖该 describe);
  兜底单点本体另有静态钉(lib 剥注释后必须含 unrouteAll + ignoreErrors 字面, 缺一即红)。
  扫描面边界: 只扫 *.spec.mjs, 桩助手收敛进 e2e/lib/ 时本守阵对那些 spec 失明须同步扩面。
  运行期差分守阵经实证不可构造(route 调用「结束后才发起」被 playwright 静默吞掉不归账;
  in-flight 跨界窗 = 服务端往返毫秒级不可控), 差分证据 = 修复轮复验(修前单跑 6 例 2 红(2/6)
  ↔ 修后全绿)。

检出能力由合成源红验内建(同 test_test_plan_docstring_guard 的自证结构): 每个扫描器都有
"该抓的抓得到 + 不该抓的放得过"断言, 扫描逻辑退化即红(guard-dead-branch / static-guard-mutation
两坑的固化防御)。

## 测试计划

- test_repo_no_new_bare_sleep_in_tests: 1. 全仓对账 —— tests/ 裸 sleep 新增/失效两侧零漂移
- test_repo_no_new_wait_for_timeout_in_e2e: 2. 全仓对账 —— e2e waitForTimeout 零漂移
- test_repo_no_bare_time_calls_in_src: 3. 全仓对账 —— src/ 裸取时零漂移(clock.py 豁免)
- test_repo_no_fixed_port_bind_in_tests: 4. 全仓对账 —— bind 位固定端口零漂移
- test_repo_route_fetch_specs_wired_route_cleanup: 5. 全仓守阵 —— route.fetch spec 接线兜底零漂移
- test_reconcile_flags_new_and_stale: 对账函数单测 —— 超额/缺额/缺文件两侧都能报, 行文本全等口径
- test_sleep_scanner_liveness: 1. 活性探针 —— 实调用抓到, patch 字符串/注释不误伤
- test_wait_timeout_scanner_liveness: 2. 活性探针 —— waitForTimeout 抓到, toHaveTimeout/同词根不误伤
- test_bare_time_scanner_liveness: 3. 活性探针 —— time.time/monotonic(_ns)/裸名抓到, strftime 不误伤, clock.py 豁免
- test_bind_scanner_liveness: 4. 活性探针 —— .bind( 位与构造位(ThreadingHTTPServer/create_server)字面非 0 端口
  都抓到(双向禁绑: 18788 与 28788 都探), port=0/变量/配置值位/非绑定构造名不误伤
- test_route_cleanup_wiring_scanner_liveness: 5. 活性探针 —— 未接线/两行全注释/只注释调用行/describe
  作用域调用/注释提及/分离 await 六形态抓到, 已接线/纯 route.fulfill 不误伤
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

import flaky_allowlist as allow

REPO = Path(__file__).resolve().parent.parent

#: 取时单点本体的路径豁免(guard 3.): 它内部的 time.time/monotonic 是单点定义, 不是违例
CLOCK_SINGLETON = "src/auto_qb/infra/clock.py"

# ---------- 扫描器(纯函数: 输入 (相对路径, 源文本) 流, 输出 文件 -> {行文本: 条数}) ----------


def _py_sources(base: str):
    """目录下全部 .py 的 (仓库相对路径, 源文本); 跳过虚拟环境/依赖目录"""
    for p in sorted((REPO / base).rglob("*.py")):
        if any(x in p.parts for x in (".venv", "node_modules", "__pycache__")):
            continue
        yield p.relative_to(REPO).as_posix(), p.read_text(encoding="utf-8", errors="ignore")


def _scan_calls(sources, match) -> dict[str, Counter]:
    """AST 实调用扫描骨架: match(call_node, func_node) 判违例, 行文本计数"""
    out: dict[str, Counter] = {}
    for rel, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue  # 收集面外的坏文件不归本守阵管(语法错误自有收集期报)
        lines = src.splitlines()
        counter: Counter = Counter()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and match(node.func):
                counter[lines[node.lineno - 1].strip()] += 1
        if counter:
            out[rel] = counter
    return out


def _is_time_attr_call(func: ast.expr) -> bool:
    """time.time / time.monotonic / time.monotonic_ns 裸直调"""
    return (
        isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "time" and
        func.attr in ("time", "monotonic", "monotonic_ns")
    )


def _is_time_bare_name_call(func: ast.expr) -> bool:
    """from time import monotonic[ _ns] 后的裸名直调"""
    return isinstance(func, ast.Name) and func.id in ("monotonic", "monotonic_ns")


def scan_sleep(sources) -> dict[str, Counter]:
    """1. tests/ 裸 time.sleep(...) 实调用"""
    return _scan_calls(
        sources,
        lambda f: isinstance(f, ast.Attribute) and f.attr == "sleep" and isinstance(f.value, ast.Name) and f.value.id ==
        "time",
    )


def scan_wait_timeout(sources) -> dict[str, Counter]:
    """2. e2e 的 waitForTimeout(...) 按行文本(mjs 不进 AST, 文本扫描)"""
    out: dict[str, Counter] = {}
    for rel, src in sources:
        counter = Counter(s.strip() for s in src.splitlines() if "waitForTimeout(" in s)
        if counter:
            out[rel] = counter
    return out


def scan_bare_time(sources) -> dict[str, Counter]:
    """3. src/ 裸取时实调用(单点 clock.py 路径豁免)"""
    hits = _scan_calls(sources, lambda f: _is_time_attr_call(f) or _is_time_bare_name_call(f))
    hits.pop(CLOCK_SINGLETON, None)
    return hits


#: 构造位绑定族(26-11-11-0114): 不经 .bind( 直接在构造实参里占口的形态 —— socketserver 服务族
#: (含 HTTP/Threading/Forking 变体)与 socket.create_server(裸名/属性两形态); 子类化改名再实例化与
#: 关键字实参位属静态扫描盲区, 撞上即进白名单带理由(与存量口径一致)
BIND_CONSTRUCTOR_NAMES = frozenset(
    {
        "TCPServer",
        "UDPServer",
        "ThreadingTCPServer",
        "ThreadingUDPServer",
        "ForkingTCPServer",
        "ForkingUDPServer",
        "HTTPServer",
        "ThreadingHTTPServer",
    }
)


def _is_binding_site_call(func: ast.expr) -> bool:
    """真去占口的调用位: 任意对象 .bind( 方法位, 或构造位绑定族(裸名与属性形态都算)"""
    if isinstance(func, ast.Name):
        return func.id in BIND_CONSTRUCTOR_NAMES or func.id == "create_server"  # from-import 裸名形态
    if isinstance(func, ast.Attribute):
        if func.attr == "bind":
            return True
        if func.attr == "create_server":
            return isinstance(func.value, ast.Name) and func.value.id == "socket"  # socket.create_server
        return func.attr in BIND_CONSTRUCTOR_NAMES  # socketserver.TCPServer / http.server.HTTPServer 等
    return False


def scan_bind_ports(sources) -> dict[str, Counter]:
    """4. 绑定调用位第一个参数二元组的端口位(下标 1)的非 0 整数字面量(.bind( 位 + 构造位绑定族)"""
    out: dict[str, Counter] = {}
    for rel, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        counter: Counter = Counter()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_binding_site_call(node.func) and node.args):
                continue
            arg = node.args[0]
            if (
                isinstance(arg, ast.Tuple) and len(arg.elts) >= 2 and isinstance(arg.elts[1], ast.Constant) and
                isinstance(arg.elts[1].value, int) and not isinstance(arg.elts[1].value, bool) and
                arg.elts[1].value != 0
            ):
                counter[lines[node.lineno - 1].strip()] += 1
        if counter:
            out[rel] = counter
    return out


#: mjs 注释剥除(接线侧判据用): 先块后行 —— 行注释里的 `http://` 一类串会被行注释规则吃掉,
#: 但那只影响接线侧的搜索面, 误剥只会把"已接线"误判成"未接线"(逼着装兜底, 向安全侧偏差)
_MJS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_MJS_LINE_COMMENT = re.compile(r"//[^\n]*")


def _strip_mjs_comments(src: str) -> str:
    return _MJS_BLOCK_COMMENT.sub("", _MJS_LINE_COMMENT.sub("", src))


#: 违例/接线两侧的调用位形态(评审轮 1 收紧 / 轮 4 顶层锚, 26-11-13-0234): 违例侧原文匹配
#: (注释提及也算, `const resp = route.fetch()` 先取后 await 的分离形态同拦); 接线侧剥注释后
#: 必须见**文件顶层**(行首无缩进)的调用形态 —— import 单独在场不算(只注释调用行 = 临时关闸),
#: describe 作用域内的缩进调用也不算(afterEach 只覆盖该 describe, 同文件 describe 外用例裸奔)
_ROUTE_FETCH_CALL = re.compile(r"route\.fetch\s*\(")
_ROUTE_CLEANUP_CALL = re.compile(r"^installRouteCleanup\s*\(", re.M)


def scan_route_fetch_unwired(sources) -> list[str]:
    """5. e2e spec 含 route.fetch 调用位却未接线 route 收尾兜底(issue 26-11-13-0234):
    桩回调内 await(route.fetch) 是飞行物, 用例结束时仍在飞的回调其 route 调用报
    "Test ended" 记成用例失败 —— 接线 = 文件顶层 installRouteCleanup(test)
    (e2e/lib/route-cleanup.mjs 的 file 级 afterEach unrouteAll ignoreErrors)。
    文本级扫描(mjs 不进 AST, 同 scan_wait_timeout 口径), 返回未接线的相对路径有序表。
    两侧取噪声方向相反的安全侧: 违例侧看原文(注释提及也算, 逼着接线);
    接线侧剥注释后判「文件顶层的调用形态」(把调用注释掉 ≠ 接线, 防「注释掉临时关闸」;
    describe 内缩进调用 ≠ 顶层, 防 describe 外用例裸奔)。扫描面边界: 只扫 *.spec.mjs ——
    桩助手若收敛进 e2e/lib/(spec 文本不再含 route.fetch), 本守阵对那些 spec 静默失明,
    届时须同步扩面(评审轮 4 记录的前置边界, 现树无非 spec 的 route.fetch 调用位)。"""
    out = []
    for rel, src in sorted(sources):
        if not _ROUTE_FETCH_CALL.search(src):
            continue
        if not _ROUTE_CLEANUP_CALL.search(_strip_mjs_comments(src)):
            out.append(rel)
    return out


# ---------- 对账(两侧: 新增 / 失效) ----------


def _new_violations(actual: dict[str, Counter], allowed: dict[str, dict[str, int]]) -> list[str]:
    """白名单没覆盖的违例(文件不在表内 / 行文本不在条目内 / 条数超出)"""
    out = []
    for f, counter in actual.items():
        rule = allowed.get(f, {})
        for line, n in sorted(counter.items()):
            excess = n - rule.get(line, 0)
            if excess > 0:
                out.append(f"{f}: 超出白名单 {excess} 处 x {line}")
    return out


def _stale_entries(actual: dict[str, Counter], allowed: dict[str, dict[str, int]]) -> list[str]:
    """失效条目(文件已无任何违例 / 行文本扫不到 / 条数下降)—— 清理后必须同步删条目"""
    out = []
    for f, rule in allowed.items():
        counter = actual.get(f, Counter())
        for line, n in sorted(rule.items()):
            deficit = n - counter.get(line, 0)
            if deficit > 0:
                out.append(f"{f}: 白名单条目失效(实扫 {counter.get(line, 0)}/{n}) x {line}")
    return out


def _reconcile(actual: dict[str, Counter], allowed: dict[str, dict[str, int]]) -> None:
    """两侧对账断言: 新增与失效都是失败(消息直接给出要补/要删的条目)"""
    new = _new_violations(actual, allowed)
    stale = _stale_entries(actual, allowed)
    assert not new, "新增违例须先进 tests/flaky_allowlist.py 带理由登记(或直接修掉):\n" + "\n".join(new)
    assert not stale, "白名单有失效条目(存量已清理), 须同步删除收紧:\n" + "\n".join(stale)


# ---------- 全仓守阵(五类) ----------


def test_repo_no_new_bare_sleep_in_tests():
    _reconcile(scan_sleep(_py_sources("tests")), allow.ALLOW_SLEEP_TESTS)


def test_repo_no_new_wait_for_timeout_in_e2e():
    sources = (
        (p.relative_to(REPO).as_posix(), p.read_text(encoding="utf-8")) for p in sorted((REPO / "e2e").rglob("*.mjs"))
    )
    _reconcile(scan_wait_timeout(sources), allow.ALLOW_WAIT_TIMEOUT_E2E)


def test_repo_no_bare_time_calls_in_src():
    _reconcile(scan_bare_time(_py_sources("src")), allow.ALLOW_TIME_SRC)


def test_repo_no_fixed_port_bind_in_tests():
    _reconcile(scan_bind_ports(_py_sources("tests")), allow.ALLOW_BIND_PORT)


def test_repo_route_fetch_specs_wired_route_cleanup():
    sources = (
        (p.relative_to(REPO).as_posix(), p.read_text(encoding="utf-8"))
        for p in sorted((REPO / "e2e").rglob("*.spec.mjs"))
    )
    unwired = scan_route_fetch_unwired(sources)
    assert not unwired, (
        "含 route.fetch( 调用位的 e2e spec 必须在文件顶层接线 installRouteCleanup(test)"
        "(e2e/lib/route-cleanup.mjs; 机制与判据见 memory-bank/pitfalls/testing/route-callback-teardown-race.md):\n" +
        "\n".join(unwired)
    )
    # 兜底单点本体也要钉(评审轮 4): 接线守卫只看 spec 文本, lib 被改坏(删 afterEach 体/
    # 丢 ignoreErrors 改默认等待语义)时接线全在场、守阵全绿, 收尾假红静默复活
    lib = _strip_mjs_comments((REPO / "e2e/lib/route-cleanup.mjs").read_text(encoding="utf-8"))
    missing = [k for k in ("unrouteAll", "ignoreErrors") if k not in lib]
    assert not missing, f"e2e/lib/route-cleanup.mjs 兜底语义字面缺失({missing}), 收尾竞态兜底已被改坏"


# ---------- 对账函数单测(行文本全等 + 条数口径) ----------


def test_reconcile_flags_new_and_stale():
    actual = {"a.py": Counter({"time.sleep(1)": 2}), "c.py": Counter({"time.sleep(9)": 1})}
    allowed = {"a.py": {"time.sleep(1)": 1}, "b.py": {"time.sleep(2)": 1}, "c.py": {"time.sleep(9)": 1}}
    new = _new_violations(actual, allowed)
    stale = _stale_entries(actual, allowed)
    assert new == ["a.py: 超出白名单 1 处 x time.sleep(1)"], new  # 超额按条数报
    assert stale == ["b.py: 白名单条目失效(实扫 0/1) x time.sleep(2)"], stale  # a 超额只在新增侧, c 覆盖恰好
    assert "b.py: 白名单条目失效(实扫 0/1) x time.sleep(2)" in _stale_entries({}, allowed)  # 整文件清零也报
    assert _new_violations({}, {"a.py": {"time.sleep(1)": 1}}) == []  # 空实扫只触发失效侧, 不误报新增


# ---------- 活性探针(合成源红验: 扫描逻辑退化即红) ----------

SRC_SLEEP_BAD = """import time


def f():
    time.sleep(1)  # 新冒头的固定睡等
"""

SRC_SLEEP_PATCH_OK = """import time
from unittest.mock import patch


def f():
    # patch 字符串与注释里的 time.sleep 不该误伤: 它们不是真的睡
    with patch("auto_qb.x.time.sleep"):
        pass
"""

SRC_WAIT_BAD = "await page.waitForTimeout(300);\n"
SRC_WAIT_OK = (
    "await expect(page.getByText('x')).toHaveTimeout(300);\n"  # 同词根但非 waitForTimeout 调用
    "// 历史注释: 这里曾用 page.waitForTimeout —— 注释行按行文本计, 但守阵对账的是全行\n"
)

SRC_TIME_BAD = """import time


def f():
    return time.time() + time.monotonic() + time.monotonic_ns()
"""

SRC_TIME_BARE_IMPORT_BAD = """from time import monotonic


def f():
    return monotonic()
"""

SRC_TIME_OK = """import time


def f():
    return time.strftime("%H%M")  # 非取时调用, 不拦
"""

SRC_BIND_BAD = """def f(sock):
    sock.bind(("127.0.0.1", 18788))  # bind 位的字面固定口(生产带)
"""

SRC_BIND_BAD_TESTBAND = """def f(sock):
    sock.bind(("127.0.0.1", 28788))  # bind 位的字面固定口(测试带, 双向禁绑另一侧)
"""

SRC_BIND_OK = """PORT = 18788


def f(sock, port):
    sock.bind(("127.0.0.1", 0))  # OS 分配
    sock.bind(("127.0.0.1", PORT))  # 变量位(经配置/取号单点), 不属 bind 字面位
    assert PORT == 18788  # 配置值位的固定口字面量, 不拦
"""

SRC_BIND_CONSTRUCTOR_BAD = """from http.server import ThreadingHTTPServer


def f(handler):
    ThreadingHTTPServer(("127.0.0.1", 18788), handler)  # 构造位绑定不经 .bind(, 同拦(生产带)
"""

SRC_BIND_CONSTRUCTOR_BAD_TESTBAND = """import socket


def f():
    socket.create_server(("127.0.0.1", 28788))  # 构造位绑定: create_server 形态(测试带, 双向禁绑另一侧)
"""

SRC_BIND_CONSTRUCTOR_ATTR_BAD = """import socketserver


def f(h):
    socketserver.TCPServer(("127.0.0.1", 18788), h)  # 构造位属性形态: 删 attr 命中分支必红
"""

SRC_BIND_CONSTRUCTOR_BARE_BAD = """from socket import create_server


def f():
    create_server(("127.0.0.1", 28788))  # 构造位裸名形态: from-import, 删裸名分支必红
"""

SRC_BIND_CONSTRUCTOR_OK = """import socket
import socketserver


def f(handler, port):
    ThreadingHTTPServer(("127.0.0.1", 0), handler)  # OS 分配
    socket.create_server(("127.0.0.1", port))  # 变量位
    socketserver.TCPServer(("127.0.0.1", 0), handler)  # 构造位属性形态的放行侧: port=0 照样过
    MyConfig(("127.0.0.1", 18788))  # 非绑定构造族的名字不拦(配置值位口径同 .bind 位)
"""

SRC_ROUTE_UNWIRED = """test('x', async ({ page }) => {
  await page.route('**/api/config', async (route) => {
    const json = await (await route.fetch()).json();  // 回调飞行物: 收尾竞态源
    return route.fulfill({ json });
  });
});
"""

SRC_ROUTE_WIRED = (
    "import { installRouteCleanup } from './lib/route-cleanup.mjs';\n"
    "installRouteCleanup(test);\n\n" + SRC_ROUTE_UNWIRED
)

SRC_ROUTE_FULFILL_ONLY = "await page.route('**/api/x', (route) => route.fulfill({ json: {} }));\n"

#: 注释掉的接线 ≠ 接线: 摘兜底的「注释掉临时关闸」形态也要红(26-11-13-0234 红验补的形态)
SRC_ROUTE_COMMENTED_WIRING = (
    "// import { installRouteCleanup } from './lib/route-cleanup.mjs';\n"
    "// installRouteCleanup(test); // 临时摘除\n\n" + SRC_ROUTE_UNWIRED
)

#: 只注释调用行、留真实 import 的最小摘除形态(评审轮 1 收紧): import 行的标识符单独在场
#: 不构成接线, 照样判未接线 —— 临时关闸最自然的单行改法不得静默绕过
SRC_ROUTE_COMMENTED_CALL_ONLY = (
    "import { installRouteCleanup } from './lib/route-cleanup.mjs';\n"
    "// installRouteCleanup(test); // 临时摘除\n\n" + SRC_ROUTE_UNWIRED
)

#: 分离消费形态: route.fetch( 不与 await 相邻(先取响应再 await), 违例侧照样要拦(评审轮 1)
SRC_ROUTE_DETACHED_AWAIT = """test('x', async ({ page }) => {
  await page.route('**/api/config', async (route) => {
    const resp = route.fetch();  // 先发起
    const json = await (await resp).json();  // 后消费 —— 飞行窗同在
    return route.fulfill({ json });
  });
});
"""

#: route.fetch 仅存在于注释(无真实调用): 违例侧看原文不看剥后文本 —— 该形态照样判未接线,
#: 钉住「违例侧不剥注释」这支(评审轮 4: 若违例侧误套 _strip_mjs_comments, 本形态漏报必红)
SRC_ROUTE_COMMENT_MENTION = (
    "// 历史注释: 这里曾用 await route.fetch() 取真树, 已改走他路\n"
    "test('x', async ({ page }) => { /* 无桩 */ });\n"
)

#: describe 作用域内调用(有缩进): afterEach 只覆盖该 describe, 同文件 describe 外用例裸奔
#: —— 接线侧钉「文件顶层」(剥注释后行首无缩进的调用形态), 缩进位不算接线(评审轮 4)
SRC_ROUTE_SCOPED_CALL = """test.describe('g', () => {
  installRouteCleanup(test);
});

test('bare', async ({ page }) => {
  await page.route('**/api/config', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json });
  });
});
"""


def test_sleep_scanner_liveness():
    bad = scan_sleep([("tests/synthetic_bad.py", SRC_SLEEP_BAD), ("tests/synthetic_ok.py", SRC_SLEEP_PATCH_OK)])
    assert bad == {"tests/synthetic_bad.py": Counter({"time.sleep(1)  # 新冒头的固定睡等": 1})}, bad


def test_wait_timeout_scanner_liveness():
    bad = scan_wait_timeout([("e2e/bad.spec.mjs", SRC_WAIT_BAD), ("e2e/ok.spec.mjs", SRC_WAIT_OK)])
    assert bad == {"e2e/bad.spec.mjs": Counter({"await page.waitForTimeout(300);": 1})}, bad


def test_bare_time_scanner_liveness():
    sources = [
        ("src/x/bad.py", SRC_TIME_BAD),
        ("src/x/bare_import.py", SRC_TIME_BARE_IMPORT_BAD),
        ("src/x/ok.py", SRC_TIME_OK),
        (CLOCK_SINGLETON, SRC_TIME_BAD),  # 单点本体同源码: 路径豁免
    ]
    bad = scan_bare_time(sources)
    assert set(bad) == {"src/x/bad.py", "src/x/bare_import.py"}, bad
    assert bad["src/x/bad.py"] == Counter({"return time.time() + time.monotonic() + time.monotonic_ns()": 3}), bad


def test_bind_scanner_liveness():
    bad = scan_bind_ports(
        [
            ("tests/bad.py", SRC_BIND_BAD),
            ("tests/bad_band2.py", SRC_BIND_BAD_TESTBAND),
            ("tests/bad_ctor.py", SRC_BIND_CONSTRUCTOR_BAD),
            ("tests/bad_ctor_band2.py", SRC_BIND_CONSTRUCTOR_BAD_TESTBAND),
            ("tests/bad_ctor_attr.py", SRC_BIND_CONSTRUCTOR_ATTR_BAD),
            ("tests/bad_ctor_bare.py", SRC_BIND_CONSTRUCTOR_BARE_BAD),
            ("tests/ok.py", SRC_BIND_OK),
            ("tests/ok_ctor.py", SRC_BIND_CONSTRUCTOR_OK),
        ]
    )
    # 双向禁绑: 生产带(18788)与测试带(28788)两字面各探一份 —— 扫描器退化成「只拦某一侧」必红;
    # 构造位探四份(socketserver 族裸名/属性 + create_server 属性/裸名)—— 只拦 .bind( 或漏任一形态即红(26-11-11-0114)
    assert bad == {
        "tests/bad.py":
            Counter({'sock.bind(("127.0.0.1", 18788))  # bind 位的字面固定口(生产带)': 1}),
        "tests/bad_band2.py":
            Counter({'sock.bind(("127.0.0.1", 28788))  # bind 位的字面固定口(测试带, 双向禁绑另一侧)': 1}),
        "tests/bad_ctor.py":
            Counter({'ThreadingHTTPServer(("127.0.0.1", 18788), handler)  # 构造位绑定不经 .bind(, 同拦(生产带)': 1}),
        "tests/bad_ctor_band2.py":
            Counter({'socket.create_server(("127.0.0.1", 28788))  # 构造位绑定: create_server 形态(测试带, 双向禁绑另一侧)': 1}),
        "tests/bad_ctor_attr.py":
            Counter({'socketserver.TCPServer(("127.0.0.1", 18788), h)  # 构造位属性形态: 删 attr 命中分支必红': 1}),
        "tests/bad_ctor_bare.py":
            Counter({'create_server(("127.0.0.1", 28788))  # 构造位裸名形态: from-import, 删裸名分支必红': 1}),
    }, bad


def test_route_cleanup_wiring_scanner_liveness():
    sources = [
        ("e2e/unwired.spec.mjs", SRC_ROUTE_UNWIRED),
        ("e2e/wired.spec.mjs", SRC_ROUTE_WIRED),
        ("e2e/commented_wiring.spec.mjs", SRC_ROUTE_COMMENTED_WIRING),
        ("e2e/commented_call_only.spec.mjs", SRC_ROUTE_COMMENTED_CALL_ONLY),
        ("e2e/scoped_call.spec.mjs", SRC_ROUTE_SCOPED_CALL),
        ("e2e/comment_mention.spec.mjs", SRC_ROUTE_COMMENT_MENTION),
        ("e2e/detached_await_unwired.spec.mjs", SRC_ROUTE_DETACHED_AWAIT),
        ("e2e/fulfill_only.spec.mjs", SRC_ROUTE_FULFILL_ONLY),
    ]
    # 未接线抓到; 已接线放过; 注释掉的接线(两行全注释 / 只注释调用行)都算未接线;
    # describe 作用域调用(缩进位)不算顶层接线; 注释提及(route.fetch 仅在注释)也算违例;
    # 分离 await 形态拦到; 纯 route.fulfill(同步桩, 无飞行窗)不误伤
    assert scan_route_fetch_unwired(sources) == [
        "e2e/comment_mention.spec.mjs",
        "e2e/commented_call_only.spec.mjs",
        "e2e/commented_wiring.spec.mjs",
        "e2e/detached_await_unwired.spec.mjs",
        "e2e/scoped_call.spec.mjs",
        "e2e/unwired.spec.mjs",
    ]

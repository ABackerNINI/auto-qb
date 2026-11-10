"""flaky 治理四类守阵: 裸 sleep / waitForTimeout / 裸取时 / bind 位固定口(计划 26-11-05-0118 S1)

时序类 flaky 的防回归闸门 —— 四类违例模式各配一个扫描器, 存量全进白名单单点
tests/flaky_allowlist.py(带理由, 机器可清点), 守阵做**两侧对账**:
- 新增侧: 扫描出的违例白名单没覆盖 -> 红(新增即红, S2/S3/S4 期间违例只许减不许涨);
- 失效侧: 白名单条目在对应文件已扫不到 / 条数下降 -> 红(清理后必须回来删条目, 白名单只减不涨)。

扫描器口径:
- 1. tests/ 裸 time.sleep: AST 实调用(替换方法上的 patch 字符串与注释提及不算);
- 2. e2e/*.mjs page.waitForTimeout(...): 文本按行(Playwright 头号反模式, S4 换 expect 系);
- 3. src/ 裸 time.time()/time.monotonic[_ns](): AST 实调用(含 from time import 的裸名),
  src/auto_qb/infra/clock.py 路径豁免 —— 那是取时单点本体, 不是违例;
- 4. tests/ bind 调用位的非 0 字面端口: AST(bind((host, <int>))) —— 配置值位的固定端口
  字面量(断言/构造参数)不拦, 只拦真去 bind 的位(碰撞面, 见 pitfalls/testing/fixed-port-test-collision.md)。
  双向禁绑(计划 26-11-10-0515 S5): 生产带 18788 与测试带 28788 都在拦截面内(扫描器拦一切
  非 0 字面, 两带天然同拦; 活性探针两带各探一份, 防「只拦某一侧」的退化), 桩脚本在 scripts/ 不受限。

检出能力由合成源红验内建(同 test_test_plan_docstring_guard 的自证结构): 每个扫描器都有
"该抓的抓得到 + 不该抓的放得过"断言, 扫描逻辑退化即红(guard-dead-branch / static-guard-mutation
两坑的固化防御)。

## 测试计划

- test_repo_no_new_bare_sleep_in_tests: 1. 全仓对账 —— tests/ 裸 sleep 新增/失效两侧零漂移
- test_repo_no_new_wait_for_timeout_in_e2e: 2. 全仓对账 —— e2e waitForTimeout 零漂移
- test_repo_no_bare_time_calls_in_src: 3. 全仓对账 —— src/ 裸取时零漂移(clock.py 豁免)
- test_repo_no_fixed_port_bind_in_tests: 4. 全仓对账 —— bind 位固定端口零漂移
- test_reconcile_flags_new_and_stale: 对账函数单测 —— 超额/缺额/缺文件两侧都能报, 行文本全等口径
- test_sleep_scanner_liveness: 1. 活性探针 —— 实调用抓到, patch 字符串/注释不误伤
- test_wait_timeout_scanner_liveness: 2. 活性探针 —— waitForTimeout 抓到, toHaveTimeout/同词根不误伤
- test_bare_time_scanner_liveness: 3. 活性探针 —— time.time/monotonic(_ns)/裸名抓到, strftime 不误伤, clock.py 豁免
- test_bind_scanner_liveness: 4. 活性探针 —— 字面非 0 端口抓到(双向禁绑: 18788 与 28788 都探), port=0/变量/配置值位不误伤
"""
from __future__ import annotations

import ast
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


def scan_bind_ports(sources) -> dict[str, Counter]:
    """4. bind 调用位第一个参数二元组的端口位(下标 1)的非 0 整数字面量"""
    def _fixed_port_call(func: ast.expr) -> bool:
        return isinstance(func, ast.Attribute) and func.attr == "bind"

    out: dict[str, Counter] = {}
    for rel, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        counter: Counter = Counter()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _fixed_port_call(node.func) and node.args):
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


# ---------- 全仓守阵(四类) ----------


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
        [("tests/bad.py", SRC_BIND_BAD), ("tests/bad_band2.py", SRC_BIND_BAD_TESTBAND), ("tests/ok.py", SRC_BIND_OK)]
    )
    # 双向禁绑: 生产带(18788)与测试带(28788)两字面各探一份 —— 扫描器退化成「只拦某一侧」必红
    assert bad == {
        "tests/bad.py": Counter({'sock.bind(("127.0.0.1", 18788))  # bind 位的字面固定口(生产带)': 1}),
        "tests/bad_band2.py": Counter({'sock.bind(("127.0.0.1", 28788))  # bind 位的字面固定口(测试带, 双向禁绑另一侧)': 1}),
    }, bad

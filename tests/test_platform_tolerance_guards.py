"""平台容差/跨平台断言守阵: skipif 强制带理由+负责人 + 容差常量自洽(计划 26-11-05-0118 S6/D6)

规范单点 tests/platform_tolerance.py(模块 docstring = 规范摘要); 正文单点
memory-bank/testing/file-conventions.md「跨平台断言规范」节。本文件把规范里**能变成红的**
部分固化:

- **skipif 准入**: tests/ 全部 ``pytest.mark.skipif`` 必须带 ``reason=``(平台/环境语义依据)
  与 ``# owner: <名>``(负责人, 装饰器行范围内) —— 缺任一即红。skip 不是免责: 处置口径
  (理由 + issue 入池)见 flaky 台账「巡检约定」节(memory-bank/testing/flaky-ledger.md)。
- **容差常量自洽**: 下界余量 >= 2 tick(计划口径), 刻度常量不被无意改小 —— 挂钟下界断言的
  余量全部走单点, 手写魔数靠 code review 把关(静态扫描"- 0.02"误报面大, 不做扫描守阵)。
- **文本子进程不依赖宿主码页**: ``text=True`` / ``universal_newlines=True`` 的 ``subprocess`` 调用
  必须显式 ``encoding="utf-8"`` + ``errors="replace"``。node 输出恒为 UTF-8, 而 GitHub
  ``windows-latest`` 是 cp1252 / 中文开发机是 cp936 —— 让 locale 猜会把 ``UnicodeDecodeError``
  抛在 ``subprocess._readerthread`` 后台线程里(表现为 ``proc.stdout is None``, 或 stderr 读线程
  退出后子进程卡在写管道上直到超时)。2026-11-06 CI 一次红了 6 条 node 探针, 12 处调用漏声明。
  口径单点见 pitfalls/ops/console-encoding.md 与 pitfalls/testing/ci-only-guard.md。
  守阵**同时校验值**: 只查"声明在不在"会把 ``errors="strict"``(正是超时根因)放过去。

检出能力由合成源红验内建(同 test_flaky_timing_guards 的自证结构): 每个判定都有
"该抓的抓得到 + 该放的放得过"断言, 判定逻辑退化即红。

## 测试计划

- test_repo_skipif_all_have_reason_and_owner: 1. 全仓对账 —— tests/ 全部 skipif 带 reason + owner
- test_skipif_checker_liveness: 1. 活性探针 —— 缺 owner / 缺 reason 抓到, 双全放得过
- test_platform_tolerance_constants_sane: 2. 常量自洽 —— 下界余量 >= 2 tick 且刻度常量未被改小
- test_repo_text_subprocess_calls_pin_utf8: 3. 全仓对账 —— src/、tests/ 与 scripts/ 全部文本子进程显式 UTF-8 + replace
- test_text_subprocess_checker_liveness: 3. 活性探针 —— 漏声明/值错/双模式抓到, 字节模式与动态形态放得过
"""
from __future__ import annotations

import ast
from pathlib import Path

import platform_tolerance

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "tests"
SCRIPTS = REPO / "scripts"
SRC = REPO / "src"


def _is_pytest_mark_skipif_call(func: ast.expr) -> bool:
    """pytest.mark.skipif(...) 调用形态(仓库统一写法, 别名 import 不在口径内)"""
    return (
        isinstance(func, ast.Attribute) and func.attr == "skipif" and isinstance(func.value, ast.Attribute) and
        func.value.attr == "mark" and isinstance(func.value.value, ast.Name) and func.value.value.id == "pytest"
    )


def _has_reason(call: ast.Call) -> bool:
    """reason= 关键字或第一个位置参数是字符串字面量"""
    if any(kw.arg == "reason" for kw in call.keywords):
        return True
    return bool(call.args) and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)


def check_skipif(path: Path, source: str) -> list[str]:
    """单文件 skipif 违例清单: 缺 reason / 缺 owner 各报一条。纯函数(源文本进出), 便于红验。"""
    out: list[str] = []
    rel = path.relative_to(REPO).as_posix()
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_pytest_mark_skipif_call(node.func)):
            continue
        where = f"{rel}:{node.lineno}"
        if not _has_reason(node):
            out.append(f"{where}: skipif 缺 reason(平台/环境语义依据): {lines[node.lineno - 1].strip()}")
        span = "\n".join(lines[node.lineno - 1:node.end_lineno])
        if "owner:" not in span:
            out.append(f"{where}: skipif 缺负责人(行范围内加 '# owner: <名>'): {lines[node.lineno - 1].strip()}")
    return out


def test_repo_skipif_all_have_reason_and_owner():
    violations: list[str] = []
    for p in sorted(TESTS.glob("*.py")):
        violations.extend(check_skipif(p, p.read_text(encoding="utf-8")))
    assert not violations, "skipif 必须带 reason + # owner:(规范见 tests/platform_tolerance.py):\n" + "\n".join(violations)


# ---------- 活性探针(合成源红验) ----------

SRC_OK = '''import pytest

pytestmark = pytest.mark.skipif(False, reason="win32 专属注册表键名语义, posix 无此键")  # owner: abacker


@pytest.mark.skipif(
    True,
    reason="junction 仅 Windows, posix 真实建不出目录联接",
)  # owner: abacker
def test_a():
    pass
'''

SRC_NO_OWNER = 'import pytest\n\npytestmark = pytest.mark.skipif(False, reason="junction 仅 Windows")\n'
SRC_NO_REASON = "import pytest\n\n@pytest.mark.skipif(True)  # owner: abacker\ndef test_a():\n    pass\n"


def test_skipif_checker_liveness():
    ok = check_skipif(TESTS / "_synthetic_ok.py", SRC_OK)
    assert ok == [], ok  # 双全(单行/多行两种形态)都放得过
    no_owner = check_skipif(TESTS / "_synthetic_bad.py", SRC_NO_OWNER)
    assert len(no_owner) == 1 and "缺负责人" in no_owner[0], no_owner  # 缺 owner 抓到
    no_reason = check_skipif(TESTS / "_synthetic_bad.py", SRC_NO_REASON)
    assert len(no_reason) == 1 and "缺 reason" in no_reason[0], no_reason  # 缺 reason 抓到


# ---------- 容差常量自洽 ----------


def test_platform_tolerance_constants_sane():
    # 计划口径: 下界余量 >= 2 tick(15.6ms x 2 = 31.2ms)—— 覆盖取整方向翻转仍不损失判别力
    assert platform_tolerance.WIN_TIMER_TICK_S == 0.0156, "刻度常量被改小/改大? 先读 timing-tolerance 坑档"
    assert platform_tolerance.SLEEP_LOWER_MARGIN_S >= 2 * platform_tolerance.WIN_TIMER_TICK_S, "下界余量 < 2 tick"
    # 历史口径兜底: 不得弱于 S3 收敛时的 20ms 余量(2026-09-22 实测假红的最小充分余量)
    assert platform_tolerance.SLEEP_LOWER_MARGIN_S >= 0.02


# ---------- 文本子进程捕获口径: 不把解码交给宿主码页 ----------

_TEXT_SUBPROCESS_FUNCS = {"run", "check_output", "check_call", "Popen"}
_TEXT_SUBPROCESS_REQUIRED = {"encoding": "utf-8", "errors": "replace"}


def check_text_subprocess(path: Path, source: str) -> list[str]:
    """文本模式子进程里声明缺失/值不对的调用清单。纯函数(源文本进出), 便于红验。

    只认字面量 True 的 text / universal_newlines —— text=<变量> 的动态形态不误报, 交 code review。
    按函数名而非 import 形态匹配, 同时罩住 ``subprocess.run`` 与 ``from subprocess import run``。
    encoding / errors 不但要声明, 值还须是字面量 utf-8 / replace —— 只查声明在不在会把
    ``errors="strict"``(严格解码打死读线程 → TimeoutExpired)放过去。
    """
    out: list[str] = []
    rel = path.relative_to(REPO).as_posix()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
        if name not in _TEXT_SUBPROCESS_FUNCS:
            continue
        kws = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        modes = [kws[k] for k in ("text", "universal_newlines") if k in kws]
        if not any(isinstance(m, ast.Constant) and m.value is True for m in modes):
            continue
        hint = "(须显式 encoding='utf-8', errors='replace')"
        missing = [key for key in _TEXT_SUBPROCESS_REQUIRED if key not in kws]
        if missing:
            out.append(f"{rel}:{node.lineno}: text=True 缺 {'/'.join(missing)}{hint}")
            continue
        for key, want in _TEXT_SUBPROCESS_REQUIRED.items():
            got = kws[key]
            if not (isinstance(got, ast.Constant) and got.value == want):
                out.append(f"{rel}:{node.lineno}: text=True 的 {key} 不是字面量 {want!r}{hint}")
    return out


def test_repo_text_subprocess_calls_pin_utf8():
    violations: list[str] = []
    for p in sorted(TESTS.rglob("*.py")) + sorted(SCRIPTS.rglob("*.py")) + sorted(SRC.rglob("*.py")):
        violations.extend(check_text_subprocess(p, p.read_text(encoding="utf-8")))
    assert not violations, (
        "文本子进程必须显式 encoding='utf-8' + errors='replace'(英文 Windows runner cp1252 "
        "会打死 subprocess 读线程, 2026-11-06 CI 六连红; 扫描面含 src/、tests/ 与 scripts/, "
        "issue 26-11-07-1216 src/ 与 scripts/ 曾长期漏扫):\n" + "\n".join(violations)
    )


SRC_TEXT_OK = (
    "import subprocess\n"
    'subprocess.run(["node"], text=True, encoding="utf-8", errors="replace")\n'
    'subprocess.check_output(["node"], universal_newlines=True, encoding="utf-8", errors="replace")\n'
    'subprocess.run(["node"], capture_output=True)  # 字节模式不归本守阵\n'
    'subprocess.run(["node"], text=False, capture_output=True)  # 显式字节模式同样放得过\n'
    'subprocess.run(["node"], text=flag, capture_output=True)  # 动态形态不误报, 交 code review\n'
)
SRC_TEXT_BAD = (
    "import subprocess\n"
    'subprocess.run(["node"], text=True)\n'  # 缺两项
    'subprocess.Popen(["node"], universal_newlines=True, encoding="utf-8")\n'  # 缺 errors
    'subprocess.run(["node"], text=True, encoding="utf-8", errors="strict")\n'  # errors 值错(超时根因)
    'subprocess.run(["node"], text=True, encoding="cp1252", errors="replace")\n'  # encoding 值错
    'subprocess.run(["node"], text=True, encoding=None, errors="replace")\n'  # encoding 非字面量
    'subprocess.run(["node"], text=None, universal_newlines=True)\n'  # text=None 不得短路掉后者
)


def test_text_subprocess_checker_liveness():
    assert check_text_subprocess(TESTS / "_synthetic_ok.py", SRC_TEXT_OK) == []
    bad = check_text_subprocess(TESTS / "_synthetic_bad.py", SRC_TEXT_BAD)
    assert len(bad) == 6, bad
    assert "encoding/errors" in bad[0], bad  # 两项都缺
    assert "缺 errors" in bad[1], bad  # 只缺 errors
    assert "errors" in bad[2] and "不是字面量" in bad[2], bad  # 声明了但值错
    assert "encoding" in bad[3] and "不是字面量" in bad[3], bad
    assert "encoding" in bad[4] and "不是字面量" in bad[4], bad
    assert "encoding/errors" in bad[5], bad  # 两个 mode 关键字都在时不得短路

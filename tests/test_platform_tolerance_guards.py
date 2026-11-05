"""平台容差/跨平台断言守阵: skipif 强制带理由+负责人 + 容差常量自洽(计划 26-11-05-0118 S6/D6)

规范单点 tests/platform_tolerance.py(模块 docstring = 规范摘要); 正文单点
memory-bank/testing/file-conventions.md「跨平台断言规范」节。本文件把规范里**能变成红的**
部分固化:

- **skipif 准入**: tests/ 全部 ``pytest.mark.skipif`` 必须带 ``reason=``(平台/环境语义依据)
  与 ``# owner: <名>``(负责人, 装饰器行范围内) —— 缺任一即红。skip 不是免责: 处置口径
  (理由 + issue 入池)见 flaky 台账「巡检约定」节(memory-bank/testing/flaky-ledger.md)。
- **容差常量自洽**: 下界余量 >= 2 tick(计划口径), 刻度常量不被无意改小 —— 挂钟下界断言的
  余量全部走单点, 手写魔数靠 code review 把关(静态扫描"- 0.02"误报面大, 不做扫描守阵)。

检出能力由合成源红验内建(同 test_flaky_timing_guards 的自证结构): 每个判定都有
"该抓的抓得到 + 该放的放得过"断言, 判定逻辑退化即红。

## 测试计划

- test_repo_skipif_all_have_reason_and_owner: 1. 全仓对账 —— tests/ 全部 skipif 带 reason + owner
- test_skipif_checker_liveness: 1. 活性探针 —— 缺 owner / 缺 reason 抓到, 双全放得过
- test_platform_tolerance_constants_sane: 2. 常量自洽 —— 下界余量 >= 2 tick 且刻度常量未被改小
"""
from __future__ import annotations

import ast
from pathlib import Path

import platform_tolerance

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "tests"


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

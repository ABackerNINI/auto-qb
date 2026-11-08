"""infra 依赖纪律 AST 守阵 (issue 26-11-08-0703; 计划 26-09-22-2112 §04 依赖方向表)

infra/__init__.py 声明「infra 只被依赖 —— 不 import core / 表现层 / config」, 此前只靠人记:
R4#18 的 notify.py 曾运行期 `from ..config import NotifyConfig`, 靠人工评审才发现并收进
TYPE_CHECKING 块。本守阵把纪律变成「违反就红」:

- 运行期(含函数内延迟导入): infra/ 下所有 .py 的 import 目标只允许 stdlib / 三方 /
  `auto_qb.infra*`; 解析到 `auto_qb` 根包本身、其它子包(config / core / webui / tray / ...)
  或爬出 auto_qb 根的相对导入一律红。根包也判红是因为 `import auto_qb` 可经属性访问绕到
  任意上游层而不留 import 语句。用「白名单 = infra」而非黑名单枚举, 以后新增层自动罩住。
- TYPE_CHECKING 块: 运行期不执行, 按 R4#18 既定口径放行; 但例外面钉死为只许
  `auto_qb.config*` 的类型引用(notify.py 的 NotifyConfig), core / 表现层即便只做标注
  也不许上行。`if TYPE_CHECKING: ... else: ...` 的 else 分支仍属运行期, 照常检查。

判据按解析后的**全限定名**, 不按文本: `from ..config import X` / `from .. import config` /
`from auto_qb import core` / `import auto_qb.core` / `from auto_qb.core.qbmanager import X`
同归一族; 嵌套包按文件相对 infra/ 的深度算 level, 不写死两层。AST 而非文本扫描还有一个
必要性: 纪律声明本身就写在 __init__.py 的 docstring 里, 纯文本扫描会假红。

## 测试计划(每个测试函数一条)

- test_runtime_rejects_upward_imports: 合成源九种上行 import 形态逐条判红(根包/绝对/相对/from auto_qb import/深层/爬出根)
- test_runtime_allows_intra_infra_stdlib_and_thirdparty: 包内一层相对导入/stdlib/三方/绝对自引用零 finding
- test_type_checking_config_import_is_exempt: notify.py 同形态(R4#18)放行, 运行期与 TYPE_CHECKING 两侧都不红
- test_type_checking_else_branch_is_still_runtime: TYPE_CHECKING 的 else 分支按运行期规则判红
- test_type_checking_rejects_core_and_presentation: TYPE_CHECKING 块内 core / webui 上行判红(config 例外不外扩)
- test_lazy_import_inside_function_is_checked: 函数内延迟上行导入判红(不只扫模块顶层)
- test_scan_dir_flags_violating_file: 真目录(tmp_path)注入违例文件能定位到文件名与行号, 干净文件不误报
- test_repo_infra_imports_follow_discipline: 真仓 infra/ 全量零违例 + 反空转(文件数下限 + 扫到 notify.py 例外节点)
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_DIR = REPO_ROOT / "src" / "auto_qb" / "infra"
PACKAGE_PARTS = ("auto_qb", "infra")
ALLOWED_PREFIX = "auto_qb.infra"
CONFIG_EXCEPTION = "auto_qb.config"
OUTSIDE = "<outside-auto_qb>"


def _is_type_checking_test(test: ast.expr) -> bool:
    """只认 `if TYPE_CHECKING:` / `if typing.TYPE_CHECKING:`; `if not TYPE_CHECKING:` 是运行期分支。"""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING" and isinstance(test.value, ast.Name) and test.value.id == "typing"
    return False


ImportNode = ast.Import | ast.ImportFrom


def _partition_imports(tree: ast.Module) -> tuple[list[ImportNode], list[ImportNode]]:
    """把 import 节点分成 (运行期, TYPE_CHECKING 块内)。

    逐语句体递归而不是 ast.walk 一把抓: TYPE_CHECKING 的 body 运行期恒不执行, 但它的
    orelse 会执行; 函数 / try / with / for 里的延迟导入仍属运行期。
    """
    runtime: list[ImportNode] = []
    type_checking: list[ImportNode] = []

    def walk(body: list[ast.stmt], in_tc: bool) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                (type_checking if in_tc else runtime).append(stmt)
            elif isinstance(stmt, ast.If):
                walk(stmt.body, in_tc or _is_type_checking_test(stmt.test))
                walk(stmt.orelse, in_tc)
            else:
                for child in ast.iter_child_nodes(stmt):
                    if isinstance(child, ast.stmt):
                        walk([child], in_tc)
                    elif isinstance(getattr(child, "body", None), list):
                        walk(child.body, in_tc)  # ExceptHandler / match_case

    walk(tree.body, False)
    return runtime, type_checking


def _targets(node: ast.Import | ast.ImportFrom, rel: Path) -> list[str]:
    """一条 import -> 全限定模块名列表; 相对导入按文件相对 infra/ 的深度解析。"""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level == 0:
        base = node.module or ""
        if base == "auto_qb":
            return [f"auto_qb.{alias.name}" for alias in node.names]
        return [base] if base else [alias.name for alias in node.names]

    pkg = PACKAGE_PARTS + rel.parent.parts
    keep = len(pkg) - (node.level - 1)
    if keep <= 0:
        return [OUTSIDE]
    prefix = ".".join(pkg[:keep])
    if node.module:
        return [f"{prefix}.{node.module}"]
    return [f"{prefix}.{alias.name}" for alias in node.names]  # from .. import config


def _is_forbidden(target: str, allow_config: bool) -> bool:
    if target == OUTSIDE:
        return True
    if target == ALLOWED_PREFIX or target.startswith(ALLOWED_PREFIX + "."):
        return False  # infra 包内 / 绝对自引用
    if allow_config and (target == CONFIG_EXCEPTION or target.startswith(CONFIG_EXCEPTION + ".")):
        return False  # R4#18 唯一例外: 类型标注引用 NotifyConfig
    if target != "auto_qb" and not target.startswith("auto_qb."):
        return False  # stdlib / 三方
    return True  # 根包与其余 auto_qb 子包都是上行依赖


def _describe(node: ast.Import | ast.ImportFrom) -> str:
    names = ", ".join(alias.name for alias in node.names)
    if isinstance(node, ast.Import):
        return f"import {names}"
    return f"from {'.' * node.level}{node.module or ''} import {names}"


def _findings(nodes: list[ImportNode], rel: Path, allow_config: bool, label: str) -> list[str]:
    found = []
    for node in nodes:
        for target in _targets(node, rel):
            if _is_forbidden(target, allow_config):
                found.append(f"{label} {rel}:{node.lineno} {_describe(node)} -> {target}")
                break
    return found


def _scan_tree(tree: ast.Module, rel: Path) -> list[str]:
    runtime, type_checking = _partition_imports(tree)
    return (_findings(runtime, rel, False, "[runtime]") + _findings(type_checking, rel, True, "[type-checking]"))


def scan_source(source: str, rel: str = "mod.py") -> list[str]:
    """扫一段源码, 返回违例描述(空 = 合规); 合成源红验与真仓扫描走同一条路径。"""
    p = Path(rel)
    return _scan_tree(ast.parse(source, filename=rel), p)


def scan_dir(root: Path) -> list[str]:
    """扫目录下全部 .py(含嵌套包), 跳过 __pycache__。"""
    found = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(root))
        found.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return found


# ---- 合成源样本: 每种上行形态各一条, 逐条钉住「解析后判红」而不是「文本命中」 ----
UPWARD_CASES = (
    "import auto_qb",
    "import auto_qb.config",
    "import auto_qb.core.qbmanager",
    "from auto_qb import config",
    "from auto_qb.core.qbmanager import QbManager",
    "from ..config import NotifyConfig",
    "from .. import config",
    "from ..webui import WebUIRuntime",
    "from ...core import qbapi",
)

CLEAN_SOURCE = """import os
import logging
from typing import TYPE_CHECKING, Optional
from filelock import FileLock
from . import utils
from .clock import SYSTEM_CLOCK
from auto_qb.infra import clock
"""


def test_runtime_rejects_upward_imports():
    for source in UPWARD_CASES:
        found = scan_source(source)
        assert len(found) == 1 and found[0].startswith("[runtime]"), (source, found)


def test_runtime_allows_intra_infra_stdlib_and_thirdparty():
    assert scan_source(CLEAN_SOURCE) == []


def test_type_checking_config_import_is_exempt():
    """notify.py 现状: 运行期零依赖, TYPE_CHECKING 里的 config 引用属唯一例外。"""
    source = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import NotifyConfig
"""
    assert scan_source(source) == []
    assert scan_source(source, rel="notify.py") == []


def test_type_checking_else_branch_is_still_runtime():
    source = """from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import NotifyConfig
else:
    from ..core import QbManager
"""
    found = scan_source(source)
    assert len(found) == 1 and "[runtime]" in found[0] and "..core" in found[0], found


def test_type_checking_rejects_core_and_presentation():
    for module in ("..core", "..webui", "..tray"):
        source = f"from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from {module} import X\n"
        found = scan_source(source)
        assert len(found) == 1 and "[type-checking]" in found[0], (module, found)


def test_lazy_import_inside_function_is_checked():
    source = """def late():
    from ..config import NotifyConfig
    return NotifyConfig
"""
    found = scan_source(source)
    assert len(found) == 1 and ":2 " in found[0], found


def test_scan_dir_flags_violating_file(tmp_path):
    (tmp_path / "clean.py").write_text(CLEAN_SOURCE, encoding="utf-8")
    (tmp_path / "bad.py").write_text("from ..config import NotifyConfig\n", encoding="utf-8")
    found = scan_dir(tmp_path)
    assert len(found) == 1 and "bad.py:1" in found[0], found
    assert "clean.py" not in found[0]


def test_repo_infra_imports_follow_discipline():
    files = [p for p in INFRA_DIR.rglob("*.py") if "__pycache__" not in p.parts]
    assert len(files) >= 10, f"infra/ 扫描面异常(只找到 {len(files)} 个 .py), 守阵不能空转"
    assert scan_dir(INFRA_DIR) == []

    # 反空转: 扫描器确实走到 notify.py 的 TYPE_CHECKING 例外, 而不是把整块入口漏掉
    tree = ast.parse((INFRA_DIR / "notify.py").read_text(encoding="utf-8"))
    _runtime, type_checking = _partition_imports(tree)
    assert any(isinstance(n, ast.ImportFrom) and n.level >= 2
               for n in type_checking), ("notify.py 的 TYPE_CHECKING 例外节点没被扫到, 放行口径可能是空判")

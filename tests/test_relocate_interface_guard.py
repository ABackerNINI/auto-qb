"""relocate 家族接口面 AST 守阵(计划 26-11-15-2340 §04 S5-2; 骨架套 test_infra_import_discipline)

S5 验收里「grep 无跨层私有引用」此前只靠 grep 人肉, 本守阵把接口面纪律变成「违反就红」。
四条判据(全部按解析后的**全限定名**判, 不按文本命中; 相对导入解析成全限定名后与绝对
导入同族, webui 深层相对路径 `from ....core.modules...` 天然覆盖):

- P1 禁入面 import: 非 relocate 家族文件(家族 = core/modules/relocate_{mod,exec,lifecycle,
  plan,probe,proof,common,units}.py)import 解析到 `auto_qb.core.modules.relocate_{probe,
  lifecycle,exec,plan,mod,proof,common}` -> 红; relocate_units 是公开判定层, 族外一律可依。
  TYPE_CHECKING 块运行期不执行(R4#18 既有口径), 但豁免钉死为 core/module.py 一处; 运行期
  豁免钉死为 core/modules/__init__.py 一处(RelocateModule 再导出装配面)。qbmanager 的
  `from .modules import RelocateModule` 是包级 import, 解析目标不是 relocate_* 子模块,
  天然不命中, 不设豁免。
- P2 跨界私有名 import: 非 family 文件 `from X import N` 且 N 以 `_` 开头、X 解析到
  relocate 家族模块 -> 红。射程只在 relocate 家族的私有名(现靶 _RESUME_RETRY_MAX 已随
  S5-2 清零, 本条防回归); 其它包(config/hr/...)的包内私有共享是各包自己的纪律, 不在本
  守阵射程, 误扫会大面积假红。tests 不在扫描根(src/auto_qb)内, 全豁免。
- P3 三登记名直读: 非 family 文件出现 `relocating_hashes` / `resuming_hashes` /
  `relocating_alias_roots` 的**直读**(ast.Attribute.attr / ast.Name.id, 或 getattr/setattr
  名称参数位的字符串常量)-> 红。三登记集已随 S5-1 退役为 RelocateModule 的派生查询**方法**
  (同名), 所以「紧随调用的 Attribute/Name(func 位)」是 S5 合法消费面(fuse/grouping/
  ops_skip/qbapi 四处), 只有**不带调用的直读**(把名字当登记集属性/变量取值)判红 ——
  这正是防「绕过派生查询语义、直接摸登记集」回归的钉。docstring 不进 AST, 文字提及不误红;
  getattr/setattr 只认名称参数位(ast.Constant), 不扫所有字符串。
- P4 钉扎消费面收口: qbapi.py 与 webui/views_*.py、webui/relocate_chain.py、
  webui/server/routes/relocate_chain.py 的 relocate 家族 import 目标只准是 relocate_units
  (P1 的特例强化: 这批文件是 S5 拍板的收口面, 家族面哪怕将来对其它文件放宽, 钉扎面仍
  锁死 units 单点)。

合成源红验与真仓扫描走同一条 scan_source() 路径(仿 test_infra :137-140); 白名单/豁免
逐条带理由、单点置顶可清点(仿 test_manager_single_point)。

## 测试计划(每个测试函数一条)

- test_p1_flags_cross_family_imports: 非 family 文件 import probe/lifecycle 等禁入模块(相对/绝对 ImportFrom/包路径+子模块名/ast.Import/函数内延迟 五形态)逐条判红; TYPE_CHECKING 形态在非豁免文件判 [P1-tc]
- test_p1_allows_units_family_and_pinned_exemptions: units 族外可依 / 家族内部互依 / __init__ 与 module.py 两处豁免生效, 同形态换到非豁免文件即红
- test_p2_flags_family_private_name_imports: 家族模块私有名跨界 import 判红(含与 P1 并发); 家族内部私有共享放行; 非家族源(config)的私有 import 不在射程
- test_p3_flags_registry_name_direct_reads: 三登记名直读(属性/裸名/getattr/setattr 参数位)判红; 紧随调用的派生查询是合法消费面; family 文件豁免
- test_p4_pins_consumer_import_surface: 四条钉扎消费面(qbapi/views_*/relocate_chain/routes_relocate_chain)逐条非 units 家族 import 红验 + units 放行, 且 P4 只对钉扎面生效
- test_repo_relocate_interface_surface_is_clean: 真仓 src/auto_qb 全量零违例 + 反空转(文件数下限 + 钉扎面在场 + qbapi 真实 import 解析到 units + fuse_mod 派生查询调用确实走到豁免分支)
"""
from __future__ import annotations

import ast
import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOT = REPO_ROOT / "src" / "auto_qb"
PACKAGE_PARTS = ("auto_qb", )
OUTSIDE = "<outside-auto_qb>"

UNITS_MODULE = "auto_qb.core.modules.relocate_units"
FAMILY_FILES = frozenset(
    f"core/modules/relocate_{name}.py"
    for name in ("mod", "exec", "lifecycle", "plan", "probe", "proof", "common", "units")
)
FAMILY_MODULES = frozenset(
    f"auto_qb.core.modules.relocate_{name}"
    for name in ("mod", "exec", "lifecycle", "plan", "probe", "proof", "common", "units")
)
FORBIDDEN_FAMILY_MODULES = FAMILY_MODULES - {UNITS_MODULE}
REGISTRY_NAMES = frozenset({"relocating_hashes", "resuming_hashes", "relocating_alias_roots"})

#: 豁免表(单点, 逐条带理由; 新豁免先在此排队, 再改判据):
P1_RUNTIME_EXEMPTS = {
    # RelocateModule 经 modules 包 __init__ 再导出(qbmanager 包级 import 的装配面),
    # __init__ 必须运行期导入 relocate_mod 才能再导出 —— 这是聚合点不是消费点。
    "core/modules/__init__.py": "RelocateModule 再导出装配面(modules 包聚合点)",
}
P1_TYPE_CHECKING_EXEMPTS = {
    # 内核契约层 module.py 的 AppContext.ctx.relocate 类型标注(R4#18 口径: 运行期不执行);
    # 仅此一处 —— webui 等其余文件连 TYPE_CHECKING 也不放行(类型标注统一标到 units 判定层)。
    "core/module.py": "ctx.relocate 类型标注(契约层 TYPE_CHECKING, 运行期零依赖)",
}

#: P4 钉扎消费面(S5 拍板的收口文件; webui/views_*.py 族经通配并入):
P4_PINNED_FILES = frozenset({"core/qbapi.py", "webui/relocate_chain.py", "webui/server/routes/relocate_chain.py"})
P4_VIEWS_PATTERN = "webui/views_*.py"


def _is_family(rel: str) -> bool:
    return rel in FAMILY_FILES


def _is_pinned_consumer(rel: str) -> bool:
    return rel in P4_PINNED_FILES or fnmatch.fnmatch(rel, P4_VIEWS_PATTERN)


def _is_type_checking_test(test: ast.expr) -> bool:
    """只认 `if TYPE_CHECKING:` / `if typing.TYPE_CHECKING:`; `if not TYPE_CHECKING:` 是运行期分支。"""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING" and isinstance(test.value, ast.Name) and test.value.id == "typing"
    return False


ImportNode = ast.Import | ast.ImportFrom


def _partition_imports(tree: ast.Module) -> tuple[list[ImportNode], list[ImportNode]]:
    """把 import 节点分成 (运行期, TYPE_CHECKING 块内)。(骨架搬自 test_infra_import_discipline:
    TYPE_CHECKING 的 body 运行期恒不执行, orelse 会执行; 函数/try/with/for 里的延迟导入仍属运行期。)"""
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


def _import_targets(node: ImportNode, rel: Path) -> list[str]:
    """一条 import -> 可能绑定的全限定名候选(模块目标 + 「包.子模块名」两条腿)。

    `from pkg import name` 有两义: 绑定 pkg 的普通属性或其**子模块** —— P1/P4 对「name 是
    relocate_* 子模块」敏感(如 `from .modules import relocate_probe`), 只取模块路径会漏;
    误报面由 FORBIDDEN/UNITS 的精确全限定名兜住(普通名如 RelocateModule 不在名单)。
    相对导入按文件相对 src/auto_qb 的深度解析(仿 test_infra: level L 从所在包上爬 L-1 层)。
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level == 0:
        base = node.module or ""
        if base == "auto_qb":
            return [f"auto_qb.{alias.name}" for alias in node.names]
        if base:
            return [base] + [f"{base}.{alias.name}" for alias in node.names]
        return [alias.name for alias in node.names]
    pkg = PACKAGE_PARTS + rel.parent.parts
    keep = len(pkg) - (node.level - 1)
    if keep <= 0:
        return [OUTSIDE]
    prefix = ".".join(pkg[:keep])
    if node.module:
        return [f"{prefix}.{node.module}"] + [f"{prefix}.{node.module}.{alias.name}" for alias in node.names]
    return [f"{prefix}.{alias.name}" for alias in node.names]  # from .. import modules


def _describe(node: ImportNode) -> str:
    names = ", ".join(alias.name for alias in node.names)
    if isinstance(node, ast.Import):
        return f"import {names}"
    return f"from {'.' * node.level}{node.module or ''} import {names}"


def _p1(nodes: list[ImportNode], rel: str, label: str) -> list[str]:
    if _is_family(rel):
        return []
    if label == "[P1]" and rel in P1_RUNTIME_EXEMPTS:
        return []
    if label == "[P1-tc]" and rel in P1_TYPE_CHECKING_EXEMPTS:
        return []
    found = []
    for node in nodes:
        for target in _import_targets(node, Path(rel)):
            if target in FORBIDDEN_FAMILY_MODULES:
                found.append(f"{label} {rel}:{node.lineno} {_describe(node)} -> {target}")
                break
    return found


def _p2(nodes: list[ImportNode], rel: str) -> list[str]:
    if _is_family(rel):
        return []  # 家族内部共享私有 helper 是拆分设计面(如 exec <- common._LINK_CHUNK)
    found = []
    for node in nodes:
        if not isinstance(node, ast.ImportFrom):
            continue
        targets = _import_targets(node, Path(rel))
        if not any(t in FAMILY_MODULES for t in targets):
            continue  # 射程 = relocate 家族模块的私有名; 其它包的包内私有不归本守阵
        for alias in node.names:
            if alias.name.startswith("_"):
                found.append(f"[P2] {rel}:{node.lineno} {_describe(node)} -> 私有名 {alias.name}")
    return found


def _p3(tree: ast.Module, rel: str) -> list[str]:
    if _is_family(rel):
        return []
    # S5 派生查询消费面(fuse/grouping/ops_skip/qbapi 的 relocate.<name>() 调用)按「名字
    # 处于 Call 的 func 位」放行 —— 逐 Call 记 func 节点身份, 直读判定跳过这些节点。
    call_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name)):
            call_funcs.add(id(node.func))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in REGISTRY_NAMES:
            if id(node) in call_funcs:
                continue
            found.append(f"[P3] {rel}:{node.lineno} 登记名直读 .{node.attr}")
        elif isinstance(node, ast.Name) and node.id in REGISTRY_NAMES:
            if id(node) in call_funcs:
                continue
            found.append(f"[P3] {rel}:{node.lineno} 登记名直读 {node.id}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name in ("getattr", "setattr") and len(node.args) >= 2:
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in REGISTRY_NAMES:
                    found.append(f"[P3] {rel}:{node.lineno} {name}(..., '{arg.value}', ...) 名称参数位")
    return found


def _p4(nodes: list[ImportNode], rel: str) -> list[str]:
    if not _is_pinned_consumer(rel):
        return []
    found = []
    for node in nodes:
        for target in _import_targets(node, Path(rel)):
            if target in FAMILY_MODULES and target != UNITS_MODULE:
                found.append(f"[P4] {rel}:{node.lineno} {_describe(node)} -> {target} (钉扎消费面只准 relocate_units)")
                break
    return found


def _scan_tree(tree: ast.Module, rel: Path) -> list[str]:
    reln = rel.as_posix()
    runtime, type_checking = _partition_imports(tree)
    return (
        _p1(runtime, reln, "[P1]") + _p1(type_checking, reln, "[P1-tc]") + _p2(runtime + type_checking, reln) +
        _p3(tree, reln) + _p4(runtime + type_checking, reln)
    )


def scan_source(source: str, rel: str = "core/mod_x.py") -> list[str]:
    """扫一段源码, 返回违例描述(空 = 合规); 合成源红验与真仓扫描走同一条路径。"""
    p = Path(rel)
    return _scan_tree(ast.parse(source, filename=rel), p)


def scan_dir(root: Path = SCAN_ROOT) -> list[str]:
    """扫目录下全部 .py(含嵌套包), 跳过 __pycache__。"""
    found = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root)
        found.extend(scan_source(path.read_text(encoding="utf-8"), str(rel)))
    return found


def _tc_source(module: str) -> str:
    return f"from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    {module}\n"


def test_p1_flags_cross_family_imports():
    """非 family 文件 import 禁入面模块(五形态 + 函数内延迟导入)逐条判红; TYPE_CHECKING 在非豁免文件判 [P1-tc]

    rel 取非钉扎消费面(core/exporter.py), 让 P1 单独承重不与 P4 并发(P4 的并发红验在
    test_p4_pins_consumer_import_surface 单独钉)。
    """
    cases = (
        "from ..core.modules.relocate_probe import TAG_PROBE",  # S5-2 前的 qbapi 旧形态(相对)
        "from ..core.modules.relocate_lifecycle import LifecycleMixin",
        "from auto_qb.core.modules.relocate_probe import TAG_PROBE",  # 绝对 ImportFrom(level==0 全限定名)
        "from ..core.modules import relocate_probe",  # 包路径 + 子模块名两义形态(只取模块路径会漏)
        "import auto_qb.core.modules.relocate_probe",
    )
    for source in cases:
        found = scan_source(source, rel="core/exporter.py")
        assert len(found) == 1 and "[P1] " in found[0] and "[P1-tc]" not in found[0], (source, found)
    # 函数内延迟导入仍属运行期(真实现役形态: webui/relocate_chain.py:75/99 局部 import);
    # 分区 walk 不下探函数体的话本条静默漏判且全套仍绿
    lazy = "def late():\n    from ..core.modules.relocate_probe import TAG_PROBE\n    return TAG_PROBE\n"
    found = scan_source(lazy, rel="core/exporter.py")
    assert len(found) == 1 and "[P1] " in found[0] and ":2 " in found[0], found
    found = scan_source(
        _tc_source("from ..core.modules.relocate_lifecycle import LifecycleMixin"), rel="webui/views.py"
    )
    assert len(found) == 1 and "[P1-tc]" in found[0], found


def test_p1_allows_units_family_and_pinned_exemptions():
    """units 族外可依; 家族内部互依; __init__/module.py 两处豁免生效; 同形态挪出豁免即红"""
    assert scan_source(
        "from ..core.modules.relocate_units import chain_gate_hits, file_alias_intersects, is_probe_torrent",
        rel="core/qbapi.py"
    ) == []
    assert scan_source("from .relocate_probe import run_probe", rel="core/modules/relocate_exec.py") == []
    assert scan_source("from .relocate_mod import RelocateModule", rel="core/modules/__init__.py") == []
    assert scan_source(_tc_source("from .modules.relocate_mod import RelocateModule"), rel="core/module.py") == []
    # 反向钉豁免边界: 同形态换到非豁免文件即红(豁免按文件钉, 不按形态全局放行)
    found = scan_source("from .modules.relocate_mod import RelocateModule", rel="core/exporter.py")
    assert len(found) == 1 and "[P1]" in found[0], found
    found = scan_source(_tc_source("from ..core.modules.relocate_lifecycle import X"), rel="core/exporter.py")
    assert len(found) == 1 and "[P1-tc]" in found[0], found


def test_p2_flags_family_private_name_imports():
    """家族模块私有名跨界 import 判红; 家族内部私有共享放行; 非家族源私有 import 不在射程"""
    found = scan_source("from ..core.modules.relocate_units import _norm", rel="webui/relocate_chain.py")
    assert len(found) == 1 and "[P2]" in found[0] and "_norm" in found[0], found
    # 与 P1 并发(lifecycle 禁入 + 私有名): 两判据各出一条
    found = scan_source(
        "from ..core.modules.relocate_lifecycle import _RESUME_RETRY_MAX", rel="webui/views_relocate.py"
    )
    assert any("[P2]" in f for f in found) and any("[P1]" in f and "[P1-tc]" not in f for f in found), found
    assert scan_source(
        "from .relocate_common import _LINK_CHUNK, _native, logger", rel="core/modules/relocate_exec.py"
    ) == []
    assert scan_source("from ..config import _strip_none", rel="core/exporter.py") == []


def test_p3_flags_registry_name_direct_reads():
    """三登记名直读(属性/裸名/getattr/setattr 参数位)判红; 派生查询调用放行; family 豁免"""
    attr_read = "def f(relocate):\n    reg = relocate.relocating_hashes\n    return reg\n"
    getattr_read = 'def f(relocate):\n    return getattr(relocate, "resuming_hashes")\n'
    setattr_write = 'def f(mod):\n    setattr(mod, "relocating_alias_roots", frozenset())\n'
    derived_call = "def f(relocate):\n    return relocate.resuming_hashes()\n"
    for source in (attr_read, getattr_read, setattr_write):
        found = scan_source(source, rel="core/modules/fuse_mod.py")
        assert len(found) == 1 and "[P3]" in found[0], (source, found)
    assert scan_source(derived_call, rel="core/modules/fuse_mod.py") == []
    assert scan_source(attr_read, rel="core/modules/relocate_mod.py") == []
    # docstring/普通字符串提及不误红(不扫所有字符串, 只认 getattr/setattr 名称参数位)
    prose = 'def f(mod):\n    """历史 = mod.relocating_hashes 整表重算"""\n    return mod.other\n'
    assert scan_source(prose, rel="core/modules/fuse_mod.py") == []


def test_p4_pins_consumer_import_surface():
    """钉扎消费面 import 家族非 units 成员判红(units 放行); P4 只对钉扎面文件生效

    webui/views_relocate.py 深两层, 相对导入按两粒度(.... 形态只对 routes 四层包成立);
    `FINALIZE_WINDOW_PHASES as _WINDOW_PHASES` 的 asname 带下划线不算私有 import —— P2 认
    导入名(alias.name), 不认本地绑定名。
    """
    found = scan_source("from ..core.modules.relocate_lifecycle import LifecycleMixin", rel="core/qbapi.py")
    assert any("[P4]" in f for f in found) and any("[P1]" in f and "[P1-tc]" not in f for f in found), found
    found = scan_source(_tc_source("from ..core.modules.relocate_exec import X"), rel="webui/views_relocate.py")
    assert any("[P4]" in f for f in found) and any("[P1-tc]" in f for f in found), found
    assert scan_source("from ..core.modules import relocate_units as ru", rel="webui/views_relocate.py") == []
    assert scan_source(
        "from ....core.modules.relocate_units import FINALIZE_WINDOW_PHASES as _WINDOW_PHASES",
        rel="webui/server/routes/relocate_chain.py"
    ) == []
    # 清单成员资格逐条钉(评审 minor-3): P4_PINNED_FILES + views 通配四条钉扎面各一条非 units
    # 家族 import 红验(qbapi/views 两条在上方), 从清单删任一条后本段当场红; 顺带钉住
    # webui 2 粒度与 routes 4 粒度两种相对深度的解析(选合成红验而非 _is_pinned_consumer
    # 谓词断言: 后者只钉成员资格, 钉不住同文件的判据执行路径)
    found = scan_source("from ..core.modules.relocate_lifecycle import LifecycleMixin", rel="webui/relocate_chain.py")
    assert any("[P4]" in f for f in found), found
    found = scan_source(
        "from ....core.modules.relocate_lifecycle import LifecycleMixin", rel="webui/server/routes/relocate_chain.py"
    )
    assert any("[P4]" in f for f in found), found
    # 非钉扎面文件只吃 P1, 不吃 P4(P4 射程 = S5 拍板的收口文件清单)
    found = scan_source("from ..core.modules.relocate_lifecycle import LifecycleMixin", rel="core/exporter.py")
    assert len(found) == 1 and "[P1]" in found[0] and "[P4]" not in found[0], found


def test_repo_relocate_interface_surface_is_clean():
    """真仓 src/auto_qb 全量零违例 + 反空转: 文件数下限 / 钉扎面在场 / qbapi units import 解析到位 / fuse_mod 调用豁免分支确实被走到"""
    files = [p for p in SCAN_ROOT.rglob("*.py") if "__pycache__" not in p.parts]
    assert len(files) >= 150, f"src/auto_qb 扫描面异常(只找到 {len(files)} 个 .py), 守阵不能空转"
    for pinned in (
        "core/qbapi.py", "webui/views_relocate.py", "webui/relocate_chain.py", "webui/server/routes/relocate_chain.py"
    ):
        assert (SCAN_ROOT / pinned).exists(), f"钉扎消费面 {pinned} 不在扫描集, P4 可能失真"
    assert scan_dir() == []

    # 反空转 1: qbapi 真实 import 经 _import_targets 解析出 units 全限定名(解析器确实工作)
    tree = ast.parse((SCAN_ROOT / "core" / "qbapi.py").read_text(encoding="utf-8"))
    runtime, _tc = _partition_imports(tree)
    targets = [t for node in runtime for t in _import_targets(node, Path("core/qbapi.py"))]
    assert UNITS_MODULE in targets, "qbapi 的 relocate_units import 没被解析到, P1/P4 口径可能空判"

    # 反空转 2: fuse_mod 的 resuming_hashes() 派生查询调用存在(证明 P3 的调用豁免分支承重,
    # 不是「扫到了但没有可豁免对象」的假口径)
    fuse_tree = ast.parse((SCAN_ROOT / "core" / "modules" / "fuse_mod.py").read_text(encoding="utf-8"))
    hits = [
        n for n in ast.walk(fuse_tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "resuming_hashes"
    ]
    assert hits, "fuse_mod 的派生查询调用没被扫到, P3 豁免分支可能是空判"

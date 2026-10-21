"""防复发守阵: QbManager 构造单点 helpers.make_manager 不得被旁路。

守什么: 单点存在但"参数面不够"时, 用例会退回内联装配 —— `FakeConfig()` + 逐段赋值 +
`QbManager("", config=cfg, no_lock=True)` + `mgr.client = FakeClient()`, 一次四行。同一段样板
复制到 15 个文件 89 处后, 改一处装配语义(锁 / 规则加载 / 客户端注入)要改 89 处
(issue 26-10-21-0502-refactor-test-manager-builder-params-dup)。单点已扩参数
(cfg / bare / client / load_rules / **段覆盖), 本守阵负责让"参数不够就绕过"这条路走不通:
新增场景请扩 make_manager 的参数面, 不要内联构造。

判定纯静态: ast.parse 每个 tests/*.py, 找 func 名为 QbManager 的 Call; 唯一豁免是单点所在的
helpers.py 本身。零其它豁免(需要持锁就 no_lock=False, 需要自备配置就 cfg=, 需要空配置就 bare=True)。

## 测试计划

- test_no_inline_qbmanager_construction_outside_helpers: tests/ 下除 helpers.py 外不得出现 QbManager(...) 构造调用, 违规即红并列出 文件:行号
- test_guard_detects_inline_construction: 造一份含内联构造的一次性文件必须被报出(防守阵自身恒绿)
"""

import ast
import pathlib

TESTS_DIR = pathlib.Path(__file__).resolve().parent
SINGLE_POINT_FILE = "helpers.py"  # 构造单点本体


def _inline_constructions(directory=TESTS_DIR):
    """返回 [(相对文件名, 行号)], 即除单点文件外的 QbManager(...) 构造调用"""
    found = []
    for p in sorted(pathlib.Path(directory).glob("*.py")):
        if p.name == SINGLE_POINT_FILE:
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name == "QbManager":
                found.append((p.name, node.lineno))
    return found


def test_no_inline_qbmanager_construction_outside_helpers():
    """tests/ 除 helpers.py 外零内联 QbManager 构造; 有则红并给出 文件:行号"""
    found = _inline_constructions()
    assert not found, (
        "发现内联 QbManager 构造(单点 = helpers.make_manager, 扩它的参数面而不是绕过它):\n" +
        "\n".join(f"  {f}:{line}" for f, line in found)
    )


def test_guard_detects_inline_construction(tmp_path):
    """造一个内联构造的一次性文件必须被报出(防本守阵退化成恒绿)"""
    (tmp_path / "test_synthetic.py").write_text(
        'from auto_qb.core.qbmanager import QbManager\n'
        'def test_x():\n'
        '    mgr = QbManager("", config=None, no_lock=True)\n',
        encoding="utf-8"
    )
    assert _inline_constructions(tmp_path) == [("test_synthetic.py", 3)]

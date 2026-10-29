"""防复发守阵: 受守类的测试构造单点不得被旁路(QbManager / HrRefreshService)。

守什么: 单点存在但"参数面不够"时, 用例会退回内联装配。两单实证:
- QbManager: `FakeConfig()` + 逐段赋值 + `QbManager("", config=cfg, no_lock=True)` +
  `mgr.client = FakeClient()`, 一次四行, 复制到 15 个文件 89 处(issue
  26-10-21-0502-refactor-test-manager-builder-params-dup); 单点是 helpers.make_manager。
- HrRefreshService: 4 个文件各一份本地构造器(181/47/5 次调用) + 10 处内联, 每份只覆盖
  自己需要的参数, 多站 confs / 换 data_dir / sleeper=None 的场景只能绕过它直接 new(issue
  26-10-29-1404-refactor-b-r24a03-hr-service-builder); 单点是 hr_helpers.make_service。

单点已扩全参数面, 本守阵负责让"参数不够就绕过"这条路走不通: 新增场景请扩单点的参数面,
不要内联构造。

判定纯静态: ast.parse 每个 tests/*.py, 找 func 名为受守类的 Call; 唯一豁免是该类单点所在的
文件(见 SINGLE_POINTS), 零其它豁免。收口后 `grep -rn "HrRefreshService(" tests/*.py` 应只剩
单点一处(QbManager 同理)。

## 测试计划

- test_no_inline_qbmanager_construction_outside_helpers: tests/ 下除各单点文件外不得出现
  QbManager(...) / HrRefreshService(...) 构造调用, 违规即红并列出 文件:行号:类名
- test_guard_detects_inline_construction: 造一份含内联构造的一次性文件必须被报出、单点文件
  豁免生效(防守阵自身恒绿)
"""

import ast
import pathlib

TESTS_DIR = pathlib.Path(__file__).resolve().parent
#: 受守类 -> 其装配单点所在文件(该文件豁免; 其它任何文件构造即违规)
SINGLE_POINTS = {
    "QbManager": "helpers.py",
    "HrRefreshService": "hr_helpers.py",
}


def _inline_constructions(directory=TESTS_DIR):
    """返回 [(相对文件名, 行号, 类名)], 即除各单点文件外的受守类构造调用"""
    found = []
    for p in sorted(pathlib.Path(directory).glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name in SINGLE_POINTS and SINGLE_POINTS[name] != p.name:
                found.append((p.name, node.lineno, name))
    return found


def test_no_inline_qbmanager_construction_outside_helpers():
    """tests/ 除各单点文件外零受守类内联构造; 有则红并给出 文件:行号:类名"""
    found = _inline_constructions()
    assert not found, (
        "发现内联构造(单点见 SINGLE_POINTS, 扩它的参数面而不是绕过它):\n" + "\n".join(f"  {f}:{line} {cls}" for f, line, cls in found)
    )


def test_guard_detects_inline_construction(tmp_path):
    """造一个内联构造的一次性文件必须被报出 + 单点文件豁免生效(防本守阵退化成恒绿)"""
    for cls, single_file in sorted(SINGLE_POINTS.items()):
        # 违规文件必须被报出(文件名带类名, 两个探针不互相干扰)
        probe = tmp_path / f"test_synthetic_{cls}.py"
        probe.write_text(f"def test_x():\n    obj = {cls}()\n", encoding="utf-8")
        assert _inline_constructions(tmp_path) == [(probe.name, 2, cls)]
        probe.unlink()
        # 豁免规则自检: 同样的构造落在单点文件里不报
        (tmp_path / single_file).write_text(f"def _f():\n    return {cls}()\n", encoding="utf-8")
        assert _inline_constructions(tmp_path) == []
        (tmp_path / single_file).unlink()

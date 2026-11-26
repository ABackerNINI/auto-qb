"""防复发守阵: 同文件重名的顶层 test_ 函数 = 死测试 (后者遮蔽前者, 前一条从未被收集执行)。

守什么: Python 顶层同名 def 后者覆盖前者, pytest 按模块 dict 收集, 于是重名对里的**前一份**
永远不进用例集 —— 断言再错也是绿的 (真实事故: issue 26-09-20-2212 两对 + 26-10-01-2012
test_config.py 5 对 + test_sim_corpus.py 3 对, 合计 10 对死测试在库里躺过多轮全量绿)。
判定纯静态: ast.parse 每个 tests/*.py, 收集顶层 FunctionDef 的 test_ 名, 同文件内重复即红。
零豁免; 跨文件重名在 pytest 下各自独立收集、互不遮蔽, 不在拦截面内。

## 测试计划

- test_no_duplicate_top_level_test_names_per_file: tests/ 下任一 .py 文件的顶层 test_ 函数名同文件内不得重复 (含被遮蔽对; 零豁免)
- test_no_duplicate_top_level_test_names_reports_file_and_line: 造一个含重名对的一次性文件必须被报出且带文件名 (防守阵自身恒绿)
"""

import ast
import collections
import pathlib

TESTS_DIR = pathlib.Path(__file__).resolve().parent


def _duplicate_test_names_by_file(directory=TESTS_DIR):
    """返回 {文件名: [(重名, [行号...]), ...]}, 只含确有同文件重复的文件"""
    found = {}
    for p in sorted(pathlib.Path(directory).glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        by_name = collections.defaultdict(list)
        for node in tree.body:  # 只看顶层: 类内方法 / 嵌套函数不进 pytest 顶层命名空间, 不构成遮蔽
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                by_name[node.name].append(node.lineno)
        dups = [(name, lines) for name, lines in by_name.items() if len(lines) > 1]
        if dups:
            found[p.name] = dups
    return found


def test_no_duplicate_top_level_test_names_per_file():
    """tests/ 每个文件的顶层 test_ 名同文件内唯一; 有重名即红并列出全部 (名, 行号)"""
    found = _duplicate_test_names_by_file()
    assert not found, (
        "发现同文件重名的顶层测试函数(后者遮蔽前者, 前一份是死测试); "
        "逐字相同者合并保留一份, 有差异者改名让两份都执行:\n" +
        "\n".join(f"  {f}: {n} 行号 {ls}" for f, dups in found.items() for n, ls in dups)
    )


def test_no_duplicate_top_level_test_names_reports_file_and_line(tmp_path):
    """红验: 造含重名对的临时测试目录, 守阵必须报出文件名与行号 (防守阵自身恒绿)"""
    (tmp_path / "test_bad.py").write_text(
        "def test_x():\n    assert True\n\n\ndef test_x():\n    assert False\n",
        encoding="utf-8",
    )
    (tmp_path / "test_ok.py").write_text("def test_y():\n    assert True\n", encoding="utf-8")
    found = _duplicate_test_names_by_file(tmp_path)
    assert list(found) == ["test_bad.py"], found
    assert found["test_bad.py"] == [("test_x", [1, 5])], found


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))

#!/usr/bin/env python3
"""my-commit-flow 的自测 —— stdlib `unittest`, 零依赖, 与被测脚本同目录。

为什么放在 skill 目录而不是项目的 `tests/`: 这份 skill 是**跨项目资产**, 绑进某个仓库的
`tests/` 会把两边耦合起来; 它依赖的是 skill 自己的脚本, 不是那个仓库的 `src/`。
(本项目 `pytest.ini` 的 `testpaths = tests` 也不会收集到它 —— 正合预期。)

跑法:
    python <包>/scripts/test_preflight.py
    python -m unittest discover -s <skill-dir>/scripts -p "test_*.py"

覆盖: 占位符展开(四种 + 展开失败) / 闸门分类与执行(红 → STOP、--no-auto 不执行) /
      配置体检(未知键与 timeout 非法 → STOP) / each_limit 上限 /
      开工自检分类 classify_sync(齐平 / 落后 / 分叉 / 本地领先 / 离线 / 空仓库 / 远端对象缺失)。
"""

from __future__ import annotations

import ast
import builtins
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight  # noqa: E402
from _ship_config import config_problems, find_root, load_config  # noqa: E402

PY = sys.executable


def ctx(root: Path, changed: list[str], each_limit: int = 99) -> dict:
    return {"root": root, "changed": changed, "each_limit": each_limit}


class GlobMatchTest(unittest.TestCase):
    def test_star_matches_across_dirs(self) -> None:
        self.assertTrue(preflight._glob_match("src/auto_qb/a.py", "*.py"))
        self.assertFalse(preflight._glob_match("src/auto_qb/a.py", "*.md"))

    def test_double_star_with_prefix(self) -> None:
        pat = ".agents/skills/**/scripts/*.py"
        self.assertTrue(preflight._glob_match(".agents/skills/my-commit-flow/scripts/preflight.py", pat))
        self.assertTrue(preflight._glob_match(".agents/skills/a/b/scripts/x.py", pat))
        self.assertFalse(preflight._glob_match(".agents/skills/a/b/x.py", pat))


class ExpandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".agents" / "skills" / "create-issue").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_root_placeholder(self) -> None:
        cmds, skip = preflight.expand_run("python <root>/scripts/x.py", ctx(self.root, []))
        self.assertIsNone(skip)
        self.assertEqual(cmds, [f"python {self.root}/scripts/x.py"])

    def test_changed_placeholder(self) -> None:
        cmds, skip = preflight.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["src/b.py", "src/a.py", "a.md"]))
        self.assertIsNone(skip)
        self.assertEqual(cmds, ["yapf -i src/a.py src/b.py"])  # 排序后拼接

    def test_changed_no_match_is_skipped(self) -> None:
        cmds, skip = preflight.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["a.md"]))
        self.assertEqual(cmds, [])
        self.assertIn("无匹配文件", skip or "")

    def test_each_placeholder_fan_out(self) -> None:
        cmds, skip = preflight.expand_run(
            "python <each:.agents/skills/**/scripts/*.py> --help",
            ctx(self.root, [".agents/skills/a/scripts/x.py", ".agents/skills/b/scripts/y.py"])
        )
        self.assertIsNone(skip)
        self.assertEqual(len(cmds), 2)
        self.assertTrue(all(c.endswith("--help") for c in cmds))

    def test_each_limit_exceeded(self) -> None:
        files = [f".agents/skills/s{i}/scripts/x.py" for i in range(3)]
        with self.assertRaises(preflight.ExpandError) as raised:
            preflight.expand_run("python <each:*.py> --help", ctx(self.root, files, each_limit=2))
        self.assertIn("each_limit", str(raised.exception))

    def test_skill_dir_placeholder(self) -> None:
        cmds, skip = preflight.expand_run("python <skill-dir:create-issue>/scripts/gen.py --check", ctx(self.root, []))
        self.assertIsNone(skip)
        found = preflight.find_skill_dir("create-issue", self.root)
        self.assertEqual(cmds, [f"python {found}/scripts/gen.py --check"])

    def test_skill_dir_missing_is_error(self) -> None:
        with self.assertRaises(preflight.ExpandError) as raised:
            preflight.expand_run("python <skill-dir:create-issues>/x.py", ctx(self.root, []))
        self.assertIn("找不到 skill 目录", str(raised.exception))

    def test_unknown_placeholder_is_error(self) -> None:
        with self.assertRaises(preflight.ExpandError) as raised:
            preflight.expand_run("yapf -i <改过的 py 文件>", ctx(self.root, []))
        self.assertIn("无法展开", str(raised.exception))

    def test_quotes_paths_with_spaces(self) -> None:
        cmds, _ = preflight.expand_run("yapf -i <changed:*.py>", ctx(self.root, ["src/a b.py"]))
        self.assertEqual(cmds, ['yapf -i "src/a b.py"'])


class RunAutoGatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _gate(self, cmd: str, auto: bool = True, timeout: int = 60) -> dict:
        return {"match": [""], "run": [cmd], "auto": auto, "timeout": timeout, "note": "测试闸门"}

    def test_passing_gate(self) -> None:
        rows, manual, tails = preflight.run_auto_gates([self._gate(f'"{PY}" -c "pass"')], ctx(self.root, []))
        self.assertEqual(manual, [])
        self.assertEqual(tails, [])
        self.assertTrue(any(r[0] == preflight.PASS and "1 条全过" in r[2] for r in rows))

    def test_failing_gate_is_stop(self) -> None:
        rows, _, tails = preflight.run_auto_gates(
            [self._gate(f'"{PY}" -c "import sys; sys.exit(3)"')], ctx(self.root, [])
        )
        self.assertTrue(any(r[0] == preflight.STOP and "rc=3" in r[2] for r in rows))
        self.assertEqual(len(tails), 1)  # 失败要留末 20 行供定位

    def test_timeout_is_stop(self) -> None:
        rows, _, _ = preflight.run_auto_gates(
            [self._gate(f'"{PY}" -c "import time; time.sleep(5)"', timeout=1)], ctx(self.root, [])
        )
        self.assertTrue(any(r[0] == preflight.STOP and "rc=-1" in r[2] for r in rows))

    def test_no_auto_lists_instead_of_running(self) -> None:
        cmd = f'"{PY}" -c "import sys; sys.exit(3)"'
        rows, manual, tails = preflight.run_auto_gates([self._gate(cmd)], ctx(self.root, []), execute=False)
        self.assertEqual(manual, [cmd])
        self.assertEqual(tails, [])
        self.assertFalse(any(r[0] == preflight.STOP for r in rows))

    def test_manual_gate_is_not_executed(self) -> None:
        cmd = f'"{PY}" -c "import sys; sys.exit(3)"'
        rows, manual, _ = preflight.run_auto_gates([self._gate(cmd, auto=False)], ctx(self.root, []))
        self.assertEqual(manual, [cmd])
        self.assertFalse(any(r[0] == preflight.STOP for r in rows))

    def test_expand_failure_of_auto_gate_is_stop(self) -> None:
        rows, manual, _ = preflight.run_auto_gates([self._gate("python <nope:x>")], ctx(self.root, []))
        self.assertTrue(any(r[0] == preflight.STOP and "展开失败" in r[2] for r in rows))
        self.assertEqual(manual, [])  # 不降级成打印

    def test_gates_for_empty_match_hits_everything(self) -> None:
        gates = [{"match": [""], "run": ["x"], "auto": True}]
        self.assertEqual(len(preflight.gates_for(["src/a.py"], gates)), 1)
        self.assertEqual(preflight.gates_for(["src/a.py"], [{"match": ["docs/"], "run": ["x"]}]), [])


class ClassifySyncTest(unittest.TestCase):
    """classify_sync 是 --check-started 的判定核心(纯函数) —— 七种状态一个不落。"""

    R, H = "ff" * 20, "ab" * 20

    def test_offline_is_warn_not_lockout(self):
        level, msg = preflight.classify_sync("", self.H, None)
        self.assertEqual(level, preflight.WARN)
        self.assertIn("无法验证", msg)

    def test_empty_repo_skips_compare(self):
        level, msg = preflight.classify_sync(self.R, "", None)
        self.assertEqual(level, preflight.WARN)
        self.assertIn("空仓库", msg)

    def test_in_sync_is_pass(self):
        level, msg = preflight.classify_sync(self.R, self.R, None)
        self.assertEqual(level, preflight.PASS)
        self.assertIn("齐平", msg)

    def test_behind_tells_how_to_sync(self):
        level, msg = preflight.classify_sync(self.R, self.H, (3, 0))
        self.assertEqual(level, preflight.WARN)
        self.assertIn("落后 3", msg)
        self.assertIn("--ff-only", msg)

    def test_ahead_only_is_pass(self):
        level, msg = preflight.classify_sync(self.R, self.H, (0, 2))
        self.assertEqual(level, preflight.PASS)
        self.assertIn("本地领先 2", msg)

    def test_diverged_is_warn(self):
        level, msg = preflight.classify_sync(self.R, self.H, (1, 2))
        self.assertEqual(level, preflight.WARN)
        self.assertIn("已分叉", msg)

    def test_remote_object_missing_tells_refetch(self):
        level, msg = preflight.classify_sync(self.R, self.H, None)
        self.assertEqual(level, preflight.WARN)
        self.assertIn("先 fetch", msg)


SPECIALS = {"__name__", "__file__", "__doc__", "__package__", "__spec__", "__loader__", "__builtins__", "__debug__"}


def _bound(node: ast.AST) -> set[str]:
    """某个作用域里**被绑定**的名字 —— 赋值 / 参数 / for / with / except / 推导 / 嵌套定义 / import。"""
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, ast.Global):
            names.update(n.names)
        elif isinstance(n, ast.alias):
            names.add((n.asname or n.name).split(".")[0])
    return names


def _loaded(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def undefined_names(path: Path) -> set[str]:
    """静态找出"用了但从未定义"的名字 —— 冷门分支里的 NameError 只有靠这个才抓得到。

    push.py 曾把 `MIRROR_URL_NOW` 写成 `MIRROR_URL`: 那个分支只有"没找到镜像远端"时才走,
    平时主线推送失败会提前 return, 于是这个未定义名在真机上潜伏到被人踩到为止。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_bound = _bound(tree) | set(dir(builtins)) | SPECIALS
    bad: set[str] = set()

    def walk(node: ast.AST, inherited: set[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                own = _bound(child)
                scope = inherited | own
                bad.update(_loaded(child) - scope)
                walk(child, scope)  # 闭包: 外层绑定的名字对内层可见
            else:
                walk(child, inherited)

    bad.update(_loaded(tree) - module_bound)
    walk(tree, module_bound)
    return bad


class StaticNameTest(unittest.TestCase):
    SCRIPTS = ["_ship_config.py", "preflight.py", "push.py", "commit.py", "verify_ref.py"]
    # memory-bank skill 的脚本同属"改了就可能留下未定义名"的资产, 一并纳入
    # (2026-09-22 目录化重构新增了 4 个; 之前只扫本 skill 自己那 5 个)。
    OTHER_SCRIPTS = (
        ".agents/skills/memory-bank/scripts/_common.py",
        ".agents/skills/memory-bank/scripts/gen_tasks_index.py",
        ".agents/skills/memory-bank/scripts/gen_kb_index.py",
        ".agents/skills/memory-bank/scripts/check_kb_structure.py",
    )

    def test_no_undefined_names_in_other_skill_scripts(self) -> None:
        root = find_root()
        missing = [rel for rel in self.OTHER_SCRIPTS if not (root / rel).is_file()]
        self.assertFalse(missing, f"清单里的脚本不存在(改名了? 同步本清单): {missing}")
        bad = [f"{rel}: {', '.join(sorted(undefined_names(root / rel)))}" for rel in self.OTHER_SCRIPTS]
        bad = [b for b in bad if not b.endswith(": ")]
        self.assertFalse(bad, "memory-bank skill 脚本里有未定义名:\n" + "\n".join(bad))

    def test_no_undefined_names_in_scripts(self) -> None:
        bad = [
            f"{name}: {', '.join(sorted(undefined_names(Path(__file__).resolve().parent / name)))}"
            for name in self.SCRIPTS
        ]
        bad = [line for line in bad if not line.endswith(": ")]
        self.assertEqual(bad, [], "存在未定义的名字(拼写错 / 改名漏改), 会在冷门分支上 NameError")

    def test_checker_actually_catches_undefined_names(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write("def f():\n    return MIRROR_URL\n")
            tmp = Path(fh.name)
        try:
            self.assertEqual(undefined_names(tmp), {"MIRROR_URL"})
        finally:
            tmp.unlink()

    def test_checker_is_not_fooled_by_closure(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write("def outer():\n    x = 1\n    def inner():\n        return x\n    return inner\n")
            tmp = Path(fh.name)
        try:
            self.assertEqual(undefined_names(tmp), set())  # 闭包变量不算未定义
        finally:
            tmp.unlink()


class ConfigProblemsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".my-commit-flow.toml"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _problems(self, text: str) -> list[tuple[str, str]]:
        self.path.write_text(text, encoding="utf-8")
        cfg, _ = load_config(explicit=str(self.path))
        return config_problems(cfg, self.path)

    BASE = 'confirmed = true\nred_lines = ["a"]\n'

    def test_unknown_gate_key_is_stop(self) -> None:
        levels = dict(self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\nauto_run = true\n'))
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\nauto_run = true\n')
        self.assertTrue(any(lvl == "STOP" and "auto_run" in msg for lvl, msg in problems))
        self.assertIn("STOP", levels)  # 键名被点名

    def test_unknown_top_key_is_stop(self) -> None:
        problems = self._problems(self.BASE + "staged_panicc = 5\n")
        self.assertTrue(any(lvl == "STOP" and "staged_panicc" in msg for lvl, msg in problems))

    def test_bad_timeout_is_stop(self) -> None:
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\ntimeout = 0\n')
        self.assertTrue(any(lvl == "STOP" and "timeout" in msg for lvl, msg in problems))

    def test_valid_config_has_no_stop(self) -> None:
        problems = self._problems(self.BASE + '[[gates]]\nmatch = ["src/"]\nrun = ["x"]\nauto = true\ntimeout = 60\n')
        self.assertFalse([p for p in problems if p[0] == "STOP"])

    def test_unconfirmed_draft_is_warn(self) -> None:
        problems = self._problems('confirmed = false\nred_lines = ["a"]\n')
        self.assertTrue(any(lvl == "WARN" and "初稿" in msg for lvl, msg in problems))


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)

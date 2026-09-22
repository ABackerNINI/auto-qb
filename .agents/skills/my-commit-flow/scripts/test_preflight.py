#!/usr/bin/env python3
"""my-commit-flow 的自测 —— stdlib `unittest`, 零依赖, 与被测脚本同目录。

为什么放在 skill 目录而不是项目的 `tests/`: 这份 skill 是**跨项目资产**, 绑进某个仓库的
`tests/` 会把两边耦合起来; 它依赖的是 skill 自己的脚本, 不是那个仓库的 `src/`。
(本项目 `pytest.ini` 的 `testpaths = tests` 也不会收集到它 —— 正合预期。)

跑法:
    python <skill-dir>/scripts/test_preflight.py
    python -m unittest discover -s <skill-dir>/scripts -p "test_*.py"

覆盖: 占位符展开(四种 + 展开失败) / 闸门分类与执行(红 → STOP、--no-auto 不执行) /
      配置体检(未知键与 timeout 非法 → STOP) / each_limit 上限。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preflight  # noqa: E402
from _ship_config import config_problems, load_config  # noqa: E402

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


class ConfigProblemsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".commit-flow.toml"

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

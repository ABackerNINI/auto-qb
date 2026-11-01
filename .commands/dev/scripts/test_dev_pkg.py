"""dev 包配置守阵 —— 闸门 `test.pkg.scoped` 要求改包必带自测(issue 26-11-01-0921, 方案①)。

背景: test.pkg.scoped(计划 26-11-01-0434 方案 C)对改动包跑 `pytest .commands/<包>`,
包内没有任何 test_*.py 时 pytest 收集为空 → 退出码 5 → 闸门 FAIL(fail-closed, 无豁免路径)。
dev/doc/env/kb 四包同款; real 已按先例补过最小自测(.commands/real/scripts/test_real_pkg.py)。
本文件是 dev 包的最小守阵: 不跑任何任务动作, 只静态核 config.toml 与它引用的脚本
(引擎 cwd=仓库根, run 命令里的相对路径一律按仓库根解析)。

跑法: uv run pytest .commands/dev -q --no-cov -n 8 (test.pkg.scoped 口径, TMPDIR 由 wrapper 内置)

## 测试计划
- ConfigTomlTest   config.toml 可解析 + [pack].name == "dev" + 任务必备键(run/timeout/when)
- ScriptRefTest    run 命令引用的 .py 脚本在仓库根下都存在 + 引用抽取非空(防空转假绿)
"""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/dev/scripts/ → .commands/dev/
ROOT = PKG.parents[1]                      # → 仓库根


def _load_cfg() -> dict:
    return tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))


def _py_refs(cfg: dict) -> list[tuple[str, str]]:
    """抽 run 命令里以 .py 结尾的 token, 形如 (task id, token)。"""
    refs: list[tuple[str, str]] = []
    for tid, spec in cfg["tasks"].items():
        for cmd in spec["run"]:
            refs.extend((tid, tok) for tok in cmd.split() if tok.endswith(".py"))
    return refs


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _load_cfg()

    def test_pack_name(self):
        self.assertEqual(self.cfg["pack"]["name"], "dev")

    def test_tasks_have_required_keys(self):
        tasks = self.cfg["tasks"]
        self.assertTrue(tasks, "tasks 段为空")
        for tid, spec in tasks.items():
            for key in ("run", "timeout", "when"):
                self.assertIn(key, spec, f"{tid} 缺 {key}")
            self.assertIsInstance(spec["run"], list, f"{tid}.run 应是命令列表")
            self.assertTrue(spec["run"], f"{tid}.run 为空")


class ScriptRefTest(unittest.TestCase):
    def test_referenced_scripts_exist(self):
        refs = _py_refs(_load_cfg())
        self.assertTrue(refs, "没抽到任何 .py 引用 —— 抽取逻辑空转, 守阵失效")
        for tid, tok in refs:
            self.assertTrue((ROOT / tok).is_file(), f"{tid} 引用的脚本不存在: {tok}")


if __name__ == "__main__":
    unittest.main()

"""env 包配置守阵 —— 闸门 `test.pkg.scoped` 要求改包必带自测(issue 26-11-01-0921, 方案 1)。

背景: test.pkg.scoped(计划 26-11-01-0434 方案 C)对改动包跑 `pytest .commands/<包>`,
包内没有任何 test_*.py 时 pytest 收集为空 → 退出码 5 → 闸门 FAIL(fail-closed, 无豁免路径)。
dev/doc/env/kb 四包同款; real 已按先例补过最小自测(.commands/real/scripts/test_real_pkg.py)。
本文件是 env 包的最小守阵: 不跑任何任务动作(uv sync / 真机 import 都不碰), 只静态核
config.toml 与 env.version 依赖的版本单源。

## 测试计划
- ConfigTomlTest     config.toml 可解析 + [pack].name == "env" + 任务必备键(run/timeout/when)
- VersionSourceTest  env.version 的 inline -c 打印 auto_qb.__version__; 单源按 note 在 src/auto_qb/__init__.py
"""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/env/scripts/ → .commands/env/
ROOT = PKG.parents[1]  # → 仓库根


def _load_cfg() -> dict:
    return tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _load_cfg()

    def test_pack_name(self):
        self.assertEqual(self.cfg["pack"]["name"], "env")

    def test_tasks_have_required_keys(self):
        tasks = self.cfg["tasks"]
        self.assertTrue(tasks, "tasks 段为空")
        for tid, spec in tasks.items():
            for key in ("run", "timeout", "when"):
                self.assertIn(key, spec, f"{tid} 缺 {key}")
            self.assertIsInstance(spec["run"], list, f"{tid}.run 应是命令列表")
            self.assertTrue(spec["run"], f"{tid}.run 为空")


class VersionSourceTest(unittest.TestCase):
    def test_version_single_source(self):
        run = _load_cfg()["tasks"]["env.version"]["run"][0]
        self.assertIn("auto_qb.__version__", run, "env.version 不再打印 auto_qb.__version__, 本守阵判定对象已变")
        init = ROOT / "src" / "auto_qb" / "__init__.py"
        self.assertTrue(init.is_file(), "src/auto_qb/__init__.py 不存在 —— env.version 会直接跑挂")
        self.assertIn("__version__", init.read_text(encoding="utf-8"), "__version__ 单源不在 src/auto_qb/__init__.py")


if __name__ == "__main__":
    unittest.main()

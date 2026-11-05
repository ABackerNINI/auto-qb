"""release 包配置守阵 —— 闸门 `test.pkg.scoped` 要求改包必带自测(env 先例, 26-11-01-0921)。

test.pkg.scoped 对改动包跑 `pytest .commands/<包>`, 包内零 test_*.py 时收集为空 →
退出码 5 → 闸门 FAIL(fail-closed)。本文件是 release 包的最小守阵: 不跑任何任务动作
(不 bump / 不 merge / 不建页), 只静态核 config.toml 结构、task 引用的脚本存在、
以及两条拍板口径的机械面版本(build 必须 --wheel, bump-my-version 配置 commit/tag=false)。

## 测试计划
- ConfigTomlTest     config.toml 可解析 + [pack].name == "release" + 任务必备键 + <args> 占位纪律
- ScriptRefsTest     每条 run 引用的 skill 脚本文件真实存在
- BuildTaskTest      release.build 用 `uv build --wheel`(源根构建)而非全量 uv build(sdist 两段式丢 git 上下文)
- BumpWiringTest     pyproject [tool.bumpversion] commit/tag 均 false(闸门纪律), 与 test_version_guard 互为备份
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/release/scripts/ → .commands/release/
ROOT = PKG.parents[1]  # → 仓库根


def _load_cfg() -> dict:
    return tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _load_cfg()

    def test_pack_name(self):
        self.assertEqual(self.cfg["pack"]["name"], "release")

    def test_tasks_have_required_keys(self):
        tasks = self.cfg["tasks"]
        self.assertTrue(tasks, "tasks 段为空")
        for tid, spec in tasks.items():
            for key in ("run", "timeout", "when"):
                self.assertIn(key, spec, f"{tid} 缺 {key}")
            self.assertIsInstance(spec["run"], list, f"{tid}.run 应是命令列表")
            for cmd in spec["run"]:
                self.assertIsInstance(cmd, str, f"{tid}.run 元素应是命令串(引擎语义: 元素=整条 shell 命令)")

    def test_args_taking_tasks_have_placeholder(self):
        # note 声明"agent 追加参数"的 task 必须带 <args> 占位符, 否则追加参数会被引擎 STOP。
        for tid, spec in self.cfg["tasks"].items():
            needs_args = any(word in spec.get("note", "") for word in ("agent 追加", "<args>"))
            has_placeholder = any("<args>" in cmd for cmd in spec["run"])
            if needs_args:
                self.assertTrue(has_placeholder, f"{tid} note 声明追加参数但 run 缺 <args> 占位符")


class ScriptRefsTest(unittest.TestCase):
    def test_referenced_scripts_exist(self):
        for tid, spec in _load_cfg()["tasks"].items():
            for cmd in spec["run"]:
                for m in re.finditer(r"\.agents/skills/[\w\-/]+\.py", cmd):
                    path = ROOT / m.group(0)
                    self.assertTrue(path.is_file(), f"{tid} 引用的脚本不存在: {m.group(0)}")


class BuildTaskTest(unittest.TestCase):
    def test_build_uses_wheel_only(self):
        run = _load_cfg()["tasks"]["release.build"]["run"]
        joined = " ".join(run)
        self.assertIn("--wheel", joined, "release.build 必须带 --wheel(源根构建保住 git 上下文)")
        self.assertNotRegex(joined, r"uv build(?! --wheel)", "release.build 禁用全量 uv build(sdist 两段式丢 BUILD_ID)")


class BumpWiringTest(unittest.TestCase):
    def test_bumpversion_gates_off(self):
        with (ROOT / "pyproject.toml").open("rb") as fh:
            bump = tomllib.load(fh)["tool"]["bumpversion"]
        self.assertIs(bump["commit"], False, "自动 commit 会绕开 ship.commit 闸门")
        self.assertIs(bump["tag"], False, "自动 tag 会绕开 release.tag 的 ls-remote 核验")


if __name__ == "__main__":
    unittest.main()

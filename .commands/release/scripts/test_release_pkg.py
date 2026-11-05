"""release 包配置守阵 —— 闸门 `test.pkg.scoped` 要求改包必带自测(env 先例, 26-11-01-0921)。

test.pkg.scoped 对改动包跑 `pytest .commands/<包>`, 包内零 test_*.py 时收集为空 →
退出码 5 → 闸门 FAIL(fail-closed)。本文件是 release 包的最小守阵: 不跑任何任务动作
(不 bump / 不 merge / 不建页), 只静态核 config.toml 结构、task 引用的脚本存在、
项目事实参数(远端/分支/仓库名)、以及两条拍板口径的机械面版本(build 必须 --wheel,
bump-my-version 配置 commit/tag=false)。

## 测试计划
- ConfigTomlTest     config.toml 可解析 + [pack].name == "release" + 任务必备键 + <args> 占位纪律(when+note 双扫)
- TaskSetTest        7 条 task id 集合完整 + 项目事实值钉死(gitee/master/双 gh-repo/双远端 tag)
- ScriptRefsTest     每条 run 引用的 skill 脚本文件真实存在
- FlagConsistencyTest config.toml 手写旗标 ⊆ 对应脚本 argparse 的 add_argument 集合(改旗标即红)
- BuildTaskTest      release.build 用 `uv build --wheel`(源根构建)而非全量 uv build(sdist 两段式丢 git 上下文)
- BumpWiringTest     pyproject [tool.bumpversion] commit/tag 均 false + [tool.hatch.build.hooks.custom] 接线在位
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


def _pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _argparse_flags(script_rel: str) -> set[str]:
    """扫被引脚本源码的 add_argument("--x") 旗标集(静态正则, 不 import 不执行)。"""
    src = (ROOT / script_rel).read_text(encoding="utf-8")
    return set(re.findall(r'add_argument\(\s*"(--[\w\-]+)"', src))


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
        # when+note 任一声明的"追加参数"的 task 必须带 <args> 占位符(R2-F1-8: 只扫 note 会漏 when 侧)。
        for tid, spec in self.cfg["tasks"].items():
            declared = spec.get("note", "") + spec.get("when", "")
            needs_args = ("agent 追加" in declared) or ("<args>" in declared)
            has_placeholder = any("<args>" in cmd for cmd in spec["run"])
            if needs_args:
                self.assertTrue(has_placeholder, f"{tid} when/note 声明追加参数但 run 缺 <args> 占位符")


class TaskSetTest(unittest.TestCase):
    def test_seven_tasks_complete(self):
        # 删整条 task(如 release.ci-gate)必须红(R2-F3-3)。
        self.assertEqual(
            set(_load_cfg()["tasks"]),
            {
                "release.suggest",
                "release.bump",
                "release.build",
                "release.merge",
                "release.ci-gate",
                "release.tag",
                "release.page",
            },
        )

    def test_project_facts_pinned(self):
        # 项目事实值改动即红: 发布分支/主线远端/双 gh-repo/tag 双远端。
        tasks = _load_cfg()["tasks"]
        self.assertIn("--remote <args>", tasks["release.merge"]["run"][0], "merge 的远端必须是 <args> 二跑位")
        self.assertIn("--to-branch master", tasks["release.merge"]["run"][0])
        self.assertIn("--gh-repo ABackerNINI/auto-qb", tasks["release.ci-gate"]["run"][0])
        self.assertIn("--remotes gitee,github", tasks["release.tag"]["run"][0])
        self.assertIn("--gitee-repo ABacker/auto-qb", tasks["release.page"]["run"][0])
        self.assertIn("--github-repo ABackerNINI/auto-qb", tasks["release.page"]["run"][0])


class ScriptRefsTest(unittest.TestCase):
    def test_referenced_scripts_exist(self):
        for tid, spec in _load_cfg()["tasks"].items():
            for cmd in spec["run"]:
                for m in re.finditer(r"\.agents/skills/[\w\-/]+\.py", cmd):
                    path = ROOT / m.group(0)
                    self.assertTrue(path.is_file(), f"{tid} 引用的脚本不存在: {m.group(0)}")


class FlagConsistencyTest(unittest.TestCase):
    def test_config_flags_subset_of_argparse(self):
        # config 侧手写旗标必须落在脚本 argparse 集合内(R2-F3-5): 旗标改名/拼错当轮红, 不等发版当场炸。
        for tid, spec in _load_cfg()["tasks"].items():
            for cmd in spec["run"]:
                m = re.search(r"\.agents/skills/release/scripts/([\w\-]+\.py)", cmd)
                if not m:
                    continue
                flags = _argparse_flags(f".agents/skills/release/scripts/{m.group(1)}")
                for flag in re.findall(r"(--[\w\-]+)", cmd):
                    if flag == "--args":  # <args> 占位符不是旗标
                        continue
                    self.assertIn(flag, flags, f"{tid} 的旗标 {flag} 不在 {m.group(1)} 的 argparse 集合内")


class BuildTaskTest(unittest.TestCase):
    def test_build_uses_wheel_only(self):
        run = _load_cfg()["tasks"]["release.build"]["run"]
        joined = " ".join(run)
        self.assertIn("--wheel", joined, "release.build 必须带 --wheel(源根构建保住 git 上下文)")
        self.assertNotRegex(joined, r"uv build(?! --wheel)", "release.build 禁用全量 uv build(sdist 两段式丢 BUILD_ID)")


class BumpWiringTest(unittest.TestCase):
    def test_bumpversion_gates_off(self):
        bump = _pyproject()["tool"]["bumpversion"]
        self.assertIs(bump["commit"], False, "自动 commit 会绕开 ship.commit 闸门")
        self.assertIs(bump["tag"], False, "自动 tag 会绕开 release.tag 的 ls-remote 核验")

    def test_custom_build_hook_wired(self):
        # BUILD_ID 侧车接线被移除时构建静默丢溯源 —— 钉死钩子段存在(R2-F3-4)。
        hatch = _pyproject()["tool"]["hatch"]
        self.assertIn("custom", hatch.get("build", {}).get("hooks", {}), "[tool.hatch.build.hooks.custom] 缺失")


if __name__ == "__main__":
    unittest.main()

"""real 包配置守阵 —— 双环境化(2026-11-01)后闸门 `test.pkg.scoped` 要求改包必带自测。

背景: test.pkg.scoped(计划 26-11-01-0434 方案 C)对改动包跑 `pytest .commands/<包>`,
包内没有 test_*.py 时 pytest 收集为空 → 退出码 5 → 闸门 FAIL(fail-closed, 无豁免路径)。
本文件是 real 包的最小守阵: 不跑任何真机动作, 只静态核配置与脚本的一致性 ——
双环境的端口/EXE 真值在 tests-real/lib/env_registry.py, 那边改了这里跟着红。

跑法: uv run pytest .commands/real -q --no-cov -n 8 (test.pkg.scoped 口径)

## 测试计划
- ConfigTomlTest       config.toml 可解析 + [pack].name == "real" + 任务必备键(run/timeout/when)
- RunnerSubCmdTest     runner.py 型任务的子命令在 runner.py 的 sub.add_parser 清单里(防 task id 与实现脱节)
- ScriptRefTest        任务引用的脚本文件都存在(runner.py / seed.py)
- EnvRegistryTest      env_registry 两环境的端口/EXE 互异且 EXE 键覆盖主副端口, 与 config.toml 的 note 口径不冲突
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/real/scripts/ → .commands/real/
ROOT = PKG.parents[1]                      # → 仓库根

sys.path.insert(0, str(ROOT / "tests-real"))

import unittest


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.raw = (PKG / "config.toml").read_bytes()
        self.cfg = tomllib.loads(self.raw.decode("utf-8"))

    def test_pack_name(self):
        self.assertEqual(self.cfg["pack"]["name"], "real")

    def test_tasks_have_required_keys(self):
        tasks = self.cfg["tasks"]
        self.assertTrue(tasks, "tasks 段为空")
        for tid, spec in tasks.items():
            for key in ("run", "timeout", "when"):
                self.assertIn(key, spec, f"{tid} 缺 {key}")
            self.assertTrue(spec["run"], f"{tid}.run 为空")


class RunnerSubCmdTest(unittest.TestCase):
    def test_runner_tasks_map_to_subcommands(self):
        import re

        runner = (ROOT / "tests-real" / "runner.py").read_text(encoding="utf-8")
        declared = set(re.findall(r'sub\.add_parser\("([^"]+)"', runner))
        # up/down 走循环注册: for name, fn, text in (("up", cmd_up, ...), ...) —— 把元组里的名字也收进来
        declared |= set(re.findall(r'\("([a-z-]+)",\s*cmd_\w+', runner))
        self.assertTrue(declared, "runner.py 里抽不到子命令注册清单")
        cfg = tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))
        for tid, spec in cfg["tasks"].items():
            run = spec["run"][0]
            if "runner.py" not in run:
                continue
            sub = run.split("runner.py", 1)[1].split()[0]
            self.assertIn(sub, declared, f"{tid} 引用的 runner 子命令 {sub!r} 在 runner.py 未注册")


class ScriptRefTest(unittest.TestCase):
    def test_referenced_scripts_exist(self):
        cfg = tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))
        for tid, spec in cfg["tasks"].items():
            for cmd in spec["run"]:
                head = cmd.split()[0]
                if head.endswith(".py"):
                    self.assertTrue((ROOT / head).is_file(), f"{tid} 引用的脚本不存在: {head}")


class EnvRegistryTest(unittest.TestCase):
    def test_envs_consistent(self):
        from lib import env_registry

        envs = env_registry.ENVIRONMENTS
        seen_ports: set[int] = set()
        for eid, env in envs.items():
            p, s = env["primary"], env["secondary"]
            self.assertNotEqual(p, s, f"环境{eid} 主副端口相同")
            self.assertNotIn(p, seen_ports, f"环境{eid} 主端口与其它环境撞车")
            self.assertNotIn(s, seen_ports, f"环境{eid} 副端口与其它环境撞车")
            seen_ports.update({p, s})
            self.assertEqual(set(env["exe"]), {p, s}, f"环境{eid} EXE 键未覆盖主副端口")
            for port, exe in env["exe"].items():
                self.assertTrue(exe.startswith(env["image_prefix"]), f"环境{eid} 端口 {port} EXE 越出镜像前缀")
            for web, bt in env["bt_listen"].items():
                self.assertIn(web, {p, s}, f"环境{eid} bt_listen 键 {web} 不在主副端口内")
                self.assertNotEqual(web, bt, f"环境{eid} WebUI/BT 端口相同: {web}")


if __name__ == "__main__":
    unittest.main()

"""kb 包配置守阵 —— 闸门 `test.pkg.scoped` 要求改包必带自测(issue 26-11-01-0921, 方案①)。

背景: test.pkg.scoped(计划 26-11-01-0434 方案 C)对改动包跑 `pytest .commands/<包>`,
包内没有任何 test_*.py 时 pytest 收集为空 → 退出码 5 → 闸门 FAIL(fail-closed, 无豁免路径)。
dev/doc/env/kb 四包同款; real 已按先例补过最小自测(.commands/real/scripts/test_real_pkg.py)。
本文件是 kb 包的最小守阵: 不跑任何任务动作(gen_all 等生成器都不碰, 只读不写), 只静态核
config.toml 与它引用的脚本 —— kb 的 run 全走 `<skill-dir:memory-bank>/scripts/*.py`,
展开规则单点在引擎 .agents/skills/commands/scripts/_config.py 的 find_skill_dir
(就地加载复用, 不抄候选表)。

跑法: uv run pytest .commands/kb -q --no-cov -n 8 (test.pkg.scoped 口径)

## 测试计划
- ConfigTomlTest   config.toml 可解析 + [pack].name == "kb" + 任务必备键(run/timeout/when)
- ScriptRefTest    run 命令引用的 .py 脚本都存在(skill-dir 占位符按引擎单点展开) + 引用抽取非空(防空转假绿)
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]  # .commands/kb/scripts/ → .commands/kb/
ROOT = PKG.parents[1]                      # → 仓库根

_spec = importlib.util.spec_from_file_location(
    "_commands_engine_config_kbpkg",
    ROOT / ".agents" / "skills" / "commands" / "scripts" / "_config.py",
)
assert _spec is not None and _spec.loader is not None, "引擎 _config.py 不在了, 本守阵无法判定 skill-dir 引用"
_ENGINE = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _ENGINE  # 先注册再 exec: 引擎是 future-annotations + dataclass 模块, 3.13 下不注册会在注解求值期炸 NoneType
_spec.loader.exec_module(_ENGINE)


def _load_cfg() -> dict:
    return tomllib.loads((PKG / "config.toml").read_text(encoding="utf-8"))


def _resolve(tok: str) -> Path | None:
    """token → 真实路径; skill 定位不到返回 None(由调用方记缺失)。"""
    if tok.startswith("<skill-dir:"):
        name, _, rest = tok[len("<skill-dir:"):].partition(">")
        found = _ENGINE.find_skill_dir(name, ROOT)
        return None if found is None else found / rest.lstrip("/")
    return ROOT / tok


def _missing_refs(cfg: dict) -> tuple[int, list[str]]:
    """返回 (.py 引用总数, 缺失清单) —— 总数兼作"抽取非空"判据, 防守阵空转。"""
    total, missing = 0, []
    for tid, spec in cfg["tasks"].items():
        for cmd in spec["run"]:
            for tok in cmd.split():
                if not tok.endswith(".py"):
                    continue
                total += 1
                p = _resolve(tok)
                if p is None or not p.is_file():
                    missing.append(f"{tid}: {tok}")
    return total, missing


class ConfigTomlTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _load_cfg()

    def test_pack_name(self):
        self.assertEqual(self.cfg["pack"]["name"], "kb")

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
        total, missing = _missing_refs(_load_cfg())
        self.assertGreater(total, 0, "没抽到任何 .py 引用 —— 抽取逻辑空转, 守阵失效")
        self.assertEqual(missing, [], "有脚本引用落空")


if __name__ == "__main__":
    unittest.main()

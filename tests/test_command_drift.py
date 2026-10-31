"""check_command_drift 按改动收窄(计划 memory-bank/plans/26-11-01-0434 方案 A)的守卫。

`scan(only=)` 的候选集仍由 SCAN_GLOBS 的 `ROOT.glob` 现算(与全量同源), `only` 只收窄
**读取与逐行比对** —— 本文件用临时 ROOT + 替身骨架做功能测试, 不碰真库; 闸门配置侧的
run 形态钉在 `.commands/my-commit-flow/scripts/test_pipeline.py::GateScopingConfigTest`。

## 测试计划

- test_scan_full_finds_drift_in_all_non_exempt: 全量模式命中全部非豁免病灶; EXEMPT(plans/tasks)不报
- test_scan_only_scopes_files: only 模式只判传入文件 —— 未传入文件的同病灶不报(行号对得上)
- test_scan_only_still_honors_exempt: 收窄**不放松**豁免 —— 传入的豁免文件照旧不报
- test_main_arg_wiring: --files → scan(集合); --full → scan(None); 无参 → scan(None); --files 空参 → scan(None)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("check_command_drift", ROOT / "scripts" / "check_command_drift.py")
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

SKEL = ("test.dummy", "uv run pytest tests -q", mod.skeleton("uv run pytest tests -q"))
DRIFT_LINE = "旧文档写: uv run pytest tests -q\n"


@pytest.fixture()
def kb(tmp_path, monkeypatch):
    """临时 ROOT: 一个根部病灶 + 一个坑档病灶 + 两个豁免病灶(plans/ 与 tasks/)。"""
    (tmp_path / "AGENTS.md").write_text("# 引导\n" + DRIFT_LINE, encoding="utf-8")
    pit = tmp_path / "memory-bank" / "pitfalls" / "git"
    pit.mkdir(parents=True)
    (pit / "x.md").write_text("---\n---\n# 坑\n" + DRIFT_LINE, encoding="utf-8")
    plans = tmp_path / "memory-bank" / "plans"
    plans.mkdir(parents=True)
    (plans / "x.md").write_text("# 历史快照\n" + DRIFT_LINE, encoding="utf-8")
    tasks = tmp_path / "memory-bank" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "26-01-01-x.md").write_text("# 档案\n" + DRIFT_LINE, encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "find_skeletons", lambda: [SKEL])
    return tmp_path


def test_scan_full_finds_drift_in_all_non_exempt(kb):
    hits = mod.scan()
    files = {rel for rel, *_ in hits}
    assert files == {"AGENTS.md", "memory-bank/pitfalls/git/x.md"}, files


def test_scan_only_scopes_files(kb):
    hits = mod.scan(only={"memory-bank/pitfalls/git/x.md"})
    assert [(rel, no) for rel, no, *_ in hits] == [("memory-bank/pitfalls/git/x.md", 4)]
    assert mod.scan(only={"AGENTS.md"})[0][0] == "AGENTS.md"


def test_scan_only_still_honors_exempt(kb):
    assert mod.scan(only={"memory-bank/plans/x.md", "memory-bank/tasks/26-01-01-x.md"}) == []


def test_main_arg_wiring(kb, monkeypatch):
    seen: list = []
    monkeypatch.setattr(mod, "scan", lambda only=None: seen.append(only) or [])
    assert mod.main(["--files", "AGENTS.md", "memory-bank/pitfalls/git/x.md"]) == 0
    assert seen[-1] == {"AGENTS.md", "memory-bank/pitfalls/git/x.md"}
    assert mod.main(["--full", "AGENTS.md"]) == 0
    assert seen[-1] is None
    assert mod.main([]) == 0
    assert seen[-1] is None
    assert mod.main(["--files"]) == 0
    assert seen[-1] is None  # 空参兜底成全量(保守)

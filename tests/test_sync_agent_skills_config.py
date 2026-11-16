"""test_sync_agent_skills_config 测试计划: sync 脚本配置化守卫 (计划 26-11-17-0010 S9)。

守什么: `scripts/sync_agent_skills.py` 的排除项/挂载目标外置在
`.agents/skills/.config/sync.toml`(点前缀目录防被 skill 遍历误收) 后, 三件事不能破:
本仓 sync 行为零变化(出厂配置 == 脚本内置默认)、配置可增删排除项/链接目标、
回落永不静默(缺失/形态不对必打提示, 坏 TOML fail-fast 不回落, D13/R-7)。

## 测试计划

- test_shipped_config_resolves_to_legacy_defaults: 出厂 sync.toml 解析结果 == 改前硬编码
  EXCLUDED/LINK_TARGETS(本仓行为零变化的机检锚)
- test_config_missing_falls_back_with_hint: 无配置 → 内置默认 + 一行回落提示(禁静默降级)
- test_config_can_add_and_remove_entries: 配置可增删排除项; link_targets 相对路径按仓库根
  解析、绝对路径原样采用
- test_explicit_empty_lists_are_legal: 显式空列表 = 合法配置(不排除/不挂载, 不提示不回落)
- test_malformed_sections_fall_back_with_hint: 值非数组/混型含非 str/节缺失 → 回落默认 + 提示
- test_bad_toml_fails_fast: 坏 TOML → TOMLDecodeError 裸抛(坏配置不是「缺失」)
- test_dot_prefixed_dirs_are_never_skills: `.config/` 等点前缀目录不进 skill 清单(D19 防误收)
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync_agent_skills.py"
SHIPPED_CONFIG = REPO_ROOT / ".agents" / "skills" / ".config" / "sync.toml"

# 改前硬编码值 (2026-11-17 S9 收编进 sync.toml 之前) —— 行为零变化的对照锚。
LEGACY_EXCLUDED = {"autoclaw-design-capability"}
LEGACY_TARGETS = [REPO_ROOT / ".codebuddy" / "skills"]


def _load_module():
    spec = importlib.util.spec_from_file_location("sync_agent_skills", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sync(tmp_path, monkeypatch):
    """隔离态: SYNC_CONFIG/REPO_ROOT 指到 tmp_path, 不碰真实仓库文件。"""
    module = _load_module()
    monkeypatch.setattr(module, "SYNC_CONFIG", tmp_path / "sync.toml")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    return module


def _write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_shipped_config_resolves_to_legacy_defaults():
    """出厂 sync.toml 的解析结果必须与改前硬编码值逐项相等(行为零变化锚)。"""
    module = _load_module()
    excluded, targets, hints = module.resolve_sync_config()
    assert not hints  # 出厂配置齐备, 不该有任何回落提示
    assert excluded == LEGACY_EXCLUDED
    assert targets == LEGACY_TARGETS
    # 点前缀防误收的另一半: 出厂配置就住在 .config/ 下, 文件必须真实存在(防被挪走后静默回落)
    assert SHIPPED_CONFIG.is_file()


def test_config_missing_falls_back_with_hint(sync):
    assert not sync.SYNC_CONFIG.exists()
    excluded, targets, hints = sync.resolve_sync_config()
    assert excluded == set(sync.DEFAULT_EXCLUDED)
    assert targets == [sync.REPO_ROOT / p for p in sync.DEFAULT_LINK_TARGETS]
    assert len(hints) == 1 and "回落内置默认" in hints[0]


def test_config_can_add_and_remove_entries(sync):
    _write(
        sync.SYNC_CONFIG, '\n[exclude]\nnames = ["code-review", "autoclaw-design-capability"]\n\n'
        '[link_targets]\npaths = [".zcode/skills", "/abs/nowhere/skills"]\n'
    )
    excluded, targets, hints = sync.resolve_sync_config()
    assert not hints
    assert excluded == {"code-review", "autoclaw-design-capability"}  # 增删后按配置生效
    assert targets == [sync.REPO_ROOT / ".zcode" / "skills", Path("/abs/nowhere/skills")]


def test_explicit_empty_lists_are_legal(sync):
    _write(sync.SYNC_CONFIG, "[exclude]\nnames = []\n\n[link_targets]\npaths = []\n")
    excluded, targets, hints = sync.resolve_sync_config()
    assert excluded == set() and targets == [] and not hints  # 合法配置, 不回落不提示


@pytest.mark.parametrize(
    "body",
    [
        '[exclude]\nnames = "oops"\n',  # 值非数组
        '[exclude]\nnames = ["x", 2]\n',  # 混型含非 str
        "[exclude]\nwrong_key = []\n",  # 键缺失
        "[other]\nnames = []\n",  # 节缺失
        "[link_targets]\npaths = [1]\n[exclude]\n",  # link_targets 面混型, exclude 节缺失
    ]
)
def test_malformed_sections_fall_back_with_hint(sync, body):
    _write(sync.SYNC_CONFIG, body)
    excluded, targets, hints = sync.resolve_sync_config()
    assert excluded == set(sync.DEFAULT_EXCLUDED)
    assert targets == [sync.REPO_ROOT / p for p in sync.DEFAULT_LINK_TARGETS]
    assert hints and all("回落" in h for h in hints)


def test_bad_toml_fails_fast(sync):
    _write(sync.SYNC_CONFIG, "[exclude\nnames = [bad")
    with pytest.raises(tomllib.TOMLDecodeError):
        sync.resolve_sync_config()


def test_dot_prefixed_dirs_are_never_skills():
    """`.config/` 等点前缀目录不进 skill 清单 —— 防配置面被当成 skill 遍历/链接 (D19)。"""
    module = _load_module()
    names = module.list_source_skills(set())
    assert names and all(not name.startswith(".") for name in names)
    assert ".config" not in names

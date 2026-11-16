"""test_deps_upgrade_user_agent —— deps-upgrade skill User-Agent 外置守阵 (计划 26-11-17-0010 S11 批9b)。

背景: `check_updates.py` 的 HTTP User-Agent 曾硬编码项目词 `auto-qb-deps-upgrade/1.0`,
S11 grep 白名单审计判为轨道内操作性命中 (未申报)。批9b 照 S1 同款模式外置到
`<skill>/config/project.toml` `[user_agent] value`(D19 统一落点): 缺失/形态不对回落
**通用**默认 + stderr 提示一次 (D13 提示着降级, 非静默); 坏 TOML fail-fast。

本文件进程内 import check_updates (importlib 按路径加载, 不起子进程, 不发网络请求)。

## 测试计划

- test_user_agent_from_config: 配置在场读配置值 (改 toml 即生效, 不触代码)
- test_user_agent_fallback_generic_and_hint: 配置缺失回落通用默认 (零项目词) + 必打提示行一次
- test_user_agent_malformed_value_falls_back: value 非字符串 / 空白串 → 回落 + 提示 (禁静默)
- test_user_agent_broken_toml_fails_fast: 坏 TOML → 异常上抛 (坏配置不是「缺失」)
"""
from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/deps-upgrade/scripts/check_updates.py"
_spec = importlib.util.spec_from_file_location("deps_check_updates", _SCRIPT)
check_updates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_updates)


def _write_cfg(tmp_path: Path, text: str | None) -> Path:
    """写 tmp 配置并让模块指向它; text=None = 配置文件不存在。"""
    if text is None:
        path = tmp_path / "missing-project.toml"
    else:
        path = tmp_path / "project.toml"
        path.write_text(text, encoding="utf-8")
    return path


def test_user_agent_from_config(tmp_path: Path, monkeypatch, capsys) -> None:
    """配置在场 → 读配置值; 不打回落提示 (配置存在 = 行为与旧硬编码版一致)。"""
    cfg = _write_cfg(tmp_path, '[user_agent]\nvalue = "farm-deps/2.0 (ro)"\n')
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", cfg)
    monkeypatch.setattr(check_updates, "_user_agent_hint_done", False)
    assert check_updates.user_agent() == "farm-deps/2.0 (ro)"
    assert capsys.readouterr().err == "", "配置在场不得打回落提示行"


def test_user_agent_fallback_generic_and_hint(tmp_path: Path, monkeypatch, capsys) -> None:
    """配置缺失 → 回落**通用**默认 (零项目词 —— 项目标识属于配置不属于代码) 且 stderr
    **必打**提示行 (D13); 提示只打一次。"""
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", _write_cfg(tmp_path, None))
    monkeypatch.setattr(check_updates, "_user_agent_hint_done", False)
    ua = check_updates.user_agent()
    assert ua == check_updates.DEFAULT_USER_AGENT, "回落通用默认"
    assert "auto_qb" not in ua and "auto-qb" not in ua, "通用默认零项目词"
    err1 = capsys.readouterr().err
    assert "[DEPS-CONFIG]" in err1 and "User-Agent" in err1, f"回落必打提示行: {err1}"
    check_updates.user_agent()
    assert capsys.readouterr().err == "", "提示只打一次"


def test_user_agent_malformed_value_falls_back(tmp_path: Path, monkeypatch, capsys) -> None:
    """value 非字符串 / 空白串 / 节非表 → 同缺失: 回落 + 提示 (禁静默降级)。"""
    monkeypatch.setattr(check_updates, "_user_agent_hint_done", False)
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", _write_cfg(tmp_path, '[user_agent]\nvalue = 2\n'))
    assert check_updates.user_agent() == check_updates.DEFAULT_USER_AGENT
    assert "[DEPS-CONFIG]" in capsys.readouterr().err

    monkeypatch.setattr(check_updates, "_user_agent_hint_done", False)
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", _write_cfg(tmp_path, '[user_agent]\nvalue = "  "\n'))
    assert check_updates.user_agent() == check_updates.DEFAULT_USER_AGENT, "空白串 = 未配置"
    assert "[DEPS-CONFIG]" in capsys.readouterr().err

    monkeypatch.setattr(check_updates, "_user_agent_hint_done", False)
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", _write_cfg(tmp_path, 'user_agent = "flat"\n'))
    assert check_updates.user_agent() == check_updates.DEFAULT_USER_AGENT, "节非表 → 回落"
    assert "[DEPS-CONFIG]" in capsys.readouterr().err


def test_user_agent_broken_toml_fails_fast(tmp_path: Path, monkeypatch) -> None:
    """坏 TOML → 解析异常上抛 (坏配置不是「缺失」, 静默回落会让守卫假绿, D13 同源)。"""
    bad = tmp_path / "project.toml"
    bad.write_text("[user_agent]\nvalue = [unterminated\n", encoding="utf-8")
    monkeypatch.setattr(check_updates, "USER_AGENT_CONFIG_PATH", bad)
    with pytest.raises(tomllib.TOMLDecodeError):
        check_updates.user_agent()

"""test_version_guard 测试计划: 版本号单源守阵 (计划 26-09-22-2318 v2 §05, issue 26-09-21-1408)。

守什么: `auto_qb.__version__` 是版本号唯一权威出处 (pyproject dynamic + hatchling regex
接线后), 必须恒为纯 SemVer 三段数字 —— hash 尾等 local 段只允许出现在显示层拼接
(计划 v2 §4.2 双路径), 不允许进入存储版本 (否则 uv.lock 漂移、tag 判定口径破坏);
pyproject 侧不得回潮静态 version 键 (双写即漂移, 已实证 0.1.0 vs 0.2.0)。

## 测试计划

- test_dunder_version_matches_semver: __version__ 匹配 ^\\d+\\.\\d+\\.\\d+$ (存储段严格, 不放宽 local)
- test_pyproject_declares_dynamic_version: pyproject 声明 dynamic 含 version 且无静态 version 键 (防双写回潮)
- test_hatch_version_wiring_points_at_init: [tool.hatch.version] regex 指向 src/auto_qb/__init__.py (单源接线在位)
- test_importlib_metadata_agrees_with_dunder: 打包元数据与 __version__ 一致 (双源结构性消失的端到端断言)
- test_cli_version_flag_prints_version: cli --version 退出码 0 且透出与 __version__ 同源的号
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

import auto_qb

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _load_pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def test_dunder_version_matches_semver() -> None:
    # 存储段恒纯 SemVer: local/build 段(+hash)只许在显示层拼接, 不许进 __version__。
    assert re.fullmatch(
        r"\d+\.\d+\.\d+", auto_qb.__version__
    ), (f"__version__ 必须是纯 SemVer 三段数字, 当前 {auto_qb.__version__!r} "
        "(hash 尾走显示层拼接, 见计划 26-09-22-2318 v2 §4.2)")


def test_pyproject_declares_dynamic_version() -> None:
    # 单源纪律的 pyproject 侧: dynamic 声明在位 + 静态 version 键不得回潮。
    project = _load_pyproject()["project"]
    assert "version" in project.get("dynamic", []), "pyproject 缺 dynamic=[\"version\"] 声明"
    assert "version" not in project, "pyproject 静态 version 键回潮 —— 双写已实证漂移(0.1.0 vs 0.2.0)"


def test_hatch_version_wiring_points_at_init() -> None:
    # 单源接线在位: hatchling regex 源指向 __init__.py 的 __version__ 行。
    wiring = _load_pyproject()["tool"]["hatch"]["version"]
    assert wiring["source"] == "regex"
    assert wiring["path"] == "src/auto_qb/__init__.py"


def test_importlib_metadata_agrees_with_dunder() -> None:
    # 端到端: 打包元数据(构建期从单源提取)与运行时 __version__ 一致 —— 双源结构性消失。
    import importlib.metadata

    assert importlib.metadata.version("auto-qb"
                                     ) == auto_qb.__version__, ("打包元数据与 __version__ 不一致 —— uv sync 后元数据未刷新或单源接线被破坏")


def test_cli_version_flag_prints_version(capsys, monkeypatch) -> None:
    # --version 旗标在位且与 __version__ 同源(argparse version 动作打印后 SystemExit(0))。
    from auto_qb import cli

    monkeypatch.setattr(sys, "argv", ["auto-qb", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert auto_qb.__version__ in out
    assert out.startswith("auto-qb ")

"""S0 冒烟: 包可安装可起、模块可导入、版本与 pyproject 一致, CLI 入口形态.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S0)。
S1-S9 的各模块守阵 (采样/落盘/恢复/通知/租约/installer 幂等等) 逐步补进本目录:
test_sampler.py (S1) / test_storage.py (S2) 已落地, 无子命令时 CLI 打印帮助。
"""

import tomllib
from pathlib import Path

import pytest

import gtm

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_version_consistency_with_pyproject():
    """__init__.__version__ 与 pyproject [project].version 必须一致."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert gtm.__version__ == pyproject["project"]["version"]


def test_all_modules_importable():
    """S0 骨架的六个模块 + 入口均可导入 (无副作用、无第三方依赖引入)."""
    import gtm.__main__  # noqa: F401
    import gtm.config  # noqa: F401
    import gtm.installer  # noqa: F401
    import gtm.notifier  # noqa: F401
    import gtm.sampler  # noqa: F401
    import gtm.server  # noqa: F401
    import gtm.storage  # noqa: F401


def test_cli_version_flag(capsys):
    """gtm --version 打印版本并以 0 退出 (argparse version action)."""
    with pytest.raises(SystemExit) as excinfo:
        gtm.__main__.main(["--version"])
    assert excinfo.value.code == 0
    assert f"gtm {gtm.__version__}" in capsys.readouterr().out


def test_cli_no_subcommand_prints_help(capsys):
    """无子命令时打印帮助 (含 run) 并返回 0 (S2 起 run 子命令可用)."""
    assert gtm.__main__.main([]) == 0
    out = capsys.readouterr().out
    assert "usage: gtm" in out and "run" in out

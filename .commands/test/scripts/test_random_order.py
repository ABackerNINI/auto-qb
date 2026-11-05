"""test.random-order 脚本的纯函数单测(与脚本同目录, 由 test.pkg 收集)。

## 测试计划

- test_plan_defaults: 1. 缺省 = 1 轮 / 随机 seed / 无透传
- test_plan_samples_and_seed: 1. --samples/--seed 解析与边界(0 轮拒收)
- test_plan_passthrough: 1. `--` 后参数透传给 pytest; `--` 前未知参数报 ValueError
- test_build_cmd_shape: 1. 命令形态 —— -o addopts= 替换值含并行度, seed 以 --randomly-seed 落位
"""
from __future__ import annotations

import subprocess

import pytest

from random_order import ADDOPTS_OVERRIDE, build_cmd, plan, reproduction_cmd


def test_plan_defaults():
    assert plan([]) == (1, None, [])


def test_plan_samples_and_seed():
    assert plan(["--samples", "3"]) == (3, None, [])
    assert plan(["--seed", "42"]) == (1, 42, [])
    assert plan(["--samples", "2", "--seed", "7"]) == (2, 7, [])
    with pytest.raises(ValueError, match="--samples 必须 >= 1"):
        plan(["--samples", "0"])
    with pytest.raises(ValueError, match="缺值"):
        plan(["--seed"])


def test_plan_passthrough():
    assert plan(["--", "-k", "hr"]) == (1, None, ["-k", "hr"])
    assert plan(["--samples", "2", "--", "-x"]) == (2, None, ["-x"])
    with pytest.raises(ValueError, match="未知参数"):
        plan(["--nope"])


def test_build_cmd_shape():
    cmd = build_cmd(123, ["-k", "hr"])
    assert cmd[:3] == ["uv", "run", "pytest"]
    assert "-o" in cmd and f"addopts={ADDOPTS_OVERRIDE}" in cmd  # 随机序开关 = 替换 ini addopts
    assert "--randomly-seed=123" in cmd
    assert cmd[-2:] == ["-k", "hr"]
    assert "-p" not in cmd  # 不再禁用 randomly(禁用在被替换掉的 pytest.ini addopts 里)
    # 复现命令是可直接粘进 shell 的形态(list2cmdline): 含空格的 addopts 值必须带引号
    assert reproduction_cmd(123, []) == subprocess.list2cmdline(build_cmd(123, []))
    assert '"addopts=-n 8"' in reproduction_cmd(123, [])

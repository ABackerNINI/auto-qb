"""`traffic_source_agent_support` 支撑: 从 `test_traffic_source_agent.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import ast

import builtins

import json

import logging

import os

import re

import shutil

import subprocess

from pathlib import Path

from types import SimpleNamespace

import pytest

from auto_qb.core.traffic_source import agent

from auto_qb.infra.utils import is_windows

from auto_qb.webui import tool_client

from helpers import capture_logs, write_credential_file, write_endpoint_pointer

#: 本平台对应的 D19 启动器文件名(与工具目录里的文件同名同源)
_LAUNCHER = agent._LAUNCHER_WINDOWS if is_windows() else agent._LAUNCHER_POSIX


def _conf(*, tool_dir="", tool_exe=""):
    """拉起源参数段替身: resolve_launch_target / ensure_running 只鸭子类型读 tool_dir / tool_exe"""
    return SimpleNamespace(tool_dir=tool_dir, tool_exe=tool_exe)


@pytest.fixture()
def probe_env(tmp_path, monkeypatch):
    """探活环境: 真指针 + 真密钥文件 + 可换的假控制面 -> (monkeypatch 出的调用记录, 切换函数)"""
    token_path = write_credential_file(tmp_path)
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=token_path)
    calls = []

    def set_tool(result=None, exc=None):
        """把 call_tool 换成给定返回 / 抛错的替身(默认 200)"""
        def fake(base_url, path, method, credential, payload=None, timeout=None):
            calls.append((path, method, credential, timeout))
            if exc is not None:
                raise exc
            return result if result is not None else (200, {"ok": True})

        monkeypatch.setattr(tool_client, "call_tool", fake)

    return calls, set_tool


def _down(*_a, **_k):
    """探活替身: 工具不可达(缺席)"""
    raise tool_client.ToolUnreachable("down")


_REPO_ROOT = Path(__file__).resolve().parents[1]

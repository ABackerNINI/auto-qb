"""test_traffic_source_agent_state 测试计划: 全局流量监视器联动单点(探测 / 缺席拉起 / 状态, 计划 26-10-17-0339 S16)

## 测试计划(每个测试函数一条)
- test_status_reports_states: ready / not_running 两态与端点字段读数(launching / launch_failed /
  not_installed 由拉起用例覆盖)
- test_read_deferred_note_states (D7): 注记只读; 损坏/schema 未知 -> None(不猜字段)

P1-T1.3 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_read_deferred_note_non_dict_payload: 注记顶层非对象 -> None(只告警, 不猜字段)
- test_note_error_throttles_same_reason: 同因首次 WARNING、其后 DEBUG, 换因重新 WARNING

W7(R31) S5 补测(变异审计真洞守阵, 2026-11-01; 分类与位点见 tmp-analysis/w7-r31/classify.md) ——
平台支一律**强制进支**钉面(is_windows 打桩)—— WSL 池里 is_windows() 恒 False, Windows 支
变异靠强制进支让守阵在任何环境咬合(平台内断言), 不依赖 WSL 端到端:
- test_status_ready_and_not_running_fields: 状态区字段读数(status_19/21/26/36)
"""

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

from traffic_source_agent_support import (
    _LAUNCHER,
    _conf,
    _down,
    probe_env,
)


def test_status_reports_states(tmp_path, monkeypatch, probe_env):
    """ready / not_running 两态与端点字段读数"""
    _calls, set_tool = probe_env
    (tmp_path / _LAUNCHER).write_text("", encoding="utf-8")
    conf = _conf(tool_dir=str(tmp_path))
    a = agent.TrafficSourceAgent()

    # 探活失败 + 目标可解析 + 无拉起/退避记忆 -> not_running
    monkeypatch.setattr(tool_client, "call_tool", _down)
    st = a.status(conf)
    assert st["state"] == "not_running"
    assert st["endpoint"] is None
    assert st["pid"] == 0 and st["version"] == ""

    # 探活成功 -> ready, 端点字段回填
    set_tool(result=(200, {"ok": True}))
    st = a.status(conf)
    assert st["state"] == "ready"
    assert st["endpoint"] is not None
    assert st["pid"] == 4321 and st["version"] == "0.1.0"
    assert st["autostart_registered"] is True
    assert st["autostart_error"] is None  # 没失败 -> None(issue 26-10-17-1455)


def test_read_deferred_note_states(tmp_path, monkeypatch):
    """缺失 -> None; 合法 -> 载荷; 损坏 / schema 未知 -> None(不猜字段, 指针同族纪律)"""
    note_path = tmp_path / "ptr" / "deferred.json"
    monkeypatch.setattr(agent, "deferred_note_path", lambda: str(note_path))
    assert agent.read_deferred_note() is None  # 缺失
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        json.dumps({
            "schema": agent.DEFERRED_SCHEMA,
            "reason": "relayed",
            "detail": "已让位"
        }), encoding="utf-8"
    )
    note = agent.read_deferred_note()
    assert note["reason"] == "relayed" and note["detail"] == "已让位"
    note_path.write_text("{ not json", encoding="utf-8")
    assert agent.read_deferred_note() is None  # 损坏按无注记
    note_path.write_text(json.dumps({"schema": 999, "reason": "relayed"}), encoding="utf-8")
    assert agent.read_deferred_note() is None  # schema 未知不猜字段


def test_read_deferred_note_non_dict_payload(tmp_path, monkeypatch):
    """注记顶层非对象(如数组)-> None: 只告警不猜字段, 与指针 schema 守卫同族纪律"""
    note_path = tmp_path / "ptr" / "deferred.json"
    monkeypatch.setattr(agent, "deferred_note_path", lambda: str(note_path))
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(json.dumps([agent.DEFERRED_SCHEMA]), encoding="utf-8")
    assert agent.read_deferred_note() is None


def test_note_error_throttles_same_reason():
    """失败日志节流(同一原因只说明白一次): 首条 WARNING, 同因降 DEBUG; 换原因重新 WARNING
    —— 工具没起是常态, 逐轮 WARNING 会刷屏"""
    lg = logging.getLogger("auto_qb.core.traffic_source.agent")
    records = []

    class _Rec(logging.Handler):
        def emit(self, record):
            records.append((record.levelno, record.getMessage()))

    handler = _Rec()
    handler.setLevel(logging.DEBUG)
    old_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    try:
        a = agent.TrafficSourceAgent()
        a._note_error("拉起失败: 拒绝访问")
        a._note_error("拉起失败: 拒绝访问")
        assert [lv for lv, _ in records] == [logging.WARNING, logging.DEBUG]
        a._note_error("未安装: 工具目录解析不到")
        assert records[-1][0] == logging.WARNING and "未安装" in records[-1][1]
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


def test_status_ready_and_not_running_fields(tmp_path, monkeypatch):
    """ready 态端点字段读数(status_19: data_dir 不得恒空)与 retry_s 基线(status_36)"""
    write_endpoint_pointer(tmp_path, monkeypatch, token_path=write_credential_file(tmp_path))
    monkeypatch.setattr(tool_client, "call_tool", lambda *a, **k: (200, {"ok": True}))
    st = agent.TrafficSourceAgent().status(_conf())
    assert st["state"] == "ready"
    assert st["data_dir"] == str(tmp_path / "gtm")
    assert st["retry_s"] == 0.0

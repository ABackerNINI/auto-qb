"""`rule_compat_support` 支撑: 从 `test_rule_compat.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import os

import tempfile

import pytest

import yaml

from auto_qb.config import ConfigError, load_config

from auto_qb.config.compat import (
    CONDITION_TREE_MAX_DEPTH,
    CONDITION_GROUPING_MAP,
    normalize_action_entry,
    normalize_conditions,
    normalize_legacy_rule,
    normalize_legacy_rules,
)

from auto_qb.config.validation import _strip_none

from auto_qb.core.modules import rules_mod

from auto_qb.core.state import StateService

from auto_qb.rules import registry

from auto_qb.rules.actions import AddTagsAction

from auto_qb.rules.base import VERDICT_ERROR, VERDICT_EXECUTED, VERDICT_NO_OP, VERDICT_RETRY, Rule

from helpers import FakeClient, FakeTorrent, make_ctx, make_manager


def _checking_params(with_mode: str) -> dict:
    """checking 动作参数(生产 4 条校验规则共用形状; BaseLoader 标量全为字符串)"""
    return {
        "basic_check": "filelist",
        "with_reference": {
            "enabled": "true",
            "mode": with_mode,
            "auto_start": "false"
        },
        "without_reference": {
            "enabled": "true",
            "mode": "full-checking",
            "auto_start": "false"
        },
    }


def _default_on_error() -> dict:
    """缺省 on_error(W2-B normalize 注入值; schema.fields.ON_ERROR_DEFAULTS 单点的快照副本)"""
    return {"policy": "stop", "retries": 3, "backoff": 60}


class _Fixed:
    """固定返回值的哑条件(求值/短路测试用): calls 记录被求值次数"""
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def match(self, ctx):
        self.calls += 1
        return self.value


class _Boom:
    """求值即抛的哑条件: 用于断言短路后不被触达 / 异常上抛路径"""
    def __init__(self):
        self.calls = 0

    def match(self, ctx):
        self.calls += 1
        raise RuntimeError("boom")


def _load_config_from_text(text: str):
    """文本 -> 临时文件 -> load_config(真实载入链: _strip_none -> normalize -> validate)"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "c.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_config(path)


def _load_errors(text: str) -> str:
    """载入失败聚合错误全文(成功返回空串)"""
    try:
        _load_config_from_text(text)
        return ""
    except ConfigError as e:
        return str(e)

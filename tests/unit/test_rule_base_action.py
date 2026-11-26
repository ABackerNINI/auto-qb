"""test_rule_base_action 测试计划: rules/base ActionResult/RuleContext/Rule

## 测试计划(每个测试函数一条)
- test_action_result_states: ActionResult 状态语义
"""

import os

import tempfile

from auto_qb.config import TrackerConfig

from auto_qb.core.modules import rules_mod

from auto_qb.rules.base import (
    VERDICT_DEDUPED,
    VERDICT_ERROR,
    VERDICT_EXECUTED,
    VERDICT_NO_MATCH,
    VERDICT_NO_OP,
    VERDICT_PENDING,
    ActionResult,
    BaseAction,
    Rule,
    RuleContext,
)

from auto_qb.rules.conditions import SizeCondition

from auto_qb.rules.actions import AddTagsAction

from auto_qb.infra import utils

from helpers import FakeClient, FakeTorrent, _hr_rule, make_ctx, make_manager


def test_action_result_states():
    """ActionResult 三态与判定属性"""
    ok = ActionResult.ok("成功")
    fail = ActionResult.fail("失败")
    skip = ActionResult.skip("跳过")
    assert ok.is_ok and not ok.is_failed and not ok.is_skipped
    assert fail.is_failed and fail.message == "失败"
    assert skip.is_skipped
    assert "success" in repr(ok)

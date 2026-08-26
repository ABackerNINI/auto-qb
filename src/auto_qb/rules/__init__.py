"""
rules 框架: 条件/动作插件(规则由 QbManager 统一加载与调度, 见 qbmanager.py)
"""
from . import conditions  # noqa: F401  注册内置条件插件
from . import actions  # noqa: F401  注册内置动作插件
from .base import Rule, RuleContext, ActionResult

__all__ = ["Rule", "RuleContext", "ActionResult"]

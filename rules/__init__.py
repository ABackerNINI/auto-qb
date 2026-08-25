"""
rules 框架: 条件/动作插件 + RuleManager 统一管理
"""
from . import conditions  # noqa: F401  注册内置条件插件
from . import actions     # noqa: F401  注册内置动作插件
from .base import Rule, RuleContext, ActionResult
from .manager import RuleManager

__all__ = ["RuleManager", "Rule", "RuleContext", "ActionResult"]

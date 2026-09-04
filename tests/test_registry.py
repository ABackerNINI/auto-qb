"""test_registry 测试计划: rules/registry 注册表与工厂

## 测试计划(每个测试函数一条)
- test_create_condition_known: 已知条件工厂创建
- test_create_condition_unknown: 未知条件直接按名索引抛 KeyError(名称合法性由 config.validate_config 保证)
- test_create_action_known: 已知动作工厂创建
- test_create_action_unknown: 未知动作直接按名索引抛 KeyError
- test_register_condition_decorator: 条件注册装饰器
- test_register_action_decorator: 动作注册装饰器
"""
import pytest

from auto_qb.rules.registry import (
    ACTIONS,
    CONDITIONS,
    create_action,
    create_condition,
    register_action,
    register_condition,
)


def test_create_condition_known():
    """已知条件类型可创建"""
    c = create_condition({"size": ">=1MiB"})
    assert c.name == "size"


def test_create_condition_unknown():
    """未知条件直接索引注册表抛 KeyError(fail-fast 校验已保证名称合法, 工厂不再检查)"""
    with pytest.raises(KeyError):
        create_condition({"nope": 1})


def test_create_action_known():
    """已知动作类型可创建"""
    a = create_action("add_tags", ["X"], ignore_error=False)
    assert a.name == "add_tags"


def test_create_action_unknown():
    """未知动作直接索引注册表抛 KeyError"""
    with pytest.raises(KeyError):
        create_action("nope", None, ignore_error=False)


def test_register_condition_decorator():
    """register_condition 装饰器注册新条件"""
    assert "size" in CONDITIONS
    n = len(CONDITIONS)

    @register_condition
    class AlwaysTrue:
        name = "always_true"

        def __init__(self, spec):
            self.spec = spec

        def match(self, ctx):
            return True

    assert "always_true" in CONDITIONS
    assert len(CONDITIONS) == n + 1
    assert create_condition({"always_true": None}).match(None)


def test_register_action_decorator():
    """register_action 装饰器注册新动作"""
    assert "start" in ACTIONS
    n = len(ACTIONS)

    @register_action
    class Noop:
        name = "noop"

        def __init__(self, spec, ignore_error=False):
            pass

        def execute(self, ctx):
            from auto_qb.rules.base import ActionResult
            return ActionResult.ok("noop")

    assert "noop" in ACTIONS
    assert len(ACTIONS) == n + 1
    assert create_action("noop", None, ignore_error=False).execute(None).is_ok

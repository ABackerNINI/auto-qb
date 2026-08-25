"""条件/动作插件注册表: 通过装饰器注册, 按名称创建实例"""

CONDITIONS: dict = {}
ACTIONS: dict = {}


def register_condition(cls):
    """装饰器: 注册条件插件, 类需有 name 属性和 match(ctx) 方法"""
    CONDITIONS[cls.name] = cls
    return cls


def register_action(cls):
    """装饰器: 注册动作插件, 类需有 name 属性和 execute(ctx) 方法"""
    ACTIONS[cls.name] = cls
    return cls


def create_condition(spec: dict):
    """根据条件配置(单键dict)创建条件实例, 如 {'size': '>=100MiB'}"""
    name, value = next(iter(spec.items()))
    cls = CONDITIONS.get(name)
    if cls is None:
        raise ValueError(f"未知条件: {name}, 可用: {sorted(CONDITIONS)}")
    return cls(value)


def create_action(name: str, value, ignore_error: bool = False):
    """根据动作名与配置创建动作实例"""
    cls = ACTIONS.get(name)
    if cls is None:
        raise ValueError(f"未知动作: {name}, 可用: {sorted(ACTIONS)}")
    return cls(value, ignore_error)

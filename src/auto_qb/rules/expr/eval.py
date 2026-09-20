"""表达式求值: AST + RuleContext -> 值

三条硬约束(见计划第 05/07 节):
- **纯读取**: 求值不修改任何状态, 保证幂等(黄金法则 1)
- **短路**: and/or 必须短路 —— 否则 `a and freespace("R:/") < 100GiB` 会给每个种子都来一次磁盘调用
- **出错即抛 ExprError**: 由 Rule.process 的条件分支兜成「不匹配 + 停后续规则」;
  ⚠ 绝不静默返回 False/0 —— 那会让「低于阈值」这类条件在数据源失效时静默成真

昂贵取值(有 I/O / API / 全库遍历 / 时变)按 **ctx 缓存**: 键为名字或函数名+参数,
生命周期 = 一次规则执行(RuleContext.expr_cache), 同规则同轮只算一次。
"""
from typing import Any

from ... import utils
from . import env
from .errors import ExprError
from .parser import Binary, Call, ListLit, Lit, Name, Unary
from .types import is_number, label, type_name

_LOGIC = ("and", "or")
_ARITH = ("+", "-", "*", "/", "%")
_ORDER = (">", "<", ">=", "<=")
_EQ = ("==", "!=")


def evaluate(node, ctx) -> Any:
    """求值 AST 节点; 运行期类型错误 / 数据源不可用 -> ExprError"""
    if isinstance(node, Lit):
        return node.value
    if isinstance(node, Name):
        return _name_value(node, ctx)
    if isinstance(node, Call):
        return _call_value(node, ctx)
    if isinstance(node, ListLit):
        return tuple(evaluate(item, ctx) for item in node.items)
    if isinstance(node, Unary):
        return _unary(node, ctx)
    if isinstance(node, Binary):
        return _binary(node, ctx)
    raise ExprError(f"无法求值的节点: {node!r}")


def trace(node, ctx) -> list:
    """求值路径上的中间值(供 WEB 试算面板显示, 让人看清每个名字到底取到了什么)

    返回 [{"kind": "name"/"call", "name": str, "value": Any}], 顺序即求值顺序。
    值经 _jsonable 处理(JSON 安全: 集合转列表、inf 转字符串)。
    """
    items: list = []

    def walk(n):
        if isinstance(n, Name):
            items.append({"kind": "name", "name": n.name, "value": _jsonable(evaluate(n, ctx))})
        elif isinstance(n, Call):
            items.append({"kind": "call", "name": n.name, "value": _jsonable(evaluate(n, ctx))})
            for arg in n.args:
                walk(arg)
        elif isinstance(n, Unary):
            walk(n.operand)
        elif isinstance(n, Binary):
            walk(n.left)
            walk(n.right)
        elif isinstance(n, ListLit):
            for item in n.items:
                walk(item)

    walk(node)
    return items


def _jsonable(value):
    """转 JSON 安全值: 集合/元组转列表, inf/nan 转字符串(避免 JSON 序列化报错)"""
    if isinstance(value, (frozenset, set, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, float) and (value == float("inf") or value != value):
        return str(value)
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    return str(value)


def _cache(ctx) -> dict:
    cache = getattr(ctx, "expr_cache", None)
    if cache is None:
        cache = {}
        ctx.expr_cache = cache
    return cache


def _name_value(node: Name, ctx):
    info = env.NAME_TABLE.get(node.name)
    if info is None:  # 静态校验已挡在配置期, 这里是运行期兜底
        raise ExprError(f"未知取值 '{node.name}'")
    if not info.expensive:
        return info.getter(ctx)
    cache = _cache(ctx)
    key = ("name", node.name)
    if key not in cache:
        cache[key] = info.getter(ctx)
    return cache[key]


def _call_value(node: Call, ctx):
    info = env.FUNC_TABLE.get(node.name)
    if info is None:
        raise ExprError(f"未知函数 '{node.name}'")
    args = tuple(evaluate(a, ctx) for a in node.args)
    if not info.expensive:
        return info.call(ctx, args)
    cache = _cache(ctx)
    key = ("call", node.name, args)
    if key not in cache:
        cache[key] = info.call(ctx, args)
    return cache[key]


def _as_bool(value, op: str) -> bool:
    if not isinstance(value, bool):
        raise ExprError(f"'{op}' 的操作数必须是布尔, 得到 {label(type_name(value))}")
    return value


def _as_num(value, op: str):
    if not is_number(value):
        raise ExprError(f"'{op}' 的操作数必须是数值, 得到 {label(type_name(value))}")
    return value


def _unary(node: Unary, ctx):
    value = evaluate(node.operand, ctx)
    if node.op == "not":
        return not _as_bool(value, "not")
    return -value if node.op == "-" else value


def _binary(node: Binary, ctx):
    op = node.op
    # 短路: 右侧不必求值(昂贵取值靠这条避免无谓调用)
    if op == "and":
        return _as_bool(evaluate(node.left, ctx), op) and _as_bool(evaluate(node.right, ctx), op)
    if op == "or":
        return _as_bool(evaluate(node.left, ctx), op) or _as_bool(evaluate(node.right, ctx), op)

    left = evaluate(node.left, ctx)
    right = evaluate(node.right, ctx)

    if op in _ARITH:
        _as_num(left, op)
        _as_num(right, op)
        if op in ("/", "%") and right == 0:
            raise ExprError(f"'{op}' 的除数为 0")
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        return left % right

    if op in _ORDER:
        if is_number(left) and is_number(right):
            pass
        elif isinstance(left, str) and isinstance(right, str):
            pass
        else:
            raise ExprError(f"'{op}' 两侧必须同为数值或同为字符串, 得到 {label(type_name(left))} 与 "
                            f"{label(type_name(right))}")
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        return left <= right

    if op in _EQ:
        if type_name(left) != type_name(right):
            raise ExprError(f"'{op}' 两侧类型不一致: {label(type_name(left))} 与 {label(type_name(right))}")
        return left == right if op == "==" else left != right

    if op == "in":
        try:
            return left in right
        except TypeError as e:
            raise ExprError(f"'in' 右侧不是可容纳取值的容器: {label(type_name(right))}") from e

    if op == "~":
        # 模式匹配: 复用 utils.MatchPattern 语法(regex: 前缀 / :ignore_case 后缀)
        # 左侧为集合(tor.tags)时语义 = 任一元素命中
        pattern = str(right)
        targets = left if isinstance(left, (list, tuple, frozenset, set)) else [left]
        return any(utils.match_value(str(t), [pattern]) for t in targets)

    raise ExprError(f"未知运算符 '{op}'")

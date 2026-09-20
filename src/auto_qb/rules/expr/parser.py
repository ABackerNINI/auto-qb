"""表达式语法分析: Token 列表 -> AST(编译期完成语法层静态检查)

核心约束(见计划第 03 节): **一层一个运算符** —— 同一括号层最多出现一个运算符
(含 not、一元负号, 同种连续也算第二个)。于是**不需要优先级表**: 同层永远只有一个
运算符, "谁先算"的歧义在语法层面被消除, 括号是唯一的分层手段。

本模块只做**语法层**检查: 一层一运算符、标识符前缀形态、字面量单位与字面量之间的
类型冲突。名字是否存在 / 类型是否匹配 / 数据源可用性归 W2 的 env.py(需要语义信息)。
"""
from dataclasses import dataclass
from typing import Any, Tuple

from .errors import ExprSyntaxError
from .lexer import Token, tokenize
from .types import check_op_types, check_unary_types, is_number, type_name

# 中缀运算符("=" 归一化为 "=="; 一元 not/-/+ 不在其中)
_BINOPS = (">=", "<=", "==", "!=", "=", ">", "<", "and", "or", "in", "~", "+", "-", "*", "/", "%")
_UNARY_OPS = ("not", "-", "+")
_ARITH_OPS = ("+", "-", "*", "/", "%")
_ORDER_OPS = (">", "<", ">=", "<=")
_EQ_OPS = ("==", "!=")
_LOGIC_OPS = ("and", "or")
_LITERAL_KINDS = ("num", "size", "time", "speed", "hhmm", "str", "bool")

# ---------- AST 节点 ----------


@dataclass(frozen=True, slots=True)
class Lit:
    """字面量: 值已在词法阶段解析好(带单位的大小/时长/速度/时刻均为数值)"""

    value: Any


@dataclass(frozen=True, slots=True)
class Name:
    """取值名: 一律带作用域前缀(tor.* / tracker.* / sys.*)"""

    name: str
    pos: int = 0


@dataclass(frozen=True, slots=True)
class Call:
    """函数调用: 函数名不带前缀, 参数显式传入"""

    name: str
    args: Tuple[Any, ...]
    pos: int = 0


@dataclass(frozen=True, slots=True)
class ListLit:
    """列表字面量 [a, b]: 供 in 使用(如 state in ["uploading", "forcedUP"])"""

    items: Tuple[Any, ...]
    pos: int = 0


@dataclass(frozen=True, slots=True)
class Unary:
    """一元运算: not / -(负) / +(正)"""

    op: str
    operand: Any


@dataclass(frozen=True, slots=True)
class Binary:
    """二元运算: 比较 / 逻辑 / 算术 / in / ~"""

    op: str
    left: Any
    right: Any


@dataclass(frozen=True, slots=True)
class Expr:
    """编译产物: 原文 + AST 根节点"""

    text: str
    root: Any


def compile_expr(text) -> Expr:
    """编译表达式 -> Expr; 词法/语法/静态检查失败抛 ExprSyntaxError(配置期 fail-fast)"""
    return _Parser(tokenize(text), str(text)).parse()


class _Parser:
    """递归下降解析: 每个括号层一个 _level 调用, 层内运算符计数即"一层一个"判定"""
    def __init__(self, tokens, text: str):
        self._tokens = tokens
        self._text = text
        self._i = 0

    # ---------- token 流 ----------

    def _peek(self) -> Token:
        return self._tokens[self._i]

    def _next(self) -> Token:
        t = self._tokens[self._i]
        self._i += 1
        return t

    # ---------- 语法 ----------

    def parse(self) -> Expr:
        root, used = self._level_ex()
        t = self._peek()
        if t.kind != "eof":
            # 多余的运算符按"一层一个运算符"报(比笼统的"多余内容"更能照着改)
            if t.kind == "op":
                self._reject_second(used, t)
            raise ExprSyntaxError(f"表达式结尾有多余内容 '{t.text}'", t.pos)
        _check_literals(root)
        return Expr(self._text, root)

    def _level(self):
        """一个括号层: 最多一个运算符"""
        node, _ = self._level_ex()
        return node

    def _level_ex(self):
        """一个括号层, 额外返回该层已用掉的运算符(供上层拼改写提示)"""
        used = None  # 该层已用掉的运算符文本

        t = self._peek()
        if t.kind == "op" and t.value in _UNARY_OPS:
            self._next()
            operand = self._primary()
            if t.value == "not":
                used = t.value
                node = Unary("not", operand)
            elif isinstance(operand, Lit) and is_number(operand.value):
                # 一元 +/- 作用于数字字面量: 折叠为字面量(如 -5), 不算运算符
                node = Lit(-operand.value if t.value == "-" else operand.value)
            else:
                used = t.value
                node = Unary(t.value, operand)
        else:
            node = self._primary()

        t = self._peek()
        if t.kind == "op":
            if t.value not in _BINOPS:
                raise ExprSyntaxError(f"运算符 '{t.value}' 不能出现在中缀位置", t.pos)
            self._reject_second(used, t)
            self._next()
            used = t.value
            nxt = self._peek()
            if nxt.kind == "op":
                # 右操作数再带一元 = 该层第二个运算符
                self._reject_second(t.value, nxt)
            node = Binary("==" if t.value == "=" else t.value, node, self._primary())
        return node, used

    def _primary(self):
        t = self._peek()
        if t.kind == "(":
            self._next()
            node = self._level()
            if self._peek().kind != ")":
                raise ExprSyntaxError("括号未闭合", t.pos)
            self._next()
            return node
        if t.kind == "[":
            return self._list_literal()
        if t.kind == "name":
            return self._name_or_call()
        if t.kind in _LITERAL_KINDS:
            self._next()
            return Lit(t.value)
        if t.kind == "op":
            raise ExprSyntaxError(f"缺少操作数: 运算符 '{t.value}' 位置不对", t.pos)
        label = t.text or "表达式结尾"
        raise ExprSyntaxError(f"意外的 '{label}'", t.pos)

    def _name_or_call(self):
        t = self._next()
        if self._peek().kind != "(":
            if "." not in t.value:
                raise ExprSyntaxError(f"标识符必须带作用域前缀(tor.* / tracker.* / sys.*): '{t.value}'", t.pos)
            return Name(t.value, t.pos)

        self._next()  # 吃掉 '('
        args = []
        if self._peek().kind != ")":
            while True:
                args.append(self._level())
                if self._peek().kind == ",":
                    self._next()
                    continue
                break
        if self._peek().kind != ")":
            raise ExprSyntaxError(f"函数 '{t.value}' 的参数括号未闭合", t.pos)
        self._next()
        if "." in t.value:
            raise ExprSyntaxError(f"函数名不带作用域前缀: '{t.value}'", t.pos)
        return Call(t.value, tuple(args), t.pos)

    def _list_literal(self):
        t = self._next()  # '['
        items = []
        if self._peek().kind != "]":
            while True:
                items.append(self._level())
                if self._peek().kind == ",":
                    self._next()
                    continue
                break
        if self._peek().kind != "]":
            raise ExprSyntaxError("列表字面量未闭合(缺少 ']')", t.pos)
        self._next()
        return ListLit(tuple(items), t.pos)

    # ---------- 报错 ----------

    def _reject_second(self, used, t: Token) -> None:
        """一层一个运算符: 出现第二个即报错, 并给出加括号的改写提示"""
        if used is None:
            return
        raise ExprSyntaxError(f"同一括号内只能有一个运算符(已有 '{used}', 又出现 '{t.value}') —— "
                              f"请用括号分组, 如 (左) {t.value} (右)", t.pos)


# ---------- 字面量类型静态检查 ----------


def _check_literals(node) -> None:
    """字面量之间的类型冲突(两侧都能在编译期定值时才查; 含名字的一侧归 env)

    只查字面量, 是为了在**不依赖取值面**的前提下尽早发现明显的笔误
    (如 '10GiB' > "abc"); 名字一侧的类型由 env.validate 提供静态类型后检查。
    类型规则与 env 共用 types.py, 两边不一致会出现"写字面量报错、写名字不报错"的割裂。
    """
    if isinstance(node, Binary):
        _check_literals(node.left)
        _check_literals(node.right)
        if isinstance(node.left, Lit) and isinstance(node.right, Lit):
            check_op_types(node.op, type_name(node.left.value), type_name(node.right.value))
        return
    if isinstance(node, Unary):
        _check_literals(node.operand)
        if isinstance(node.operand, Lit):
            check_unary_types(node.op, type_name(node.operand.value))
        return
    if isinstance(node, Call):
        for arg in node.args:
            _check_literals(arg)
        return
    if isinstance(node, ListLit):
        for item in node.items:
            _check_literals(item)

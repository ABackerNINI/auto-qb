"""表达式类型: 静态类型标记 + 运算符类型规则(编译期校验的单一事实源)

被 parser.py(字面量之间的检查)与 env.py(名字/函数的静态类型检查)**共用** —— 两边规则必须一致,
否则会出现"写字面量报错、写名字不报错"的割裂, 用户会觉得校验时灵时不灵。

另提供运行期数值断言 `require_number`(is_number 单点的唯一消费者): 求值侧的「操作数/参数
必须是数值」校验(env 的数值函数 + eval 的算术运算符)统一走它, 判据与报错文案只有一处实现。
"""
from .errors import ExprError, ExprSyntaxError

NUM = "num"
BOOL = "bool"
STR = "str"
LIST = "list"  # 字符串集合(tags / tracker.groups / 列表字面量)
ANY = "any"  # 无法静态确定的类型(如 raw()), 参与运算时不检查

_ARITH_OPS = ("+", "-", "*", "/", "%")
_ORDER_OPS = (">", "<", ">=", "<=")
_EQ_OPS = ("==", "!=")
_LOGIC_OPS = ("and", "or")

# 静态类型 -> 中文名(报错文案用)
_TYPE_LABEL = {NUM: "数值", BOOL: "布尔", STR: "字符串", LIST: "列表", ANY: "任意"}


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def type_name(value) -> str:
    """运行期值 -> 静态类型标记"""
    if is_number(value):
        return NUM
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, str):
        return STR
    if isinstance(value, (list, tuple, frozenset, set)):
        return LIST
    return ANY


def label(kind: str) -> str:
    return _TYPE_LABEL.get(kind, kind)


def require_number(value, what: str):
    """运行期断言 value 是数值(非布尔), 否则抛 ExprError

    what = 报错主体短语(如 "该函数的参数" / "'abs' 的操作数"), 由调用方按语境传入 ——
    判据与文案骨架单点在此, 具体指代仍贴各自场景。判据复用 is_number, 与编译期
    check_op_types/check_unary_types 同源(不重复 isinstance(...) and not isinstance(..., bool))。
    """
    if not is_number(value):
        raise ExprError(f"{what}必须是数值, 得到 {label(type_name(value))}")
    return value


def result_type(op: str) -> str:
    """运算符的结果静态类型(算术得数值, 其余得布尔)"""
    return NUM if op in _ARITH_OPS else BOOL


def check_op_types(op: str, left: str, right: str) -> None:
    """二元运算符的类型规则(静态类型层面); 违规抛 ExprSyntaxError"""
    if ANY in (left, right):
        return
    if op in _ARITH_OPS:
        if left != NUM or right != NUM:
            raise ExprSyntaxError(f"'{op}' 两侧都必须是数值, 得到 {label(left)} 与 {label(right)}")
        return
    if op in _ORDER_OPS:
        same_num = left == NUM and right == NUM
        same_str = left == STR and right == STR
        if not (same_num or same_str):
            raise ExprSyntaxError(f"'{op}' 两侧必须同为数值或同为字符串, 得到 {label(left)} 与 {label(right)}")
        return
    if op in _EQ_OPS:
        if left != right and not (left == NUM and right == NUM):
            raise ExprSyntaxError(f"'{op}' 两侧类型不一致: {label(left)} 与 {label(right)}")
        return
    if op in _LOGIC_OPS:
        if left != BOOL or right != BOOL:
            raise ExprSyntaxError(f"'{op}' 两侧都必须是布尔, 得到 {label(left)} 与 {label(right)}")
        return
    if op == "in":
        if right not in (LIST, STR):
            raise ExprSyntaxError(f"'in' 右侧必须是列表或字符串, 得到 {label(right)}")
        return
    if op == "~":
        if left != STR or right != STR:
            raise ExprSyntaxError(f"'~' 两侧都必须是字符串(左侧为被匹配值, 右侧为模式), 得到 {label(left)} 与 {label(right)}")
        return
    raise ExprSyntaxError(f"未知运算符 '{op}'")


def check_unary_types(op: str, operand: str) -> None:
    """一元运算符的类型规则; 违规抛 ExprSyntaxError"""
    if operand == ANY:
        return
    if op == "not":
        if operand != BOOL:
            raise ExprSyntaxError(f"'not' 的操作数必须是布尔, 得到 {label(operand)}")
        return
    if op in ("-", "+"):
        if operand != NUM:
            raise ExprSyntaxError(f"'{op}' 的操作数必须是数值, 得到 {label(operand)}")

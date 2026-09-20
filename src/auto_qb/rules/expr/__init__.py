"""规则条件表达式: 词法 / 语法 / 编译(W1 内核)

分层(与 docs/plans/26-09-20-2225-rule-conditions-expression-plan.html 一致):
- lexer.py  字符串 -> Token 列表(字面量单位解析复用 utils, 与配置其它处同口径)
- parser.py Token -> AST, 编译期完成**语法层**静态检查
- env.py    取值面(名字 -> 取值器 + 类型 + 可用性)与语义校验 —— W2
- eval.py   AST 求值 —— W2

W1 只交付语法内核, 不接规则系统、不做取值。语法层静态检查负责:
① 一层一个运算符(同括号层第二个运算符即报错, 含 not 与同种连续)
② 标识符必须带作用域前缀(tor.*/tracker.*/sys.*), 函数名不带前缀
③ 字面量单位合法(10GB -> 报错, 须 iB)、字面量之间的类型冲突
名字是否存在 / 类型是否匹配 / 数据源可用性由 W2 的 env 负责(需要 AST 语义信息)。
"""
from .env import FUNC_TABLE, GATED_NAMES, NAME_TABLE, gated_names_in, validate
from .errors import ExprError, ExprSyntaxError
from .eval import evaluate
from .lexer import Token, tokenize
from .parser import Binary, Call, Expr, ListLit, Lit, Name, Unary, compile_expr
from .types import ANY, BOOL, LIST, NUM, STR

__all__ = [
    "ExprError",
    "ExprSyntaxError",
    "Token",
    "tokenize",
    "Expr",
    "Lit",
    "Name",
    "Call",
    "ListLit",
    "Unary",
    "Binary",
    "compile_expr",
    "evaluate",
    "validate",
    "NAME_TABLE",
    "FUNC_TABLE",
    "GATED_NAMES",
    "gated_names_in",
    "ANY",
    "BOOL",
    "LIST",
    "NUM",
    "STR",
]

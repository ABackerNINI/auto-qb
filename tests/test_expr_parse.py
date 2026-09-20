"""test_expr_parse 测试计划: rules/expr 表达式语法内核(词法 + 语法 + 静态检查)

## 测试计划(每个测试函数一条)
- test_tokenize_literals: 字面量切分(裸数字/大小/时长/速度/时刻/字符串/布尔), 值与单位解析复用 utils
- test_tokenize_invalid_units: 非法单位与"数字后紧跟字母"(10GB / 100abc / 5X)在词法阶段即报错
- test_tokenize_keywords_must_be_lowercase: 关键字大写(AND)给出改成小写的提示, 不被当成名字
- test_tokenize_names_and_ops: 带点名字与两字符运算符切分
- test_parse_single_operator_ok: 一层一个运算符的正例(比较/逻辑/in/单值/函数调用)
- test_parse_second_operator_rejected: 同层第二个运算符一律拒绝(and+or/比较+and/算术+比较/not+and/比较链)
- test_parse_same_kind_chain_rejected: 同种连续也算第二个(and and / + -), 必须加括号
- test_parse_paren_group_is_opaque: 括号组对该层不透明, (a + b) > c 合法且 AST 正确
- test_parse_unary_minus_literal_folded: -5 折叠为字面量(不算运算符); -tor.size 占一层
- test_parse_names_require_prefix: 标识符必须带 tor.*/tracker.*/sys.* 前缀
- test_parse_call: 函数调用形态(参数个数/无前缀/括号未闭合)
- test_parse_list_literal: 列表字面量(多项/空列表/未闭合)
- test_parse_structural_errors: 空表达式/括号未闭合/空括号/缺操作数/结尾多余内容
- test_parse_literal_type_conflicts: 字面量之间的类型冲突(算术/比较/not)
- test_compile_expr_ast_shape: 综合表达式的 AST 形状与原文保留("=" 归一化为 "==")
"""
import pytest

from auto_qb.rules.expr import Binary, Call, Expr, ListLit, Lit, Name, Unary, compile_expr
from auto_qb.rules.expr.errors import ExprSyntaxError
from auto_qb.rules.expr.lexer import tokenize


def _root(text):
    return compile_expr(text).root


def test_tokenize_literals():
    toks = [t for t in tokenize('100 1.5 10GiB 24H 1MiB/s 22:30 "HR" true') if t.kind != "eof"]
    assert [(t.kind, t.value) for t in toks] == [
        ("num", 100),
        ("num", 1.5),
        ("size", 10 * 1024**3),
        ("time", 86400),
        ("speed", 1024**2),
        ("hhmm", 22 * 60 + 30),
        ("str", "HR"),
        ("bool", True),
    ]


def test_tokenize_invalid_units():
    for bad in ("10GB", "100abc", "5X"):
        with pytest.raises(ExprSyntaxError):
            tokenize(bad)


def test_tokenize_keywords_must_be_lowercase():
    with pytest.raises(ExprSyntaxError, match="关键字必须小写"):
        tokenize("tor.a AND tor.b")


def test_tokenize_names_and_ops():
    toks = [t for t in tokenize("tor.size >= sys.dow") if t.kind != "eof"]
    assert [(t.kind, t.text) for t in toks] == [("name", "tor.size"), ("op", ">="), ("name", "sys.dow")]


def test_parse_single_operator_ok():
    assert isinstance(_root("tor.size >= 10GiB"), Binary)
    assert isinstance(_root("true and false"), Binary)
    assert isinstance(_root("tor.name"), Name)
    assert isinstance(_root("freespace(tor.save_path)"), Call)
    root = _root('tor.state in ["uploading", "forcedUP"]')
    assert isinstance(root, Binary) and root.op == "in" and isinstance(root.right, ListLit)
    assert isinstance(_root("sys.time_of_day >= 22:30"), Binary)


def test_parse_second_operator_rejected():
    for text in (
        "tor.a and tor.b or tor.c",
        "tor.ratio > 1.5 and tor.seeding_time > 3D",
        "tor.uploaded / tor.size > 1.5",
        "not tor.is_complete and tor.is_uploading",
        "1 < 2 < 3",
    ):
        with pytest.raises(ExprSyntaxError, match="同一括号内只能有一个运算符"):
            compile_expr(text)


def test_parse_same_kind_chain_rejected():
    for text in ("tor.a and tor.b and tor.c", "tor.a + tor.b - tor.c"):
        with pytest.raises(ExprSyntaxError, match="同一括号内只能有一个运算符"):
            compile_expr(text)


def test_parse_paren_group_is_opaque():
    root = _root("(tor.a + tor.b) > tor.c")
    assert isinstance(root, Binary) and root.op == ">"
    assert isinstance(root.left, Binary) and root.left.op == "+"


def test_parse_unary_minus_literal_folded():
    root = _root("-5 > 0")
    assert isinstance(root, Binary) and root.left == Lit(-5)
    assert isinstance(_root("(-tor.size) > 0"), Binary)
    with pytest.raises(ExprSyntaxError, match="同一括号内只能有一个运算符"):
        compile_expr("-tor.size > 0")


def test_parse_names_require_prefix():
    with pytest.raises(ExprSyntaxError, match="必须带作用域前缀"):
        compile_expr("size > 10GiB")
    assert isinstance(_root("tor.size > 10GiB"), Binary)


def test_parse_call():
    root = _root("min(tor.a, 1)")
    assert isinstance(root, Call) and root.name == "min" and len(root.args) == 2
    with pytest.raises(ExprSyntaxError, match="函数名不带作用域前缀"):
        compile_expr("tor.size()")
    with pytest.raises(ExprSyntaxError, match="参数括号未闭合"):
        compile_expr("freespace(tor.save_path")


def test_parse_list_literal():
    assert len(_root('["a", "b"]').items) == 2
    assert len(_root("[]").items) == 0
    with pytest.raises(ExprSyntaxError, match="列表字面量未闭合"):
        compile_expr('["a"')


def test_parse_structural_errors():
    with pytest.raises(ExprSyntaxError, match="不能为空"):
        compile_expr("")
    with pytest.raises(ExprSyntaxError, match="括号未闭合"):
        compile_expr("(1 + 2")
    with pytest.raises(ExprSyntaxError):
        compile_expr("()")
    with pytest.raises(ExprSyntaxError, match="缺少操作数"):
        compile_expr("and tor.a")
    with pytest.raises(ExprSyntaxError, match="多余内容"):
        compile_expr("tor.a tor.b")


def test_parse_literal_type_conflicts():
    with pytest.raises(ExprSyntaxError, match="两侧都必须是数值"):
        compile_expr('"a" + 1')
    with pytest.raises(ExprSyntaxError, match="必须同为数值或同为字符串"):
        compile_expr('1 > "a"')
    with pytest.raises(ExprSyntaxError, match="操作数必须是布尔"):
        compile_expr('not "a"')


def test_compile_expr_ast_shape():
    text = '((sys.dow <= 5) and ((sys.time_of_day >= 22:30) or (sys.time_of_day <= 7:00)))'
    expr = compile_expr(text)
    assert isinstance(expr, Expr) and expr.text == text
    root = expr.root
    assert isinstance(root, Binary) and root.op == "and"
    assert isinstance(root.left, Binary) and root.left.op == "<="
    assert isinstance(root.right, Binary) and root.right.op == "or"
    assert isinstance(root.right.left, Binary) and root.right.left.right == Lit(22 * 60 + 30)
    assert _root("tor.state = 'uploading'").op == "=="
    assert isinstance(_root("not (tor.a and tor.b)"), Unary)

# 分类: src/auto_qb/rules/expr/parser.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__parser.py.txt`
- 机器实测: 42 条全部真存活
- 计数: 42 条 = 真洞 3 / 等价 39 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `_Parser.parse__mutmut_14` | `parse` | 异常 `pos` 实参 `t.pos` → `None` | 等价 | 异常类型/抛出点/主文案不变, 仅少掉 `（第 N 列）` 后缀(诊断文案) |
| 2 | `_Parser.parse__mutmut_16` | `parse` | 异常 `pos` 实参删成尾逗号(默认 `None`) | 等价 | 同上, 与 #1 同一落点 |
| 3 | `_Parser._level_ex__mutmut_10` | `_level_ex` | `t.value == "not"` → `"XXnotXX"` | 真洞 | `not <数字字面量>` 不再走 `Unary("not")`, 而是掉进一元符号折叠成 `Lit(5)`, 于是 `(not 5) > 3` 从编译期报错变成求值为 `True`(类型检查被绕过)。**建议守阵**: `compile_expr("(not 5) > 3")` 必须抛 `ExprSyntaxError` |
| 4 | `_Parser._level_ex__mutmut_11` | `_level_ex` | `t.value == "not"` → `"NOT"` | 真洞 | 与 #3 同根因(`not` 判断失效 → 数字字面量被折叠)。**建议守阵**: 同 #3 一条断言即可覆盖两种拼写变异 |
| 5 | `_Parser._level_ex__mutmut_25` | `_level_ex` | `-x if t.value == "-" else x` → 条件后追加 `or True` | 真洞 | 一元 `+` 恒取负: `(+5) > 3` 由 `True` 变 `False`。**建议守阵**: `compile_expr("(+5) > 3")` 求值为 `True` |
| 6 | `_Parser._level_ex__mutmut_42` | `_level_ex` | 异常 `pos` 实参 `t.pos` → `None` | 等价 | 仅丢列号后缀, 抛错条件不变 |
| 7 | `_Parser._level_ex__mutmut_44` | `_level_ex` | 异常 `pos` 实参删成尾逗号 | 等价 | 同上 |
| 8 | `_Parser._primary__mutmut_8` | `_primary` | `"括号未闭合"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 9 | `_Parser._primary__mutmut_10` | `_primary` | `"括号未闭合"` 的 `pos` 删成尾逗号 | 等价 | 同上 |
| 10 | `_Parser._primary__mutmut_11` | `_primary` | 文案 `"括号未闭合"` → `"XX括号未闭合XX"` | 等价 | 纯异常文案扰动, 判定分支与抛错位置不变 |
| 11 | `_Parser._primary__mutmut_23` | `_primary` | `"缺少操作数…"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 12 | `_Parser._primary__mutmut_25` | `_primary` | `"缺少操作数…"` 的 `pos` 删成尾逗号 | 等价 | 同上 |
| 13 | `_Parser._primary__mutmut_26` | `_primary` | `label = t.text or "表达式结尾"` → `label = None` | 等价 | 只改末尾 `"意外的 '<label>'"` 文案内容(变 `'None'`) |
| 14 | `_Parser._primary__mutmut_27` | `_primary` | `label` 的 `or` → `and` | 等价 | `label` 只流入异常文案, 取值差异不改变"是否报错/报什么类型" |
| 15 | `_Parser._primary__mutmut_28` | `_primary` | 兜底文案 `"表达式结尾"` → `"XX表达式结尾XX"` | 等价 | 纯文案 |
| 16 | `_Parser._primary__mutmut_29` | `_primary` | `ExprSyntaxError(f"意外的…", t.pos)` → `(None, t.pos)` | 等价 | 仍抛 `ExprSyntaxError`, 仅消息退化成 `None（第 N 列）` |
| 17 | `_Parser._primary__mutmut_30` | `_primary` | `"意外的…"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 18 | `_Parser._primary__mutmut_31` | `_primary` | `ExprSyntaxError(f"意外的…", t.pos)` → `(t.pos)` | 等价 | 仍抛同类异常, 只是消息退化成裸列号(文案) |
| 19 | `_Parser._primary__mutmut_32` | `_primary` | `"意外的…"` 的 `pos` 删成尾逗号 | 等价 | 仅丢列号后缀 |
| 20 | `_Parser._name_or_call__mutmut_7` | `_name_or_call` | 作用域前缀报错的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 21 | `_Parser._name_or_call__mutmut_9` | `_name_or_call` | 作用域前缀报错的 `pos` 删成尾逗号 | 等价 | 同上 |
| 22 | `_Parser._name_or_call__mutmut_11` | `_name_or_call` | `Name(t.value, t.pos)` → `Name(t.value, None)` | 等价 | `Name.pos` 全仓只在 env 的 3 处报错文案里被读, 不参与计算/比较 |
| 23 | `_Parser._name_or_call__mutmut_13` | `_name_or_call` | `Name(t.value, t.pos)` → `Name(t.value, )`(pos 默认 0) | 等价 | 同上, 只是列号变 0 |
| 24 | `_Parser._name_or_call__mutmut_26` | `_name_or_call` | `"参数括号未闭合"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 25 | `_Parser._name_or_call__mutmut_28` | `_name_or_call` | `"参数括号未闭合"` 的 `pos` 删成尾逗号 | 等价 | 同上 |
| 26 | `_Parser._name_or_call__mutmut_32` | `_name_or_call` | `"函数名不带作用域前缀"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 27 | `_Parser._name_or_call__mutmut_34` | `_name_or_call` | `"函数名不带作用域前缀"` 的 `pos` 删成尾逗号 | 等价 | 同上 |
| 28 | `_Parser._name_or_call__mutmut_37` | `_name_or_call` | `Call(t.value, tuple(args), t.pos)` → `(…, None)` | 等价 | `Call.pos` 只进 env 报错列号, 无业务读点 |
| 29 | `_Parser._name_or_call__mutmut_40` | `_name_or_call` | `Call(…)` 的 `pos` 删成尾逗号(默认 0) | 等价 | 同上 |
| 30 | `_Parser._list_literal__mutmut_14` | `_list_literal` | `"列表字面量未闭合"` 的 `pos` → `None` | 等价 | 仅丢列号后缀 |
| 31 | `_Parser._list_literal__mutmut_16` | `_list_literal` | 同上, `pos` 删成尾逗号 | 等价 | 同上 |
| 32 | `_Parser._list_literal__mutmut_17` | `_list_literal` | 文案 `"列表字面量未闭合…"` → `"XX…XX"` | 等价 | 纯文案 |
| 33 | `_Parser._list_literal__mutmut_19` | `_list_literal` | `ListLit(tuple(items), t.pos)` → `(…, None)` | 等价 | `ListLit.pos` 全仓无任何读点 |
| 34 | `_Parser._list_literal__mutmut_21` | `_list_literal` | `ListLit(…)` 的 `pos` 删成尾逗号 | 等价 | 同上 |
| 35 | `_Parser._reject_second__mutmut_3` | `_reject_second` | 改写提示的 `pos` → `None` | 等价 | 仅丢列号后缀, `used is None` 的放行判据不变 |
| 36 | `_Parser._reject_second__mutmut_5` | `_reject_second` | 改写提示的 `pos` 删成尾逗号 | 等价 | 同上 |
| 37 | `_check_literals__mutmut_1` | `_check_literals` | `_check_literals(node.left)` → `_check_literals(None)` | 等价 | `_check_literals` 只是 `validate()` 的重复前置检查: 三处调用(conditions / config 校验 / webui 试算)都在 `compile_expr` 后紧跟 `validate`, 而 `env.static_type` 会带字面量类型递归调用同一个 `check_op_types`, 系统边界不可区分 |
| 38 | `_check_literals__mutmut_2` | `_check_literals` | `_check_literals(node.right)` → `_check_literals(None)` | 等价 | 同 #37(重复检查, 被 `static_type` 覆盖) |
| 39 | `_check_literals__mutmut_12` | `_check_literals` | `_check_literals(node.operand)` → `_check_literals(None)` | 等价 | 同 #37(`static_type` 对 Unary 亦递归 + `check_unary_types`) |
| 40 | `_check_literals__mutmut_14` | `_check_literals` | `check_unary_types(node.op, type_name(...))` → `(node.op, None)` | 等价 | `None` 既不等于 `ANY` 也不等于 `BOOL/NUM`, 违规输入照样抛 `ExprSyntaxError`, 只是文案里类型名变成 `None` |
| 41 | `_check_literals__mutmut_18` | `_check_literals` | 调用实参 `_check_literals(arg)` → `_check_literals(None)` | 等价 | 同 #37(`static_type` 逐参递归并做类型检查) |
| 42 | `_check_literals__mutmut_19` | `_check_literals` | 列表元素 `_check_literals(item)` → `_check_literals(None)` | 等价 | 同 #37(`static_type` 对 `ListLit` 逐项递归) |

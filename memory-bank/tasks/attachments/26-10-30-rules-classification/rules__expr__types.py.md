# 分类: src/auto_qb/rules/expr/types.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__types.py.txt`
- 机器实测: 22 条全部真存活
- 计数: 22 条 = 真洞 4 / 等价 18 / 假存活 0

判定口径:判据(`is_number` / 类型相容关系 / 枚举成员)变化 ⇒ 真洞;仅异常文案里 `label(...)` 的参数被换成 `None` ⇒ 等价(仍抛同类异常,只有「得到 数值/字符串」这类短语变「得到 None」)。

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.expr.types.x_label__mutmut_2` | label | `_TYPE_LABEL.get(kind, kind)` → `.get(kind, None)` | 等价 | 所有调用点的 kind 都来自 `type_name()` 或 `NAME_TABLE/FUNC_TABLE`(均用 NUM/BOOL/STR/LIST/ANY 常量),必在表内,默认分支不可达 |
| 2 | `auto_qb.rules.expr.types.x_label__mutmut_3` | label | `.get(kind, kind)` → `.get(kind)` | 等价 | 同上,`get` 缺省值同为 None,默认分支不可达 |
| 3 | `auto_qb.rules.expr.types.x_label__mutmut_4` | label | `.get(kind, kind)` → `.get(kind, )` | 等价 | 与 #2 完全等价(仅多余逗号),默认分支不可达 |
| 4 | `auto_qb.rules.expr.types.x_require_number__mutmut_4` | require_number | 报错 `label(type_name(value))` → `label(None)` | 等价 | 判据 `is_number` 不变,仍抛 ExprError,仅文案变「得到 None」 |
| 5 | `auto_qb.rules.expr.types.x_require_number__mutmut_5` | require_number | 报错 `label(type_name(value))` → `label(type_name(None))` | 等价 | `type_name(None)` 为 ANY,文案变「得到 任意」,判据不变 |
| 6 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_7` | check_op_types | 算术报错 `label(left)` → `label(None)` | 等价 | 仅文案,仍抛「两侧都必须是数值」 |
| 7 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_8` | check_op_types | 算术报错 `label(right)` → `label(None)` | 等价 | 仅文案 |
| 8 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_14` | check_op_types | `same_str = left == STR and right == STR` → `same_str = None` | 真洞 | 恒假使字符串排序全部被拒:`"a" < "b"` 由编译通过变为抛「必须同为数值或同为字符串」。**建议守阵**: `compile_expr('"a" < "b"')` 应通过(字符串可比大小) |
| 9 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_21` | check_op_types | 排序报错 `label(left)` → `label(None)` | 等价 | 仅文案 |
| 10 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_22` | check_op_types | 排序报错 `label(right)` → `label(None)` | 等价 | 仅文案 |
| 11 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_24` | check_op_types | 相等判定 `if left != right and not (...)` → `or not (...)` | 真洞 | 同类型字面量比较被误判:`"a" == "b"` 由通过变为抛「两侧类型不一致」。**建议守阵**: `compile_expr('"a" == "b"')` 应通过,同类型(含两个字符串)相等比较合法 |
| 12 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_29` | check_op_types | `not (left == NUM and right == NUM)` → `not (left == NUM and right != NUM)` | 真洞 | 混合类型相等不再报错:`1 == "a"` 编译通过并在求值时静默得 False,类型校验形同虚设。**建议守阵**: `compile_expr('1 == "a"')` 应抛「两侧类型不一致」 |
| 13 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_31` | check_op_types | 相等报错 `label(left)` → `label(None)` | 等价 | 仅文案 |
| 14 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_32` | check_op_types | 相等报错 `label(right)` → `label(None)` | 等价 | 仅文案 |
| 15 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_38` | check_op_types | 逻辑报错 `label(left)` → `label(None)` | 等价 | 仅文案 |
| 16 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_39` | check_op_types | 逻辑报错 `label(right)` → `label(None)` | 等价 | 仅文案 |
| 17 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_45` | check_op_types | `in` 报错 `label(right)` → `label(None)` | 等价 | 仅文案,`right not in (LIST, STR)` 判据不变 |
| 18 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_52` | check_op_types | `~` 报错 `label(left)` → `label(None)` | 等价 | 仅文案 |
| 19 | `auto_qb.rules.expr.types.x_check_op_types__mutmut_53` | check_op_types | `~` 报错 `label(right)` → `label(None)` | 等价 | 仅文案 |
| 20 | `auto_qb.rules.expr.types.x_check_unary_types__mutmut_7` | check_unary_types | `not` 报错 `label(operand)` → `label(None)` | 等价 | 仅文案,`operand != BOOL` 判据不变 |
| 21 | `auto_qb.rules.expr.types.x_check_unary_types__mutmut_10` | check_unary_types | 一元运算符枚举 `("-", "+")` → `("-", "XX+XX")` | 真洞 | `"+"` 掉出枚举,一元加号不再做静态检查:`+"abc"` 由编译期抛「操作数必须是数值」变为编译通过、求值时 `_unary` 原样返回 `"abc"`。**建议守阵**: `compile_expr('+"a"')` 应抛「操作数必须是数值」 |
| 22 | `auto_qb.rules.expr.types.x_check_unary_types__mutmut_13` | check_unary_types | 一元 `+/-` 报错 `label(operand)` → `label(None)` | 等价 | 仅文案 |

# 分类: src/auto_qb/rules/expr/eval.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__eval.py.txt`
- 机器实测: 38 条全部真存活
- 计数: 38 条 = 真洞 18 / 等价 20 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `x_trace__mutmut_30` | `trace` | 调用实参遍历 `walk(arg)` → `walk(None)` | 真洞 | `walk(None)` 不匹配任何分支, 调用实参里的取值项(如 `exists(tor.save_path)`)从求值轨迹里整段消失, WEB 试算面板少显示。**建议守阵**: `trace(compile_expr("exists(tor.save_path)").root, ctx)` 的条目里含 `tor.save_path` |
| 2 | `x_trace__mutmut_34` | `trace` | 列表元素遍历 `walk(item)` → `walk(None)` | 真洞 | 列表字面量内的取值项漏进轨迹(与 #1 同根因, 范围更窄: 需 `[<name/call>]`)。**建议守阵**: `trace(tor.state in [tor.xxx])` 含内层 name 项 |
| 3 | `x__jsonable__mutmut_2` | `_jsonable` | `isinstance(value, float) and (…)` → `or (…)` | 真洞 | 任何有限浮点都命中 → 数值被转成字符串(`3.5` → `"3.5"`), trace 里数值类型退化。**建议守阵**: `_jsonable(3.5) == 3.5` 且 `_jsonable(float("inf")) == "inf"` |
| 4 | `x__jsonable__mutmut_7` | `_jsonable` | `float("inf")` → `float("INF")` | 等价 | `float()` 对 inf/infinity 大小写不敏感, 解析结果同为 `inf` |
| 5 | `x__jsonable__mutmut_8` | `_jsonable` | `value != value`(NaN 判据) → `value == value` | 真洞 | `value == value` 对一切非 NaN 浮点恒真 → 所有浮点都被转字符串, 与 #3 等价后果。**建议守阵**: #3 那条断言即可覆盖 |
| 6 | `x__jsonable__mutmut_12` | `_jsonable` | 兜底 `str(value)` → `str(None)` | 真洞 | 非原始类型(`raw()` 可返回 dict/自定义对象)在轨迹里被吞成字符串 `"None"`, 试算面板显示错误值。**建议守阵**: `_jsonable({"a": 1}) == "{'a': 1}"` |
| 7 | `_name_value__mutmut_10` | `_name_value` | 缓存键前缀 `("name", …)` → `("XXnameXX", …)` | 等价 | 键只在本函数内自洽读写; 与 call 键(3 元组)形状不同, 无跨类碰撞, 也无外部读点 |
| 8 | `_name_value__mutmut_11` | `_name_value` | 缓存键前缀 → `"NAME"` | 等价 | 同 #7 |
| 9 | `_call_value__mutmut_19` | `_call_value` | 缓存键前缀 `("call", …)` → `"XXcallXX"` | 等价 | 同 #7(命中/未命中行为一致) |
| 10 | `_call_value__mutmut_20` | `_call_value` | 缓存键前缀 → `"CALL"` | 等价 | 同 #7 |
| 11 | `_as_bool__mutmut_3` | `_as_bool` | 报错文案 `label(type_name(value))` → `label(None)` | 等价 | 只改异常文案里的类型名, 判定分支不变 |
| 12 | `_as_bool__mutmut_4` | `_as_bool` | `label(type_name(value))` → `label(type_name(None))` | 等价 | 同上 |
| 13 | `_unary__mutmut_11` | `_unary` | `_as_bool(value, "not")` → `_as_bool(value, None)` | 等价 | `op` 仅用于拼报错文案(`'None' 的操作数必须是布尔`) |
| 14 | `_unary__mutmut_14` | `_unary` | `"not"` → `"XXnotXX"` | 等价 | 同上, 纯文案 |
| 15 | `_unary__mutmut_15` | `_unary` | `"not"` → `"NOT"` | 等价 | 同上, 纯文案 |
| 16 | `_unary__mutmut_17` | `_unary` | `-value if node.op == "-" else value` → 条件后追加 `or True` | 真洞 | 一元 `+` 变成取负: `+tor.ratio` 结果翻号(解析期 `+5` 已被折叠成字面量, 所以此路只在名字/表达式操作数上暴露)。**建议守阵**: `evaluate(compile_expr("(+tor.ratio) > 0").root, ctx)` 与 `tor.ratio > 0` 同值 |
| 17 | `_binary__mutmut_7` | `_binary` | `and` 左侧 `_as_bool(..., op)` → `(..., None)` | 等价 | `op` 仅进报错文案, 短路结构与求值顺序不变 |
| 18 | `_binary__mutmut_34` | `_binary` | `or` 右侧 `evaluate(node.right, ctx)` → `None` | 真洞 | 左假时 or 右支永不被求值, 直接 `_as_bool(None)` 抛 `ExprError` → `false or true` 变成报错。**建议守阵**: `evaluate(compile_expr("(1 > 2) or (2 > 1)").root, ctx) is True` |
| 19 | `_binary__mutmut_35` | `_binary` | `or` 右侧 `_as_bool(..., op)` → `(..., None)` | 等价 | `op` 仅进报错文案 |
| 20 | `_binary__mutmut_36` | `_binary` | `or` 右侧 `_as_bool(evaluate(...), op)` → `_as_bool(op)`(少一实参) | 真洞 | 左假时抛 `TypeError`(缺 `value` 实参)而非 `ExprError`, `Rule.process` 的兜底捕不到 → 崩溃而非"不匹配+停规则"。**建议守阵**: `false or true` 正常返回 `True` 且不抛 `TypeError` |
| 21 | `_binary__mutmut_37` | `_binary` | `or` 右侧 `_as_bool(evaluate(...), )`(缺 `op` 实参) | 真洞 | 同 #20: 左假时 `TypeError` 泄漏出求值层。**建议守阵**: 同 #18 的 `false or true` 正例, 且断言异常类型不为 `TypeError` |
| 22 | `_binary__mutmut_38` | `_binary` | `or` 右侧 `evaluate(node.right, ctx)` → `evaluate(None, ctx)` | 真洞 | 左假时抛 `ExprError("无法求值的节点: None")`, 合法的 `false or …` 全废。**建议守阵**: 同 #18, `false or true` 必须返回 `True` |
| 23 | `_binary__mutmut_39` | `_binary` | `or` 右侧 `evaluate(node.right, ctx)` → `evaluate(node.right, None)` | 真洞 | 左假且右支为取值名时 ctx 缺失 → 取数失败(右支是字面量时才侥幸同值)。**建议守阵**: `(1 > 2) or (tor.size > 1)` 必须按 ctx 取到真实值 |
| 24 | `_binary__mutmut_40` | `_binary` | `or` 右侧 `evaluate(node.right, ctx)` → `evaluate(ctx)`(少一实参) | 真洞 | 左假时 `TypeError` 泄漏, 同 #20。**建议守阵**: 同 #18 一条 `false or true` 正例覆盖 |
| 25 | `_binary__mutmut_41` | `_binary` | `or` 右侧 `evaluate(node.right, )`(缺 ctx) | 真洞 | 左假时 `TypeError` 泄漏, 同 #20。**建议守阵**: 同 #18 一条 `false or true` 正例覆盖 |
| 26 | `_binary__mutmut_79` | `_binary` | 算术 `/` 分支 `left / right` → `left * right` | 真洞 | 除法静默变乘法(`10 / 4` → `40`), 除零守卫拦不住。**建议守阵**: `evaluate(compile_expr("(10 / 4) > 2").root, ctx)` 为 `True` 且 `(10 / 4) > 3` 为 `False` |
| 27 | `_binary__mutmut_87` | `_binary` | 比较文案 `label(type_name(left))` → `label(None)` | 等价 | 仅异常文案里的类型名 |
| 28 | `_binary__mutmut_88` | `_binary` | `label(type_name(left))` → `label(type_name(None))` | 等价 | 同上 |
| 29 | `_binary__mutmut_89` | `_binary` | 比较文案 `label(type_name(right))` → `label(None)` | 等价 | 同上 |
| 30 | `_binary__mutmut_90` | `_binary` | `label(type_name(right))` → `label(type_name(None))` | 等价 | 同上 |
| 31 | `_binary__mutmut_93` | `_binary` | `>` 分支 `left > right` → `left >= right` | 真洞 | 相等值上 `>` 变真(`10GiB > 10GiB` → `True`), 阈值语义整体偏移一格。**建议守阵**: 两侧相等时 `>` 求值为 `False` |
| 32 | `_binary__mutmut_95` | `_binary` | `if op == "<"` → `if op == "XX<XX"` | 真洞 | `<` 分支失配, 落到函数末尾 `return left <= right` → 相等时变真。**建议守阵**: 两侧相等时 `<` 求值为 `False` |
| 33 | `_binary__mutmut_96` | `_binary` | `<` 分支 `left < right` → `left <= right` | 真洞 | 同 #31/#32: 相等边界上 `<` 变真。**建议守阵**: 同 #32 一条断言即可 |
| 34 | `_binary__mutmut_107` | `_binary` | 相等比较文案 `label(left_tn)` → `label(None)` | 等价 | 仅异常文案 |
| 35 | `_binary__mutmut_108` | `_binary` | 相等比较文案 `label(right_tn)` → `label(None)` | 等价 | 仅异常文案 |
| 36 | `_binary__mutmut_125` | `_binary` | `in` 报错文案 `label(type_name(right))` → `label(None)` | 等价 | 仅异常文案, `TypeError`→`ExprError` 的转换仍成立 |
| 37 | `_binary__mutmut_126` | `_binary` | `in` 报错文案 → `label(type_name(None))` | 等价 | 同上 |
| 38 | `_binary__mutmut_132` | `_binary` | `targets = left if isinstance(...) else [left]` → 条件后追加 `and False` | 真洞 | `~` 左侧为集合(`tor.tags`)时不再逐元素匹配, 退化成"整集合转字符串"匹配, "任一元素命中"语义丢失。**建议守阵**: `tor.tags ~ "regex:^HR"` 在 tags 含 `HR-x` 时为 `True` |

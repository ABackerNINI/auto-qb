# 分类: src/auto_qb/rules/expr/lexer.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__lexer.py.txt`
- 机器实测: 73 条全部真存活
- 计数: 73 条 = 真洞 4 / 等价 69 / 假存活 0
- 分片文件共 84 个 `@@@` 块:73 条 `survived`(本表全列)+ 11 条 `timeout`(`x_tokenize__mutmut_11/12/55/77/78/93/94`、`x__read_string__mutmut_3/4/18/30`,变异把下标推进改成 `i = 1` / `i -= 1` / `i -= 2` 造成死循环,mutmut 计为 killed,不在「95 条真存活」口径内,故不入表)。

判定口径:接受/拒绝结论、token 种类或 token 值发生变化 ⇒ 真洞;仅异常文案、报错列号 `pos`、无读点字段变化 ⇒ 等价(parser 只按 `kind` 与 `value` 分发,`text` 仅出现在 `parser.py:113` / `parser.py:174` 的报错串里,`pos` 仅进 `Name/Call/ListLit.pos` 与报错列号)。

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_5` | tokenize | 空表达式文案 `"表达式不能为空"` → `"XX表达式不能为空XX"` | 等价 | 仍抛 ExprSyntaxError,判据 `not s.strip()` 不变,仅文案差异 |
| 2 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_15` | tokenize | `pos = i + 1` → `pos = None` | 等价 | pos 只作报错列号,无判定读点 |
| 3 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_16` | tokenize | `pos = i + 1` → `pos = i - 1` | 等价 | 列号偏移 2,不影响 token 种类/值 |
| 4 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_17` | tokenize | `pos = i + 1` → `pos = i + 2` | 等价 | 同上,仅列号偏移 |
| 5 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_19` | tokenize | 引号集合 `c in "'\""` → `c in "XX'\"XX"`(加入 `X`) | 真洞 | `tokenize("X")` 由返回 name token 变为按字符串读并抛「字符串缺少结束引号」,词法器接受的字符集被放宽,记号流被改写。**建议守阵**: `tokenize("X")` 仍返回单个 `kind=="name"` 的 token(不得把 `X` 当引号起始) |
| 6 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_27` | tokenize | str token `text=raw` → `text=None` | 等价 | str 的值走 `value`,`text` 只进报错文案(parser.py:113) |
| 7 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_29` | tokenize | str token `pos` → `None` | 等价 | 列号 |
| 8 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_45` | tokenize | 括号集合 `c in "()[],"` → `c in "XX()[],XX"`(加入 `X`) | 真洞 | `tokenize("X")[0].kind` 由 `"name"` 变为 `"X"`,记号种类被改写,parser 侧退化为「意外的 'X'」。**建议守阵**: `tokenize("X")[0].kind == "name"`(括号集合不得含字母) |
| 9 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_48` | tokenize | 括号 token `text=c` → `text=None` | 等价 | 括号只按 `kind` 匹配,text 无读点 |
| 10 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_49` | tokenize | 括号 token `value=c` → `value=None` | 等价 | 括号 value 无读点 |
| 11 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_50` | tokenize | 括号 token `pos` → `None` | 等价 | 列号 |
| 12 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_66` | tokenize | 两字符运算符 token `pos` → `None` | 等价 | 列号 |
| 13 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_79` | tokenize | 两字符运算符 `i += 2` → `i += 3` | 真洞 | 运算符后多跳一字符,`tokenize("a<=b")` 丢掉 `b`,记号流由 4 个变 3 个(紧贴运算符的右操作数被吞)。**建议守阵**: `tokenize("a<=b")` 的 `[(k.text or k.value) …]` 恰为 name/op/name/eof 四项 |
| 14 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_84` | tokenize | 单字符运算符 token `text=c` → `text=None` | 等价 | op 分发走 `value`(parser.py:127/143),text 只进报错 |
| 15 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_86` | tokenize | 单字符运算符 token `pos` → `None` | 等价 | 列号 |
| 16 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_113` | tokenize | 大写关键字报错 `pos` → `None` | 等价 | 仍抛「关键字必须小写」,仅少列号 |
| 17 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_115` | tokenize | 大写关键字报错省略 `pos` 实参 | 等价 | 同上 |
| 18 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_119` | tokenize | bool token `text=word` → `text=None` | 等价 | bool 走 `value`(True/False) |
| 19 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_121` | tokenize | bool token `pos` → `None` | 等价 | 列号 |
| 20 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_130` | tokenize | 关键字运算符(and/or/not/in)token `text` → `None` | 等价 | op 分发走 `value` |
| 21 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_132` | tokenize | 关键字运算符 token `pos` → `None` | 等价 | 列号 |
| 22 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_144` | tokenize | name token `pos` → `None` | 等价 | pos 只落到 `Name/Call.pos`,最终只进报错列号 |
| 23 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_153` | tokenize | 非法字符报错 `pos` → `None` | 等价 | 仍抛「非法字符」,仅少列号 |
| 24 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_155` | tokenize | 非法字符报错省略 `pos` 实参 | 等价 | 同上 |
| 25 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_158` | tokenize | eof token `text=""` → `text=None` | 等价 | parser.py:174 写的是 `t.text or "表达式结尾"`,`None` 与 `""` 同效 |
| 26 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_159` | tokenize | eof token `pos=n+1` → `None` | 等价 | eof 的 pos 无判定读点 |
| 27 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_166` | tokenize | eof token `text=""` → `"XXXX"` | 等价 | 仅把「意外的 '表达式结尾'」文案改成「意外的 'XXXX'」 |
| 28 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_167` | tokenize | eof token `pos=n+1` → `n-1` | 等价 | 列号 |
| 29 | `auto_qb.rules.expr.lexer.x_tokenize__mutmut_168` | tokenize | eof token `pos=n+1` → `n+2` | 等价 | 列号 |
| 30 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_13` | _read_string | 转义判定 `i + 1 < len(s)` → `i + 2 < len(s)` | 真洞 | 转义符位于倒数第二位时不再生效:`"a\"`(4 字符)由抛「字符串缺少结束引号」变为被接受,值含裸反斜杠,引号/转义语义被改写。**建议守阵**: `tokenize('"a\\"')` 必须抛「字符串缺少结束引号」(末尾 `\"` 是转义而非收尾) |
| 31 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_23` | _read_string | 原始文本切片 `s[start:i + 1]` → `s[start:i - 1]` | 等价 | 该切片只作 token.text,仅影响报错里回显的原文 |
| 32 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_24` | _read_string | 原始文本切片 `s[start:i + 1]` → `s[start:i + 2]` | 等价 | 同上,仅报错回显文案 |
| 33 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_34` | _read_string | 未闭合报错 `pos=start+1` → `None` | 等价 | 列号 |
| 34 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_36` | _read_string | 未闭合报错省略 `pos` 实参 | 等价 | 列号 |
| 35 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_37` | _read_string | 未闭合报错 `pos=start+1` → `start-1` | 等价 | 列号 |
| 36 | `auto_qb.rules.expr.lexer.x__read_string__mutmut_38` | _read_string | 未闭合报错 `pos=start+1` → `start+2` | 等价 | 列号 |
| 37 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_13` | _read_number | 非法时间报错 `pos` → `None` | 等价 | 仍抛「非法时间字面量」,仅少列号 |
| 38 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_15` | _read_number | 非法时间报错省略 `pos` 实参 | 等价 | 同上 |
| 39 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_16` | _read_number | 非法时间报错 `pos=start+1` → `start-1` | 等价 | 列号 |
| 40 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_17` | _read_number | 非法时间报错 `pos=start+1` → `start+2` | 等价 | 列号 |
| 41 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_19` | _read_number | hhmm token `text=raw` → `text=None` | 等价 | hhmm 的值走 `value`(分钟数) |
| 42 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_21` | _read_number | hhmm token `pos` → `None` | 等价 | 列号 |
| 43 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_31` | _read_number | hhmm token `pos=start+1` → `start-1` | 等价 | 列号 |
| 44 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_32` | _read_number | hhmm token `pos=start+1` → `start+2` | 等价 | 列号 |
| 45 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_40` | _read_number | 「无法识别的数字」报错 `pos` → `None` | 等价 | 仍抛,仅少列号 |
| 46 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_42` | _read_number | 同上,省略 `pos` 实参 | 等价 | 同上 |
| 47 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_43` | _read_number | 同上,`pos=start+1` → `start-1` | 等价 | 列号 |
| 48 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_44` | _read_number | 同上,`pos=start+1` → `start+2` | 等价 | 列号 |
| 49 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_69` | _read_number | 单位分支 `_ensure_boundary(…, raw, …)` → `raw=None` | 等价 | raw 只进「数字后紧跟非法字符」文案,越界判定与抛错时机不变 |
| 50 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_70` | _read_number | 单位分支 `_ensure_boundary(…, start)` → `None` | 等价 | 只影响报错列号 |
| 51 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_77` | _read_number | 非法字面量 `ExprSyntaxError(f"…", pos)` → `ExprSyntaxError(None, pos)` | 等价 | 仍抛 ExprSyntaxError,文案变「None（第 N 列）」 |
| 52 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_78` | _read_number | 非法字面量报错 `pos` → `None` | 等价 | 列号 |
| 53 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_79` | _read_number | 非法字面量 `ExprSyntaxError(f"…", pos)` → `ExprSyntaxError(start + 1)` | 等价 | 仍抛,文案退化为列号数字 |
| 54 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_80` | _read_number | 非法字面量报错省略 `pos` 实参 | 等价 | 列号 |
| 55 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_81` | _read_number | 非法字面量报错 `pos=start+1` → `start-1` | 等价 | 列号 |
| 56 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_82` | _read_number | 非法字面量报错 `pos=start+1` → `start+2` | 等价 | 列号 |
| 57 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_84` | _read_number | 单位 token `text=raw` → `text=None` | 等价 | 单位字面量的值走 `value`(字节/秒/时长) |
| 58 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_86` | _read_number | 单位 token `pos` → `None` | 等价 | 列号 |
| 59 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_91` | _read_number | 单位 token `pos=start+1` → `start-1` | 等价 | 列号 |
| 60 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_92` | _read_number | 单位 token `pos=start+1` → `start+2` | 等价 | 列号 |
| 61 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_95` | _read_number | 裸数字分支 `_ensure_boundary(…, num_text, …)` → `None` | 等价 | raw 只进报错文案,`1.5.2` / `100abc` 仍在同一位置拒收 |
| 62 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_103` | _read_number | `float(num_text) if "." in num_text else int(num_text)` → 恒 `float` | 等价 | `100` 与 `100.0` 在 `==`、算术、`type_name`(均为 NUM)上不可区分,仅 repr 差异,不改变任何判据 |
| 63 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_109` | _read_number | 裸数字 token `text=num_text` → `text=None` | 等价 | num 走 `value` |
| 64 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_111` | _read_number | 裸数字 token `pos` → `None` | 等价 | 列号 |
| 65 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_118` | _read_number | 裸数字 token `pos=start+1` → `start-1` | 等价 | 列号 |
| 66 | `auto_qb.rules.expr.lexer.x__read_number__mutmut_119` | _read_number | 裸数字 token `pos=start+1` → `start+2` | 等价 | 列号 |
| 67 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_5` | _ensure_boundary | 字符集合 `s[i] in "_."` → `s[i] in "XX_.XX"`(加入 `X`) | 等价 | `"X".isalnum()` 本就为真,`X` 早已被左支覆盖,加入是纯冗余,分支判定完全不变 |
| 68 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_6` | _ensure_boundary | 报错 `ExprSyntaxError(f"…", pos)` → `ExprSyntaxError(None, pos)` | 等价 | 仍抛,文案变「None（第 N 列）」 |
| 69 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_7` | _ensure_boundary | 报错 `pos` → `None` | 等价 | 列号 |
| 70 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_8` | _ensure_boundary | 报错 → `ExprSyntaxError(start + 1)` | 等价 | 仍抛,文案退化为列号数字 |
| 71 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_9` | _ensure_boundary | 报错省略 `pos` 实参 | 等价 | 列号 |
| 72 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_10` | _ensure_boundary | 报错 `pos=start+1` → `start-1` | 等价 | 列号 |
| 73 | `auto_qb.rules.expr.lexer.x__ensure_boundary__mutmut_11` | _ensure_boundary | 报错 `pos=start+1` → `start+2` | 等价 | 列号 |

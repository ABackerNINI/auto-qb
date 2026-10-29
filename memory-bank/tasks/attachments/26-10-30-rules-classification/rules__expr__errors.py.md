# 分类: src/auto_qb/rules/expr/errors.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__errors.py.txt`
- 计数: 4 条 = 真洞 0 / 等价 4 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.expr.errors.xǁExprSyntaxErrorǁ__init____mutmut_1` | ExprSyntaxError.__init__ | 属性赋值 `self.pos = pos` → `None` | 等价 | 全仓无任何读取 `.pos` 的代码（src/tests 均无），异常类型与消息都不受影响，行为不可观测 |
| 2 | `auto_qb.rules.expr.errors.xǁExprSyntaxErrorǁ__init____mutmut_3` | ExprSyntaxError.__init__ | 条件追加 `and False`，列号后缀恒不拼 | 等价 | 仅异常消息少一段「（第 N 列）」，属消息文案差异，不影响类型与调用方判断 |
| 3 | `auto_qb.rules.expr.errors.xǁExprSyntaxErrorǁ__init____mutmut_4` | ExprSyntaxError.__init__ | 条件追加 `or True`，pos=None 时也拼后缀 | 等价 | 仅消息变成「（第 None 列）」，属消息文案差异 |
| 4 | `auto_qb.rules.expr.errors.xǁExprSyntaxErrorǁ__init____mutmut_5` | ExprSyntaxError.__init__ | 判断反转 `pos is not None` → `pos is None` | 等价 | 只是把「带列号」与「纯消息」两种文案对调，异常类型与定位信息载体不变，属消息文案差异 |

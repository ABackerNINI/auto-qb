# 分类: src/auto_qb/rules/registry.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__registry.py.txt`
- 计数: 3 条 = 真洞 0 / 等价 3 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.registry.x_create_action__mutmut_1` | create_action | 参数默认值 `ignore_error=False` → `True` | 等价 | 全部调用点（base.py:175 与 test_registry 三处）都显式传参，默认值不可达，任何执行路径都拿不到差异 |
| 2 | `auto_qb.rules.registry.x_create_action__mutmut_3` | create_action | 实参 `ignore_error` → `None` | 等价 | 动作侧唯一消费点 base.py:257 是 `if not action.ignore_error` 真值判断，None 与 False 同分支，无 `is` 比较 |
| 3 | `auto_qb.rules.registry.x_create_action__mutmut_5` | create_action | 省略第二实参（`ACTIONS[name](value, )`） | 等价 | 落到各动作自身 `__init__(spec, ignore_error=False)` 默认值，与显式传 False 完全等价 |

# 分类: src/auto_qb/rules/conditions.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__conditions.py.txt`
- 计数: 12 条 = 真洞 3 / 等价 9 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.conditions.x__in_range__mutmut_9` | _in_range | `split("-", 1)` → `split("-")`（去掉 maxsplit） | 等价 | 合法单区间/单值 spec 拆分结果完全一致；只有多段 spec 才分叉，而两边都抛 ValueError（解包失败 vs int 转换失败），仅消息文案不同 |
| 2 | `auto_qb.rules.conditions.x__in_range__mutmut_10` | _in_range | `split` → `rsplit` | 等价 | 只含一个 `-` 的合法 spec 两者相同；多段 spec 两边同样 ValueError，仅报错文案不同 |
| 3 | `auto_qb.rules.conditions.x__in_range__mutmut_12` | _in_range | maxsplit `1` → `2` | 等价 | 单区间 spec 拆分一致；多段 spec 仍是非法配置，两边都以 ValueError 收场，异常类型一致 |
| 4 | `auto_qb.rules.conditions.x__in_range__mutmut_15` | _in_range | 区间上界 `<=` → `<` | 真洞 | 上界被排除：`day_of_month: 1-31` 在 31 号、`day_of_week: 1-7` 在周日会误判 False；池内只测单值和 `3-8` 内点，唯一 `1-7` 用例（test_expr_eval 等价表）只在周日才失败，属日期巧合。**建议守阵**: 补 `_in_range(8, "3-8")`、`_in_range(31, "1-31")` 的上界断言 |
| 5 | `auto_qb.rules.conditions.xǁTagsConditionǁmatch__mutmut_17` | TagsCondition.match | `ok = False` → `ok = None` | 等价 | `ok` 只被 `if ok:` 读一次，None 与 False 同为假走同一分支，无其它读取点 |
| 6 | `auto_qb.rules.conditions.xǁCategoryConditionǁmatch__mutmut_3` | CategoryCondition.match | 空值回退 `""` → `"XXXX"` | 等价 | 仅当 category 为空/None 且 pattern 恰好命中哨兵字面量 `XXXX`（如 `regex:^X`）时才可区分，现实配置无此 pattern；精确匹配与通配正则两侧同结果 |
| 7 | `auto_qb.rules.conditions.xǁTrackersConditionǁmatch__mutmut_4` | TrackersCondition.match | 条件加 `or True`，else 变死支 | 真洞 | conf=None 时从「恒不匹配」变成 `None.name` 抛 AttributeError，与 TrackerGroupCondition 文档写明的「无 tracker_conf 恒不匹配，与 trackers 同语义」相悖；池内 trackers 用例全部带已匹配站点。**建议守阵**: 补 conf=None 用例，断言 `TrackersCondition("HHan").match(ctx) is False` 且不抛 AttributeError |
| 8 | `auto_qb.rules.conditions.xǁSeedtimeConditionǁmatch__mutmut_1` | SeedtimeCondition.match | 运算符 `self.op` → `None` | 真洞 | `utils.compare(None, ...)` 落到末尾 `return left == right`，比较符被静默丢弃成等值判断；池内 `">=1H"` 恰好因 seeding_time=3600 与阈值相等而通过。**建议守阵**: 同 ctx 补 `assert SeedtimeCondition(">1H").match(ctx) is False` |
| 9 | `auto_qb.rules.conditions.xǁExprConditionǁmatch__mutmut_8` | ExprCondition.match | 异常消息里 `type(value)` → `type(None)` | 等价 | 只改报错文案中的类型名，且该分支已被静态校验挡死（结果必为 bool），运行期不可达 |
| 10 | `auto_qb.rules.conditions.xǁFreespaceConditionǁ__init____mutmut_17` | FreespaceCondition.__init__ | `get("amount", "")` 默认值 → `None` | 等价 | amount 缺键时 `str(None)="None"` 与 `""` 都在 parse_compare 内抛 ValueError（仅消息不同），且 schema 将 amount 标为 required，缺键不可达 |
| 11 | `auto_qb.rules.conditions.xǁFreespaceConditionǁ__init____mutmut_19` | FreespaceCondition.__init__ | `get("amount", )` 省略默认值（等价 None） | 等价 | 与 mutmut_17 同形：缺键走 None，parse_compare 仍抛 ValueError，异常类型不变 |
| 12 | `auto_qb.rules.conditions.xǁFreespaceConditionǁ__init____mutmut_22` | FreespaceCondition.__init__ | 默认值 `""` → `"XXXX"` | 等价 | `"XXXX"` 与 `""` 都在 parse_compare 内抛 ValueError（一处正则不匹配、一处 parse_fsize 失败），类型一致仅文案不同 |

# 动作域加嵌套容器(choose)后, 遍历 actions 的检测/剔除判定不递归 = 校验放行而载入崩

> 摘要: 动作域加嵌套容器(choose)后, 遍历 actions 的检测/剔除判定不递归 = 校验放行而载入崩
> 触发: choose, 编排块, then, default, 嵌套, 递归, 遍历 actions, 退役伪动作, 校验放行, 载入崩
**Refs:**

### 给 actions 域新增嵌套容器后, 所有遍历 actions 的判定/改写仍只扫顶层

- **触发**: 动作列表(actions)域新增合法嵌套容器(现状: choose 编排块, W3-B)之后, 给既有的「遍历 actions 做检测/剔除/统计」逻辑补容器支持时——或者反过来, 容器落地时没回头排查全部遍历方。退役伪动作检测(`retired_control_keys_in`)与剔除(`disable_retired_rule_spec`)、前端 `cfgRuleRetiredKeys` 三处当初都只扫顶层, choose 的 then/default 里嵌同形项就漏(issue 26-11-03-1120)。同类高危点: 校验器对嵌套项的放行口径与遍历方的识别口径不一致(校验认伪动作键面合法, 载入层却不认 = 校验放行、消费崩)。
- **判别**: 校验零错误但规则载入抛 ConfigError(如「动作 ignore_next_action_error: ...」); 或 probe 直调检测函数对嵌套 spec 返回空/漏项。特征是**同一形状顶层能识别、嵌套不能** —— 拿嵌套 spec 分别在顶层与容器内各跑一遍检测即见分叉。
- **处置**: 遍历方抽共用递归(命中判定 `_is_retired_action` + 递归 `_iter_retired_action_checks` / 剔除 `_strip_retired_actions`, rules_mod.py 单点), 前端同口径递归(`cfgActionsContainRetired`); 递归只进合法容器, 异形分支原样透传交校验器报(不吞形状错误); 注意顶层短路面——多分支项在前会先命中, default 路径要单独探到(写测试时全覆盖)。
- **守阵**: `tests/test_rule_base_rule.py::test_load_retired_nested_in_choose_branches` + `test_retired_detection_strip_nested_edge_shapes`(后端检测/剔除嵌套+边界); node 语义电池 `_NODE_RETIRED_KEYS_PROBE` 含 nestedThen/nestedDefault/nestedClean 三形态(前端判定)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

# 5051 passed + 1 failed(上游坏链 26-11-04-0245) + 10 skipped(根 98.86%, test.full 146.82s) —— choose 嵌套退役伪动作修复(issue 26-11-03-1120)全量基线

> 摘要: 5051 passed + 1 failed(上游坏链 26-11-04-0245) + 10 skipped(根 98.86%, test.full 146.82s) —— choose 嵌套退役伪动作修复(issue 26-11-03-1120)全量基线
> 基线时间: 2026-11-04 05:05
**Refs:**

## 验收数字

- `commands run test.full`(2026-11-04 实测): TOTAL 23407 / 184 miss / 8006 branch / 157 partial, 覆盖率 98.86%; `1 failed, 5051 passed, 10 skipped in 146.82s (0:02:26)`。
- 失败口径: 唯一失败 `test_memory_bank_docs.py::test_doc_links_are_not_broken` 为**上游既有**(f16188e2 带入的 real-baselines 两切片坏链, 已入池 issue 26-11-04-0245, 与本改动面无关); 覆盖率跌破 99% 闸门同为上游面(上绿基线 26-11-04-0212 gtm-auth-body-drain: TOTAL 23325 / 99% / 5032 全绿, 之后合入的远端提交抬高 TOTAL 且带来未覆盖面)。
- 相关套件: `test_rule_base_rule.py` 41 passed(含本轮 2 条新用例); 相关 5 文件(含 choose/校验/on_error)160 passed, rules_mod 92%(缺口全在未触碰既有段); 前端 node 语义电池 12 项全绿(有 node 环境)。

## 本改动面

- `src/auto_qb/core/modules/rules_mod.py`: 退役检测/剔除抽共用递归单点 —— `_is_retired_action`(命中判定) + `_iter_retired_action_checks`(检测递归 choose 分支 then/块级 default) + `_strip_retired_actions`(剔除递归, choose 浅拷贝改写, 异形透传交校验器); `retired_control_keys_in`/`disable_retired_rule_spec` 改走递归 —— 修 issue 26-11-03-1120: 只扫顶层时嵌套伪动作通过校验但构造 Rule ConfigError, 载入硬失败。
- `src/auto_qb/webui/static/shared/config_rules.js`: 新增 `cfgActionsContainRetired`(同口径递归), `cfgRuleRetiredKeys` 改走 —— 嵌套伪动作的升级提示面(未启用徽标/卡脚)不再无声。
- `tests/test_rule_base_rule.py`: 新增 `test_load_retired_nested_in_choose_branches`(嵌套载入链全行为: 转未启用 + warning + then/default 两侧剔除 + 原配置保留)与 `test_retired_detection_strip_nested_edge_shapes`(边界形状: 非 dict/异形透传、多分支不短路、default 单测防顶层短路面); 头部「测试计划」docstring 同步两行。
- `tests/webui_dom_page_support.py`: `_NODE_RETIRED_KEYS_PROBE` 增 nestedThen/nestedDefault/nestedClean 三规则形态 + 3 断言; `tests/test_webui_static_dom_page_layout.py` 守阵下限 9→12 并同步 docstring。
- `memory-bank/rule-system/rules-and-triggers.md`「两键退役」段: 载入层/前端口径补嵌套递归说明; 新坑档 `memory-bank/pitfalls/backend/nested-container-recursion.md`(嵌套容器加入后遍历判定不递归家族)。
- `memory-bank/issues/26-11-03-1120-bug-rules-choose-nested-retired-control.html`: Open → In Progress → Done, 复验 + 修复后补充(实际修法/验证方式/测试数字)留痕; 另入池 `26-11-04-0245-docs-memory-baseline-broken-links.html`(上游坏链, 计划外不顺手修)。

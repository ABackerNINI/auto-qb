# 已实现 · 规则与配置

> 摘要: 摘要: 规则引擎、checking 动作、限速(单种 + 全局曲线)、fail-fast 配置校验的落地记录。
> 触发: 做过没有, 规则, 条件, 动作, checking, 限速, 配置校验

## 已实现 (✅, 有单测覆盖)

- 规则引擎: interval 触发 + 16 条件 + 12 动作 + execute_once/cooldown 去重 + 断点续跑 + stop_following_rules_if; 事件触发 (interval/on_* 四值 trigger + 事件分派引擎 + rule-event 断点续跑 + on_torrent_deleted 动作白名单 `print_torrent_details`, 2026-09-12 落地, 设计细节见下"事件触发(规则)规划")
- checking 动作: filelist/piecehashes/custom 三种参考判定 + full-checking (异步轮询) + skip-checking (导出→删除→重加, 同日去重+备份)
- tracker 单种限速 (奇数保护)
- 全局限速曲线: Traffic Monitor 数据源, DAY/MONTH/ND 聚合, 全程分档覆盖, 取最严 (2026-09 最近的大功能, commit ee88bc8..20481f3)
- fail-fast 全量配置校验 (2026-09-05): `config.validate_config` 聚合校验未知键/必填项/值格式/规则 spec/引用存在性; 留空(空串/None)走默认值; Rule 构造报错带规则名上下文; `load_*` 解析函数已剥离全部检查(先验证再解析, 解析假定配置正确)
- **⓪ 规则条件表达式化 (2026-09-20/21, W1 已提交 `93f1911`)**: 计划
  [docs/plans/26-09-20-2225-rule-conditions-expression-plan.html](../../docs/plans/26-09-20-2225-rule-conditions-expression-plan.html)
  (v3: 五条拍板口径 + §11 动作是否纳入的三档分析, L1 动作参数表达式记为候选排在 python 插件之后)。
  **W1 已入库 `93f1911`**(语法内核: errors/lexer/parser + 15 条测试, 未接规则系统)。
  **W2 已入库 `a1841e9`**(取值面 env + 求值 eval + 类型规则 types + `ExprCondition` + `RuleContext.expr_cache` +
  **`base.py` 出错即停规则 `(False, True)`** + 校验/schema/前端接线)。
  **W3 收尾(本轮)**: `sys.upload_today/download_today/upload_month`(Traffic Monitor dat)+ **配置期数据源门控**
  (`_expr_gate` → `_validate_rules(rules_config, errors, cfg)` → expr 单独分发, 门控跑在曲线段校验之前故须容忍
  结构非法的 `traffic_source`)、前端 expr 渲染为多行文本框、知识库回写(rule-system.md 新增「表达式条件」章 +
  出错即停语义、`modules.md` 加 `expr/` 行、`conventions.md` 立「新条件字段一律先进 env.py」)。
  实测 1062 → **1094 passed**(Windows; Linux 侧未同步重测, 已在 testing.md 标注)。
  已知坑: ①解析器"一层一运算符"判定必须在消费二元运算符后给 `used` 赋值, 否则退化成笼统报错;
  ②语义校验(types.py)与运行期求值(eval.py)的报错文案不同源, 测试按文案匹配时容易写错预期。

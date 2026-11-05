# 4347 passed, 10 skipped (coverage 99%: 21828 stmts, 164 miss, 7394 br, 127 pb) —— 规则引擎重设计 W1 两键退场收尾(webui 升级提示面 + 文档回写)

> 摘要: 规则引擎重设计 W1 两键退场收尾(webui 升级提示面 + 文档回写)
> 基线时间: 2026-11-01 03:23
**Refs:** memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html

## 验收数字

`commands run test.full` (176.8s, 2026-11-01 实测):

```text
TOTAL                                                21828    164   7394    127    99%
4347 passed, 10 skipped in 174.42s (0:02:54)
```

- 口径见 [baseline.md](../baseline.md)。

W1 期基线(plan 26-11-01-0106): 本期新增守阵 1 条(退役键升级提示面, 见下), 上基线其余增量来自 W1-A 前半段改写与同步。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/webui/static/shared/config_rules.js`: 伪动作判断 `isIgnoreNext` 退役, 换成两键退役检测单点 —— `cfgRuleRetiredKeys`(规则级 `stop_following_rules_if` + actions 域伪动作项, 口径与后端 `retired_control_keys_in` 同源)/ `cfgIsRetiredAction` / `cfgRuleRetiredHint`(话术对齐后端 `_warn_retired_rule`, 含等价新写法 `on_error: {policy: continue}`); webui 自测键名不依赖后端回写 config.yml。头注与规则级字段段注释如实化(死键话术移除)。
- `src/auto_qb/webui/static/shared/config_hub.js`: `hubPluginText` 对退役伪动作项显示「已退役: ignore_next_action_error」标记(判定在 meta 判空之前 —— 退役键不在插件索引, meta 恒空)。
- `src/auto_qb/webui/static/shared/tpl/settings.html`: 规则卡卡头新增「未启用·含退役键」徽标(`hb-badge warn`, 现有 dark 令牌族) + 卡脚升级提示(`cfgRuleRetiredHint` 单点)。
- `tests/test_webui_static_dom_page.py`: 新增 `test_frontend_retired_rule_keys_upgrade_surface` —— 旧判断/话术零残留 + 检测/提示单点各一处 + 模板接线齐全 + hubPluginText 判定次序 + 有 node 时真跑 9 项语义电池(四规则形态 × 检测/提示/动作行人话); 头部测试计划同步。
- `memory-bank/rule-system/rules-and-triggers.md`: process 语义按 verdict 契约回写(单值 `VERDICT_*` 表 + 引擎显式消费), stop 六档语义段换「两键退役」节(载入转未启用 + 每次载入 warning + webui 提示面), ActionResult 表第三列从「对 stop_following_rules_if 的影响」改为执行流影响, 伪动作段退役化。
- `docs/configuration.md`: 示例配置块删除两键两行, 动作表删除 `ignore_next_action_error` 行并补「已退役键」提示块, 「动作结果与错误处理」按新语义回写(failed 中断本条动作链 / on_error W2 / 退役键无停止忽略语义)。
- 键面守卫核对: `tests/fixtures/config_key_surface.txt` 无需改 —— `test_config_key_surface.py` + `test_config_schema.py` 51 条全绿(RULE_FIELDS 键面保留识别, W1-A 报告确认)。

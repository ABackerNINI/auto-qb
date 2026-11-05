# 4378 passed, 10 skipped (coverage 99%: 21977 stmts, 167 miss, 7468 br, 133 pb) —— 规则引擎重设计 W2 错误策略一等化收尾(on_error 三档 + retry=requeue)

> 摘要: 规则引擎重设计 W2 错误策略一等化收尾(on_error 三档 + retry=requeue)
> 基线时间: 2026-11-01 04:57
**Refs:** memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html

## 验收数字

`commands run test.full` (151.4s, 2026-11-01 实测):

```text
TOTAL                                                21977    167   7468    133    99%
4378 passed, 10 skipped in 149.58s (0:02:29)
```

- 口径见 [baseline.md](../baseline.md)。

W2 期基线(plan 26-11-01-0106): 错误策略一等化(on_error 三档) + retry=任务级 requeue + 条件异常 per-step 语义断言 + webui on_error 控件 + normalize 注入缺省 on_error(金标准快照重锚定)。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/config/schema/fields.py`: `ON_ERROR_POLICIES` 三档枚举 + `ON_ERROR_DEFAULTS`({policy: stop, retries: 3, backoff: 60}) 单点声明; `schema/__init__.py` payload 增 `on_error_policies`/`on_error_defaults` constants(webui 默认值同源)。
- `src/auto_qb/config/compat.py`: `ACTION_ENTRY_KEYS` 扩 `on_error`; `normalize_action_entry` 注入缺省 on_error(补齐缺省字段, 伪动作不注入) + 混合形(webui 动作卡写出的 `{动作键: 值, on_error: {...}}`)单点翻译; 幂等保持。
- `src/auto_qb/config/validation/rules.py`: `_validate_on_error`(dict/未知子键/policy 三档/retries>=0/backoff>0, 聚合报错) + 形错话术含 on_error; `validation/__init__` 重导出 `ON_ERROR_POLICIES`(枚举单源守卫)。
- `src/auto_qb/core/taskqueue.py`: `Task.attempt`(retry 计数, 重启随任务重建归零) + `Task.retry_delay`(requeue 推迟秒数); `_requeue` 消费 retry_delay —— >0 时按 backoff 推迟 `next_run` 且**保留断点**(从失败动作续跑, 不被 cooldown/execute_once 拦下), 否则原样 interval 重排; `add_task`/`reset` 清 retry_delay。
- `src/auto_qb/rules/base.py`: `VERDICT_RETRY` 常量; `Rule.action_on_error`(与 actions 对齐的 per-action 策略, 构造期解析, 非法值 ConfigError); `process` 动作失败/异常按三档分派 —— stop=break(现状)/continue=WARNING 后继续/retry=断点挂失败动作 + `task.retry_delay=backoff` 返回 RETRY(上限 retries, 耗尽按 stop; 无任务上下文退化 stop); 正常完成清断点 + attempt 归零(单点)。
- `src/auto_qb/core/modules/rules_mod.py`: `_handle_rule` 消费 RETRY → `task.attempt += 1` 返回 REQUEUE(队列收尾按 backoff 推迟); `_apply_event_rule`/`_handle_event_rule` 事件规则同语义(rule-event 任务带断点按 backoff 重入队, 续跑成功 FINISHED 消亡)。
- `src/auto_qb/webui/static/shared/config_rules.js`: `cfgOnError*` 方法族(默认值读 schema constants 同源; 非缺省才写树, 全缺省整键摘除; 写混合形) + `cfgPluginName`/`cfgSpecPath`/`cfgIsRetiredAction` 兼容规范形 `{type, params, on_error}`。
- `src/auto_qb/webui/static/shared/tpl/settings.html` + `console_hub.css`: 动作卡「失败策略」行(policy 三档下拉 + retry 档 retries/backoff 数字输入, 伪动作不渲染, `.hb-oe-row` 样式)。
- 测试: `test_actions.py` +11(on_error 三档 × 失败/异常矩阵 + 构造期拒非法), `test_modules_p5.py` +5(_handle_rule requeue/backoff/耗尽/无 sleep + 事件 requeue), `test_rule_base.py` +1(条件异常他规则照常 + 无「停止后续」话术), `test_rule_compat.py` 快照按「含缺省 on_error」口径重锚定 + 注入/混合形/校验边界新例, `test_config_schema.py` constants 守卫 + `ON_ERROR_POLICIES` 单源, `test_webui_static_dom_page.py` +1(on_error 控件守阵 + 13 项 node 语义电池); 各文件头「## 测试计划」同步。
- `memory-bank/rule-system/rules-and-triggers.md`: verdict 表补 `retry` 档, 动作失败三档分派回写, 新增「动作级错误策略 on_error」节(含去重键口径注记)。
- 键面守卫核对: `tests/fixtures/config_key_surface.txt` 无需改(on_error 为动作项子键, 不进顶层键面)。

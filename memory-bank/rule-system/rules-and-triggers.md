# 规则定义 · 触发 · process 语义

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。
> **代码**: `rules/base.py`(Rule / RuleContext / ActionResult)、`rules/conditions.py`、
> `rules/actions/`(动作包: basic / transfer / checking / full_checking / skip_checking)、`rules/registry.py`;
> **调度**: `mixins/rule_engine.py`; **配置加载 / 校验**: `config/loaders.py` + `config/validation/`(含 `rules_config`)。

> 摘要: 规则怎么定义与绑定、触发时机、`Rule.process()` 执行语义、去重语义与 ActionResult 四态。
> 触发: 规则定义, 绑定, 触发时机, trigger, process, execute_once, cooldown, ActionResult

## 规则的定义与绑定

- 配置中 `config` 段下**所有以 `_rules` 结尾的键**是规则集: `{规则集名: {规则名: spec}}` → Rule 全名 `{规则集名}.{规则名}` (如 `example_rules.rule1`)。
- 规则加载在 `run()` 中 (`_load_rules`), **不在构造时** (`--export-yaml` 模式不需要)。
- tracker 通过 `rules: ["@规则集", "@规则集.规则名"]` 引用规则 (`_resolve_refs` 按名称去重)。
- **规则是种子级任务**: 新种子被检测到时, 为其匹配 tracker 引用的每条规则各建一个 Task (kind=rule, interval=规则自身的 interval, 默认 0 → 归一化为每 tick)。未匹配 tracker 配置的种子不创建任何任务。
- 规则执行 = 该 Task 到期 → `_handle_rule` → 构造 `RuleContext(manager, client, config, hash, dry_run, task=task)` → `rule.process(ctx)`。

## 触发时机 (trigger)

| 触发 | 状态 | 说明 |
|------|------|------|
| `interval` | ✅ 已实现 | 默认; 规则任务按自身 interval 循环; `spec["interval"]` 解析为秒 |
| `on_torrent_added` | ✅ 已实现 | 事件触发 (一次性, 非周期); 新增种子匹配 tracker 后即时分派, 遇 checking 断点续跑 |
| `on_torrent_state_enum_changed` | ✅ 已实现 | 事件触发; 对比上一轮 `state_snapshot` 与当前状态枚举, 变化的种子触发 (名字与 `TorrentState` 枚举对齐) |
| `on_torrent_deleted` | ✅ 已实现 | 事件触发; 种子删除后无活现场, 仅 `print_torrent_details` 只读留档动作可用 (白名单拒绝需活种子的动作) |

`Rule.trigger` 从 `spec.get("trigger", "interval")` 解析 (base.py), 取值合法性由 config 校验保证 (见 05)。事件 trigger 的规则**不建周期任务** (`_create_rule_task` 返回 None): 由 `_refresh_torrents` 分派点即时执行 (同步), 遇 checking 时内部建 rule-event origin → 轮询子任务 → 断点续跑 (设计细节见 progress.md 事件触发规划)。

## Rule.process() 执行语义 (base.py, 核心函数)

```
process(ctx) -> (handled: bool, stop: bool)
```

1. **断点续跑**: 若 `ctx.task.has_breakpoint` (resume_index 非空) → 从断点动作继续, **跳过条件评估与去重** (用于 full-checking pending 后的恢复); 断点只在正常完成时消费清零, 异常路径由 taskqueue 收尾默认重置兜底 (下轮从头)。
2. **条件评估**: `matches()` = 所有条件 AND; **条件抛异常 → 出错即停规则** (2026-09-20 拍板): ERROR 级日志(含规则名/表达式/种子/原因, 同因 5 分钟节流) + 返回 `handled=False, stop=True` —— 判据都不可信时, 让后面的规则继续对这个种子做动作才是真风险。**故障优先于 `stop_following_rules_if`**(配 `never` 也停)。旧条件与 `expr` 同样适用。
3. **去重**: `_dedup_allowed` (见下节) 不通过 → 不执行。
4. **动作顺序执行**:
   - `ActionResult.ok` → `ok_action=True`, 记录日志继续。
   - `ActionResult.skip` → 不算失败, 继续 (如标签已存在)。
   - `ActionResult.fail` → `failed=True`; 若该动作未设 `ignore_error` → **break** 中断后续动作。
   - `ActionResult.pending` → 任务队列驱动时: 记录 `task.resume_index = i+1`, 返回 `(True, True)` 中断 (`_handle_rule` 检测断点返回 False 不重入; 校验轮询子任务完成后按情况重新入队); 无任务时视为成功继续。
5. **执行历史**: `ok_action` 且非 dry_run 且有动作 → `manager.record_execution(name, hash)` (幂等去重依据)。注意: 只要有任一动作成功就记录, 包括后续动作失败的场合 (断点续跑时 ok_action 初始为 True)。
6. **stop 计算** (`stop_following_rules_if`): `conditions-met`(默认, 匹配即停) / `always` → stop=True; `action-failed` 且 failed → True; `all-actions-succeed` 且 not failed → True; `conditions-not-met` → 不匹配时 stop=True; `never` → 永不停。
7. 返回 `handled`: `not result.is_skipped` (最后一个动作非 skipped); 空循环(断点后无动作)时返回 `ok_action`。

### 去重语义 (`execute_once` / `cooldown`)

- `execute_once: never`(默认) 且 `cooldown: 0S` → 每次条件满足都执行, **只适合幂等动作** (加/删标签、设分类)。
- 非幂等动作 (校验/开始/强制汇报/限速) 必须配 `execute_once: once/daily/hourly` 或 `cooldown`。
- `cooldown` 优先于 `execute_once` 粒度: 距上次执行成功不足 cooldown 则跳过。
- 记录键: `state["exec_history"]["{rule_name}:{hash}"] = {ts, date, hour}`; `daily` 按自然日切换 (与 upload_size_today 口径一致), `hourly` = 同日同小时。
- 另有**独立于规则去重的兜底**: `CheckAction` 跳检自带同日去重 (每规则每种子每天最多跳检一次)。

### ActionResult 四态

| 状态 | 含义 | 对 stop_following_rules_if=action-failed 的影响 |
|------|------|------|
| `success` | 动作执行成功 (dry-run 也返回 success) | 不算失败 |
| `skipped` | 条件不满足未执行 (标签已存在/已设置/状态不符/段未启用) | 不影响 |
| `failed` | API 非 200 / 抛异常 / 前置检查未通过 | 触发 |
| `pending` | 已提交等待异步完成 (仅 full-checking), 规则中断待恢复 | 中断执行流 |

`ignore_next_action_error: true` 是伪动作: Rule 构造时解析, 给**下一个**动作设 `ignore_error=True`, 失败不 break 继续执行。

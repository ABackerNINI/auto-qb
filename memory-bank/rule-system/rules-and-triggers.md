# 规则定义 · 触发 · process 语义

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。
> **代码**: `rules/base.py`(Rule / RuleContext / ActionResult)、`rules/conditions.py`、
> `rules/actions/`(动作包: basic / transfer / checking / full_checking / skip_checking)、`rules/registry.py`;
> **调度**: `mixins/rule_engine.py`; **配置加载 / 校验**: `config/loaders.py` + `config/validation/`(含 `rules_config`)。

> 摘要: 规则怎么定义与绑定、触发时机、`Rule.process()` 执行语义、去重语义与 ActionResult 四态。
> 触发: 规则定义, 绑定, 触发时机, trigger, process, execute_once, cooldown, ActionResult
**Refs:** memory-bank/reports/26-11-01-0057-report-rule-engine-redesign.html

## 规则的定义与绑定

- 配置中 `config` 段下**所有以 `_rules` 结尾的键**是规则集: `{规则集名: {规则名: spec}}` → Rule 全名 `{规则集名}.{规则名}` (如 `example_rules.rule1`)。
- 规则加载在 `run()` 中 (`_load_rules`), **不在构造时** (`--export-yaml` 模式不需要)。
- tracker 通过 `rules: ["@规则集", "@规则集.规则名"]` 引用规则 (`_resolve_refs` 按名称去重)。
- **规则是种子级任务**: 新种子被检测到时(torrents_added 相位), 为其匹配 tracker 引用的每条规则各建一个 Task (kind=rule, interval=规则自身的 interval, 默认 0 → 归一化为每 tick)。未匹配 tracker 配置的种子不创建任何任务。创建入口 `_create_torrent_tasks` 队列查重幂等(`TaskQueue.has_task`, 黄金法则 1) —— L2 重建后的 full_round 补建(issue 26-10-01-2147)与 added 管线共用该入口, 同一 (kind, name, hash) 恰一份。
- 规则执行 = 该 Task 到期 → `_handle_rule` → 构造 `RuleContext(manager, client, config, hash, dry_run, task=task)` → `rule.process(ctx)`。

## 触发时机 (trigger)

| 触发 | 状态 | 说明 |
|------|------|------|
| `interval` | ✅ 已实现 | 默认; 规则任务按自身 interval 循环; `spec["interval"]` 解析为秒 |
| `on_torrent_added` | ✅ 已实现 | 事件触发 (一次性, 非周期); 新增种子匹配 tracker 后即时分派, 遇 checking 断点续跑 |
| `on_torrent_state_enum_changed` | ✅ 已实现 | 事件触发; 对比上一轮 `state_snapshot` 与当前状态枚举, 变化的种子触发 (名字与 `TorrentState` 枚举对齐) |
| `on_torrent_deleted` | ✅ 已实现 | 事件触发; 种子删除后无活现场, 仅 `print_torrent_details` 只读留档动作可用 (白名单拒绝需活种子的动作) |
| `on_torrent_field_changed` | ✅ 已实现 | 事件触发 (计划 26-09-27-1438); 指定字段 (配套键 `watch_fields`, v1: tags/category) 发生**净变化**时触发: qB 增量 ∩ 监听字段后与持久化基线 (`state.field_snapshots`, state v3) 对比; 首见只落基线, 程序自写不自触发 (self-caused 值匹配抑制, 单点 store.update_torrent_fields), 重启停机期变化首轮补捕, cooldown/execute_once 复用 exec_history。全量 refresh 降级路径同判据(与基线对比, 非"全变") |

`Rule.trigger` 从 `spec.get("trigger", "interval")` 解析 (base.py), 取值合法性由 config 校验保证 (见 05)。事件 trigger 的规则**不建周期任务** (`_create_rule_task` 返回 None): 由 `_refresh_torrents` 分派点即时执行 (同步), 遇 checking 时内部建 rule-event origin → 轮询子任务 → 断点续跑 (设计细节见 progress.md 事件触发规划)。

## Rule.process() 执行语义 (base.py, 核心函数)

```
process(ctx) -> verdict: str   # 单值, 取值域 = base.py 模块级 VERDICT_* 常量
```

> **返回值契约已收口** (2026-11-01, plan 26-11-01-0106 W1): 旧的 `(handled, stop)` 二元组
> 中 `stop` 档自始无人消费(唯一调用点整体丢弃), `handled` 同样漂移 —— 现收口为引擎
> (`rules_mod._run_rule`)显式消费的单值 verdict: 每次执行 DEBUG 记结论供排障, W2 已按
> `error`/`retry` 档驱动 per-step 错误语义、W4 起进 per-run trace, 均以该返回值为单点入口。

| verdict | 含义 |
|---------|------|
| `no_match` | 条件不满足(含种子已删): 本轮未执行 |
| `error` | 条件求值出错: 本条规则本轮跳过, 不影响其它规则 |
| `deduped` | execute_once/cooldown 去重拦下 |
| `no_op` | 条件满足且未被去重, 但无动作产生效果(空动作表/全 skip) |
| `pending` | 动作等待异步完成: 断点已记录, 本轮中断待恢复 |
| `executed` | 本轮执行了动作(成功/失败均计; 续跑完成同) |
| `retry` | 动作失败且该动作 `on_error.policy: retry`(W2): 断点挂失败动作 + `task.retry_delay=backoff`, 引擎按任务级 requeue 处理(下次到期按 backoff 推迟, 从失败动作续跑, 不被去重拦下; 上限 retries, 耗尽按 stop 收场) |

1. **断点续跑**: 若 `ctx.task.resume_index` 非空 → 从断点动作继续, **跳过条件评估与去重** (用于 full-checking pending 后的恢复); 断点只在正常完成时消费清零, 异常路径由 taskqueue 收尾默认重置兜底 (下轮从头)。
2. **条件评估**: `matches()` = 所有条件 AND; **条件抛异常 → 本条规则本轮跳过** (2026-09-20 拍板的行为不变, W1 话术收口): ERROR 级日志(含规则名/表达式/种子/原因, 同因 5 分钟节流) + 返回 `VERDICT_ERROR` —— 每规则每种子独立任务模型里不存在「后续规则」链, 出错只影响本条本轮, 其它规则照常。旧条件与 `expr` 同样适用。
3. **去重**: `_dedup_allowed` (见下节) 不通过 → `VERDICT_DEDUPED`。
4. **动作顺序执行**:
   - `ActionResult.ok` → `ok_action=True`, 记录日志继续。
   - `ActionResult.skip` → 不算失败, 继续 (如标签已存在)。
   - `ActionResult.fail` (含动作内异常, 异常转 fail 不外抛) → 按 per-step `on_error` 三档分派 (W2 落地, plan G5):
     `stop`(缺省)= **break** 中断本条动作链; `continue` = 记 WARNING 后继续后续动作(替代退役布尔);
     `retry` = 断点挂失败动作 + `task.retry_delay=backoff`, 返回 `VERDICT_RETRY` 引擎 requeue
     (无 run 内 sleep, 黄金法则 3/5; 上限 retries, 耗尽按 stop)。无任务上下文(外部入口)retry 退化为 stop。
   - `ActionResult.pending` → 任务队列驱动时: 记录 `task.resume_index = i+1`, 返回 `VERDICT_PENDING` 中断 (`_handle_rule` 检测断点返回 False 不重入; 校验轮询子任务完成后按情况重新入队); 无任务时视为成功继续。
5. **执行历史**: `ok_action` 且非 dry_run 且有动作 → `manager.record_execution(name, hash)` (幂等去重依据)。注意: 只要有任一动作成功就记录, 包括后续动作失败的场合 (断点续跑时 ok_action 初始为 True)。
6. 返回: `VERDICT_EXECUTED`(本轮执行了非 skip 动作或任一成功) / `VERDICT_NO_OP`(条件满足但无动作产生效果)。

### 两键退役 (plan 26-11-01-0106 W1, D1 配置升级路线)

`stop_following_rules_if` 与伪动作 `ignore_next_action_error` 已退役, **引擎零消费**:

- **载入层** (`rules_mod.disable_retired_rule_spec`): 检测到含键规则 → 内存副本转**未启用** (enabled=false) + 剔除 actions 里的伪动作项; 配置原内容**不回写、原样保留**供改写; **每次载入**出 warning, 话术给出 `ignore_next_action_error` 的等价新写法 `on_error: {policy: continue}` (on_error 随 W2 落地)。
- **键面保留识别**: schema/RULE_FIELDS 与校验侧仍识别两键(用于升级检测), webui 规则卡对含键规则显示「未启用·含退役键」徽标与卡脚升级提示(检测单点 `cfgRuleRetiredKeys`, 与后端 `retired_control_keys_in` 同口径)。
- **绕过载入层**直接构造 Rule 遇伪动作按未知动作 ConfigError; 需「首中即停」→ `evaluation: first_match`
  (W4 枚举位已占坑, 本版本占位未实现, 见下节); 需「动作失败继续」→ `on_error: {policy: continue}` (W2)。

### 去重语义 (`execute_once` / `cooldown`)

- `execute_once: never`(默认) 且 `cooldown: 0S` → 每次条件满足都执行, **只适合幂等动作** (加/删标签、设分类)。
- 非幂等动作 (校验/开始/强制汇报/限速) 必须配 `execute_once: once/daily/hourly` 或 `cooldown`。
- `cooldown` 优先于 `execute_once` 粒度: 距上次执行成功不足 cooldown 则跳过。
- 记录键: `state["exec_history"]["{rule_name}:{hash}"] = {ts, date, hour}`; `daily` 按自然日切换, `hourly` = 同日同小时。
- 另有**独立于规则去重的兜底**: `CheckAction` 跳检自带同日去重 (每规则每种子每天最多跳检一次)。

### ActionResult 四态

| 状态 | 含义 | 对执行流的影响 |
|------|------|------|
| `success` | 动作执行成功 (dry-run 也返回 success) | 继续后续动作 |
| `skipped` | 条件不满足未执行 (标签已存在/已设置/状态不符/段未启用) | 不算失败, 继续 |
| `failed` | API 非 200 / 抛异常 / 前置检查未通过 | 按动作 `on_error` 三档分派(W2): stop=break 中断链(缺省)/ continue=继续后续动作 / retry=任务级 requeue(backoff 推迟, 上限 retries) |
| `pending` | 已提交等待异步完成 (仅 full-checking), 规则中断待恢复 | 记断点并返回 `VERDICT_PENDING` |

`ignore_next_action_error` 伪动作已退役 (plan 26-11-01-0106 W1): 载入识别后转未启用 + warning, 引擎不再消费; 等价新写法 `on_error: {policy: continue}` (W2 已落地)。见上节「两键退役」。

### 动作级错误策略 on_error (plan 26-11-01-0106 W2/G5)

动作规范形 `{type, params, on_error: {policy, retries, backoff}}`:

- `policy` 三档: `stop`(缺省 = 现行失败即止) / `continue` / `retry` (任务级 requeue, 见上)。
- 缺省值: `retries=3`, `backoff=60` 秒 (`schema/fields.py` `ON_ERROR_DEFAULTS` 单点); 载入链
  normalize 单点(`config/compat.py`)对每个动作注入缺省 on_error, 引擎/校验器只认规范化形态。
- retry 语义: attempt 计数挂 Task(断点续跑同款机制, 重启随任务重建归零); `_handle_rule` 返回
  REQUEUE 且队列收尾按 backoff 推迟 `next_run` 并保留断点(从失败动作续跑, 跳过条件与去重 ——
  重试若重走全流程会被 cooldown/execute_once 拦下)。事件规则同语义(rule-event 任务带断点按
  backoff 重入队, 续跑成功 FINISHED 消亡)。
- webui: 动作卡「失败策略」控件(config_rules.js `cfgOnError*` 方法族), 默认值与后端
  schema constants 同源; 全部为缺省值时不写树。
- exec_history 去重键口径不受影响: 键 = `规则名:hash`, hash = 种子 infohash, **不含 spec 序列化**。

### evaluation 求值模式枚举位 (plan 26-11-01-0106 W4/D4)

规则级可选键 `evaluation: all|first_match`, 默认 `all` = 现状(每轮完整求值条件并执行全部动作)。
`first_match` 是**占位键值, 本版本不实现**(D4 拍板): 校验放行先占坑(`schema/fields.py`
`EVALUATION_MODES` 单点), 引擎对非 `all` 值在 Rule 构造期显式 WARNING 后按 `all` 处理, 行为零变化
—— 后续实现「首中即停」时键面/校验零改动。webui 规则编辑下拉取自 rule_fields 的 options, 无额外前端键。

### per-run trace (plan 26-11-01-0106 W4/D5)

`Rule.process()` 每次调用装配一条 trace, 写入 `state["rule_traces"]["{规则名}:{hash}"]`
(维度 = 规则 x 种子 hash), 回答「这条规则这次为什么没跑/跑了什么」:

- 单条内容: `verdict` 结论 + `conditions` 逐叶子求值明细(顺序 = 实际求值顺序, 短路可见;
  choose 分支叶子带 `b` 分支号) + `actions` 每步结果(`st` 状态 / `disp` 处置 / `msg` 截断消息) +
  retry/断点信号(`retry: {attempt, delay}` / `resume: 断点索引`) + dry-run `dry` 标记;
  `ts`/`date` 排序字段由 state 层补齐。
- 截断口径(两层合围): 写入侧条件明细叶子条数 <= 32(超出保留头部 + `{"clip": 丢弃数}` 标记)、
  错误/消息串 <= 200 字符(`rules/base.py` `_TRACE_*`); state 层单条序列化 <= 2048 字节
  (`_TRACE_ENTRY_MAX_BYTES`, 超限降级为截断存根, 保留 verdict 与排序字段)。
- 体积红线: 每维度环形保留最近 **5** 条 + 保留期 **7** 天 + 全键面总条目上限 **300** 条
  (`core/state.py` `_TRACE_*` 常量, 固定值不开配置面) —— 与单条 2KiB 上限相乘, 体积硬上界
  600KiB < **1 MiB** 红线(压测用例 test_rule_trace; 实测数字见 kb.baseline)。
- prune 复用 `_prune_exec_history` 同款机制(`_evict_oldest` / `prune_day_keys` 单点, 不复制逻辑):
  日期淘汰按维度最新条目定维龄(维度内条目紧密成簇), 总量逐出走同一排序口径 —— 唯一差异是
  trace 无去重语义, 上限逐出当日记录也参与(`keep_today=False`)。
- trace 是排障辅助**无去重语义**, 与 exec_history(去重依据)同键口径互不迁移, 不动既有键面;
  写入在单一写线程内(process 只在主循环线程被调), 落盘语义随 `state_save_interval`;
  记录失败只 DEBUG, 不影响规则执行。保守默认: trace 默认开且轻量(无开关键, 常量兜底体积);
  条件不命中的运行同样落一条(这正是排障诉求), 未被调度的规则零开销。

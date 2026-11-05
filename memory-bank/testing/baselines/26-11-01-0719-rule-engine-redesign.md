# 4411 —— 规则引擎重设计 W4 per-run trace+evaluation 枚举位收尾

> 摘要: 规则引擎重设计 W4 per-run trace+evaluation 枚举位收尾
> 基线时间: 2026-11-01 07:19
**Refs:** memory-bank/plans/26-11-01-0106-plan-rule-engine-redesign.html

## 验收数字

`commands run test.full` (156.1s, 2026-11-01 实测):

```text
TOTAL                                                22325    196   7666    153    99%
4411 passed, 10 skipped in 154.05s (0:02:34)
```

- 口径见 [baseline.md](../baseline.md)。

W4 期基线(plan 26-11-01-0106): per-run trace(D5) + evaluation 枚举位(D4)收尾。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/rules/base.py`: W4 收口 —— `process` 加 per-run trace 包装(每次调用装配一条: verdict 结论 + 条件逐叶子求值明细 + 动作步结果 + retry/断点信号 + dry 标记, `_trace_record` 经 `ctx.state.record_rule_trace` 落账单点, 失败只 DEBUG); `_TRACE_MSG_MAX_CHARS`(200)/`_TRACE_COND_MAX_ITEMS`(32)写入侧截断常量与 `_trace_clip`/`_trace_cond_name`(哑条件缺 name 回退类名); `matches`/`_eval_condition_node`/`_pick_choose_branch` 加 trace 参数(与无 trace 路径共用同一套求值代码, 无第二语义分支); `evaluation` 引擎参数读取(D4 占位: 非 all 值构造期 WARNING 按 all 处理); 计划外修复: 叶子 trace 明细原来直取 `payload.name`, 内存直构哑条件(无 name 属性)会 AttributeError 连带 verdict 翻 error(W3 test_choose_engine_branch_dispatch 实红)。
- `src/auto_qb/core/state.py`: `rule_traces` 新键面 —— `record_rule_trace`(维度 = 规则名:hash, ts/date 补齐, 单条序列化字节量兜底 `_TRACE_ENTRY_MAX_BYTES`=2048 超限降级截断存根) + `_prune_rule_traces`(复用 `_prune_exec_history` 同款机制: `prune_day_keys` 维度保留期淘汰 + `_evict_oldest` 总量逐出, 唯一差异 keep_today=False —— trace 无去重语义当日也参与); 常量 `_TRACE_KEEP_PER_DIM`=5 / `_TRACE_KEEP_DAYS`=7 / `_TRACE_MAX_ENTRIES`=300(固定值不开配置面); 体积硬上界 300 x 2KiB = 600KiB < 1MiB 红线。
- `src/auto_qb/config/schema/fields.py` / `config/schema/rules.py` / `config/validation/rules.py`: `EVALUATION_MODES = ("all", "first_match")` 单点 + 规则级可选键 `evaluation`(RULE_FIELDS 枚举 Field, webui 下拉自 options 派生) + 校验放行 all|first_match、其它取值 fail-fast(D4 占坑口径 a)。
- 测试: `test_rule_trace.py`(新, 10 例: 条件不命中/条件异常/动作失败三个排障端到端例 + retry/断点信号 + 环形 + 单条字节兜底 + prune 保留期/总量 + 1MiB 红线压测(120 维度 x 300 条实测 305,907 字节) + 旧 state 载入回归(exec_history 去重判定不变) + dry-run 标记), `test_rule_base.py` +2(evaluation 缺省零告警 / first_match 占位 WARNING 按 all 处理), `test_config.py` +1(evaluation 枚举校验: 放行/拒绝/缺省); 三文件 docstring 测试计划同步。
- 文档: `memory-bank/rule-system/rules-and-triggers.md` 新增「evaluation 求值模式枚举位」与「per-run trace」两节(键面/截断口径/体积红线/prune 复用), 两键退役节的「等 W4」指针更新。

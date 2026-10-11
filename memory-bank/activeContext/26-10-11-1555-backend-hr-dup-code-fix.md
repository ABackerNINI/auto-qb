# hr 重复代码重构 · 低风险子集(5 条 refactor issue 认领与修复)

> 摘要: 用户「修复hr部分问题: 26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」。滚动报告 §14–§17(轮 11–14)对 hr 全包入池 9 条 refactor issue; 按用户拍板**只做低风险高收益子集(5 条)+ 保守口径(只做无行为变化的收口)**, 修完即置 `Done` 并补认领链: ① `hr-adapter-parse-boilerplate-dup`(`parse_header_counters` / `_standard_kwargs` / `query_param`); ② `hr-report-cli-boilerplate-dup`(`_gate_enabled_sites` + `_build_service` / `_scope_of` 收单点 / 删死件 `stamp_text_ts`); ③ `hr-lane-transition-boilerplate-dup`(`_settle_lane`); ④ `hr-warn-dedup-throttle-dup`(`_warn_once` / `_abort_wave` / `warn_gap_floor`); ⑤ `hr-model-serialize-helper-dup`(仅 `_as_int/_as_float` 收单点)。**零行为变化**(结构收口 + 删一处死件)。余 4 条跨包/低收益件按口径**暂缓**, 留 `Open`。全量 `test.full` **3112 passed + 4 skipped / 0 failed / 99%**(较上基线 3113 少 1 = 删掉的死件单测)。
> 最后活动: 2026-10-11 15:55

**Refs:** memory-bank/tasks/26-10-11-backend-hr-dup-code-fix.md

## 正在进行

- **hr 低风险子集重构已完成**(5 条 issue 置 `Done`): 见任务档案 [26-10-11-backend-hr-dup-code-fix](../tasks/26-10-11-backend-hr-dup-code-fix.md)。改动面仅 hr 包内 9 个文件 + 1 个测试文件; 跨包(webui/core/infra)零改动。
- **暂缓 4 条(留 Open, 等排期)**: `hr-store-recover-lock-family-dup`(建议与轮 18 infra 合并) / `hr-token-persist-convention-dup`(动 webui/server/common) / `hr-site-derive-convention-dup`(webui 半属轮 15) / `hr-thread-lifecycle-boilerplate-dup`(报告标收益低可暂缓)。

## 关键结论(供后续执行参考)

- **报告口径要复核, 不照抄**: 报告把档位处置三处判为 A 类「仅 detail 文案不同」, 实读发现 **fail_streak 推进与升级告警三处各不相同** —— 故 `_settle_lane` 用 `count_failure` 显式参数承载差异; 照报告的 `_fail_or_truncate(st, detail)` 抽会**静默改行为**(给预算截断也计连续失效)。
- **节流窗口(③)改道**: 4 处窗口值并不相同(service/worker `max(60, CHANNEL_SILENCE_WARN)` / server 6h 字面量 / core/traffic_store 3600s), 且 worker 侧有 16 条单测按模块常量打补丁 ⇒ 只抽**算法**(`warn_gap_floor`), 阈值仍留各模块常量, 既消重又不动补丁面。
- **删死件判据**: `stamp_text_ts` 全仓仅被自己的单测引用(生产侧零调用), 且与 `status.stamp_text` **同体异格式**(`%Y-%m-%d` vs `%m-%d`)无法「改复用」⇒ 按 issue 的「删除」侧执行(含删其单测)。
- **暂缓三条跨包件的边界**: token 口径(hr↔webui)、读坏恢复链(hr/store↔core/state, 且 hr/store 裸 `FileLock` 未走 infra/locking)、站点派生(hr↔webui routes/hr)都要动 hr 包外, 与「仅 hr / 低风险」口径不符, 留待各自的 infra / webui 轮次。

## 后续候选(未开工)

- hr 余 4 条暂缓 issue; `hr-lane-transition` 的 B 类子项(各档摘要串 service ↔ status, `(全深度)` vs `(全)`)需先钉文案差异点 + 回归保护再合。
- 重复代码审查主线: Phase 2 前端(轮 20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(轮 26)仍未开工(见 `26-10-10-backend-dup-code-audit`)。

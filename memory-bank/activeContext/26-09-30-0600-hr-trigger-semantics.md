# HR 触发语义重构: 已实施完毕 → 待提交

> 摘要: plans/26-09-30-0559 已于 2026-09-30 会话全量落地并验证 —— 判定层三方法重构
> (check_hr_condition 纯本地触发 / check_hr_satisfied 义务已了单点 / hr_managed 需管束单点)、
> 打标「放行短路+超额跳过+satisfied 分流」、展示三分(疑似辅种 warning 黄档, unknown/unverified
> 退役)、规则与表达式切换(tor.hr_condition_met 换绑 hr_managed + 新增 tor.hr_local_triggered)。
> test.full 1806 passed + 3 skipped / 91%, 真机 dry-run 零报错。
> **实施明细与决策归档**: [tasks/26-09-30-backend-hr-trigger-semantics](../tasks/26-09-30-backend-hr-trigger-semantics.md);
> 实测数字: [testing/baselines/26-09-30-0709](../testing/baselines/26-09-30-0709-hr-trigger-semantics.md)。
> 触发: 未核实, 本地不触发, 疑似辅种, warning, hr_managed, 全量纳入, 超额跳过, 触发语义,
> check_hr_condition, check_hr_satisfied, tor.hr_local_triggered, SRC_UNVERIFIED, 标签铺面
> 最后活动: 2026-09-30 07:09 (实施完毕, 改动未提交)

## 未完成

- **commit + push**: 全部改动在工作区未提交, 等用户显式「提交」。
- **迁移提示待用户自查**(已交付, 无法自动迁移): `tor.hr_condition_met` 与规则 `hr: condition-met`
  语义已变(→ 需管束); 存量规则若用它过滤「我下载的种子」, 手动迁移到 `tor.hr_local_triggered`。
- **范围外漂移待拍板是否入池**: `webui/static/shared/config_hub.js:93` 仍在文档化已废弃键
  `hr_check.unknown_policy`(26-09-28-1932 已删) —— config 编辑器提示文案过期。

## 指针

- [任务档案](../tasks/26-09-30-backend-hr-trigger-semantics.md) ·
  [修改计划 26-09-30-0559 (Done)](../plans/26-09-30-0559-plan-hr-trigger-semantics.html) ·
  [上游计划 26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html)

**Refs:** memory-bank/plans/26-09-30-0559-plan-hr-trigger-semantics.html

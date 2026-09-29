# HR 触发语义重构: 已入库 (87d154c) · config_hub 漂移已修

> 摘要: plans/26-09-30-0559 已全量落地并随 **87d154c** 入库 —— 判定层三方法重构
> (check_hr_condition 纯本地触发 / check_hr_satisfied 义务已了单点 / hr_managed 需管束单点)、
> 打标「放行短路+超额跳过+satisfied 分流」、展示三分(疑似辅种 warning 黄档, unknown/unverified
> 退役)、规则与表达式切换(tor.hr_condition_met 换绑 hr_managed + 新增 tor.hr_local_triggered)。
> **范围外漂移已修(2026-09-30 07:47 轮, 用户拍板直接修未入池)**: config_hub.js HUB_HELP 删
> `hr_check.unknown_policy` 死条目(26-09-28-1932 已删键, rel 引用的 verified_ttl 同批已删),
> 语义由 schema hr.py sites.enabled help 承载。
> **实施明细与决策归档**: [tasks/26-09-30-backend-hr-trigger-semantics](../tasks/26-09-30-backend-hr-trigger-semantics.md);
> 实测数字: [testing/baselines/26-09-30-0747](../testing/baselines/26-09-30-0747-webui-config-hub-drift.md)(1829 passed / 91%)。
> 触发: 未核实, 本地不触发, 疑似辅种, warning, hr_managed, 全量纳入, 超额跳过, 触发语义,
> check_hr_condition, check_hr_satisfied, tor.hr_local_triggered, SRC_UNVERIFIED, 标签铺面
> 最后活动: 2026-09-30 07:47 (漂移修复随本轮提交入库)

## 未完成

- **迁移提示待用户自查**(已交付, 无法自动迁移): `tor.hr_condition_met` 与规则 `hr: condition-met`
  语义已变(→ 需管束); 存量规则若用它过滤「我下载的种子」, 手动迁移到 `tor.hr_local_triggered`。

## 指针

- [任务档案](../tasks/26-09-30-backend-hr-trigger-semantics.md) ·
  [修改计划 26-09-30-0559 (Done)](../plans/26-09-30-0559-plan-hr-trigger-semantics.html) ·
  [上游计划 26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html)

**Refs:** memory-bank/plans/26-09-30-0559-plan-hr-trigger-semantics.html

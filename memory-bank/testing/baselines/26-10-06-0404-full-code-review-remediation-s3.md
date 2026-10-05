# 2646 —— Code Review 修复实施计划 S3 批 (竞态/守卫/回执族 ×4)

> 摘要: 计划 [26-10-06-0103-plan-full-code-review-remediation.html](../../plans/26-10-06-0103-plan-full-code-review-remediation.html)
> §05 S3 批 (webui/前端竞态与回执族 ×4: E-01 读侧快照 / F1-01 modal 身份戳 / E-03 空组回执 / F2-03 请求代际守卫)
> 实施完成后的全量测试基线。
> 基线时间: 2026-10-06 04:04

**Refs:** memory-bank/plans/26-10-06-0103-plan-full-code-review-remediation.html

- 分支: develop @ f9a6d6ab(批实施起点, `my-commit-flow.sync` 所得; 本切片实测于修复后工作树)
- 命令: `commands run test.full`(Windows, 双次采样 40.1s / 39.3s —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2646 passed + 4 skipped, 39.3~40.1s, 覆盖率 TOTAL 98%**
  (15723 语句 / 167 未覆盖 / 5444 分支 / 143 partial)
- 相对对照点 [26-10-06-0144](26-10-06-0144-full-code-review-remediation-s0-baseline.md) 与批起点 f9a6d6ab
  (26-10-06 本会话实测: 2642 passed + 4 skipped, 15718/167/5442/143, 98%):
  passed +4 恰为本批新增守阵 4 条, skipped 持平; 未覆盖 167 / partial 143 **逐字持平**;
  语句 +5 / 分支 +2 均为本批新增且**全覆盖**的修复代码(else 回执分支 / 快照语句 / 守卫语句)。
  判定口径备注: 拍板口径写的「99% 档」经 stash 回 f9a6d6ab 复测实为 **98%**(15718/167/5442/143),
  S3 前后同为 98% 档 —— 未覆盖 / partial 零回退, 无需再判漂移。
- 本批新增守阵 4 条已登记 [../guards.md](../guards.md)「S3 竞态/回执批次守阵」节, 均已做红验。

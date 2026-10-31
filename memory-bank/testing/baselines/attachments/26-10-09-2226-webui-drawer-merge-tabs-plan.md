# 2870 —— 面板页签合并计划(纯文档轮)基线

> 摘要: 本轮零 Python/前端代码触碰, 唯一产出 = `memory-bank/plans/26-10-09-2219-plan-webui-drawer-merge-tabs.html`(种子详情面板「常规+内容 / Tracker+用户」并排合并构想, 待拍板); 全量测试照 DoD 跑一遍记录实测, 收集面与上基线一致。
> 基线时间: 2026-10-09 22:26

## test.full 实测

- 分支: `develop`(HEAD `66d746ec`, 会话开工同步所得; 工作树仅新增计划文档与回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 28.4s —— 与上基线 25.2s 同区间噪声)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 收集面差异说明: 与上基线(2870+4)逐位一致 —— 本轮纯文档, 无任何收集面变化。
- 增量明细: `src/` 零改动; 知识库新增 2 份(计划文档 + 本切片)+ `plans/_index.md` 重建。

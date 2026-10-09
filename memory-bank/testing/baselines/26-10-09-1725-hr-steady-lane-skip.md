# 2870 —— HR 稳态期跳过 B/C 档取数可行性基线

> 摘要: 用户命题「HR 在线核实稳态时 B/C 页是否不用访问, 只访问 A 页, 分析可行性」。本轮产出可行性报告 `reports/26-10-09-1725-report-hr-steady-lane-skip.html`(单文件 HTML, `doc-topic=hr-steady-throttle`, 状态 `Done`)。**零 `src/` 与 `tests/` 改动** —— 纯文档轮(报告 + 任务档案 + 切片 + 索引重建)。
> 基线时间: 2026-10-09 17:29

**Refs:** memory-bank/activeContext/26-10-09-1725-hr-steady-lane-skip.md

## test.full 实测

- 分支: `develop`(HEAD `7f263d62`, 工作树含本轮报告 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- **收集面未变**: 本会话**零 `src/` 与 `tests/` 改动**; 会话开工 `my-commit-flow.sync` 从
  `df9bf989` 快进到 `7f263d62` 的提交只动 `webui` 与 `memory-bank`, 未触及测试收集面。
- 增量明细(本轮真正新增): `memory-bank/reports/26-10-09-1725-report-hr-steady-lane-skip.html`;
  回写 `memory-bank/tasks/26-10-09-backend-hr-steady-lane-skip.md`、
  `memory-bank/activeContext/26-10-09-1725-hr-steady-lane-skip.md`;
  重建 `memory-bank/reports/_index.md` / `memory-bank/tasks/_index.md`。

## 对照判据(后续沿用)

- 以本切片为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本报告**不产生代码改动**; 若后续按报告 §08 推进「稳态只看 A」(涉 `FETCH_LANES` 参与档收窄 +
  稳态定义收紧 + 缺席证明的全档假设), 数字变化在实施轮另立基线切片。

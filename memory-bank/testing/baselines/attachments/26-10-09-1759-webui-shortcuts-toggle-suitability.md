# 2870 —— WEBUI 快捷键「改为切换语义」适配性分析基线

> 摘要: 用户命题「分析快捷键中哪些适合改为切换类型(如 qB 流量图 —— 按一下打开、再按一下关闭), 写报告含适合/不适合表格」。本轮产出报告 `reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html`(单文件 HTML, `doc-topic=webui-keyboard-shortcuts`, 状态 `Done`)。**零 `src/` 与 `tests/` 改动** —— 纯文档轮(报告 + 任务档案追加 + 切片 + 索引重建)。
> 基线时间: 2026-10-09 17:59

**Refs:** memory-bank/activeContext/26-10-09-1759-webui-shortcuts-toggle-suitability.md

## test.full 实测

- 分支: `develop`(HEAD `7f263d62`, 工作树含本轮报告 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- **收集面未变**: 本会话**零 `src/` 与 `tests/` 改动**; 会话开工 `my-commit-flow.sync` 已同步 `7f263d62`, 未触及测试收集面 ⇒ 与上基线 [26-10-09-1725](../baselines/26-10-09-1725-hr-steady-lane-skip.md) 同值。
- 增量明细(本轮真正新增): `memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html`;
  追加 `memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md`;
  新增 `memory-bank/activeContext/26-10-09-1759-webui-shortcuts-toggle-suitability.md`;
  重建 `memory-bank/reports/_index.md`。`tests/` 与 `src/` **零改动** ⇒ pytest 收集面不变。

## 对照判据(后续沿用)

- 以本切片(2870+4 / 16567 / 167 / 5716 / 143)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本报告**不产生代码改动**; 若后续按报告推进「快捷键切换化」(涉 `shortcuts.js` 的 `run` 分支「已开 ⇒ 关」+ 浮层自切换放行白名单), 数字变化在实施轮另立基线切片。

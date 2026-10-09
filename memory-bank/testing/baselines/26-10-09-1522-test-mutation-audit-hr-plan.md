# 2850 —— hr 包变异测试审计执行计划(计划派生, 零代码改动)基线

> 摘要: 按 `mutation-testing` skill 的「派生计划」节, 为 `hr/` 包写分步执行计划(用户点名 hr), 落 `plans/26-10-09-1459-plan-mutation-hr.html`(单文件 HTML, `doc-topic=mutation-audit`, 状态 `Open` 待拍板)。本轮**零 `src/` 与 `tests/` 改动**(只新增 1 份计划 HTML + 回写同专题 activeContext 切片 / 任务档案 / 常驻锚), 相对上基线 [26-10-09-1435](../baselines/26-10-09-1435-webui-kbd-scroll-band-viewportrow.md) 的 pytest 面 passed **+1**(来自本会话开工 `sync` 快进拉入的提交, 非本轮), 覆盖四项逐位持平。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-09 15:22

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(HEAD `9926953b`, 工作树含本轮计划 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2850 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- 相对上基线 [26-10-09-1435](../baselines/26-10-09-1435-webui-kbd-scroll-band-viewportrow.md)
  (2849 passed + 4 skipped, 同 16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial):
  passed **+1** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- **+1 的归属**: 本会话**零 `tests/` 改动** —— 差额来自会话开工 `my-commit-flow.sync` 快进拉入的 3 笔提交(`667b3924` / `31413e51` / `9926953b`, 均改 `tests/`; 其中 `31413e51` 净增 1 个测试函数, 全仓 `def test_` 2593 → 2594)。
- 增量明细(本轮真正新增): `memory-bank/plans/26-10-09-1459-plan-mutation-hr.html`;
  回写 `memory-bank/activeContext/26-10-08-0642-test-mutation-audit.md`、
  `memory-bank/tasks/26-10-08-test-mutation-audit.md`、
  `memory-bank/issues/26-10-08-0642-test-mutation-audit-standing.html`(§07 行指针 + §08 台账行 + §09 日志);
  重建 `memory-bank/plans/_index.md`。`tests/` 与 `src/` **零改动** ⇒ pytest 收集面不变。

## 对照判据(后续沿用)

- 以本切片(2850+4 / 16567 / 169 / 5716 / 145)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本计划本身**不产生变异数字**(计划边界: 不在计划里实施); hr 首轮变异数 / 杀死率 / 耗时, 在拍板执行后另立 `mutants-hr` 基线切片(体例见 `mutation-testing` skill 的「记录口径」节)。

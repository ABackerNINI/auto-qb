# 2772 —— config 包变异测试审计执行计划(计划派生, 零代码改动)基线

> 摘要: 按 `mutation-testing` skill 的「派生计划」节, 为 `config/` 包写分步执行计划(用户点名 config), 落 `plans/26-10-08-0720-plan-mutation-config.html`(单文件 HTML, `doc-topic=mutation-audit`, 状态 `Open` 待拍板)。本轮**零 `src/` 与 `tests/` 改动**(只新增 1 份计划 HTML + 回写同专题 activeContext 切片与任务档案各一行), 相对上基线 [26-10-08-0647](26-10-08-0647-test-mutation-audit.md) 的 pytest 面 passed **±0**, 覆盖四项逐位持平。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 07:27

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本轮计划 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2772 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0647](26-10-08-0647-test-mutation-audit.md)
  (2772 passed + 4 skipped, 同 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: 新增 `memory-bank/plans/26-10-08-0720-plan-mutation-config.html`;
  回写 `memory-bank/activeContext/26-10-08-0642-test-mutation-audit.md` 与
  `memory-bank/tasks/26-10-08-test-mutation-audit.md`(各一行); 重建 `memory-bank/plans/_index.md`。
  `tests/` 与 `src/` **零改动** ⇒ pytest 收集面不变。

## 对照判据(后续沿用)

- 以本切片(2772+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本计划本身**不产生变异数字**(计划边界: 不在计划里实施); config 首轮变异数 / 杀死率 / 耗时, 在拍板执行后另立 `mutants-config` 基线切片(体例见 `mutation-testing` skill 的「记录口径」节)。

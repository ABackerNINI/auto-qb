# 2785 —— 变异审计指导 / 命令包 / 排期锚按首轮经验回灌 基线

> 摘要: 按 config 首轮(计划 26-10-08-0720)的实施经验回灌三处 —— ①**命令包**新增 `mutants.report`(存活/未覆盖变异导出成**带 diff 的清单** + 按状态/按模块汇总)与 `mutants.verify`(S4「全套件确认」的机械化: apply → 全套件 → 还原, 可续跑), 配套新脚本 `scripts/mutants_dump.py`; ②**指导 skill** 补「流程约束 9–11」(池覆盖函数面 / S4 收窄候选 / 复跑带新守阵用 `--no-refresh`)与两条记录纪律(切片之外不手抄 `N passed` / 新 issue 填 `doc-refs`); ③**常驻排期锚**标注 config 进度、补 R1/R2 与回灌日志; 证据报告新增 §14。**零 `src/`、零 `tests/` 改动**(新包脚本不以 `test_` 前缀命名, 不进 pytest 收集面)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 09:20

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本专题全部新增件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2785 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16476 语句 / 164 未覆盖 / 5694 分支 / 148 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0902](26-10-08-0902-mutants-config.md)(2782 passed + 4 skipped, 同 16476 / 164 / 5694 / 148):
  passed **+3** —— 来自本轮同步进来的**远端提交**(`ship.commit` 的 rebase 带进来的 4 笔), 非本专题改动;
  语句 · 未覆盖 · 分支 · partial **±0**。

## 包内脚本测试实测(本轮有新包脚本)

- 命令: `commands run test.pkg`
- **实测**: **154 passed, 0 failed, 68.58s**
- 说明: 新增的 `mutants_dump.py` 与改动后的 `mutants.py` 都不以 `test_` 前缀命名 ⇒ 不被 pytest 收集(与 `.commands/dev/scripts/*.py` 同款);
  154 与上基线同批一致, 说明新脚本**没有**破坏包脚本测试面。

## 新 task 的 smoke 实测(工具面, 非本仓库测试基线)

- `commands run mutants.report -- --target '**/config/*.py'`: 导出 **827** 条带 diff 的清单(16.4s), 汇总按状态(`survived` 772 / `no tests` 55)与按模块打点 —— 与首轮 `mutants.run` 复跑的「存活 + no tests」一致。
- `commands run mutants.verify -- --ids-file <2 条>`: **14s/条**, KILLED / SURVIVED 判定与预期一致(在镜像里用已有守阵跑)。
- `commands run doc.drift` / `kb.check` / `doc.caps`: 全过(0 处手抄命令 / 认领链闭环 / 无新增 cap 债务)。

## 对照判据(后续沿用)

- 后续每轮 `mutants.report` 的条数应等于同轮 `mutants.run` 的「存活 + `no tests`」; 不等先核池 / glob 是否漂移。
- `test.pkg` 以 **154** 为对照点: 往 `.commands/mutants/scripts/` 加脚本不应改变它(除非加了 `test_` 前缀的文件)。
- `test.full` 以本切片(2785 + 4 / 16476 / 164 / 5694 / 148)为对照点。

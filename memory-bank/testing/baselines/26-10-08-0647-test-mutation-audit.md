# 2772 —— 变异测试审计基建(指导 / mutants 包 / 常驻锚)基线

> 摘要: 把报告 26-10-08-0231 落成可复用流程: 指导 skill `mutation-testing` + 命令包 `.commands/mutants`(setup/run/gremlins/status) + 常驻排期锚 issue + 方法论坑档。本轮**零 Python 产品代码改动**(只加 skill / 命令包 / memory-bank 文档), 但新增的 `.commands/mutants/scripts/*.py` 落进 `test.pkg` 收集面 ⇒ 相对上基线 [26-10-08-0559](26-10-08-0559-webui-qb-traffic-yaxis-annotation.md) 的 pytest 面 passed **±0**(新增的是非 test_ 前缀脚本, 不被收集), 包内脚本测试 **154 passed**(上基线同批 154)。覆盖率口径逐位持平。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 06:47

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本专题全部新增件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2772 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 同树复测区间: **54.75s ~ 70.29s**(回写前 / 提交前各一次, passed 与覆盖四项**逐位相同**;
  单次数字不单独作基准 —— 口径见 testing/baseline.md「必须带区间」)。
- 相对上基线 [26-10-08-0559](26-10-08-0559-webui-qb-traffic-yaxis-annotation.md)
  (2772 passed + 4 skipped, 同 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: 新增 `.agents/skills/mutation-testing/SKILL.md`(指导)、`.commands/mutants/`(config + 2 脚本 + references)、
  1 条 issue、1 条坑档、1 份任务档案、1 张 activeContext 切片。`tests/` 与 `src/` **零改动** ⇒ pytest 收集面不变。

## 包内脚本测试实测(本轮新包进面)

- 命令: `commands run test.pkg`
- **实测**: **154 passed, 0 failed, 115.35s**
- 说明: `.commands/mutants/scripts/mutants.py` 与 `set_conf.py` 不以 `test_` 前缀命名 ⇒ 不被 pytest 收集(与 `.commands/dev/scripts/*.py` 同款);
  本轮 154 与上基线同批一致, 说明新包**没有**破坏包脚本测试面。

## 变异测试面实测(本轮为工具/流程验证, 非本仓库测试基线)

> 数字来自可行性报告同款目标, 用于确认 `mutants` 包的端到端可用性; **不是**本仓库的测试基线, 只记口径锚点。

- **mutmut(WSL, `infra/versioning.py` + `tests/test_versioning.py`)**: 155 变异 / 21.6s / 杀 147(存活 7 + 超时 1), 8.25 mut/s。
- **pytest-gremlins(Windows, 同目标)**: 25 变异 / 11.9s / 杀 25(100%)。
- 与报告 §07 的 155 变异一致 ⇒ 密度复核通过; 两个工具的杀死率差异源于算子面(与报告 §07 结论同向)。

## 对照判据(后续沿用)

- 以本切片(2772+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 变异面锚点: 同目标同池复跑应得同数(变异执行是确定性的); 换池则数字不可比 —— 池必须随轮次一起记。

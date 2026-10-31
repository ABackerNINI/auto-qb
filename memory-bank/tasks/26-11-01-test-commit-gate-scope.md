# 26-11-01-test-commit-gate-scope — 提交闸门按改动收窄优化实施

**Status:** In Progress
**Added:** 2026-11-01
**Updated:** 2026-11-01
**Summary:** 提交闸门按改动收窄优化实施
**Topics:** test-commit-gate-scope
**Refs:** memory-bank/plans/26-11-01-0434-plan-commit-gate-scope.html

## 原始请求

1. 「提交闸门优化：部分提交闸门不需要全检，只需要检查改动过的文件，先列一个表，哪些闸门适合优化」——盘点后用户确认方向。
2. 「test.quick暂不改动，先写成计划文档」——计划 26-11-01-0434 落盘（D1 拍板）。
3. 「将check_context_caps纳入计划，拍板按推荐，开始实施」——方案 D 纳入（D5），D2–D4 按推荐拍板，本轮实施 S1–S5。

## 思考过程与决策

取舍与机检约束（详见计划 §01/§03）：改动清单单点 = 预检 `changed_files()`，闸门脚本不自查 git（复跑阶段树已净，自查语义就错）；守阵 `test_commit_gate_covers_kb_check` 逐字钉 `--check` run 清单 ⇒ 十连检并行只能落引擎层 `run_gates`，不许合 wrapper；`<changed:GLOB>` 无匹配即整条 run 静默跳过（方案 A/C/D 的自选机制）；展开语义已核实（`_glob_match` 的 `**/` 跨目录、脚本类 task 的 `--` 参数直尾）。拍板：D1 test.quick 不动；D2 并发池=4；D3 drift 全量触发面=config.toml+引擎 scripts；D4 ≥2 包整跑+引擎必整跑；D5 caps 债务改改动面（硬规定逐字不动）。

## 实现计划

计划 `memory-bank/plans/26-11-01-0434-plan-commit-gate-scope.html` §04：S1 方案 A（drift 收窄）→ S2 方案 B（run_gates 并发化）→ S3 方案 C（test.pkg.scoped）→ S4 方案 D（caps 收窄）→ S5 收尾（复测回写 + test.full 基线）。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| S1 | 方案 A：drift --files/--full + 闸门三条 run + tests/test_command_drift.py | Done(2026-11-01) |
| S2 | 方案 B：run_gates 并发化 + test_pipeline 并发语义用例 | Done(2026-11-01) |
| S3 | 方案 C：test.pkg.scoped wrapper + 闸门两条 run + 包内自测 | Done(2026-11-01) |
| S4 | 方案 D：caps --files + check_caps(only) + 闸门三条 run + 用例 | Done(2026-11-01) |
| S5 | 收尾：dev.fmt / kb.check / test.pkg / test.quick / test.full + 基线切片 / 复测回写 | Done(2026-11-01) |

## 进度日志

### R0 · 立档 (2026-11-01)

立档即开工：计划 R1 版（方案 D 已入）为实施蓝本；本档随各步完成在子任务状态表置 Done 并由 kb.wrap 追加进度行。

- 2026-11-01 05:41 提交闸门收窄优化 S1-S5 全部落地: 方案A drift收窄/方案B run_gates并发化/方案C test.pkg.scoped/方案D caps收窄; 复测数字见计划 R2 与基线切片 26-11-01-0541; 回归 test.pkg 206 过 + test.quick/test.full 4355 过 + 10 跳(覆盖率 99%)

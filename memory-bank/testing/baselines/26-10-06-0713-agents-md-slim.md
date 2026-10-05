# 2676 —— AGENTS.md 精简后的复验 (@ 0e278f12)

> 摘要: 本轮只改 `AGENTS.md` —— 纯格式精简 (去 markdown 链接 / 去多余空格与符号), **零 Python 与测试改动**。
> 两条相邻采样与上一条基线 `26-10-06-0619`(2676 + 4 / 16021 / 166 / 5472 / 144)的 passed、语句总数、
> 分支总数**全同**, 只差**未覆盖 166 → 163** 与 **partial 144 → 143**; 差值不来自代码 (见下), 落在
> xdist 并行调度的覆盖率抖动上, **不作回归结论**。
> 基线时间: 2026-10-06 07:13

**Refs:** memory-bank/activeContext/26-10-06-0720-agents-md-slim.md, memory-bank/pitfalls/testing/parallel-run.md

- 分支: develop @ **0e278f12**(工作树只有本轮 `AGENTS.md` 一处改动未提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows, 两次相邻采样一致)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**;
  单次 **46.61s**(引擎计时 48.2s)。语句 16021 / 未覆盖 163 / 分支 5472 / partial 143。
- 相对上一条基线 `26-10-06-0619`(2676 + 4 / 16021 / 166 / 5472 / 144 / 75.06s):
  passed ±0 · 语句 ±0 · 分支总数 ±0 · **未覆盖 -3** · **partial -1**; 耗时 75.06s → 46.61s
  (前后相差 ~1h, 机器负载不同; 单次数字不作基准)。
- **差值归因**: `2be3fe79..0e278f12` 三个提交经 `git diff --name-only` 核验**只碰 `e2e/smoke.spec.mjs`
  与 `memory-bank/` 文档**, 零 `src/` 零 `tests/` 改动; 本轮改动也只在 `AGENTS.md`, 不进 `--cov=src`
  统计 ⇒ 两侧都排除 ⇒ 落在并行调度抖动 (口径见 `pitfalls/testing/parallel-run.md`, 该条原记 ±1、
  本次实测到 ±3)。
- **为什么单记一条**: 目的不是报新数字, 而是把"同一份代码连跑两次稳定、跨会话却有 ±3 行未覆盖"这个
  **抖动区间**留档 —— 后续看到目的层数字微变时, 先对照本条再判断是不是真回归。

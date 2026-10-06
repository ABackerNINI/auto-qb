# 基线切片 26-10-07-0508 — kb.nav 类型列移除空值占位符

> 摘要: 用户报上轮 (26-10-07-0458) 补的类型列「空值不利于对齐」—— 非 issue 行显 `·`
> 占位符反而破坏观感, 移除占位符, 空 typec 单元格渲染为空。台账行模板 ledgerCells 一处
> 三元分支的 fallback 由 `"·"` 改 `""`, 「链」列的 `·` 占位不在本次范围保持不动。
> 基线时间: 2026-10-07 05:08

- 分支: develop @ 644663be (+ 本轮未提交改动: nav_page.html / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2705 passed + 4 skipped, 34.38s, 覆盖率 TOTAL 99%**
  (16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **39 passed**。列序守阵只钉栏序不钉占位符, 无需改断言。
- 相对上基线 (26-10-07-0458: 2705 passed + 4 skipped / 99% / 36.10s): passed/覆盖全同,
  纯前端单文件一行改, 无新增测试; 耗时差 (36.10s→34.38s) 为采样噪声。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(ledgerCells typec 一行)。
  src/ 与测试零改动。

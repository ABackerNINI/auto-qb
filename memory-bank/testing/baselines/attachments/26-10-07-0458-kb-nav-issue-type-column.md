# 基线切片 26-10-07-0458 — kb.nav 台账补 issue 类型列

> 摘要: 用户报 kb.nav 台账缺 issue 类型列 (bug/perf/...) —— 数据层 `issue-type` 字段早已
> enrich (nav_data.py), 侧栏筛选器也按类型过滤, 只有台账表格没展示。台账在「状态」与「标题」
> 之间加「类型」列 (表头 + 共用行模板 ledgerCells + 列序守阵同步), issue 行显类型 chip,
> 非 issue 行显 `·`; 置顶专区/隐藏区共用 ledgerCells 自动跟随。
> 基线时间: 2026-10-07 04:58

- 分支: develop @ 23a59f3a (+ 本轮未提交改动: nav_page.html / tests/test_kb_nav.py / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2705 passed + 4 skipped, 36.10s, 覆盖率 TOTAL 99%**
  (16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial; 门槛 98% 达标)
- 靶向 (tests/test_kb_nav.py): **39 passed**。列序守阵
  test_ledger_status_column_between_form_and_title 断言更新为含 `typec`
  (idx/stamp/formc/statc/typec/title-cell/topic/refs), 表头与行模板两头同步改。
- 相对上基线 (26-10-07-0438: 2689 passed + 4 skipped / 99% / 41.75s): passed **+16**
  —— 本轮守阵为改写既有断言不增条数, 增量全部来自会话开工快进 (329a843c→23a59f3a)
  拉入的远端区间; skip 集合不变 (Windows 侧 4 条 POSIX 专属)。
- 改动面: `.agents/skills/memory-bank/scripts/nav_page.html`(表头 + ledgerCells 各一行,
  栏序注释同步) + tests/test_kb_nav.py(守阵断言与头部清单措辞)。src/ 零改动。

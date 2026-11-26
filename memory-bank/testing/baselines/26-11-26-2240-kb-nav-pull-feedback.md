# 7038 passed + 6 skipped —— kb.nav 拉取按钮结果可区分全量基线

> 摘要: kb.nav 拉取按钮结果可区分全量基线
> 基线时间: 2026-11-26 22:40

## 验收数字

`commands run test.full` 实测(2026-11-26 22:38, Windows, rc=0, 136.90s, 工作树批态 = 三态反馈修复全改动未提交):

```
TOTAL                                                31424    108  11198     93    99%
7038 passed, 6 skipped, 1 warning in 136.90s (0:02:16)
```

与上基线(26-11-26-0606, 7036P/6S, TOTAL 31424/108/11198/94)对账: passed +2 (新增 `test_pull_ff_only_up_to_date_kind` 与 `test_do_pull_three_states_distinct` 两条守阵); skipped 持平; 语句/分支/覆盖 11198/93/99% —— 分支统计 94→93 属覆盖率口径波动, 无用例删除。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_server.py`: `pull_ff_only` 返回 (ok, message, kind) 三元组, 三成功态各一 kind + 失败(含 diverged)统一 error; `/api/pull` 响应加 kind 字段 (仅加字段, ok/message 语义不变)。
- `.agents/skills/memory-bank/scripts/nav_page.html`: `doPull` 按 kind 切三态短文案 (已是最新/已更新/本地领先), 3000ms 复位, 连点先清旧 timer; `.pullbtn` 加 `white-space:nowrap`、`#pullLabel` 加 `min-width:4em` 防换行抖动。
- `tests/test_kb_nav_server.py`: 既有拉取测试解包改三元组并钉 kind; 新增齐平态单测; endpoint 契约测试覆盖四 kind。
- `tests/test_kb_nav_shell.py`: 静态守阵扩三态文案映射、3000ms、clearTimeout、nowrap/min-width。
- `tests/test_kb_nav_interaction.py`: node 回放真实 doPull 验三态文案 + error 回落 + 连点清旧 timer; 三份测试文件 docstring 清单同步。
- 计划 `memory-bank/plans/26-11-26-2221-plan-kb-nav-pull-feedback.html` + 档案 `memory-bank/tasks/26-11-26-memory-bank-kb-nav-pull-feedback.md` 立档。

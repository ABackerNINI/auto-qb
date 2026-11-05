# 5375 passed + 10 skipped —— 全量基线: kb.nav 搜索被排除匹配提示行落地

> 摘要: 5375 passed + 10 skipped —— 全量基线: kb.nav 搜索被排除匹配提示行落地
> 基线时间: 2026-11-06 03:22
**Refs:** memory-bank/tasks/26-11-06-memory-bank-kb-nav-search-ghint.md

## 验收数字

```
TOTAL                                                24483     77   8396     40    99%
Required test coverage of 99.5% reached. Total coverage: 99.62%
5375 passed, 10 skipped, 1 warning in 157.08s (0:02:37)
```

- 口径: `commands run test.full`(coverage on); 1 warning 为既有告警面, 与本改动无关。
- 评审修复后复跑: 5375 passed / 10 skipped / TOTAL 99.62% 逐位不变 (128.11s), 上表数字仍为事实源。
- 环境注记: 本 clone trampoline 定点重装(pytest/yapf/coverage, 见 venv-trampoline-clone-copy 复发行)后首条本机基线。

## 本改动面

- 壳 `.agents/skills/memory-bank/scripts/nav_page.html`: 新增 `ghintExclDims`/`ghintData`(按活动视图算被勾选/隐藏排除的搜索匹配) + `renderGhint` 渲染单点 + `#ghint`/`.ghint` CSS(悬浮搜索框下方) + 三视图 render 末尾挂载 + `wire()` 点击委托勾回。
- 守阵: `tests/test_kb_nav_interaction.py` +2(`test_search_excluded_matches_hint_computed` node 回放十场景 / `test_search_excluded_hint_ui_wiring` 接线单点), 测试计划清单 +2 行; `tests/kb_nav_support.py` +`_shell_fn`(花括号配平抽函数体)。
- 真机验证: 静态导出页真实 DATA(1113 件)回放 26-09-30-0052 三兄弟场景 + Playwright 渲染冒烟(提示浮现/文案/点组名勾回/主表回行)。

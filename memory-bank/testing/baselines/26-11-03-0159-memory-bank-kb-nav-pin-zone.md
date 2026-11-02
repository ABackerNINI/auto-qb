# 4908 passed + 10 skipped(根, 99%) —— kb.nav 置顶区折叠 + 置顶条目单击对齐主区

> 摘要: kb.nav 置顶区折叠 + 置顶条目单击对齐主区
> 基线时间: 2026-11-03 01:59

## 验收数字

`commands run test.full` 实测(根套件):

- 汇总行: `4908 passed, 10 skipped, 3 warnings in 165.17s (0:02:45)`(任务总耗时 168.1s)
- TOTAL 表: `22531 语句 / 152 未覆盖 / 7732 分支 / 134 部分覆盖 / 99%`
- 口径: 同步到 `0c60bcf0` 后在本轮工作树上热跑; 合流时远端 `63f47598`(R2 测试大文件 move-only 拆分) 已把
  `tests/test_kb_nav.py` 拆为 `test_kb_nav_data/interaction/server/shell` 四桶, 两条新守阵随之落到
  `test_kb_nav_interaction.py`, 复跑定向 14 passed, 条目计数不变。

## 首跑红及处置

- 无: 首跑即全绿, 无需处置。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: 置顶区标题行新增折叠按钮 `#pzToggle`(原生 button + `aria-expanded` / `aria-controls="pzBody"`, 折叠态落 `mb-nav-pin-collapsed`, 只藏表格主体, 标题行与展开入口始终可见); 置顶条目单击改走与主表共用的 `openRowDetail()` 单点(同一 `renderDrawer` / 同 `sel` 高亮), 退役原 `window.open` 原文路径; Esc 行选择退档改扫 `#v-ledger` 下全部 `tr.sel` 覆盖双区。
- `tests/test_kb_nav_interaction.py`: 新增 `test_pin_zone_collapse_toggle` 与 `test_pin_row_click_opens_drawer_via_shared_path`(node 回放页内真实 JS; 合流时随远端 R2 拆分从原 `tests/test_kb_nav.py` 迁入本桶), 并同步头部「## 测试计划」清单。
- `memory-bank/progress/implemented-tooling.md`: 追加置顶区交互落地记录。
- 数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动; 未改产品 `src/`、`config.yml`、`auto-qb-data/`。

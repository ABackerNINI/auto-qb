# 4901 passed + 10 skipped(根, 99%) —— kb.nav 搜索支持文件名/相对路径修复后全量基线

> 摘要: kb.nav 搜索支持文件名/相对路径修复后全量基线(搜索单点 + 守阵)
> 基线时间: 2026-11-03 00:51

## 验收数字

`commands run test.full` 实测(根套件):

- 汇总行: `4901 passed, 10 skipped, 3 warnings in 229.74s (0:03:49)`
- TOTAL 表: `22531 语句 / 152 未覆盖 / 7732 分支 / 134 部分覆盖 / 99%`
- 口径: 同步后的 `61d04ca3` 工作树上热跑, 含本轮全部改动; 新增守阵 `test_search_matches_file_name_and_relative_path` 计入 passed; 首跑绿, 无红处置。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: 新增 `navSearchText()` / `navSearchQuery()` 搜索单点 (标题 / 专题 / issue 摘要 + link + memory-bank/link), 台账 `aFiltered` / 控制台 `renderChannels` / 卡片墙 `cVisibleItems` 统一消费; 正文不入索引, 大小写与反斜杠归一; 顶部 docstring 同步。另修提交闸门暴露的 vnu 规范错误: 台账外层 `section` 改 `div` (`main` 不得作 `section` 后代), `check_html --vnu` 复跑零 error。
- `tests/test_kb_nav.py`: 新增 `test_search_matches_file_name_and_relative_path` (node 回放页内真实 JS 单点, 覆盖 basename / 两种相对路径 / 大小写 / 反斜杠 / 原字段 / 无关词), 同步头部「## 测试计划」清单。
- `memory-bank/progress/implemented-tooling.md`: 追加本轮落地记录。
- 数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动; 未改产品 `src/`、`config.yml`、`auto-qb-data/`。


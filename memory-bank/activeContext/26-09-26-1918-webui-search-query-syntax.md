# WEBUI 搜索强化: 行级语义 + 真机回访双修已全绿, 随本提交入库

> 摘要: 调研报告(26-09-26-1918)→ 用户拍板**行级** → 已实施: `views.py` `_parse_query`(websearch 宽容词法: 词 AND / `-排除` / `"短语"`) + `search_torrents` 行级匹配(候选行=名字或单文件, 行含全部正词且无负词即命中; 仅负词返回空 + negative_only)+ 前端两主题 placeholder/空态提示。真机回访双修: ①种子页 `filteredTorrents` 旧整句客户端过滤 → 同语法升级(filters.js `_parseSearchQuery`/`_searchNorm`/`_torrentTextMatch` 单点, 与 views.py 行为级对账守阵, 对账抓到 `_` 折叠漂移); ②清除钮有焦点点不动 → 两主题 `@mousedown.prevent`。+7 测试累计, 全量 **1680 passed + 1 skipped / 0 failed**(TOTAL 91%, 基线切片 26-09-26-2121)。档案 `tasks/26-09-26-webui-search-query-syntax.md`。
> 最后活动: 2026-09-26 21:21

## 已完成

- 根因定位 + 实测复现(第一问); 六系调研 + 报告落盘(第二问); 行级拍板
- 实施: 后端 views.py(解析器 + 行级匹配 + docstring)/ 测试 +6 与测试计划同步 / 前端 app.js + atlas/prism 成对
- 真机回访双修: 种子页客户端查询语法补齐(含 JS/Python 对账守阵)+ 清除钮 mousedown.prevent 两主题成对
- 闸门: 全量 1680 绿(TOTAL 91%, 基线 26-09-26-2121); progress/implemented-webui 置顶条目已更新; 坑 `pitfalls/web-ui/search-syntax.md`

## 待办

- ✅ **随本提交入库**: 代码 5 文件(filters.js / hr.js / 两主题 index.html / test_web.py)+ 知识库回写件随车
- 真机复测: 种子页「恶女 10」「恶女 10 -DV」与仅负词空态; 分组/追剧视图回归; 清除钮焦点态清除

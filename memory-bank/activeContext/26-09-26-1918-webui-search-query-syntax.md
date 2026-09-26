# WEBUI 搜索强化: 行级语义已实施全绿 — 已入库 05d223a

> 摘要: 调研报告(26-09-26-1918)→ 用户拍板**行级** → 已实施: `views.py` `_parse_query`(websearch 宽容词法: 词 AND / `-排除` / `"短语"`) + `search_torrents` 行级匹配(候选行=名字或单文件, 行含全部正词且无负词即命中; 仅负词返回空 + negative_only)+ 前端两主题 placeholder/空态提示。+6 测试, 全量 **1679 passed + 1 skipped / 0 failed**(TOTAL 91%, 基线切片 26-09-26-2030)。「恶女 10」失配已修复并有回归钉。档案 `tasks/26-09-26-webui-search-query-syntax.md`。
> 最后活动: 2026-09-26 20:30

## 已完成

- 根因定位 + 实测复现(第一问); 六系调研 + 报告落盘(第二问); 行级拍板
- 实施: 后端 views.py(解析器 + 行级匹配 + docstring)/ 测试 +6 与测试计划同步 / 前端 app.js + atlas/prism 成对
- 闸门: test_web 169 绿 → 全量 1679 绿(TOTAL 91%); progress/implemented-webui 置顶回写

## 待办

- ✅ **提交入库已完成** `05d223a`: 代码 3 文件 + 模板 2 文件 + 知识库回写件随车; 当初标注的
  「并发会话的 `tasks/26-09-26-webui-long-path-open.md` 仍 untracked, 应随车入库」也已一并带上,
  `tasks/_index.md` / `_doc-map.md` 同批重建。
- 真机走查(需真实 qB): 双主题实测「恶女 10」「恶女 10 -DV」与仅负词空态提示

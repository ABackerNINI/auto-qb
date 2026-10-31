# 1679 passed + 1 skipped / 0 failed —— 搜索查询语法强化落地(词 AND + -排除 + "短语", 行级语义)

> 摘要: 按用户拍板(行级)实施 webui 搜索强化: views.py `_parse_query` + `search_torrents` 行级重写 + 前端两主题提示文案;
> +6 测试全绿; 无配置/状态/依赖变化
> 基线时间: 2026-09-26 20:30
> 档案: 26-09-26-webui-search-query-syntax

- **测试增量**: +6 条(`test_web.py`,「## 测试计划」docstring 同步)——
  `test_parse_query_tokens`(词法: 正负词/短语/孤立-/未闭合引号/纯标点/--dv/web-dl/词中引号)·
  `test_search_torrents_row_level_and`(行级 AND 钉**跨行不命中**——与种子级的分界)·
  `test_search_torrents_negative_term`(负词按行作废, 合集包非 DV 行不误杀; 排除短语)·
  `test_search_torrents_phrase`(短语连续子串词序敏感, 与 terms-AND 的区分用例)·
  `test_search_torrents_regression_envnv10`(报障回归: 「恶女 10」命中单文件发布物, -ubweb 可排除)·
  `test_search_torrents_negative_only_empty`(仅负词/空查询返回空 + negative_only, 不投递构建)。
- **既有测试口径更新**(设计变更所致, 非回归): `test_search_torrents_separator_normalized` 的
  `dragon cat` 断言由「序敏感判空」改为「行级 AND 命中」——旧断言钉的正是本次有意放宽的子串序敏感口径。
- **首跑 2 红均为测试预期写错**(实现行为正确): `dragon cat` 漏算 HB 下划线文件行; 负词用例顺序
  忽略「名字轮先于文件轮」([HC,HB] / [HA,HC,HB]), 修正后绿。
- **前端**: `searchNegativeOnly` 状态单点(app.js 三处)+ atlas/prism placeholder 与 5 处空态成对;
  模板守阵(静态断言类)不受影响。

TOTAL 91%(11298 语句 / 816 未覆盖 / 3724 分支 / 332 partial; views.py 97%, 新增解析/匹配路径全覆盖;
并行 test.full 19.0–19.6s, 串行采样 20.6s; 覆盖率口径见 [../baseline.md](../baseline.md))。

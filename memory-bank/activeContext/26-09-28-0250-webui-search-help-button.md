# 搜索框语法帮助入口(框内幽灵「?」+ 锚定浮卡, 方案A)实施

> 摘要: 用户令给 WEBUI 搜索框加「高级用法」帮助入口, 先出 3 版交互式提案供挑选(计划 26-09-28-0201), 拍板**方案A**(框内幽灵「?」+ 锚定浮卡)并简化占位符为「搜索种子或文件名...」。实施: `topbar.html` 挂钮与浮卡(四行语法 + 容错提示, 示例行点击回填即搜); 挂件样式入三 UI 共用层 `shared/console_hub.css`(mono 用 `var(--font-mono, 内联栈)` longhand —— 星图无该令牌), 各皮肤只留差异(atlas pill 钮圆)与 input 右内边距 52px; `searchHelpOpen` 状态 + `view.js` `toggleSearchHelp`/`searchHelpFill`(回填即搜 + 焦点还输入框), 收起走点空白/Esc(lifecycle 既有链)+ goView/openSettings 导航收起; 新守阵 `test_frontend_search_help_wiring`。实机验证: dev.harness 桩 + Playwright 三套 UI 全交互通过, 示例 `"web dl"` 经真实后端命中 35/60 辅种。索引收口: 新计划文档触 doc-map 撞 index-auto cap → 按 cap-counting「两个出口」①改渲染口径(计划/报告展示戳截到日期, 零信息损失)。test.full 1815 passed + 3 skipped, TOTAL 91%(基线 26-09-28-0250); 档案 tasks/26-09-26-webui-search-query-syntax.md(追加)。
> 最后活动: 2026-09-28 02:50

## 正在进行

- 等待用户说「提交」—— 收尾回写已全部落盘(档案追加/切片/基线/progress 条目/坑档复发/索引重建)。

## 关键决策

- 方案A 胜出理由: 顶栏是全 UI 最挤的一条, 帮助入口收进输入框内部是唯一零占位解; 「语法是输入框的属性」语义最准; B 的示例回填已内含在 A 的浮卡里。
- 挂件样式放 `shared/console_hub.css` 而非各皮肤 components.css: atlas 该文件已贴 700 行单文件上限(26-09-28 实测 697+), 共用层不计各自 cap; 皮肤差异(atlas pill)以 1 行覆盖留各自文件。
- `searchHelpFill` 走 `doSearch()` 即搜不等 400ms 防抖: 示例是完整查询, 回填即见结果才是「教」的完成态。
- 帮助浮卡是纯展示层: 语法语义单点仍在 `views.py::_parse_query`, 模板注释钉了「改语法先改后端注释再同步浮卡」的顺序。

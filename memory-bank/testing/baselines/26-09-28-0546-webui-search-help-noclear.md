# 1818 passed / 3 skipped —— 搜索框「?」无清空钮时右移补位

> 摘要: 用户反馈承接 9dc7a1b(语法帮助入口): 空框时「?」钉在 27px, 右侧留清除钮的死空位。topbar.html 帮助钮加 `'no-clear': !searchQuery` 条件类(searchQuery 为空 ⇔ 清除钮不渲染, 同源条件); 共用层 console_hub.css 新增 `.search-help.no-clear { right: 6px }`(即清除钮的位), 有词时保持 27px 让位, transition 补 `right` 与聚焦展宽同拍。守阵 test_frontend_search_help_wiring 同步锁定(模板绑定 + 共用层规则)。冒烟(自建桩挂真静态 UI + Playwright 量测): 空框距右缘 6px / 有词 27px 且与 x 间隙 1px / 点 x 清空回 6px, 星图 + 棱镜双皮通过。
> 基线时间: 2026-09-28 05:46
> 档案: tasks/26-09-26-webui-search-query-syntax.md(追加)

- 纯前端共用层一处 + 模板一个条件类 + 守阵两条断言, 用例总数不变: 1818 passed / 3 skipped / 0 failed。
- TOTAL **91%**(12512 语句 / 914 未覆盖 / 4204 分支 / 388 partial), 耗时 20.0s。

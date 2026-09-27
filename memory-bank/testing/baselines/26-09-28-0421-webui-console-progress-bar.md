# 1818 passed / 3 skipped —— 控制台皮肤进度条消失修复(CSS 注释提前终止)

> 摘要: 用户实报 console 皮肤种子页进度列无进度条、辅种页明细表进度条异常。根因单一: console/css/components.css 进度条注释文字 `(s-*/member-row 族)` 里的 `*/` 把注释提前终止, 浏览器错误恢复把紧跟的 `.m-progress { display: flex }` 整条静默吞掉, `.bar` 保持 inline 宽度 0 —— 辅种组行/明细行/种子页行三处进度条全部只剩百分比没有条。修复 = 注释内加空格; 守阵 = `test_web.py::_scan_css_comments`(浏览器同款注释语义扫描, 非 vendor 全部 CSS, 代码态孤立 `*/` 即红; red 验证: 回退该行测试即红)。全量静态 CSS 扫描(含 HEAD 全部历史 css)确认仅此一处。
> 基线时间: 2026-09-28 04:21
> 档案: (无 —— 未达立档阈值, 切片 26-09-28-0421-webui-console-progress-bar)

- 新增守阵 1 个(`_scan_css_comments`, 挂进 `test_frontend_static_bundle_health`), 用例总数不变(守阵挂在既有用例内): 1818 passed / 3 skipped。
- 视觉验证用 `scripts/ui_harness.py`(合成 400 种子 / 200 组, 端口 8231)+ Playwright 实测: 种子页 / 辅种页组行 / 展开明细行 `.m-progress` display:flex、bar 宽 ~37-43px、LED 填充渐变在 —— 三处全恢复。
- TOTAL **91%**(12512 语句 / 914 未覆盖 / 4204 分支 / 387 partial), 耗时 20.1s。

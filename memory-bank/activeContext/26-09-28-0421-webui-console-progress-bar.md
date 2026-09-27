# 控制台皮肤进度条消失修复

> 摘要: 用户实报控制台(console 皮肤)两处症状 —— 种子页进度列无进度条、辅种页明细表进度条异常。根因单一: console/css/components.css 进度条注释文字里写了 `(s-*/member-row 族)`, 注释体内的 `*/` 把注释提前终止, 尾巴成代码态垃圾, 浏览器错误恢复把紧跟的 `.m-progress { display: flex }` 整条吞掉(静默, 无报错), `.bar` 保持 inline 宽度 0 —— 三处表格(辅种组行/明细行/种子页行)进度条全部只剩百分比没有条。修复 = 注释加空格(`s-* / member-row`); 守阵 = test_web.py 新增 `_scan_css_comments`(浏览器同款注释语义, 代码态孤立 `*/` 即红, red 验证过)。全部静态 CSS(含 HEAD 全量)扫描确认仅此一处。
> 最后活动: 2026-09-28 04:21

## 已完成
- 修复 console/css/components.css:367 注释(s-*/member-row → s-* / member-row), `.m-progress` flex 布局恢复。
- 守阵 `_scan_css_comments` 挂进 `test_frontend_static_bundle_health`(非 vendor 全部 .css), 测试计划清单同步。
- 用 ui_harness.py(端口 8231, 合成 400 种子/200 组)+ Playwright 实渲染验证: 种子页/辅种页组行/展开明细行进度条均恢复(LED 分段条 7px + mono 百分比)。
- 新坑立档 pitfalls/web-ui/css-comment-terminator.md, kb.index 已重建。

## 测试
- test.full 1818 passed / 3 skipped(基线切片 26-09-28-0421); test.quick 同数。

## 下一步
- 等用户说「提交」(commit + push 一次走完)。

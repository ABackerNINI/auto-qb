# CSS 注释体内的 `*/` 会吞掉紧跟的规则

> 摘要: CSS 注释以第一个 `*/` 结束 —— 注释文字里再出现 `*/`(如 `s-*/member-row`)会把注释提前砍断, 尾巴落成代码态垃圾, 浏览器按错误恢复把**紧跟的那条规则整条静默丢弃**, 无任何报错。
> 触发: 写 CSS 注释, 注释里出现 星号斜杠, 进度条不显示, 样式规则不生效, display 没生效, 控制台皮肤, m-progress

### 注释文字里的 `*/` = 提前终止 + 其后规则整条消失(静默)

- **触发**: 在 CSS 注释里写含 `*` 的通配表述后紧跟 `/`(2026-09-28 实测: console/css/components.css 进度条注释写了 `(s-*/member-row 族)`, 想表达"两种行类名族")。
- **判别**: 症状 = 某条规则"看起来在文件里却不生效"(实测: `.m-progress { display: flex }` 被吞, 三处表格进度条只剩百分比没有条, `.bar` 保持 inline 宽度 0)。**静态看文件永远"没问题"** —— 必须看浏览器实际消费的规则: DevTools Styles 面板缺这条, 或 `document.styleSheets` 遍历 cssRules 找不到该选择器。花括号配平、`_scan_css_blocks` 均查不出(注释态里括号本就不计)。
- **处置**: 注释文字里避开 `*/` 序列(写成 `s-* / member-row` 加空格); 同理慎用 `/*` 出现在注释文字里。守阵 `test_frontend_static_bundle_health::_scan_css_comments`(浏览器同款注释语义扫描, 代码态出现孤立 `*/` 即红)。
- **守阵**: tests/test_web.py `_scan_css_comments`(red 验证: 回退 components.css 该行测试即红)。

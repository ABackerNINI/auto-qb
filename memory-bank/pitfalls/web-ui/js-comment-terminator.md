# JS 注释体内的 `*/` 会提前终止块注释, node --check 仍绿、运行时才炸

> 摘要: JS 块注释以第一个 `*/` 结束 —— 注释文字里再出现 `*/`(如 `Key*/Digit*` 想表达通配前缀)会把注释提前砍断, 尾巴落成**代码态**; 与 CSS 版(见 css-comment-terminator)不同, 尾巴常能被解析成正则字面量等合法语法, `node --check` 与全部静态守阵都绿, 直到页面首次执行该文件才抛 ReferenceError 整站白屏。
> 触发: 写 JS 注释, 注释里出现 星号斜杠, Digit is not defined, pageerror 白屏, node check 全绿, shortcuts.js

### 注释文字里的 `*/` = 提前终止 + 尾巴变代码(运行时才炸)

- **触发**: 在块注释里写含 `*` 的通配表述后紧跟 `/`(2026-09-30 实测: shortcuts.js 注释写了 `Key*/Digit*/Numpad* 取后缀`, `*/` 把注释砍断, 尾巴 `Digit*/Numpad* ...` 被解析成 `Digit * /正则` 的合法表达式序列)。
- **判别**: 症状 = `node --check` 全绿 + pytest 静态守阵全绿, 但浏览器 `pageerror: <名字> is not defined` 且整站白屏(boot.js 按清单序加载, 首个炸点即停)。静态查不出是因为尾巴**恰好合法** —— 语法层无错误可报。
- **处置**: 注释文字里避开 `*/` 序列(写成 `Key / Digit / Numpad 前缀` 加空格); 浏览器探针(ui_harness + pageerror 监听)是唯一可靠防线, 改完 JS 至少开一次页面。
- **关联**: CSS 同族坑与守阵见 [css-comment-terminator.md](css-comment-terminator.md); 本条暂无静态守阵(可靠区分"注释文字里的 */"需完整 JS 词法分析, 收益不抵复杂度, 以探针兜底)。

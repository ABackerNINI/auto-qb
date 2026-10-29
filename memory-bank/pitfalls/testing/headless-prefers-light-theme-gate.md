# 无头浏览器跟随系统亮色会误触亮主题排除前缀, 让暗主题规则整体假性失效

> 摘要: 无头浏览器跟随系统亮色会误触亮主题排除前缀, 让暗主题规则整体假性失效
> 触发: 无头, Playwright, 亮主题, prefers-color-scheme, 诊断假象, theme 排除

### 无头浏览器跟随系统亮色 → 亮主题类规则被排除前缀整体关掉, 诊断假性「改动没生效」

- **触发**: 用 Playwright/无头 Chromium 诊断带「亮主题排除」口径的 CSS（如主表行语言 row_lang.css 的 `:not([data-theme="frost"]):not([data-theme="golden"])` 前缀）。无头环境默认跟随系统 `prefers-color-scheme`，宿主机是亮色 ⇒ theme.js 落 frost ⇒ 暗主题规则组整体不生效。
- **判别**: 诊断时发现新规则「完全没命中」（如 ::before content:none、计算样式里找不到预期值），但代码与加载序都对。先看 `getComputedStyle(document.documentElement).getPropertyValue('--bg')` 或 `data-theme` 属性——落 frost/golden 即中招。本例：诊断「左条不可见」时白跑一轮几何取证，实际规则整体被前缀关闭。
- **处置**: 诊断脚本先钉主题再测：`localStorage['autoqb.ui.theme']='ocean'` 后 reload（theme.js 的存储键），或 `page.emulateMedia({ colorScheme: 'dark' })`。e2e 断言涉及暗主题专属规则时同样要显式钉暗。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

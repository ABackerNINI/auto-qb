# 自绘 .aq-tip 只摘最内层 title, 嵌套带 title 的组叠出双 tooltip

> 摘要: 全局自绘 tooltip(.aq-tip, 调度单点 shared/ui_feedback.js)靠「hover 时摘掉 title 属性」压制原生气泡。当模板出现**嵌套带 title 结构**(外层组 + 内层按钮/条目各有 title, 典型 = statusbar.html 的 .sb-today > .sb-hist / .sb-stats > .sb-item / .sb-speed > .sb-spd), 旧实现只摘 `closest("[title]")` 命中的最内层 —— 浏览器原生气泡随即**借外层祖先的 title 还魂**(hover 链上最内层无 title 时浏览器向上回溯), 350ms 自绘浮层 + ~1s 原生气泡同时可见 = 用户报「状态栏多数元素有两个 tooltip」。另一同源触发: 状态栏 `:title` 绑定随轮询逐轮变值, Vue patch 在悬浮期间把 title 重写回去而 mouseover 不会再触发, 原生气泡同样复活。
> 触发: 双 tooltip, 两个 tooltip, 状态栏 tooltip, aq-tip, 嵌套 title, 祖先 title, 原生气泡还魂, Vue 重写 title, 轮询 title 变值, statusbar, sb-today, sb-stats, sb-speed, ui_feedback
> 收口: 2026-10-04, 修 ui_feedback.js enter()/hide()(祖先链整条摘 + 250ms 周期补摘), test.full 2423 passed

## 条目

- **触发**: ①模板里外层组与内层元素**同时**挂 title/`:title`(状态栏三组全中, 全局 tooltip 接入是「模板零改动」设计, 对嵌套无感知); ②悬浮期间 `:title` 绑定值变化(speed / 今日流量随主轮询逐轮变), Vue 写回 title 后无人再摘。两者都表现为自绘浮层之上又浮出原生气泡(两段文字不同, 原生的那个是祖先组/新值的文案)。
- **判别**: ①grep 模板里同一条 hover 链上有 ≥2 个带 title 的嵌套节点(`grep -n "title=" .../tpl/statusbar.html` 外层 span 与内层 button 同现即命中); ②`ui_feedback.js` 的 enter() 只有单点摘除(`target.__aqTitle = ...; target.removeAttribute("title")`)而无祖先链循环; ③真机 hover 内层按钮 >1s 出现两个气泡(一个 .aq-tip 样式、一个原生样式)。
- **处置**: enter() 从锚点沿 `parentElement` 向上**整条祖先链**摘 title(链存入 `chain` 数组, hide() 单点还原; 还原时 `__aqTitle` 已是补摘捕获的最新值, Vue 写回的新值不丢); 另设 `REARM_MS=250` 周期补摘定时器, 悬浮期间把 Vue 重写回去的 title 再摘掉(周期短于原生气泡 ~1s 起跳延迟, 重写值撑不到弹出), 离开/失焦/滚动/点击统一在 hide() 清定时器并还原整链。
- **守阵**: 无静态断言(行为层逻辑, 字符串钉不住语义); 复验方式 = 状态栏 hover 历史入口/qB 图标/速度组 >2s 只见一个自绘气泡, 移开后 title 恢复(DevTools 现查属性回来)。
- **复发**: 0

# 自绘 .aq-tip 靠「hover 时摘 title」压原生气泡, 摘不干净叠出双 tooltip

> 摘要: 全局自绘 tooltip(.aq-tip, 调度单点 shared/ui_feedback.js)若靠「hover 时摘掉 title 属性 + 离开还原」压制原生气泡, 摘除时机永远追不上 title 的出现时机: ①模板**嵌套带 title 结构**(statusbar.html 的 .sb-today > .sb-hist / .sb-stats > .sb-item / .sb-speed > .sb-spd), 只摘最内层时原生气泡借外层祖先 title 还魂; ②`:title` 绑定随轮询逐轮变值, Vue patch 在悬浮期间把 title 重写回去而 mouseover 不再触发; ③**Vue 把指针下节点整个换掉时指针不动、mouseover 根本不触发**, 新节点带着 title 直接入 DOM(前两轮修法对此全盲) —— 三条路都让原生气泡复活, 与 350ms 自绘浮层叠出双 tooltip(用户先后报「多数元素有两个」与「两 tooltip 交替出现」)。定稿修法(2026-10-04 三轮): **原生 tooltip 断供式** —— MutationObserver 盯全文档, title 属性任何时刻出现即刻迁进 data-aq-tip 并删掉原属性, DOM 里不存在 title, 原生气泡从根上无从弹出。
> 触发: 双 tooltip, 两个 tooltip, 状态栏 tooltip, aq-tip, 嵌套 title, 祖先 title, 原生气泡还魂, Vue 重写 title, 轮询 title 变值, 节点替换 title, statusbar, sb-today, sb-stats, sb-speed, ui_feedback
> 收口: 2026-10-04 三轮定稿, ui_feedback.js 改 MutationObserver 断供式(title→data-aq-tip 单向迁移, 不还原), test.full 2423 passed + Playwright 冒烟 8 项全过

## 条目

- **触发**: ①模板里外层组与内层元素**同时**挂 title/`:title`(状态栏三组全中, 全局 tooltip 接入是「模板零改动」设计, 对嵌套无感知); ②悬浮期间 `:title` 绑定值变化(speed / 今日流量随主轮询逐轮变), Vue 写回 title 后无人再摘; ③轮询/重渲染把指针下节点**整个替换** —— 指针不动就没有 mouseover/mouseout, 前两轮的「进入时摘」与「250ms 补摘」都只作用于旧节点, 新节点 title 原样入 DOM。三者都表现为自绘浮层之外又冒出原生气泡(交替出现 = ③的节点替换时序随机)。
- **判别**: ①grep 模板里同一条 hover 链上有 ≥2 个带 title 的嵌套节点(`grep -n "title=" .../tpl/statusbar.html`); ②`ui_feedback.js` 里存在「hover 时摘 title / 还原 title / 周期补摘」类逻辑(摘除依赖鼠标事件 = 有缝); ③真机 hover 内层按钮 >1s 出现两个气泡, 或两气泡交替出现。
- **处置**: 不与 title 的出现时机赛跑, **在 DOM 层断供** —— MutationObserver 盯 `document`(childList+subtree+attributes, attributeFilter: ["title"]), 任何时刻出现 title 即刻 `capture()`: 值迁进 `data-aq-tip`、原属性删除; 启动时对现存 DOM 先 `sweep()` 一遍。浮层委托改命中 `[data-aq-tip]`, 文案 show() 时现读(轮询变值即显新值); 嵌套组 `closest()` 天然取最内层。⚠ 自身 `removeAttribute("title")` 也进观察器批次, capture() 里 `getAttribute("title") === null` 时幂等直返, 不得误清刚写入的 data-aq-tip; 空串 title 连旧标记一并清。代价: title 不再还原, 原生悬浮语义由 .aq-tip 承接(`:title` 绑定值变化时 Vue 仍会 setAttribute, 被观察器再次截走, 数据流闭环)。
- **守阵**: 无静态断言(行为层逻辑, 字符串钉不住语义); 复验方式 = Playwright 冒烟(动态插入 title / 悬浮出泡 / 悬浮期重写 / 节点替换无鼠标事件 / 空串 title / 嵌套组 / 全文档无残留 title 共 8 断言) + 真机状态栏 hover >2s 只见一个自绘气泡、DevTools 现查 DOM 无 title 属性。
- **复发**: 2(①一轮修「只摘最内层」→ 二轮报同样症状, 补祖先链摘除 + 250ms 补摘; ②二轮修完真机仍两 tooltip **交替**出现 —— 节点替换时 mouseover 不触发这条缝没被前两轮模型覆盖, 且补摘定时器与原生 ~1s 起跳存在竞态; 三轮改断供式根治。没提前命中的原因: 坑档只记了嵌套与写回两条触发, 节点替换场景是二轮复现后才识别出的第三条)

# JS/变体注入的 DOM 带 title 属性会被全局 MutationObserver 立刻迁走成 data-aq-tip, title 读不回来

> 摘要: 全局自绘 tooltip 的「原生 title 断供式」机制(shared/ui_feedback.js 的 MutationObserver)对
> **一切**新出现的 title 属性做单向迁移 —— 不只 Vue 模板渲染, **JS 手工插值出的 DOM(innerHTML /
> dtHtml 模板串 / createElement 后 setAttribute)同样在入 DOM 的观察器批次里被即刻摘掉 title、
> 改写为 data-aq-tip**。后果: ①插入后读 `el.getAttribute("title")` 恒为 null(想要原文案读
> `data-aq-tip`); ②CSS/测试选择器 `[title]` 永远匹配不上(要写 `[data-aq-tip]`); ③Playwright
> `get_attribute("title")` 返回 null 不是 bug。变体层(模板变体自管 DOM)的悬浮提示**不需要也
> 不应该自建 tooltip** —— title 照写, .aq-tip 自动承接。
> 触发: 变体 DOM, title 属性, data-aq-tip, getAttribute null, [title] 选择器, MutationObserver, ui_feedback, 悬浮提示, Playwright title
> 收口: 2026-10-06, 详情面板 15 变体巡检核实断供管道对变体 DOM 同样生效(切换器/动作钮悬浮提示正常)

## 条目

### 变体/JS 注入的 title 是「一次性票券」, 落 DOM 即被换成 data-aq-tip

- **触发**: 详情面板 15 个模板变体(计划 26-10-06-0838)全部走 `dtHtml` 标签模板拼 HTML 再
  `replaceChildren` 原子换帧, 节点带 `title="..."`(如复制钮 `title="复制hash"`、行
  `title="打开目录"`)。这些 title 在插入宿主的同一个 MutationObserver 批次里就被
  `capture()` 迁走(`ui_feedback.js` 的 sweep + capture, 全文档观察)。
- **判别**: 插入后立刻 `getAttribute("title")` 返回 **null**, `getAttribute("data-aq-tip")`
  才是原文案; DOM 检查器里看不到任何 title 属性(「title 莫名消失」不是内存泄漏也不是变体
  bug)。依赖 `[title]` 的 CSS 规则、按 title 统计的守阵断言、Playwright
  `page.get_attribute("title")` 全部落空 —— 同类断言要改用 `data-aq-tip`。机制细节:
  capture 对自身 removeAttribute 的回批**幂等直返**(不会误清刚写入的 data-aq-tip);
  空串 title 视为清除提示(连旧标记一起摘)。
- **处置**: 变体 / JS 注入 DOM 想要悬浮提示: **照常写 title**, 不要自建 tooltip 也不要直接写
  data-aq-tip(写 title 走统一断供管道, 行为与三皮肤模板一致; 直接写 data-aq-tip 也可,
  但两套并存徒增分叉)。插入后需要回读提示文案: 读 `data-aq-tip`。想以「无提示」表达某状态:
  写 `title=""`(空串, 观察器把旧 data-aq-tip 一并摘掉)。单点实现:
  `shared/ui_feedback.js` 的 `capture()` / `sweep()`; 机制前史见
  aq-tip-nested-title-double.md(断供式定稿)。

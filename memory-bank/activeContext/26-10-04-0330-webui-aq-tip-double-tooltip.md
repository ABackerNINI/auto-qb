# 状态栏双 tooltip — aq-tip 祖先链摘除 + 悬浮期补摘

> 摘要: 用户报「WEBUI 状态栏多数元素有两个 tooltip」。根因 = 全局自绘 tooltip(.aq-tip,
> ui_feedback.js)靠 hover 时摘 title 压原生气泡, 但 statusbar.html 是嵌套带 title 结构
> (.sb-today > .sb-hist/.sb-qb、.sb-stats > .sb-item、.sb-speed > .sb-alt/.sb-spd), 旧实现只摘
> closest("[title]") 最内层 —— 原生气泡借外层祖先 title 还魂; 同源: 状态栏 `:title` 随轮询
> 逐轮变值, Vue patch 悬浮期间写回 title 而 mouseover 不再触发。两路都修在 enter()/hide()。
> 最后活动: 2026-10-04 03:30

## 已完成 (2026-10-04)

- **修复**: `shared/ui_feedback.js` enter() 从锚点沿 parentElement **整条祖先链**摘 title
  (链存 `chain` 数组, hide() 单点还原), 另设 `REARM_MS=250` 周期补摘定时器把 Vue 重写回去的
  title 再摘掉(补摘捕获即最新值, 还原不丢新值; 周期短于原生气泡 ~1s 起跳延迟)。文件头机制
  注释同步改写。
- **回写**: conventions/webui.md「悬浮提示 .aq-tip」触发面段同步(祖先链 + 补摘口径);
  新坑档 [pitfalls/web-ui/aq-tip-nested-title-double.md](../pitfalls/web-ui/aq-tip-nested-title-double.md)
  (触发/判别/处置 + 真机复验方式; 无静态守阵 —— 行为层逻辑字符串钉不住); kb.index 重跑 20 生成物。
- 收尾: 基线切片 [baselines/26-10-04-0329](../testing/baselines/26-10-04-0329-webui-aq-tip-double-tooltip.md)
  (**2423 passed + 3 skipped / 99% / 29.14s** @ 64316c09; 纯前端行为层修复 +0 用例)。
  不满足立档阈值(单轮单源文件小修)。

## 状态

任务完结, 改动留在工作树等用户显式「提交」指令(本轮未获提交授权)。
真机走查项: 三皮肤状态栏 hover 历史入口/速度组 >2s 只见一个自绘气泡, 移开后 DevTools 现查
title 属性恢复。

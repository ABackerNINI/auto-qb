# 状态栏双 tooltip — aq-tip 断供式定稿 (title→data-aq-tip 单向迁移)

> 摘要: 用户报「WEBUI 状态栏多数元素有两个 tooltip」, 二轮修复(祖先链摘除 + 250ms 补摘,
> 71251d61)后仍报**两 tooltip 交替出现**。第三条触发路径: Vue 轮询把指针下节点整个替换时
> 指针不动、mouseover 不触发, 新节点带着 title 直接入 DOM, 原生气泡还魂; 补摘定时器与原生
> ~1s 起跳另有竞态。定稿 = 用户拍板「只留自绘 tooltip, 移除原生」: MutationObserver 盯全
> 文档, title 属性任何时刻出现即刻迁进 data-aq-tip 并删掉原属性, DOM 里不存在 title,
> 原生气泡从根上断供; title 不再还原。
> 最后活动: 2026-10-04 04:15

## 已完成 (2026-10-04)

- **一轮** (71251d61): enter() 祖先链整条摘 title + 悬浮期 250ms 周期补摘 —— 覆盖了嵌套
  还魂与 Vue 写回两条路, 但真机仍交替出双泡。
- **二轮→三轮定稿** (本轮): `shared/ui_feedback.js` 整块重写为**断供式** —— ①启动 `sweep()`
  清现存 title; ②MutationObserver(childList+subtree+attributes, attributeFilter:["title"])
  任何时刻出现 title 即 `capture()` 迁进 data-aq-tip 并删原属性(自身 removeAttribute 的
  null 幂等直返, 空串连旧标记清); ③浮层委托 mouseover/focusin 改命中 `[data-aq-tip]`,
  closest 取嵌套组最内层, 文案 show() 现读最新值; ④删除 chain/restore/REARM 补摘全部
  逻辑(不再与出现时机赛跑)。模板 130+ 处 title 零改动, `:title` 绑定数据流闭环(Vue 写回
  即被截走)。
- **验证**: node --check + Playwright 冒烟 8 断言全过(含「节点替换无鼠标事件」这条上轮
  还魂缝、全文档无残留 title); test.full **2423 passed + 3 skipped / 99% / 30.21s**
  @ 800ccba2, 基线切片 [baselines/26-10-04-0414](../testing/baselines/26-10-04-0414-webui-aq-tip-tooltip-severed.md)。
- **回写**: conventions/webui.md 触发面段改断供式口径; 坑档
  [pitfalls/web-ui/aq-tip-nested-title-double.md](../pitfalls/web-ui/aq-tip-nested-title-double.md)
  重写(触发补第③条节点替换路径, 复发 +2, 处置改断供式) + `_index.md` 行同步。

## 状态

任务完结, 改动留在工作树等用户显式「提交」指令(本轮未获提交授权)。
真机走查项: 三皮肤状态栏 hover 历史入口/速度组 >2s 只见一个自绘气泡, DevTools 现查 DOM
无 title 属性(原生 tooltip 应全局绝迹)。

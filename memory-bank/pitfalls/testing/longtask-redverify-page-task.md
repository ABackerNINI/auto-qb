# longtask 量具的红验注入必须走页面任务队列

> 摘要: 给 longtask 预算断言做红验(注入长任务证必红)时, Playwright `page.evaluate` 里直跑忙等
> **不产生 longtask 条目**(CDP 注入的任务不归账, 2026-11-13 实测 130ms 忙等 -> `[]`), 红/绿验会
> 双双假绿; 必须在页面内**自调度任务** —— `page.evaluate(() => setTimeout(() => { 忙等 }, n))`
> 实测归账 `[130]`。注入 63ms 可确定性复刻负载毛刺形态(issue 26-11-13-0519 的假红条件)。
> 触发: longtask, 长任务, 红验, 红绿双验, 注入, 忙等, evaluate, PerformanceObserver, 量具, 预算断言

- **现象**: `page.evaluate(() => { const t0 = performance.now(); while (performance.now() - t0 < 130); })`
  在页内 PerformanceObserver(`entryTypes: ['longtask']`)已安装的前提下跑完, `window.__lt` 仍为空 ——
  130ms 的主线程阻塞没有任何 longtask 条目。独立探针(about:blank + 同款观察者)复证实测: evaluate
  直跑忙等 `[]`, `setTimeout` 自调度忙等 `[130]`。
- **根因**: CDP `Runtime.evaluate` 派发的任务不进 longtask 归账(Chromium 对该来源的任务不做
  长任务上报); 页面自己经任务队列调度的任务(setTimeout/rAF/事件回调)才被 PerformanceObserver 记。
- **处置**: 红验注入一律写成页面自调度形态 —— `await page.evaluate(() => setTimeout(() => {
  const t0 = performance.now(); while (performance.now() - t0 < MS); }, 30))`, MS 取量具阈值上方
  (证必红)或取已知噪声值如 63(证容忍, 复刻假红条件); 注入后观察窗必须覆盖定时器触发点
  (30ms 延迟 < 500/800ms 窗)。别用 evaluate 直跑忙等判"新口径放行" —— 它什么都没注入。
- **相关**: 计数口径本身(为什么 count==0 在负载态假红)见
  [timing-tolerance.md](timing-tolerance.md) 复发④; 量具本体
  `e2e/dt-live-update.spec.mjs`(`LT_REGRESSION_MS` 注释)。

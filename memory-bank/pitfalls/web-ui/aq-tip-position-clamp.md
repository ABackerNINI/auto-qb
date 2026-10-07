# 自绘 .aq-tip 定位: 锚点脱离文档 / 竖向末尾夹取, 都会把浮层压到元素身上

> 摘要: 全局自绘 tooltip(.aq-tip, 调度单点 `shared/ui_feedback.js`)的定位缺陷, 都表现为「位置错误 / 浮层盖住它描述的元素」: ①(首轮)`show()` 的 350ms 延时窗口内锚点被 Vue 轮询整个换掉 → 拿到已脱离文档的节点, `getBoundingClientRect()` 全 0, 浮层落视口左上角 `(8,6)`; ②(首轮)竖向末尾无条件夹回视口, 底缘锚点被浮层压住; ③(二轮 2026-10-07)**显示期锚定失活** —— 定位只在 `show()` 做一次, 此后锚点被轮询重建(换节点)或移位(布局/折叠), 浮层留在原地漂移; 键盘 `focusin` 路径无指针坐标(NaN)无法走指针重解析。
> 触发: tooltip 位置错误, tooltip 挡住元素, tooltip 跑到左上角, aq-tip, ui_feedback, show 定位, getBoundingClientRect 全 0, 脱离文档, detached, 节点替换, 350ms 延时, 状态栏 tooltip, 上传速度 tooltip, sb-spd, 浮层压住锚点, 夹取, 锚点漂移, tooltip 留在原地, reacquire, rAF 帧环, 键盘 tooltip 错位, focusin NaN
> 收口: 2026-10-04 05:25 `show()` 改「锚点 `!isConnected` 时按 `mouseover` 记下的指针坐标 `elementFromPoint()` 重解析 + 竖向任何分支不越过锚点」; 2026-10-07 11:42 二轮加「place() 定位单点 + reacquire() 语义重解析 + watch()/tick() rAF 帧环显示期保活」, test.full 2717 passed + 4 skipped / 99%(基线 26-10-07-1142)
**Refs:** memory-bank/tasks/26-10-07-webui-detail-panel-followups.md

## 条目

- **触发**: ①**锚点脱离** —— `enter()` 命中锚点后起 `setTimeout(show, 350)`, 这 350ms 内 Vue 轮询把指针下的节点整个换掉(新节点无鼠标事件、`mouseover` 不再触发), `cur` 指向的原节点已 `isConnected === false`; `getBoundingClientRect()` 对脱离文档的元素**一律返回全 0**, 于是 `x = max(EDGE, 0 - w/2) = 8`、`y = 0 - h - GAP < EDGE` ⇒ 翻下方 `y = 6`, 浮层落在视口左上角。②**竖向末尾夹取** —— 原末尾 `if (y + h > vh - EDGE) y = max(EDGE, vh - h - EDGE)` 无条件执行: 锚点在视口底缘(状态栏 `position: fixed; bottom: 0`)时, 只要上方放不下而走了「转下方」分支, 这一步就把浮层从锚点下方**拉回视口底部** —— 恰好压在锚点(以及整条状态栏)上。⚠ 常规窗口尺寸下 ② 触发不到(需 `vh ≲ 76px`), 所以"平时看起来没问题"与"真机偶尔盖住元素"可以并存。
- **判别**: ①`ui_feedback.js` 的 `show()` 直接对传进来的锚点 `getBoundingClientRect()` 而**不校验 `isConnected`** ⇒ 有缝; ②竖向定位末尾存在**无条件** `Math.max(EDGE, innerHeight - h - EDGE)` 之类的夹取(夹取目标只保证"进视口", 不保证"不压锚点") ⇒ 有缝; ③复现(Playwright): 派发 `mouseover` 后**立刻**把该节点 `remove()` 并插入一个 clone, 等 >350ms 读 `.aq-tip` 的 box —— 全 0 锚点会给出 `[8, 6, …]`; 或把视口压到 `vh ≤ 76` 再看 box 与锚点 box 是否相交。
- **处置**: ①**锚点解析与使用分离** —— `mouseover` 时把 `ev.clientX/clientY` 一并记下; `show()` 开头若 `!anchor.isConnected`, 用 `document.elementFromPoint(curX, curY)?.closest("[data-aq-tip]")` **重新解析**当前真正的锚点(解析不到就 `hide()`: 宁可不弹, 也不弹到错误位置); 键盘路径(`focusin`)无指针坐标, 传 `NaN` 不参与重解析。②**竖向三档** —— 上方放得下用上方 → 上方放不下、下方放得下用下方 → 两侧都放不下才允许溢出视口(取空间较大的一侧)。**去掉末尾那次无条件夹取**; 三档都保证浮层不越过锚点。⚠ 别在退化分支里"为了进视口"再夹一次 —— 那正是把浮层推回锚点身上的原因。
- **守阵**: 无静态断言(行为层几何, 字符串钉不住语义); 复验 = Playwright 两组用例 —— (a) 常规尺寸 sweep(1280/1440/1024/900/800/640 × 三皮肤)确认**位置逐像素不变**(防回归); (b) 节点替换用例确认 box 回到锚点上方、`vh` 76→50 逐档确认 `overlap === false`。
- **复发**: 0(新记)

### 显示期锚定失活: 定位只做一次, 锚点随后被重建/移位就漂移(2026-10-07 二轮)

- **触发**: 首轮修法只覆盖了 `show()` 那一帧 —— 350ms 延时窗口内锚点已脱离文档。但 tooltip 显示期
  横跨多个轮询周期(1.5~3s), 轮询整节点重建让锚点**换节点**(浮层还钉在旧节点坐标上)、布局/折叠让锚点
  **移位**(浮层原地不动 = 相对锚点漂移); 键盘路径(`focusin`)无指针坐标(传 NaN), 首轮的指针重解析帮不上。
- **判别**: 「定位」被实现成 `show()` 里的一次性计算, 而浮层与锚点是**持续的空间关系** —— 凡锚点活在
  高频重建的列表里, 一次性定位等于把"此刻快照"当"全程事实"。复现: tooltip 显示中触发该区域重渲染
  (轮询/折叠/换肤), 浮层留在旧坐标; 键盘 Tab 聚焦带 tip 的控件, 坐标错位。
- **处置**: 三件套收口在 `show()` 单点 —— ①`place()` 定位单点(首帧与重定位同一份几何代码);
  ②`reacquire()` 语义重解析: `cur` 断链时按 `data-aq-tip` **同文案**候选节点里取「视口中心距旧矩形
  最近」者接续(文案相同 = 语义相同, 位置最近 = 大概率同一目标); ③`watch()`/`tick()` rAF 帧环: 显示期
  每帧查 1 次 `getBoundingClientRect`(零额外 DOM 查询), 断链走重解析、四轴漂移 >1px 走重定位;
  键盘 NaN 坐标路径由**矩形基准**(首帧锚点矩形)兜住, 不依赖指针。
- **守阵**: `test_web_longtail.py::test_aq_tip_anchor_watch_and_reacquire_wired`(接线断言); 行为层几何仍以
  Playwright 真机验证为准(本轮四项实测之一)。
- **复发**: 0(二轮新记)

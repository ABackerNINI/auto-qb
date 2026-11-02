# 行高签名混入视图态因子 + 容器过渡期几何不可采信: 千级下切页/关抽屉秒级卡死

> 摘要: 行高签名混入视图态因子 + 容器过渡期几何不可采信: 千级下切页/关抽屉秒级卡死
> 触发: 切标签页卡死, 关抽屉卡死, 能滚不能点, 行高签名, viewMode, ResizeObserver, _winCtnSync, 假 bump, 全量量齐
**Refs:** memory-bank/tasks/26-11-02-webui-large-filelist-perf.md, memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html

### 行高签名因子混入「不真正改变行几何」的视图态(如 viewMode), 切页即全表作废退全量量齐

- **触发**: 窗口化引擎的行高签名(`_measureRowH` 的 sig)把 viewMode 这类「不真正改变行几何」的因子算进去; 切标签页(torrent/group/member 视图互换)→ 签名失配 → 三 kind 行高全表作废 → 回原视图时退回全量渲染量齐, 3000 行下单发 5.8~8.4s longtask。
- **判别**: 切页后第一拍出现秒级 longtask, CDP 栈顶全指向 `_measureRowH ← updated (lifecycle.js)`; `getBoundingClientRect` 自耗秒级(布局抖动); `_winMeasured` 被翻 false。
- **处置**: 签名因子白名单化 —— 只保留**真正改变行几何**的因子(resize 代 `_winResize`、列集合 colcounts); 每加一个新因子先自问「它变时行高会变吗, 有没有别的因子已经盯住它」。
- **守阵**: `e2e/window-invalidation.spec.mjs` ①(切页往返不重置行窗) + `tests/test_webui_static_dom_page.py::test_frontend_row_window_sig_and_ctn_sync_guard`(静态断言签名无 viewMode)。

### 容器离场过渡期(clientWidth 跳变)被 ResizeObserver 当真 resize, 假 bump 与主表共用的引擎态

- **触发**: 抽屉关闭时 `.drawer-leave-active` 把面板转 `position:absolute` 出流, `.drawer-body` clientWidth 跳变(实测 1894→1918); RO 首拍触发 `_winCtnSync` 假 bump `_winResize` → 主表 3000 行全量重渲 5.6s longtask。用户观感「列表能滚但 hover/点击无响应」—— 滚轮走合成器线程, 鼠标事件被主线程长任务饿死; `elementFromPoint` 前后对照无遮罩残留, 别误判成 hit-test 劫持。
- **判别**: 关抽屉后下一拍 `_winResize` 0→1 且随后秒级 longtask; elementFromPoint 命中正常行节点(无覆盖层) ⇒ 主线程饥饿, 不是残留遮罩。
- **处置**: 容器几何采集点加状态守卫 —— 过渡期/收场期(`!this.drawer.open` 一类)宽度不可采信, 直接 return; 真重开经重绑路径重 sync 不丢状态。
- **守阵**: `e2e/window-invalidation.spec.mjs` ②(关抽屉不假 bump: `_winResize` 恒等 + 确定性 refresh 下一拍仍窗口化)。

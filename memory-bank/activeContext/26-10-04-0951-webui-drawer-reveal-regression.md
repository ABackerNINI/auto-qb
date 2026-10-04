# 抽屉双击末行遮挡回归 — 落定几何三发让位 (Done)

> 摘要: 2026-10-03「双击末尾种子被抽屉挡住」修复回归, 用户再报同症状。真浏览器逐帧取证双层
> 根因(让位量了 loading 态几何 + 文档底 scrollBy 被钳制, 下滚余量是槽位长高才创造的), 修法
> 三发让位全走 _kbRevealRow 单点(逐帧重登记 / FX-29 待到集合挂单兑现 / afterEnter 槽位落定
> 补发), 真机探针 prism 红 → 三皮肤绿, 守阵两条扩展, test.full 2461 passed / 99%。
> 最后活动: 2026-10-04 09:51

## 已完成 (2026-10-04)

- **取证** (ui_harness 400 合成种子 + Playwright 探针, dev-only): 修复前 prism 双击末行 —— 行
  784/828 被面板(顶 488, h=378)盖住, scrollY 全程 24953 一字不动, animTop=616(loading 态登记,
  落定 488), reveal 只发一发 scrollBy(+236) 且 y1==y0(被文档底 max 钳死)。深层: 26-10-03 修复
  在 nextTick 量一次几何, 那刻面板是 loading 空态(≈百来px), 详情几十 ms 到手长到 42vh —— 开场
  几何作废; 且用户在文档底, scrollBy 无余量可滚 —— 余量是停靠槽位(.drawer-dock 流内元素)长高
  才创造的, 槽位长高发生在让位之后。键盘跟随不踩坑(面板早已长好), 故「键盘正常、双击被盖」。
  上轮修复真机走查未做, 静态守阵探不到「调用存在但几何/时机错」, 回归潜伏至今。
- **修复** (全在 drawer.js, `_kbRevealRow` 本体不动): ①`drawerEnterHook` 追赶循环逐帧重登记
  `_drawerAnimTop = dock底缘 - 面板自然高`(sticky 吸底期底缘恒定; 面板布局高不受槽位裁剪)——
  修量测, 动画中键盘跟随也受益; ②`openTorrentDrawer` 复用 FX-29 待到集合登记 `detail + 初值
  页签` 源(流量页签定高不进集合)+ 挂单 `_drawerOpenReveal`, `_drawerDone` 清空时兑现(open/hash
  双守卫防迟到误发)——修「页签数据中途长高」; ③`drawerAfterEnterHook` 槽位落定后补发(种子形态
  门控)——修「文档底钳制」。三发都在被点行被盖时才 scrollBy, 中间行实测 scrollY 不变(不抢滚轮)。
- **验证**: 真机探针 prism 红 → prism/atlas/console 三皮肤绿(行落定 428±1, 面板顶 488,
  零 pageerror); 中间行/打断重开(残留挂单清空)/开着换行三边界绿。守阵扩展
  `test_drawer_open_reveal_row`(三发挂点+挂单守卫) / `test_drawer_transition_dock_anim`
  (逐帧重登记) 2 passed; test.full **2461 passed + 4 skipped / 99% / 29.13s**
  (基线 [baselines/26-10-04-0951](../testing/baselines/26-10-04-0951-webui-drawer-reveal-regression.md))。
- **回写**: 坑档 [pitfalls/web-ui/dock-panel.md](../pitfalls/web-ui/dock-panel.md) 第三条复发 +1
  (为什么没命中: 守阵只断言「调用了让位」, 探不到几何/时机错) + 新增第四条「落定几何与文档底
  余量」(触发/判别/处置/守阵)。

## 状态

任务完结。改动留在工作树(drawer.js + tests/test_web_shortcuts.py), 等用户提交指令。
探针脚本与截图在系统临时目录(dev-only 不入库)。

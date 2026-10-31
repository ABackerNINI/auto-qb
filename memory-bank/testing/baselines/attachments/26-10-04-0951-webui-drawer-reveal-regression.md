# 基线切片 26-10-04-0951 — 抽屉双击末行被遮挡回归修复 (落定几何三发让位)

> 摘要: 2026-10-03「双击末尾种子被抽屉挡住」修复回归。真浏览器取证双层根因: ①让位量测发生在
> loading 态(面板百来px), 详情到手长到 42vh 后开场几何作废(实量与动画期登记 _drawerAnimTop 同病);
> ②用户在文档底, scrollBy(+Δ) 被浏览器钳制成 0 —— 下滚余量是停靠槽位(.drawer-dock 流内元素)
> 长高才创造的, 而槽位长高发生在让位之后。修法三发让位全走 _kbRevealRow 单点: 追赶循环逐帧
> 重登记落定顶缘投影 / 开场按 FX-29 待到集合挂单、数据全到手兑现 / afterEnter 槽位落定补发。

- 时间: 2026-10-04 09:51 (GMT+8); 基线 = 开工同步 `72a7d274` + 本轮 drawer.js/守阵改动
- 分支: develop @ 72a7d274 + 工作区
- 命令: `commands run test.full`
- 实测: **2461 passed + 4 skipped, 29.13s, 覆盖率 TOTAL 99%**(14650 语句 / 139 未覆盖 / 4894 分支 / 108 partial)
- 相对上基线(26-10-04-0752: 2460 passed)净增 1 用例, 来自开工同步带入的远端提交; 本轮只扩两条
  既有守阵的断言(无新用例)。守阵单跑: test_drawer_open_reveal_row / test_drawer_transition_dock_anim 2 passed
- 真机探针(ui_harness 400 合成种子 + Playwright, dev-only): 修复前 prism 红(行 784 被盖、scrollY
  全程不动、animTop=616 loading 快照); 修复后 prism/atlas/console 三皮肤绿(行落定 428±1, 面板顶 488,
  零 pageerror) + 中间行不扰滚动(scrollY 不变) + 打断重开(残留挂单清空)与开着换行两边界绿
- 备注: 探针脚本与截图在系统临时目录(dev-only 不入库); 跑批顺序 = 改码 → 探针红 → 修复 →
  探针绿 → 守阵 → test.full

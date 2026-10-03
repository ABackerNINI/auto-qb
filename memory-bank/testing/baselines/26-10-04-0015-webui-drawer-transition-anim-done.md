# 基线 · 2416 passed + 3 skipped / 99% —— 抽屉出入过渡动画轮

> 摘要: 用户报「WEBUI 抽屉出现与消失时很生硬, 添加过渡动画」: 停靠面板占据文档流, open 翻转时
> 列表底部一帧被面板撑开/收回 —— 面板本体 transform/opacity 滑淡(W1 既有)治不了布局跳变。
> 修法 = JS 过渡钩子驱动 `.drawer-dock` 槽位高度插值(drawer.js `drawerEnterHook/drawerLeaveHook`
> + after 钩子, drawer.html `<transition>` 接线): 开场槽位追面板实时高(详情中途长高也跟),
> 收场同步收面板自身高度 + dock 跟随(CSS 退场转 absolute 底缘锚定, closeDrawer 冻结用户可见高);
> 动画期几何登记 `_drawerAnimTop` 供 `_kbViewBottom` 单点优先消费(行让位不读中间插值),
> seq 代际闸管快速往返, reduced-motion 与 D3 窄屏全屏态双豁免。守阵 `test_drawer_transition_dock_anim`;
> 真浏览器探针三皮肤各 9/9。档案 [tasks/26-10-03-webui-drawer-redesign](../../tasks/26-10-03-webui-drawer-redesign.md)。
> 基线时间: 2026-10-04 00:15, develop @ 926d1f66 + 工作区(本轮回写件随主提交暂存)。

TOTAL **2418 passed + 3 skipped / 99%**(14,395 语句 / 130 未覆盖 / 4,810 分支 / 104 partial,
test.full 47.8s, rc=0)。
相对上一切片(26-10-03-2106: 2415 passed + 3 skipped / 99%, 14,395 语句 / 130 未覆盖 / 4,810 分支,
@ 7ca46436) **passed +3** —— 本单新增守阵 1 条(`test_drawer_transition_dock_anim`) + 远端合流件
2 条(926d1f66 与 91a4f1d7 等批次带入, 未逐文件归因); 语句/分支数持平, 未覆盖数持平。
test.quick 同口径 35.2s 全绿(2416 + 3 skipped, 合流前); 合流后复跑 test.full 48.8s 全绿。

真浏览器冒烟(桩服务 + Playwright 探针, 三皮肤 atlas/prism/console 各 9/9):
开(槽位插值进行中 0<中途高<=落定高 / 动画类挂载 / 动画期下界走登记值 / 收敛回自然高) ·
关(收场槽位同步递减 / 收场完毕类摘除槽位归零) · 往返(80ms 快速开关重开终态干净无残留) ·
布局(dock 全宽 = 列表容器宽不漂移) · 控制台零报错。

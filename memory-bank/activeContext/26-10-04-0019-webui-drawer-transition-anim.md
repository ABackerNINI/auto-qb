# 抽屉出入过渡动画 (Done)

> 摘要: 2026-10-04 用户报「抽屉出现与消失时很生硬, 添加过渡动画」: 停靠面板占文档流, open 翻转时
> 列表底部一帧被面板撑开/收回 —— 面板本体的 transform/opacity 滑淡治不了布局跳变。修法 = JS 过渡
> 钩子驱动 `.drawer-dock` 槽位高度插值(drawer.js 钩子 + drawer.html `<transition>` 接线 + 三皮肤 CSS
> 成对), 动画期几何登记 `_drawerAnimTop` 供 `_kbViewBottom` 单点消费(行让位不读中间插值)。
> 守阵 `test_drawer_transition_dock_anim`; 基线 26-10-04-0015(2418 + 3 skipped / 99%)。
> 最后活动: 2026-10-04 00:19

## 已完成 (2026-10-04)

- **定位**: 面板停靠化(W1)后出入场只动面板本体 transform/opacity, 布局高度一帧跳变 = 生硬根源;
  CSS 注释自认「高度不可过渡」—— 需要钩子驱动槽位插值。
- **落码**: drawer.js 出入过渡块(`drawerEnterHook` rAF 追赶循环追面板实时高 / `drawerLeaveHook`
  收面板自身高 + dock 冻结高跟随 / after 钩子收敛兜底 + 挡迟到清场 / seq 代际闸); drawer.html
  `<transition>` 接 `@enter/@leave/@after-enter/@after-leave`(❗用 `@enter` 不用 `@before-enter`
  —— 同帧元素未插入 DOM, parentElement 为 null, 动画整体失效); closeDrawer 冻结用户可见高
  (同帧零跳变); shortcuts.js `_kbViewBottom` 动画期优先读 `_drawerAnimTop` 登记值(入场中切走
  视图的悬空登记在单点内作废); 三皮肤 CSS 成对(dock 动画期裁剪 + 退场 absolute 底缘锚定,
  ❗不得用 inset:0 顶锚定——随槽位塌缩把面板顶跑); reduced-motion 与 D3 窄屏全屏态双豁免。
- **守阵**: `tests/test_web_shortcuts.py::test_drawer_transition_dock_anim`(接线必须 @enter /
  槽位插值 / 收场双高同步 / 几何登记单点消费 / seq 代际闸 / after 钩子守卫 / 三皮肤成对)
  + 文件头测试计划登记。
- **冒烟**: 桩服务 + Playwright 探针(临时工装, 未入仓库), 三皮肤各 9/9: 开场插值/收敛/收场/
  快速往返终态干净/dock 全宽不漂移/零报错。
- **基线**: test.full **2418 passed + 3 skipped / 99%**(26-10-04-0015, @ 926d1f66 + 工作区;
  合流前 2416, 远端合流带入 2 条)。
- 档案: [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md) 进度日志
  2026-10-04 条目; progress/implemented-webui.md 条目。随 ship.commit 入库(待用户提交指令)。

## 状态

任务完结; 提交待用户显式指令(触发词「提交 / 入库 / 推上去」)。

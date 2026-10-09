# WEBUI 种子详情面板页插件化 + 页签合并(已实施)

> 摘要: 用户动议「常规&内容 / Tracker&用户 合并, 仅宽度足够时提供选项, 可切换」—— R2 改版(右键开关 + 页插件化 + 功能全量保留)经四项拍板后实施完成: classic 四件页插件(drawer_pages/)入注册表, 合并 = 抽屉级布局标志 `drawerMerge` + 右键勾选菜单 + 宽度门 1920(暂态遮蔽); 双列各挂各自所选页插件, 交互全量保留。计划 `memory-bank/plans/26-10-09-2219-plan-webui-drawer-merge-tabs.html`(R3, Done)。
> 最后活动: 2026-10-09 23:53

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Topics:** webui-drawer-merge-tabs

## 已完成(迁自「正在进行」)

- 核心层(drawer_templates.js): classic 入表 + kit 工具箱 + 双实例挂载(_dtMounted/_dtMounted2)+ ownerKey 回落通道(classic 抛错走错误外壳不复位)+ .dt-tpl 限宽收窄 + drawer-split 布局 CSS + 门常量/resize 防抖/drawerMerge $watch。
- classic 插件 x4(general/trackers/peers/content, drawer_pages/): DOM 逐类名移植, 事件委托 + 状态自保(rawOpen/滚动/选中), 交互全量保留; content destroy 收回 filePrio。
- drawer.html: 经典链退役, 双结构宿主(单栏 x4 / 合并双列 v-if 互斥)+ 右键接线; ctx-menus.html 抽屉菜单分支(置灰 is-gated); state/menu/lifecycle/dialogs(escBusy) 浮层链同步。
- drawer.js 数据供给: _drawerWaitSources/_loadDrawerTab/_startDrawerPoll 按生效对偶扩展(FX-29 全对齐掀罩)+ _drawerMergeSupply 补给单点(drawerMerge $watch 与 resize 回调共用)。
- 测试: 守阵同步 6 处; e2e drawer-merge.spec.mjs 4 用例 + 既有 e2e 全绿(128 passed / 10 skipped 存量); 基线切片 `26-10-09-2353-webui-drawer-merge-tabs`(2870+4, 99%)。
- 回写: 主题文档 modules/webui-static-contract.md + progress/implemented-webui.md。

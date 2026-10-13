# 26-10-14-0204-webui-detail-classic-removal — 四内容页签经典 UI 与流量页签变体移除

> 摘要: 用户令「移除种子详情面板除『流量』页的 4 个经典 UI, 以及『流量』页的除经典外的 UI, 以及 qb 流量页的除经典外的 UI」; 二次确认选定**彻底删除经典渲染**档。终态 = 四内容页签(常规/Tracker/用户/内容)**变体独档**(缺省 = 该页签首个变体), 流量页签(含 qB 全局/分组挂点)**经典独档**。删除面: `drawer_tabs.js` 四组件 + `tpl/drawer-tabs.html` + 三个经典单元格渲染器 + 经典三表注册(drawerTracker/drawerPeer/drawerFile)/六个 columns computed/六个 state 排序字段/`drawerTrackerRows`/`fileRowSelect`/`renameFileRow`/`drawerSelPath` + 流量变体 13/14/15 + 图前/图后双宿主 + 注册表 `slot`; 档制判据收成 `CLASSIC_TABS/defaultSel/choices` 单点(全层无 `|| CLASSIC` 字面量), 渲染失败兜底改回该页签缺省档, 流量页签模板菜单因候选 < 2 不再弹; 三皮肤死 CSS 清 ~144 条。守阵 6 个 pytest 函数 + 7 份 e2e spec 同轮改写。代价(用户拍板接受): 内容页「重命名…」随经典消失; 兜底不再有第二实现。档案 [26-10-14-webui-detail-classic-removal](../tasks/26-10-14-webui-detail-classic-removal.md); 基线 [26-10-14-0244](../testing/baselines/26-10-14-0244-webui-detail-classic-removal.md)。
> 最后活动: 2026-10-14 02:44

**Refs:** memory-bank/tasks/26-10-14-webui-detail-classic-removal.md,memory-bank/testing/baselines/26-10-14-0244-webui-detail-classic-removal.md,memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

## 下一步

1. 无强制后续。可选: 变体 10/11/12 侧补「重命名」入口(内容页功能回补, 单独立项)。
2. 旧存值自愈已验证(`readSel` 白名单): 四页签存 `"classic"`、流量页签存 `13/14/15` 一律回落缺省档。

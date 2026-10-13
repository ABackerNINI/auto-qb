# 26-10-14-webui-detail-classic-removal — 移除种子详情面板的四内容页签经典 UI + 流量页签变体

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Summary:** 用户令「移除种子详情面板除『流量』页的 4 个经典 UI, 以及『流量』页的除经典外的 UI, 以及 qb 流量页的除经典外的 UI」(经二次确认选定**彻底删除经典渲染**档)。落地 = ①四内容页签(常规/Tracker/用户/内容)经典渲染链整体删除: `drawer_tabs.js` 四组件 + `tpl/drawer-tabs.html` + 三个经典单元格渲染器(表壳 + 三份 xtpl-cells 模板)+ 经典三表注册(drawerTracker/drawerPeer/drawerFile)与配套 grid/visibleCols computed、state 排序字段、`drawerTrackerRows`/`fileRowSelect`/`renameFileRow`/`drawerSelPath`; 四页签改为**变体独档**(缺省 = 该页签首个变体)。②流量页签变体 13/14/15 删除, 图前/图后双宿主(traffic-pre/post)与注册表 `slot` 一并退役, 流量页签(含 qB 全局/分组挂点)改为**经典独档**, 该页签模板菜单因候选 < 2 不再弹出。③「哪些页签还有经典」收成注册表单点 `CLASSIC_TABS/defaultSel/choices`, 渲染失败兜底由 classic 改回该页签缺省档。④三皮肤死 CSS 清除(共 ~144 条规则)。⑤守阵与 e2e 同轮改写(6 个 pytest 函数 + 7 份 e2e spec)。代价(用户已知并拍板): 内容页「重命名…」随经典消失; 渲染失败兜底不再是经典。全量 3199 passed + 4 skipped, e2e 见 Refs 基线。

**Refs:** memory-bank/testing/baselines/26-10-14-0244-webui-detail-classic-removal.md
**Topics:** webui-detail-panel-redesign, webui-drawer-templates

## 原始请求

> 移除种子详情面板除"流量"页的4个经典UI, 以及"流量"页的除经典外的UI, 以及qb流量页的除经典外的UI

二次确认(用户拍板): 范围 = **非流量四页签去经典 + 流量页去变体**; 深度 = **彻底删除经典渲染**(而非只从菜单移除)。

## 思考过程与决策

- **「4 个经典 UI」= 四个 Vue 组件**: 项目词汇里「经典」是 `drawer_tabs.js` 的四个页签组件(W2 起 classic 住 Vue 组件, 不是注册表条目), 常规/Tracker/用户/内容各一个, 恰好 4 个 —— 与请求里的「4 个」精确对应; 流量页签的「经典」不是组件(是模板内联的 uPlot 图), 故不在被删之列。
- **深度二选一先问用户**: 「移除 UI」可以只做菜单层(保留经典作渲染失败兜底 + 保住内容页重命名), 也可以连渲染链一起删。后者的代价是**内容页「重命名…」功能消失**(变体 10 自注「重命名不在本变体设计内 → 回 classic 用」)与兜底降级。用户选**彻底删除**, 故本轮按后者落地, 并在提交信息里写明这两项代价。
- **删除面靠「引用数」定, 不靠直觉**: 逐个 grep 确认 `drawerTrackerRows`/`fileRowSelect`/`renameFileRow`/`drawerSelPath`/`AQ_*_CELLS_COMPONENT`/`visibleDrawer*Cols`/`drawerTrackerGrid` 等在 `drawer_tabs.js`+`drawer-tabs.html` 之外**零引用**才删; `drawerPeerRows`(stub 表用)、`drawerFileRows`(变体 11 用)、`drawerGeneralSections`(变体 01/02/03 用)、`drawerTrackerVirtual`/`drawerTrackerStatus`(变体 04/05/06 用)、`DRAWER_*_COLUMNS`(变体列集派生底)**保留**。
- **档制判据收成单点**: 引入 `CLASSIC_TABS = ["traffic"]` + 注册表 `hasClassic/defaultSel/choices` 三件 —— 菜单候选、缺省档、渲染失败兜底、持久化写值全走它们; 全层不再出现 `|| CLASSIC` 字面量(取值口 `_dtSel(tab)`)。旧存值(四页签 `"classic"`、流量页签 `13/14/15`)在 `readSel` 白名单下自然失效回落缺省档, **无需迁移脚本**。
- **流量页签模板菜单**: 变体删光后该页签只剩经典一档, 菜单会退化成「单选项菜单」= 半残 UI; 故 `openDrawerMenu` 加「候选 < 2 且无合并项 → 不弹」早退(合并开关只属种子形态, 不受影响)。
- **死 CSS 一并清**: 经典模板专属类(drawer-hr/drawer-sec/drawer-rows/drawer-raw/drawer-toolbar*/f-row*/dtrk-*/dpeer-*/dfile-*/prio-btn/dir-name 及 `.f-row` 作用域下的 `.ico-t-*`)在 js/html 里零引用, 按「删模板连带清 CSS」纪律清除; `.ico-t-*` 本身**不是**死类(变体自带 `.dtNN-* .ico-t-*` 作用域色表, drawer.js 的 icoTone 仍在产类), 只清经典作用域那批。
- **保留 `DRAWER_TABLE_DEFS` 的变体行**: 四内容页签的表格体此后**全部**走变体桥描述符(variantTab/dyn 排序), 经典三行删除后 `ALL_TABLE_PAGES` 缩小 = 列选择器不再出现三个永不渲染的表分组。

## 实现计划

1. 流量变体: 删 3 个文件 + 三份 manifest 各 3 行 + drawer.html 图前/图后宿主 + 注册表 `slot` + `_dtFindHost` 双宿主分支 + `_drawerMenuTab` 的 `-pre/-post` 去后缀。
2. 档制单点: `CLASSIC_TABS/defaultSel/choices` + `_dtSel` + 菜单早退 + 渲染失败兜底改缺省档 + `initialDrawerTpl` 防御字面量同步。
3. 经典渲染链: drawer.html 双分支改单宿主; 删 `drawer_tabs.js` / `tpl/drawer-tabs.html` / 三个单元格渲染器 / app.js 四处组件注册 / 经典三表 def + columns.js 六个 computed + state 六个排序字段 + 四个经典专用方法; `TABLE_COLUMNS` 与 `DRAWER_TABLE_DEFS` 摘经典行。
4. 死 CSS: 三皮肤按「选择器含死类且余类在允许集内」批量清除。
5. 守阵与 e2e 同轮改写; `test.full` 记基线; 知识库回写。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 流量变体 13/14/15 + 双宿主 + slot 摘除 | ✅ |
| 档制单点(CLASSIC_TABS/defaultSel/choices/_dtSel) | ✅ |
| 四内容页签经典渲染链整体删除 | ✅ |
| 三皮肤死 CSS 清除(~144 条) | ✅ |
| 守阵改写(6 个 pytest 函数) | ✅ |
| e2e 同轮改写(7 份 spec) | ✅ |
| test.full 基线切片 + 知识库回写 | ✅ |

## 进度日志

- **2026-10-14**: 开工先 `my-commit-flow.sync` → 已同步 `58a04851`。摸底: grep 经典/变体/13-15/双宿主/drawer_tabs/渲染器全链, 逐个核引用数定删除面; 二次确认范围与深度后开工。
- **改动**: 27 个源文件(+416/−778)+ 删 5 个文件(3 个流量变体 + `drawer_tabs.js` + `drawer-tabs.html`), 命中立档阈值(≥3 源文件)。
- **既有潜伏 bug 一并修**: 首轮全量 e2e 报 19 红, 其中一类是运行期崩溃 `Cannot destructure property 'bum' of 'e' as it is null`(Vue 拆组件)。二分钉到**变体表格体桥(Teleport)**: 桥的 `v-if` 与它所属的 `.dt-host` DOM 分支(`v-if="dtSplitOn"`)同帧翻转时, 拆桥会撞上「Teleport 目标被同帧移除」。经典渲染链在位时四内容页签默认**不带桥**(经典三表无 `tableId`), 所以该路径从不触发; 本变更把默认切到带桥的变体, 100% 暴露。修法 = 合并开关(`dtToggleMerge`)与视口门跨越(`_mergeOnResize`)改为**先熄桥**(`_dtBridgesOff()`, 只摘 `on`)、**下一拍**再翻 `drawerMerge`/`dtWinW` —— 第一帧单独卸桥(锚还在文档里), 第二帧才拆分支; 另在 `_dtUnmountOne` 里把 `on` 的摘除从「按当场扫到的锚」改为**全表摘除**(锚可能已不在宿主里, 漏摘的桥会带着已被摘掉的 Teleport 目标活到下一拍)。
- **e2e 同轮重锚(7 份 spec, 非放宽容忍)**: 空态容器 `.empty` → 变体自己的 `.dt07-empty`/`.dt04-empty`/`.dt10-load`; 表 id `drawerPeer/Tracker/File` → `drawerPeerV07`/`drawerTrackerV04`/`drawerTrackerV06`/`drawerContentV10`; 模板菜单的右键目标从「.drawer-body 中心」改为「**行**」(表头 `@contextmenu.stop` 独占右键, 点中心会弹列菜单), 且点完菜单项后须等 `.ctx-menu` **离场**(pop 过渡期间仍盖在原位, 会把随后的拖宽/排序 mousedown 吃掉); `dt-live-update` 的速度实时断言改为按对端地址 `10.0.0.0` 定位行(07 默认按 upspeed 降序, 首行不是 dl_speed 会变的那一格)。
- **收口验证**: `test.full` **3199 passed / 4 skipped / 0 failed**(TOTAL 99%, 覆盖率 98.65%); `dev.e2e` **236 passed / 10 skipped, 0 failed**(6.6m)。

## 遗留

- **内容页「重命名…」已随经典移除**(用户拍板接受): 变体 10/11/12 均无重命名入口; 若要恢复, 应作为变体侧新功能单独立项, 不属本轮回滚面。
- **渲染失败兜底降级**: 四内容页签的兜底从「经典」改为「该页签首个变体」; 缺省档自身抛错时该页签留空 + console.error(不再有第二实现可退)。

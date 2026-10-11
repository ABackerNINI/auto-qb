# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W2 已落地

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**(Vue 3 组件重建 · 收敛为声明式密度变体 · 按页签分波替换 · 三列表注册进 `<aq-table>`)。**W0** = 冻结契约与验收基线; **W1** = 数据层抽离(`drawer.js` → `drawer_store.js`, 零观感变化, A/B DOM dump 逐字节等价); **W2**(本轮)= 四页签 Vue 重建 + Tracker/用户/文件三表接壳 —— 用户追加拍板「**全部一起做**」(四页签同波, 不逐页签停)与「**Vue 连变体一起声明式实现**」(变体路线定为声明式, 本体归 W5), 接壳形态取「**div 网格, 与主视图完全同源**」, 观感边界取「以『与主视图一致』为准则, **观感变化整体接受**」。本轮 `test.full` 与 W0/W1 基线**逐位相同**(3129 passed / 4 skipped), 新增 6 项真浏览器手势(四条新 pin 逐条红验), 数字见基线切片。W3–W6 待起。
>
> 最后活动: 2026-10-11 22:59

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/26-10-11-2259-webui-drawer-refactor-w2.md

## 本轮完成 (W2)

- **四页签转 Vue 组件**: 新增 `shared/drawer_tabs.js`(`AQ_DRAWER_{GENERAL,TRACKERS,PEERS,CONTENT}_COMPONENT`, 只贡献模板 + 最小实例态, 数据/动作一律 `$root` 回调根实例, **不复制任何方法实现**)与 `shared/tpl/drawer-tabs.html`; `tpl/drawer.html` 的 `dt-host` 骨架改成 `v-if="dtVueTab(tab)"` 组件 / `v-else` 旧宿主**互斥**(单一挂载点); `drawer_pages/{general,trackers,peers,content}-classic.js` 四件删除。
- **三列表接壳**: 新增**独立注册表** `DRAWER_TABLE_DEFS`(三个列模型常量 + 每表独立 `sort.gk/gd` + `headRef: null`)与合壳 `ALL_TABLE_DEFS`/`ALL_TABLE_PAGES`(= 主视图 `TABLE_DEFS` 合并抽屉三表); 三个行模型渲染器 `aq-{tracker,peer,file}-cells`; `columns.js` 五个遍历点 + `tableDefs` 改吃新壳、`_headEl` 补 DOM 兜底; `sort.js` 的 `_sortKeys(scope)` 改成「scope 即表 id」+ `sortedDrawer`/`_sortVal`; `state.js` 加六个排序字段; 三皮肤 CSS 成对。
- **修掉的真 bug**: 抽屉表头右键连带弹**两个** `.ctx-menu`(面板「选模板」右键入口在 `.drawer-body`, 表头在其内不拦冒泡)⇒ 表头改 `@contextmenu.prevent.stop`。这条只有真浏览器抓得住。
- **验收**: `test.full` = 3129 passed + 4 skipped / `TOTAL 16517 151 5626 134 99%`(与基线逐位相同); `e2e/drawer-tables.spec.mjs` 6 项全绿; 四条新 pin 逐条注入回归红验(rc=1)。

## 三处非显然的判断(下轮别再踩)

1. **抽屉表头在页签组件内 ⇒ 根实例 `$refs` 取不到它** —— `columns.js::_headEl` 必须有 DOM 兜底(`document.querySelector('.group-head[data-table="<id>"]')`)。只按 `$refs` 实现时症状是「拖宽**完全没反应**且**不报错**」, 静态守阵看不见, 只有真手势能抓。
2. **排序 scope 与表 id 解耦是零回归的关键**: `_sortKeys(scope)` 改成 `ALL_TABLE_DEFS[scope] ? scope : VIEW_TABLE[viewMode]` —— 主视图调用点传的 `tableId` 恰好等于原解析结果, 故主视图一行未改; 抽屉三表则各得独立排序键。若反过来给抽屉表硬编码 scope, 就会出现「点抽屉列头排的是主视图」。
3. **表格单元格必须是网格行的直接子元素** —— 行模型渲染器用多根 `v-for="col in cols"` **不套包裹 `div`**, 因为 `colAlignCss` 生成的 `:nth-child(n)` 对齐规则与 `gridStyle` 都按「第 n 个子元素 = 第 n 列」定位; 套一层包裹会让对齐整体错位(且无报错)。

## 待办 / 移交

- **W3–W6 待起**: W3 = 流量页签与形态收敛; W4 = 合并双列 + 右键模板选择(接壳后 `_drawerMenuColByX` 的坐标兜底需复核是否仍需要 —— 列结构由 `.dt-col` 变成了组件渲染, 但两条兜底锚 `data-dt-host`/`data-dt-tab` 仍在); W5 = 15 个过程式变体 → 声明式密度变体; W6 = 退役第二套渲染技术。
- **⚠ 需用户拍板的遗留**: 旧实现「条件属性整段拼进 `dtHtml` 插值 ⇒ 引号被 `esc` 转义 ⇒ 类名里带引号 ⇒ 按类名写的 CSS 全线静默失效」, 迁移后的四页签已由 Vue `:class` 自然修好(**观感变化**: 跳过态变灰 / 选中行高亮**首次生效**); 但 **15 个变体文件仍带同一缺陷**。回灌修法还是留到 W5 整体退役时一并消失 —— 未决, 见坑档 `pitfalls/web-ui/esc-attr-quote-dead-class.md`。
- **cap 债务(加深)**: `memory-bank/modules/webui-static-contract.md` 早超 evergreen cap, 本轮又增一条; 清理需另开新会话(`commands run doc.caps -- --strict`)。
- **切片数债务**: 本轮新增切片后 `kb.check` 报「切片数 72 > 70」(非本轮引入), 需另开新会话收口。

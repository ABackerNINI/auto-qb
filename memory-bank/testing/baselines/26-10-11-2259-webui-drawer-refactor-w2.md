# 3129 —— WEBUI 抽屉重构 W2 四页签 Vue 重建 + 三列表接壳(26-10-11-2106 计划)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-11-2136-webui-drawer-refactor-w0w1.md

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W2** —— 四个页签(general / trackers / peers / content)正文改由全局 Vue 组件承载(`shared/drawer_tabs.js` + `tpl/drawer-tabs.html`), `drawer_pages/*-classic.js` 四件退役; Tracker / 用户 / 文件三张列表从真 `<table class="drawer-table">`(无列模型)换成与主视图**同源**的 `<aq-table>` div 网格, 经**独立注册表** `DRAWER_TABLE_DEFS` 并入合壳 `ALL_TABLE_DEFS`(主视图 `TABLE_DEFS`/`TABLE_PAGES` 语义零改)。与 W0/W1 不同, **这是一波有观感变化的重建**(三列表换 DOM 形态 + 表头在面板内不吸顶), 用户 26-10-11 拍板「以『与主视图一致』为准则, 观感变化整体接受」, 逐项登记在计划 §05 W2「落地」条与 §11 变更记录。故本切片的判据**不是**「A/B DOM dump 逐字节等价」(那是 W1 的判据, 只对零观感变化的纯搬迁成立), 而是: ① `test.full` 与基线**逐位一致**; ② 全量 e2e 通过数 = 基线 + 本轮新增用例数, **零失败**; ③ W2 的四件验收动词(拖宽 / 排序 / 右键隐藏 / 行键盘在面板内可用)各有**真实浏览器手势**断言且逐条红验。
> 基线时间: 2026-10-11 22:59

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `9b0d6f41`; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3129 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial; 本轮 30.68s, `test.full` 总 32.6s)
- **与上基线(`26-10-11-2136-…-w0w1`)逐位相同** —— 本轮**没有增删任何 pytest 用例**, 只改既有守阵的读取面/断言面(同轮同数, R8 口径不放宽), 故通过数、跳过数、覆盖四项数字与语句/分支分母必须一字不动。

## e2e 实测

- 命令: `commands run dev.e2e`(Windows; 桩 `scripts/ui_harness.py` 由 webServer 自动起, 默认档 ok/on/on/300)
- **实测 (Windows)**: **164 passed + 0 failed + 10 skipped**(4.3m)
- **与上基线对账**: 上片 **158 passed** + 本轮新增 **6 项** = **164** ✅ 逐位对齐预期(不是"数字大了就行" —— 差一项就说明有用例静默失效或漏跑)。
- **本轮新增的 6 项**(`e2e/drawer-tables.spec.mjs`, 3 用例 × 2 皮肤, 双皮肤逐条通过):
  1. `Tracker 列表: 拖宽 / 排序 / 右键隐藏 / 列偏好持久化` —— 拖 `.resizer` +60px → 首列 grid 轨道加宽; 点「状态」列头 → **本表**箭头唯一出现; 表头右键 → `隐藏「消息」` 且**模板菜单不出现**; `reload` 后仍是 5 列; 列选择器里三表成组且能勾回「消息」。
  2. `面板开着行键盘仍可用并驱动面板跟随(W2 第四件)` —— 双击开面板 → `ArrowDown` → 列表光标落到下一行(`.torrent-row.kb-cursor` 的 `data-hash` 变化) → 面板 `hash` 在防抖内跟随且**不关**。
  3. `单栏: 正文右键弹当前页签模板选择 + 变体/经典单一挂载点` —— Tracker 页签正文右键出 trackers 变体集(状态卡片栅格)且**不出** general 的(英雄行·键值栅格); 选变体 → 宿主带 `.dt-tpl` 而 Vue 网格**消失**; 选回经典 → 反向。**四支既有 spec 同轮改锚点**(非放宽): `drawer-peers` / `drawer-merge` 的 `table.drawer-table tbody tr` → `.group-row[data-table=…]`, 通过数与改前一致。

## W2 验收四动词 × 红验(「按下去到底行不行」的记录)

计划 §05 W2 验收的四件, 逐件钉在真浏览器上, 并逐条做**注入回归红验**(改回错法 → 用例必须红):

| 验收件 | 断言位置 | 红验注入 | 结果 |
|---|---|---|---|
| 拖宽 | 用例① | **摘掉** `columns.js::_headEl` 的 DOM 兜底 | rc=1 (红 ✓) |
| 排序 | 用例① | 表壳排序 scope 传 `undefined`(落回主视图) | rc=1 (红 ✓) |
| 右键隐藏 | 用例① | 表头 `@contextmenu.prevent.stop` → 去掉 `.stop` | rc=1 (红 ✓) |
| 行键盘在面板内可用 | 用例② | 把 `drawer.open` 塞回 `_kbOverlayBusy` 名单 | rc=1 (红 ✓) |
| (附) 单栏模板右键锚点 | 用例③ | `_drawerMenuTab` 兜底回落改成固定 `general` | rc=1 (红 ✓) |

- 补充红验(守阵侧): 把 `drawerFile` 混进 `TABLE_DEFS` → `test_frontend_table_registry_single_point` rc=1(红 ✓, 证明「抽屉 id 不在 `TABLE_DEFS` 体内」那条 pin 有效)。

## 增量明细(本轮真正新增/改动)

- **源(四页签)** —— 新增 `webui/static/shared/drawer_tabs.js`(`window.AQ_DRAWER_{GENERAL,TRACKERS,PEERS,CONTENT}_COMPONENT`)+ `webui/static/shared/tpl/drawer-tabs.html`; `tpl/drawer.html` 的 `dt-host` 骨架改 `v-if="dtVueTab(tab)"` 组件 / `v-else` 旧宿主; `drawer_pages/{general,trackers,peers,content}-classic.js` **删除**(4 文件)。
- **源(三表接壳)** —— `shared/app.js`: 三个列模型常量 `DRAWER_{TRACKER,PEER,FILE}_COLUMNS` + `DRAWER_TABLE_DEFS` + `ALL_TABLE_DEFS`/`ALL_TABLE_PAGES` + 三个 `app.component` 注册, 四处逐表遍历改吃新壳; `shared/columns.js`: `_headEl` DOM 兜底 + 五个遍历点与 `tableDefs` 改吃新壳 + 三个 grid/可见列 computed; `shared/sort.js`: `_sortKeys(scope)` 语义改「scope 即表 id」+ `sortedDrawer`/`_sortVal`; `shared/table.js` + `tpl/xtpl-cells.html`(→ 300 行, cap 400): 三个行模型渲染器; `shared/state.js`: 六个排序字段; `shared/drawer.js` / `drawer_tabs.js`: `drawerTrackerRows`/`drawerPeerRows`/`drawerFileRows` 补 `_raw` 与统一出口; `tpl/xtpl.html`: 表头右键 `.stop` + 排序 scope 传 `tableId`。
- **CSS** —— 三皮肤成对追加(抽屉作用域 `position:static` / `.group-row` 指针与态类 / `.mono-cell` / 省略号): `atlas/css/dialogs.css`、`console/css/dialogs.css`、`prism/css/components.css`。
- **测试** —— 新增 `e2e/drawer-tables.spec.mjs`; `e2e/drawer-peers.spec.mjs` / `e2e/drawer-merge.spec.mjs` 同轮改锚点; 守阵 `tests/test_webui_static_skins.py`(`test_frontend_table_shell_single_point` 组件面 9 项 + xtpl-cells 7 模板 + 抽屉三处调用点; `test_frontend_table_registry_single_point` 新增 W2 块)/ `tests/test_web_shortcuts.py` / `tests/test_webui_static_dom_panel.py` 同轮改(口径不放宽)。
- **坑档** —— 新增 `pitfalls/web-ui/esc-attr-quote-dead-class.md`(旧实现条件属性整段拼进 `dtHtml` 插值 ⇒ 引号被 `esc` 转义 ⇒ 类名带引号 ⇒ `.virtual/.skipped/.sel` 规则全线静默失效; 迁 Vue 后**首次生效**)。
- **文档面** —— 计划 `26-10-11-2106-*`(§05 进度注 + W2「落地」条 + §07 落地偏差注 + §11 变更记录) + 任务档案 `26-10-11-webui-drawer-refactor.md` + 本切片 + `activeContext/26-10-11-2259-webui-drawer-refactor.md` + `modules/webui-static-contract.md`(新增「抽屉三列表接入公共表壳」条, 并修正「抽屉 3 表无列模型」的陈旧口径)。

## 风险 / 观察

- **本轮的判据不是 DOM 逐字节等价** —— W2 主动换了三列表的 DOM 形态(真 `<table>` → div 网格), 与主视图同源是**目的**而非副作用。若拿 W1 的 sha256 口径来卡 W2 必然"红", 那是口径误用; 该换的是判据(改用「验收动词 + 既有 e2e 逐位」), 见摘要段。
- **`_headEl` 的 DOM 兜底是这次唯一的"不兜底就静默烂掉"点**: 抽屉表头在页签组件内, 根实例 `$refs` 取不到; 只按 `$refs` 实现时拖宽的失败形态是**毫无反应且无报错**, 静态守阵与 pytest 都看不见 —— 只能真手势(用例①)。
- **排序 scope 改成「表 id」是零回归的关键**: 主视图调用点传的 `tableId` 恰好等于原 `VIEW_TABLE[viewMode]` 解析结果, 故主视图一行未改; 抽屉三表则各得独立 `gk/gd`(`dtrkSortKey` / `dpeerSortKey` / `dfileSortKey`)。反之若给抽屉表硬编码 scope, 症状是「点抽屉列头排的却是主视图」。
- **行模型单元格必须是网格行的直接子元素**(多根 `v-for`, 不套包裹 `div`): `colAlignCss` 的 `:nth-child(n)` 与 `gridStyle` 都按"第 n 个子元素 = 第 n 列"定位, 套包裹即整体错位且无报错。
- **表头右键必须独占**(`.prevent.stop`): 面板把「选模板」右键入口挂在 `.drawer-body` 上, 表头在其内; 不拦冒泡就同时弹两个 `.ctx-menu` —— 这条是**本轮真浏览器抓出来的真 bug**, 静态侧完全看不出。
- **⚠ 未决遗留(需报告用户)**: 旧实现的「条件属性拼进 `dtHtml` 插值」缺陷, 迁移后的四页签已由 Vue `:class` 自然修好(**观感变化**: 跳过态变灰 / 选中行高亮首次生效); 但 **15 个变体文件仍带同一缺陷**, 是否回灌修法还是留到 W5 整体退役时一并消失 —— 未决(坑档 `esc-attr-quote-dead-class.md` 已记「不许静默修」)。
- **债务**: `modules/webui-static-contract.md` 超 evergreen cap(25,728 > 20,000 字符, 本轮加深 —— 又增一条回写); `kb.check` 报「切片数 72 > 70」(本轮新增切片后触发, 非本轮引入)。两项均**不拦提交**, 需另开新会话收口。
- W3–W6 待起(W3 = 流量页签与形态收敛; W4 = 合并双列 + 右键模板选择; W5 = 15 变体 → 声明式密度变体; W6 = 退役第二套渲染技术)。

# WEBUI 表格公共组件 · P0 表注册表落地

> 摘要: 专题 `webui-table-component` 开工。用户「把辅种表/追剧表抽成公共模板组件(拖拽换位/拖宽/点击排序/右键隐藏), 方便后续重构详情页用户列表/文件列表/设置各种表」→ 计划 [26-10-11-1722](../plans/26-10-11-1722-plan-webui-table-component.html) 出稿; 用户定调「详情面板问题很多, 后续完全重构、不考虑兼容」后同文件修订(详情面板移出迁移范围 / DOM 适配降级为条件项 / D1 改单适配 / 新增风险 10); 用户「按推荐开始实施」。**P0 已落地(零行为变化)**: app.js 新增表注册表 `TABLE_DEFS`(每张表一行: 列定义 / 宿主 ref / grid 与可见列 computed 名 / 行窗口化 kind / 排序键), `TABLE_PAGES` 由它派生; `columns.js` 的 `gridStyle`/`_headEl`/`_winContainer`/`_winGapOf`/`_ensureWinTop`/`_measureRowH`/`recomputeEffective`/`colAlignCss` 与 `sort.js` 的 `_sortKeys`/`_resetSort` 一律按 id 取, 十处页字面量与 ref 名映射清零。模板 / CSS / DOM 结构零改动。
> 最后活动: 2026-10-11 17:48

## 正在进行

- 专题在办(P1 待起): P1 = 抽 Vue 全局组件 `<aq-table>` 并先只接辅种表; 验收 = 真浏览器 DOM 逐字节等价。
- 本会话实测数字见 `commands run kb.baseline`(本会话切片 `26-10-11-1748-webui-table-registry-p0`)。

## 关键结论

- **盘点改变落点(最重要的一条)**: 用户要的四项交互**行为早已单点** —— `shared/columns.js`(显隐/重排/调宽/对齐/持久化/行窗口化) + `shared/sort.js`(三态排序)。**没单点的是模板**: 表头块 5 份、单元格 `v-if` 分支 127 条(groups 49 / shows 50 / torrents 28)、成员明细行 2 份逐字近似、列选择器 4 段、横滚同步 3 份、页枚举字面量 18+ 处。⇒ 后续各步的重心是**抽表壳 + 注册表化**, 不是重写交互。**再遇到"要统一某类前端实现"的需求, 先分清"行为单点"与"模板单点"再定落点。**
- **表身份单点 = `TABLE_DEFS`(app.js 顶部)**: `columns` / `headRef` / `tableRef` / `grid` / `cols` / `window` / `sort`。`grid`/`cols` 存 **computed 名**(模板仍用 `groupGrid`/`visibleGroupCols` 这些既有名字, 只是 id→名字的映射收了单点)。**新增一张表 = 注册表加一行 + `state.js` 加排序字段, 不升 `COLS_STORE_KEY` 版本**(升版本会清空用户手调的宽/隐/序, 见 [pitfalls/web-ui/columns-persist.md](../pitfalls/web-ui/columns-persist.md))。
- **行窗口化的 kind ≠ 表 id**: 明细表 id = `detail` 而 kind = `member`(`member` 无表定义 ⇒ `_winGapOf`/`_ensureWinTop` 回 `null` ⇒ 走 `.detail` 父容器, 与旧分支等价)。做表壳抽取(P1)时必须保留这层"无独立滚动容器"的语义。
- **P0 为什么能保证零行为变化**: ①列定义常量原样保留(守阵 `_scan_column_cells_paired` 按 `const 名 + 模板字面` 扫, 注册表只引用 ⇒ 守阵不用动); ②`_measureRowH` 的私有签名按注册表现算, `map(...).join("|")` 与旧模板串逐字节相同; ③`_resetSort` 的目标值(最近添加降序 / 最近动静降序 / 空键)与 `state.js` 初值逐项对齐。**验证 = 全量 `test.full` 与上一片基线六项数字全等**(数字见 kb.baseline), 而非"看着像没变"。
- **坑(复发)**: Edit 工具改 `shared/sort.js` 把整份写成 CRLF(`git diff --stat` 只显示改动行, 靠 `git status` 的 CRLF 警告露头), 已按字节归一回 LF; 已在 [pitfalls/git/editing-traps.md](../pitfalls/git/editing-traps.md) 记 `复发 +1`。**定式: 改完任何文本文件跑一次 `git status` 扫 CRLF 警告, 与改的是哪个目录无关。**

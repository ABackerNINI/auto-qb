# 26-09-25 WebUI 展开态跨视图记忆(辅种 ⇄ 种子 ⇄ 追剧)

> 摘要: 用户报「辅种界面切到种子界面再切回, 展开的分组会收起来」。根因是 `setViewMode` 里三行
> `expandedKey / expandedShows / expandedShowEp = null` 把展开态随切页丢掉。改为**按视图分桶暂存**
> (`expandMemo`): 切走收进桶 + 清空实时字段, 切回还回该视图最后一次的展开(**还回前验那一行还在**);
> 同步把 `groupWin` 的退避判据从"expandedKey 非空"改成"展开的组确实在可见集合里"。
> 触发: 展开态, 切视图收起, expandedKey, expandMemo, groupWin 退避, 辅种页, 种子页, 追剧页
> 最后活动: 2026-09-25 18:35

## 状态

**Done(2026-09-25, 已入库 `2541c4e`)。** 全量 `test.full` **1607 passed + 1 skipped / 0 failed**;
浏览器冒烟 102 项 0 失败(红绿双验)。⚠ 该提交同时带上主线 `441ffe4` 遗留的
`pitfalls/testing/tmpdir.md` 超 cap 修复(否则闸门必红)。

## 关键判据

- 展开态是"我正盯着这一组"的**临时意图**, 与 `page` / `viewMode` 同类(判断据见
  [ui-location-persist.md](../pitfalls/web-ui/ui-location-persist.md) 同名条目), 切走再切回应还在。
- **不能直接删掉那三行置空**: 展开态确实不该串台到别的视图(种子视图没有展开概念)⇒ 正确形状是分桶,
  不是"留在原字段不管"。
- **还回必须验存活性**: 组可能已被删/被筛掉。留悬空的 `expandedKey` 会让 `groupWin` **永久**退避行窗口
  ⇒ 大库上悄悄退化成全量渲染(界面完全正常, 只是滚动变卡, 没人会往这里想)。
- 纯内存, **不落盘**: 展开是临时意图, 与"停在哪一页"不同级, 刷新后不还原;`_logout` 一并清桶。

## 改动面

- `shared/app.js`: data 加 `expandMemo`; 新增 `stashExpandState` / `restoreExpandState`, `setViewMode`
  改为 stash → 切 → restore;`_logout` 清桶。
- `shared/columns.js`: `groupWin` 退避判据加 `.some(k => k === expandedKey)`。
- `tests/test_web.py`: 新增静态守阵 `test_frontend_expand_state_survives_view_switch`
  (禁"切页置空"回潮 + 必须验存活性 + groupWin 判据同步); 同步头部测试计划清单。
- 知识库: `pitfalls/web-ui/ui-location-persist.md` 新增条目 + 触发词;`systemPatterns/web-responsiveness.md`
  订正"有 expandedKey 即退避"的表述。

## 真浏览器冒烟(已跑, 含红绿双验)

- **跑法**: 本 clone 没有 `node_modules`, 但 playwright 在 **npx 缓存**里 —— 用
  `NODE_PATH='C:\Users\11059\AppData\Local\npm-cache\_npx\<hash>\node_modules' node scripts/ui_smoke.cjs …`
  即可(`playwright-core@1.63` ↔ 缓存里的 `chromium-1243` 对齐)。桩服务另起一份(走 task id,
  命令与端口口径见 [../pitfalls/testing/smoke.md](../pitfalls/testing/smoke.md) ——
  **它会一直 serve 不会自己退出**, 必须单独后台跑; 默认端口常被别的 clone 占着)。
- **绿**: 全量 **102 项 0 失败**(prism + atlas 各 51), 本修复的 4 条断言全过。
- **红**: 把 `setViewMode` 临时改回旧行为(三行置空)⇒ 「切回辅种视图: 展开的组还在」**报红**
  (`expandedKey=null / .detail 0 个`), 其余 47 项仍绿 ⇒ 这条守阵确实咬得住, 不是恒绿。
- **取证截图**: `.workbuddy-ai/tmp/ui-smoke/expand-{1-展开后,2-切到种子页,3-切回辅种页}.png`
  (临时脚本 `.workbuddy-ai/tmp/expand-cross-view-shot.cjs`, 不入库)。

## 遗留

- `ui_smoke.cjs` 里新加的 4 条断言依赖"首行组行可点开" —— 若将来组行改成需要点 caret 才展开,
  这条会红(会如实报 FAIL, 不中断整轮)。

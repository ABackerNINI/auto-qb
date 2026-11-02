# 派生状态快照被渲染期无条件消费

> 摘要: 派生状态(如"未归组命中")在事件落袋时被存成**快照**, 渲染期却按**当前**数据无条件消费 —— 快照与真值分叉后同一实体画两遍; 修法是渲染期用当前源现算判据 + 双条件闸, 而非在快照里打补丁
> 触发: 搜索, 虚拟行, 未归组, 重复行, u- 行, searchUncovered, 派生快照, 渲染期判据, filteredGroups, 跨视图, 归组关系变化, search_rev 不变, 同一 hash 两行
**Refs:** memory-bank/tasks/26-11-03-webui-search-uncovered-dedup.md

### 事件时快照 + 渲染时无条件追加 = 同一实体两行

- **触发**: 把「某实体在某刻属于哪一类」(如 `searchUncovered` = 搜索落袋时未归组的命中)存成事件时快照,
  渲染期却直接 append 到列表、不与**当前**归组/命中真值复核。归组关系一跨视图变化(种子页首轮
  `/api/state?view=torrent` 不回 groups ⇒ `this.groups=[]` ⇒ 所有命中被判未归组; 切辅种页后真实组到位),
  同一 hash 就被画成「真实组行 + `u-<hash>` 虚拟行」两遍; `search_rev` 不变时自动重查不会救场, 滞留到手动重搜。
- **判别**: 列表里同一 hash 出现两次(真实行 + 虚拟/兜底行); `vm.searchUncovered` 长度与 `vm.groups` 的成员
  关系不自洽; 只切视图(不改任何数据)就能稳定复现 —— 说明是前端派生面而非后端数据重复
  (`/api/search` 每 hash 至多一条, 组 key 与虚拟行 key `u-` 不会合并)。
- **处置**: 判据在**渲染期**用未过滤真值现算(与落袋时同一口径): `filteredGroups` 用 `this.groups` 全部成员 hash
  建 `groupedNow`, 虚拟行循环最前过两道闸 —— `if (!hits.has(r.hash)) continue`(已在命中集)与
  `if (groupedNow.has(r.hash)) continue`(已归组); 两道闸必须排在所有 facet 过滤与 `kept.push` **之前**。
  惰性构建(仅待兜底快照非空), 无搜索态不加 O(n) 成本。同族: `poll-reseed-filter.md`(反向形态 —— 真值变了
  候选没重播种)。
- **守阵**: `tests/test_webui_static_skins_widget.py::test_frontend_search_uncovered_deduped`(按语义**位置**
  断言闸 < facet < push / 判据源 = 未过滤 `this.groups` / 消费点恰一处 / `filteredTorrents` 不得引入)
  + `e2e/search-uncovered-no-duplicate.spec.mjs`(三皮肤 × 4 场景, 含跨视图 stale groups 与删除时效)。
- **复发**: 0

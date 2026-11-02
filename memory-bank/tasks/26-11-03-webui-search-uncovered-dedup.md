# 26-11-03-webui-search-uncovered-dedup — 搜索未归组虚拟行去重(issue 26-11-03-0254)

**Status:** In Progress
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 搜索未归组虚拟行去重(issue 26-11-03-0254)
**Topics:** webui-search-uncovered-dedup
**Refs:** memory-bank/issues/26-11-03-0254-bug-search-uncovered-stale-virtual-row.html, memory-bank/pitfalls/web-ui/derived-snapshot-render.md

## 原始请求

1. 认领 `memory-bank/issues/26-11-03-0254-bug-search-uncovered-stale-virtual-row.html`(状态 In Progress, 认领链双向)。
2. 先只做修改计划 + grilling, 不动代码; 用户拍板 Q1-Q5 全按推荐后进入修复轮。
3. 修复轮口径: 方案 A —— `filteredGroups` 追加虚拟行前用**当前 `this.groups`** 建归组判据, 并加「已在 hits / 已归组」两道闸; 判定用未过滤 groups, 与 `doSearch` 一致; 三皮肤共享, 不改后端 / `/api/search` 契约 / `search_rev`。
4. 测试: 新增三皮肤 e2e spec 覆盖 4 个场景; 扩展静态守阵, 断言**语义顺序**而非仅变量名。
5. 验证: 定向用例 + `test.full` + `dev.e2e` 实测; 删除时效按 ≤1 搜索刷新周期验收; 性能先不加缓存。
6. 范围守恒: 不入本次范围的问题只入池不修; 不碰 `config.yml` / `auto-qb-data/`; 不跨仓库; 本轮不 commit / push。

## 思考过程与决策

- **根因**: `searchUncovered` 只是 `doSearch` 落袋那一刻的快照(`view.js`), 而 `filters.js::filteredGroups`
  渲染期无条件追加 —— 归组关系变化(跨视图 stale groups / 新增成员并入 / 配置开关)或命中集变化后,
  同一 hash 会被画成「真实组行 + u- 虚拟行」两遍; 若 `search_rev` 不变则不触发自动重查, 滞留到手动搜索。
  另两处疑点已证伪: `/api/search` 每 hash 至多一条; 虚拟行键 `u-<hash>` 不会与真实组 key 合并。
- **取舍 A(采用) vs B/C/D**: A = 渲染期用未过滤 `this.groups` 现算 `groupedNow` + 两道闸, 单点收敛、
  与 `doSearch` 的 `grouped` 同口径、零状态形状改动; B(在每个 groups 变化入口重算快照)需枚举所有入口,
  易漏; D(改状态形状/模板)爆炸半径过大; C(不修)达不到「删除时效 ≤1 刷新周期」的验收。
- **语义顺序是判据的一部分**: 两道闸必须排在所有 facet 过滤与 `kept.push` **之前** —— 否则虚拟行会先过
  facet 再被挡, 或挡在 push 之后等于没挡; 静态守阵按位置断言(不认变量名)。
- **性能**: `groupedNow` 惰性构建(仅 `searchUncovered` 非空时), 无搜索态不增加每次渲染的 O(n) 成本;
  用户拍板暂不加缓存。
- **e2e 场景按桩能力落形**: 桩合成种子全部已归组且运行期 `add_torrent` 的新种子恒落在「未归组」侧
  (增量归组相位不在 `_refresh_torrents` 里跑), 桩也不支持热改分组配置(`reload_config` 只回执不应用)
  ⇒ 计划初稿的「add 同路径种子成组」「设置页关/开分组」不可达; 改用**跨视图 stale groups**
  (首屏落种子页时 `this.groups=[]` ⇒ 命中全判未归组, 切辅种页后旧快照重画)复现同一根因。
- 计划 `memory-bank/plans/26-11-03-0120-plan-webui-search-auto-refresh.html`(本件是该计划「相邻缺陷」的落地跟踪)。

## 实现计划

1. `static/shared/filters.js::filteredGroups`: `const hits = this.searchHits` 后惰性声明并构建 `groupedNow`
   (遍历 `this.groups` 全部成员 hash); 虚拟行循环最前加 `if (!hits.has(r.hash)) continue;` 与
   `if (groupedNow.has(r.hash)) continue;`, 均排在 facet 与 `kept.push` 之前。
2. `tests/test_webui_static_skins_widget.py`: 新增 `test_frontend_search_uncovered_deduped`, 按语义位置断言
   (判据源 = 未过滤 `this.groups` / 惰性构建 / 两道闸 < facet < push / 消费点恰一处 / `filteredTorrents` 不得引入),
   并同步头部「## 测试计划」。
3. 新增 `e2e/search-uncovered-no-duplicate.spec.mjs`(三皮肤 × 4 场景): 首搜跨视图 / 叠加分类筛选 /
   命中删除后 ≤1 刷新周期消失 / 视图往返幂等; 运行期增删走桩控制面并在 afterEach 清理。
4. 验证: 定向静态守阵 + `commands run test.full` + `commands run dev.e2e -- e2e/search-uncovered-no-duplicate.spec.mjs`。
5. 收尾: issue 置 Done 留证据; 基线切片; 坑档; `kb.wrap` / `kb.index` / `kb.check`; 认领链双向。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| T1 | `filters.js` 渲染期 `groupedNow` + 两道闸(排在 facet/push 之前) | Done(2026-11-03) |
| T2 | 静态守阵 `test_frontend_search_uncovered_deduped` + 测试计划清单 | Done(2026-11-03) |
| T3 | `e2e/search-uncovered-no-duplicate.spec.mjs`(三皮肤 4 场景) | Done(2026-11-03) |
| T4 | 定向静态守阵 + `test.full` + `dev.e2e` 实测 | Done(2026-11-03) |
| T5 | issue 置 Done / 基线切片 / 坑档 / kb.check / 认领链双向 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

本轮一轮落地: 渲染期两道闸 + 静态守阵 + 三皮肤 e2e + 全量实测, issue 置 Done; 根因与取舍见上,
测试数字见 `kb.baseline` 最新切片(本件不再手抄), 坑档 `pitfalls/web-ui/derived-snapshot-render.md`。
- 2026-11-03 04:48 修复搜索未归组虚拟行重复/滞留: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet 与 push 之前); 静态守阵按语义位置; e2e 三皮肤四场景; 全量见 kb.baseline

- 2026-11-03 04:54 修复 issue 26-11-03-0254: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet/push 之前); 静态守阵按语义位置 + 三皮肤 4 场景 e2e; 全量见 kb.baseline; issue 置 Done

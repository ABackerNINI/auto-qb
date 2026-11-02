# 4925 passed + 2 skipped —— 搜索未归组虚拟行去重修复收尾基线

> 摘要: 搜索未归组虚拟行去重修复收尾基线
> 基线时间: 2026-11-03 04:52
**Refs:** memory-bank/issues/26-11-03-0254-bug-search-uncovered-stale-virtual-row.html

## 验收数字

`commands run test.full` 实测(收尾文档回写后复跑, 161.3s):

```text
TOTAL                                                22543    134   7736    128    99%
4925 passed, 2 skipped, 3 warnings in 159.15s (0:02:39)
```

口径注记:
- 全量 1 轮, 3 条 warning 为既有存量; 2 skipped 为环境跳过用例。
- 定向静态守阵(`test.one` 跑 `test_frontend_search_uncovered_deduped` + `test_frontend_search_pending_no_collapse`
  + `test_frontend_search_auto_refresh_wiring`)3 条全绿。
- `commands run dev.e2e -- e2e/search-uncovered-no-duplicate.spec.mjs`: 三皮肤 × 4 场景 12/12 全绿
  (含删除用例重跑 3/3 全绿)。

## 本改动面

- `src/auto_qb/webui/static/shared/filters.js`: `filteredGroups` 在 `const hits = this.searchHits` 后惰性构建
  `groupedNow`(遍历渲染时未过滤的 `this.groups` 全部成员 hash), 虚拟行循环最前加「已不在命中集」与「已归组」
  两道闸, 均排在 facet 过滤与 `kept.push` 之前。
- `tests/test_webui_static_skins_widget.py`: 新增 `test_frontend_search_uncovered_deduped`(按语义位置断言:
  判据源 / 惰性构建 / 两道闸 < facet < push / 消费点恰一处 / `filteredTorrents` 不得引入), 同步头部测试计划。
- `e2e/search-uncovered-no-duplicate.spec.mjs`(新增): 三皮肤 × 4 场景 —— 首搜跨视图切辅种页 / 叠加分类筛选 /
  命中删除后 1 个刷新周期内虚拟行消失 / 视图往返幂等; 运行期增删种子走桩控制面并在 afterEach 清理。

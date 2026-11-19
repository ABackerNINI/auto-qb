# 6485 passed + 6 skipped —— 排序三态默认升序键 no-op 修复收尾基线

> 摘要: 6485 passed + 6 skipped —— 排序三态默认升序键 no-op 修复收尾基线
> 基线时间: 2026-11-19 21:52

## 验收数字

实测树: develop 分支 tip 105c093f + 本批工作树(修复 + 守阵 + 回写文档)。`commands run test.full` 实测(2026-11-19 21:4x, 150.3s):

```
TOTAL                                                28915     44  10322     61    99%
6485 passed, 6 skipped, 7 warnings in 148.28s (0:02:28)
```

单跑守阵 `test_r4_sort_domain`(battery 真跑)1 passed(覆盖率门限单跑不满足, 全量已达标); 静态守阵 `test_webui_static_skins_table` + `test_webui_static_r4_static_batteries` 25 passed。评审零发现(检 0/0); ship.gate 全绿。

## 本改动面

- `src/auto_qb/webui/static/shared/sort.js`: `setSort` dyn 与经典两分支第三击复位前加默认升序键判据(`cell.key===defKey && defDir===1` 翻降序), 修复默认列三击全 no-op(IP 列点了没反应); 非默认列/defDir=-1/空 defKey 表零行为变化。
- `tests/test_webui_static_r4_node_batteries.py`: `_NODE_SORT_PROBE` 增 dPos(addr/1)/dEmpty 两表与默认列三态断言组; docstring 测试计划同步。
- `e2e/drawer-peers-variant-tables.spec.mjs`: dt07 用例在点「下载」列前插入点 addr 列头验 aria-sort 与行序翻转的三击回归。
- KB: 新坑档 `pitfalls/web-ui/sort-default-asc-tristate-noop.md` + `kb.index` 重生成; `architecture/webui.md` 增排序引擎单点小节并回写摘要/触发词; 本基线切片。

# 6180 passed, 2 skipped —— WEBUI 种子详情 tooltip 清理 S5 回归全量基线

> 摘要: WEBUI 种子详情 tooltip 清理 S5 回归全量基线
> 基线时间: 2026-11-15 11:47

## 验收数字

`commands run test.full` 实测(2026-11-15 11:47, Windows 开发机):

```text
TOTAL                                                27436     72   9646     77    99%
6180 passed, 2 skipped in 133.98s (0:02:13)
```

- 汇总: 6180 passed / 2 skipped, 覆盖率 99%(TOTAL 行 27436 语句 / 72 未覆盖 / 9646 分支 / 77 partial; Windows 闸 99.5 差异面见 conftest COVERAGE_FLOOR 单点, 实测表尾 99% 由 pytest-cov 出), 耗时 133.98s (0:02:13)。
- 与上一切片的差值口径见 `memory-bank/testing/baseline.md`, 本切片不重复。

## 本改动面

- 修复 P2 实施直接引入的破损: `src/auto_qb/webui/static/shared/drawer_tpl/05-trackers-health-groups-low.js:313` 的 `data-fold">`(删 title 残留孤立引号)精确修为 `data-fold>`(只删孤立 `"`); 全库仅此一处破损, `node --check` 通过。
- 守阵补最小回归钉: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_tooltip_prune_static_guard` 末尾补 2 断言 + 1 注释(「P2 删 title 残留孤立引号的回归钉」), 断言 `data-fold">` 不在该 05 文件内容且 `data-fold>` 在位; 红绿双验(临时加回破损串必红 / 恢复必绿)已过。
- 其余产品代码零改动(本批仅修 P2 破损, 无计划外改动)。

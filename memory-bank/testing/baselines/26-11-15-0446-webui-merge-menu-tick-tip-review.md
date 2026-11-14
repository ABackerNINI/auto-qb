# 6137 passed, 2 skipped —— 提交轮评审修复后全量绿: 勾/tooltip 守阵三组红验

> 摘要: 提交轮评审修复后全量绿: 勾/tooltip 守阵三组红验
> 基线时间: 2026-11-15 04:46

## 验收数字

`commands run test.full` 实测(2026-11-15 04:46, Windows 本机, 评审修复轮工作树):

```
TOTAL                                                27305     68   9588     73    99%
6137 passed, 2 skipped in 155.21s (0:02:35)
```

覆盖率 99%。e2e 另计: `dev.e2e -- e2e/drawer-merge.spec.mjs` 14 passed(54.8s, prism/atlas 双皮肤, 含新增的门跨越置灰态勾断言); 定点 `test.one -- -k test_drawer_tpl_menu_right_click_selection` 1 passed。

三组红验逐组实测(2026-11-15): ①`dtMergeOn` 回潮 `dtMenuMergeOn` → 静态守阵 1 failed + e2e 双皮肤 2 failed(关态 `.ctx-tick` Expected 0 / Received 1); ②`:title` 加回合并项 → 静态守阵 1 failed(「合并项又挂 title」) + e2e 双皮肤 2 failed(`[null, "功能说明文案"]` ≠ `[null, null]`); ③临时摘关态断言 + 回潮勾绑定 → e2e 双皮肤 2 failed 恰报「再关 0 勾」行(Expected 0 / Received 1), 前一行 `toBeVisible` 先通过。三组还原即绿。闸门预跑首轮曾在无关用例 `test_cmd_resync_keeps_schedule_when_nothing_moved` 出计时假红(gap 1.60s vs 1.4), 单跑 1 passed、重跑 ship.gate 全绿, 零代码改动。

## 本改动面

- `e2e/drawer-merge.spec.mjs`: 评审轮补「再关 0 勾」段合并项在场 `toBeVisible` 兜底(防 `toHaveCount(0)` 恒绿), 「门跨越」用例补窄视口置灰态 1 勾真断言 + Escape 收菜单
- `memory-bank/pitfalls/web-ui/ctx-menu-item-state-tip.md`: 「标志保留」证据引用校正为「门跨越」置灰态勾断言; 守阵段补三组红验逐组数字
- `memory-bank/testing/baselines/26-11-15-0324-webui-merge-menu-tick-tip.md`: 红绿双验段落由一组扩为三组, 「本改动面」e2e 条目同步
- `memory-bank/active-context/26-11-15-0325-webui-merge-menu-tick-tip.md`: `kb.wrap` 追加 R1 行(评审修复与红验结论)
- `kb.index` 重建(坑档正文修订后索引自洽)

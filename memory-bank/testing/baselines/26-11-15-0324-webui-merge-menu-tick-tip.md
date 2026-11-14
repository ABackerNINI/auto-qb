# 6137 passed, 2 skipped —— 抽屉右键合并菜单勾选态与提示修复批全量绿

> 摘要: 抽屉右键合并菜单勾选态与提示修复批全量绿
> 基线时间: 2026-11-15 03:24

## 验收数字

`commands run test.full` 实测(2026-11-15 03:21, Windows 本机, 本批工作树):

```
TOTAL                                                27305     68   9588     73    99%
6137 passed, 2 skipped in 242.28s (0:04:02)
```

覆盖率 99%。e2e 另计: `dev.e2e -- e2e/drawer-merge.spec.mjs` 14 passed(评审补钉后复跑 54.8s, prism/atlas 双皮肤); 定点 `test.one -- -k test_drawer_tpl_menu_right_click_selection` 1 passed。

红绿双验(2026-11-15 三组, 评审补钉守阵后逐组实测): ①把 `dtMergeOn` 改回 `dtMenuMergeOn` → 静态守阵 1 failed + e2e 双皮肤 2 failed(关态 `.ctx-tick` Expected 0 / Received 1); ②把 `:title` 加回合并项 → 静态守阵 1 failed(「合并项又挂 title」) + e2e 双皮肤 2 failed(`[null, "功能说明文案"]` ≠ `[null, null]`, 原生 title 已单向迁成 `data-aq-tip`); ③单独验「再关 0 勾」非安慰剂(临时摘关态断言 + 回潮勾绑定) → e2e 双皮肤 2 failed 恰报在该行 `toHaveCount(0)`(Expected 0 / Received 1), 前一行 `toBeVisible` 先通过。三组全部还原即绿。

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/ctx-menus.html`: 抽屉右键「合并页签」项的勾 `v-if="dtMenuMergeOn"` → `v-if="dtMergeOn"`(真实开关态), 摘掉该项 `:title`(自绘 `.aq-tip` z90 恒被 `.ctx-menu` z100 盖住), 头注同步
- `src/auto_qb/webui/static/{atlas,prism,flux,console}/css/components.css`: 四皮肤置灰规则注释删「title 提示」口径(零 CSS 规则改动)
- `tests/test_webui_static_dom_panel_drawer.py`: `test_drawer_tpl_menu_right_click_selection` §4 增三条静态断言(勾读 `dtMergeOn` / `dtMenuMergeOn` 不得回潮 / 合并项零 title), 头部「测试计划」该条同步
- `e2e/drawer-merge.spec.mjs`: 首例增关态 0 勾、项上 `title`/`data-aq-tip` 双 null、再关后 0 勾三处断言; 文件头用例清单同步; 评审轮补「再关 0 勾」段菜单项在场 `toBeVisible` 兜底 + 「门跨越」用例窄视口置灰态 1 勾断言(坑档证据口径随之校正)
- `memory-bank/conventions/webui.md`: 「悬浮提示」增高层浮层内部不写 title 的边界 + 新增「菜单勾选态」条
- `memory-bank/pitfalls/web-ui/ctx-menu-item-state-tip.md`: 新坑档(两条目: 恒真形态判据当状态 / 提示被菜单盖住), `kb.index` 已重建

# 4007 passed + 2 skipped(根) —— WEBUI 设定位置下拉: 高亮滚动只滚菜单内部(八修)后全量基线

> 摘要: WEBUI 设定位置下拉: 高亮滚动只滚菜单内部(八修)后全量基线
> 基线时间: 2026-10-29 04:12
**Refs:** memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md, memory-bank/pitfalls/web-ui/hover-keynav-fight.md

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`, 2026-10-29 04:05 实测):

```
  TOTAL                                                20981     98   7088    100    99%
  Required test coverage of 99% reached. Total coverage: 99.28%
  4007 passed, 2 skipped in 124.71s (0:02:04)
```

- 汇总行: **4007 passed + 2 skipped(根)**; 覆盖率 99.28%(门槛 99)。
- 逐条口径注记:
  - 用例数 4006 → **4007**(+1): 新增静态守阵 `test_frontend_combo_hiscroll_never_scrolls_ancestors`(八修, 剥注释后禁 `scrollIntoView` + 钉 `box.contains(n)`/`n === box` 有界走法)。同步在 `tests/test_webui_static_dom_panel.py` 头部「## 测试计划」清单补一行 —— 漏补会让 `test_test_plan_docstring_guard.py::test_repo_plan_matches_defs` 判红(本轮实测过一次)。
  - 「2 skipped(根)」是既有的根级用例, 与本轮无关。
  - ⚠ **并行偶发**: 同一天连续两次全量, 第一次红在 `tests/test_hr_discovery.py::test_runtime_discovery_bind_failure_keeps_data_endpoint`(与本轮改动零交集: 只碰前端 JS/CSS/模板), 单跑绿、紧接重跑全量绿 ⇒ 判为并行端口抢占偶发, **未定位**(首次红的 traceback 没留存, 只留了汇总行; 复现时先存 traceback 再动手)。
- e2e(`commands run dev.e2e -- --grep @fast`, 端口 8137, 2026-10-29 04:20 实测): **226 passed (7.5m)**, 比七修那轮 224 +2 = 八修两皮肤各一条 `选中候选后再点下拉 · 弹窗文案不滑动 @fast`。
- 单文件复跑(`e2e/move-dialog-fit.spec.mjs` 全 12 条): 12 passed (41.0s) —— 含八修红验后恢复的整轮。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/webui/static/shared/add_torrent.js` | `_hiScroll` 弃用 `scrollIntoView`, 改「从高亮项逐级向上、以菜单根为界」手动差值调 `scrollTop`(block: nearest 语义); 注释里记清八修根因与实测帧数 |
| `tests/test_webui_static_dom_panel.py` | 新增 `test_frontend_combo_hiscroll_never_scrolls_ancestors`(静态守阵) + 头部「## 测试计划」清单补一行 |
| `e2e/move-dialog-fit.spec.mjs` | 新增两皮肤 `选中候选后再点下拉 · 弹窗文案不滑动 @fast`: 逐帧采 `body.scrollTop` + 文案 `top`, 反向守卫 `hiVisible()` 证滚动跟随仍生效 |
| `memory-bank/pitfalls/web-ui/hover-keynav-fight.md` | 「复发: 0」→「复发: 1」, 记其自身处置 ④ 的 `scrollIntoView` 禁令从未落到 `_hiScroll` 单点 |
| `memory-bank/tasks/26-10-29-webui-move-dialog-pick-geometry.md` | 标题/摘要升到八修, 原诉求补第 8 条, 子任务 S15–S18, 进展 R5/R6 |
| `memory-bank/activeContext/26-10-29-0107-webui-move-dialog-pick-geometry.md` | 摘要行 + R4/R5/R6 |

**未改**: 三皮肤 `dialogs.css`(五修几何原样)、`tpl/combo-input.html`(六/七修原样)、`tpl/move-dialog.html`。

**红验**(临时回退即红): 把 `_hiScroll` 循环还原成 `scrollIntoView` ⇒ 两皮肤均报 `开层全过程 .add-dialog-body 的 scrollTop 必须恒 0(祖先容器被滚动 = 弹窗文案滑动)` + 静态守阵判红; 恢复后 12 passed。

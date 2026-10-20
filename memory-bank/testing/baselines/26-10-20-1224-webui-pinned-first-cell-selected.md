# 3770 passed + 10 skipped(根) —— 必显列: 选中行保留行底

> 摘要: 必显列: 选中行保留行底
> 基线时间: 2026-10-20 12:24

**Refs:** memory-bank/activeContext/26-10-20-1224-webui-pinned-first-cell-selected.md

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20362    390   6982    262    98%
3770 passed, 10 skipped in 179.12s (0:02:59)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过(98%)。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件): `328 passed, 10 skipped (11.9m)`, 0 failed;
  含本轮新增的 6 条(`e2e/main-table-pinned-selected.spec.mjs`: 三主表 × 双皮肤, 选中 + 悬停选中)。
  日常门口 `npm run test:e2e:fast` 本轮同样跑过: `202 passed (7.1m)`。
- 红绿双验(本轮, 三处独立):
  ① 静态守阵: 把 atlas 的 `.group-row.selected` 还原成裸 `var(--sel-bg)` ⇒
     `test_frontend_pinned_first_cell_selected_row_keeps_base` 红, 报「行底被半透明 tint 替换了
     (background 末层不是 --bg-row)」; 还原后绿。
  ② e2e: 同一处回退 ⇒ atlas 三例全红(辅种/种子表报行板 `rgba(99,109,191,0.23)` /
     `rgba(28,35,56,0.686)` 半透明; 追剧表报 `backgroundImage` 行板 `none` vs 首格渐层); 还原后 6 例全绿。
  ③ 像素探针(修复前后各一跑): 首格与相邻列同相对位置取色, 选中行 atlas Δ9/255、prism Δ5/255 →
     修后 prism Δ0、atlas ≤1(取整); 未选中行两侧全 0。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/{prism,atlas,console}/css/views.css` | `.group-row.selected` / `.group-row.partial` 从「裸半透明 tint 替换行底」改为「同色 `linear-gradient` 叠 `var(--bg-row)`」(与吸左首格镜像同一表达式); `.member-row.selected/.partial` 拆出单独规则, 保持裸柔底(无吸左首格, 承光底是 `.detail` 的 `--bg-sunken`) |
| `tests/test_webui_static_skins.py` | 新增静态守阵 `test_frontend_pinned_first_cell_selected_row_keeps_base`(三皮肤 × selected/partial: 行板 background 末层必须是 `--bg-row`、tint 与首格同字面、首格镜像同基色、`.member-row.selected` 拆分后仍在)+ 文件头测试计划一行 |
| `tests/test_web_shortcuts.py` | `test_sel_visual_parity_and_site_cell` 口径随结构调整: 由「成员行与组行**同一条规则文本**」改钉「同一 tint 令牌 + 同吃左色条规则 + `.member-row` 保 position: relative」(原断言与「组行要合成、成员行不要」冲突, 会假红) |
| `e2e/main-table-pinned-selected.spec.mjs` | 新增行为守阵(三主表 × 双皮肤, 6 例): 真手势 Ctrl+click 选中后 —— 行板 backgroundColor 不透明 + 行板与首格 backgroundColor/backgroundImage **逐字相等**(含指针压在选中行上) |
| `memory-bank/pitfalls/web-ui/frozen-column.md` | 新增 §⑩「半透明状态底是叠加不是替换」+ 触发词 + 守阵登记 |

未触及: 抽屉各面的按面重锚色值(`shared/dt_table.css`)、`.group-row.expanded` 的 `--bg-sunken` 合成
(实测残差 Δ5(atlas)/2(prism), 低于可辨阈, 已记坑档 §⑩)、列模型/可见列、轮询与数据面。

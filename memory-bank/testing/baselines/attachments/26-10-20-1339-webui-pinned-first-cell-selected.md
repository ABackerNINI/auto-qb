# 3771 passed + 10 skipped(根) —— 必显列: 选中/半选/展开行保留行底

> 摘要: 必显列: 选中/半选/展开行保留行底
> 基线时间: 2026-10-20 13:39

**Refs:** memory-bank/activeContext/26-10-20-1224-webui-pinned-first-cell-selected.md

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20362    390   6982    262    98%
3771 passed, 10 skipped in 193.94s (0:03:13)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过(98%)。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件): `332 passed, 10 skipped (11.9m)`, 0 failed;
  含本轮新增的 4 条展开行用例(`e2e/main-table-pinned-selected.spec.mjs` 内, 辅种表/追剧表 × 双皮肤)。
- 进程内两条独立红绿双验(本轮, 都是「展开行」这一面):
  ① 静态: 把 atlas 的 `.group-row.expanded` 还原成裸 `var(--bg-sunken)` ⇒
     `test_frontend_pinned_first_cell_expanded_row_keeps_base` 红, 报「行底被半透明下沉底替换了
     (background 末层不是 --bg-row)」; 还原后绿。
  ② e2e: 同一处回退 ⇒ atlas 两条展开用例红(辅种表/追剧表), prism 两条仍绿(只回退 atlas);
     还原后 10 例全绿。
- 像素探针(辅种页, 修复前后各一跑): 展开行 atlas Δ5/255、prism Δ2/255 → 修后两侧均 Δ0;
  同页其余状态(plain / expanded+selected / partial / 横滚后 selected)全 ≤1(取整)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/prism/css/views.css` | `.group-row.expanded` 由裸 `var(--bg-sunken)` 改为「同色 `linear-gradient` 叠 `var(--bg-row)`」(+根因注记) |
| `src/auto_qb/webui/static/atlas/css/components.css` | 同上(注释改为**行内注记** —— 该文件已顶 700 行 cap, 见下) |
| `src/auto_qb/webui/static/console/css/components.css` | 同上(多行注释, 有余量) |
| `src/auto_qb/webui/static/console/css/views.css` | console 独享的 `.group-row.expanded:hover { background: var(--bg-sunken) }` 同步改成叠底 —— 不改则悬停展开行那一下首格与行板重新分家 |
| `tests/test_webui_static_skins.py` | 新增静态守阵 `test_frontend_pinned_first_cell_expanded_row_keeps_base`(三皮肤: 行板末层 `--bg-row` / 首格镜像同基色 / console 的 `expanded:hover` 不得跌回裸 sunken) + 文件头测试计划一行 |
| `e2e/main-table-pinned-selected.spec.mjs` | 新增 4 条展开行用例(辅种表/追剧表 × 双皮肤): 展开行板不透明 + 与首格 backgroundColor/backgroundImage 逐字相等, 含悬停; 文件头补展开态段落 |
| `memory-bank/pitfalls/web-ui/frozen-column.md` | §⑩ 增「同族拓展」段(展开态 Δ5/2 → 0, console hover 覆盖的陷阱) + 守阵登记 |
| `memory-bank/pitfalls/web-ui/css-file-line-cap.md` | **复发 +1**: 本轮把 atlas `components.css` 顶到 702 行被守阵抓住; 记「为何没命中」= 用 `(Get-Content).Count` 量行数少计 51 行, 判据改为 `wc -l` / Python 逐行; 并记「行内注记」这一压行手法 |

未触及: 抽屉各面的按面重锚色值(`shared/dt_table.css`)、列模型/可见列、轮询与数据面。
上一轮(选中/半选行)的改动与数字见 `memory-bank/testing/baselines/26-10-20-1224-webui-pinned-first-cell-selected.md`。

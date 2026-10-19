# 3764 passed + 10 skipped —— 必显列悬停闪竖带(首格过渡与行板同源)

> 摘要: 必显列悬停闪竖带(首格过渡与行板同源)
> 基线时间: 2026-10-20 01:54

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20362    390   6982    262    98%
3764 passed, 10 skipped in 206.10s (0:03:26)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过(98%)。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件, 非 @fast 子集)本轮跑了**全套**:
  `318 passed, 10 skipped (11.0m)`, 0 failed。含本轮新增的 6 条
  (`e2e/main-table-pinned-hover.spec.mjs`: 三主表 × 双皮肤, 滑入/移出逐帧)。
- 红绿双验(本轮): 抽掉三皮肤首格那行 `transition` ⇒ 静态守阵红(atlas 先报)且 e2e 6 条全红
  (报「必显列首格缺 background 过渡」); 还原后静态绿 + e2e 逐帧差全为 0。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/{prism,atlas,console}/css/views.css` | 各 +1 条: `.group-row > :first-child` 补 `transition: background-color var(--dur) var(--ease)`(+根因注记)。行板 `.group-row` 的 160ms 过渡一字未动; 首格色值/吸左/发丝线/按面重锚全不变 |
| `tests/test_webui_static_skins.py` | 新增静态守阵 `test_frontend_pinned_first_cell_hover_transition_parity`(钉行板时长基准 `background var(--dur)` / 三皮肤首格同源声明 / 首格悬停镜像在位 / 禁字面毫秒)+ 文件头测试计划一行 |
| `e2e/main-table-pinned-hover.spec.mjs` | 新增行为守阵(三主表 × 双皮肤): ①行板与首格 background 过渡时长相等且非零 ②滑入/移出各 rAF 逐帧采 ~32 帧, 首格 vs 行板逐通道差 ≤ 2(修复前实测 14/18) ③稳态同色且确实变过色(防「两边都没变」空过) |
| `memory-bank/pitfalls/web-ui/frozen-column.md` | 新增 §⑨「首格镜像底色必须连过渡一起镜像」+ 触发词 + 守阵登记 |

未触及: 行板过渡参数、各面按面重锚的色值规则(dt_table.css)、列模型/可见列、轮询与数据面。
渐层状态(expanded/selected/search-hit)的离散替换仍为已知残留(机制层, 未量), 见坑档 §⑨。

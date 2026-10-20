# webui-pinned-first-cell-selected

> 摘要: 修 WEBUI 三主表选中行必显列异色竖带: 选中态用半透明 tint 替换了行底(承光层变页底 --bg), 与吸左首格按 --bg-row 合成分家(真浏览器逐像素 Δ9/255 atlas、5/255 prism, 未选中行 Δ0); 三皮肤改为「同色 linear-gradient 叠 --bg-row」与首格同一表达式, 成员行拆出保持裸柔底; 静态 + e2e 双守阵(修后 Δ0/1), 全量 pytest 与 e2e @fast 全绿
> 最后活动: 2026-10-20 13:27

**R0(2026-10-20 12:24):** 修 WEBUI 三主表选中行必显列异色竖带: 选中态用半透明 tint 替换了行底(承光层变页底 --bg), 与吸左首格按 --bg-row 合成分家(真浏览器逐像素 Δ9/255 atlas、5/255 prism, 未选中行 Δ0); 三皮肤改为「同色 linear-gradient 叠 --bg-row」与首格同一表达式, 成员行拆出保持裸柔底; 静态 + e2e 双守阵(修后 Δ0/1), 全量 pytest 与 e2e @fast 全绿

## 用户诉求

上一轮(切片 webui-pinned-first-cell-hover)修完悬停闪竖带后遗留的一条: 「选中的行必显列背景与其它列不一致」。
修完后用户又追加「group 一同修」—— 把同族最后一条半透明状态(组行展开)也收掉。

## 本轮过程

1. 开工同步: `commands run my-commit-flow.sync` 快进 `5ce3e295 → 4eef60fe`。
2. 真浏览器像素探针(Playwright 截图 + PIL 取色, 脚本 `tmp-analysis/probe-selected.mjs`): 三主表 × 双皮肤 ×
   四态(plain / expanded / selected / selected-hover), 首格与相邻格取**同相对位置**的像素。
3. 反解承光层: 相邻列可见底 ≈ `--bg`(atlas #0e1218 / frost #f2f6fb), 首格 ≈ 局部 `--bg-row` ⇒
   选中态两侧合成基色分家。
4. 三皮肤 views.css 把 `.group-row.selected/.partial` 从「裸半透明 tint(替换行底)」改为「tint 叠
   `--bg-row`(层叠)」—— 与首格镜像同一个表达式; `.member-row` 拆出保持裸柔底(无吸左首格、底由
   `.detail` 的 `--bg-sunken` 承光)。
5. 守阵: 静态 `test_frontend_pinned_first_cell_selected_row_keeps_base`(三皮肤/两态/末层 --bg-row/同 tint
   字面) + e2e `main-table-pinned-selected.spec.mjs`(三主表 × 双皮肤, 真手势 Ctrl+click 后行板 backgroundColor
   不透明 + 行板与首格 color/image 逐字相等, 含悬停); 两者均红绿双验。
6. 顺带修订既有守阵 `test_sel_visual_parity_and_site_cell`: 它钉的是「成员行与组行**同一条规则文本**」,
   与「组行要合成、成员行不要」的新结构冲突 —— 改钉「同一 tint 令牌 + 同吃左色条规则」。

## 关键事实

- 主表行板的真实承光底是**页底 `--bg`**, 不是 `--bg-row`: 行底被状态规则替换后, 露出的就是页底。
- 残差量级: 选中行 atlas Δ9/255、prism Δ5/255(整列高, 可辨); 未选中行 Δ0。修后 prism Δ0、atlas ≤1(取整)。
- 同族残差: expanded 原本 Δ5(atlas)/2(prism)(低于可辨阈, R0 未动) —— **R1 已同口径收掉**, 修后 Δ0;
  console 另有 `.group-row.expanded:hover` 覆盖, 同样要叠底(否则悬停展开行那一下又分家)。
- 选中瞬间不会错拍: 行板 `transition: background` 看似把 image 层纳进过渡, 实测两侧 `background-image`
  同帧出现(36/38ms, 0 帧不一致, 探针 `tmp-analysis/probe-select-transient.mjs`)。
- 抽屉变体面用 `.sel/.is-chk/.bad/.err`、不用 `.selected` ⇒ 本次主表规则不影响按面重锚(dt_table.css)。

## 产出

- `src/auto_qb/webui/static/{prism,atlas,console}/css/views.css`(三皮肤同改)
- `tests/test_webui_static_skins.py`(新守阵 + 模块测试计划清单)、`tests/test_web_shortcuts.py`(口径修订)
- `e2e/main-table-pinned-selected.spec.mjs`(新 e2e, 6 例)
- `memory-bank/pitfalls/web-ui/frozen-column.md` ⑩(半透明状态底是叠加不是替换)

**R1(2026-10-20 13:27):** 用户「group 一同修」⇒ 收掉同族最后一条半透明状态: 组行展开 .group-row.expanded 原本裸用 --bg-sunken(下沉底替换行底), 辅种页实测 Δ5/255 atlas、2/255 prism; 三皮肤改「同色 linear-gradient 叠 --bg-row」(prism views.css / atlas·console components.css), console 独享的 .group-row.expanded:hover 同款; 新增静态守阵 test_frontend_pinned_first_cell_expanded_row_keeps_base + e2e 展开行用例(辅种/追剧 × 双皮肤), 两侧红绿双验; 途中撞 CSS 700 行 cap(atlas components.css 702 行) —— 行数测量用 PowerShell Get-Content 少计 51 行所致, 已用行内注记把文件拉回 700 并给坑档记复发

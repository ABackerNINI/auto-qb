# 表格几何变量单点(--tbl-pad-x / --tbl-gap): 变体改行几何必须同取

> 摘要: 引擎表格「列头与值格同缘」靠变量单点: 三皮肤 `.group-head` 与 `.group-row` 的横向内距都读 `--tbl-pad-x`(默认 14px)。变体只改行的内距、不在行容器作用域声明变量 ⇒ 列头留在皮肤默认 14px, 首格与行内容根整体错位(2026-10-16 05 面实测 14px, 两皮肤与 CI 一致)。
> 等级: L0
> 触发: 改变体表格 CSS, 改行内距, 列头没对齐, 列头与值格错位, 列头比行右移, 表头左边多一截, --tbl-pad-x, --tbl-gap, dt05, 05 健康分组, drawer_tpl 变体, 几何守阵, dt-table-layout-parity

### 变体改行的横向内距 ⇒ 必须在行容器作用域声明 --tbl-pad-x(W2 口径)

- **触发**: 给某变体面写 `.dtNN-list .group-row { padding: … }`, 或把行的横向内距改成 0(去引擎卡底、行改整宽容器)。
- **判别**: 列头的横向内距**不在变体里给** —— 三皮肤各有一条 `.group-head { padding: 7px var(--tbl-pad-x, 14px) }`, 行是 `.group-row { … padding: 10px var(--tbl-pad-x, 14px) }`; 变体在行上硬写数值, 两者立刻分叉。判别法(真浏览器量): `.group-head > .h-cell` 与 `.group-row > :first-child` 的 `getBoundingClientRect().left` 之差 —— |Δ| ≤ 1px 才算同缘; 比的**是行的内容根**(05 面是 `.dt05-rowin` 这类首格), 不是行板。
- **处置**: 变量值只在**变体行容器作用域**声明一处, 列头与行都读它 —— 06 先例 `.drawer .dt06-list { --tbl-pad-x:8px }` + `.group-row { padding:4px var(--tbl-pad-x, 8px) }`; 11 同(4px); 整宽面(05)声明 `0px` 且行内距写成 `padding:2px var(--tbl-pad-x, 0px)`。**别给列头另写 padding 补丁** —— 那是第二处事实源, 下次改变量又只动一半。列头 `display:none` 的面(04/10)无此约束, 但也不得以「修对齐」之名把列头复活。
- **守阵**: `e2e/dt-table-layout-parity.spec.mjs`(已达标面 × 两皮肤: 轨道数 / 列头格数 / 行格数三处相等 + 左缘 ±1px + text-align 一致); 静态对齐面由 `tests/test_webui_static_skins.py` 扫。
- **复发**: 1 —— 2026-10-16。`9b7ec767`(修 05 外壳接线: 外层 dt05-wrap 下补内层 .dt05-list)让 05 变体六条 `.group-row` 版式规则**由空转转为生效**, 行的横向内距从皮肤默认 14px 变成 0, 列头留在 14px ⇒ 05 面错位 14px。**为什么没命中**: 那次改动跑的是 @fast 快门禁(子集), 而几何守阵**不在 @fast 里** —— 只有全量 e2e 覆盖这一面, 于是红在 CI 上而不是本地。⇒ 改这类几何(行/列头内距、轨道数、列对齐)必须跑全量 e2e: `commands run dev.e2e`; 只跑 @fast 子集 = 假绿。
  - 附(已处置 2026-10-16): 全量 e2e 涨到 280 用例量级后**超出 `dev.e2e` 包内 600s 预算**(实测被引擎到点强杀) —— 用户拍板**抬该 task 的 timeout 到 1200s**(≈1.8× 实测 654s); 全量轮自此照常走 `commands run dev.e2e`。套件再涨就该重估(拆轮 / 与 CI 分工), 别再靠调数字顶。

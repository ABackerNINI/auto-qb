# 排序三态的隐藏前提: 默认排序键配升序(defDir=1)时, 点默认列三击全 no-op

> 摘要: `setSort` 三态循环(首击降序/再击升序/第三击复位默认)用 `(key, dir)` 二元组表示状态, 隐含前提「初始态不等于某一中间态」。当表描述符 `sort.defKey` 非空且 `sort.defDir === 1`(默认就按某列**升序**)时, `dtSortCell` 懒建的初始 cell 恰为 `{key: defKey, dir: 1}` —— 点击该默认列时, `cell.key !== key` 为假、`cell.dir === -1` 为假, 直接落第三击复位分支, 而复位目标正是 `(defKey, 1)`, 等于没点。用户症状「IP 列/默认列点了没反应」, 无任何报错、箭头恒指默认列, 静态守阵(可排性判据/几何)全绿, 只有真跑 setSort 三态或真浏览器点击现形。defDir=-1 或空 defKey 的表无此问题(初始 dir=-1 命中第二分支翻升序; 空键表首击任意列都走换列降序)。
> 触发: 表头排序, 三态排序, 点了没反应, 排序不生效, 默认列排序失效, IP 列点不动, setSort, defKey, defDir, defDir 1, 默认升序, dtSortCell, 排序箭头, dyn 排序, 三态 no-op

## 条目

- **触发**: 给 dyn 表写 `sort: { dyn: true, defKey: "<列>", defDir: 1 }`(默认按某列升序), 或收到「某张表的默认排序列点不动/排序没反应」; 也适用于把某表默认方向从降序改升序的口径调整。
- **判别**: ①症状是「默认列看着能点、点了三下全没变化」—— 箭头方向、行序、aria-sort 任一时刻都不变; ②非默认列(如用户表的「下载」列)点击排序完全正常, 唯独默认列失效; ③看表描述符 `defKey` 与 `defDir`: defKey 非空 + defDir=1 即命中; ④静态守阵全绿(判据源/几何没错), 现有三态 node 电池若只测「换列首击」也不覆盖此路径 —— 必须真跑「点默认列第一击」。
- **处置**: `setSort` 第三击分支(同键升序)复位前加判据 `if (cell.key === k.defKey && k.defDir === 1) { cell.dir = -1; return; }` —— 默认升序列首击翻降序, 非默认列仍照常复位默认, 三态语义对其余列不变。dyn 与经典(gk/gd)两分支同口径补齐。**：**修根因而非把 defDir 改回 -1(那会破坏「默认按该列升序」的产品口径, 如用户表 IP 点分数值序升序)。
- **守阵**: node 电池 `tests/test_webui_static_r4_node_batteries.py::test_r4_sort_domain` 的 `dPos`(defKey=addr/defDir=1)断言组 —— 默认列一击降序/二击升序/三击再降序(非 no-op)、非默认列三击复位、空默认键表零误伤; e2e `e2e/drawer-peers-variant-tables.spec.mjs` dt07 用例点 addr 列头验 aria-sort 与行序翻转。红验: 修复前源码跑「默认列一击=降序」必失败(dir 恒 1)。
- **复发**: 0

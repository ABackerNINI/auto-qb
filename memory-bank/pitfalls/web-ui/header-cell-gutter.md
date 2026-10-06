# 表头格子给拖拽把手留的 10px 右内边距, 让右对齐列的表头与数值错位 11px

> 摘要: `.h-cell` 带 `padding-right: 10px` —— 这是给 `.resizer`(拖拽调宽把手)留的命中区, 因为 `.h-cell` 自身有 `overflow: hidden`(给列名省略号用), 把手伸到格子外会被裁掉、点不到(星图主题里有一条注释专门记着这个动机)。而值单元格 `.g-stat` / `.m-stat` 的 `padding-right` 是 **0**。右对齐时两边各自贴「自己内容盒的右缘」⇒ **表头文字恒比数值左偏 10px**(数据行有 1px 侧边框时 11px, 明细行无侧边框则恰好 10px)。左对齐列完全不受影响(两边都贴左缘, 表头左内边距为 0)—— 所以这个坑**只在右对齐列露头**, 且三套主题(atlas/console/prism)同源同错、错得一样多。同族第二个来源: 排序箭头若写成「恒在 DOM、只用 `opacity: 0` 隐藏」, 布局上仍占宽 —— 右对齐表头再被顶 11px(HR 明细表① 实测 14px = 箭头 11px + `margin-left: 3px`; **2026-10-06 已归正** —— 表① 该箭头改绝对定位不占流, 实测 14px -> 0px, 三主题一致)。
> 触发: 右对齐, 列对齐, 表头没对齐, 标题文字对不齐, 数值列, text-align right, h-cell, padding-right, resizer, 拖拽把手, 列宽拖拽, colAlignCss, nth-child, 排序箭头, arrow, opacity 0 占位, HR 在线核实表, num 列, 抽屉表, 表头与值同源

## 条目

- **触发**: 给表格列做右对齐; 收到「右对齐列没有真正对齐标题文字」; 或给表头加/改拖拽把手、排序箭头。也适用于「给某个格子加了内边距/占了位的东西」这类改动 —— 只要它只加在表头侧。
- **判别**: ①量**盒模型**: 表头格子内容盒右缘 `= getBoundingClientRect().right − paddingRight`, 值格子同理, 两者相减; 差 ≈10px 即命中(本仓 2026-10-06 实测: 分组/种子/追剧 11px, 明细 10px, HR 表① 14px)。②grep `padding-right: 10px` 是否只在 `.h-cell` 上(三主题各一处)。③grep 表头箭头是否**缺内层 `v-if`**(只靠 `opacity: 0` 隐藏 = 仍占位)。
  ⚠ **别拿「值文字墨迹右缘」当唯一判据**: 值宽于列宽时会被省略号截断, 墨迹量值能偏出 10px —— 那是列宽/省略号问题, 与对齐无关。判据以**盒模型差**为准; 要看墨迹请挑「值没溢出」的列。
  ⚠ 居中列不能量左缘差(左缘随内容宽度变化), 要比中线 —— 否则会得到 −7~−14px 的**假**错位。
- **处置**: 二选一 ——
  ①**最小**(单文件): 让值格子拿到同一右槽 —— 在 `shared/columns.js::colAlignCss()` 生成的规则里, 对 `align === "right"` 的列补 `padding-right: 10px`。该规则用 `:where([data-table=X]) > :nth-child(n)` 选择器, **同时命中表头与值格**, 且三主题共用同一份列模型 ⇒ 一处改、三套全好。代价: 右对齐列内容宽各 −10px, 数值与右邻列文字的间距 +10px。
  ②**彻底(2026-10-06 已采用 · 计划 26-10-06-1009)**: 把「把手槽」与「文字排版」解耦 —— 省略号下移到内层标签 `<span class="h-label">`, `.h-cell` 自身改 `display:flex; overflow:visible; padding-right:0`, 把手 `right:-5px` 跨进 grid 的 10px 列间距(半进半出, **不新增宽度开销**)。落地 = 5 个表头块 / 3 模板 + 3 主题 CSS + `columns.js::colAlignCss()` 给 right 列追加 `.arrow{order:-1}`。**实测**(桩服务 + headless Chromium, 三主题): 盒模型差 group/torrent **1px**(数据行 1px 侧边框, 允许 ±1)、detail **0px**(改前 11 / 10); 排序后仍 ≤1(改前 21~22)。
  ⚠ **不要**反过来直接把 `.h-cell` 的 `padding-right` 归 0 而**不挪把手**: 右对齐表头最后 10px 会落进把手命中区, **点标题会被判成拖宽**(把手 hit-test 优先)。彻底方案的前提正是「省略号先下移 → `.h-cell` 才能 `overflow:visible` → 把手才能外伸」。
  ⚠ **排序箭头**: 右对齐列要把箭头排到标签**左侧**(`.h-cell` 成 flex + `.arrow { order: -1 }`), 否则点一次排序标题会左右跳(实测 11px)。HR 表① 是**真 `<table>`**(`th` 是 table-cell, 不能改 `display:flex` —— 实测会把列宽撑爆, delta 172px), 它的箭头**已改绝对定位不占流**(2026-10-06, 计划 26-10-06-1009 §7 · 报告 26-10-06-0945 B1): `.hr-detail-table th .arrow { position: absolute }` + `th.sortable { position: relative }` —— 无偏移 = 取**静态位置**(仍紧贴标签右缘、`opacity` 揭示与 hover 语义全不变), 但不再参与行内布局 ⇒ 标签回到列右缘。实测 14px -> **0px**(三主题一致)。**别改回 `display:inline-block`**, 也别补内层 `v-if`(切换排序列时标题会左右跳, 与主表 P3 同形)。
  ⚠ **`0 值居中` 是同族第三处冲突(2026-10-06 已归正)**: `.g-stat.zero { text-align: center }`(2026-09-17 既有口径)让「值为 0」的格子居中, 与「右对齐列标题要对齐」直接冲突(用户截图里的「可用性 0.00」即此)。2026-10-06 判为**旧口径/文档漂移**(第九轮 D4 早已裁决取消、代码却留着) —— 三主题该规则已删, 0 值格回落 `colAlignCss` 注入的 `right`, 与同列表头同缘; `.zero` 的淡化配色保留。
  ⚠ **落地副作用(2026-10-06 实测)**: atlas `components.css` 原本顶在 **699 行**(单文件 700 行 cap), 新增的 `.h-label` 规则须放 `atlas/css/views.css`(见 [../../modules/webui-static-contract.md](../../modules/webui-static-contract.md)), 否则 `tests/test_web.py` 的「≤700 行」守阵红。
- **复发**: 0(2026-10-06 主表实施轮 + 同日的 HR 表① 补修轮均读取本档并照做, 未再踩)

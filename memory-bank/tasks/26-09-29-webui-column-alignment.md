# 26-09-29-webui-column-alignment — WEBUI 表格列对齐口径实施

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-10-06 11:09
**Summary:** 【26-09-29 口径实施 · 已完成】按 reports/26-09-28-2345 审计报告推荐实施列对齐口径: P1 明细/种子两表 completion_on + time_active 共 4 处 align right→left(时间/时长族 R4 统一左, 默认隐藏列低风险); P2 抽屉 3 表数值列 9 字段(Tracker 做种/用户, 用户 进度/下行/上行/已下载/已上传/关联度, 内容 大小/进度)th/td 挂 .num 类 + 三主题 CSS 各补一条右对齐规则。test.full 1831 passed / 3 skipped(91%), 见基线 26-09-29-0240。 【26-10-06 几何错位取证 · 待拍板】用户报「右对齐列没有真正对齐标题文字」—— 实测属实(只读轮次, 零代码改动): 主视图 4 表全部右对齐列偏 11px(明细表 10px, 根因 `.h-cell` 的把手槽 `padding-right: 10px`), 设置页 HR 表① 4 个 num 列偏 14px(排序箭头缺内层 `v-if`, `opacity:0` 仍占位), 三主题一致; 抽屉 3 表 / HR 表②③ 不受影响。报告 reports/26-10-06-0945, 见基线 26-10-06-0958。**Status 由 Done 重开为 Open: 修法选型与「0 值居中」口径待用户拍板。** 【26-10-06 10:37 实施完成 · Status Open → Done】按计划 plans/26-10-06-1009 落地「彻底方案」(报告 §5 P0/C1): ①模板 5 处列名加 `h-label`; ②三主题 `.h-cell` 改 flex + `overflow:visible` + `padding-right:0` + 新增 `.h-cell > .h-label` 省略号 + `.resizer` 挪进 10px 列间距(`right:-5px`); ③`columns.js::colAlignCss()` right 列追加 `.arrow{order:-1}`; ④三主题删 0 值居中规则; ⑤`e2e/smoke.spec.mjs` 加几何守卫(红绿双验); ⑥回写知识库。实测盒模型差 group/torrent 1px、detail 0px(改前 11/10), 排序后 ≤1(改前 21~22), 三主题一致; `dev.e2e` 6 passed; `test.full` 2676 passed + 4 skipped / 99%。 【26-10-06 11:09 范围外项补修】计划 §7 划出范围外的设置页 HR 表①(报告 §1 P2 / §5 B1, 14px)按该节推荐处置落地: 三主题 `.hr-detail-table th .arrow` 由 `display:inline-block` 改 `position:absolute`(无偏移取静态位置)+ `th.sortable` 补 `position:relative`; 实测 14px -> 0px(三主题一致, 标签仍紧贴箭头、hover/opacity 语义不变); `tests/test_web.py` 加静态守阵(红绿双验)。Status 保持 Done。
**Topics:** webui-column-alignment
**Refs:** memory-bank/testing/baselines/26-10-06-0958-webui-column-alignment-header-offset.md, memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/testing/baselines/26-10-06-1022-webui-column-alignment-plan.md, memory-bank/testing/baselines/26-10-06-1037-webui-column-alignment-fix.md, memory-bank/testing/baselines/26-10-06-1119-webui-hr-table-arrow.md

## 原始请求

用户: 「按推荐实施 memory-bank/reports/26-09-28-2345-report-webui-column-alignment.html」—— 落地该审计报告 §5 建议改动清单(最小 diff): P1 时间/时长族 4 处 align 改左; P2 抽屉表数值列右对齐; 分享率例外等 5 类明确不动。

## 思考过程与决策

- **P1 走列模型单点**: align 只改 app.js 两份列模型数组, 表头/值由 colAlignCss 同源注入自动生效, 三主题 CSS 零改动。两列均默认隐藏(hide: true), 默认视图不受影响。
- **P2 走模板挂类**: 抽屉表无列模型(机制性缺口), 报告建议 th/td 挂对齐类。类名选 `.num` —— 改前 grep 全 static/ 确认无占用(仅 `hr-num` 等复合名与 JS 变量, 不冲突)。
- **CSS 规则写成 `th.num, td.num` 双选择器一条**: 抽屉表 th 的既有 `text-align: left` 在同特异性下按源序被后置规则覆盖, td 无既有对齐规则, 一条即可覆盖两侧。
- **模板加载机制核实**: tpl/*.html 由三主题 index.html 声明、前端运行时 fetch 拼装(无构建步骤), 改源文件即生效。
- **明确不动**(报告 P3/既有口径): 分享率左对齐(2026-09-26 拍板例外)、4 主表进度列左(进度条部件)、H&R/站数/版本居中、.g-stat.zero 0 值居中、操作列 cell-act 右。
- **未新增守阵测试**: 纯对齐值改动; 列模型对齐已有"表头/值同源"机制保证, 抽屉 .num 无重复出现面(类挂在单一模板源, 三主题 CSS 由同一条规则串起), 暂无守阵收益点。

### 2026-10-06 追加 · 右对齐列「几何错位」取证(只读轮次)

> 上一轮把**口径**(哪列该左/该右)单点化了, 但**没验几何**: 口径一致 ≠ 表头文字与值文字落在同一竖线上。

- **现象**: 用户截图反馈「右对齐列没有真正对齐标题文字」(截图为种子页 已下载 / 可用性 两列)。
- **实测(桩服务 + headless Chromium, 基线 295bb226)**: 右对齐列的**盒模型**差(表头内容盒右缘 − 值内容盒右缘)——
  分组 / 种子 / 追剧 **11px**、组内明细 **10px**、设置页 HR 表① 4 个 num 列 **14px**、当前排序列再 **+11px**;
  三主题 atlas / console / prism **数值完全一致**; 抽屉 3 表与 HR 表②③ 为 **0**; 全站左对齐列 ≤1px。
- **根因①(主视图 4 表)**: `.h-cell { padding-right: 10px }` 是给 `.resizer`(拖拽把手)留的命中区 ——
  因 `.h-cell` 自身 `overflow: hidden`(列名省略号用), 把手伸到格外会被裁掉、点不到(星图主题有注释记此动机);
  值格子 `padding-right: 0` ⇒ 右对齐时两边各贴「自己内容盒的右缘」, 差 10px; 多出的 1px 来自数据行
  `border: 1px solid`(表头行只有 border-bottom)。**左对齐列不受影响**(两边都贴左缘) ⇒ 只在右对齐列露头。
- **根因②(HR 表① 14px)**: 表头箭头**缺内层 `v-if`**(SVG 恒在 DOM), 只用 CSS `opacity: 0` 隐藏 ——
  透明度不影响布局, 标签右缘恒被左顶 11px + `margin-left: 3px`。主表写法是空 `<span>`(宽 0), 只在真排到该列时占宽。
- **决策: 本轮只取证不修**。用户原话「先确定修改范围, 写一个报告」⇒ 只读轮次: 不入池 issue、不动代码。
- **待拍板(阻塞修法)**: ①修法 A = `shared/columns.js::colAlignCss()` 对 right 列补 `padding-right: 10px`
  (规则同时命中表头与值格, 三主题共用列模型 ⇒ 单文件全好; 代价 = 右对齐列内容宽 −10px) vs 彻底方案
  = 把手槽与文字排版解耦(省略号下移内层标签 + `.h-cell` 改 `overflow: visible` + 把手挪进 grid 间距;
  动 5 个表头块 / 3 模板 + 3 主题 CSS)。**不可**直接把 `.h-cell` 的 `padding-right` 归 0 ——
  右对齐表头末 10px 会落进把手命中区, 点标题被判成拖宽。
  ②`0 值居中`(`.g-stat.zero { text-align: center }`, 2026-09-17 拍板)与「标题右对齐」直接冲突 ——
  用户截图里的「可用性 0.00」即此; 要么 0 值也右对齐, 要么接受 0 值列看起来没对齐。
- **修正上一份审计的推论**: reports/26-09-28-2345 判「主表机制健康」指的是**口径单点化**(成立),
  但其「表头与值同源 ⇒ 不会错位」的推论**不成立** —— 同源只保证口径一致。
- **新增坑档**: `pitfalls/web-ui/header-cell-gutter.md`(未并入 `layout-css.md`: 后者 17.6KB 已超 12KB cap)。
- **复跑**: `commands run dev.harness -- --port 8099 --torrents 300 --groups 40` +
  `NODE_PATH=<workspace>/node_modules node .workbuddy-ai/tmp/measure2.cjs`(主表+抽屉) /
  `measure_shows.cjs` / `measure_hr.cjs`(HR 表① 用真实主题 CSS 做 DOM 复现 —— 桩不灌 HR 条目, 表① 不渲染)。
  判据: 右对齐列盒模型差必须为 0(允许 ±1)。

## 实现计划

1. P1: app.js DETAIL_COLUMNS(:120/:122) + TORRENT_COLUMNS(:158/:160) 的 completion_on / time_active align "right"→"left", 附 R4 口径注释。
2. P2: tpl/drawer.html 三张表数值列 th/td 挂 `.num`(20 处); 三主题(atlas·console 的 dialogs.css / prism 的 views.css)各补 `.drawer-table th.num, .drawer-table td.num { text-align: right }`。
3. test.full 验证 → 基线切片 → kb.index → 随主提交入库。

## 子任务状态表

| # | 子任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | P1 列模型 4 处 align 改左 | 完成 | app.js 两份列模型, 默认隐藏列 |
| 2 | P2 抽屉模板挂 .num 类 | 完成 | drawer.html 三表 20 处 |
| 3 | P2 三主题 CSS 右对齐规则 | 完成 | 每主题 1 条, 含口径注释 |
| 4 | test.full + 基线切片 | 完成 | 1831 passed / 3 skipped, 91% |
| 5 | kb.index 重建 + 入库 | 完成 | 随主提交 ship.commit |
| 6 | 全表右对齐几何实测(3 主视图 + 明细 + HR 表① + 抽屉, 3 主题) | 完成 | 实测 11 / 10 / 14px, 抽屉 0; 桩服务 + headless Chromium |
| 7 | 出取证报告 + 坑档 + 回写知识库 | 完成 | reports/26-10-06-0945 · pitfalls/web-ui/header-cell-gutter.md · 基线 26-10-06-0958 |
| 8 | **拍板修法选型**(A 值格补同宽右槽 vs 彻底解耦把手槽) | 完成 | 2026-10-06 用户裁决: 取**彻底方案**(报告 §5 P0/C1); `0 值居中` 判为旧口径/文档漂移, 一并归正 |
| 9 | 实施修法 + 复量至 0(允许 ±1) + 补守阵 | 完成 | 计划 plans/26-10-06-1009(PHASE 0-7) 全落地; 实测 group/torrent 1px、detail 0px; e2e 几何守卫红绿双验; test.full 2676+4/99% |
| 10 | **范围外项补修**: 设置页 HR 表① 排序箭头改绝对定位不占流(计划 §7 推荐处置) | 完成 | 三主题 `.hr-detail-table th .arrow` 改 `position:absolute`(去 `display:inline-block`)+ `th.sortable` 补 `position:relative`; 实测 14px -> **0px**(三主题一致); `tests/test_web.py` 静态守阵红绿双验 |

## 进度日志

- **2026-09-29 02:40**: 报告推荐全部落地, 5 文件 +24/-17, test.full 一次通过(基线 26-09-29-0240)。分享率等 5 类"明确不动"项未触碰。报告为冻结快照, 本档案为后续实施与效果回溯的单点。
- **2026-10-06 09:58**: 用户反馈「右对齐列没有真正对齐标题文字」⇒ 只读取证轮次(零代码改动)。实测确认两个独立机制
  (表头把手槽 10px + 数据行 1px 边框 ⇒ 11px; HR 表① 隐形箭头 ⇒ 14px), 三主题一致, 抽屉与 HR 表②③ 不受影响。
  报告 `reports/26-10-06-0945-report-webui-column-alignment.html`, 坑档 `pitfalls/web-ui/header-cell-gutter.md`,
  基线 `26-10-06-0958`。**Status Done → Open**: 修法选型与 `0 值居中` 口径待用户拍板, 未动代码、未入池 issue。
- **2026-10-06 10:09**: 用户拍板 —— ①修法取**彻底方案**(报告 §5 P0/C1: 把手槽与文字排版解耦, 非最小方案 A);
  ②`0 值居中` 判为**旧口径/文档漂移**(第九轮 D4 已裁决取消、代码与三主题 CSS 及知识库仍留), 正式实施时一并修复。
  出分步实施计划 `plans/26-10-06-1009-plan-webui-column-alignment.html`(doc-status **Open**, PHASE 0-7:
  模板标签内层化 → 三主题 CSS 解耦 → columns.js 箭头顺序 → 0 值口径归正 → e2e 几何守卫 → 验证 → 回写)。
  计划轮**未改任何代码**; 范围外已记 HR 表① 的 14px(报告 §5-B1, 机制不同, 计划 §7 给推荐处置)。
  认领链闭环: 报告 doc-refs ↔ 本计划(仅 meta 机械面); kb.index 重建绿; docmap --check 绿;
  `tests/test_docs_forms.py` 11 passed。**test.full 2676 passed + 4 skipped / 99%**
  (16021 语句 / 163 未覆盖 / 5472 分支 / 143 partial, 两次采样 62.92s / 51.69s), 与上一条纯文档基线
  0958 逐位持平 ⇒ 基线切片 `26-10-06-1022-webui-column-alignment-plan.md`。**随计划轮提交入库(提交 `2836e522`)。**
- **2026-10-06 10:37**: **实施完成(Status Open → Done)**。用户指令「实施计划: 26-10-06-1009」⇒ 执行任务轮。
  开工 `my-commit-flow.sync` 到 **2836e522**(计划基线 c2e43cf9 之后)。按 PHASE 1-7 落地:
  ①模板 5 处(groups ×2 · torrents · shows ×2)列名 `<span>` 加 `class="h-label"`;
  ②三主题 CSS: `.h-cell` 改 `display:flex; align-items:center; gap:4px; overflow:visible; padding-right:0`,
  新增 `.h-cell > .h-label` 省略号三件套, `.resizer` 改 `right:-5px`(跨进 10px 列间距);
  ③`shared/columns.js::colAlignCss()` 对 `align==="right"` 列追加 `.arrow{order:-1}` + 注释块改写;
  ④三主题删 `.g-stat.zero,.m-stat.zero{text-align:center}`(0 值口径归正);
  ⑤`e2e/smoke.spec.mjs` 新增几何守卫(盒模型右缘差 ≤1px + 值格不居中; 覆盖 `.group-head` 与 `.detail-head`);
  ⑥知识库回写(本档 · 坑档 · 契约文档 · 计划 doc-status)。
  **实测**(桩服务 8099 + headless Chromium, 三主题): 右对齐列盒模型差 group/torrent **1px**、detail **0px**
  (改前 11/10); 点「大小」排序后 ≤1(改前 21~22); 三主题一致。红绿双验: 注入缺陷(prism `.h-cell` 复加
  `padding-right:10px`)时 e2e 守卫报 `delta:11` 红, 复原后绿。`dev.e2e` **6 passed**;
  `test.full` **2676 passed + 4 skipped / 99%**(16021/163/5472/143, 53.7s wall)。
  **落地偏差两处**: ①atlas `components.css` 原 699 行触 700 行 cap, 新增 `.h-label` 规则按约定改放
  `atlas/css/views.css`(改后 components 698 行); ②计划把 0 值注释落点记作 `shared/app.js:646`, 实际在
  `shared/columns.js:646`(已按实际位置改写)。**本轮改动随实施提交入库(2026-10-06 提交轮)。**
- **2026-10-06 11:19**: **范围外项补修(Status 保持 Done)**。用户指令「实施计划中的 设置页 HR 在线核实表」⇒
  按计划 `plans/26-10-06-1009` §7 给「单独排期」的推荐处置, 落地 HR 表① 4 个 num 列的 **14px** 归正。
  开工 `my-commit-flow.sync` 到 **cdacf51a**(实施轮 2836e522 之后)。
  **机制核实(先量后改)**: 表① 是**真 `<table>`**(`th` 是 table-cell) ⇒ 主表那套 `.h-cell` 改 flex +
  `.arrow{order:-1}` **不适用** —— 实测 `th{display:flex}` 会把列宽撑爆(盒模型差 172~282px); 故取 §7
  推荐案「箭头**绝对定位不占流**」。另核实候选: `right:0` 会让箭头与标签重叠 3px(且左对齐列箭头跑到列最右);
  `th > span:first-child{position:relative}` + `right:100%` 无效(箭头是标签的**兄弟**, 不是子元素, 相对定位
  不成立) ⇒ 最终取「`position:absolute` 无偏移 = 静态位置」, 标签与箭头的相对位置**完全不变**, 只是箭头
  不再参与行内布局。
  **改法**: 三主题(atlas/console 的 `dialogs.css` · prism 的 `views.css`)各 2 行 —— `.hr-detail-table th.sortable`
  补 `position: relative`, `.hr-detail-table th .arrow` 由 `display:inline-block` 改 `position: absolute`
  (保留 `margin-left:3px`)。**零模板改动、零 JS 改动**。
  **实测**(桩服务 8099 + headless Chromium; 表① 在桩里不渲染, 用**真实主题 CSS + 逐字抄模板 DOM** 复现,
  与报告 §5-B1 同法): 4 个 num 列盒模型差 **14px -> 0px**, 三主题 atlas/console/prism 一致(改前 14 与报告同值);
  左对齐列不变; 表头行高 27.89px 不变(箭头脱离行内布局未压缩行高); 箭头仍渲染(width 11px)、hover/opacity
  揭示语义不变; 箭头对 num 列右溢 6px 落在**列间距**里(不压邻列内容, 4 个 num 列后面都还有列, 无末列越界)。
  **守阵**: `tests/test_web.py::test_frontend_hr_table_sort_filter_reorg_wiring` 加静态断言(三主题 `.arrow`
  规则体必须含 `position:absolute` 且不含 `display:inline-block`); **红绿双验**(把 console 改回 `inline-block`
  时红, 复原即绿)。静态断言看不见盒子模型 —— 几何量测口径见坑档 `pitfalls/web-ui/header-cell-gutter.md`。
  `dev.e2e` **6 passed**; `test.full` **2676 passed + 4 skipped / 99%**(16021/163/5472/143, 58.4s wall,
  与上一条 1037 逐位持平) ⇒ 基线切片 `26-10-06-1119-webui-hr-table-arrow.md`。
  **落地偏差**: 无(计划 §7 只给推荐处置, 落点与之一致: 三主题各 1 条, 未动模板)。**本轮改动随提交入库(2026-10-06 提交轮)。**

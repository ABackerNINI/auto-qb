# 26-09-29-webui-column-alignment — WEBUI 表格列对齐口径实施

**Status:** Open
**Added:** 2026-09-29
**Updated:** 2026-10-06 09:58
**Summary:** 【26-09-29 口径实施 · 已完成】按 reports/26-09-28-2345 审计报告推荐实施列对齐口径: P1 明细/种子两表 completion_on + time_active 共 4 处 align right→left(时间/时长族 R4 统一左, 默认隐藏列低风险); P2 抽屉 3 表数值列 9 字段(Tracker 做种/用户, 用户 进度/下行/上行/已下载/已上传/关联度, 内容 大小/进度)th/td 挂 .num 类 + 三主题 CSS 各补一条右对齐规则。test.full 1831 passed / 3 skipped(91%), 见基线 26-09-29-0240。 【26-10-06 几何错位取证 · 待拍板】用户报「右对齐列没有真正对齐标题文字」—— 实测属实(只读轮次, 零代码改动): 主视图 4 表全部右对齐列偏 11px(明细表 10px, 根因 `.h-cell` 的把手槽 `padding-right: 10px`), 设置页 HR 表① 4 个 num 列偏 14px(排序箭头缺内层 `v-if`, `opacity:0` 仍占位), 三主题一致; 抽屉 3 表 / HR 表②③ 不受影响。报告 reports/26-10-06-0945, 见基线 26-10-06-0958。**Status 由 Done 重开为 Open: 修法选型与「0 值居中」口径待用户拍板。**
**Topics:** webui-column-alignment
**Refs:** memory-bank/testing/baselines/26-10-06-0958-webui-column-alignment-header-offset.md, memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/testing/baselines/26-10-06-1022-webui-column-alignment-plan.md

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
| 9 | 实施修法 + 复量至 0(允许 ±1) + 补守阵 | 未开始 | 计划已出: plans/26-10-06-1009-plan-webui-column-alignment.html(Open, PHASE 0-7); 等用户显式「开工」 |

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
  0958 逐位持平 ⇒ 基线切片 `26-10-06-1022-webui-column-alignment-plan.md`。**未提交, 等用户指令。**

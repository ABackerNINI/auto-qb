# 26-09-29-webui-column-alignment — WEBUI 表格列对齐口径实施

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29 02:40
**Summary:** 按 reports/26-09-28-2345 审计报告推荐实施列对齐口径: P1 明细/种子两表 completion_on + time_active 共 4 处 align right→left(时间/时长族 R4 统一左, 默认隐藏列低风险); P2 抽屉 3 表数值列 9 字段(Tracker 做种/用户, 用户 进度/下行/上行/已下载/已上传/关联度, 内容 大小/进度)th/td 挂 .num 类 + 三主题 CSS 各补一条右对齐规则。test.full 1831 passed / 3 skipped(91%), 见基线 26-09-29-0240。
**Topics:** webui-column-alignment

## 原始请求

用户: 「按推荐实施 memory-bank/reports/26-09-28-2345-report-webui-column-alignment.html」—— 落地该审计报告 §5 建议改动清单(最小 diff): P1 时间/时长族 4 处 align 改左; P2 抽屉表数值列右对齐; 分享率例外等 5 类明确不动。

## 思考过程与决策

- **P1 走列模型单点**: align 只改 app.js 两份列模型数组, 表头/值由 colAlignCss 同源注入自动生效, 三主题 CSS 零改动。两列均默认隐藏(hide: true), 默认视图不受影响。
- **P2 走模板挂类**: 抽屉表无列模型(机制性缺口), 报告建议 th/td 挂对齐类。类名选 `.num` —— 改前 grep 全 static/ 确认无占用(仅 `hr-num` 等复合名与 JS 变量, 不冲突)。
- **CSS 规则写成 `th.num, td.num` 双选择器一条**: 抽屉表 th 的既有 `text-align: left` 在同特异性下按源序被后置规则覆盖, td 无既有对齐规则, 一条即可覆盖两侧。
- **模板加载机制核实**: tpl/*.html 由三主题 index.html 声明、前端运行时 fetch 拼装(无构建步骤), 改源文件即生效。
- **明确不动**(报告 P3/既有口径): 分享率左对齐(2026-09-26 拍板例外)、4 主表进度列左(进度条部件)、H&R/站数/版本居中、.g-stat.zero 0 值居中、操作列 cell-act 右。
- **未新增守阵测试**: 纯对齐值改动; 列模型对齐已有"表头/值同源"机制保证, 抽屉 .num 无重复出现面(类挂在单一模板源, 三主题 CSS 由同一条规则串起), 暂无守阵收益点。

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

## 进度日志

- **2026-09-29 02:40**: 报告推荐全部落地, 5 文件 +24/-17, test.full 一次通过(基线 26-09-29-0240)。分享率等 5 类"明确不动"项未触碰。报告为冻结快照, 本档案为后续实施与效果回溯的单点。

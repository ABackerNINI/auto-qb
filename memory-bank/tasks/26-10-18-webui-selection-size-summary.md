# 26-10-18-webui-selection-size-summary — WEBUI 选中摘要: 种子个数 + 合计/实际占用大小

**Status:** In Progress
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** WEBUI 选中摘要: 种子个数 + 合计/实际占用大小
**Topics:** webui-selection-size-summary
**Refs:** memory-bank/plans/26-10-18-2013-plan-webui-selection-size-summary.html, memory-bank/testing/baselines/26-10-18-2125-webui-selection-size-summary.md

## 原始请求

1. 「WEBUI添加显示选择种子个数与总大小功能, 比如选中xx个种子 xx KiB」(指定 grilling 流程——先多轮设计问答达成共识再动手)。
2. 第二轮 grilling 拍板：「Q1 a，但之前的风格设计与主题不符需避免。改为"已选 N 个种子 · 合计 X · 实际占用Y"即当X!=Y时显示实际占用，辅种Y只算一份。Q7 一并加入删除确认框。重新grilling」。
3. 「按推荐」。

## 思考过程与决策

两轮 grilling 共 13 问全部拍板(D1–D13，完整结论见计划 §06)。关键取舍：

- **位置**：筛选行(status-strip)内联纯文本指示器，占 2026-10-05 退役批量控制条原槽位；**旧控制条视觉风格禁用**(与主题不符)——零新 CSS，整行复用 `.strip-note`(三套皮肤逐字同款)。
- **三口径**：N = `selHashSet` 去重成员数(选组 = 全组成员)；X = Σ 选中成员 `size`(与删除框既有「总大小」同口径)；Y = 按 `occ_key` 内容单元去重、单元取选中成员**最大** size(最完整副本，与后端 progress=max/availability=max 同族)——Y ≤ X 恒成立，Y 仅 X≠Y 时显示。
- **occ_key 载荷契约**(D8)：种子页平铺行无组结构，前端算不出 Y ⇒ 后端 `_member_view` 加 `occ_key`(归组带 `encode_group_key`、未归组 null，字段恒在)；不靠前端补拉/缓存。
- **辅种语义根**：组内成员指向同一份文件，磁盘只占一份(组行 size/total_size 双口径的选中版)；跨组文件交叉不再去重(D10，后端另有标记)；追剧页同集多版本不额外去重(D11)。
- **算法单点**：`selection.js::selSizeSummaryOf` 一处实现，筛选行与删除框共用(两处各自演化是本项目最常犯的口径漂移)。
- **R1 实施期微调**(计划 §10)：未归组种子由「不带该键」改「字段恒在、值 null」——保 `_member_view` 的 `return {字典字面量}` 形状(守阵 AST 假设)，契约更稳。

## 实现计划

S1 后端 occ_key 契约 → S2 前端算法单点 + computed → S3 筛选行指示器 → S4 删除框条件行 → S5 守阵 + e2e + 文档回写 + 全量基线(计划 §04，每步独立可验)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | `views.py::_member_view` 加 occ_key(归组带组 key、未归组 null，查表前置保字面量形状) | Done(26-10-18) |
| S2 | `selection.js` 算法单点 `selSizeSummaryOf` + `selectedSize` computed(无选中早退) | Done(26-10-18) |
| S3 | `topbar.html` `.sel-summary` 指示器(v-if=selectedCount，复用 .strip-note 零新 CSS) | Done(26-10-18) |
| S4 | `delete_flow.js` 总大小行走单点 + Y<X 条件行(d.hint 口径说明) + `popovers.html` title 吃 d.hint | Done(26-10-18) |
| S5 | 守阵 2 条 + e2e 2 test×双皮肤 + conventions/webui.md 口径节 + test.full 基线切片 + 六轮矩阵 | Done(26-10-18) |

## 进度日志

### R0 · 立档 (2026-10-18)

实施与验证全部完成。落点：后端 `views.py` occ_key 契约；前端 `selection.js` 算法单点 + `topbar.html` 指示器(零新 CSS) + `delete_flow.js`/`popovers.html` 删除框同口径条件行。验证：`test.full` 与 e2e 六轮矩阵(含 @fast 门禁)数字见基线切片 26-10-18-2125。收尾副产物：矩阵轮暴露 2 项存量测试债(与本次改动无关，HEAD 同签名实证)，已入池未修 —— issue 26-10-18-2122(delta-sync 真值对齐用例无模式分流，error/hang 轮恒红 4 条)与 26-10-18-2226(追剧页行落点对冲在 3000 规模确定性失效 4 条)；选中摘要新 test 曾在 3000 轮因期望值失真(桩 `--groups` 默认 200 致前两行未归组)4 红，已改为从产品 occ_key 载荷现推期望值(两分支都断言)并复跑转绿，教训记入 spec 文件头与 pitfalls/testing/assertions.md。

- 2026-10-18 22:49 WEBUI 选中摘要(已选 N 个种子 · 合计 X · 实际占用 Y)实施并验证完成: 后端 occ_key 契约(views.py::_member_view) + 前端算法单点(selection.js::selSizeSummaryOf + selectedSize) + 筛选行 .sel-summary 指示器(零新 CSS) + 删除框同口径条件行(d.hint); 守阵 2 条 + e2e 2 test×双皮肤; test.full 3590 passed/4 skipped/98%; e2e 六轮矩阵 + @fast 170 passed(error/hang 两轮 4 红与 3000 轮 4 红均为存量债, HEAD 同签名实证, 已入池 26-10-18-2122/2222... 2226 未修); 载荷 +1.7%; conventions/webui.md 新增口径节

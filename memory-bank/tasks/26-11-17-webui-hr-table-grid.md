# 26-11-17-webui-hr-table-grid — HR 三表迁 aq-table grid 链路 + 四项交互全量统一

**Status:** In Progress
**Added:** 2026-11-17
**Updated:** 2026-11-17
**Summary:** HR 三表迁 aq-table grid 链路 + 四项交互全量统一
**Topics:** webui-hr-table-grid
**Refs:** memory-bank/plans/26-11-17-0059-plan-hr-table-wiring.html, memory-bank/plans/26-11-10-0027-plan-dt-table-wiring.html, memory-bank/issues/26-11-17-0132-docs-reports-stray-md-skill-portability.html

## 本篇只回答

HR 三表(hrDetail/hrWave/hrKv)怎么迁 aq-table grid 链路并拿到与主表同款的四项交互(拖宽/拖序/右键隐藏/持久化) —— 方案与判据单点在 [计划 26-11-17-0059](../plans/26-11-17-0059-plan-hr-table-wiring.html), 本档案只管跨会话推进与状态。

## 原始请求

1. 「memory-bank/plans/26-11-10-0027-plan-dt-table-wiring.html 计划还差什么闭环?」(只读问答)
2. 「翻状态收尾，同时开启第二轮，grilling，出一个计划」—— ①第一轮计划翻 Done 关单(用户终验四面通过) ②第二轮(HR 三表统一交互, 第一轮 D7)立项: grilling 拍板 + 出计划
3. grilling 两轮逐项拍板: Q1=A 全量统一 · Q2/Q3/Q4 按推荐(registerCell 本轮接/复用 v5 持久化/三波节奏) · Q5=04 卡片留 issue 待排期 · Q6/Q7/Q8 按推荐(并入 ALL_TABLE_DEFS/hrKv 补列头/排序并入引擎)

## 思考过程与决策

- 方案单点: 计划 [26-11-17-0059](../plans/26-11-17-0059-plan-hr-table-wiring.html) §03/§04, 拍板 E1-E8 在其 §06。关键事实: 四项交互机制在主表已单点齐备(startResize/startColDrag/openHeadMenu/toggleColumn/persistPage), HR 只差插头; v5 store 新增 page 向后兼容不升版本(app.js:739-741); 纯前端改造, e2e 桩服 --hr-scene 可验。
- 04 卡片(drawerTrackerV04)明确出轮: 入池 issue 26-11-17-0038(Open, 待排期), 例外清单收缩后成为唯一几何旁路例外。
- 第一轮计划 26-11-10-0027 于同会话翻 Done(用户终验四面 06/09/10/11 通过, §10 R2 行)。

## 实现计划

三波(计划 §04 判据前置写死): W1 迁壳+几何单点+守阵翻面(列定义补 tpl/align、并入 ALL_TABLE_DEFS、原生表迁 grid、排序并入 setSort、mode="thead" 退役、例外清单守阵改口径) → W2 交互全量+持久化+单元格注册化(四项交互逐表通路、v5 三表子树、assertLayout 覆盖、registerCell/cellOf 接线) → W3 e2e+终验收单(parity CASES 增 HR 三面、文档回写、基线切片、用户终验点头)。每波一笔提交, D8 止损沿用。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| W1 | 迁壳+几何单点+守阵翻面 | Open |
| W2 | 交互全量+持久化+单元格注册化 | Open |
| W3 | e2e+终验收单 | Open |

## 进度日志

### R0 · 立档 (2026-11-17)

立项轮: grilling 两轮 8 问拍板(E1-E8, 计划 §06); 计划 26-11-17-0059 落盘(判据前置); 04 卡片入池 issue 26-11-17-0038; 第一轮计划 26-11-10-0027 翻 Done(用户终验四面通过); 事实探查(只读子代理)引文进计划 §02; 本轮零生产代码改动。

- 2026-11-17 01:02 第二轮立项: grilling 8 问拍板 E1-E8, 计划 26-11-17-0059 落盘(判据前置), 04 卡片入池 26-11-17-0038(Open 待排期), 第一轮计划 26-11-10-0027 翻 Done(终验四面通过); 旧切片 26-11-10-0430-dt-table-wiring 迁出删除; 本轮零生产代码改动

- 2026-11-17 01:33 闸门复核: test.full 1 failed(存量红: reports/ stray .md 由远端 a54213b9 带入, 与本批无关, 入池 26-11-17-0132), 其余全过; 非涉码轮且红因不属本批, 不建基线切片(最新绿基线保持权威); 批评审两轮出口零 actionable(全轮累计 送检3/过检3/修3)

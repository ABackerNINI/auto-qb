# 26-11-17-webui-hr-table-grid — HR 三表迁 aq-table grid 链路 + 四项交互全量统一

**Status:** In Progress
**Added:** 2026-11-17
**Updated:** 2026-11-18
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

| W1 | 迁壳+几何单点+守阵翻面(58c22fc5 + cc1bcc4f) | Done |
| W2 | 交互全量+持久化+单元格注册化(6f78ec08 + d0621c4c) | Done |
| W3 | e2e+终验收单(收口已落; 用户终验待做) | In Progress |

## 进度日志

### R0 · 立档 (2026-11-17)

立项轮: grilling 两轮 8 问拍板(E1-E8, 计划 §06); 计划 26-11-17-0059 落盘(判据前置); 04 卡片入池 issue 26-11-17-0038; 第一轮计划 26-11-10-0027 翻 Done(用户终验四面通过); 事实探查(只读子代理)引文进计划 §02; 本轮零生产代码改动。

- 2026-11-17 01:02 第二轮立项: grilling 8 问拍板 E1-E8, 计划 26-11-17-0059 落盘(判据前置), 04 卡片入池 26-11-17-0038(Open 待排期), 第一轮计划 26-11-10-0027 翻 Done(终验四面通过); 旧切片 26-11-10-0430-dt-table-wiring 迁出删除; 本轮零生产代码改动

- 2026-11-17 01:33 闸门复核: test.full 1 failed(存量红: reports/ stray .md 由远端 a54213b9 带入, 与本批无关, 入池 26-11-17-0132), 其余全过; 非涉码轮且红因不属本批, 不建基线切片(最新绿基线保持权威); 批评审两轮出口零 actionable(全轮累计 送检3/过检3/修3)

- 2026-11-17 03:16 W1①②(58c22fc5): 三表列定义补 tpl/align(hrKv 删 header:false 补列头「项/值」+ k 列 locked, E7), 经 AQB_HR_TABLE_DEFS window 桥并入 ALL_TABLE_DEFS(新 page 键 hrDetail/hrWave/hrKv), columns_computed.js 同构登记三对 computed, 全走 _gridTemplate/_visibleCols 单点; R1 实证选定固化轨(模态未展开 display:none, 窗口实测轨拿不到宽度, 默认走 tpl 显式宽度); 评审批次修 4(选择器过桥门 pickerHold/装载序守阵等); 含 test_docs_forms 存档特例单文件豁免(用户拍板保真优先保 .md, 临时过桥, 并行 clone 转 HTML 入库后整笔移除); 复评轮 2 零新增发现

- 2026-11-17 04:51 W1③④⑤⑥(cc1bcc4f): settings-detail 三表原生表迁 aq-table grid 容器+grid 行(T1 实证挂载形态: 表头组件根 + .group-row[data-table] 兄弟行), td 按列保真清单逐列迁移; hrDetail 排序并入引擎 setSort 删 hrsSetSort 专用状态(E8); mode="thead" 借壳分支整体退役; 守阵 HTML 面翻面(r4 probe 钉「注册在盘×3 + tpl 恰 20 + stickyHead:false 恰 3 + grid 几何恰 3 处 + 零旁路拼轨」, 红绿双验); 摘 pickerHold, HR 三分组恢复进列选择器(E6); sticky-head 决策 = HR 表头声明 stickyHead:false 不进吸顶测量; 评审批次修 7(menu.js headMenuSort scope 直传等); 复评轮 2 零新增发现

- 2026-11-17 07:46 W2①(6f78ec08): 拖序侧 locked 守卫(columns_drag.js startColDrag 拒绝启动 + applyColOrder no-op 双保险, 非 locked 列自由度逐位不变; 主表 locked 列拖序从可拖走变不可拖走 = R7 授权口径); 设置页右键菜单/列选择器结构性解封(用户授权随批: ctx-menus 收口对回归 #app 直接子级 + col-menu 弹层迁出 header, z 层级梯 above-full-modal 135 让位) —— 该 shell 缺陷早于本计划(2026-09-25 起); 评审批次修 1(_menuFitRefit 预算/menus.spec settle 轮询, 评审裁定非测试弱化); 复评轮 2 零新增发现

- 2026-11-18 00:37 W2②③④(d0621c4c): 持久化还原(v5 三表子树读侧还原矩阵手势级全绿; resetAll/fitAll 波及 HR 面); assertLayout HR 覆盖(columns_grid.js 修 headRef=null 分支半截缺陷, headDom 分支按首个有盒表头兜底, 未展开 v-show 未挂载豁免 R4); registerCell 注册化(20 渲染器经 AQB_HR_CELLS_REGISTER fail-fast 注册, 模板经 hrCellOf→DT_TABLE.cellOf 消费, 确认空清单按钮本体留模板, dt_table 六口子全活); 评审批次修 5(全守阵侧); 复评轮 3 零新增发现

- 2026-11-17 W2 中场 T3 零改动核验轮: e2e 回归(hr-history 等)与渲染探查全绿, parity CASES 当时未增 HR 面(沙箱不加载 hr_status.js, 几何等价探针 13 张不含 HR, HR 等价性留 W3 parity e2e 真跑); W1 判据 dry-run 冒烟已实跑(`commands run dev.run -- config.yml --dry-run` 26.3s): 配置加载/schema 迁移(v5→v8 内存生效)/全局任务创建启动链全正常, 连接 qBittorrent 127.0.0.1:16585 拒绝(本机 qB 未运行)主循环未起 —— 按预案冒烟止步连接 qB 不阻塞判据, 主程序启动/校验面无红

- 2026-11-18 00:49 W3 收口(T6): parity 守阵 e2e/dt-table-layout-parity.spec.mjs 增 HR 三面(hrDetail 10/hrWave 8/hrKv 2 列; route 拦截喂 /api/hr/status 与 /api/hr/sites/*/entries 合成载荷 —— 桩只灌表3 history, 表1/2 真读磁盘未播种, 手法 variant-tables 家族同款; 双皮肤全绿); hr-history 回归全绿; 守阵/文档回写: hr_status.js 头注微调(parity 守阵事实补一行), memory-bank/architecture/webui.md D4 例外清单收缩为「仅 04 卡片」+ 守阵条补 HR 三面事实, 根 README HR 节补「列宽/列序/隐藏列与主表同款可调且刷新后保持」; 计划 26-11-17-0059 §10 增 R2 变更记录行(doc-updated 抬戳, doc-status 保持 Open —— 待用户终验点头才翻 Done, D5 同款); 基线切片落盘(见 kb.baseline); test_docs_forms MD_WHITELIST 豁免移除留待并行 clone 转换件入库(明确不做)。W3⑤ 用户终验(settings → HR 在线核实 → 三表逐一手测四项交互+刷新持久, 主表回归四面)待用户

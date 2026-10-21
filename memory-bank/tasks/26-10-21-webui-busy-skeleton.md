# 26-10-21-webui-busy-skeleton — 前端 busy+try+反馈+finally 骨架收敛为三单点(issue 26-10-20-2231 认领修复)

**Status:** In Progress
**Added:** 2026-10-21
**Updated:** 2026-10-21
**Summary:** 认领并修复 issue 26-10-20-2231(fe-dialogs-js-boilerplate-dup): 「置 busy → try 请求 → 失败反馈 → finally 复位」骨架在 dialogs.js 与 config_hub.js 手抄 19 处(issue 标题记 15, 按其 lede 分族 5+5+4+5 复核为 19), 收敛为 dialogs.js 三个骨架单点 —— `_mgrRun`(管理对话框写操作, mgr CRUD 5 处) / `_panelLoad`(面板加载与槽回执, dialogs 5 处 + tm 族 5 处; loading 可选, 错误槽与 toast 双反馈通道) / `_postWaitCmd`(POST+waitCmd 三态 toast 判据单点, 4 处); 各处差异(成功收尾 / 失败回滚 / 槽名 / 静默变体)以参数与回调留在调用点, tmShutdownTool(保存失败回滚内存态)按台账口径保持原样。守阵: 三单点在册 + 19 处接线数对账 + finally 复位保底 + 裸 busy 置位反向断言(红验)。全量与 e2e 数字见 kb.baseline。
**Topics:** webui-busy-skeleton
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-dialogs-js-boilerplate-dup.html

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-20-2231-refactor-fe-dialogs-js-boilerplate-dup.html」——
   用户显式指派认领(create-issue skill 的「用户指派」口径), 同时授权修复这一件。
2. 开工同步 `my-commit-flow.sync`: 已同步 `95baf46b`(远端领先 3 笔, 快进 cecbe4a9→95baf46b)。
3. 收尾按 AGENTS.md DoD: 全量测试 + 基线切片 + issue 状态流转 + 索引重建。用户**未**说「提交」,
   本轮不 commit / 不 push。

## 思考过程与决策

**复验(改前)**: issue 锚点逐处重读源码 —— 19 处全部在位(台账 R20-B-01/B-02/B-03/R20-C-15 的
行号有漂移但符号全部 grep 可达); issue 标题「15 处」与其 lede 的分族算术(5+5+4+5)对不上, 以
实际 grep 为准记 19。

**决策 1 · 三个单点, 不是 issue 建议的两个**: issue 建议抽 `_busyRun(el, fn, opts)` + `_postWaitCmd`。
实际 mgr CRUD 族(ok toast → 重拉列表)与面板加载族(错误/消息槽上屏)的**反馈通道不同**, 强并一个
万能 helper 就要把各 catch 体全部回调化, 调用点反而更难读。按台账各自的建议形态落三个:
`_mgrRun`(R20-B-01 建议 mgrSubmit) / `_panelLoad`(R20-B-02 建议 panelLoad, 兼并 R20-C-15 的 tm
槽回执族) / `_postWaitCmd`(R20-B-03)。与建议修法的差异在 issue 的 Done 记录里说明改道原因。

**决策 2 · 差异留调用点**: 成功收尾(清输入 / 回滚勾选态 / 刷新托管状态)、失败装配(tmLoad 的
不可达三字段)、槽名、静默变体(loadSpeedMode 无 loading 位)一律以参数或 onOk/onErr/onFinally
回调留在调用点; helper 只拥有「置位 → try → 反馈判据 → finally 复位」这条不变式。

**决策 3 · 刻意不收编**: tmShutdownTool(台账 R20-C-15 维护风险注记)是「保存失败回滚内存态」
特例, catch 内复合回滚且无错误槽, 骨架形状不同 —— 保持原样。

**决策 4 · 等价性口径**: 纯重构不改行为 —— 逐处对照原 catch/finally 的反馈文案、时长、auth
闸门(dialogs 族 !e.auth 静默 vs tm 族恒上屏)、复位对象与次序; loadSpeedMode 的「不预清旧错」
用 loading 缺位 + keepErr 两条口径保真; toggleAltSpeed 的 ok 文案「按切换前状态措辞」用 okMsg
传函数(成功此刻才取值)保真。

**决策 5 · 守阵**: 结构守阵(三单点在册 + 19 处接线数对账 + finally 复位保底必须住在单点内)
+ 裸 busy 置位反向断言(再手抄 = 破单点, 回潮即红)。

## 实现计划

1. 复验: 重读 19 处锚点与各 catch/finally 差异清单(文案 / 时长 / auth 闸 / 复位对象)。
2. dialogs.js 落三单点并改写 14 处调用点。
3. config_hub.js 的 tm 族 5 处(hubImportSites / tmLoad / tmSave / tmAutostart / tmPickLoad)改接 `_panelLoad`。
4. node --check 双文件语法; 新增守阵 test_frontend_busy_skeleton_single_point + 文件头测试计划同步。
5. 红验: 拆一处接线 / 删 finally 保底 → 守阵判红 → 还原。
6. 验证: test.full + e2e; 基线切片记实测数字。
7. 收尾: issue 置 Done(含改道说明) + 索引重建 + 档案进度行 + kb.wrap 切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 复验 19 处锚点与差异清单 | Done(2026-10-21) |
| S2 | dialogs.js 三单点 + 14 处调用点改写 | Done(2026-10-21) |
| S3 | config_hub.js tm 族 5 处改接单点 | Done(2026-10-21) |
| S4 | 守阵 + 文件头测试计划同步 | Done(2026-10-21) |
| S5 | 红验 | Done(2026-10-21) |
| S6 | test.full + e2e + 基线切片 | Done(2026-10-21) |
| S7 | issue Done + 索引 + 档案进度行 + 切片 | Done(2026-10-21) |

## 进度日志

### R0 · 立档 (2026-10-21)

- 认领 issue 26-10-20-2231(用户指派「认领并修复」), 复验 19 处锚点全部在位。
- 基线: 动手前 test.full 全绿(树上 95baf46b, 数字见 kb.baseline 最新切片)。

- 2026-10-21 06:07 认领修复 issue 26-10-20-2231 完成: dialogs/config_hub 手抄 19 处 busy 骨架收敛为 dialogs.js 三单点(_mgrRun/_panelLoad/_postWaitCmd), tmShutdownTool 特例保留; triggers.js calls 表四处 POST 旧登记并为统一出口一行; 新守阵 busy_skeleton_single_point 两支红验; test.full 与 dev.e2e 双绿, 数字见基线切片 26-10-21-0605

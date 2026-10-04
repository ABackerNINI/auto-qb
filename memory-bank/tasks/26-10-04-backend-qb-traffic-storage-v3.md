# 26-10-04-backend-qb-traffic-storage-v3 — qB 流量存储 v3 实施

**Status:** In Progress
**Topics:** qb-traffic-storage-v3
**Added:** 2026-10-04
**Updated:** 2026-10-04
**Summary:** 实施计划 26-10-04-1957 开工: feature/qb-traffic-v3 分支五期拆七步串行子智能体实施(S1 纯函数→S4 配置键→S2a/S2b 写侧→S3a/S3b 读侧→S5 收尾), 每步 test.full + 普通 git commit, 完成后合回 develop 等提交指令; D4 拍板 6mo/1y/all 三档。

**Refs:** memory-bank/plans/26-10-04-1957-plan-qb-traffic-storage-v3.html, memory-bank/reports/26-10-04-1730-report-qb-traffic-storage-v3.html, memory-bank/activeContext/26-10-04-1745-webui-qb-traffic-storage-v3-design.md

## 原始请求

用户 2026-10-04 晚指令: 实施计划 26-10-04-1957。口径: 主会话只委派与总结, 实施派子智能体**串行**执行(不并列防超并发); 强关联阶段可合并, 特大任务拆小防子智能体 O(n²) token 消耗; 待拍板先问(裁决 D4); 新开本地分支, 每步完成本地 commit(**不用** my-commit-flow); 全部完成后同步到 develop 等提交指令; 子智能体非正常失败 3 次即停等人工。

拍板回执(开工前 AskUserQuestion): D4 前端档位 = **6mo/1y/all 三档**(90d 延后); 立档 = 按计划 §9.2 开工立任务档案。

## 思考过程与决策

- 五期拆七步: S2(2-2.5 人日)拆 S2a 写侧翻转核心 + S2b 聚合与恢复; S3(1.5-2 人日)拆 S3a 读侧核心 + S3b 视图/端点/前端; S1/S4/S5 保持独立。拆分线沿文件与关注点边界, S2a/S2b 与 S3a/S3b 各自先后接续, 后者基于前者 commit。
- 计划合批约束(§00)在私有分支上自动满足: 各步都是本地 commit 不上真机, S4→S2→S3 串行天然同批。
- 每步收尾跑 `commands run test.full` 后普通 git commit(gitmoji + 中文一行); 推送统一等用户「提交」指令(ship.commit)。
- D4 拍板 6mo/1y/all → S3b 的 WINDOW_SPECS/WINDOW_NAMES/前端文案按 13 档落, 90d 视图延后(day 行照常产出)。

## 实现计划

见计划 [26-10-04-1957](../plans/26-10-04-1957-plan-qb-traffic-storage-v3.html) §02-§07: 格式规格 §02 / 写侧 §03 / 聚合分层 §04 / 读侧 §05 / 配置迁移 §06 / 五期派发与验收判据 §07 表(每期验收判据逐条钉住)。

## 子任务状态表

| # | 子任务 | 内容 | 状态 |
|---|--------|------|------|
| ⓪ | 计划入库 | 计划 HTML + kb.index 生成物, commit 633d58cd | Done |
| ① | S1 存储层纯函数 | v3 行型序列化/解析/游标 dt 链/按天路径/聚合 9 列纯函数, 不接线, 既有 107 例零改动 | Done (9744655b) |
| ② | S4 配置键 + schema | flush_interval 全链 + sample_interval ≥main_tick 硬校验 | Open |
| ③ | S2a 写侧翻转核心 | BlockBuffer/游程/flush 驱动/跨天切块/stop()/回拨钳制/翻 v3 目录/热重载联动 | Open |
| ④ | S2b 聚合与恢复 | 累计器/水位封口/文件尾恢复/catch-up 硬序/hour 裁剪/淘汰新口径/seal_sweep 退役 | Open |
| ⑤ | S3a 读侧核心 | 有效 dt 桶宽/跨桶覆盖(D1)/块间 gap 真空/按天加载/解析缓存 | Open |
| ⑥ | S3b 视图+端点+前端 | WINDOW_SPECS(D4: 6mo/1y/all)/组端点去 global/A4 下界常量/档位文案 | Open |
| ⑦ | S5 收尾与基线 | index.json/v1v2 死代码退役/docstring v3 契约/实测数字/基线切片/回写 | Open |
| ⑧ | 合回 develop | 分支合并回本地 develop, 等用户提交指令 | Open |

## 进度日志

- **2026-10-04 20:3x 开工**: 同步成功 b3b037ac; 开分支 feature/qb-traffic-v3; D4 与立档两项经用户拍板(6mo/1y/all 三档; 按计划立档); commit⓪ 计划入库(633d58cd); 本档案建立。
- **2026-10-04 21:xx S1 完成 (9744655b)**: traffic_store.py 末尾新增 v3 纯函数区 +661 行(行型/游标 dt 链/路径/聚合), 不接线; 新增 10 例已登记测试计划。实施期定约(§09.2 授权随做随记): 游程 dt_ms = last_seen − OpenRun.start, OpenRun.start := 链上锚点(上一记录槽位)——相邻游程间一次采样间隔并入后一游程 dt_ms, 缺省/显式语义统一; **S2 写侧须按同约定产出**。
- **2026-10-04 21:xx 认领链修复 (01bc35b6)**: 立档 commit 曾致 test_docs_forms 2 例红(档案缺 **Topics:** 行 + Refs 未双向声明); 修法: 档案补 Topics 行, 计划/报告 HTML 补 doc-refs meta, 切片 Refs 追加本档案。子智能体 stash 对照判「既有失败」不成立——stash 不回退已提交态, 该判法不可信。
- 全量复核: 2525 passed / 4 skipped, 覆盖率 99%。

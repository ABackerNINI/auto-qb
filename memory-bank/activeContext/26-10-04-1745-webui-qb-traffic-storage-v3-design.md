# qB 流量存储 v3 设计 — 四构思验证成立, 报告已转化为实施计划

> 摘要: 用户认定 v2 未实际解决三问题(P1 落盘应每 10min 批量类似 state / P2 无法兼容采样率更改 3s→1.5s / P3 无法与主循环同步 main_tick=2s 时 3s/1.5s 被量化), 派两阶段串行子智能体静态取证(现状盘点 → 构思验证对比), 四项构思成立: C1 采样率下限锁 main_tick+倍数约束(告警级) / C2 块+元数据头行+**稀疏 delta 实测时间差**(逐记录有效 dt 桶宽消除 26-10-04-1639 伪断线根因, 块间 gap 天然真空判定, 去 global 依赖) / C3 每 10min 批量落盘+退出 stop 钩子(写 IO 300×↓, 崩溃窗口 ≤10min 拍板接受) / C4 按天分文件+按需读+解析缓存(读放大 20-60×↓)。**修订轮(18:20)**: 用户补充质疑主循环耗时使「每行不需要时间」不成立 → 取证实锤 next_tick_at 按实际时刻累加(qbmanager.py:518-527, 任务线耗时 0.5s 时实际节拍=2.5s), 纯等间隔为格式性错误(块内线性累积, d̄=0.1s 块尾误差 ~29s+块边界伪真空) → 格式修订为 r/z/n 行可选 dt_ms 列+累积漂移触发(tol 200-250ms), C1 整数倍降级告警级、I≥main_tick 保留硬校验。**修订轮 3(19:19)**: 用户补充「月/年视图+聚合分开存储」→ 验证成立(hour 行留天文件则年视图冷读 365 文件/解析上界 536MB, 解析缓存救不了), 采纳聚合分层: 每系列一个 agg.dat(hour/day/month 9 列行追加混存, hour 加 cov_s 有效时长列, dt 加权公式)/内存累计器+flush 合流封口+文件尾水位恢复+catch-up 先于裁剪/seal_sweep 与 tmp+replace 常规写路径退役(仅存裁剪)/raw→hour→day→month 严格逐级/零新增配置键; 视图映射新增 90d/6mo/1y→day、all→month。报告 [26-10-04-1730](../reports/26-10-04-1730-report-qb-traffic-storage-v3.html)(v3 修订, **待评审**)。
> 最后活动: 2026-10-04 20:35

**Refs:** memory-bank/reports/26-10-04-1730-report-qb-traffic-storage-v3.html, memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html, memory-bank/plans/26-10-04-0721-plan-qb-traffic-v2-zrow.html, memory-bank/reports/26-10-04-0636-report-qb-traffic-storage.html

## 现状

- 设计报告已立档并经两轮修订(87.3KB, 8 节, dark 主题自检过, doc-updated 26-10-04-1919); 代码零改动, 无新基线(纯文档轮)。
- 修订轮 3 裁决(报告 §6.4): 聚合分层方案采纳——agg.dat 追加混存/9 列+cov_s/水位封口/catch-up 先于裁剪/Q4 旧口径(每小时首采样触发)作废; 时钟回拨现状无防护(traffic_sample_mod.py:244 直用 time.time()), 写侧单调钳制 dt_ms=max(1,actual−prev) 列为实施期新增项。
- 用户拍板四项: ①本轮仅设计报告 ②旧 v2 dat 不迁移直接换代(新目录 qb-traffic-v3/, 旧目录留存不读, 删留未决处置权在用户) ③验证方式=静态取证 ④落 reports/ 设计报告形态。
- 修订裁决(报告 §6.3): 用户补充「考虑主循环耗时, 改存 delta 时间差」→ 采纳稀疏 delta+累积漂移触发方案(r/z/n 行可选 dt_ms 列, 缺省=标称, |actual−projected|>tol 才写; 单行偏差触发有稳态小漂移永不写入的陷阱); C1「整数倍」从精度保证降级告警级(有载时实际节奏=ceil(I/(main_tick+d̄))×(main_tick+d̄), 名义倍数失效), 「I≥main_tick」保留硬校验; 时间精度由实测 dt 保证。
- 格式级开放问题闭合情况: Q1-Q4 按推荐闭合(省略声明列/失配取整降级/缓冲槽上限 3600/hour 合流触发); 修订轮新增唯一开放项: 跨桶记录覆盖语义(单记录 dt 跨多桶时中间桶须按覆盖处理防伪洞)。
- 配置键变更点已锁定: 改 sample_interval 校验(I≥main_tick 硬校验+整数倍告警级) + 新增 flush_interval(默认 600s, 60-3600), 须同步 validate_config + schema(黄金法则 4)。
- **计划轮(20:0x)**: 用户指令「将报告转化为分步实施计划」→ 计划 [26-10-04-1957](../plans/26-10-04-1957-plan-qb-traffic-storage-v3.html) 立档(Open, 待开工指令)。七项计划裁决: D1 跨桶记录覆盖其间桶(开放项①闭合) / D2 tol=250ms 起步 / D3 agg 快读上界 1MB 口径(开放项④闭合) / D4 前端档位默认 6mo/1y/all、90d 延后(仍待用户随开工指令拍板) / D5 倍数失配告警落点=模块检测点(validate_config 保持 errors-only) / D6 旧测试重写随行为翻转同期进行(修正报告 §7 把重写压 S5 的分界) / D7 不预留 aggregate_window(开放项③闭合)。五期三批派发: 批次一 S1 存储层纯函数 → 批次二 S4 配置键→S2 采样器写侧翻转→S3 读侧翻转(同批, S4 先行提交) → 批次三 S5 退役清理+基线; 工作量 ≈6-8 人日, 新增/改口径用例 ≈46-65 例。代码零改动, 纯文档轮无新基线。

## 下一步

- 用户评审计划(尤其 D4 前端档位取舍) → 显式开工指令后**另起轮次**按计划 §07 五期三批实施(批次一 S1 先行; 合批约束: S4 先于/同批 S2, S2+S3 同批); 「继续」不构成开工授权。

## 实施开工轮 (20:3x)

- 开工授权已下达(用户显式指令), D4 拍板: **6mo/1y/all 三档**; 立档拍板: 按计划 §9.2。
- 执行形态: 主会话只委派, 子智能体串行实施; 五期拆七步(S2→S2a/S2b, S3→S3a/S3b)在分支 `feature/qb-traffic-v3`, 每步 test.full + 普通 git commit(不走 my-commit-flow), 全部完成后合回 develop 等提交指令。
- 任务档案: [tasks/26-10-04-backend-qb-traffic-storage-v3](../tasks/26-10-04-backend-qb-traffic-storage-v3.md)(进度单点); commit⓪ 计划入库 633d58cd。

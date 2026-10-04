# qB 流量存储 v3 设计 — 四构思验证成立, 报告待评审

> 摘要: 用户认定 v2 未实际解决三问题(P1 落盘应每 10min 批量类似 state / P2 无法兼容采样率更改 3s→1.5s / P3 无法与主循环同步 main_tick=2s 时 3s/1.5s 被量化), 派两阶段串行子智能体静态取证(现状盘点 → 构思验证对比), 四项构思成立: C1 采样率下限锁 main_tick+倍数约束(告警级) / C2 块+元数据头行+**稀疏 delta 实测时间差**(逐记录有效 dt 桶宽消除 26-10-04-1639 伪断线根因, 块间 gap 天然真空判定, 去 global 依赖) / C3 每 10min 批量落盘+退出 stop 钩子(写 IO 300×↓, 崩溃窗口 ≤10min 拍板接受) / C4 按天分文件+按需读+解析缓存(读放大 20-60×↓)。**修订轮(18:20)**: 用户补充质疑主循环耗时使「每行不需要时间」不成立 → 取证实锤 next_tick_at 按实际时刻累加(qbmanager.py:518-527, 任务线耗时 0.5s 时实际节拍=2.5s), 纯等间隔为格式性错误(块内线性累积, d̄=0.1s 块尾误差 ~29s+块边界伪真空) → 格式修订为 r/z/n 行可选 dt_ms 列+累积漂移触发(tol 200-250ms), C1 整数倍降级告警级、I≥main_tick 保留硬校验。**修订轮 3(19:19)**: 用户补充「月/年视图+聚合分开存储」→ 验证成立(hour 行留天文件则年视图冷读 365 文件/解析上界 536MB, 解析缓存救不了), 采纳聚合分层: 每系列一个 agg.dat(hour/day/month 9 列行追加混存, hour 加 cov_s 有效时长列, dt 加权公式)/内存累计器+flush 合流封口+文件尾水位恢复+catch-up 先于裁剪/seal_sweep 与 tmp+replace 常规写路径退役(仅存裁剪)/raw→hour→day→month 严格逐级/零新增配置键; 视图映射新增 90d/6mo/1y→day、all→month。报告 [26-10-04-1730](../reports/26-10-04-1730-report-qb-traffic-storage-v3.html)(v3 修订, **待评审**)。
> 最后活动: 2026-10-04 19:19

**Refs:** memory-bank/reports/26-10-04-1730-report-qb-traffic-storage-v3.html, memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html, memory-bank/plans/26-10-04-0721-plan-qb-traffic-v2-zrow.html, memory-bank/reports/26-10-04-0636-report-qb-traffic-storage.html

## 现状

- 设计报告已立档并经两轮修订(87.3KB, 8 节, dark 主题自检过, doc-updated 26-10-04-1919); 代码零改动, 无新基线(纯文档轮)。
- 修订轮 3 裁决(报告 §6.4): 聚合分层方案采纳——agg.dat 追加混存/9 列+cov_s/水位封口/catch-up 先于裁剪/Q4 旧口径(每小时首采样触发)作废; 时钟回拨现状无防护(traffic_sample_mod.py:244 直用 time.time()), 写侧单调钳制 dt_ms=max(1,actual−prev) 列为实施期新增项。
- 用户拍板四项: ①本轮仅设计报告 ②旧 v2 dat 不迁移直接换代(新目录 qb-traffic-v3/, 旧目录留存不读, 删留未决处置权在用户) ③验证方式=静态取证 ④落 reports/ 设计报告形态。
- 修订裁决(报告 §6.3): 用户补充「考虑主循环耗时, 改存 delta 时间差」→ 采纳稀疏 delta+累积漂移触发方案(r/z/n 行可选 dt_ms 列, 缺省=标称, |actual−projected|>tol 才写; 单行偏差触发有稳态小漂移永不写入的陷阱); C1「整数倍」从精度保证降级告警级(有载时实际节奏=ceil(I/(main_tick+d̄))×(main_tick+d̄), 名义倍数失效), 「I≥main_tick」保留硬校验; 时间精度由实测 dt 保证。
- 格式级开放问题闭合情况: Q1-Q4 按推荐闭合(省略声明列/失配取整降级/缓冲槽上限 3600/hour 合流触发); 修订轮新增唯一开放项: 跨桶记录覆盖语义(单记录 dt 跨多桶时中间桶须按覆盖处理防伪洞)。
- 配置键变更点已锁定: 改 sample_interval 校验(I≥main_tick 硬校验+整数倍告警级) + 新增 flush_interval(默认 600s, 60-3600), 须同步 validate_config + schema(黄金法则 4)。

## 下一步

- 用户评审报告 → 认可后**另起轮次**按报告 §7 分期建议(S1 存储层 v3 / S2 采样器缓冲+flush / S3 读侧逐块桶宽+按天 / S4 配置键+schema / S5 收尾基线)立计划档案实施; 「继续」不构成开工授权。

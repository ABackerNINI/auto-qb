# 26-10-04-backend-qb-traffic-storage-v3 — qB 流量存储 v3 实施

**Status:** Done
**Topics:** qb-traffic-storage-v3
**Added:** 2026-10-04
**Updated:** 2026-10-05
**Summary:** 实施计划 26-10-04-1957 开工: feature/qb-traffic-v3 分支五期拆七步串行子智能体实施(S1 纯函数→S4 配置键→S2a/S2b 写侧→S3a/S3b 读侧→S5 收尾), 每步 test.full + 普通 git commit, 完成后合回 develop 随本专题入库; D4 拍板 6mo/1y/all 三档。真机验收追加 S6 活尾合流(2026-10-05): 用户报「流量图不实时更新, 得等落盘才更新」→ 方案 A 落地(采样模块每轮发布 LiveTail 快照 + 三端点 raw 段窗合流 + ts 精确去重), 图面尾部随采样节拍实时。

**Refs:** memory-bank/plans/26-10-04-1957-plan-qb-traffic-storage-v3.html, memory-bank/reports/26-10-04-1730-report-qb-traffic-storage-v3.html, memory-bank/activeContext/26-10-04-1745-webui-qb-traffic-storage-v3-design.md, memory-bank/issues/26-10-05-1015-feat-qb-traffic-agg-live-buckets.html

## 原始请求

用户 2026-10-04 晚指令: 实施计划 26-10-04-1957。口径: 主会话只委派与总结, 实施派子智能体**串行**执行(不并列防超并发); 强关联阶段可合并, 特大任务拆小防子智能体 O(n²) token 消耗; 待拍板先问(裁决 D4); 新开本地分支, 每步完成本地 commit(**不用** my-commit-flow); 全部完成后同步到 develop 随本专题入库; 子智能体非正常失败 3 次即停等人工。

拍板回执(开工前 AskUserQuestion): D4 前端档位 = **6mo/1y/all 三档**(90d 延后); 立档 = 按计划 §9.2 开工立任务档案。

## 思考过程与决策

- 五期拆七步: S2(2-2.5 人日)拆 S2a 写侧翻转核心 + S2b 聚合与恢复; S3(1.5-2 人日)拆 S3a 读侧核心 + S3b 视图/端点/前端; S1/S4/S5 保持独立。拆分线沿文件与关注点边界, S2a/S2b 与 S3a/S3b 各自先后接续, 后者基于前者 commit。
- 计划合批约束(§00)在私有分支上自动满足: 各步都是本地 commit 不上真机, S4→S2→S3 串行天然同批。
- 每步收尾跑 `commands run test.full` 后普通 git commit(gitmoji + 中文一行); 推送统一随本专题入库(ship.commit)。
- D4 拍板 6mo/1y/all → S3b 的 WINDOW_SPECS/WINDOW_NAMES/前端文案按 13 档落, 90d 视图延后(day 行照常产出)。

## 实现计划

见计划 [26-10-04-1957](../plans/26-10-04-1957-plan-qb-traffic-storage-v3.html) §02-§07: 格式规格 §02 / 写侧 §03 / 聚合分层 §04 / 读侧 §05 / 配置迁移 §06 / 五期派发与验收判据 §07 表(每期验收判据逐条钉住)。

## 子任务状态表

| # | 子任务 | 内容 | 状态 |
|---|--------|------|------|
| ⓪ | 计划入库 | 计划 HTML + kb.index 生成物, commit 11619fbf | Done |
| ① | S1 存储层纯函数 | v3 行型序列化/解析/游标 dt 链/按天路径/聚合 9 列纯函数, 不接线, 既有 107 例零改动 | Done (9744655b) |
| ② | S4 配置键 + schema | flush_interval 全链 + sample_interval ≥main_tick 硬校验 | Done (30eebcf0) |
| ③ | S2a 写侧翻转核心 | BlockBuffer/游程/flush 驱动/跨天切块/stop()/回拨钳制/翻 v3 目录/热重载联动 | Done (7b89d0da) |
| ④ | S2b 聚合与恢复 | 累计器/水位封口/文件尾恢复/catch-up 硬序/hour 裁剪/淘汰新口径/seal_sweep 退役 | Done (62998945) |
| ⑤ | S3a 读侧核心 | 有效 dt 桶宽/跨桶覆盖(D1)/块间 gap 真空/按天加载/解析缓存 | Done (fca0cb96) |
| ⑥ | S3b 视图+端点+前端 | WINDOW_SPECS(D4: 6mo/1y/all)/组端点去 global/A4 下界常量/档位文案 | Done (eb66e3c4) |
| ⑦ | S5 收尾与基线 | index.json/v1v2 死代码退役/docstring v3 契约/实测数字/基线切片/回写 | Done (7f155e3b) |
| ⑧ | 合回 develop | 分支合并回本地 develop| Done (fast-forward) |
| ⑨ | S6 活尾合流(验收追加) | 真机验收发现图面不实时 -> LiveTail 快照发布 + 三端点 raw 段窗合流 + ts 精确去重; 零新配置键 | Done (未提交) |

## 进度日志

- **2026-10-04 20:3x 开工**: 同步成功 b3b037ac; 开分支 feature/qb-traffic-v3; D4 与立档两项经用户拍板(6mo/1y/all 三档; 按计划立档); commit⓪ 计划入库(11619fbf); 本档案建立。
- **2026-10-04 21:xx S1 完成 (9744655b)**: traffic_store.py 末尾新增 v3 纯函数区 +661 行(行型/游标 dt 链/路径/聚合), 不接线; 新增 10 例已登记测试计划。实施期定约(§09.2 授权随做随记): 游程 dt_ms = last_seen − OpenRun.start, OpenRun.start := 链上锚点(上一记录槽位)——相邻游程间一次采样间隔并入后一游程 dt_ms, 缺省/显式语义统一; **S2 写侧须按同约定产出**。
- **2026-10-04 21:xx 认领链修复 (01bc35b6)**: 立档 commit 曾致 test_docs_forms 2 例红(档案缺 **Topics:** 行 + Refs 未双向声明); 修法: 档案补 Topics 行, 计划/报告 HTML 补 doc-refs meta, 切片 Refs 追加本档案。子智能体 stash 对照判「既有失败」不成立——stash 不回退已提交态, 该判法不可信。
- 全量复核: 2525 passed / 4 skipped, 覆盖率 99%。
- **2026-10-04 21:xx S4 完成 (30eebcf0)**: flush_interval 全链 10 文件(validate/schema/groups/models/loaders/键面 fixture 155→156/keys.md/configuration.md); sample_interval 下限改 ≥main_tick 硬校验, 倍数失配不进 errors(D5 告警留 S2a)。新增 3 例 + 守卫 parametrize 补 qb_traffic 段(此前漏登记的互检缺口, 计划内补齐)。test.full 2529 passed / 4 skipped / 99%。
- **2026-10-04 22:xx S2a 完成 (7b89d0da)**: TrafficV3Store 落盘单点(open("a")+fsync, 尾字节查补每 flush 一次); traffic_sample_mod 全文件重写(v2 触发面缩 no-op 存根留 S5); BlockBuffer/四触发+跨天封口/累积漂移 250ms/回拨钳制/handler 内 flush/00:00 硬切/stop() 幂等/失配 ceil+告警一次/has_entry 改目录判定; 断开旧目录与 index.json。sample 30→44 例, store 写侧族重写。2540 passed / 99%。S2b 接缝: _seal_run(累计器)/_maybe_flush_all(水位+淘汰)/append_records 同款纪律(agg append)/stop()(聚合封口)。
- S2a 实施期细化(已钉测试): 块首游程 dt 基准 = B.start(非块首 = 写侧游标), OpenRun.start 保留首样本实测时刻作时长基准; 块首亚秒余量成初始累积漂移由显式 dt 吸收; 午夜硬切天然 ≤1 间隔块间 gap(真空判定属 S3)。
- **2026-10-05 0x:xx S2b 完成 (62998945)**: SeriesAgg 前向记账(与 dt 链同源)/flush 时点水位封口合并 append/catch-up 硬序(补算全落盘才裁剪, 窗口=rollup_window)/hour 裁剪 tmp+replace 仅存点/淘汰删系列目录(文件名日期算龄+每小时节流)/dry_run 全短路。修复中断会话遗留实现的真缺陷: _agg_ingest_hour/day 产出行从未进待写批(hour/day 行落不了盘)。新增 17 例。2557 passed / 4 skipped, 覆盖率报 98.50%(S5 收尾核对是否跌破 99% 基线)。偏差: n 游程引导区间记上一观测速率(前向记账必然); _agg_ingest_day 月级联支防御面保留。
- 流程注记: T4 首次派发遇配额中断(现场遗留 557 行未提交实现), 重派后经逐条核对规格+补测试+修真缺陷后入库——中断遗留代码不可盲信, 必须核对。
- **2026-10-05 S3a 完成 (fca0cb96)**: grid v3 读侧区(v3_series_points/v3_totals_points/v3_series_slots 并流接缝); V3DayCache(mtime_ns+size 键控, 4MB 文本预算 LRU, 整天粒度); 真空/断连分离(≤1 间隔天然 gap 被块首桶吸收不误报); D1 实施期定约: 覆盖语义实现为「逐记录覆盖桶」(桶宽=ceil(有效dt) 天然覆盖有效 dt 全程; z 均摊槽展开多桶为字面形态), 否决向前铺格方案(ceil 累积偏移破坏时间真值)。grid 17→20, store +3 缓存例。2563 passed / 4 skipped; 覆盖率回落 98%(grid 96%, v2 残留路径经端点面间接覆盖)——S5 退役 v2 后复核回 99%。
- **2026-10-05 S3b 完成 (eb66e3c4)**: WINDOW_SPECS 13 档(3d/7d/30d→hour 行, 6mo/1y→day 行滚动窗, all→month 行, 90d 不存在 400); V3DayCache.read_agg(64 条目 LRU); 三端点翻 v3; 组端点去 global(null=桶内无成员观测); earliest_row_ts 三层全算; 前端 A4 下界 1500+13 档文案+月轴; D1 栅格形态=覆盖区间重叠秒加权。实施期定约: _qbPointsToData 非 null 点真值覆写(all 视图月行非等距防 5 天漂移, 对等距视图恒等); all 视图 meta.interval_s=标称月长 30d。grid 25/web 家族重写+5/node 探针+4。2574 passed / 4 skipped, 覆盖率 98%。
- **2026-10-05 S5 完成 (7f155e3b)**: 退役清理净 -1942 行(TrafficDatStore 整类/v2 解析面/6 存根/grid v2 残留; 删 53 条死代码用例); 保留 v1/v2 头行识别-忽略(R2)与 8 列兜底 cov_s=3600(防御); traffic_store docstring 升 v3 契约单点。实测: test.full 2526 passed/4 skipped/99%(98% 疑虑闭合); 写 IO 144+24 次/天(300x↓@2s, 20x↓@30s); 24h 窗 2 文件/组 Mx1/1y 冷读 1 open; r 行 49B→36B, 空闲天 16.4x 压缩。基线切片 testing/baselines/26-10-05-0447-qb-traffic-v3-s5-done.md。
- **2026-10-05 收尾**: 七步全清, feature/qb-traffic-v3 fast-forward 合回本地 develop(未推送, 等用户提交指令)。§9.1 端到端 --dry-run 真机验收与旧目录 qb-traffic/ 删留待用户; D2 tol 真机复核窗在 S5 后仍开放。
- **2026-10-05 S6 活尾合流(真机验收追加, 用户拍板「按推荐修复, 并入 V3」)**: 用户报「流量图不实时更新, 得等后端数据落盘时才更新」并贴 v3 实测 dat。根因定位: 写侧采样点进内存 BlockBuffer 每 flush_interval(默认 600s)批量落盘, 读侧三端点纯磁盘取数(V3DayCache), 两版间无活数据桥; 计划全文「实时」零命中 —— 设计缺口非拍板取舍。附带发现 agg 段窗更糟: 未完结小时/日/月桶在 3d+/1y/all 图恒缺(行只随封口产出)。
  修法(方案 A, set_traffic_view 快照发布同款): ①采样模块 `_publish_live_tail` 每轮 handler 末尾构建不可变 LiveTail 表整体替换引用(Web 线程只读单引用, 黄金法则 5 不破); ②store 纯函数 `v3_live_tail_slots` 复原绝对槽位 —— **head_pending(块全量未落盘)整块复用 v3_block_slots / 部分落盘从写侧游标 projected_ts 倒推**(关键定约: 中途 flush 后 buf.records 的链锚点在磁盘链上, 前向续推不成立, 倒推对非块首记录恒等且不依赖磁盘链在窗内可见 —— 1m 窗看不到上次 flush 记录时活尾定位照常); ③grid `v3_series_points` 增 tail_slots 合流(同链延续不做块间真空判定, 按槽 ts 精确去重 —— 镜像保证: 同一记录写侧推进与落盘重算的槽 ts 恒等, 保留严格更晚后缀即不重不漏); ④三端点 raw 段窗接活尾(组端点空态判据计入成员活尾)。模块宿主缺位/替身 manager 全防御退回纯磁盘读路径, 既有测试零改动。agg 段窗合流已入池 [26-10-05-1015](../issues/26-10-05-1015-feat-qb-traffic-agg-live-buckets.html)(候选 S7, 未拍板不实施)。
  新增守阵 7 条(store 3 含镜像保证族 / grid 1 / sample 1 / web 2 含端到端三态逐点一致), 全部登记各文件「## 测试计划」。**实测: test.full 2596 passed + 4 skipped / 99% / 29.09+31.05s(基线 [26-10-05-1007](../testing/baselines/26-10-05-1007-qb-traffic-v3-s6-live-tail.md); 相对本 clone 改动前真值 +7 用例 / +84 语句 / +34 分支; 附: 0846 基线绝对语句数在重写历史下不可复现, 已在基线切片注记)。**
- **2026-10-05 S6 追修: 块头 interval_s 放宽小数秒(用户报「sample_interval=1.5 实际 2s」, 拍板「直接修」)**: 根因 = `_apply_interval` 把为块头 B 行设计的整数秒口径 `int(ceil(effective))` 同时赋给 `task.interval` —— 1.5s 配 main_tick=1.5s 恰为整数倍(失配告警不触发)却被静默抬到 2s 调度; v3 计划自身不一致(下限=main_tick 硬校验 + 前端 A4 轮询下界 1500ms 均按 1.5s 档设计, 唯格式 §02 钉死整秒)。修法: ①`_apply_interval` 生效间隔保持浮点(`task.interval = effective`, 取整只发生在失配归倍数层); ②格式规格放宽「整秒 → >=1 允许小数秒」—— `_fmt_interval_s` 规范十进制(整值不带小数点与历史文件形态一致, 非整值最短往返表示如 1.5)/ `_parse_v3_interval_s`(与 run_len 正整数口径分离, NaN/inf/越界坏行)/ `V3Block`·`LiveTail`·`BlockBuffer.interval_s` int→float / `append_records` 去 `int(header[1])` 静默截断点。兼容性 = 纯放宽(旧整秒文件是小数子集, 零迁移)。新增 2 例(sample 匹配小数档 / store 小数 roundtrip+解析非法族), 重钉 1 例(30.5 从非法清单移出)。**实测: test.full 2619 passed + 4 skipped / 99%(基线 [26-10-05-1814](../testing/baselines/26-10-05-1814-qb-traffic-v3-decimal-interval.md))。**

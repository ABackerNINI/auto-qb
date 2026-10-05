# qB 流量图 v3 S6 活尾合流: raw 段窗随采样节拍实时, 不等落盘

> 摘要: 用户真机验收 v3 报「流量图不实时更新, 得等后端数据落盘时才更新」并贴 v3 实测 dat(2s 采样 + z 游程)。只读排查定位根因: 写侧采样点进内存 BlockBuffer、每 flush_interval(默认 600s)才批量落盘, 读侧三端点纯磁盘取数(V3DayCache 天文件/agg.dat), 两个 v3 版本之间没有活数据桥; 前端本就按采样间隔轮询, 后端两次落盘之间无新数据可给。计划 26-10-04-1957 全文「实时」零命中 —— 设计缺口, 非拍板取舍。附带发现 agg 段窗更糟: 未完结小时/日/月桶在 3d+/1y/all 图恒缺。用户拍板「按推荐修复, 并入 V3」→ 方案 A 实施: 采样模块每轮发布不可变 LiveTail 快照(未落盘 buffer 记录 + 开放游程冻结副本, set_traffic_view 同款单引用发布, 黄金法则 5 不破), store 新增纯函数 v3_live_tail_slots(head_pending 整块复用 v3_block_slots / 部分落盘从写侧游标**倒推**复原绝对槽位), grid v3_series_points 增 tail_slots 合流(同链延续不做真空判定, 按槽 ts 精确去重 —— 镜像保证: 同一记录写侧推进与落盘重算的槽 ts 恒等, 快照与 flush 竞态不重不漏), 三端点 raw 段窗接活尾(组空态判据计入成员活尾)。关键实施定约: 中途 flush 后 buf.records 的链锚点在磁盘链上, 前向续推不成立, 倒推且不依赖磁盘链在窗内可见(1m 窗看不到上次 flush 记录时活尾定位照常成立)。零新配置键, API 响应形状不变, 前端零改动。
> 最后活动: 2026-10-05 10:07

**Refs:** memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md, memory-bank/plans/26-10-04-1957-plan-qb-traffic-storage-v3.html, memory-bank/testing/baselines/26-10-05-1007-qb-traffic-v3-s6-live-tail.md

## 现状

- **S6 实施完成, 待提交**(develop @ 86441e54 + 工作区改动; 与 v3 主体的提交统一等用户「提交」指令)。改动面: `core/traffic_store.py`(LiveTail/LiveTailRun 契约 + v3_live_tail_slots 纯函数) · `core/traffic_grid.py`(v3_series_points 增 tail_slots 形参) · `core/modules/traffic_sample_mod.py`(live_tail 发布) · `webui/server/traffic_qb.py`(三端点 raw 段合流) · 四个测试文件(+7 守阵, 测试计划已登记)。
- 验证: `commands run test.full` **2596 passed + 4 skipped / 99% / 29.09+31.05s**(基线 [26-10-05-1007](../testing/baselines/26-10-05-1007-qb-traffic-v3-s6-live-tail.md); 相对本 clone 改动前真值(stash 往返实测)+7 用例 / +84 语句 / +34 分支)。镜像保证族守阵 `test_v3_live_tail_slots_mirror_identity_family` 钉死去重正确性根基; web 层端到端三态(纯活尾 → 滞后快照 → 快照清空)逐点一致。
- ⚠ 26-10-05-0846 基线的绝对语句数(15576)在本 clone 不可复现(另一 clone 测得, danger-guards 提交哈希在 Gitee develop 上被重写; 本 clone 无 bcc2bce2 等对象)—— 本 clone HEAD 字面真值 15398 语句已实测钉住, 后续语句面对比以 1007 基线为准。
- 已知留面(记录非缺陷, 已入池 [26-10-05-1015](../issues/26-10-05-1015-feat-qb-traffic-agg-live-buckets.html)): agg 段窗(3d/7d/30d/6mo/1y/all)仍纯磁盘 —— 未完结小时/日/月桶缺口(当前小时不出 3d 图 / 当日不出 1y 图 / 当月不出 all 图)未合流, 候选 S7 待用户拍板。
- 真机验收: 待用户在本机跑 `dev.run --dry-run` 实测图面实时性(2s 采样下应逐桶滚动); 旧目录 qb-traffic/ 删留决定权仍在用户。

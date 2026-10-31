# 3198 —— qB 流量图 agg 段活尾合流(S7): 3d+ 视图图尾真空修复

**Refs:** memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md

> 摘要: 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点, 实际上现在已经 14 日 1 点了」。根因 = `agg.dat` 只含封口行, 未封口的开放小时/当日/当月桶只活在采样写侧累计器, 读侧无通道(S6 活尾只接了 raw 段窗, 代码注释原写明「留待后续切片」; KB 早有入池 issue 26-10-05-1015 记该缺口, 候选 S7)。修法 = S6 活尾口径平移到 agg 段: `LiveTail` 增第 8 字段 `pending_agg` 发布写侧累计器未封口部分行(小时 dt 加权 + 当日/当月逐级 rollup), 读侧 `v4_agg_obs_live` 按 epoch 与磁盘封口行合流(开放桶直映 / 已封桶残余走 `v4_merge_agg`, 与写侧迟到补记同判据不双计), month 段数据面铺格计入活尾当月行(否则当月桶不在栅格被窗外过滤丢弃), 组端点空态判据与逐成员 obs 均计入活尾, degraded 路径不融合活尾保 last-good 兜底语义。前端零改动(points 末桶出值后 uPlot 数据驱动 x 轴自然延伸到当前桶, 与 raw 段活尾同形态)。
> 基线时间: 2026-10-14 05:28
> 档案: memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md

## 验收数字

- `test.full`: **3198 passed + 4 skipped** / `TOTAL 16839 160 5736 140 99%`.
- 耗时: **123.98s**(本机并行默认; 单次采样, 区间意义见 baseline.md 口径段).
- 包内脚本测试(`commands run test.pkg`): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 闸门 match 不命中, 未跑。
- Linux(WSL)侧未重测 —— 改动为读写两侧纯逻辑 + 测试, 无平台分支; 按 baseline.md 口径, 本条 Windows 侧数字为事实源, Linux 侧重跑时另立切片。

## 本改动面

- **源(5 文件)**: `core/traffic_store.py`(`LiveTail` 第 8 字段 `pending_agg`, 缺省空向后兼容 7 参位置构造) · `core/modules/traffic_sample_mod.py`(模块级纯函数 `_pending_agg_rows` + `_publish_live_tail` 发布面从 raw 键扩到 agg 键) · `core/traffic_grid.py`(读侧纯函数 `v4_agg_obs_live`) · `webui/server/traffic_qb.py`(三端点 agg 分支合流 + `_live_agg_rows` 按段过滤 + month 铺格计入活尾 + 组空态判据) · 前端 `qb_traffic_chart.js` 零改动。
- **测试(3 文件, 新增守阵 6 个测试函数)**: `test_traffic_sample.py`(部分行发布与封口清除, 假时钟驱动 handler 两轮端到端) · `test_traffic_grid.py`(开放桶直映 / 同 epoch 残余合流不双计 / 活尾空退化 / 窗外 epoch 不消费) · `test_web_longtail.py`(4 个端点测试: 3d 开放小时 / 6mo 当日 / all 当月铺格 / 组 30d 成员部分行+空态, 均带修复前形态对照; 头部「## 测试计划」同步)。
- **文档**: 本切片 · 任务档案 `tasks/26-10-14-webui-qb-traffic-agg-live-tail.md` · activeContext 切片 `26-10-14-0528-webui-qb-traffic-agg-live-tail.md` · 坑档 `pitfalls/testing/win-fake-clock-timestamp-oserror.md` · `kb.index` 生成物重建。

## 已知偏差 / 移交

- **组月段 totals 预期一度写错**: 把单系列相邻桶差分预期误搬到组口径 —— `group_totals_points` 是逐成员先差分再求和, 双成员各自基线缺失时正确值就是 0(「宁可少计一桶不出洞」)。已修正, 并补同一成员跨接缝阶段(HA 磁盘上月行 → 活尾当月行, 组 totals 差分链不断)钉住月段组合流。
- **入池 issue 26-10-05-1015-feat-qb-traffic-agg-live-buckets 正是本缺陷(候选 S7)**: 按请求边界(认领 issue 需逐项显式确认)本轮未认领未置 Done, 待用户确认后补。
- **真机走查未做**: 单元测试覆盖用户所报形态(开放桶出值 + 跨接缝 totals), 真机 qB 端到端待用户重启后观察。

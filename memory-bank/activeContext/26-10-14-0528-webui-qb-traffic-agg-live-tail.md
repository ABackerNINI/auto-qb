# 26-10-14-0528-webui-qb-traffic-agg-live-tail — qB 流量图 agg 段活尾合流(S7)已落地

> 摘要: 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点, 实际上现在已经 14 日 1 点了」。根因 = agg.dat 只含封口行, 未封口的开放小时/当日/当月桶只活在采样写侧累计器, 读侧无通道(S6 活尾只接了 raw 段窗)。修法 = S6 活尾口径平移到 agg 段: `LiveTail.pending_agg` 发布写侧累计器未封口部分行, 读侧 `v4_agg_obs_live` 按 epoch 与磁盘封口行合流(开放桶直映 / 已封桶残余走 `v4_merge_agg` 不双计), month 段铺格计入活尾当月行, 组端点空态判据与逐成员 obs 计入活尾, 前端零改动。小于 3 天的 7 档(raw 段)经核查无此问题(S6 已修), 缺陷分界即数据源分界。实测数字见基线切片(引 `commands run kb.baseline`)。
> 最后活动: 2026-10-14 05:28
> 状态: Open(实现+守阵+回归全绿, 待真机走查)

**Refs:** memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md

## 现在做到哪

S7 五步全部落地, 守阵与全量回归全绿(数字见基线切片 `baselines/26-10-14-0528-webui-qb-traffic-agg-live-tail.md`):

1. **`LiveTail` 第 8 字段 `pending_agg`**(`core/traffic_store.py`): 缺省空 = 纯磁盘 agg 读, 向后兼容既有 7 参位置构造; docstring 与模块头补 S7 口径。
2. **写侧发布**(`core/modules/traffic_sample_mod.py`): 模块级纯函数 `_pending_agg_rows(agg, now)` 产出未封口部分行 —— 开放小时(dt 加权)+ 当日(`day_hours` ∪ 开放小时部分行 rollup)+ 当月(`month_days` ∪ 当日部分行 rollup); `_publish_live_tail` 发布面从 raw 键扩到 agg 键。day/month 两级包 try/except 三型(Windows 假时钟 OSError, 坑档已记)。
3. **读侧合流**(`core/traffic_grid.py`): `v4_agg_obs_live(rows, live_rows, grid)` 按 epoch 合流; 已封桶残余走 `v4_merge_agg`(与写侧迟到补记同判据, 竞态窗不双计不出尖峰); 窗外 epoch 不消费。
4. **端点装配**(`webui/server/traffic_qb.py`): `_live_agg_rows(key, kind)` 按段过滤; 单系列 agg 分支合流 + month 铺格(`build_month_grid` 数据面计入活尾当月行, 否则当月桶不在栅格被丢弃); 组端点逐成员取活尾 + 空态判据计入活尾 + 逐成员 obs 合流; degraded(read_agg OSError)路径不融合活尾保 last-good 兜底。
5. **守阵 6 个**(均带修复前形态对照): 端点 4 个(3d 开放小时补尾 / 6mo 当日补尾 / all 当月入栅格 / 组 30d 成员部分行+空态) + 底层 2 个(发布与封口清除 / 残余合流不双计)。

## 关键口径(别改回去)

- **活尾部分行走 S6 同一快照通道**: 主循环线程发布、`AggRow` 冻结、Web 线程只读 —— 不破单一写线程。
- **month 段铺格必须计入活尾当月行**: 漏了这步, all 窗的当月桶整个不在栅格, 合流被窗外过滤丢弃(修复前连 null 都没有)。
- **组 totals 是逐成员先差分再求和**: 基线缺失不出洞 = 0; 同一成员跨接缝(磁盘上行 → 活尾当前行)差分链不断 —— 写测试预期时别把单系列相邻桶差分预期搬过来。
- **前端不动**: points 末桶出值后 uPlot 数据驱动 x 轴自然延伸到当前桶, 与 raw 段活尾同形态。

## 下一步 / 移交

- **真机走查**: 单元测试已覆盖用户所报形态, 真机 qB 端到端待用户重启后观察(图尾实时延伸到当前开放桶)。
- **入池 issue 26-10-05-1015-feat-qb-traffic-agg-live-buckets 正是本缺陷(候选 S7)**: 按请求边界未认领未置 Done, 待用户显式确认后补认领与复验记录。
- **窗口档位全景**: 13 档中 raw 段 7 档(<3 天)S6 已修无此问题; agg 段 6 档(≥3 天)由本单修复 —— 用户追问「小于3天的是否有此问题」的结论。

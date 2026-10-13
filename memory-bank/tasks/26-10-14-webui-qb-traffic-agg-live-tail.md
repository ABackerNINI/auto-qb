# 26-10-14-webui-qb-traffic-agg-live-tail — qB 流量图 agg 段活尾合流(S7): 3d+ 视图图尾真空修复

**Status:** Open(实现+守阵+回归全绿, 待真机走查)
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Topics:** webui-qb-traffic-agg-live-tail
**Summary:** 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点, 实际上现在已经 14 日 1 点了」。根因 = agg.dat 只含封口行, 未封口的开放小时/当日/当月桶只活在采样写侧累计器, 读侧无通道(S6 活尾只接了 raw 段窗, 代码注释原写明「留待后续切片」)。修法 = S6 活尾口径平移到 agg 段: `LiveTail` 增第 8 字段 `pending_agg`(发布写侧累计器未封口部分行: 小时 dt 加权 + 当日/当月逐级 rollup), 读侧 `v4_agg_obs_live` 按 epoch 与磁盘封口行合流(开放桶直映 / 已封桶残余走 `v4_merge_agg`, 与写侧迟到补记同判据, 竞态窗不双计不出尖峰), month 段数据面铺格计入活尾当月行, 组端点空态判据与逐成员 obs 均计入活尾, degraded 路径不融合活尾。触及 5 源文件 + 3 测试文件, 新增守阵 6 个测试函数(均带修复前形态对照), 前端零改动。全量回归与实测数字见基线切片(引 `kb.baseline`)。KB 早有入池 issue 26-10-05-1015 记该缺口(候选 S7), 按请求边界未认领, 待用户确认。
**Refs:** memory-bank/testing/baselines/26-10-14-0528-webui-qb-traffic-agg-live-tail.md,memory-bank/activeContext/26-10-14-0528-webui-qb-traffic-agg-live-tail.md,memory-bank/pitfalls/testing/win-fake-clock-timestamp-oserror.md

## 原始请求

用户原文: 「3天及以上的流量图视图有真空: 目前仅显示到14日0点, 实际上现在以及14日1点了, 修复」(该指令出现过两次, 含一次中断后重复投递)。后续用户追问「小于3天的是否有此问题?」—— 经代码核查确认: 小于 3 天的 7 档(1m/5m/30m/3h/6h/12h/24h)全走 raw 段, S6 早已合流活尾, 无此问题; 缺陷分界即数据源分界。

## 思考过程与决策

- **根因定位**: agg 段窗(3d/7d/30d/6mo/1y/all)的读侧只读 `agg.dat` 封口行; 未封口的开放桶(开放小时 / 当日 / 当月)只活在采样模块写侧累计器(`agg.pending` / `agg.day_*` / `agg.month_*`), 读侧没有任何通道拿到它 ⇒ 图尾停在最后一个封口桶, 当前桶整格 null 真空。raw 段窗(1m-24h)在 S6 就有活尾合流(`v4_live_tail_slots`), 故只有 3d+ 中招。代码注释原写明「agg 段窗(3d+)仍纯磁盘…留待后续切片」, 本单即该切片; KB 侧 issue 26-10-05-1015 于 2026-10-05 已入池记录同一切口(候选 S7)。
- **决策 1(发布通道)**: 活尾部分行搭 S6 同一快照通道 —— `LiveTail` 增第 8 字段 `pending_agg: tuple = ()`, 缺省空 = 纯磁盘 agg 读, 向后兼容既有 7 参位置构造。快照由主循环线程在 handler 末尾发布, `AggRow` 冻结不可变, Web 线程只读, 不破黄金法则 5(单一写线程)。
- **决策 2(读侧合流判据)**: `v4_agg_obs_live(rows, live_rows, grid)` 按 epoch 合流 —— 开放桶(磁盘无同行)直映; 已封桶残余(磁盘行与活尾部分行同 epoch, 来自 flush 竞态窗或迟到补记)走 `v4_merge_agg`: cov 加权 avg / max 取大 / totals 取后封行 / cov 相加截到桶宽 —— 与写侧 `_agg_merge_prev` 同判据, 双行合流不会双计也不会出尖峰。
- **决策 3(month 段铺格)**: `build_month_grid` 的数据面必须计入活尾当月行 —— 否则当前月桶整个不在栅格里, 合流结果被窗外过滤丢弃(all 窗修复前连 null 都没有, 比 hour/day 段更重的形态)。
- **决策 4(组端点)**: 空态判据(「组从未产过流量」)与逐成员 obs 都计入活尾部分行 —— 修复前成员仅活尾(零盘)会被误判空态返回 `points: []`; 组尾桶 = Σ 成员观测(无行成员按 0 计), 组口径不变。
- **决策 5(degraded 不融合)**: `read_agg` OSError 的 degraded 路径不融合活尾, 保持 last-good / 空态标 stale 的兜底语义(§08), 不以空态冒充无数据的老口径不动。
- **决策 6(前端零改动)**: points 末桶出值后 uPlot 数据驱动 x 轴自然延伸到当前桶, 与 raw 段活尾同形态; `qb_traffic_chart.js` 无需任何改动。
- **决策 7(假时钟异常面)**: `_pending_agg_rows` 的 day/month 两级推算包 `try/except (ValueError, OSError, OverflowError)` —— Windows 上 1970 前本地日期过 `datetime.timestamp()` 抛 OSError, 被既有用例的假时钟首次触达; 生产时钟恒正不受影响, 纯增益面缺该级只回到修复前形态。教训入坑档 `pitfalls/testing/win-fake-clock-timestamp-oserror.md`。
- **实现期发现(测试预期错误, 非产品缺陷)**: 组月段 totals 预期一度把单系列相邻桶差分预期搬到组口径 —— `group_totals_points` 是逐成员先差分再求和, 双成员各自基线缺失时正确值就是 0(「宁可少计一桶不出洞」)。已修正并补同一成员跨接缝阶段(HA 磁盘上月行 → 活尾当月行)钉住月段组合流差分链。
- **事实回写面**: 无常青主题文档记载 agg 读路径(stale 声明只存在于入池 issue 与已冻结的 S6 基线切片, 后者按设计不可改), 故事实沉淀于本档案 + activeContext 切片 + 基线切片; 根 README 与 docs/configuration.md 的流量记载限于配置语义, 不受本次读侧改动影响。

## 实现计划

按五步串行执行, 每步测试全绿再进下一步:

1. `traffic_store.py`: `LiveTail` 增 `pending_agg` 字段 + docstring S7 口径 + 模块头读路径说明。
2. `traffic_sample_mod.py`: 新增模块级纯函数 `_pending_agg_rows(agg, now)`(小时部分行 dt 加权; 当日行 = `day_hours` ∪ 开放小时部分行按 epoch 过滤后 rollup; 当月行 = `month_days` ∪ 当日部分行 rollup); `_publish_live_tail` 发布面从 raw 键扩到 agg 键。
3. `traffic_grid.py`: 新增读侧纯函数 `v4_agg_obs_live`(epoch 合流 + `v4_merge_agg` 残余合流 + 栅格窗外过滤)。
4. `traffic_qb.py`: `_live_agg_rows(key, kind)` 按段过滤; 单系列 agg 分支合流 + month 铺格计入活尾; 组端点逐成员取活尾 + 空态判据 + month 铺格 + 逐成员 obs 合流。
5. 测试与回归: 底层 2 个守阵(发布/合流) + 端点 4 个守阵(3d/6mo/all/组, 均带修复前形态对照) + 全量回归 + 基线切片 + 本档案 + 切片 + 坑档 + `kb.index`。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| 1 | LiveTail 增 pending_agg 字段 | ✅ | core/traffic_store.py; 7 参位置构造向后兼容 |
| 2 | 采样模块发布未封口聚合部分行 | ✅ | core/modules/traffic_sample_mod.py; `_pending_agg_rows` + 发布面扩面; test_traffic_sample.py +1 守阵 |
| 3 | traffic_grid 合流纯函数 | ✅ | core/traffic_grid.py; `v4_agg_obs_live`; test_traffic_grid.py +1 守阵 |
| 4 | 三端点读侧合流装配 | ✅ | webui/server/traffic_qb.py; `_live_agg_rows` + 单系列/组 agg 分支 + month 铺格 |
| 5 | 测试补齐与全量回归 | ✅ | test_web_longtail.py +4 端点守阵; 全量回归数字见基线切片; 回写四件 + kb.index |

## 进度日志

- **2026-10-14 05:1x** 实现五步全部落地; 底层与端点守阵先红后绿; 修两处实现期问题: ① day/month 两级推算被 Windows 假时钟触达抛 OSError(既有 5 用例红) —— 包 try/except 三型后复绿, 教训入坑档; ② 组月段 totals 预期写错(单系列差分预期误搬组口径) —— 修正为组口径正确值并补同成员跨接缝阶段。
- **2026-10-14 05:2x** 全量回归通过(`commands run test.full`, 数字见基线切片 26-10-14-0528); 建基线切片、本档案、activeContext 切片、坑档, `kb.index` 重建; 随本专题入库。
- **2026-10-14 05:3x** 用户追问「小于3天的是否有此问题?」—— 只读核查确认 raw 段 7 档 S6 已合流无此问题, 缺陷分界即数据源分界; 该结论补入原始请求节。

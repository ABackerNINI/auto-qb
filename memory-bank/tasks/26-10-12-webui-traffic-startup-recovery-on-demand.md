# 26-10-12-webui-traffic-startup-recovery-on-demand — 流量启动恢复改为按需读取口径

**Status:** Done
**Added:** 2026-10-12
**Updated:** 2026-10-12 21:04
**Topics:** webui-traffic-startup-recovery-on-demand
**Summary:** 报告 26-10-12-1923 取证「启动后 WEB UI 需数秒才正常」= **启动死区**: 装配序最后的 `TrafficSampleModule.start()` → `_recover_aggregates()` **静默**把 `qb-traffic-v4/` 全部历史天文件重读一遍并逐槽重算(实测恢复 7.09~7.28s / 死区 11.16s / 约 +1.5~2.0s/天 无界增长)。用户定调三条: ①流量图方案定调一直是**按需读取**(不打开不读历史文件; 打开 24h 图最多读 2 天), 启动恢复全量重读是**该定调的实施缺口**; ②`rollup_window: 1000000D` 永久保留是**有意设定**; ③保持同步恢复。按计划 26-10-12-2010 实施完毕(W0-W2): 恢复读集下界 `now - rollup_window` → **agg 水位所在日**(常态 1 个、跨日界至多 2 个天文件), `agg.dat` 仍按系列照读, agg 无水位时全量兜底 + INFO; 保留口径与图表读侧零改动; 新增起止 INFO + 计数属性埋点(读集有界可机检)与 17 个守阵(含读侧契约 13 档逐档机检); `test.full` 3164 passed + 4 skipped。B2(后台化)/B3(raw_window 删除)/A1(调小窗口)/C1(搜索索引首建) 出局或另题。**真机走查(重启看 INFO 行与死区时长)留待用户。**
**Refs:** memory-bank/plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html,memory-bank/reports/26-10-12-1923-report-webui-startup-latency.html,memory-bank/activeContext/26-10-12-2017-webui-traffic-startup-recovery-on-demand.md,memory-bank/testing/baselines/26-10-12-2019-webui-traffic-startup-recovery-on-demand.md

## 原始请求

用户原文(三轮): ①「按报告写一个修改计划 26-10-12-1923-report-webui-startup-latency.html。之前的流量图方案定调一直是按需读取, 这是实施缺口。即不打开流量图理论上不需要读取历史文件。打开24小时流量图理论上最多读取2天的数据。注: rollup_window 是有意设置的, 永久保留数据, 理论上此场景下不能有太大性能问题。」②「为什么还需要恢复读取? 不应该是打开时触发读取吗?」③「简单在报告里解释一下, 然后提交」。

## 思考过程与决策

- **定调对齐(用户 D1)**: 按需读取是**图表读侧**既定契约 —— 不打开不读历史文件, 打开 24h 最多读 2 天。核对代码: 读侧早已如此(`webui/server/traffic_qb.py` `_payload_series` → `V4DayCache.read_window` 按窗口日期集只读涉及天文件, 24h 常态 2 / 窗首跨午夜至多 3; agg 段窗只读单文件 `agg.dat`; 前端 `_qbPollStart`/`_qbPollStop` 只在页签打开期间轮询, 关闭后零请求路径)。⇒ **缺口定位在启动恢复路径**, 不在读侧。
- **保留口径不动(用户 D2)**: `rollup_window: 1000000D` 是有意设定 ⇒ 报告 §7 的 B3(补 `raw_window` 天文件删除)与 A1(调小 `rollup_window`)出局; 报告 §4.2 已证「调小窗口治不了本」(系列还在产数据则天文件永不删, 30D 稳态仍约 750 个天文件)。本计划不动 hour 行裁剪与系列淘汰口径。
- **修复靶点**: 读集下界 `now - rollup_window` → `v4_day_epoch(wm_hour)`(`wm_hour` = `parsed.hours[-1].epoch`, agg 文件尾最新封口小时)。传**所在日**而非水位时刻, 因为 `series_day_dates` 按**文件名日期**过滤(`v4_date_str_epoch(d) >= min_epoch`), 传细时刻会误排掉水位当天的天文件; 水位之后的 raw 恰好落在 `day(wm_hour)` 或更晚的天文件里(天文件 00:00 硬切、块不跨天)。已封口小时不重算的判据(`h <= wm_hour`)代码里**已存在** —— 本次只把「哪些文件读」收敛到同一水位, 不新增语义。
- **为什么不彻底取消恢复读(用户追问②)**: 恢复读的不是图表数据, 而是**写侧聚合链的缺口** —— 内存累计器(`_agg_states`: `pending` 当前小时 / 当日 / 当月)随进程消失, 未封口小时的 raw 只落在天文件里, 是唯一幸存来源。不补则那几小时**永不封口** ⇒ hour 行永久缺失 ⇒ day/month 行(只从 hour 行逐级派生, **不从 raw 直聚**)永久偏小, 且 3d/6mo/1y/all 窗口只读 `agg.dat`、缺口在图上永远看不到补; 重启后首次 flush(默认 ≤600s)就会把残缺累计器封成行, 错误当场固化。让「打开图表」触发它 = 读路径写盘 ⇒ 破坏单写线程(黄金法则 5)与读侧只读契约, 且不打开就永久丢数据。要「重启零 raw 读」只有两条取舍路(**在途累计器落盘** / **接受空洞**), 均不免费 —— 记入报告 §10 与计划 §4.3, 当前设计取「raw 单一事实源 + 重启补读有界」。
- **不做 B2 后台化(用户 D3)**: 读集收敛后同步成本有界, 后台化会与在线记账争 `_agg_states`/水位, 风险大于收益。
- **正确性边界(计划 §5)**: agg 缺失/无可信水位 ⇒ 退回现口径全量兜底 + 日志(诚实兜底, 不猜); 崩溃窗口 ≤ `flush_interval` 的 raw 已在天文件, 由 `h > wm_hour` 判据补算; 长停机跨日时中间日期无文件 ⇒ 真空(与块间 gap 同语义); catch-up → append → trim 硬序不变; 恢复侧读集(日期区间 ≤2)与读侧图表窗首外扩(至多 3)同阶不同数, 不强行统一。
- **埋点(报告 B4)**: 恢复起止 INFO + 计数属性(系列数 / 读入天文件数 / 补算小时数 / 耗时), 把「读集有界」变成可机检事实 —— 报告把「完全静默」列为本次排查最大障碍。
- **文档面**: 报告追加 §10「为什么启动恢复必须读 raw」(用户要求「简单解释」)并抬 `doc-updated`; 计划 §2 已把 D1-D5 记为实施边界。

## 实现计划

见 [计划 26-10-12-2010](../plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html) §4 方案设计 / §6 改动点 / §7 波次与验收:
**W0** 冻结契约与验收基线(零代码) → **W1** 后端(`_recover_series` 读集下界 + `_recover_aggregates` 埋点 + 模块/方法 docstring; `traffic_store.series_day_dates` docstring) + 新守阵(单系列读集 ≤2 天断言 / fallback 不烂 / 既有等价·硬序·空闲 cov 守阵全绿 / 注入红验) → **W2** 收尾(`test.full` + 基线切片 + 回写 + 真机走查)。

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| W0 | 冻结契约与验收基线 | 已完成(既有守阵全绿: test_traffic_store 41 passed / test_traffic_sample 66 passed; 开工基线取 20:19 切片) |
| W1 | 后端: 读集下界 = agg 水位所在日 + 埋点 + 守阵 | 已完成(17 新守阵 + 注入红验; 计划外 issues 26-10-12-2104 入池) |
| W2 | 收尾: 全量测试 + 基线切片 + 回写 + 真机走查 | 已完成(真机走查留待用户) |

## 进度日志

- 2026-10-12 19:36 会话开工同步 `9548367d`; 读报告 26-10-12-1923 + 核代码(`traffic_sample_mod._recover_aggregates/_recover_series/_agg_credit_day_file`、`traffic_store.series_day_dates/read_day`、`V4DayCache.read_window`、`traffic_qb._payload_series`), 确认「读侧已按需、缺口在启动恢复」; 另核 `series_day_dates` 生产调用方只有恢复路径一处(单点修改)。
- 2026-10-12 20:10 计划成文 [26-10-12-2010](../plans/26-10-12-2010-plan-webui-traffic-startup-recovery-on-demand.html)(Open, 待实施确认): 依据报告 + 用户三条定调收敛靶点, B2/B3/A1/C1 出局或另题。
- 2026-10-12 20:17 用户追问「为什么还需要恢复读取? 不应该是打开时触发读取吗?」⇒ 论证写侧聚合链缺口(内存累计器随进程消失 / 未封口小时 raw 为唯一幸存源 / 不补则 hour·day·month 永久缺失且首 flush 即固化 / 读侧只读契约不容写), 并按用户指令把该说明**简单追加进报告 §10**(报告 `doc-updated` 抬至 26-10-12-2017)。
- 2026-10-12 20:17 收尾入库: 纯文档轮(计划 + 报告 §10 + 本档案 + 活跃切片 + 基线切片), 零代码零测试改动; 数字见 `commands run kb.baseline`。
- 2026-10-12 20:27 用户要求「其它视图需要读取多少历史文件, 需要一一定下来」⇒ 逐档核定读侧读集并钉进计划 **§3.2 契约表**(13 档 × 三类文件: raw 天文件 / `agg.dat` / 限速天文件; 含日期数公式、跨日界规则、24h 恒 2·3 的原因、组作用域放大只在数据面、「不打开 = 0 文件」)。**关键发现**: 唯一随窗口/历史增长的项 = **限速注解面**(1 文件/天且不淘汰 ⇒ 6mo 约 183 / 1y 约 366 / `all` 随保留无界; 已由 mtime+size 缓存 + 单文件几十条兜住), 备选(限速事件 rollup 进 `agg.dat` / 长窗按段裁剪)记为另题; §6/§7 加「读侧契约逐档机检」验收项(表驱动守阵)。
- 2026-10-12 21:04 用户指令「实施计划」⇒ W0-W2 实施完毕: ①读集下界改 `v4_day_epoch(wm_hour)`(D1), fallback 全量兜底(D5); ②起止 INFO + `recovery_reads`/`recovery_stats` 计数属性(§4.2); ③17 个新守阵(读集有界 24 系列×30 天 / fallback 不烂 / 埋点行 / 读侧契约 13 档逐档机检 / 前端轮询门控), 注入红验通过(下界改回 `now - window` ⇒ 红, 还原即绿); ④`test.full` 3164 passed + 4 skipped / 41.3s / 覆盖 99%(基线切片 26-10-12-2104); ⑤e2e 全量 61 失败全为桩服务 8137 中途拒连(环境坑, 零断言内容失败), 复跑 @fast 子集 108/0 证实健康(全量复跑留待环境稳定); ⑥`config/models.py` `QbTraffic` docstring 旧「三义合一」口径漂移按范围守恒入池 issue 26-10-12-2104(未动); ⑦真机走查(重启看 INFO 行与死区时长)留待用户。

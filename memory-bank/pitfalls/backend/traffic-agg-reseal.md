# 流量聚合: 已封桶的迟到补记与单系列封口异常

> 摘要: 小时/日/月聚合行的封口有两条非显然约束 —— ①已封口的桶**仍会**收到迟到信用(长空闲 z 游程
> 延迟到 `ZRUN_FLUSH_S`(24h)才封口, 其槽位区间起始落在早已弹出的桶上), 故「同 epoch 重封」必须是
> **合流**而非替换(替换只对完整重算成立); ②逐系列封口循环里的单点异常会**放大成全局停写** ——
> 其余系列本轮不封口 + 整批 agg 行丢弃 + 抛点在状态复位之前 ⇒ 同一错每轮 flush 复现。
> 真机实证(2026-10-13): 日行 cov_s 只留残余(44712 vs 离线全量 86400), 并每 10 分钟刷
> 「逐级聚合无有效覆盖」, 期间全系列小时行一个多小时未落盘。
> 触发: 逐级聚合无有效覆盖, cov_s 只留残余, 同 epoch 重封, 替换丢覆盖, 覆盖率偏小, agg 停写, 全系列小时行不落盘, 一个系列坏全批不写, 每轮 flush 复现, pending.pop, ZRUN_FLUSH_S, 延迟封口, 长空闲游程, 重封, 亚秒残余

### 已封口的桶仍会收到迟到信用 —— 同 epoch 重封必须「合流」

- **触发**: 改聚合封口/累计器并入(`_agg_flush_series` · `_agg_ingest_hour` · `_agg_ingest_day` · `_ingest_acc`),
  或排查「日/月视图流量覆盖率明显偏小」「agg.dat 里同一小时两行」。
- **判别**: 问一句「桶弹出之后, 还会不会有人往这个小时里记账?」—— 答案是**会**: `_agg_flush_series`
  在小时完结时 `pending.pop(h)`, 而信用入账时点取决于**记录封口**时点: 长空闲 z 游程按
  `ZRUN_FLUSH_S`(24h)才封口, 其槽位区间起始落在早已封口的桶上 ⇒ 重建出一个**只含残余**的桶。
  残余可以很大(真机每小时两行、两段相加恰满一小时), 于是「同 epoch 取最后一行」的替换语义
  把先到的那部分覆盖丢掉 —— 真机 global 日行 `cov_s` 44712, 按合流重算 = 86400 = 离线全量重算值。
- **处置**: 同 epoch 重封走**合流**(`v4_merge_agg`: cov 相加并截到桶宽 / avg 按各自 cov 加权 /
  max 取大 / totals 取后封行), 且**落批的必须是合流行**(解析按「同 epoch 取末行」, 落残余行
  等于读侧也只看到残余)。替换语义只留给**完整重算**(重启 catch-up 走 `_catch_up_level`, 不经
  合流, 否则重复计)。配套: 小时行 `cov_s` 下限 1 —— 亚秒残余桶经 `int(round())` 会折成 0,
  该行成为日里唯一子行时 `Σcov_s = 0`, day 封口直接抛「逐级聚合无有效覆盖」(真机崩点)。
  注意历史坏行不回补: 已写进 agg.dat 的残余行是既成事实, 真值仍在未过裁剪窗的 raw 天文件里。
- **守阵**: `test_traffic_store.py::test_v4_merge_agg_same_epoch_reseal_keeps_coverage` ·
  `test_traffic_sample.py::test_agg_reseal_merges_late_credit_keeps_full_coverage` ·
  `test_traffic_store.py::test_v4_hour_agg_subsecond_coverage_floors_cov_to_one` ·
  `test_traffic_sample.py::test_agg_flush_subsecond_hour_rolls_up_without_raise`
  (红验: 还原替换语义 / 摘掉 cov_s 下限即红, 见 `testing/guards.md` 流量聚合封口批次)

### 逐系列批处理循环里的单点异常会放大成全局停写

- **触发**: 写「逐系列循环 + 每系列落盘」这类批处理(封口 / 导出 / 发布 / 淘汰), 或排查
  「某功能静默停写, 而日志里只有一条别的错」。
- **判别**: 看异常抛点相对**状态复位与落盘**的位置。本仓实例: `_agg_append` 在 `_agg_flush_series`
  末尾, 而可抛的日封口在它之前 ⇒ 一次异常同时造成三件事: ①其余系列本轮也不封口 ②本批 agg 行
  整批丢弃 ③累计器停在「已封未落盘」态 ⇒ **同一错每轮 flush 复现**(真机: 每 10 分钟一条,
  全系列小时行一个多小时没落盘, 日志只报那一条)。
- **处置**: 逐系列 **try/except 隔离** + 善后单点(`_agg_reset_after_error`): 同系列恢复前只告警
  一次(免刷屏), 并**重置该系列累计器** —— 不重置就会每轮重抛同一错; 重置后后续小时照常封口,
  缺口由下次重启 catch-up 从天文件重算补回(告警行写明出处, 不猜不静默)。留一眼恢复健康路径:
  成功时清掉告警记忆, 下次再错重新告警一次。
- **守阵**: `test_traffic_sample.py::test_agg_flush_all_isolates_series_error_and_resets`
  (红验: 去掉 try/except, 注入异常直接上抛即红)

# 3172 —— 流量聚合封口三修: 亚秒残余 cov_s 下限 · 同 epoch 重封合流 · 逐系列封口隔离

> 摘要: 承接真机报错「逐级聚合无有效覆盖」(另一工作区旧快照)。三处同族修复: ①小时行 `cov_s` 下限 1
> (亚秒残余桶经 `int(round())` 折 0 会让日封口的 `v4_rollup_agg` 失掉 `Σcov_s > 0`); ②同 epoch 重封
> 由「替换」改**合流**(`v4_merge_agg`, 落批行 = 合流行) —— 长空闲 z 游程延迟封口会给早已封口的桶
> 补记, 替换语义把先到的覆盖丢掉(真机日行 cov_s 44712 vs 离线全量 86400); ③`_agg_flush_all` 逐系列
> 隔离 + `_agg_reset_after_error`(单系列异常不再放大成「全系列 agg 静默停写 + 每轮 flush 复现」)。
> 新增 5 条守阵(含 3 条模块级走真实 `_agg_flush_series` 链路), 三处红验闭环。
> 基线时间: 2026-10-13 02:19

## 验收数字

- `test.full`: **3172 passed + 4 skipped** / `TOTAL 16750 162 5702 141 99%`。
- 耗时: **45.5 ~ 60.8s**(本轮 5 次 `test.full` 采样, 中位 56.4s; 本机并行默认 `-n 8`)。
- Linux 侧未重测(改动为平台无关的聚合语义; WSL 侧仍停在 `testing/baseline.md` 常驻警告里的旧值)。

## 本波改动面

- `src/auto_qb/core/traffic_store.py`: `v4_hour_agg` 的 `cov_s` 加下限 1; 新增 `v4_merge_agg` 与 `_agg_width_s`。
- `src/auto_qb/core/modules/traffic_sample_mod.py`: 新增 `_agg_merge_prev`; `_agg_ingest_hour`/`_agg_ingest_day`
  落批行改合流行; `_agg_flush_all` 逐系列隔离 + 新增 `_agg_reset_after_error`; `__init__` 加 `_agg_warned`。
- 守阵 5 条: `test_traffic_store.py` 2 条(亚秒 cov_s 下限 / 重封合流) + `test_traffic_sample.py` 3 条
  (亚秒桶日封口 / 重封合流走真实 flush 链 / 逐系列隔离), 两份测试文件头部「测试计划」清单同步;
  `memory-bank/testing/guards.md` 新增「流量聚合封口批次」段。

## 已知偏差 / 移交

- 真机数据复算(只读取证): 合流后日覆盖逐日等于离线全量重算(global 10-12 `44712 → 86400`)。
- 历史坏行不回补(解析仍按「同 epoch 取末行」; raw 天文件未过裁剪窗, 回补需另开一次性重算)。
- 真机实例需重启后由 catch-up 补回停写期间(10-13)缺失的小时行。

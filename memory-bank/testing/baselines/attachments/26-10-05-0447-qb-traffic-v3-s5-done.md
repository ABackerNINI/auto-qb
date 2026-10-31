# 基线切片 26-10-05-0447 — qB 流量存储 v3 S5 收尾: 退役清理 + 实测基线

> 摘要: 计划 26-10-04-1957 S5(批次三末步)。index.json 机制全删(条目门/updated_at/对账重建孤儿
> 条目)、v1/v2 解析与封口/归并重写死代码、traffic_sample_mod 的 v2 no-op 存根、grid 的 v2 读侧
> 残留(series_bucket_obs/_obs_from_*/earliest_row_ts)与只测死代码的旧用例一并删除; 三模块合计
> -2251 行/+309 行(净 -1942)。traffic_store.py 模块 docstring 重写为「格式 v3 契约」主题事实单点;
> 保留面: v3 读侧对 v1/v2 旧头行的识别-忽略(换代语义 R2)、agg 8 列旧行兜底 cov_s=3600(计划
> §02.2 明文防御)。新增 3 例实测单测(写 IO 2s/30s 档计数器防回归 + 体量对比)。
> 实测数字全部由单测/临时目录构造采集, 未触生产数据目录(auto-qb-data/)与 config.yml。

> 基线时间: 2026-10-05 04:47
> 档案: memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md (S5)

**Refs:** memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md · memory-bank/plans/26-10-04-1957-plan-qb-traffic-storage-v3.html

- 分支: feature/qb-traffic-v3 @ c20e51c0 (+ 本轮未提交改动: core/traffic_store.py /
  core/traffic_grid.py / core/modules/traffic_sample_mod.py / tests/test_traffic_store.py /
  tests/test_traffic_grid.py / tests/test_traffic_sample.py / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2526 passed + 4 skipped, 30.52s, 覆盖率 TOTAL 99%**
  (15252 语句 / 162 未覆盖 / 5222 分支 / 135 partial)
- 相对上记录 (S3b 后, 任务档案 26-10-05: 2574 passed / 98%): passed 2574 -> **2526**(净 -48 =
  删只测已退役死代码的 v2 用例 53 条、新增实测用例 5 条); 覆盖率 98% -> **99%**(v2 残留路径
  删除后自然回升, S2b 起的 98% 疑虑闭合)。
- **写 IO 实测(全局系列一整天采样流经采样模块 + store, 假时钟, open 计数断言进单测防回归)**:
  - 2s 档(43200 样本/天): 天文件 append open **144 次/天**(86400s / flush_interval 600s; 含午夜
    硬切收尾)+ 次日首样本 1 次 + agg append **24 次/天**(每小时封口 1 次) —— 对照 v2 逐行追加
    43200 次/天 = **300x 下降**(计划 §09.1 ≈144 达标)。
  - 30s 档(2880 样本/天): 同样 **144 次/天 + 24 次 agg**(写 IO 与采样率解耦, 只随 flush_interval)
    —— 对照 v2 2880 次/天 = **20x 下降**(计划 §09.1 口径)。
- **读放大复核(S3a/S3b 既有 open 计数断言全绿)**: 24h 窗只开 2 个日期天文件(缓存重查零 open);
  3d/7d/30d 组窗只读成员 agg 文件(2 成员恰 2 open = M×1); 1y 单 agg 冷读恰 1 open。
- **体量对比(同一构造采样序列, v2 行型布局仅作测量基线)**: 活跃 r 行宽 49B(v2 raw 行, 规格带
  40-52B) -> **36B**(v3 r 行, 规格带 30-40B; 无时间戳列, 时刻由 dt 链推算); 活跃天数据区
  141120B -> 103680B(-26%); 全空闲天 66240B -> 4032B = **16.4x 压缩**(z 游程 144 行 vs 零值
  raw 2880 行)。
- grep 验收: src/ 与 tests/ 无 index.json / 旧行型(v2 raw/hour/z、旧解析与封口面)残留引用。

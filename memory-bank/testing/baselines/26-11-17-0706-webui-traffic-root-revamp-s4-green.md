# 6226 —— traffic root revamp S4 修复轮全量基线(bench cov-skip 与覆盖率补测两阻断已修, 全绿)

> 摘要: traffic root revamp S4 修复轮全量基线(bench cov-skip 与覆盖率补测两阻断已修, 全绿)
> 基线时间: 2026-11-17 07:06
**Refs:** memory-bank/tasks/26-11-15-webui-traffic-root-revamp.md

## 验收数字

`commands run test.full` 实测(2026-11-17 07:06 与 07:19 两跑同表, Windows 开发机, 基线 commit efc90ea5 + 本轮纯测试增量):

```text
TOTAL                                                27925     72   9848     78    99%
Required test coverage of 99.5% reached. Total coverage: 99.60%
6226 passed, 6 skipped in 163.64s (0:02:43)
```

- 汇总: 6226 passed / 6 skipped / 0 failed, 覆盖率 99.60%(Windows 闸 99.5 **PASS**)。闸行原文取自当日同表跑(silent_success 只出结论行; 覆盖表 TOTAL 行三次跑逐位一致 27925/72/9848/78, 闸值 = (27853+9770)/37773 = 99.60% 随表定)。
- **6 skipped = 2 基线 skip(前片 26-11-17-0617 同款)+ 4 bench**(`test_traffic_qb_bucket_cache_perf.py` 整模块经 `pytest.mark.skipif(coverage.Coverage.current() is not None)` 在插桩环境 skip —— 两阻断之一落地的直接观测面)。
- **与前片 26-11-17-0617(红快照)的关系**: 前片两阻断在本片全部清偿 —— ①A4 冷态插桩红: bench 电池改标定环境 skip(隔离 --no-cov 实测绿维持前片验收数字节 A4 标定环境条目数字, 判据本体不变); ②覆盖率闸 99.40% FAIL: 补 17 条真测试收口, 缺口单位(miss+partial) 219 → 150(净 -69; miss 110 → 72 / partial 109 → 78), 最大缺口面 `core/traffic_grid.py`(前片 35 miss + 29 partial)经折叠态机/游标/槽组守卫定向补测清偿, 其余 codec/agg/traffic_qb 零星面同批覆盖。用例账目: 6215 → 6232 收集(+17 新测试), bench 4 例由跑改 skip, passed 6212 → 6226(= -3 bench 转skip + 17 新)。
- A1-A8 落地映射**沿用前片** 26-11-17-0617「本改动面」节的 F1-F8 七提交映射(T1-T7 基线 efc90ea5 未动, 本轮零 src 改动)。

## 本改动面

本轮**零 src 改动**(纯测试收口, 主会话拍板「写真测试不降窗」), 逐文件:

- `tests/test_traffic_qb_bucket_cache_perf.py`(+21): bench 电池标定环境 skip —— 模块级 `pytest.skipif(_COV_MEASURING)` 单点(经 `coverage.Coverage.current()` 探测插桩; ImportError 分支 `pragma: no cover`), 模块 docstring 写明标定环境口径与 ~4.6x 膨胀实测(345-380ms -> 1581-1724ms), A4 阈值断言只在无插桩环境有效, 判据本体不改(抬线会让 A4 在正常环境失真)。skipif 行带 `# owner: abacker`(计划外发现: 全仓 skipif 元守卫 `test_platform_tolerance_guards.py::test_repo_skipif_all_have_reason_and_owner` 要求 reason + 行范围内 owner, 首跑此面红一条, 补注释即绿)。
- `tests/test_traffic_grid_grid.py`(+10 测试): 折叠态机与缓存防线直构面 —— `_bucket_index` 双向校正环(非精确二进制桶宽触发实证 + 键语义不变式)/ `_check_gap_bound` 非法值 fail-fast + None 缺省 / `sanitize` 窗界再对齐契约(复位 + 冷重建信号 + 哨兵不误判)/ `emit` 窗外回填与标记过滤 + 封口源桶解析(字节守恒)+ 源桶缺失 KeyError / `held_at` 四扫描路径 / `sealed_floor` null_lo 兜底 / 接缝摊配零份额与余额归接(字节守恒)/ 天游标结构校验 9 失效面 + 2 合法对照 / 槽组时序守卫 fail-fast。
- `tests/test_traffic_grid_bucket_cache.py`(+3 测试): 非 raw 段窗 ValueError 门闩 / 未来块空槽组游标停驻推进(续展与全量现算逐位等价)/ 游程中段停驻 `last_rec` 记账(续展逐位等价)。
- `tests/test_traffic_store_agg.py`(+2 测试): `_acc_upsert_row` 同 epoch 原位替换/无则追加(不得重复行)/ `_agg_reseal_closed_day` 已关日迟到重封三面(存根首写 + 合流对照 + 月层不匹配零动作, 背日不级联翻月)。
- `tests/test_traffic_store_codec.py`(+2 测试): `v4_block_slots_from` 游标停驻非游程型 TypeError 门闩 / 未知记录型白名单 TypeError fail-fast。
- `tests/test_web_traffic_qb.py`(+1 断言): `test_service_defensive_paths` 增补 `bucketcache` 构造期预建单例断言(F4-2/3 只读引用)。
- 全部新测试同步各文件头部 docstring 测试计划清单; `dev.fmt` 全量过(yapf 零 diff)。

新测试判别力口径: 每条钉一个防御面/契约本体, 集成面等价性(逐位对账)归 bucket_cache 主阵, 两层互不替代; 受影响六电池 `test.one` 全绿(10/60/12/29/23/4 passed), bench 4 例在 `--no-cov` 标定环境照常跑(15.96s 实测)。

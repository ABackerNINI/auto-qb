# 1,804 变异, 2,843 s, rc=0 —— core W5 traffic_sample_mod 中池单轮复跑 children 1 — killed 1,703, survived 97, timeout 4, 杀死率 94.40%

> 摘要: core W5 traffic_sample_mod 中池单轮复跑(children 1, 1.5 GiB ulimit): 1,804 变异 · 2,843 s · rc=0 · killed 1,703 · survived 97 · timeout 4 · no-tests 0 · 杀死率 94.40%(含 timeout 94.62%) · 峰值 used 3,250 MB / avail 最低 8,711 MB / 单进程峰值 1,340 MB / 零 OOM。97 条 survived 逐 id 对差 W5 终态账本: **真新增 0**(表面 2 条为本轮源码修复后的重编号), 4 条 timeout 单列。
> 基线时间: 2026-11-02 20:44
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **TOTAL(变异单轮)**: **1,804 变异 / 2,843 s(47 分 23 秒) / rc=0**; killed **1,703** · survived **97** · timeout **4** · no-tests **0** · not-checked 0; 杀死率 **94.40%**(含 timeout 口径 **94.62%**)。`1,703 + 97 + 4 = 1,804` 闭合。
- **资源**: 峰值 used **3,250 MB** · avail 最低 **8,711 MB** · 单进程 mutmut 峰值 **1,340 MB** · **OOM 0**(全程零 OOM, 无 `wsl.exe` 客户端被切)。
- **目标 / 池 / 工具**: `**/core/modules/traffic_sample_mod.py` · 池 3 文件 `tests/test_traffic_sample.py` / `tests/test_traffic_limits.py` / `tests/test_traffic_store.py` · mutmut **3.8.1** · `--max-children 1` · `timeout_multiplier=15` · `ulimit -v 1536 MB` 失控分配保护。
- **镜像口径**: `~/auto-qb-mut` head **c32e8e03**(本轮 `[head]` 实测); 本地分支已到 8867f75e, 但该区间对目标与三个池文件零改动。池文件 `tests/test_traffic_limits.py` 在本地 8867f75e 比镜像多 32 行(W2 新守阵, 未进本轮), 本轮实测口径以镜像 c32e8e03 为准。收尾镜像刷新另记任务档案 R41。
- **id 级对差(97 survived vs W5 终态账本 26-11-01-0235)**:
  - **95** 条 id 直接重合 W5 终态账本; 表面新增 **2** 条 `_publish_live_tail__mutmut_63` / `_67`。
  - **真新增 0**: 目标源码在 W5 之后被 `59e814fd`(issue 26-11-01-0050 修复)改了一行 `buf is not None` -> `has_block`, 使 `_publish_live_tail` 内变异重编号 −1。按 diff 映射: 旧 64(`or 1` -> `or 2`)现为 63 · 旧 68(`0.0` -> `1.0`)现为 67; 现 64/68 killed 对应旧 65/69, 与 W5 终态一致。**无移入**。
  - **三分类(97)**: 已知等价 **94** · 已知假存活 **1**(`__init____mutmut_13`, W5 已证全套件可杀) · 已知 bug 面 **1**(`_publish_live_tail__mutmut_59`, issue 已修复, 变异转等价候选待销账) · 已知未盖/存疑 **1**(`_agg_credit_day_file__mutmut_9`) · 已知平台盲区 **0** · 本轮新出现 **0**。
  - **timeout 4(单列, 不并入 survived)**: `_agg_credit_hours__mutmut_3` / `_5` / `_14` / `_30`(while 循环界机械死循环族); W5 的 10 条盲区中 6 条本轮转 killed(`_agg_credit_hours_31` · `record_slots_8` · `hour_spans_3/5/14` · `agg_feed_39`)。
- **条目级红验(仅表面新增 2 条)**: `mutants.verify --ids-file` 在镜像 c32e8e03 跑全套件 `-n 8`; 基线既有失败 1 条(`tests/test_relocate_exec.py::test_spawn_args_pinned`, 与变异无关); 两条均 **SURVIVED**(4814 passed + 12 skipped), 未获 KILLED —— **不声称已杀**, 沿用 W5 等价出处。结果文件 `H:\Temp\auto-qb-mutants\s4-verify-mid1-new-ids.txt`(副本 `R:\Temp\auto-qb\mutants\`)。
- **结果文件备份**: `R:\Temp\auto-qb\mutants\mid-mid1.meta`(631,456 B) · `mid-mid1.log`(181,611 B) · `mem_mid1.log`(157,235 B)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `memory-bank/testing/baselines/26-11-02-2044-mutation-core-w5-traffic-sample-mid1.md` | 本切片 |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | R41 进度段(编号避让: R40 已被 W8 遗留两件占用) + Refs 反向声明 |
| `memory-bank/activeContext/26-10-08-0642-test-mutation-audit.md` | kb.wrap 追加本轮 R 行 |

**未改**: `src/` / `tests/` 零改动; `.wslconfig` 未改; `mutants` 工具链零改动; 未加 swap、未 shutdown。

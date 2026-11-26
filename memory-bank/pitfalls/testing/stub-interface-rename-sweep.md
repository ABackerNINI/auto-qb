# 改生产接口(改名/新增查询)未同步测试桩: 无护栏消费点直接炸

> 摘要: 给生产模块改名/新增公开查询时, 镜像该接口的手写测试桩(ui_harness 假桩/FakeClient/helpers)不会自动跟随 —— 桩缺方法在「替身缺位回落」护栏下静默, 在无护栏消费点直接炸; 改生产消费点必须 grep 测试桩同步面。
> 触发: 改名, 接口改名, 派生查询, 测试桩, 假桩, 替身漂移, ui_harness, FakeClient, helpers, 桩缺方法, 无护栏, boot-first, getattr 替身, 同步面, e2e 启动炸
**Refs:** memory-bank/tasks/26-11-21-backend-traffic-recovery.md

## 本篇只回答

改生产公开面(方法改名/搬家/新增派生查询/改签名)时, 怎么把「镜像该接口的手写替身」找全并同步 —— 与 `stubs-sim.md`(FakeConfig 新字段批炸、替身保真度)同族不同面: 那篇管「桩长得像不像」, 本篇管「桩跟没跟上接口改名」。

### 生产查询改名后假桩没跟上: 缺方法在无护栏消费点炸掉启动首轮

- **触发**: 对生产模块做接口改写(旧内部登记集改名/拆成命名派生查询、方法搬家、新增公开方法), 而仓内有手写替身镜像该模块的公开面 —— 实例: relocate 计划 S5-1(2026-11-20, bde75be0)把模块句柄改写为命名派生查询(`relocating_hashes()` 等), `scripts/ui_harness.py` 的 `_FakeRelocateJobs` 假桩只暴露 `jobs_snapshot()`, 期间无人补齐改名同步(其间 T5 156d817f 虽动过该假桩、追加 `foreign_notified_view()`, 也未补 `relocating_hashes()`)。
- **判别**: 桩缺方法有两条症状路: ①消费点有 getattr 缺位回落护栏 → 替身缺位静默当空集, 呈现面降级(可能假绿); ②消费点**无护栏直调** → 一旦新路径(如 boot-first e2e 走真 `_sync_line`)触到该消费点, AttributeError 直接炸启动首轮。本仓实例: 计划 26-11-21-1546 S4 让 e2e 冷启动走真同步线, 真 `grouping_mod._scan_triggered_groups` 调 `ctx.relocate.relocating_hashes()`(搬迁让路面, 无异常护栏), 桩缺该方法直接炸。
- **处置**: 改生产公开面时把「**grep 测试桩同步面**」写进改动清单动作列: 对旧名与新名各 grep 一遍 `scripts/ui_harness.py` + `tests/unit/helpers.py`(FakeClient/FakeConfig 等) + 其它手写替身, 逐个补齐镜像方法; 桩上新方法的语义选「与替身既有行为逐字保持」(本例 `relocating_hashes()` 恒空集 = S5 前桩缺登记集被当空集的既有行为), 不顺手加戏; 顺带评估该消费点是否该有缺位护栏(生产健壮性面另行裁决, 不混进桩同步)。
- **守阵**: 桩面无静态护栏可自动拦「改名未同步」(假桩是手写散件) —— 防线就是本条目的动作纪律; 既有先例同族: `stubs-sim.md` 的 FakeConfig 批炸(判别特征 `'FakeConfig' object has no attribute ...` 一片红)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

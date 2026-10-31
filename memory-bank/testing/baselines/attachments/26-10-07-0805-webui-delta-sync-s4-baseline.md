# 2720 —— WebUI rid 式增量同步实施计划 S4 关键步基线 (feat/webui-delta-sync, 前端 delta 合并落地)

> 摘要: 计划 [26-10-07-0414-plan-webui-delta-sync.html](../../plans/26-10-07-0414-plan-webui-delta-sync.html)
> S4 关键步: 前端消费 delta(单一合并入口 `applyStateRows`)落地后重立 test.full 基线,
> 对比 S0 基线(2705+4 / 36.40s / 99%)。
> 基线时间: 2026-10-07 08:05

**Refs:** memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html,
[26-10-07-0514-webui-delta-sync-s0-baseline.md](26-10-07-0514-webui-delta-sync-s0-baseline.md)

## test.full 实测

- 分支: feat/webui-delta-sync(本地分支, S4 不做 sync; 工作树含 S4 未提交改动时实测 ——
  前端 JS 与桩改动不进 pytest 计数, 与 S3 后树态同源)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2720 passed + 4 skipped, 0 failed, 40.11s, 覆盖率 TOTAL 99%**
  (16017 语句 / 167 未覆盖 / 5560 分支 / 147 partial; 门槛 98% 达标)
- 相对 S0 基线 [26-10-07-0514](26-10-07-0514-webui-delta-sync-s0-baseline.md)
  (2705 passed + 4 skipped @ 36.40s, 15863 语句 / 163 未覆盖 / 5496 分支 / 143 partial):
  passed **+15** / 未覆盖 +4 / 分支 +64 / partial +4 —— 增量全部来自 **S1-S3 三步的新增
  服务端代码与守阵测试**(S0 之后 S1/S2/S2补/S3 已各自入库, 本步 S4 为纯前端+冒烟桩改动,
  pytest 侧零新增); 语句总数 15863 → **16017**(+154)在在账 ±200 摆动簇内。4 skipped 为
  Windows 侧 POSIX 专属存量, 与在账一致。
- e2e 轨(同轮实测, pytest 之外): `commands run dev.e2e` 全量 **90 passed / 10 skipped /
  0 failed(4.0m)** —— 含本步新增 e2e/delta-sync.spec.mjs 6 条(双皮肤 × 3 场景);
  单跑该 spec 6 passed(15.0s)。

## S4 步改动面(对照判据的"该段改动")

- `src/auto_qb/webui/static/shared/polling.js`: 新增单一合并入口 `applyStateRows(payload)`
  (full=整表替换原样 / delta=行级 upsert+removed 剔除, 未脏行引用原样保留, 数组新实例赋回);
  refresh() 请求恒带 `delta=1`(P-05 默认开, 不加配置键)。
- `scripts/ui_harness.py`(仅冒烟桩保真): `_publish_with_delta` —— 桩直改状态后按生产口径
  喂 `store.delta_fields`/`view_changed` 并走 `flush_views(force=True)`(原 rebuild_views 推不出
  脏行, 前端 delta=1 后真值轮恒空桶); 起盘补建 `store.member_to_key`(直写 groups 绕过了
  归组路径, 组桶推不出且 singles 防御检查整代转 full)。
- `e2e/delta-sync.spec.mjs`(新增): 增量轮冒烟 —— 真实暂停手势触发 full=false 轮且渲染正确 +
  未脏行引用恒等 / applyStateRows 行级语义直测(upsert 替换·追加 + removed 剔除 + 数组新实例
  + lastRid 置空走 full) / 分组视图整组暂停组桶。

## 对照判据(S5-S10 逐段沿用)

- 以本切片(2720+4 / 16017 / 167 / 5560 / 147)为 S4 后对照点: 预期 passed 只升不降、
  未覆盖 / partial 不升; 回退先查该段改动。
- e2e 对照点: dev.e2e 全量 90 passed / 10 skipped / 0 failed; delta-sync.spec 6 条。
- 量级收益(前端赋值/传输段)以 S10 真机分档实测对照 S0 切片「before」段。

# 3184 —— 种子状态 A 系 S2 deferral (own_writes + TTL 兜底 + D-1/D-2/D-3 三闸门)

> 摘要: A 系实施计划 (plans/26-10-13-0540) 的 **S2 deferral 层**落地 —— 收回「陈旧-放行 ⇒ 脏数据洗白」窗口。新增 `TorrentStore.own_writes`(hash → 登记时刻, 纯内存不落盘) + `note_own_write`/`own_write_pending`(判据含**组维度**: 目标 hash 或其组任一成员命中即让位) + TTL 兜底 `_OWN_WRITE_TTL=10s`; QbApi 四入口 `start/stop/pause/resume` 在 raw client 调用成功后登记; 逐出单点 = `_apply` 应用到该 hash 新 `state` 时(另有种子删除/热重载两处清理)。三处闸门: **D-1** 队列级 `qbmanager._own_write_defer_gate` → `TaskQueue.run_due(defer_gate=)`(命中者以 `next_run=now` 重排下一 tick, 覆盖 task 线全体消费) / **D-2** `ops.skip_check` 执行路径(WEB 路径不经 task 线) / **D-3** `CheckAction.execute` 决策链入口(事件即时分派等非队列路径)。有界性双依据: 同步逐出(依赖 qB 前进) + TTL 兜底(不依赖外部条件)。全绿即基线。
> 基线时间: 2026-10-13 06:43

## 验收数字

- `test.full`: **3184 passed + 4 skipped** / `TOTAL 16778 159 5714 140 99%`.
- 耗时: **69.2s** (本机并行默认); `test.quick` 同绿 (3184 passed, 4 skipped).
- 较 S1 基线 (3176/16728/5692): 用例 **+8**(新增 S2 守阵), 语句 **+50**、分支 **+22**(deferral 三闸门 + 登记/逐出/TTL 的新代码量).
- Linux 侧未重测 (改动为纯 Python 值层/队列层与测试, 平台无关).

## 本波改动面

- **源**: `torrents/store.py` (`own_writes` 容器 + `note_own_write`/`own_write_pending`/`_evict_expired_own_writes` + TTL 常量; `_apply` 的 state 变化分支逐出; `remove_torrent`/`reset_runtime` 清理) · `core/qbapi.py` (四入口登记) · `core/taskqueue.py` (`run_due` 增 `defer_gate` 可选回调 + 命中者重入堆) · `core/qbmanager.py` (`_task_line` 传闸门 + `_own_write_defer_gate`) · `core/modules/ops_mod.py` (`skip_check` 入口 D-2 闸门) · `rules/actions/checking.py` (`CheckAction.execute` 入口 D-3 闸门).
- **测试**: `tests/test_taskqueue.py` (D-1 机制) · `tests/test_qbmanager.py` (D-1 判据) · `tests/test_sync.py` (逐出/TTL/组维度/不落盘) · `tests/test_ops.py` (D-2; 附 `wire_group` 注释同步) · `tests/test_checking.py` (D-3; 既有组串行用例补「同步回流逐出」一步).
- **文档**: `pitfalls/backend/concurrency.md` (新增「deferral 纪律」条目) · `testing/guards.md` (新增「种子状态 A 系批次」守阵表) · 任务档案 · activeContext 切片 · 计划件 · 基线切片 (本份) · `kb.index` 生成物重建.

## 已知偏差 / 移交

- **D-3 用 `skip` 而非 `pending`**(与计划字面的「返回 pending」有别): `pending` 需轮询子任务恢复 origin, 本闸无此驱动, 会把规则任务丢掉; task 线的「下一 tick 重排」由 D-1 队列级闸门承担, D-3 只补拦非队列路径。已在代码注释与计划 §12 变更记录写明。
- **D-2 落在 `skip_check` 执行路径而非 `_skip_gates_detail`**(与计划落点有别): `_skip_gates_detail` 同时服务只读预检 `skip_check_precheck`, 其 cls 契约(blocked/force)不引入第四类; 执行路径拦下即可, 预检照旧摊开闸门。
- **§8.3 余下守阵仍未落** (V1/V2 值域枚举、E1/E2 发射时机、I1 幂等) + 幂等可选件 A2 (`pending_writes`) —— 按计划归 **S3 收尾**; 本波只做 **S2 deferral 专属**的 D1/D2(S2 静态) 三条 + 两条机制/判据守阵.
- 数字差异看差值 `commands run kb.baseline -n 2` 现列.

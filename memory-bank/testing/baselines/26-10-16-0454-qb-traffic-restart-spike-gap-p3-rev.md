# 3406 passed + 4 skipped —— qB 流量图重启缝尖峰 P3 判据修订(per-key 语义修纯做种启动误报)

> 摘要: 用户「按推荐修复警告的问题」→ 修订 plan `26-10-15-0829` P3 的速率键新鲜度判据。根因: 原判据「两键同现才算新鲜」与 qB sync/maindata 增量轮**逐键 diff** 语义错配(仅值变化的键才出现在响应里), 纯做种时 dl_info_speed 恒 0(值不变)⇒ 增量轮该键永远缺席 ⇒ 每进程启动后第 3 个增量轮必误报一条(运行实例 26-10-15 22:50 / 26-10-16 01:25 / 01:30 三次重启各一条, 只读取证实锤); 且同专题已实锤「速率恒 0 而 alltime 在涨」是 payload 口径 vs 计数器口径的设计使然(报告 §04.5), 非陈旧。修订 = per-key 语义: 已收到过的键在增量轮缺席 = 值未变 = 合并旧值即当前值(不计); 仅「全量轮快照缺键」与「该键从未收到过」两类计无读数。阈值/节流/复位语义不变, 合并语义零改动。改动 2 源文件: `src/auto_qb/torrents/store.py` + `tests/test_sync.py`。
> 基线时间: 2026-10-16 04:54

**Refs:** memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html

## 验收数字

- test.full: 3406 passed + 4 skipped / TOTAL 17343 182 5846 158 99%; 耗时 130.5s(单次采样, 口径见 baseline.md)。
- 守阵红绿双验(突变判红后还原复绿): 丢全量快照判据(absent 谓词去掉 full 支)→ 2 红 / 丢从未收到判据(谓词收敛为仅 full)→ 2 红 / 退回旧行为(任一缺席即计)→ 2 红(两条误报回归守住); 还原后 `test.one -- tests/test_sync.py` 53 passed(46 既有 + 7 rate 键用例)。
- P3 判据支仍达成: 真正的无读数(全量快照缺键 / 从未收到)连续 3 轮仍告警一次并携带合并读数; 纯做种稳态(一键恒 0 长期缺席)与整包无 server_state(两键均未变)不再误报。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 未跑。
- Linux(WSL)侧未重测 —— 纯增量观测层无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/torrents/store.py`: `_track_rate_key_freshness(md, *, full)` 重写为 per-key 判据(reported/merged/absent 三个集合; 新增模块常量 `_RATE_KEYS`); 告警文案区分「全量快照缺键」与「从未上报」两类根因并保留合并读数; apply_sync 调用点传 full; 常量注释/类文档/apply_sync 文档同步改写(逐键 diff 语义 + 误报背景); 合并块注释修正「qB 每轮都带 server_state」的不准确表述(增量轮无变化时整键缺席)。
- `tests/test_sync.py`: rate 键用例 6 → 7 条(重写 5 + 新增全量快照缺键 1): 从未上报连续无读数恰一次告警 / 全量快照缺键告警且合并保留旧值 / 纯做种 dl 恒 0 长期缺席不告警(误报回归) / 已收键 + 增量轮整包缺 server_state 不告警(误报回归) / 恢复复位·新段再告警 / 常量冻结 / reset_sync 复位; 头部 docstring 测试清单同步。
- 滚动面: activeContext 切片(追加 R10) · 计划 doc P3 修订注记 + 变更记录(doc-updated 抬行) · tasks 档案进度日志 · kb.index 重建。

# 3363 passed + 4 skipped —— qB 流量图重启缝尖峰 P3 同步层速率键新鲜度实施轮

> 摘要: 用户「实施计划P3」(范围拍板: 只做做法①缺席告警, 计划 §07 #3; 做法②定期 rid=0 全量刷新不实施)→ 落地 plan `26-10-15-0829` 的 P3(同步层速率键新鲜度可观测)。改动面: `src/auto_qb/torrents/store.py`(apply_sync 合并时刻挂 `_track_rate_key_freshness`: server_state 速率键 dl_info_speed/up_info_speed 连续 3 轮未上报记 WARNING 一次(携带合并读数), 恢复上报复位, reset_sync 一并复位; **合并语义零改动**) + `tests/test_sync.py`(6 条 rate 键用例)。
> 基线时间: 2026-10-15 12:47

**Refs:** memory-bank/activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html

## 验收数字

- test.full: 3363 passed + 4 skipped / TOTAL 16915 153 5730 140 99%; 耗时 129.3s(单次采样, 口径见 baseline.md)。
- 对上一基线(P2, 3307+3)的 +56 passed +1 skipped 差值已对账: 102ed6c6(hr 波次第二批守阵, `test_hr_service.py` def test_ 133→184 = +51 条, 内含 1 条 skip)经 P2 提交(11:48)的内部同步 rebase 入树 —— P2 基线实测于其本地树、未含该批; 另 + 本轮 6 条(rate 键用例, `test.one -- tests/test_sync.py -k rate` = 6 passed 0 skipped)。本轮新增全部 passed。
- 守阵红绿双验(突变判红后还原复绿): 阈值失效(`< _RATE_FRESH_WARN_ROUNDS` → `< 1`)→ 3 红 / 节流失效(去 flag 判断)→ 1 红 / 恢复不复位(仅清 flag 不重置计数)→ 1 红; 还原后 `test.one -- tests/test_sync.py` 52 passed(46 既有 + 6 新增)。
- P3 判据①支达成: 「速率可能陈旧」日志可见(节流 = 恢复前一次, 携带缺席轮数与合并读数); 判据②支(「全量刷新不改变稳态行为」)随做法②未实施一并搁置, 见计划 P3 实施记录。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 未跑。
- Linux(WSL)侧未重测 —— 纯增量观测层无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/torrents/store.py`: 新增模块常量 `_RATE_FRESH_WARN_ROUNDS = 3` + 追踪状态 `_rate_absent_streak/_rate_stale_warned`(纯内存) + `_track_rate_key_freshness`(判据单位 = 键对, 两键齐报才算新鲜, 缺任一或整包缺 server_state 计缺席; 全量轮键集完整恒复位; 挂载点在 server_state 合并时刻之后、_apply 之前 —— 缺席只在合并时刻可观测, 早退轮也计数) + reset_sync 复位; 类文档/apply_sync 方法文档同步。store.py 自计划基线 8d089678 字节级零漂移(git diff 为空), 合并块现位于 :184-186(移位来自本轮自身新增代码)。
- `tests/test_sync.py`: 新增 6 条(缺席恰一次告警+携带读数 / 阈下不告警 / 恢复复位·新段再告警 / 整包缺 server_state 亦计缺席 / 常量冻结钉值 / reset_sync 复位); 头部 docstring 测试清单同步; 既有 server_state 用例逐字不动(合并语义零改动的既有基线)。
- 滚动面: activeContext 切片(追加 R6) · 计划 doc P3 实施记录(doc-updated 抬行) · plans/_index.md(kb.index 重建)。

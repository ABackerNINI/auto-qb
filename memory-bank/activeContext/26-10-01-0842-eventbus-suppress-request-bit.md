# eventbus-suppress-request-bit — issue 0750 认领修复(EventBus suppress 两字段拆分)

> 摘要: 用户指派认领 issues/26-10-01-0750(抑制窗内二次 L2 重建吞 queue_rebuilt → 全局任务丢失)。
> **已修完**: 红验先行坐实现象仍复现 → EventBus 拆请求位(`_replay_requested` + `request_suppression()`
> / `take_suppressed()` 消费)与 live 旗标(`_suppressed`, 仅 `_refresh_torrents` 两事件相位窗口内为 True),
> `rules_mod.rebuild_runtime` 改挂请求位; 连续重建的第二次 queue_rebuilt 恢复送达, 同窗内「未认领段
> 兜底重建」广播一并恢复。test.full 1895 passed + 3 skipped / 91%(基线 26-10-01-0838)。
> issue 已置 Done; 档案 [tasks/26-10-01-backend-eventbus-suppress-request-bit.md](../tasks/26-10-01-backend-eventbus-suppress-request-bit.md);
> 坑档 pitfalls/backend/suppress-request-vs-live-flag.md(一符两义教训)。
> **后续(同日)**: 审计报告(reports/26-10-01-0918)M1 已修 —— 请求位消费点从轮首移到 events_removed
> 相位前(take 即 arm), 失败轮不消费、抑制跨失败轮存活(原 _suppress_events 语义); 红验先行新回归
> test_suppression_request_survives_failed_round, test.full **1896 passed + 3 skipped / 91%**(基线
> 26-10-01-1643)。**M2 也已修(同日)**: `_rebuild_needed` 判据矩阵参数化守阵 11 例补进 test_modules_p5
> (五段级判据 + trackers 三元组逐成员/增删 + 运行时字段负例), 变异验证漏成员必红;
> test.full **1907 passed + 3 skipped / 91%**(基线 26-10-01-1752)。同轮按 scope-guard 例外 1(阻塞)补了
> 38604d07 的认领链缺口(1728 计划三目标 doc-refs 反向声明)。**待办**: ①未提交(等用户显式「提交」指令);
> ②相邻缺陷待定夺: arm→close 间抛异常卡 live 旗标, 下轮全相位被吞到 close 自愈(审计未列, 用户定夺
> 入池或另轮修)。
> 最后活动: 2026-10-01 17:52

# eventbus-suppress-request-bit — issue 0750 认领修复(EventBus suppress 两字段拆分)

> 摘要: 用户指派认领 issues/26-10-01-0750(抑制窗内二次 L2 重建吞 queue_rebuilt → 全局任务丢失)。
> **已修完**: 红验先行坐实现象仍复现 → EventBus 拆请求位(`_replay_requested` + `request_suppression()`
> / `take_suppressed()` 消费)与 live 旗标(`_suppressed`, 仅 `_refresh_torrents` 两事件相位窗口内为 True),
> `rules_mod.rebuild_runtime` 改挂请求位; 连续重建的第二次 queue_rebuilt 恢复送达, 同窗内「未认领段
> 兜底重建」广播一并恢复。test.full **1895 passed + 3 skipped / 91%**(基线 26-10-01-0838)。
> issue 已置 Done; 档案 [tasks/26-10-01-backend-eventbus-suppress-request-bit.md](../tasks/26-10-01-backend-eventbus-suppress-request-bit.md);
> 坑档 pitfalls/backend/suppress-request-vs-live-flag.md(一符两义教训)。
> **正在进行**: 无 —— 单轮收官。**待办**: 未提交(等用户显式「提交」指令)。
> 最后活动: 2026-10-01 08:42

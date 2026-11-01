# webui-add-torrents-sync-lag

> 摘要: 认领修复 issue 26-10-30-0626: 归因由「SSE 掉线/轮询」改为「qB add 是四跳异步管线 + 命令后补刷新太早(距 add 返回 0.5~0.8ms)」, 按候选 A 落地 store 有界追平(80ms × ≤3 次, TTL 3s) + 命令线登记回执 hash + 主循环提前同步线; 真机 N=6/N=12 零 1.5s 簇(24~129ms, 修复前 22%/44%), 全量测试见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-01 09:10
**Refs:** memory-bank/issues/26-10-30-0626-perf-webui-sse-down-poll-latency.html,memory-bank/testing/baselines/26-11-01-0910-webui-add-torrents-sync-lag.md

**R0(2026-11-01 09:10):** 认领修复 issue 26-10-30-0626: 归因由「SSE 掉线/轮询」改为「qB add 是四跳异步管线 + 命令后补刷新太早(距 add 返回 0.5~0.8ms)」, 按候选 A 落地 store 有界追平(80ms × ≤3 次, TTL 3s) + 命令线登记回执 hash + 主循环提前同步线; 真机 N=6/N=12 零 1.5s 簇(24~129ms, 修复前 22%/44%), 全量测试见 kb.baseline; issue 置 Done

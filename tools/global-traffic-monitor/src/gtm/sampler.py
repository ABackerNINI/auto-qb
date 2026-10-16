"""采样器: psutil 全适配器采样 + 当日累计 + 重置/恢复 (S0 骨架, 实现在 S1).

每 sample_interval (默认 5s) 读 psutil.net_io_counters(pernic=True), 按适配器
过滤 (默认排除 loopback 与 down, 可配 include/exclude 正则) 后全适配器合计
up/down。本次读数 < 上次读数 -> 判定计数器重置 (网卡重连/重启), delta 记 0 并
WARNING, 不产生负流量。按本地日界维护当日累计, 跨天 00:00 硬切写新行。

崩溃恢复: 启动读 state.json 恢复上次快照与当日累计; state 缺失/损坏时当日
累计从 dat 末行恢复 (若有), 计数器基线取当前值 (停机窗口丢流量, WARNING 说明)。
"""

# S0 骨架: 未实现。S1 落地采样循环与状态恢复。

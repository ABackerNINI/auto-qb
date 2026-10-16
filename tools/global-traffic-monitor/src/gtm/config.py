"""工具配置: 加载 / 校验 / 热重载 (S0 骨架, 实现在 S3).

配置主权: 工具自有 config.yml 置于工具数据目录; auto-qb WebUI 设置页经控制面
(PUT /config) 代理读写, last-writer-wins (多实例盲写风险由设置页「读后写」缓解)。

默认参数 (计划 §05): sample_interval=5s / flush=Δ>=1MiB 或 30s /
notify_threshold=100MiB / http=127.0.0.1:8099 / lease_ttl=180s / heartbeat=60s /
notify_timeout=3s / adapters 排除 loopback 与 down。全部可经 WebUI 设置页调整。
"""

# S0 骨架: 未实现。配置加载/校验 (黄金法则 4: fail-fast 全量校验并聚合报错)
# 与 PUT /config 热重载将在 S3 落地。

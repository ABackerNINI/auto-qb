"""控制面: 本地 HTTP 服务 (S0 骨架, 实现在 S3).

stdlib ThreadingHTTPServer, 强制绑定 127.0.0.1 (端口默认 8099, 可配; 占用即
fail-fast)。鉴权 Bearer token: 首次启动原子生成 monitor.token (临时文件 + 重命名),
比对用 compare_digest (照 auto-qb auth.py 模式)。

端点:
  GET  /status       采样状态、当日累计、末事件号、订阅者数、文件路径
  PUT  /config       全量校验 -> 原子写 config.yml -> 热重载 (last-writer-wins)
  POST /subscribe    {endpoint, token} 注册订阅 (租约 last_heartbeat + lease_ttl)
  POST /heartbeat    {id} 心跳续租 (订阅方每 60s)
  POST /unsubscribe  {id} 注销
"""

# S0 骨架: 未实现。S3 落地端点、鉴权与租约管理。

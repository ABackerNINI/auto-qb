# 组 key 随请求行走, h11 16KB 未完成事件上限间歇性拦掉组级命令

> 摘要: 组级路由把整组 key(base64url(组路径+全组文件相对路径))放进请求行; h11 缺省 16KB「未完成事件」上限在**头分片到达且停在未完成态**时判非法 —— 头一次性完整到达反而不触发, 所以症状间歇(大组「启动整组」时好时坏)。修法 = uvicorn.Config 显式放宽 `h11_max_incomplete_event_size`(lifecycle.py, 1MiB, 0.53.0 原生透传)。
> 等级: L0
> 触发: WEB 传输层,h11,请求行,组 key,Invalid HTTP request received,Receive buffer too long,MUST_CLOSE,uvicorn,启动整组,间歇性 400
**Refs:** memory-bank/testing/baselines/26-10-21-0435-webui-h11-request-line-cap.md

### 大组「启动整组/暂停/删除」时好时坏, WEBUI 日志刷 Invalid HTTP request received + asyncio ERROR

- **触发**: WEBUI 组级命令(`/api/groups/{key}/resume|pause|reannounce|delete` 与 `/api/traffic/qb/group/{key}`): 组 key = `encode_group_key`(组路径+全组文件相对路径)随请求行走, 大组(整季上千文件、中文长路径)的 base64url 请求行超 16KB。
- **判别**: uvicorn 记 `WARNING: Invalid HTTP request received.`(h11 实抛 `RemoteProtocolError("Receive buffer too long", error_status_hint=431)`, 判据在 h11/_connection.py next_event 的 NEED_DATA 分支); 浏览器收到裸 400, **请求到不了 FastAPI**(路由/鉴权日志无该请求); 同一笔请求的残留分片还会撞出 send_400 路径的 MUST_CLOSE 竞态(asyncio ERROR + `LocalProtocolError: can't handle event type Response when role=SERVER and state=MUST_CLOSE` traceback)。关键特征是**间歇**: 头一次性完整到达时不触发(不超单次读尺寸就能解析), 跨多次读且头未完即超限才拦 —— 用单发完整请求复现不了就误判成「没问题」。
- **处置**: `lifecycle.py` 的 uvicorn.Config 显式传 `h11_max_incomplete_event_size=H11_MAX_INCOMPLETE_EVENT_SIZE`(1MiB)—— uvicorn ≥0.53 原生透传给 h11.Connection; 已落 2026-10-21。上游 `send_400_response` 对 MUST_CLOSE 无防护是另一层潜在噪音(任意客户端垃圾数据+竞态才触发), 未在本轮处理。
- **守阵**: `tests/test_web_auth.py::test_start_web_server_config_raises_h11_incomplete_event_cap`(装配断言) + `test_oversized_request_line_reaches_app_not_transport_400`(真实 uvicorn 下头分两片送、首片 17KB 未完, 必须打到应用层)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

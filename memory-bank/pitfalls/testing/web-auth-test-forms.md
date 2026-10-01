# WebUI 鉴权测试的缺省形态陷阱

> 摘要: TestClient 缺省 Host=testserver / client=testclient 都不是本机形态, 跨站闸(Host 白名单)开启后必 403; loopback 免鉴权分支**先于** token 校验 —— skip 开启时 loopback 对端连错密钥也 200。
> 触发: 改 webui 鉴权, 写鉴权测试, skip_local_verify, Host 白名单, 跨站, 403, 错密钥 200, TestClient, client 参数

### TestClient 缺省形态不是 loopback, 跨站闸下必被拒

- **触发**: 写/改 `webui/server/auth.py` 鉴权相关测试(2026-10-02, issue 26-09-21-1408 跨站闸落地时)。
- **判别**: starlette TestClient 缺省 `Host: testserver`、`client=("testclient", ...)` —— 前者不在 Host 白名单(loopback 变体 + 自配 web.host), 后者非 loopback 免鉴权不生效。skip_local_verify 开启时用缺省形态打请求, 无凭证请求拿到的是跨站闸 403 而不是预期的 200/401; 显式传 `headers={"Host": "127.0.0.1:8080"}` 即可(httpx 透传显式 Host, 缺省才从 base_url 推)。
- **处置**: 鉴权测试一律显式 `TestClient(app, client=("127.0.0.1", 50000))` + 显式 Host 头; 断言「远端仍要鉴权」时同样带合法 Host 头(白名单不看对端地址, 只看头)。

### loopback 免鉴权是短路放行, 错密钥也 200

- **触发**: 断言「错密钥 → 401」时未分对端地址(2026-10-02 实测撞红)。
- **判别**: `require_token` 的 skip_local_verify 分支在 token 校验**之前** return —— 开关开启且对端是 loopback 时, 无凭证/错凭证都直接放行(设计如此: 免鉴权模式下前端不发 Authorization 头)。这不是 bug; 「错密钥 401」只对**非 loopback** 对端成立。
- **处置**: 凭证类断言按对端分流 —— loopback 对端断言放行语义, 远端 client(如 `("192.168.1.50", 50000)`)才断言 401/200; 跨站闸与免鉴权分支的先后关系见 auth.py 闸门注释。

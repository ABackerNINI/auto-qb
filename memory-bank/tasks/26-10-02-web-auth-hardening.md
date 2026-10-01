# 26-10-02-web-auth-hardening — WebUI 鉴权面加固(CSRF/Host + 三小件)

**Status:** In Progress
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Summary:** 清偿 issue 清偿路线图 W1 波 3/3(收官): A) skip_local_verify 开启时补跨站防护 —— Host 白名单(废 DNS rebinding)+ 写方法 Origin 同源校验(废 CSRF), 全部写端点经全局依赖单点覆盖, 默认关闭路径零变化; B) 三小件 —— SSE 换一次性票据(?ticket= 取代 ?token= 长期密钥进查询串) / /api/config/public 限 loopback / uvicorn 显式 proxy_headers=False。

**Topics:** web-auth-hardening
**Refs:** memory-bank/issues/26-09-21-1408-bug-web-skip-local-verify-csrf.html, memory-bank/issues/26-09-21-1408-bug-web-auth-hardening-minors.html

## 原始请求

用户授权 issue 清偿路线图 W1 波(后端速赢)实施, 本档案承担第 3/3 阶段(收官段), 同批认领两条 issue(路线图明确「三个小件合并一次加固, 与上一条同批做」):

- [26-09-21-1408-bug-web-skip-local-verify-csrf](../issues/26-09-21-1408-bug-web-skip-local-verify-csrf.html)(P2): `web.skip_local_verify=true` 时全文件无 Origin/Host 校验, 本机任意网页可跨站(CSRF)驱动删除/暂停/限速等写命令, 且存在 DNS rebinding 面。
- [26-09-21-1408-bug-web-auth-hardening-minors](../issues/26-09-21-1408-bug-web-auth-hardening-minors.html)(低危三件): SSE token 走查询串(ticket 化或 fetch 流消费) / /api/config/public 暴露面限 loopback / uvicorn 显式 proxy_headers=False。

安全纪律: skip_local_verify 关闭(默认)路径行为零变化; 校验失败 403 明确拒绝; 两条 issue 各自单独提交(A 先 B 后)。

## 思考过程与决策

- 落点核对(web.py 拆分后): 鉴权单点 `src/auto_qb/webui/server/auth.py`(factory 全局 dependencies), SSE 端点 `server/routes/events.py`, config/public 处理器 `server/routes/config.py`, uvicorn 装配 `server/lifecycle.py`(start_web_server -> _QuietLoopConfig)。
- **A 的威胁模型与闸门位置**: CSRF 与 DNS rebinding 的共同前提是**请求不携带凭证**(浏览器跨站伪造不了 Authorization/查询串凭证), 故防护只对「无任何凭证」的请求生效 —— 携带任意凭证(Authorization 头 / ?token= / ?ticket=)的请求绕过跨站闸、交由既有 token 逻辑裁决(持密 = 可信方)。闸门放在 require_token 最前(config/public 早退与非 /api 早退之前), 天然覆盖全部 /api 与静态路径。
- **写动作判定按方法不按路由清单**: POST/PUT/DELETE/PATCH 交由全局依赖单点守, 新写端点自动进覆盖面(路由清单写测试时穷举断言)。
- **Host 白名单** = loopback 变体(localhost / 127.0.0.1 / ::1 / ::ffff:127.0.0.1)+ 用户自配 web.host(合法变体放行; 解析用 urlsplit 处理 [::1]:port 与 host:port 形态); **Origin 校验** = 写方法上 Origin 非空时必须是 http(s) 且 host 在白名单且(可判定时)端口与 Host 头一致 —— 浏览器控制 Origin, 攻击页无法伪造成白名单 host。
- **B-① SSE 选 ticket 化**(issue 给的两方向里选改动面小的): 前端 fetch 能带 Authorization 头 -> POST /api/events/ticket 换**一次性 30s 票据** -> EventSource 以 ?ticket= 连接; ?token= 查询串兜底**删除**(长期密钥不再可能进反代日志)。票据存 WebUIRuntime(锁保护、单次消费、上限 64 防堆积); EventSource 自动重连带的旧票必失效 -> 前端 onerror 关连接 3s 后换新票重开(轮询兜底语义不变)。
- **B-②** config/public 加 Request 参数, 非 loopback 403: 该标志只对本机浏览器有用(免鉴权本就只对 loopback 生效), 前端读取失败自然回落密钥表单, 无需前端改动。
- **B-③** uvicorn.Config 显式 proxy_headers=False: 项目直连监听, 不信任 XFF/Forwarded —— 防「本机反代 + XFF 伪造」把 request.client.host 骗成 loopback 造成免鉴权误判。
- 既有测试适配(语义变化所致, 非放松): test_skip_local_verify_loopback_bypass / test_config_public_endpoint_no_auth 需显式指定 loopback client 与 Host 头(TestClient 默认 Host=testserver、client=testclient, 真实请求必带合法 Host); _GOLDEN_ROUTES 增 POST /api/events/ticket(67->68)。
- 与 A 的同批耦合: B-① 的 ?ticket= 计入 A 的「携带凭证」判据 —— 分两笔提交时 B 笔内补齐。

## 实现计划

1. A: `server/auth.py` —— require_token 前置跨站闸(_reject_cross_site: Host 白名单全路径 + 写方法 Origin 同源), 仅 skip_local_verify 开启且无凭证时生效; 403 明确拒绝 + WARNING 留痕。
2. A 测试: 合法 Host/Origin 变体放行 / 跨站 Origin 拒绝 / rebinding Host 拒绝(静态+API)/ 默认关闭零变化 / 携带凭证绕过闸 / 全部写路由穷举 403(迭代 _iter_api_routes); 同步 test_web.py 头部测试计划。
3. B-①: `runtime.py` 票据存储(issue/consume, 单次+TTL+上限); `routes/events.py` POST /api/events/ticket; auth.py 删 ?token= 兜底改 ?ticket= 单点; `static/shared/polling.js` 换票 + 重连续票; _GOLDEN_ROUTES 登记。
4. B-②: `routes/config.py` config/public 限 loopback。B-③: `lifecycle.py` proxy_headers=False。
5. B 测试: 票据签发/单次消费/过期 / require_token 收 ?ticket= 且 ?token= 移除 / config-public 非 loopback 403 / proxy_headers=False 装配断言 / 前端接线静态守阵。
6. 收尾: 两条 issue 翻 Done(封面徽标 + meta + 状态变更日志 + 修复后补充) -> kb.index -> activeContext 切片 -> test.full 基线切片 -> A/B 各一笔 ship.commit。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| A 代码 | auth.py 跨站闸(Host 白名单 + 写方法 Origin) | 待办 |
| A 守阵 | 放行/拒绝/默认零变化/写路由穷举 | 待办 |
| B 代码 | SSE 票据 / config-public 限 loopback / proxy_headers=False | 待办 |
| B 守阵 | 票据三态 / token= 移除 / 403 / 装配断言 | 待办 |
| 收尾回写 | 双 issue Done / kb.index / activeContext / 基线切片 | 待办 |
| 提交 | A、B 各一笔 ship.commit 推 Gitee | 待办 |

## 进度日志

- **2026-10-02 开工**: sync 至 1c237504(带上阶段 1/2 的 bc24631b、54db09f2); 摸清拆分后落点(见思考过程); 双 issue 认领建档(本文件), issue 头部补 doc-refs 双向登记; Status In Progress。

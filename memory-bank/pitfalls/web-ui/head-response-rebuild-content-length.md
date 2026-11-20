# 响应层收齐 body_iterator 重建 Response 会把 HEAD 空体重建成 Content-Length: 0

> 摘要: 响应层收齐 body_iterator 重建 Response 会把 HEAD 空体重建成 Content-Length: 0
> 触发: HEAD, Content-Length, body_iterator, Response 重建, 中间件, 缓存分流, no-cache, 空体

## 本篇只回答

按「触发动作」记一类坑: 为替换 HTML `__AQB_V__` 版本令牌（仅 text/html）而在响应层收齐 body_iterator 重建 Response 的中间件, 对 HEAD 请求会把空体重建成 `Content-Length: 0`, 破坏 HEAD 应回显 GET 等效长度语义; 给出判别与处置口径(计划 plans/26-11-20-0727 P2-b)。

### 收齐 body 重建 Response 时 HEAD 被压成 Content-Length: 0

- **触发**: 中间件为替换 HTML `__AQB_V__` 令牌（且仅 `text/html`）而 `async for chunk in response.body_iterator` 收齐 body, 再 `Response(content=b"".join(chunks), headers=..., status_code=...)` 重建响应; 对 HEAD 请求同样收齐（收时为空）而未短路。
- **判别**: HEAD 请求(缓存协商或探针)返回 `content-length: 0`, 而同 URL 的 GET 返回真实文件长度; 浏览器或代理据此认为资源空, 出现误判或缓存异常; 单测只覆盖 GET 时不报错, 只有显式 HEAD 断言才暴露。
- **处置**: 中间件入口对 `request.method == "HEAD"` 提前原样 `return response`(不收 body、不重建), 保持 HEAD 回显 GET 等效 Content-Length。重建路径仅用于 GET 及其他有体方法; 补单测对同 URL 的 GET 与 HEAD 断言 `content-length` 一致, 并确认 HEAD 的 Content-Length 与 GET 等效、缓存头按分流口径照常设置。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

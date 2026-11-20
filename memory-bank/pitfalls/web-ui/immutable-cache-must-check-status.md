# 缓存分流只判 v 匹配 + 非 HTML 不判 status: 带当前 v 的 307/404 被 immutable 缓存一年

> 摘要: 缓存分流只判 v 匹配 + 非 HTML 不判 status: 带当前 v 的 307/404 被 immutable 缓存一年
> 触发: immutable, Cache-Control, max-age=31536000, 缓存分流, v 匹配, 307, 404, 重定向, 皮肤书签, 3xx, 4xx, 5xx

## 本篇只回答

按「触发动作」记一类坑: 给静态响应加 immutable 长缓存时只判「v 匹配 + 非 HTML」而漏判 HTTP status, 导致带当前 v 的重定向/错误响应也被缓存一年; 给出判别与处置口径(计划 plans/26-11-20-0727 P2-b)。

### 只按 v 与非 HTML 分流, 带当前 v 的 307/404 被 immutable 缓存一年

- **触发**: 在响应层(static_ui.py 缓存中间件)按「请求带 v 且 v == 当前静态树版本 V + 响应非 HTML」就发 `Cache-Control: public, max-age=31536000, immutable`, 判断漏掉响应状态码。典型触发路径: `/` 与 `/newui` 的 UI cookie 裁决 307 重定向、静态资源缺失 404、服务端 5xx、任何 3xx —— 它们都会带页面 head 注入的 `?v=V`。
- **判别**: 换皮肤(改 cookie 或书签指向)后旧书签仍跳旧 UI(307 被浏览器一年不复核); 请求一个不存在的带 v 静态路径拿到 404 后, 即使文件补回仍长期 404; DevTools Network 见 307/404 响应头 `cache-control: public, max-age=31536000, immutable`, 后续请求直接 from disk cache 零网络往返。
- **处置**: immutable 仅对 `200 <= status < 300` 的静态响应发放; 3xx/4xx/5xx 一律维持 `no-cache`。把判据合成单一谓词: `v 匹配 && 非 HTML && status 是 2xx && 非 /api` → immutable, 否则 no-cache。据此改中间件缓存分流, 并补单测覆盖「带当前 v 的 307/404/500 → no-cache」与「带当前 v 的 200 静态 → immutable」两组; HTML 永不进 immutable(保每次下发新 V), 裸路径/无 v/过期 v 仍 no-cache。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

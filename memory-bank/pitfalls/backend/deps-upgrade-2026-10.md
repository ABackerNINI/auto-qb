# fastapi 0.x 升级后 body: dict 注解把 JSON null 拦成 422

> 摘要: fastapi 0.x 升级后 body: dict 注解把 JSON null 拦成 422
> 触发: fastapi 升级, 0.x minor, body dict, 422, 400 契约, Optional, pydantic 校验, notify, 签名
**Refs:** memory-bank/issues/26-10-31-0830-chore-webui-fastapi-uvicorn-upgrade.html

### fastapi 0.x 升级后 `body: dict` 注解把 JSON null 体在校验层拦成 422, 走不到 handler 的 400 闸

- **触发**: 升级 fastapi(0.141.1 → 0.162.0, 实测 2026-10-31, 随 pydantic 2.14.2)后, 端点签名写 `body: dict = None` 时, 客户端发 JSON `null`(或无体)不再放行 `None` 到 handler —— 老版只有数组/标量体被拦成 422, `null` 会到 handler。
- **判别**: 原本「handler 里对非法体回 400 + 自定义 detail」的用例突然拿到 **422**(fastapi 校验层 detail), 且只有 `null`/无体这一路变了, 数组/标量体依旧 422。
- **处置**: 若 400 是对外契约(调用方按状态码分派), 把签名改成 `body: dict | None = None` 放行 `null` 到 handler 的类型闸(参照 `routes/traffic_monitor.py` 的 `api_tm_notify`, 签名旁 docstring 注记了缘由); 若 400 只是实现细节, 则改测试与文档接受 422 —— 二选一以「对外契约是否承诺过 400」为准。
- **守阵**: `tests/test_web_traffic_monitor.py::test_notify_rejects_non_dict_body`(断言 null 体 400 + detail「JSON 对象」, 升级时它先红)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

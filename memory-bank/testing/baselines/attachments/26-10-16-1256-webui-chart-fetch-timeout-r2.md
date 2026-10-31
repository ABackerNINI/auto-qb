# 3423 passed + 4 skipped —— 前端请求级超时 + 流量图轮询悬挂兜底(issue 26-10-16-0954 收口)

> 摘要: 承本专题 `26-10-16-1226` 切片(当时 #2 已落 / #1 待人工应用)。本轮 = **#1 由用户手工应用**(15s 请求级超时: `AbortController` + 外部 signal 链接 + `AbortError` 翻译 + `finally` 清定时器; 落点 `auth.js` 文件头常量 + `_request` 内) + 新增 **#1 守阵**(静态四锚 + node 六型电池) + 红绿双验(三类突变对**副本**注入 —— 真文件写入被工作区「凭据字面量」判据整文件级拦下, 副本逐字节同源于磁盘, 验完删除并比对真文件未触碰)。全量两采样皆绿, 方案 #3(连续失败给用户提示)有意不做(既有错误空态已承担该面)。
> 基线时间: 2026-10-16 12:56
> 档案: memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md

- test.full: 3423 passed + 4 skipped / TOTAL 17196 语句 185 未覆盖 5860 分支 160 partial / 98%(闸门过)。耗时 **144.8s / 147.4s**(本片两次采样, 区间 144–148s; 口径见 baseline.md)。
- 本轮新增 #1 守阵 1 条(`test_frontend_api_request_timeout`): 静态四锚(常量单点 + 秒→毫秒派生 / `signal` 透传 / 裸 fetch 不得回潮 / AbortError 翻译 / `clearTimeout` + 跨文件不变式 `_QB_LOAD_STALL_MS >= AQB_FETCH_TIMEOUT_MS`) + node 六型电池(悬挂→「请求超时(15s)」+ `timeout` 标记 + 定时器已清 / 成功值透传且定时器清 / 401 仍走 auth 分支 / 非 2xx 文案照旧 / 已 abort 的外部 signal →「请求已取消」不冒充超时 / 非 abort 网络错误原样上抛)。
- 红绿双验(3 类突变, 逐类判红; 驱动 scratch `.openclaw/tmp/red_green_auth_timeout.py`, 未入库): ①裸 fetch(去掉 signal) ⇒ 静态层判红 + 电池层**无输出**(悬挂路径把探针的 await 挂住 —— 该失败形态已写进守阵的空输出断言); ②AbortError 翻译判空 ⇒ 静态层 + 电池 3 项; ③`finally` 空(不清定时器) ⇒ 静态层 + 电池 2 项。对照组(未突变副本)两层全绿; 副本删除后与磁盘逐字节比对一致。
- ⚠ 判据层面(环境事实): 本轮**无法就地突变真文件** —— `auth.js` 的写入被工作区「凭据字面量」判据整文件级拦下(误判命中既有行), 故红绿双验走副本路径; 已记 `pitfalls/ops/agent-write-guard-secret-false-positive.md`。
- 仍未处置(范围守恒): 两条**裸 fetch 旁路** —— `commands.js` 的导出下载与 `shortcuts.js` 的 `/api/keys` 读写绕过 `_request`, 同样没有超时; 是否入池待用户拍板。
- Linux 侧未跑 —— 改动为前端静态件与其守阵, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/static/shared/auth.js`(用户手工应用): 文件头常量 `AQB_FETCH_TIMEOUT_S = 15` / `AQB_FETCH_TIMEOUT_MS = AQB_FETCH_TIMEOUT_S * 1000`; `_request` 内 `AbortController` + 15s 定时器 + 外部 signal 链接(已 aborted 立即转发) + `signal: ctl.signal` 透传 + `AbortError` 翻译(超时/取消分型 + `timeout` 标记) + `finally` `clearTimeout(timer)`。
- `tests/test_webui_static_dom_panel.py`: 新增 `test_frontend_api_request_timeout` 与探针 `_NODE_API_TIMEOUT_PROBE` + 头部测试计划一行。
- `memory-bank/`: issue `26-10-16-0954-bug-webui-chart-fetch-no-timeout` 置 `Done`(实际修法 / 验证方式 / 测试数字); 档案收口 + `**Refs:**` 反向声明;**两条新坑档** —— `pitfalls/web-ui/inflight-flag-no-timeout.md`(在用标志 + 无超时请求的链式卡死)与 `pitfalls/ops/agent-write-guard-secret-false-positive.md`; activeContext 切片更新(`26-10-16-1214`, R2 段)。

**Refs:** memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md

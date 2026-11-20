# 26-11-20-webui-boot-static-fingerprint — WebUI 静态资源并发化 + 查询参数指纹长缓存（计划 26-11-20-0727 两期落地）

**Status:** In Progress
**Added:** 2026-11-20
**Updated:** 2026-11-20
**Summary:** WebUI 首屏静态资源两期根治落地: P1 boot.js 分片/脚本并发化 + P2 静态树哈希 V 与 ?v= 指纹长缓存 immutable 分流, 四皮肤共用; 真机验收按拍板剥离待用户做
**Topics:** webui-boot-static-fingerprint
**Refs:** memory-bank/plans/26-11-20-0727-plan-webui-boot-first-data.html, memory-bank/issues/26-11-20-0553-perf-webui-boot-serial-asset-chain.html, memory-bank/issues/26-11-20-0726-question-webui-build-toolchain.html, memory-bank/testing/baselines/26-11-20-0940-webui-boot-static-fingerprint.md

## 本篇只回答

WebUI 重启后首屏静态资源链路（分片/脚本串行 + 每次 ETag 重验）的两期根治落地到哪、真机验收为何未做；11-18 的「重启后首份数据」旧 Done 档案（同为 webui-boot-first-data 专题，后端首轮发布）不在本篇范围。

## 原始请求

1. 实施计划 `memory-bank/plans/26-11-20-0727-plan-webui-boot-first-data.html`（doc-status Open）：按 grilling 三轮 8 问拍板 D1-D8 分两期落地 —— P1 静态资源并发化，P2 查询参数指纹 + 长缓存（P2-a 版本源/HTML 令牌/响应层，P2-b boot.js 装载器/缓存分流）。
2. 范围裁定：真机验收（P1-3 真机复测 ≤3s / P2-4 框架可见 ≤1.5s）按用户拍板剥离，本轮子代理只做代码 + 自动化测试，真机待用户在有 qB/浏览器环境做。

## 思考过程与决策

- **P1 (204f69df, 2026-11-20)**: `shared/boot.js` 分片改 `Promise.all` 并发 fetch + index 归位拼接（每片独立 10s AbortController）；脚本改 `link rel=preload as=script` 并发预取 + 全部成功后按清单序批量插入 `async=false`；fail-fast/保序/四皮肤共用不变量不变。落点仅 boot.js 一处，四套皮肤共用。
- **P2-a (072f2734, 2026-11-20)**: 新 `src/auto_qb/webui/server/static_version.py` 启动算 static/ 树内容哈希 V（白名单 .js/.html/.css/.png，长度前缀 + 排序，sha256 前 16 位），挂载时算一次缓存；四套 index.html head 静态资源加 `?v=__AQB_V__` + 注入 `window.AQB_V`；`static_ui.py` 响应层把 token 换成 V（只 HTML、分块收齐、重建 Response、HEAD 提前 return）。
- **P2-b (c5cee5f0, 2026-11-20)**: boot.js 新增 `withV()` 单点给分片 fetch / preload href / script src 三处统一追加 `?v=V`（已有 query 用 `&v=`，window.AQB_V 缺失优雅退化）；中间件缓存分流 = 仅「v==当前版本 + 非 HTML + 2xx」发 `public,max-age=31536000,immutable`，裸/无 v/过期 v/3xx/4xx/5xx/HTML 维持 no-cache，/api 不受本中间件影响（保持原样，非 no-cache）（升级后旧 v 落 no-cache + HTML 永 no-cache 保新 V 下发）。
- **评审与验收口径**: 分批评审每批 2 轮零 actionable；自动化测试（test.quick）全绿，数字只进基线切片，由主会话在 test.full 后统一建；真机验收按用户拍板剥离，交付说明如实标注，不声称已做。

## 实现计划

计划单点: `memory-bank/plans/26-11-20-0727-plan-webui-boot-first-data.html`（Open）。
- P1: 分片 `Promise.all` 并发 + 脚本 preload 并发预取/按序批量插入，保序、fail-fast、四皮肤共用不变量不变。
- P2-a: 启动算 static/ 树哈希 V + 四套 HTML 令牌替换 + 响应层换 token。
- P2-b: boot.js `withV()` 三处统一追加 `?v=` + 中间件按 v/status 分流 immutable/no-cache。
- 守阵: test.quick 全绿（数字只进基线切片）；真机轨剥离待用户做。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P1 | 分片 Promise.all 并发 + 脚本 preload 并发预取/按序批量插入（204f69df） | Done(2026-11-20) |
| P2-a | static_version.py 静态树哈希 V + 四套 HTML 令牌 + 响应层换 token（072f2734） | Done(2026-11-20) |
| P2-b | boot.js withV() 三处追加 ?v= + 中间件 v/status 分流 immutable（c5cee5f0） | Done(2026-11-20) |
| P1-3 真机 | 真机复测 ≤3s（四皮肤 + 210 种子 harness） | 未做（用户拍板剥离: 本轮子代理只做代码+自动化测试, 待用户在有 qB/浏览器环境做） |
| P2-4 真机 | 真机框架可见 ≤1.5s（外部 Playwright 探针） | 未做（同上, 用户拍板剥离） |

## 进度日志

### R0 · 立档 (2026-11-20)

- P1 并发化落地 (204f69df): 分片 Promise.all + index 归位拼接，脚本 preload 并发预取 + 全成功后按序批量插入，保序/fail-fast/四皮肤共用不变量不变；test.quick 全绿（数字只进基线切片）。
- P2-a 指纹源落地 (072f2734): static_version.py 启动算 static/ 树哈希 V（白名单 + 长度前缀 + 排序 + sha256 前 16 位），四套 HTML head `?v=__AQB_V__` + window.AQB_V，static_ui.py 只 HTML 分块收齐换 token（HEAD 提前 return）；test.quick 全绿（数字只进基线切片）。
- P2-b 装载与分流落地 (c5cee5f0): boot.js withV() 三处统一追加 ?v=V（已有 query 用 &v=，缺失优雅退化），中间件仅「v 匹配 + 非 HTML + 2xx」发 immutable，其余(含 HTML)维持 no-cache，/api 不受影响（非 no-cache）；test.quick 全绿（数字只进基线切片）。

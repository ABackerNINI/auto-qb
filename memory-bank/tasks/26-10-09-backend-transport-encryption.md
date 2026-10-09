# 26-10-09-backend-transport-encryption — 本地通道传输安全调研(WebUI + HR 取数通道)

**Status:** Open
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** 用户命题「WebUI⇄auto-qb 与 auto-qb⇄扩展两条通道均为明文 HTTP, 有安全风险; 初步设想用 token 加密数据、两端解密; 要求调研成熟方案、对比成本优劣、写详细报告」。产出可行性报告 `reports/26-10-09-1529-report-transport-encryption-feasibility.html`(威胁模型分层 T0-T4 + 五方案对比 + 分阶段落地路径)。**核心结论**: ①默认回环形态下明文残余风险有限(T0 同用户进程本就可读 token 文件, 传输加密无解), 加密边际收益小; ②通道一旦暴露到 LAN/跨机, 唯一正确且省事的答案是 **TLS(本地受信 CA / 反代 / VPN)**, 而非自研应用层加密; ③用户设想的「token 加密载荷」在回环下技术成立(回环是安全上下文, `crypto.subtle` 可用), 但**跨机 LAN 的 `http://<私网IP>` 页面不是安全上下文 ⇒ Web Crypto 不可用**, 恰在最需要它的场景失效; ④最该先做的是「暴露即提示/收口」而非默认上加密。**本轮零 `src/`/`tests/` 改动**; 落地需另立计划。
**Refs:** memory-bank/reports/26-10-09-1529-report-transport-encryption-feasibility.html, memory-bank/activeContext/26-10-09-1529-transport-encryption.md
**Topics:** transport-encryption

## 原始请求

用户: 「当前 webui 与 autoqb 的数据传输使用的是 http, 是明文, autoqb 与扩展数据传输也是明文, 有安全风险, 初步设想: auto-qb 使用 token 对数据加密, webui 收到数据后解密, 浏览器扩展同理。调研成熟的解决方案, 对比各方案成本优劣等, 写一个详细的报告」。

## 思考过程与决策

- **先落威胁模型再谈方案**: 「有安全风险」不落到具体攻击者位置就无从取舍。按位置分 T0(同机同用户进程)/T1(同机异用户)/T2(LAN 被动嗅探)/T3(LAN 主动中间人)/T4(恶意网页 CSRF/rebinding)。结论: T0 传输加密无解(令牌文件同用户可读), T4 已有防护, 加密的正当理由只有 **T2/T3 在通道暴露后**。
- **报告而非计划**: 用户要的是「调研 + 对比 + 报告」, 属可行性分析 ⇒ `reports/`(出厂即冻结), 落地方案另立计划。
- **对用户设想的正面评估(方案 D)**: 具体化为 `key=HKDF(token)` + `AES-256-GCM` + 随机 nonce。技术上回环下成立, 但**安全上下文约束是死穴** —— 跨机 LAN 页面非安全上下文 ⇒ Web Crypto 不可用, 要绕开就得引前端密码库(等于自研协议)。故 D 只作「扩展跨机 + 拒绝装 CA」的受限兜底, 不作主方案。
- **推荐次序「先收口后加密」**: 阶段 0 维持明文回环 + 写清风险; 阶段 1「暴露即提示」闸门(高性价比); 阶段 2 一键本地 CA(TLS); 阶段 3 跨机复用 CA + 远程走 VPN/SSH 隧道。
- **与既有 issue 串联**: 报告是 `issues/26-10-09-0855`(HR 通道锁死回环)第 3 条「传输安全需拍板」的输入 ⇒ 建立双向 `doc-refs` 认领链(专题 `hr-channel-remote` ↔ 本报告 `transport-encryption` 分属两专题, 靠 refs 串联)。
- **未写代码**: 报告边界 = 调研与对比; 落地涉及新增 `cryptography`/`trustme` 依赖与 `web.tls.*` 配置键(须进 `validate_config` + `config/schema`), 属另一轮。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 摸清两条通道实现(鉴权/载荷/监听) + 外部方案调研(MDN/Chrome/mkcert/Caddy/Tailscale) | Done |
| S1 | 出报告 `reports/26-10-09-1529-report-transport-encryption-feasibility.html` | Done |
| S2 | 认领链: 与 issue `26-10-09-0855` 双向 `doc-refs` | Done |
| S3 | 收尾: 本档案 + activeContext 切片 + 基线切片 + `kb.index` + `kb.check` + `test.full` | Done |
| S4 | (待拍板)立项「暴露即加密闸门 + 一键本地 CA」计划 | Open |
| S5 | (待拍板)HR 通道跨机传输安全随 `hr-channel-remote` 专题推进 | Open |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| S0 现状与外部调研 | Done | 代码锚点见报告 §14; 外部来源 2026-10-09 核对 |
| S1 报告 | Done | 14 节单文件 HTML, dark 主题, `doc-topic=transport-encryption` |
| S2 认领链 | Done | report ↔ issue 双向 refs |
| S3 收尾 | Done | 切片 + 基线 + 索引 + 闸门全绿 |
| S4 落地立项 | Open | 待用户拍板; 涉新依赖与新配置键 |
| S5 跨机形态 | Open | 与 issue `26-10-09-0855` 合并推进 |

## 进度日志

### 2026-10-09 R0 — 建立(调研 + 报告)

- **会话开工**: `my-commit-flow.sync` 已同步 `de0c4fa6`(从 `9926953b` 快进)。
- **现状核实(两条通道)**:
  - WebUI: FastAPI + uvicorn, 默认 `127.0.0.1:8080`, 明文 HTTP, `Authorization: Bearer <web.token>` + `compare_digest`, SSE 走一次性票据; 前端 token 存 `localStorage.autoqb_token`。
  - HR 端点: `ThreadingHTTPServer` 仅监听 `127.0.0.1:8788`, 明文 HTTP, `X-Hr-Token` + origin 白名单 + 任务 URL 白名单 + 任务绑定; 扩展侧 `normalize.js` 把协议硬编码 `http`。
- **外部调研要点(2026-10-09 核对)**: MDN 安全上下文(`127.0.0.0/8`/`::1`/`localhost`/`*.localhost` 属 potentially trustworthy; `http://<私网IP>` 不属); Chrome 142(官方 2025-09-29 公告)推 Local Network Access 权限; mkcert 本地受信 CA; Caddy 内部 CA; Tailscale/WireGuard/SSH 隧道。
- **报告产出**: `reports/26-10-09-1529-report-transport-encryption-feasibility.html`(14 节: 问题与口径 / 结论速览 / 现状盘点 / 威胁模型 / 方案总览 / B HTTPS+本地 CA / C 反代 / D 应用层 AEAD 深评 / E VPN 隧道 / 安全上下文与 LNA / 对比矩阵 / 落地路径 / 与本仓约定衔接 / 附录)。
- **收尾实测**: `commands run test.full` → **2850 passed + 4 skipped, 覆盖率 99%**(与上基线 26-10-09-1522 逐位持平, 本轮零 `src/`、零 `tests/` 改动); `kb.index`(20 生成物) / `kb.check`(主键 / 认领链 / 回写 / 日期全过) 全绿。基线切片 [26-10-09-1529](../testing/baselines/26-10-09-1529-transport-encryption.md)。
- **待跟踪变量**(写入报告 §14): ①Chrome LNA 对扩展(<code>chrome-extension://</code>)是否豁免官方未明确, 需 Chrome 142+ 实测; ②LNA 对「公网域名反代访问 WebUI」的影响。

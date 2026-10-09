# 本地通道传输安全调研(WebUI + HR 取数通道)

> 摘要: 用户命题「WebUI⇄auto-qb 与 auto-qb⇄扩展两条通道均为明文 HTTP, 有安全风险; 设想用 token 加密载荷; 要求调研成熟方案并对比成本优劣」。产出可行性报告 `reports/26-10-09-1529-report-transport-encryption-feasibility.html`(含威胁模型分层 T0-T4 / 五方案对比 / 落地路径)。**核心结论**: ①默认回环形态下明文残余风险有限(T0 同用户进程本就可读 token 文件, 传输加密无解), 加密边际收益小; ②通道一旦暴露到 LAN/跨机, 唯一正确且省事的答案是 **TLS(本地受信 CA / 反代 / VPN)**, 而非自研应用层加密; ③用户设想的「token 加密载荷」在回环下技术成立(回环是安全上下文, `crypto.subtle` 可用), 但**跨机 LAN 的 `http://<私网IP>` 页面不是安全上下文 ⇒ Web Crypto 不可用**, 恰在最需要它的场景失效; ④最该先做的是「暴露即提示/收口」而非默认上加密。**未写任何代码**; 落地需另立计划(随 `hr-channel-remote` 专题)。
> 最后活动: 2026-10-09 15:29

## 状态

- 已完成: 报告产出并入库(`reports/_index.md` 重建); 与 issue `26-10-09-0855`(HR 通道锁死回环)建立双向 `doc-refs` 认领链。
- 未做: 无代码改动; 未拍板落地方案。
- 下一步(待用户拍板): 是否立项「阶段 1 暴露即加密闸门 + 阶段 2 一键本地 CA」; 阶段 2 涉及新增 `cryptography`/`trustme` 依赖与 `web.tls.*` 配置键(须进 `validate_config` + `config/schema`)。

**Refs:** memory-bank/reports/26-10-09-1529-report-transport-encryption-feasibility.html,memory-bank/testing/baselines/26-10-09-1529-transport-encryption.md,memory-bank/tasks/26-10-09-backend-transport-encryption.md

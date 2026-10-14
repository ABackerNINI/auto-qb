# 26-10-14-1241-hr-channel-portless-remote — 联合实施计划已出(去端口+跨机), 待开工

> 摘要: 用户指令「出一个联合实施分步计划, 包括去端口与跨机, 安全方面暂时使用 HTTP(大部分情况局域网), 非局域网用户自行反代」。本轮为纯文档轮(未改任何代码)。产出: 联合实施计划 `memory-bank/plans/26-10-14-1241-plan-hr-channel-portless-remote.html`(Open · 已拍板待开工); 原跨机计划 26-10-09-0856 转 Superseded 并互挂 doc-refs; issue 26-10-09-0855 的 doc-refs 挂上新计划(认领链, 状态仍 Open, S0 开工时才抬 In Progress)。
> 最后活动: 2026-10-14 12:41
> 状态: Open(计划已拍板待开工; S0–S7 分步在计划 §04)

## 用户拍板(计划 §01 拍板回执)

- **安全传输 = HTTP(T1 受信 LAN + token)唯一实现形态**; T2(端点自签 TLS)不实现; T3(反代终止 TLS)不实现, 仅文档给出配置路径, 非局域网用户自行反代。
- **路线 = A**(发现端口 + 随机数据端口 + token 自动分发)叠加跨机路径 C; 路线 B(native messaging)缓行不并入。

## 派生口径(计划 §01, 实施不再重复讨论)

- `port` 默认 0(随机); 显式非零 = 完全旧行为; `discovery_port` 默认 18788(用户现产端口转正), 0 = 关闭发现。
- `pairing: auto|on|off` 默认 auto: host 非回环强制配对(发现端点免 token, 是 LAN 上的 token 分发器, 需人工关口); 同机默认关。校验: 非回环 + pairing=off + 空 token ⇒ 报错。
- 扩展主机判据 = 回环 ∪ 私网段; https scheme 保留不折(反代用户); 0.0.0.0 允许+警示; 多 PC 文档推荐打包扩展。
- advertise 覆盖键不做(隧道/反代用户保持显式端口 = 旧行为)。

## 关键实施事实(本轮新取证 @ de83fbe8)

- **fault-domain 计划(26-10-09-0821)已 Done**: 401/403 节流(REJECT_WARN_GAP)、被拒接触面、WebUI 活跃信号均已落地 ⇒ 联合计划 S5 只做 C2/C3 文档翻转, 不重做机制。
- `HrChannelServer.__init__` 已收 `host` 形参(没人传); `_LoopbackServer` 的 `allow_reuse_address=False` + 免 FQDN 绑定口径须逐字保留。
- 用户 config.yml 显式 `port: 18788` ⇒ 升级后与 discovery_port 默认 18788 **撞车, 启动即报错**(S1 校验给指引; §08.2 有具体迁移两步)。
- 扩展 manifest 无 `key` 字段 ⇒ 未打包安装的扩展 id 随路径变化 ⇒ 跨机多 PC 钉单 extension_id 会挡第二台(R8; 文档推荐打包或留空 id)。
- 扩展测试 harness 是 node **实跑** normalize.js/background.js(非静态检查)⇒ discovery.js 新纯模块可入同一 harness。
- 发现端点免 token 的两道关: Origin 钉死 + 配对码(仅非回环); 配对 secret 落 `<data_dir>/hr.pairing`(0600), 展示码 6 位跨重启稳定, 凭证 = HMAC 派生(无额外状态), 删文件即吊销。

## 计划骨架(S0–S7)

S0 开工准备(立任务档案 + 基线 + issue 抬 In Progress + 行号复核) → S1 配置面(host/port:0/discovery_port/pairing + 五条校验) → S2 端点接线 + 发现服务(新模块 hr/discovery.py: InstanceRegistry + HrDiscoveryServer + 配对门) → S3 配对码机制 → S4 扩展侧(normalize 放开 + discovery.js 纯模块 + options 发现区 + background 触发器) → S5 观测衔接(C2/C3 文档) → S6 测试 → S7 文档收尾。

## 下一步 / 移交

- 待用户指令开工: S0 先行(立档 `tasks/26-10-14-hr-channel-portless-remote.md` + test.full 基线 + issue 抬 In Progress)。
- 闸门状态: `kb.docmap --check` 绿(670 文档/321 专题, 认领链闭环); `kb.index` 已重建(21 生成物); 两份计划 HTML 标签配平。
- 本轮纯文档轮: 未改代码、未跑测试基线、无 pitfalls 入池。1110/1135 两份报告为冻结快照不回头改, 决策权威在联合计划 §01。

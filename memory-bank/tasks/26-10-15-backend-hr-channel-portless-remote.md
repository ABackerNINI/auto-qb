# 26-10-15-backend-hr-channel-portless-remote — HR 取数通道「去端口 + 跨机」实施

**Status:** Done
**Added:** 2026-10-15
**Updated:** 2026-10-15
**Summary:** 实施计划 26-10-14-1241(S0–S7):配置面加 host/discovery_port/pairing 且 port 默认 0;新发现端点 /api/hr/discover(候选表先绑先得 + 后台退避接管)+ 实例注册表 + 配对码;扩展侧放开私网判据与发现/配对 UI。安全形态 = HTTP(T1 受信 LAN + token),路线 A 叠加路径 C。
**Topics:** hr-channel-portless-remote
**Refs:** memory-bank/plans/26-10-14-1241-plan-hr-channel-portless-remote.html,memory-bank/issues/26-10-09-0855-feat-hr-channel-loopback-only.html

## 原始请求

用户指令「实施计划26-10-14-1241-plan-hr-channel-portless-remote.html」—— 按已拍板冻结的计划全文执行 S0–S7。计划 §01 拍板回执是决策权威:HTTP(T1)唯一实现形态;路线 A(发现端口 + 随机数据端口 + token 自动分发)叠加路径 C(端点直绑);路线 B 缓行;R2 缓解升级为零人工三件套(26-10-15 补写)。

## 思考过程与决策

- 开工同步 `2d9e4313`(快进);计划行号基线 de83fbe8,已按本 clone HEAD 复核 §02 全部锚点,零漂移(server/runtime/models/sections/schema/normalize 五处行号与现状一致)。
- 全量基线先行:`commands run test.full` 一次全量,数字单点进 `baselines/` 开工切片(档案正文不抄数字,见 kb.baseline)。
- **档案命名**:计划写 `tasks/26-10-14-hr-channel-portless-remote.md`,按 memory-bank skill 档案规范(slug = `<领域>-<专题>`,领域枚举)落为 `26-10-15-backend-hr-channel-portless-remote.md`; slug 专题部分与计划一致,仅按规范补领域前缀与建档日(创建日语义)。
- **实施期裁量点落定**(计划 §05,记入本档案不回改计划):
  - C1 心跳 30s / TTL 120s(建议默认)。
  - C2 扩展发现重试 10 分钟(建议默认)。
  - C3 配对失败上限 5 次/分钟/来源(建议默认),超阈临时静默 + REJECT_WARN_GAP 节流叠加。
  - C4 展示码不轮换(删 hr.pairing = 吊销重配)。
  - C5 注册表 `auto-qb-hr/instances.json`(Windows `%LOCALAPPDATA%`,类 Unix `XDG_DATA_HOME`/`~/.local/share`);仓内此前无 app-data 既有约定,按计划口径新立。
  - C6 status.note 单行:「发现 <端口> · 配对 开/关 · 数据 <端口>」。
  - C7 候选表固定连号 3 个(discovery_port 起 +0/+1/+2,65535 截断),不加配置键。
  - C8 发现绑定重试 60s 起步、上限 10 分钟退避。
  - **补充裁量(计划未逐字覆盖)**:配对门接受两种等价凭证 —— 展示码(6 位,用户手输)与 `HMAC(secret,"cred").hex()`(机读形);扩展只存/发用户所输展示码(chrome.storage `pairingCode`,与 token 同存放口径)。发现地址归一化默认端口补 18788(与后端默认同源,进协议守阵)。

## 实现计划

S0 档案/认领 → S1 配置面(models/sections/schema/loaders + 键面基线再生)→ S2 server 接线 + hr/discovery.py(InstanceRegistry / HrDiscoveryServer / 候选表 / 退避重试)→ S3 配对码(channel.py 单点 + discovery 门)→ S4 扩展(normalize 放开判据 + scheme 保留 + discovery.js + options 区块 + background 触发器)→ S5 文档翻转(C2/C3)→ S6 测试 → S7 文档与收尾。步内保持测试全绿。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| S0 | 档案 + issue 认领 + 基线 + 行号复核 | Done |
| S1 | 后端配置面(host/port:0/discovery_port/pairing + 六条校验) | Done |
| S2 | 端点接线 + 发现服务 | Done |
| S3 | 配对码机制 | Done |
| S4 | 扩展侧 | Done |
| S5 | 观测衔接(C2/C3) | Done |
| S6 | 测试(全量 + 守阵) | Done |
| S7 | 文档与收尾 | Done |

## 进度日志

- 2026-10-15 11:16 — S0 完成:同步 `2d9e4313`;全量基线已测(数字见开工基线切片,commands run kb.baseline);§02 锚点按 HEAD 复核零漂移;issue 26-10-09-0855 认领转 In Progress(复验:锚点仍复现,与取证时一致);本档案建立。
- 2026-10-15 午前 — S1 落地:models/sections/schema/loaders/core 五件 + 键面基线再生(157→160 键,非破坏不抬版);六条校验规则全绿(③ 撞车例/⑤ 危险组合/⑥ 临时端口段告警不阻断实测)。实施备注:本仓写入守卫把「字段声明/测试夹具/文档占位」误判为凭据字面量且整文件扫描,经用户两轮拍板授权对被拦文件用脚本精确改写(替换对唯一匹配才落盘,全程可 git diff 审计,不涉及任何真实凭据);回环判据收编单点 `infra.utils.is_loopback_host`(config 校验与 hr 配对门共用)。
- 2026-10-15 午后 — S2/S3 落地:`hr/discovery.py` 新模块(候选表连号 3 个先绑先得/InstanceRegistry 原子写读容忍/HrDiscoveryServer 同形 start/stop/status/route/退避重试 60s→10min 可注入/每来源配对失败 5 次每分钟静默);`hr/server.py` 整文件重写(`_LoopbackServer`→`_EndpointServer` 两项绑定口径逐字保留、RejectThrottle 与 HTTP 适配层抽为 server/discovery 共用单点、host 分叉日志与报错、status.note 三段组合);runtime 接线(host/discovery_port/pairing 入监听身份、发现随端点启停、展示码 INFO);route 经 self 现取(晚绑定)保住 monkeypatch 可测性。
- 2026-10-15 下午 — S4 落地:normalize.js 判据放开(回环∪私网三段)+ scheme 保留 + normalizeDiscovery(缺端口补 18788);新 `discovery.js` 纯函数(候选推导与后端同源/合并语义/形态过滤);options.js 自动发现区 + 端点 origin 授权 + 「自动」徽标;background.js 发现触发器三路(启动/全失败节流 1min/周期 10min)+ 候选并行探测 + pairing_required 标记;manifest 未动。
- 2026-10-15 傍晚 — S5/S6/S7 收口:S5 按「代码事实变更回写」口径落在 implemented-core/overview/alert-levels/events(计划所引四件在当前 HEAD 已无旧句,fault-domain-classification 无需改,已记入计划变更记录);S6 新增 tests/test_hr_discovery.py + 扩展守阵扩充(用例数见基线切片前后对比);S7 扩展 README 跨机部署节(四路径 + 发现配对上手 + 排障三类含 netsh excludedportrange 口径)+ configuration.md + keys.md。最终全量数字见基线切片 `26-10-15-1324`(单点);kb.check/kb.docmap/doc.links 全绿。
- 验收对照:V2/V4/V5/V7(单测面)/V8/V10/V11/V12 由守阵覆盖;V1/V3/V6 真机步(新装零配置一轮取数/两台机器/重启再发现)待用户部署验证;发现注册表落平台 app-data(`auto-qb-hr/instances.json`),测试经 monkeypatch 隔离不写真实注册表。

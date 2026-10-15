# 26-10-16-0001-hr-ext-connect-selfheal — 计划 S0–S6 全部落地(连接自愈 + 手动优先 + 不静默 收口)

> 摘要: 用户实报 HR 扩展「立即发现」报 `发现未命中(未知)`、「保存发现地址与配对码」后「自测端点连通」却说 `先在 1. 存入一个实例端点再自测`。用户追问「后端改端口/重启后端口被占, 岂不还得手动操作且可能静默失败」把问题重定为**连接模型**: 数据端口重启即变、发现结果被当一次性缓存(死端点永久堆积)、后台发现结果进不了选项页(静默)、无常驻可见信号。经 grilling 11 问收敛(含用户更正"手动条目 = 高优先级而非兜底"), 立计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html`(连接自愈 + 手动优先 + 不静默), 仅动扩展侧。**S0–S6 全部落地**: S1/S2(合并语义翻转 + 失败即发现 + 徽标四态 + 结构化快照 + 健康台账)、S3/S4(选项页隐式保存/自动接自测/中文映射/实时刷新/失效标记/顶部总览 + 布局合并为一个「连接后端」区)、S5(README 口径翻「优先」+ 自愈/徽标说明)、S6(5 条新守阵 + **跨层机械比对**收口徽标态与总览态同源)。计划转 Done。细节单点在计划与档案 `tasks/26-10-16-webui-hr-ext-connect-selfheal.md`。
> 最后活动: 2026-10-16 01:13
> 状态: Done(计划 Done; S0–S6 全部落地)

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md

## 本轮落点(细节单点在档案与计划, 此处只留入口)

- 计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html`(**Done**, 10 节: 拍板回执 Q1–Q11 / 现状锚点 13 处 / 目标形态(模型+伪码+徽标四态) / S1–S6 / 裁量点 C1–C8 / 验收 V1–V8 / 风险 / 迁移 / 同步清单)。
- 档案 `tasks/26-10-16-webui-hr-ext-connect-selfheal.md`(S0–S6 全 Done; 进度日志与遗留项单点在档案)。
- 核心语义翻转: 发现 = 自愈/自动补充通道; **手动条目 = 高优先级**(置顶 + 主实例 + 不可覆盖删除); 发现集 = 租约(整批替换, **空集不替换**); 失败即发现(60s 节流) + 周期 2min; 徽标四态 + 顶部连接状态总览; 手动失效只提示不代删。
- S1/S2 落点(代码事实): `extensions/hr-fetch-proxy/discovery.js`(`isManualEntry` + `mergeInstances` 翻转)与 `background.js`(`maybeDiscover(failCount)` 任一失败即触发 / `DISCOVERY_EVERY_MINUTES = 2` / `noteDiscoveryResult` 落 `lastDiscovery` / `badgeStateOf` + `refreshBadge` + `chrome.action.onClicked` / `instanceHealth` 台账按轮落盘)。
- S3/S4 落点(代码事实): `options.js`(`discoverNow` 重写为隐式保存闭环, 授权是手势内第一个 await / `probeMainInstance` 单一判据供自测与发现后共用 / `DISCOVERY_REASON_TEXT` + `candidateSummary` 逐候选 / `refreshConnFromStorage(syncJson)` + `scheduleConnRender` / `connStateOf` + `renderConnOverview` 顶部总览 / `STALE_FAIL_STREAK=3` 失效标记)与 `options.html`(合并为「① 连接后端」一区 + `<details id="manualEndpoints">` 折叠手动区 + 徽标图例; 删 `discSave`); 守阵在 `tests/test_extension_proxy.py`(S1/S2 六条 + S3/S4 只更新既有接线用例的期望)。
- **S5/S6 落点(本轮)**: `extensions/hr-fetch-proxy/README.md`(布局块改「① 连接后端」单区 + 手动端点口径翻「优先」+ 新增「连接自愈 + 不静默」段(徽标四态 / 失败即发现 + 2min 周期 / 逐候选结果) + 排障表与「怎么确认它在工作」补徽标与总览; 连带修三处随 S4 失效的引用)与 `tests/test_extension_proxy.py`(5 条新守阵: 合并语义两条 / reason 中文映射与 `未知` 字面量 / `storage.onChanged` 监听连接面 / **跨层机械比对** `connStateOf` vs `badgeStateOf` 逐输入一致 + 四态键集同源 + 徽标图例同源)。
- 机械比对缺口**已收口**(S6): `options.js::connStateOf` 与 `background.js::badgeStateOf` 由跨层守阵切出函数体真跑同一张真值表逐输入比对 —— 此后「徽标报警但页面说正常」这类漂移有机械拦阻。
- 现场不一致(范围外, 待用户对齐): 仓库 `config.yml` 的 `port: 18788` 与发现默认端口 18788 相撞, 而运行日志显示数据端口 7031 ⇒ 仓库这份与线上不一致。

## 下一步 / 移交

- 计划 S0–S6 全部落地, 计划转 Done; 收尾 DoD 已完成(档案/切片/基线/索引)。
- 待用户: ① 现场真机验收(V1 端口变化零操作自愈 / V4 不静默三处一致 / V6 一次点击闭环 —— 计划 §06 判据为真机观察, 本机无法兑现); ② 对齐现场 `config.yml` 的 `channel.port`(0 还是显式值)。
- 闸门状态: test.full 全绿(数字见 `commands run kb.baseline` 最新切片, +5 差值已在切片内对账); kb.check / kb.docmap --check / doc.links 全绿; kb.index 已重建。

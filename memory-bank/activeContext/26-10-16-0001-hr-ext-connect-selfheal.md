# 26-10-16-0001-hr-ext-connect-selfheal — 计划立档 + S1/S2 实施(自愈与可见性已落地)

> 摘要: 用户实报 HR 扩展「立即发现」报 `发现未命中(未知)`、「保存发现地址与配对码」后「自测端点连通」却说 `先在 1. 存入一个实例端点再自测`。用户追问「后端改端口/重启后端口被占, 岂不还得手动操作且可能静默失败」把问题重定为**连接模型**: 数据端口重启即变、发现结果被当一次性缓存(死端点永久堆积)、后台发现结果进不了选项页(静默)、无常驻可见信号。经 grilling 11 问收敛(含用户更正"手动条目 = 高优先级而非兜底"), 立计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html`(连接自愈 + 手动优先 + 不静默), 仅动扩展侧。用户指令「实施计划S1-2」后, **S1/S2 已落地**(合并语义翻转 + 失败即发现 + 徽标四态 + 结构化快照 + 健康台账); S3–S6(选项页交互/布局、两份 README 口径、守阵收口)未实施。细节单点在计划与档案 `tasks/26-10-16-webui-hr-ext-connect-selfheal.md`。
> 最后活动: 2026-10-16 00:28
> 状态: Open(计划 Open; S1/S2 已实施, S3–S6 待指令)

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md

## 本轮落点(细节单点在档案与计划, 此处只留入口)

- 计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html`(Open, 10 节: 拍板回执 Q1–Q11 / 现状锚点 13 处 / 目标形态(模型+伪码+徽标四态) / S1–S6 / 裁量点 C1–C8 / 验收 V1–V8 / 风险 / 迁移 / 同步清单)。
- 档案 `tasks/26-10-16-webui-hr-ext-connect-selfheal.md`(S0–S2 Done, S3–S6 Open)。
- 核心语义翻转: 发现 = 自愈/自动补充通道; **手动条目 = 高优先级**(置顶 + 主实例 + 不可覆盖删除); 发现集 = 租约(整批替换, **空集不替换**); 失败即发现(60s 节流) + 周期 2min; 徽标四态 + 顶部连接状态总览; 手动失效只提示不代删。
- S1/S2 落点(代码事实): `extensions/hr-fetch-proxy/discovery.js`(`isManualEntry` + `mergeInstances` 翻转)与 `background.js`(`maybeDiscover(failCount)` 任一失败即触发 / `DISCOVERY_EVERY_MINUTES = 2` / `noteDiscoveryResult` 落 `lastDiscovery` / `badgeStateOf` + `refreshBadge` + `chrome.action.onClicked` / `instanceHealth` 台账按轮落盘), 守阵在 `tests/test_extension_proxy.py`(新增 6 条 + 既有合并断言翻转)。徽标文案走 ASCII(计划 §3.3 的 `✓/…` 是示意, code-style 禁图形符号)。
- **未收口的口径**(S3–S6 才动, 属计划内顺序而非遗漏): 选项页仍是旧布局与旧文案 —— `options.html:122`「手动端点(兜底…)」、`README.md:71`「② 手动端点(兜底)」、`options.js` 的「保存发现地址与配对码」按钮与 `(未知)` 失败码直出、实例列表不监听 `instances`、失败码无中文映射。**后台已按新语义跑, 选项页还按旧口径显示** —— 下一轮 S3/S4 必须成对改。
- 现场不一致(范围外, 待用户对齐): 仓库 `config.yml` 的 `port: 18788` 与发现默认端口 18788 相撞, 而运行日志显示数据端口 7031 ⇒ 仓库这份与线上不一致。

## 下一步 / 移交

- 待用户: ① 下指令启动 S3–S6(建议按 S3→S4 成对做, 否则页面文案与后台语义不一致); ② 对齐现场 `config.yml` 的 `channel.port`(0 还是显式值)。
- 闸门状态: test.full 全绿(数字见 `commands run kb.baseline` 最新切片); kb.check / kb.docmap --check / doc.links 全绿; kb.index 已重建。

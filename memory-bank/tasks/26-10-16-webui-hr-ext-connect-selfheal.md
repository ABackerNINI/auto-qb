# 26-10-16-webui-hr-ext-connect-selfheal — HR 扩展连接自愈与手动优先(计划立档)

**Status:** Open(S1/S2 已实施, S3–S6 待指令)
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户实报 HR 扩展「立即发现」报 `发现未命中(未知)`、「保存发现地址与配对码」后「自测端点连通」却说 `先在 1. 存入一个实例端点再自测`。经 grilling 11 问收敛, 根因是连接模型而非文案: 数据端口重启即变、发现结果被当一次性缓存(死端点永久堆积)、后台发现结果进不了选项页(静默)、无常驻可见信号。立计划 `plans/26-10-15-2357`(连接自愈 + 手动优先 + 不静默), 仅动扩展侧, 不碰后端与发现协议。
**Topics:** hr-ext-connect-selfheal
**Refs:** memory-bank/plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html,memory-bank/activeContext/26-10-16-0001-hr-ext-connect-selfheal.md

## 原始请求

用户指令(2026-10-15 23:40): 「目前的HR扩展点击『立即发现』有时显示『发现未命中(未知)』, 点击『保存发现地址与配对码』显示『发现地址已保存 … 点「立即发现」试一轮』, 但是『自测端点连通』显示『先在 1. 存入一个实例端点再自测…』, 操作逻辑混乱, 需要重新梳理优化, 使用 grilling 技能, 写一个修改计划」—— 附后端启动日志(数据端点 7031、发现端点实绑 18788)。

中途用户提出关键质疑(2026-10-15 23:46): 「如果后端更改了端口, 或者重启后端口被占用, 岂不是还得手动操作? 且可能静默失败!」—— 把问题从"按钮文案"重定为"连接是否自愈、是否可见"。

## 思考过程与决策

- **grilling 三轮, 11 问全部收敛**(决策权威 = 计划 §01 拍板回执):
  - 首轮 Q1–Q7: 范围=仅扩展侧; 目标心智模型=合并为一个"连接后端"区; 「立即发现」隐式保存当前输入; 发现成功后自动接一次自测; 失败码→中文+逐候选结果; 实例列表实时化; 空态指路改写。
  - 用户更正 Q1: **手动条目是高优先级的用户显式指定, 不是"兜底"** —— 与现有 `discovery.js::mergeInstances`(同端点被发现的覆盖)直接冲突。
  - 次轮 Q8–Q11: 同端点冲突**手动整条胜**; 高优先级作用面=顺序置顶+主实例+不可覆盖删除+轮询先试; 手动失效**只提示不代删**; 呈现措辞整体翻成"优先"而视觉顺序保持"自动发现在前"。
- **现状核实(锚点)**: `discovery.js:61–91`(合并只增不减 + 同端点被发现覆盖)、`background.js:30`(周期 10min)、`background.js:449–463`(`failCount>=total` 才触发 ⇒ "1 死 1 活"不自愈)、`background.js:469–507`(发现结果不落结构化快照)、`options.js:209`(失败码直接外泄 `未知`)、`options.js:731–735`(`storage.onChanged` 不监听 `instances`)、`options.js:247/553`(陈旧步骤号 "1.")、`manifest.json:29–31`(有 `action` 键但全库无 `chrome.action.setBadgeText`)。
- **实施期裁量点(计划 §05, 不回改计划)**: C1 发现返回**空集不替换**(防后端重启瞬间自断连接 —— 空实例时连"失败即发现"都不触发, 只能等周期); C2 部分集照常整批替换; C3 手动失效标记阈值 ≥3 轮; C4 徽标"重连中"vs"发现失败"边界(有应答无可用实例=重连中; 候选全无应答=发现失败); C6 发现失败态自动展开手动区; C8 旧 `instances` 无 `source` 字段 ⇒ 判为手动 ⇒ 零迁移脚本获得"优先"语义。
- **现场不一致(记入计划 §02 警示框, 本专题范围外)**: 仓库 `config.yml` 显式 `port: 18788` 与发现默认端口 18788 相撞, 而用户贴的日志显示数据端口 7031、发现实绑 18788 ⇒ 实际运行的 `port` 不是 18788, 仓库这份与线上不一致; 实施前需与用户对齐。

## 实现计划

实施按计划 §04 分步推进(用户 2026-10-16 指令「实施计划S1-2」⇒ S1/S2 已落地, S3–S6 待指令):

S1 `discovery.js` 合并语义翻转(手动优先 + 发现集整批替换 + 空集不替换) → S2 `background.js`(失败即发现 + 周期 2min + 徽标四态 + 结构化 `lastDiscovery` + `instanceHealth` 台账) → S3 `options.js`(隐式保存 + 自动接自测 + 文案映射 + 实时刷新 + 空态指路 + 失效标记 + 顶部总览) → S4 `options.html`(布局合并为一个"连接后端"区 + 措辞翻"优先") → S5 `README.md` 口径同步 → S6 `tests/test_extension_proxy.py` 七条新守阵。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| S0 | grilling 收敛 + 计划落盘 + 认领链 + 收尾回写 | Done |
| S1 | discovery.js 合并语义翻转 | Done |
| S2 | background.js 自愈触发 + 徽标 + 台账 | Done |
| S3 | options.js 交互与文案 | Open |
| S4 | options.html 布局合并 | Open |
| S5 | README 口径同步 | Open |
| S6 | 守阵测试 | Open |

## 进度日志

- 2026-10-16 00:01 — S0 完成: 开工同步 `319555af`; grilling 三轮(Q1–Q11)收敛, 计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html` 落盘(10 节, Open); 认领链双向(计划 ↔ 上游计划 26-10-14-1241 ↔ 本档案 ↔ activeContext 切片); 全量闸门数字见 `commands run kb.baseline`(本轮无代码/测试改动, 与上一基线同树)。实施未启动 —— 待用户显式指令。
- 2026-10-16 00:05 — 新坑入档 `pitfalls/kb/doc-status-meta.md`: 计划首版 `doc-status` 写了 `Draft`(语义像状态但不在 5 词表) ⇒ `kb.index` **静默漏收**该件(仍报「已生成 21 个生成物」)、`kb.check`/`kb.docmap --check`/`doc.links` **全绿**, 只有 `test.full` 的 `test_status_vocabulary` 红; 改 `Open` 后重跑索引并 `grep` 确认已收录。
- 2026-10-16 00:28 — **S1 完成**(用户指令「实施计划S1-2」): 开工同步 `b17c671d`。`discovery.js::mergeInstances` 语义翻转 —— 手动条目(`source !== 'discovered'`, 新增纯函数 `isManualEntry`)**整条胜 + 恒在前 + 原样保留**(Q8/Q1), 发现条目按租约**整批替换**旧发现集(死端点自然剪除, Q2), **空集不替换**(C1, 防后端重启瞬间自断连接); 缺 endpoint/token 的半条仍不收。既有守阵 `test_discovery_helpers_behave` 的合并断言随计划翻转(旧语义「同端点被发现覆盖 + 只增不减」被本计划废止, 属口径演进非守阵松动), 并把 `isManualEntry` 加进「禁本地副本」名单。验证: node 直跑 discovery.js 四组用例(手动胜含 token 保留 / 整批替换剪死端点 / 空集保留旧集 / 顺序稳定)全绿。
- 2026-10-16 00:28 — **S2 完成**: `background.js` 五项 —— ① `DISCOVERY_EVERY_MINUTES` 10→2(Q3); ② `maybeDiscover` 触发面由「全部实例连败」改为**任一失败**(`failCount >= 1`, 60s 节流不变, 401 仍记 ok 不触发), 且**实例清单为空也走周期分支**(R1: 否则发现集为空时连「失败即发现」都不触发, 连接再也回不来); ③ 新增 `noteDiscoveryResult` 落结构化快照 `lastDiscovery = {at, ok, port, merged, reason, answered, candidates:[{url, note}]}`(`answered` = 候选表至少一个给出 HTTP 应答, 是 C4 徽标边界的判据; `candidates` 记 base URL 供选项页按端口报结论); ④ 新增 `badgeStateOf`(纯函数, 四态)+ `refreshBadge`(徽标 + 底色 + 悬停中文标题; 禁用清空)+ `chrome.action.onClicked → openOptionsPage`, 挂点 = `pollAll` 收尾 / 发现收尾 / `onInstalled` / `onStartup`; ⑤ 新增 `instanceHealth` 台账(按端点记 `ok/at/note/failStreak`, 内存累积 + `pollAll` 收尾**按轮整份落盘**并剪掉清单外端点, R3 不每请求写)。徽标文案走 ASCII(`OK` / `..` / `!`) —— 计划 §3.3 的 `✓/…` 是示意, code-style 明令代码禁图形符号(小字号下渲染成方框), 语义交给颜色 + 悬停标题; 另把 `onInstalled` 状态行里的「手动兜底…2. 手动端点」改为「手动指定…手动端点」(同 Q11 口径, 属 background.js 内的措辞同步)。验证: 新增 node 沙箱守阵 6 条(周期常量 / 失败即发现含 401 负例与同钟位正对照 / 结构化快照 / 健康台账累加与剪枝 / 徽标四态与点击 / 徽标 ASCII), 全绿。
- 2026-10-16 00:28 — 全量闸门 `commands run test.full` 全绿(数字见 `commands run kb.baseline` 最新切片), `kb.check` 自洽。**S3–S6 未实施**: 计划 `doc-status` 仍为 `Open`; 选项页(`options.js`/`options.html`)与两份 README 的交互/布局/口径改动一律未动 —— 因此 `options.html:122` 的「手动端点(兜底…)」与 `README.md:71` 的「② 手动端点(兜底)」仍是旧口径, 与新后台语义(手动优先)暂不一致, 由 S4/S5 收口。


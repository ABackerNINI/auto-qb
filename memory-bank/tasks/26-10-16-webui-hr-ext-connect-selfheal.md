# 26-10-16-webui-hr-ext-connect-selfheal — HR 扩展连接自愈与手动优先(计划立档)

**Status:** Done(S0–S6 全部落地)
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户实报 HR 扩展「立即发现」报 `发现未命中(未知)`、「保存发现地址与配对码」后「自测端点连通」却说 `先在 1. 存入一个实例端点再自测`。经 grilling 11 问收敛, 根因是连接模型而非文案: 数据端口重启即变、发现结果被当一次性缓存(死端点永久堆积)、后台发现结果进不了选项页(静默)、无常驻可见信号。立计划 `plans/26-10-15-2357`(连接自愈 + 手动优先 + 不静默), 仅动扩展侧, 不碰后端与发现协议。
**Topics:** hr-ext-connect-selfheal
**Refs:** memory-bank/plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html
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

实施按计划 §04 分步推进(用户 2026-10-16 指令「实施计划S1-2」⇒ S1/S2 已落地; 指令「实施计划S3-4」⇒ S3/S4 已落地; 指令「实施计划S5-6」⇒ S5/S6 已落地, 计划转 Done):

S1 `discovery.js` 合并语义翻转(手动优先 + 发现集整批替换 + 空集不替换) → S2 `background.js`(失败即发现 + 周期 2min + 徽标四态 + 结构化 `lastDiscovery` + `instanceHealth` 台账) → S3 `options.js`(隐式保存 + 自动接自测 + 文案映射 + 实时刷新 + 空态指路 + 失效标记 + 顶部总览) → S4 `options.html`(布局合并为一个"连接后端"区 + 措辞翻"优先") → S5 `README.md` 口径同步 → S6 `tests/test_extension_proxy.py` 七条新守阵。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| S0 | grilling 收敛 + 计划落盘 + 认领链 + 收尾回写 | Done |
| S1 | discovery.js 合并语义翻转 | Done |
| S2 | background.js 自愈触发 + 徽标 + 台账 | Done |
| S3 | options.js 交互与文案 | Done |
| S4 | options.html 布局合并 | Done |
| S5 | README 口径同步 | Done |
| S6 | 守阵测试 | Done |

## 进度日志

- 2026-10-16 00:01 — S0 完成: 开工同步 `319555af`; grilling 三轮(Q1–Q11)收敛, 计划 `plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html` 落盘(10 节, Open); 认领链双向(计划 ↔ 上游计划 26-10-14-1241 ↔ 本档案 ↔ activeContext 切片); 全量闸门数字见 `commands run kb.baseline`(本轮无代码/测试改动, 与上一基线同树)。实施未启动 —— 待用户显式指令。
- 2026-10-16 00:05 — 新坑入档 `pitfalls/kb/doc-status-meta.md`: 计划首版 `doc-status` 写了 `Draft`(语义像状态但不在 5 词表) ⇒ `kb.index` **静默漏收**该件(仍报「已生成 21 个生成物」)、`kb.check`/`kb.docmap --check`/`doc.links` **全绿**, 只有 `test.full` 的 `test_status_vocabulary` 红; 改 `Open` 后重跑索引并 `grep` 确认已收录。
- 2026-10-16 00:28 — **S1 完成**(用户指令「实施计划S1-2」): 开工同步 `b17c671d`。`discovery.js::mergeInstances` 语义翻转 —— 手动条目(`source !== 'discovered'`, 新增纯函数 `isManualEntry`)**整条胜 + 恒在前 + 原样保留**(Q8/Q1), 发现条目按租约**整批替换**旧发现集(死端点自然剪除, Q2), **空集不替换**(C1, 防后端重启瞬间自断连接); 缺 endpoint/token 的半条仍不收。既有守阵 `test_discovery_helpers_behave` 的合并断言随计划翻转(旧语义「同端点被发现覆盖 + 只增不减」被本计划废止, 属口径演进非守阵松动), 并把 `isManualEntry` 加进「禁本地副本」名单。验证: node 直跑 discovery.js 四组用例(手动胜含 token 保留 / 整批替换剪死端点 / 空集保留旧集 / 顺序稳定)全绿。
- 2026-10-16 00:28 — **S2 完成**: `background.js` 五项 —— ① `DISCOVERY_EVERY_MINUTES` 10→2(Q3); ② `maybeDiscover` 触发面由「全部实例连败」改为**任一失败**(`failCount >= 1`, 60s 节流不变, 401 仍记 ok 不触发), 且**实例清单为空也走周期分支**(R1: 否则发现集为空时连「失败即发现」都不触发, 连接再也回不来); ③ 新增 `noteDiscoveryResult` 落结构化快照 `lastDiscovery = {at, ok, port, merged, reason, answered, candidates:[{url, note}]}`(`answered` = 候选表至少一个给出 HTTP 应答, 是 C4 徽标边界的判据; `candidates` 记 base URL 供选项页按端口报结论); ④ 新增 `badgeStateOf`(纯函数, 四态)+ `refreshBadge`(徽标 + 底色 + 悬停中文标题; 禁用清空)+ `chrome.action.onClicked → openOptionsPage`, 挂点 = `pollAll` 收尾 / 发现收尾 / `onInstalled` / `onStartup`; ⑤ 新增 `instanceHealth` 台账(按端点记 `ok/at/note/failStreak`, 内存累积 + `pollAll` 收尾**按轮整份落盘**并剪掉清单外端点, R3 不每请求写)。徽标文案走 ASCII(`OK` / `..` / `!`) —— 计划 §3.3 的 `✓/…` 是示意, code-style 明令代码禁图形符号(小字号下渲染成方框), 语义交给颜色 + 悬停标题; 另把 `onInstalled` 状态行里的「手动兜底…2. 手动端点」改为「手动指定…手动端点」(同 Q11 口径, 属 background.js 内的措辞同步)。验证: 新增 node 沙箱守阵 6 条(周期常量 / 失败即发现含 401 负例与同钟位正对照 / 结构化快照 / 健康台账累加与剪枝 / 徽标四态与点击 / 徽标 ASCII), 全绿。
- 2026-10-16 00:28 — 全量闸门 `commands run test.full` 全绿(数字见 `commands run kb.baseline` 最新切片), `kb.check` 自洽。**S3–S6 未实施**: 计划 `doc-status` 仍为 `Open`; 选项页(`options.js`/`options.html`)与两份 README 的交互/布局/口径改动一律未动 —— 因此 `options.html:122` 的「手动端点(兜底…)」与 `README.md:71` 的「② 手动端点(兜底)」仍是旧口径, 与新后台语义(手动优先)暂不一致, 由 S4/S5 收口。
- 2026-10-16 00:48 — **S3 + S4 完成**(用户指令「实施计划S3-4」): 开工同步 `d4d764d1→2a3b3e13`。两文件成对改(计划 §S4 须核对: 既有 id 全保留, 只删 `discSave` 并把它下面的表单搬进折叠区)。
  - **S3 `options.js`**(7 项): ① **隐式保存** —— `discoverNow` 重写为「归一化输入框**当前值**(同步) → `chrome.permissions.request`(**本手势内第一个 await**, 前面只许同步代码) → 落盘 `discoveryAddress/pairingCode` → `sendMessage('discover-now')`」, 独立 `saveDiscovery` 与 `discSave` 接线删除(R4: 只存不探的入口由「立即发现」自带); ② **自动接自测** —— 抽出 `probeMainInstance()`(返回 `{state,text,hint}`)作**单一判据**, 自测按钮与「发现命中后」共用, 命中结论合成为「发现命中 18788: 已合并 N 条实例; 主实例端点可达…」; ③ **文案映射** —— 新增 `DISCOVERY_REASON_TEXT`(§3.4 五码)+ `candidateSummary()` 渲染 `lastDiscovery.candidates`(逐候选 `18788 连接失败 · 18789 HTTP 404`), 全文件 `未知` 字面量清零(含 `poll()`/`clearLogsClick()` 两处旧兜底, 改「后台未给出原因」); ④ **实时刷新** —— `storage.onChanged` 增监听 `instances/instanceHealth/lastDiscovery/enabled` → `scheduleConnRender`(300ms 防抖, 与日志/两表同款); `refreshInstancesFromStorage` 升级为 `refreshConnFromStorage(syncJson)`, **外部变更不刷 JSON 文本域**(否则会盖掉用户正在编辑的内容); ⑤ **空态指路** —— 去掉陈旧步骤号「先在 1. …」, 改指向「连接后端」区(自测/获取站点/实例列表三处); ⑥ **失效标记** —— 手动条目 `failStreak >= STALE_FAIL_STREAK(3)`(C3)加「疑似失效(连续 N 轮拉不通; …确认后可删)」, **只提示不代删**(Q10), 徽标改 `[优先]`/`[自动]`(Q11②); ⑦ **顶部总览** —— `connStateOf`(纯函数, 四态)+ `lastDiscoveryText` + `renderConnOverview`(态 · 实例 N 个(M 个可用) · 上次发现…), 发现失败态**自动展开**手动区并加 `attn` 高亮(C6); 总览用 `textContent`(地址/端口来自用户输入, 不进 innerHTML)。
  - **S4 `options.html`**: 原「1 自动发现」+「2 手动端点」+ 页面底部工具栏(status/hint/自测/拉取)合并为**「① 连接后端(自动发现自愈; 手动指定优先)」**一区, 顺序 = 总览行 → 发现地址/配对码 + 单个「立即发现」→ 实例列表 → 手动端点(`<details id="manualEndpoints">` 折叠, 标题改「优先: …永远优先使用, 不会被自动发现覆盖或删除」) → 徽标图例 → 状态行 → 自测/拉取; 后续区块顺延编号(② 站点权限 / ③ 站点现状 / ④ 最近取数明细), 折叠排障区不变。`#status`/`#hint` 随按钮一起上移(留在原处会让顶部按钮的反馈落在看不见的页底)。
  - **守阵随口径更新**(S6 的七条新用例仍未做): `test_options_swiss_wiring` 的元素清单删 `discSave`、`saveDiscovery`, 补 `connState/ manualEndpoints / badgeLegend / test / poll / hint / save / instEndpoint / instToken` 与新落点函数名, 并加一条**反向断言**「`discSave` 不得回潮」; 文件头「## 测试计划」该行同步。属口径演进非守阵松动(计划 §S4 须核对 + R5 已预告)。
  - **验证**: `node --check` 过; 临时探针(未入库, `/tmp/probe_s3.js`)真跑 options.js 沙箱 —— 四态取值与后台 `badgeStateOf` **逐位一致**; 逐候选渲染、总览文案、失效标记(仅手动条目命中, 发现条目 `failStreak=9` 不标)、失败态手动区自动展开、命中后隐式保存 `192.168.1.10 → http://192.168.1.10:18788` + 自测合成结论、坏地址不落盘 —— 全部符合预期; `commands run test.one -- tests/test_extension_proxy.py` 31 passed; `commands run test.full` **全绿**(数字与 +10 差值对账见基线切片 `baselines/26-10-16-0048-hr-ext-connect-selfheal-s3s4.md`)。
- 2026-10-16 00:48 — 遗留给 S6 的**机械比对缺口**(本轮有意留下的, 非遗漏): `options.js::connStateOf` 与 `background.js::badgeStateOf` 是**同一条判据的两个展示面**(徽标 / 顶部总览), 当前是两份实现、靠注释互指; 按计划 §S6 与 R5 的口径应由 S6 补一条跨层守阵(两边的四态键名与判据分支逐项比对), 否则「徽标报警但页面说正常」这类漂移无机械拦阻。同理 `options.html` 的徽标图例文字与后台 `BADGE` 标签是语义同源, 可一并钉。
- 2026-10-16 00:48 — **越界改动披露 1(范围守卫例外「阻塞」)**: 首次全量跑红 2 条 —— `tests/test_memory_bank.py::test_wording_guard_is_green_on_current_kb` / `::test_number_guard_is_green_on_current_kb`, 根因**不在本专题**: 另一会话的 `activeContext/26-10-15-0728-qb-traffic-restart-spike-gap.md:3`(R6 段, 由 `da45dd57` 引入)手抄了一处测试数字, 使判据族 B 实测 395 > 冻结 394。判据表第一列「不修则本次交付跑不起来 / 测试红」成立(全量红 ⇒ 基线数字与提交闸门都拿不到), 故按例外 1 **就地改一行**(`3363 passed + 4 skipped` → 「全绿」, 数字仍由基线切片承载), 未动该文件其它任何字; 改后族 B = 394 达标、全量复绿。
- 2026-10-16 00:48 — **复发 +1 记档**: 本轮踩到**已记的坑** `pitfalls/git/editing-traps.md`「编辑导致整文件行尾归一」—— 用 Edit 往 `pitfalls/testing/node-guards-silent-skip.md` 追加一节, 把该件从 `LF=28/CRLF=0` 写成 `CRLF=44/LF=0`(同轮其它 6 个被 Edit 的文件都仍是 LF)。**为什么没命中**: ①路由只走到顶层 `pitfalls/_index.md`(其「主题」表是空的 `(暂无)`, 没有指向 `git/editing-traps.md` 的细路由), 而 git 类行被读成「**跑 git 命令前**必读」, 本轮动作是「编辑文档」不在该判据内 ⇒ 没进 `pitfalls/git/_index.md`(触发词「行尾」明写在顶层 git 行里却没被识别); ②`git status`/`git diff` 末尾的 `warning: … CRLF will be replaced by LF` **看到了却当成无害噪声**, 定式要求「见到即按字节归一」而我只做到「见到」。已按字节归一回 LF 并把复发条目写进该坑档(附定式强化: 收尾逐文件核 CRLF/LF 计数, 不靠肉眼扫警告)。

- 2026-10-16 01:13 — **S5 完成**(用户指令「实施计划S5-6」): 开工同步 `4611372f`。`extensions/hr-fetch-proxy/README.md` 口径同步 —— ① §2 布局块由「① 自动发现 + ② 手动端点(兜底) + 底部工具栏」改写为 S4 实际的**「① 连接后端(自动发现自愈; 手动指定优先)」单区**(总览行 → 自动发现 → 实例列表「优先/自动」徽标 → 折叠的手动端点 → 自测/拉取), 手动端点口径翻「**优先**」并写明「发现只**补齐**手动没覆盖的端点, 绝不覆盖或删除手动条目」; ② 新增「**连接自愈 + 不静默(2026-10-16)**」段(徽标四态常驻 + 点图标回本页 / 顶部总览 / 失败即发现(60s 节流)+ 2 分钟周期 / 逐候选结果); ③ 排障表「自动发现未命中」行补「逐候选探测结果 + 徽标转红」, 「退手动配置」改「退**手动指定**」(Q11④); ④ 「怎么确认它在工作」补徽标与顶部总览两条。**连带修两处随 S4 失效的引用**(越界披露 2, 见下)。验证: `commands run doc.links` 无死链。
- 2026-10-16 01:13 — **S6 完成**: `tests/test_extension_proxy.py` 补 **5 条新守阵**(计划 §S6 清单里周期/失败即发现/徽标四态/结构化快照/健康台账五条已随 S2 落地, 本轮补齐余下与跨层): ① `test_merge_instances_manual_priority`(手动整条胜含 token 保留 + 恒在前顺序稳定, Q1/Q8/Q9); ② `test_merge_instances_discovered_set_replaced`(旧发现条目整批替换剪死端点 + **空集不替换** C1); ③ `test_no_opaque_reason_leaks`(选项页无 `未知` 字面量 + 后台**每个** `reason` 都有中文映射且映射值是真中文结论); ④ `test_options_listens_instances_changes`(`storage.onChanged` 监听面覆盖 `instances/instanceHealth/lastDiscovery` 并触发重渲染); ⑤ **`test_conn_state_judgement_matches_badge`**(跨层机械比对: 从两文件切出 `badgeStateOf`/`connStateOf` 函数体真跑同一张真值表逐输入一致 + 四态键集 `BADGE` vs `CONN_STATE_TEXT` 同源 + `options.html` 徽标图例与 `BADGE.label` 同源)。配套: 把 `_NODE_RUN_DISCOVERY_HELPERS` 抽成缓存 `discovery_helpers_trace()` 供三条合并用例共用一次 node; 新增静态切块小工具 `_balanced_block`/`_js_object_block`/`_js_object_keys`; 文件头「## 测试计划」加 S6 小节。
- 2026-10-16 01:13 — **守阵红绿双验**(5 类突变判红后还原复绿): ① `connStateOf` 的 C4 分支(`answered === false`→`true`)→ 跨层用例红; ② 选项页引入 `未知` 字面量 → 红; ③ 删一个 `DISCOVERY_REASON_TEXT` 映射键 → 红; ④ 监听面去掉 `instances` → 红 —— **首版用子串判据 `"changes.instances" in body` 漏判** `changes.instancesX`(红验当场抓到), 改词边界 `\b` 后通过, 已把该教训写进用例注释; ⑤ `discovery.js` 空集不替换分支删除 → 红。还原后 `test.one -- tests/test_extension_proxy.py` 36 passed。
- 2026-10-16 01:13 — **越界改动披露 2(范围守卫例外「阻塞/同源」)**: S5 连带改 README 三处**随 S4 失效的引用**, 属计划 §S5 四条之外的改动 —— ① 跨机「发现与配对上手」第 2 步原写「填地址 → **保存** → 点立即发现」, 但 S4 已删「保存发现地址与配对码」按钮(隐式保存) ⇒ 改为「点立即发现(地址与配对码随这次点击一起保存)」; ② 「运行日志」节原写「选项页**④区**是扩展自己的运行日志」, 而 S4 重编号后 ④ = 最近取数明细、日志在折叠区 ⇒ 改为按名引用「折叠区的运行日志」; ③ 事件环说明原写「**④⑤** 的数据源」, 同一重编号下应为 ③④ ⇒ 改正。三处都是**本次口径同步所依赖的同一份 README 内部一致性**(不改则本次编辑自相矛盾), 故就地改; 未动其它任何字。
- 2026-10-16 01:13 — **收尾 DoD**: `commands run test.full` 全绿(数字见基线切片 `baselines/26-10-16-0113-hr-ext-connect-selfheal-s5s6.md`, +5 差值已在切片内对账 = 本轮 5 条新守阵); 计划 `doc-status` Open → **Done**、`doc-updated` 抬至 26-10-16-0113 并补变更记录; 本档案状态转 Done; activeContext 切片更新; `commands run kb.index` 重建索引。

## 遗留与下一步

- **S0–S6 全部落地, 计划转 Done**; 收尾 DoD 已完成(档案 / activeContext / 计划状态 / 基线切片 / 索引)。
- **真机验收待兑现**(计划 §06 判据为真机观察, 本机无法完成): V1 端口变化零操作自愈 / V4 后端停三处一致报警且恢复自动转正常 / V6 改地址后一次点击闭环 / V7 手动失效只提示不代删 —— 待用户在真机(装了扩展 + 起后端)上走一遍。
- 现场不一致(范围外, 待用户对齐): 仓库 `config.yml` 的 `channel.port: 18788` 与发现默认端口相撞, 而运行日志显示数据端口 7031。
- 可选项(计划 §07 R4 记录): 若用户确需「只存地址不探测」, 可后续按需加回独立保存入口。


# 26-10-10-webui-reannounce-inactive-gate — 非活跃种子禁强制汇报(qB 口径)

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-10 20:32
**Topics:** webui-reannounce-inactive-gate
**Summary:** 用户要求「WEBUI 非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与 qb 的行为保持一致」。口径按 qB 原样对齐(commit `aa189a7` 关闭 issue #12080: `isPaused`/`isChecking`/`isQueued` 时 `actionForceReannounce->setEnabled(false)`, tooltip 原文 "Can not force reannounce if torrent is Paused/Queued/Errored/Checking" ⇒ 暂停/停止 · 排队 · 校验中 · 错误/文件丢失 均为非活跃)。四处落点: 判定单点 `shared/decorate.js`(两张表 + 四个方法, 多目标按 qB `oneCanForceReannounce` = 任一活跃即可用); 显示层 `tpl/ctx-menus.html` 四支 + `drawer_tpl/04|05|06` 重报钮置灰(`.is-gated` + title 给原因); 行为层 `commands.js::_guardReannounce` 接在 `_actCore` 的 reannounce 前置(覆盖 组/单种/整集/批量)、`shortcuts.js::_kbAct` 早于确认框、`drawer.js::torrentCmd` 兜底 —— 四条入口一个不落。9 源文件 + 1 测试文件(静态守阵含 node 电池真跑 24 项)+ e2e `menus.spec.mjs` 块E 双皮肤(`@fast` 门禁)。机理入坑档 `pitfalls/web-ui/reannounce-inactive-gate.md`。**后续轮(20:32, 用户追问混选)**: 上一轮"照 qB 照发全选"的判断被修正 —— 复刻了 qB 的指令集合却没复刻它的观感(我们多一层 qB 没有的 per-target 确认回执, 非活跃目标会白等窗口后落假「未确认」, 把干净的成功渲染成部分失败)。用户三项拍板后新增**投递收敛**第二层: 前端单点 `decorate.js::reannouncePlan`(组目标展开为活跃成员 hash, 解析面与闸门同源)+ `_actCore` 按计划投递与跳过数文案 + 后端 `commands.py` 模块级 `REANNOUNCE_BLOCKED_STATES`/`reannounce_blocked()`/`_reannounce_active()` 与两个 `_cmd_reannounce_*` 过滤(第二道闸)。⚠ 后端判据**不得**用 `state_enum` 谓词(实测 `queuedDL` 命中 `is_downloading`, 判不出排队), 必须判 `rec.state` 原文并与前端表逐项同表(守阵钉住)。详见下方「后续轮」节。
**Refs:** memory-bank/testing/baselines/26-10-10-2004-webui-reannounce-inactive-gate.md,memory-bank/activeContext/26-10-10-2004-webui-reannounce-inactive-gate.md,memory-bank/pitfalls/web-ui/reannounce-inactive-gate.md

## 原始请求

> 用户(2026-10-10): 「WEBUI非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与qb的行为保持一致」

## 思考过程与决策

- **请求边界判定**: 执行任务(功能变更), 非问答/只读 —— 直接实现 + 守阵 + 收尾, 不另出计划/报告文档。
- **口径三问(开工先问, 不猜)**: ①「非活跃」范围 → 用户选**与 qB 完全一致**(不是"仅暂停/停止"); ②多选/整组/整集置灰规则 → 用户选**全部目标都非活跃才置灰**(= qB `oneCanForceReannounce` 的"任一活跃即可用"); ③键盘快捷键 → 用户选**一并拦截**。
- **qB 判据核实(不靠记忆)**: 拉 qB [commit `aa189a7`](https://github.com/qbittorrent/qBittorrent/commit/aa189a7) 原文 —— `const bool rechecking = torrent->isChecking(); const bool queued = (Session::instance()->isQueueingSystemEnabled() && torrent->isQueued()); if (!isPaused && !rechecking && !queued) oneCanForceReannounce = true;` 并 `setEnabled(oneCanForceReannounce)` + tooltip "Paused/Queued/Errored/Checking"; 关联网 [issue #12080](https://github.com/qbittorrent/qBittorrent/issues/12080)。**多目标判据是"任一可汇报即可用", 不是"全部"** —— 这条抄错会把混合组误置灰。
- **判定字段选型(关键)**: 项目的派生字段 `kind` 只 6 档, 而 qbittorrent-api 把 `queuedDL`/`queuedUP` 归进 `is_downloading`/`is_uploading` ⇒ 其 kind 落成 `downloading`/`seeding` —— **单看 kind 判不出排队**。故判定读 qB 原始 `state` 串(成员行/SEED_ITEM/详情 `to_dict()` 都带), `state` 缺失时回落 kind 的 paused/checking/error 三档兜底。
- **入口盘点(为什么必须四处都接)**: 强制汇报的四条路径 —— ①右键菜单四支(多选/整集/单种子/单组)→ `_actCore`; ②键盘 `Shift+A` → `_kbAct` → `_actCore`; ③详情面板 tracker 页签重报钮 → `drawerCmd` → `torrentCmd`(不经 `_actCore`!); ④任何直调。只堵右键 ⇒ 键盘与面板绕得过去。故显示层负责"变灰 + 原因", 行为层在 `_actCore`(覆盖 ① ②)与 `torrentCmd`(覆盖 ③)各设一道总闸。
- **置灰的"不可点"实现选型**: 项目既有 `is-gated` 口径(可见但不可点: 样式灰 + `cursor:default` + title 给原因 + 行为层再拦一道)。**不采用 `disabled` 属性 / `pointer-events:none`** —— 二者会让全局自绘 tooltip 的 `mouseover` 委托命中不到, "为什么变灰"的说明反而丢失(详见坑档「置灰规则的 CSS 特异性」节)。故: 菜单项恒绑 title 字符串(可用时空串, 走 ui_feedback 的「空串 title = 清除提示」通道; 绑 `|| null` 会走 removeAttribute 分支, 旧的 `data-aq-tip` 不被清), 图标色并进同一条 `is-gated` 规则(压过 `.ico-sync` 的 (0,2,0))。
- **不越界**: 未顺手改其它动作的可用性。
- ⚠ **本行原写「未改后端 / 未过滤混合批量里的非活跃成员(qB 也是照发全选, 不另裁决目标语义)」—— 该判断在后续轮被推翻, 见下节「后续轮」**。当时只把混合批量当成 qB 的忠实复刻(事实面没错: qB 确实照发全选), 但漏算了自己这侧有 tracker 确认层: 照发全选会让非活跃目标进确认跟踪白等窗口, 反而**偏离**了 qB 的实际观感(成功), 故后续轮把后端与投递集合都收敛了。

## 实现计划

- **S1** 判定单点 `shared/decorate.js`: `REANNOUNCE_BLOCKED_STATES` / `REANNOUNCE_BLOCKED_KINDS` + `reannounceBlocked` / `reannounceBlockText` / `_reannounceRows` / `_reannounceVerdict` / `reannounceTargetsGate` / `reannounceMenuGate` / `drawerReannounceGate`。
- **S2** 显示层: `tpl/ctx-menus.html` 四支置灰(`:class` + `:title` 成对); `drawer_tpl/04|05|06` 重报钮按 `drawerReannounceGate()` 置灰 + 各变体 `.is-gated` CSS; `drawer_templates.js` 核心注入的 `is-gated` 规则并集 `> .ico`。
- **S3** 行为层: `commands.js::_guardReannounce` + `_actCore` 前置; `shortcuts.js::_kbAct` 先拦后确认; `drawer.js::torrentCmd` 兜底。
- **S4** 守阵: 静态 `test_frontend_reannounce_inactive_gate_wiring`(接线四钉 + node 电池真跑 24 项 + 红验)+ 真浏览器 `e2e/menus.spec.mjs`「块E 强制汇报可用性」(`@fast`, 双皮肤 2 条 + 红验)。
- **S5** 验证与知识库收尾: `test.full` + `@fast` 门禁 + 坑档/切片/基线/档案/kb.index。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 判定单点(decorate.js) | Done |
| S2 | 显示层(右键四支 + 详情面板三变体 + CSS) | Done |
| S3 | 行为层(_actCore / _kbAct / torrentCmd) | Done |
| S4 | 静态守阵 + node 电池 | Done |
| S5 | 验证 + 知识库收尾 | Done |

## 进度日志

- **2026-10-10 20:04** 开工 `my-commit-flow.sync` 已同步 `206eb7d6` → 拉 qB commit `aa189a7`/issue #12080 核判据原文 → **三问拍板**(qB 完全一致 / 全非活跃才置灰 / 快捷键一并拦)→ S1 判定单点 + S2 显示层 + S3 行为层 → S4 守阵(静态四钉 + node 电池 + 红验: 删状态表 `queuedDL` 即报红, 还原即绿)→ `node --check` 全绿 → S5 `test.full` 全绿、`@fast` 门禁全绿(数字见基线切片 `26-10-10-2004`; 静态与 e2e 两侧各自红验过:
删状态表 `queuedDL` 静态报红、摘 `_actCore` 闸门 e2e 报"零请求"红)→ 知识库收尾(坑档新条 `pitfalls/web-ui/reannounce-inactive-gate.md`、切片/档案/基线 `26-10-10-2004`、`progress/implemented-webui.md` 新条目)→ `kb.index` 重建。
- **2026-10-10 20:32** 用户追问「多选时『任一可汇报即可用』, 目前的方案会不会导致混选时汇报非活跃种子?」→ **查证成立且危害判断修正**: 请求层确实全量投递(闸门是集合级全有全无), 但真实危害不在"汇报"(qB 引擎 `force_tracker_request` 本就空转)而在**我们自己的确认层** —— 非活跃目标进 pending 后白等到 item deadline(上限 600s)落「未确认」, 前端把干净的成功渲染成 `成功 1, 未确认 3`; qB 的 GUI 无 per-target 回执故不显此症。补证: qB 那个 gate **只在 GUI**(commit `aa189a7` 只改 `src/gui/transferlistwidget.cpp`), HTTP 端点侧无门; `TorrentImpl::forceReannounce()` 是裸透传, 真拦截在 libtorrent(issue #12080 维护者原话 "Force reannounce does nothing even for Queued torrents"); 并实测 `state_enum` 真值表(`queuedDL` 命中 `is_downloading`, 谓词判不出排队)→ **三问拍板**(收敛为活跃子集 / 前后端双保险 / 回执体现跳过数)→ 前端新单点 `decorate.js::reannouncePlan` + `_actCore` 按计划投递与跳过文案 + 后端 `REANNOUNCE_BLOCKED_STATES`/`reannounce_blocked`/`_reannounce_active` 与两个 `_cmd_reannounce_*` 过滤 → 测试桩补 `reannounce_hashes_calls` → 新单测 `test_reannounce_skips_inactive_targets` + 改造注册直判用例(其 (a) 支已从常规路径降级为竞态兜底) + 守阵扩段(投递收敛接线 / 前后端同表 / node 电池项增) + e2e 新增混选双皮肤(按 hash 断言, 不数条数) → **三轮红验**全过(摘后端过滤 / 只在前端多加一项 / 删前端 `stoppedUP`), node 电池项全过, `test.full` 与 `@fast` 门禁全绿(数字见基线切片 `26-10-10-2032`)→ 知识库收尾(坑档新增「闸门 ≠ 投递集合」节、切片更新、本档案、新基线、`progress` 新条目)→ `kb.index` 重建。

## 后续轮: 混选投递收敛(2026-10-10 20:32, 承 20:04 那轮)

**缘起**: 用户追问混选情形。上一轮的"忠实复刻 qB 照发全选"结论被修正 —— 复刻的是 qB 的**指令集合**, 没复刻它的**观感**, 因为我们多了一层 qB 没有的东西(per-target 确认回执)。

**口径(用户三项拍板)**: ①放行后的投递集合**收敛为活跃子集**(菜单可用性仍保持 qB 的 `oneCanForceReannounce` 口径不变); ②落点**前后端双保险**; ③回执/toast **体现跳过数**。

| 步骤 | 内容 | 状态 |
|---|---|---|
| F1 | 前端投递计划单点 `decorate.js::reannouncePlan` | Done |
| F2 | `_actCore` 按计划投递 + 跳过数文案 + 空投递收口 | Done |
| B1 | 后端判据表 + `reannounce_blocked()` + `_reannounce_active()` + 两个 `_cmd_reannounce_*` 过滤 | Done |
| T1 | 单测/守阵/e2e 三处补强 + 三轮红验 | Done |

**本轮的取舍与证据**:
- **不把闸门改成"含任一非活跃就置灰"**: 那会推翻用户上一轮已拍板的 qB 口径(任一活跃即可用), 且与 qB GUI 不符。改为"闸门不动、投递收敛" —— 菜单仍可点(与 qB 一致), 但真正发出去的只有活跃目标。
- **精度上比 qB 更高而非更低**: qB 的 GUI 会把整组选中目标交给引擎再由引擎丢弃; 我们在投递前丢弃。**效果等价**(引擎本来就不执行), 但省掉无用请求与假回执。
- **后端判据不能走 `state_enum` 谓词**(实测真值表: `queuedDL`/`queuedUP` → `is_downloading`/`is_uploading`; 只有 `paused*`/`stopped*` 是 `is_stopped`、`error`/`missingFiles` 是 `is_errored`)⇒ 必须判 `rec.state` 原文, 与前端表同源; 守阵钉两侧同表。
- **注册层原「停止种子立即 warn」支不删**: 投递面收敛后它从常规路径降为**竞态兜底**(过滤判活跃 → 注册前转停止), 保留并在注释里写明; 其契约由改造后的测试直接调注册面钉住。
- **e2e 断言按 hash 落**: 桩是 300 种子 / 150 组, 选中两行必同组 ⇒ 组目标会展开为整组的活跃成员, 数请求条数会随分组形态失真; 只有"非活跃那个的 hash 不在投递集合里"在任何分组下都成立。
- **不越界(本轮新增的观察到的事实, 未动手)**: 规则侧 `rules/actions/transfer.py::ReannounceAction` 只跳 `is_stopped`(不跳排队/校验中/错误), 与 qB 口径不一致 —— 那是规则引擎的主动汇报路径(自带 600s 去重), 不在本轮"WEBUI 非活跃禁汇报"范围内, 未改。

**后续候选(未做)**: ①规则侧 `ReannounceAction` 是否对齐 qB 口径(需先确认规则侧是否也该"静默跳过"); ②`kind` 只 6 档导致"排队"在其它状态相关门控里同样判不出 —— 若后续还有状态门控需求, 考虑把 `state` 原文进 `SEED_ITEM` 的既有字段面做统一判据单点。

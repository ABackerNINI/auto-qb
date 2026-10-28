# 26-10-10-webui-reannounce-inactive-gate — 非活跃种子禁强制汇报(qB 口径)

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-17
**Topics:** webui-reannounce-inactive-gate
**Summary:** 用户要求「WEBUI 非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与 qb 的行为保持一致」。口径按 qB 原样对齐(commit `aa189a7` 关闭 issue #12080: `isPaused`/`isChecking`/`isQueued` 时 `actionForceReannounce->setEnabled(false)`, tooltip 原文 "Can not force reannounce if torrent is Paused/Queued/Errored/Checking" ⇒ 暂停/停止 · 排队 · 校验中 · 错误/文件丢失 均为非活跃)。四处落点: 判定单点 `shared/decorate.js`(两张表 + 四个方法, 多目标按 qB `oneCanForceReannounce` = 任一活跃即可用); 显示层 `tpl/ctx-menus.html` 四支 + `drawer_tpl/04|05|06` 重报钮置灰(`.is-gated` + title 给原因); 行为层 `commands.js::_guardReannounce` 接在 `_actCore` 的 reannounce 前置(覆盖 组/单种/整集/批量)、`shortcuts.js::_kbAct` 早于确认框、`drawer.js::torrentCmd` 兜底 —— 四条入口一个不落。9 源文件 + 1 测试文件(静态守阵含 node 电池真跑 24 项)+ e2e `menus.spec.mjs` 块E 双皮肤(`@fast` 门禁)。机理入坑档 `pitfalls/web-ui/reannounce-inactive-gate.md`。**后续轮(20:32, 用户追问混选)**: 上一轮"照 qB 照发全选"的判断被修正 —— 复刻了 qB 的指令集合却没复刻它的观感(我们多一层 qB 没有的 per-target 确认回执, 非活跃目标会白等窗口后落假「未确认」, 把干净的成功渲染成部分失败)。用户三项拍板后新增**投递收敛**第二层: 前端单点 `decorate.js::reannouncePlan`(组目标展开为活跃成员 hash, 解析面与闸门同源)+ `_actCore` 按计划投递与跳过数文案 + 后端 `commands.py` 模块级 `REANNOUNCE_BLOCKED_STATES`/`reannounce_blocked()`/`_reannounce_active()` 与两个 `_cmd_reannounce_*` 过滤(第二道闸)。⚠ 后端判据**不得**用 `state_enum` 谓词(实测 `queuedDL` 命中 `is_downloading`, 判不出排队), 必须判 `rec.state` 原文并与前端表逐项同表(守阵钉住)。详见下方「后续轮」节。
**Refs:** memory-bank/testing/baselines/26-10-10-2004-webui-reannounce-inactive-gate.md, memory-bank/pitfalls/web-ui/reannounce-inactive-gate.md, memory-bank/issues/26-10-17-1703-bug-webui-delete-reannounce-paused.html, memory-bank/testing/baselines/26-10-17-1816-webui-reannounce-inactive-gate.md, memory-bank/plans/26-10-29-0308-plan-webui-torrent-moving-state-kind.html
## 原始请求

> 用户(2026-10-10): 「WEBUI非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与qb的行为保持一致」

## 思考过程与决策

- **请求边界判定**: 执行任务(功能变更), 非问答/只读 —— 直接实现 + 守阵 + 收尾, 不另出计划/报告文档。
- **口径三问(开工先问, 不猜)**: ①「非活跃」范围 → 用户选**与 qB 完全一致**(不是"仅暂停/停止"); ②多选/整组/整集置灰规则 → 用户选**全部目标都非活跃才置灰**(= qB `oneCanForceReannounce` 的"任一活跃即可用"); ③键盘快捷键 → 用户选**一并拦截**。
- **qB 判据核实(不靠记忆)**: 拉 qB [commit `aa189a7`](https://github.com/qbittorrent/qBittorrent/commit/aa189a7) 原文 —— `const bool rechecking = torrent->isChecking(); const bool queued = (Session::instance()->isQueueingSystemEnabled() && torrent->isQueued()); if (!isPaused && !rechecking && !queued) oneCanForceReannounce = true;` 并 `setEnabled(oneCanForceReannounce)` + tooltip "Paused/Queued/Errored/Checking"; 关联网 [issue #12080](https://github.com/qbittorrent/qBittorrent/issues/12080)。**多目标判据是"任一可汇报即可用", 不是"全部"** —— 这条抄错会把混合组误置灰。
- **判定字段选型(关键)**: 项目的派生字段 `kind` 只 6 档, 而 qbittorrent-api 把 `queuedDL`/`queuedUP` 归进 `is_downloading`/`is_uploading` ⇒ 其 kind 落成 `downloading`/`seeding` —— **单看 kind 判不出排队**。故判定读 qB 原始 `state` 串(成员行/SEED_ITEM/详情 `to_dict()` 都带), `state` 缺失时回落 kind 的 paused/checking/error 三档兜底。
  > 📌 **2026-10-29 时效注记**: 此处「kind 只 6 档」是当时的真实情况; 当日起 `state_kind` 补出第 7 档 `moving`(同时收 `allocating`), 见第四轮节与 [26-10-29-0308 计划](../plans/26-10-29-0308-plan-webui-torrent-moving-state-kind.html)。**"读 state 不读 kind"这条结论本身没有变** —— moving 同时是它的反向证据: 它自成第 7 档(看 kind 判得出), 但后端 `state_enum` 谓词**依然收不到它**, 所以后端那张 blocked 表同样只能按 state 串写。
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
  > 📌 **2026-10-29**: 仍成立(7 档也没消除"同 kind 不同 state"), 该候选**未做**; 但同轮出现了它的**镜像形态** —— 谓词收不到 `moving`(详见第四轮节), 处置已落成。

**第三轮(2026-10-17, 修 issue 26-10-17-1703)**: 删除确认框(六个入口汇入 `_deleteFlow`)是「一条'不允许'必须接全部入口」清单里唯一漏接的入口 —— 默认勾选的汇报前置对非活跃种子请求照发 → 后端 warn → 不放行 → 删除被整体中止。修法(D1–D8): 闸门层全非活跃禁用复选框(opt-pill.is-gated + aria-disabled + 标题给原因 + 模板点击短路) + 投递层 `reannouncePlan` 收敛(跳过数对话框内可见) + `_reannounceAll` 四桶分型(非活跃 warn 降级 skip 不挡删除, 推迟中/error 维持保守口径) + 竞态两处兜底; 测试三重补强(静态守阵扩段/node 电池 46 项/harness 命令泵按 state 判活跃/e2e 按 hash 断言); 坑档复发 +1; 后端零改动。数字见基线切片 26-10-17-1816。

## 第三轮: 删除确认框漏接(2026-10-17, 承 20:32 那轮)

**缘起**: issue `26-10-17-1703-bug-webui-delete-reannounce-paused`(17:03 入池, 17:38 用户显式指派「认领并修复」) —— 删除确认框(六个入口汇入 `_deleteFlow`)默认勾选的「删除前强制重新汇报」对非活跃种子: 请求照发 → 后端第二道闸 warn → `_reannounceAll` 把 warn 判为不放行 → toast「汇报未确认…已保留未删除」→ **删除被整体中止**(须手动取消勾选才能删)。删除链是本专题「一条'不允许'必须接全部入口, 少接即形同虚设」所列入口清单中**唯一漏接的入口**。

**口径(入池时 grilling 八问收敛, 用户答「按推荐」, 认领后按此实施)**:
- D1 两层都修: 闸门层(全非活跃复选框禁用) + 投递层(收敛活跃子集), 只修一层会留「混选仍挡删除」半残态;
- D2 全族判据: 复用 `reannounceBlocked`/`reannouncePlan`(前端)与 `REANNOUNCE_BLOCKED_STATES`(后端), 不新造「仅 paused」特例;
- D3 全暂停复选框形态: opt-pill 置灰禁用 + 取消勾选 + tooltip「目标均非活跃, 无法强制汇报」, 样式层真禁点击;
- D4 H&R 边界: 非活跃 warn 降级为 skip(不挡删除); 活跃目标 tracker 拒绝/超时维持不放行的保守口径, 不借修 bug 放宽;
- D5 跳过数可见: 对话框打开即带说明(如「3 个暂停目标将跳过」)+ 等待态 toast 复用「跳过 N 个非活跃」;
- D6 竞态两处兜底: 前端 `reannouncePlan` 收敛 + `_reannounceAll` 把非活跃类 warn(单种 `REANNOUNCE_INACTIVE_SKIP` / 组「均非活跃」)降级为跳过;
- D7 测试三重: 静态守阵 `test_frontend_reannounce_inactive_gate_wiring` 扩段接线删除链 + node 电池加 probe; harness 命令泵按 state 判活跃; e2e 按目标 hash 断言(全暂停零请求且删除成功 / 混选只投活跃);
- D8 流程: 认领须用户指派, 未认领不动码。

| 步骤 | 内容 | 状态 |
|---|---|---|
| R1 | 复验(node 桩重放仍复现) + issue 置 In Progress + doc-refs 认领链 | Done |
| R2 | 闸门层: 删除确认框全非活跃时 reannounce 项禁用(D3) | Done |
| R3 | 投递层: `_deleteFlow` 按 `reannouncePlan` 收敛 + 跳过数文案(D1/D5) | Done |
| R4 | `_reannounceAll` 非活跃 warn 降级 skip(D4/D6) | Done |
| R5 | 测试三重补强(D7): 静态守阵扩段 + node 电池 + harness 命令泵 + e2e | Done |
| R6 | 验证(test.full + e2e) + issue 置 Done + 坑档/基线/索引收尾 | Done |

## 进度日志(第三轮)

- **2026-10-17 17:38** 用户指派认领 issue 26-10-17-1703; 复验(node 桩重放 §01 仍复现: 暂停种子默认勾选删除 → 请求照发 → warn → 删除 0 请求中止); issue 置 In Progress, doc-refs 回填本档案; 坑档「一条不允许必须接全部入口」复发 +1(原因: 10-10 那轮按菜单可见入口盘点, 漏了删除链这个"删除的前置步骤"形态的第五入口)。
- **2026-10-17 17:45~18:19** 按 D1–D8 实施并收尾: 闸门层 `delete_flow.js::_deleteReannounceGate`(全非活跃 → 复选框禁用+取消勾选+title; 混选 → pill 带「N 个非活跃目标将跳过」)+ `popovers.html` opt-pill `is-gated`(类/标题/点击短路/aria-disabled 四件)+ 三套 CSS 成套(atlas 因 dialogs.css 后加载同补, 否则其 `.opt-pill:hover` 同特异性压过置灰 —— 坑档特异性节的原样复现); 投递层 `_deleteFlow` 按 `reannouncePlan` 收敛(计划空 = 全非活跃竞态 → 跳过汇报直删); `_reannounceAll` 三桶改四桶, 非活跃 warn(文本判据「非活跃」, 两种后端文案)降级 skip 不挡删除, 推迟中/error 维持不放行。后端零改动(第二道闸原样正确)。
- **2026-10-17 18:19** 测试三重补强完成并全绿: 静态守阵扩段 ⑦(node 电池 24→46 项, 含删除闸门五型 + `_reannounceAll` 四种回执分型)+ harness 命令泵按 state 判活跃(非活跃回 warn, 否则 warn 路径在桩上永不可达)+ e2e 块E 两条(@fast 双皮肤 4/4, 按 hash 断言); 三轮红验(静态 JS 关键词漂移 / 模板 is-gated 摘除 / e2e 投递收敛还原)全部报红后还原; node 重放 before/after/race 三幕全转绿; `test.full` 3537 passed + 4 skipped(数字见基线切片 26-10-17-1816); issue 置 Done。

- 2026-10-17 18:19 删除链接入 reannounce-inactive-gate: 闸门层(全非活跃禁用复选框)+投递层(reannouncePlan 收敛)+_reannounceAll skip 桶(D4/D6); issue 26-10-17-1703 修复置 Done; test.full 3537 passed + 4 skipped

## 第四轮(2026-10-29, kind 补第 7 档 moving)

由**另一份档案**驱动 —— 用户报「WEBUI 种子移动中的状态显示为了『其它』」。本档案只记与**本Topic(非活跃门控)**相交的部分, 完整脉络见 [26-10-29-0308 计划](../plans/26-10-29-0308-plan-webui-torrent-moving-state-kind.html)。

- **同一个根因 的镜像形态**: 前三轮反复立的是「`kind` 太粗 ⇒ 单看 kind 会把排队当活跃 ⇒ 门控必须读 `state`」。这一轮撞的是**反向**的同一个根因: qB 的 `moving` **不属于 `TorrentState` 的任何谓词集合**(is_downloading/is_uploading/is_complete/is_checking/is_errored/is_stopped 全不含它) ⇒ `state_kind` 一路判空撞兜底落成 `other`。**一个值可以同时"kind 判得出来"却"谓词判不出来"** —— 于是 "读 state 不读谓词" 这条结论在前后端两侧各自还要立一遍: 后端即便 kind 已有第 7 档, blocked 表仍须按 `state` 串写。
- **显示错位与门控放行是同一个根因的两面**: 补第 7 档只治了显示/筛选/统计; moving 不在 blocked 表里 ⇒ 被当活跃, 强制汇报与删除前汇报都能点。而 qB 在 moving 期间 peer 传输是真停的(libtorrent 搬数据), 汇报换不回 peer; 项目自己的搬迁模块也早把 moving 成员当禁区(`relocate_units.py::GATE_MOVING`)。**补法必须两侧同时落**, 只做一侧等于修了半边。
- **本 Topic 受影响的落点**: `decorate.js::REANNOUNCE_BLOCKED_STATES` 与 `commands.py::REANNOUNCE_BLOCKED_STATES` 同步登记 `moving`(文案「种子搬迁中」); `REANNOUNCE_BLOCKED_KINDS` 补 kind 侧兜底。`REANNOUNCE_INACTIVE_SKIP` 回执文案**维持原样未动**(被 `test_web_commands.py:1465` 逐字断言 + 另有漂移守卫, 改一个字牵动三处) —— moving 的语义由前端 blocked 表的值表达。
- **口径订正**: 「非活跃」自 2026-10-29 起 = 暂停/停止 · 排队 · 校验中 · 错误/文件丢失 · **搬迁中**(qB `aa189a7` 原文未列 moving, 它是按"传输确实停了"这一同一个根因 纳入的)。

# 非活跃种子禁强制汇报(qB 口径)

> 摘要: 「非活跃种子不允许强制汇报」这条 qB 对齐规则, 三处最容易做错 —— ①**判定读 `kind` 而不读 qB 原始 `state`**: `kind` 现 7 档(error/checking/paused/downloading/seeding/**moving**/other; moving 于 2026-10-29 补), 而 qbittorrent-api 把 `queuedDL`/`queuedUP` 归进 is_downloading/is_uploading ⇒ 其 kind 落成 downloading/seeding, 单看 kind 会把**排队**种子当活跃放行(而 qB 自己正是拿 `isQueued` 置灰的); **同一个坑的反向版本**: 补了 moving 档之后它虽然"看 kind 判得出来", 但后端 `state_enum` 的谓词**依然不包含它**, 所以后端那张表照样得按 `state` 串写 —— 前后端判据必须同表, 只改一边必立刻报红; ②**只接一个入口**: 强制汇报有四条入口(右键菜单四支 / 键盘 Shift+A / 详情面板 tracker 重报钮 / 程序化 `torrentCmd`), 只改右键 = 键盘与详情面板绕得过去, "不允许"就不成立; ③**置灰样式压不住 base**: 菜单项图标另有 `.ico-sync`(0,2,0), 变体动作钮 hover 是 (0,3,0), 05 失败区更有 (0,4,0) —— 不显式抬特异性就会出现"文字灰、图标仍蓝"或"置灰了还能 hover 亮起"的半灰态。
> 等级: L0
> 触发: 强制汇报, reannounce, 非活跃, 暂停种子, 排队种子, 搬迁中, moving, queuedDL, stoppedUP, checkingResumeData, is-gated, 置灰, 按钮变灰, 右键置灰, qB 口径, aa189a7, issue 12080, kind 判不出排队, state 原文, isPaused isChecking isQueued
> 更新: 2026-10-29 —— moving 进同张表并升第 7 档 kind(处境: [26-10-29-0308-plan-webui-torrent-moving-state-kind.html](../../plans/26-10-29-0308-plan-webui-torrent-moving-state-kind.html))

**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md, memory-bank/plans/26-10-29-0308-plan-webui-torrent-moving-state-kind.html

## 判定必须读 qB 原始 `state` 串, 不能只读 `kind`

- **触发**: 给"与种子状态相关"的动作做可用性门控(强制汇报是第一例, 同类还有跳检/校验/移动)。
- **判别**: 需要区分**同 kind 不同 state** 的场合 —— `/api/state` 各行与详情 `to_dict()` 都带 qB 原文 `state`(`queuedDL` / `stoppedUP` / `checkingResumeData` / `missingFiles` / `moving` …), 而项目派生字段 `kind` 现 **7 档**: `queuedDL` 与 `downloading` 同为 `downloading`(`queuedUP` 与 `uploading` 同为 `seeding`)。
- **⚠ 2026-10-29 新增的反向坑(同类第四例)**: 反过来也存在**"谓词收不到、kind 却收得到"**的状态 —— qB 的 `moving`(搬迁存储位置中)不属于 `TorrentState` 的**任何**谓词集合(is_downloading/is_uploading/is_complete/is_checking/is_errored/is_stopped 全不含它), 于是 `state_kind` 一路判空撞兜底 ⇒ 落成 `other`, 界面显示「其他」。这类"孤儿成员"的双重后果是: **显示层错位**(2026-10-29 用户报"移动中显示成了其它")且**门控层放行**(不在 blocked 表里 = 被当活跃, 强制汇报/删除前汇报都能点 —— 而 qB 在 moving 期间 peer 传输是真停的, 汇报换不回 peer)。**补法必须两边同时落**: `state_kind` 里单独成档(显示/筛选/统计)+ 前后端两张 blocked 表同步登记(门控); 只做成档不做门控 = 修了显示、漏放行。(第三方库同族孤儿还有 `allocating`, 已与 moving 同档合并 —— qB v5.3.0 不再产出, 老版回连才会复刻。完整穷举见上述计划文档 §03 全映射表)
- **处置**: 门控读 `state`, 只在 `state` 缺失(老版本/异常行)时**回落** `kind` 的 paused/checking/error 三档兜底(2026-10-29 起 moving 亦然 —— 走 state 主路径, kind 兜底不扩那一档以免本末倒置)。判据单点 = `shared/decorate.js::REANNOUNCE_BLOCKED_STATES`(qB 口径逐项: paused*/stopped*/queued*/checking*/error/missingFiles/**moving**) + `REANNOUNCE_BLOCKED_KINDS`; 后端同名表在 `commands.py`, 与前端逐项同表由守阵钉住。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_frontend_reannounce_inactive_gate_wiring` —— 含 node 电池真跑(关键一条: `state=queuedDL` 且 `kind=downloading` 仍须判非活跃)。

## 一条"不允许"必须接**全部**入口, 少接即形同虚设

- **触发**: 给某个已有动作加前置限制(置灰 / 拒绝 / 需确认)。
- **判别**: 先 `grep` 该动作的**全部**调用点 —— 强制汇报的入口: `ctx-menus.html` 四支(`ctxAct`/`actEpisode`/`actTorrent`/`act`)→ `commands.js::_actCore`; 键盘 `shortcuts.js::_kbAct`; 详情面板变体 `drawer_tpl/04|05|06` → `drawer.js::torrentCmd`; **删除确认框的汇报前置 `delete_flow.js::_deleteFlow`(六个删除入口汇入, 2026-10-17 补——见下方复发)**; 以及任何直调 `_actCore` / `torrentCmd` / `_reannounceAll` 的新代码。只堵 UI 层(模板 v-if / class)不改行为层, 键盘与程序化路径原样穿过去。
- **处置**: 判据单点(喂目标集合, 返回 `{ok, title}`)+ 行为层**一道总闸**(`_actCore` 里 `action === "reannounce"` 前置、`torrentCmd` 里同款), UI 层只负责"显示置灰 + title 说明原因"。键盘路径在前置闸门**早于**确认框(先问"确定?"再回"不行"是坏体感)。
- **守阵**: 同一守阵逐入口钉住(四支 `reannounceMenuGate()` 成对 + `_actCore`/`_kbAct` 次序 + 三变体与 `torrentCmd` + 删除链 `_deleteFlow` 的计划收敛/闸门禁用/`_reannounceAll` skip 桶), 任一入口被摘除即红。
- **复发 +1(2026-10-17, issue 26-10-17-1703)**: 2026-10-10 那轮按"菜单/键盘/详情面板/程序化"四条盘点, **漏了删除确认框这个第五入口** —— FX-16 起四条删除链统一进 `_deleteFlow`, 其汇报前置对 keys/hashes 全量原样投递, 于是暂停种子照发 → 后端 warn → 不放行 → **删除被整体中止**(用户须手动取消勾选才能删)。为什么没命中: 盘点时 `grep` 的是动作名(reannounce)的**菜单可见入口**, 而删除链的汇报是"删除的前置步骤", 不以菜单项形态出现 —— **入口清单要以"该判据保护的动作的全部触发路径"列, 不能只数菜单项**。

## 置灰规则的 CSS 特异性: 别只看文字那一层

- **触发**: 用"加个类置灰"的做法做不可用态(`.ctx-item.is-gated` / 变体 `.dt0X-act.is-gated`)。
- **判别**: 置灰是**多条声明**的组合(文字色/背景/cursor/图标色), 而它们各自的 base 规则特异性不同 —— 菜单项图标 `.ctx-item .ico-sync { color: var(--blue) }` 是 (0,2,0), 变体钮 `.drawer .dt04-act:hover` 是 (0,3,0), 05 失败区 `.drawer .dt05-fail .dt05-act:hover` 是 (0,4,0)。只写一条 (0,2,0) 的置灰 ⇒ 文字灰了图标还蓝 / hover 一碰又亮。
- **处置**: 置灰选择器按目标 base **逐条抬特异性并集写出**(菜单项把 `> .ico` 并进同一条; 变体把本变体各自最高特异性的 hover 一并列出, 05 带 `.dt05-fail` 前缀), 不靠"写在后面"取胜 —— 顺序只在特异性相同时才管用。
- **守阵**: 同一守阵钉 `.{cls}.is-gated` 与 05 的 `.dt05-fail .dt05-act.is-gated:hover` 成对存在。

## 闸门(允不允许) ≠ 投递集合(发给谁) —— 多目标门控的混选缺口(2026-10-10)

- **触发**: 给一个**作用于多目标**的动作加可用性门控(置灰 / 拒绝), 判据是"任一目标满足条件即可用"这种 **OR 语义**(qB `oneCanForceReannounce` 就是)。
- **判别**: OR 语义下混选(1 个可汇报 + N 个不可汇报)是**放行**的。这时如果实现把"放行"当成"集合里每个目标都该收到指令", 就对不可汇报的目标也投了指令。**在 qB 上无害**(引擎 `force_tracker_request` 对暂停种子直接空转, 且 qB 的 GUI 没有 per-target 回执, 空转就空转); **在有确认层的实现上有害** —— 那些目标被登记进 tracker 确认跟踪, 引擎空转 ⇒ tracker 永不前跳 ⇒ 一直 pending 到 item deadline(本项目上限 600s), 落「未确认」; 前端三桶聚合把一次干净的成功渲染成 `强制汇报: 成功 1, 失败 0, 未确认 3`。**误报比漏报更费解**: 用户看到的是"部分失败", 而真实情况是全成功。
- **处置**: 闸门与投递**分成两层**, 前者判"允不允许"(保持与 qB 同口径的集合级全有全无), 后者判"发给谁"(收敛为可执行子集)。识别信号的形状是: 判据里出现 `some(...)`/`any(...)` 就说明它是 OR 语义 —— **OR 语义 ⇔ 放行后必然需要一次集合收敛**, 否则集合里必然混着不满足条件的目标。收敛的解析面**必须与闸门同源**, 否则会出现"判过的集合 ≠ 发的集合"这种更难查的分叉; 解析不出的目标按**原样投递**处理(不静默丢), 由后端给显式回执。回执要把跳过数报出来(且**在等待态就报** —— 跳过数是投递前已知的, 拖到终态回执等于让用户盯 40s 才知道"选了 2 个为什么只汇报了 1 个")。
- **另两条附带的坑**: ①后端做同一道收敛时**不能拿 `state_enum` 的谓词当判据** —— 实测 `queuedDL`/`queuedUP` 命中 `is_downloading`/`is_uploading`(只有 `paused*`/`stopped*` 是 `is_stopped`, `error`/`missingFiles` 是 `is_errored`), 用谓词会把**排队**当活跃放过去; 后端只有 `rec.state` 原文与前端表同源才判得对。②收敛后注册层里原有的"停止种子立即 warn"分支从常规路径**降级为竞态兜底**(过滤判活跃 → 执行前转停止), 别当死代码删掉 —— 删了等于把竞态推回"白等 600s 后报未确认"。
- **守阵**: ①静态守阵钉"计划单点存在 + 动作层真的用计划 + 跳过文案 + 空投递收口" + **前后端判据表逐项同表**(两侧各写一份是刻意的: 前端要能在无后端往返时判置灰; 漂移必须立刻报红); ②e2e 断言按**目标 hash** 落(活跃的在集合里 / 非活跃的不在), **不要数请求条数** —— 选中行可能同属一组而被展开为整组成员, 条数随分组形态变, 只有 hash 级断言在任何分组下都成立(本项目桩是 300 种子 / 150 组, 两行必同组)。

## 回执的 warn 桶要按性质分型: 「非活跃·已跳过」算 skip, 不挡前置动作(2026-10-17)

- **触发**: 消费端的确认回执把不同性质的 warn 归进同一个桶, 且该桶的语义是"不放行"。
- **判别**: 「已受理·推迟中」与「非活跃·已跳过」都回 `status="warn"`, 但性质相反 —— 前者是真 H&R 风险(汇报要等最小间隔过期才真正发出, 立即删除会随种子一并丢失), 后者是**永远不可能有回执**(libtorrent `force_tracker_request` 对 `is_paused()` 直接 return; 后端第二道闸显式回 warn「种子非活跃…」/「组内均非活跃…」)。把后者当前者处理 = "不可能的承诺挡了真实操作"(删除被整体中止, 用户须手动取消勾选)。
- **处置**: 前端 `_reannounceAll` 三桶改四桶, 非活跃类 warn(文本判据: 回执含「非活跃」, web 回执无错误码故只能按文案, 两侧文案由静态守阵钉住)降级为 **skip**: 计数、在终态 toast 报出来, 但**不 return false**。这同时是渲染到点击之间状态变化的**竞态兜底** —— 收敛(`reannouncePlan`)只能收敛"投递前已知"的非活跃, 竞态窗口只能靠回执侧兜底。保守口径不放宽: 推迟中/超时/拒绝维持不放行。
- **守阵**: node 电池对 `_reannounceAll` 直接喂四种回执(非活跃 warn 两种文案 / 推迟中 warn / error / rejected)验分型; e2e 侧按 hash 断言"非活跃目标零请求"。


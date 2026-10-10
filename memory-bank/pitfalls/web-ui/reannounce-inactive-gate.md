# 非活跃种子禁强制汇报(qB 口径)

> 摘要: 「非活跃种子不允许强制汇报」这条 qB 对齐规则, 三处最容易做错 —— ①**判定读 `kind` 而不读 qB 原始 `state`**: `kind` 只 6 档(error/checking/paused/downloading/seeding/other), 而 qbittorrent-api 把 `queuedDL`/`queuedUP` 归进 is_downloading/is_uploading ⇒ 其 kind 落成 downloading/seeding, 单看 kind 会把**排队**种子当活跃放行(而 qB 自己正是拿 `isQueued` 置灰的); ②**只接一个入口**: 强制汇报有四条入口(右键菜单四支 / 键盘 Shift+A / 详情面板 tracker 重报钮 / 程序化 `torrentCmd`), 只改右键 = 键盘与详情面板绕得过去, "不允许"就不成立; ③**置灰样式压不住 base**: 菜单项图标另有 `.ico-sync`(0,2,0), 变体动作钮 hover 是 (0,3,0), 05 失败区更有 (0,4,0) —— 不显式抬特异性就会出现"文字灰、图标仍蓝"或"置灰了还能 hover 亮起"的半灰态。
> 触发: 强制汇报, reannounce, 非活跃, 暂停种子, 排队种子, queuedDL, stoppedUP, checkingResumeData, is-gated, 置灰, 按钮变灰, 右键置灰, qB 口径, aa189a7, issue 12080, kind 判不出排队, state 原文, isPaused isChecking isQueued

**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md

## 判定必须读 qB 原始 `state` 串, 不能只读 `kind`

- **触发**: 给"与种子状态相关"的动作做可用性门控(强制汇报是第一例, 同类还有跳检/校验/移动)。
- **判别**: 需要区分**同 kind 不同 state** 的场合 —— `/api/state` 各行与详情 `to_dict()` 都带 qB 原文 `state`(`queuedDL` / `stoppedUP` / `checkingResumeData` / `missingFiles` …), 而项目派生字段 `kind` 只 6 档: `queuedDL` 与 `downloading` 同为 `downloading`(`queuedUP` 与 `uploading` 同为 `seeding`)。
- **处置**: 门控读 `state`, 只在 `state` 缺失(老版本/异常行)时**回落** `kind` 的 paused/checking/error 三档兜底。判据单点 = `shared/decorate.js::REANNOUNCE_BLOCKED_STATES`(qB 口径逐项: paused*/stopped*/queued*/checking*/error/missingFiles) + `REANNOUNCE_BLOCKED_KINDS`。
- **守阵**: `tests/test_webui_static_dom_panel.py::test_frontend_reannounce_inactive_gate_wiring` —— 含 node 电池真跑(关键一条: `state=queuedDL` 且 `kind=downloading` 仍须判非活跃)。

## 一条"不允许"必须接**全部**入口, 少接即形同虚设

- **触发**: 给某个已有动作加前置限制(置灰 / 拒绝 / 需确认)。
- **判别**: 先 `grep` 该动作的**全部**调用点 —— 强制汇报有四条: `ctx-menus.html` 四支(`ctxAct`/`actEpisode`/`actTorrent`/`act`)→ `commands.js::_actCore`; 键盘 `shortcuts.js::_kbAct`; 详情面板变体 `drawer_tpl/04|05|06` → `drawer.js::torrentCmd`; 以及任何直调 `_actCore` / `torrentCmd` 的新代码。只堵 UI 层(模板 v-if / class)不改行为层, 键盘与程序化路径原样穿过去。
- **处置**: 判据单点(喂目标集合, 返回 `{ok, title}`)+ 行为层**一道总闸**(`_actCore` 里 `action === "reannounce"` 前置、`torrentCmd` 里同款), UI 层只负责"显示置灰 + title 说明原因"。键盘路径在前置闸门**早于**确认框(先问"确定?"再回"不行"是坏体感)。
- **守阵**: 同一守阵逐入口钉住(四支 `reannounceMenuGate()` 成对 + `_actCore`/`_kbAct` 次序 + 三变体与 `torrentCmd`), 任一入口被摘除即红。

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


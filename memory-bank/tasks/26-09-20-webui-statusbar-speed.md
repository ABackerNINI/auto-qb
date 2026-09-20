# 26-09-20-webui-statusbar-speed — WEBUI 状态栏上传/下载速度恒为 0

**Status:** In Progress
**Started:** 2026-09-20
**Updated:** 2026-09-20
**Owner:** 主线
**Issue:** [issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html](issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html)
**Plan doc:** [docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html](../../docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html)
**Summary:** 用户真机报「WEBUI 状态栏上传/下载速度不更新，永远显示 0」。入池后用户指派认领，先做复验与深入分析：根因是**状态栏在前端对 `groups` 求和，而 P1-1「按视图回传」在种子页不回 `groups`**（`VIEW_ARRAYS["torrent"] = ("torrents",)`）⇒ `this.groups` 永远停在初始 `[]` ⇒ 合计恒 0；次因是合计只遍历 `groups`，漏掉未归组 `singles`（桩实测少算 88.7%）。已用真 `create_app` + 合成种子桩服务复现（种子页响应里**没有 `groups` 键**，真值 15,206,400）。修复计划已产出（4 处改动 + 3 条守阵），**尚未动代码**。

## 原始请求

> 记录bug: WEBUI状态栏上传/下载速度不更新永远显示0
>
> 认领, 先深入分析, 写一个修复计划

## 思考过程与决策

- **决策 1（先复验再分析，不靠静态阅读下结论）**：入池时只做了静态阅读，报告里根因留「待查」并写了三条假设。认领后第一件事按防过期原则第 5 条重跑锚点 —— 起 `scripts/ui_harness.py`（真 `create_app` + 合成种子，自带非零 dlspeed/upspeed）直接 curl 两个视图比对。结果**假设 1 与假设 2 合并才是真相**：不是「视图没刷新」，也不是「快照不更新」，而是**视图压根没回这个数组**。若按静态阅读的猜测去修「刷新节拍」，会白改一通。
- **决策 2（不把 `groups` 加回种子页）**：最直觉的修法是补 `VIEW_ARRAYS["torrent"]`，但它会废掉 P1-1 的成果（种子页响应体 4.52MB → 6.41MB，3000 种子实测），且现有守阵 `test_api_state_view_scoped_payload` 明确断言 `"groups" not in t`。状态栏只要两个数字，不值得为它回传一整张表。
- **决策 3（服务端算 totals，放进 `status` 恒回传）**：`status` 块里的 `traffic` / `server` 已经是「恒回传、不参与 rid 门控」的口径，加 `totals` 是同一套路 —— 这才是本 bug 的解药（让状态栏不再依赖任何一个按视图裁剪的数组）。同时全量求和（含未归组）一并修掉次因。
- **决策 4（不碰 `status_snapshot()` / 不加别名）**：`status_snapshot()` 是核心域快照（托盘 UI 也用），不该掺 WEB 聚合；`_WEB_STATE_ALIAS` 是**旧字段名**的兼容层，新代码不该往里加（直接读 `manager.web.speed_totals`），少改一个文件。
- **决策 5（守阵要能防"冻结值"，不只是防 0）**：浏览器冒烟断言写成「状态栏值 === 服务端 `status.totals.dlspeed`」而不是「≠ 0」。理由：若用户先开过辅种页再切种子页，旧实现显示的是**冻结的旧值**而非 0，只断言非 0 会漏掉这个更隐蔽的形态。
- **决策 6（候选 C 只作备选并标注风险）**：`status.server.dl_info_speed`（qB 全局）零计算，但桩服务实测 `server_state = null`，走它的守阵在 CI 里**测不出真值**，只能测「不报错」。数据源可控性优先，故默认走 A。

## 实现计划

| ID | 改动 | 文件 | 状态 |
|---|---|---|---|
| F1 | 新增 `_build_speed_totals()`：对 `store.by_hash` 全量求和 dl/ul | `src/auto_qb/mixins/web_view.py` | ✅ 完成 |
| F2 | `__init__` 加 `speed_totals`；`_publish_locked()` 与四视图同临界区赋值 | `src/auto_qb/web_runtime.py` | ✅ 完成 |
| F3 | `api_state` 的 `status` 块加 `"totals": manager.web.speed_totals`；**并把 `ensure_group_state()` 提到 status 字典之前**（见下方「第二个缺陷」） | `src/auto_qb/web.py` | ✅ 完成 |
| F4 | `totalDl` / `totalUl` 改读 `this.status.totals.*`（prism/atlas 模板不动） | `src/auto_qb/web_ui/static/shared/decorate.js` | ✅ 完成 |
| F5-1 | 端点守阵：`view=torrent` 与 `updated=false` 两种情况下 `totals` 均在且等于全量合计 | `tests/test_web.py` | ✅ 完成 |
| F5-2 | 静态防回潮：`decorate.js` 不得再出现 `this.groups.reduce` 的速度求和（红绿双验过） | `tests/test_web.py` | ✅ 完成 |
| F5-3 | 浏览器冒烟：种子页 `vm.totalDl === status.totals.dlspeed` 且 > 0 | `scripts/ui_smoke.cjs` | ✅ 完成（ok / error **双模式**各 54 项 0 失败） |

#### ⚠️ 实施中抓到的第二个缺陷（原计划没有）

第一版把 `"totals": manager.web.speed_totals` 写进 status 字典、`ensure_group_state()` 仍留在 `**…` 展开位 ——
**字典字面量先求值**，读到的是上一轮的旧值：首次请求全 0，之后每轮慢一拍。是 F5-1 第一次跑红
（`{'dlspeed': 0} != {'dlspeed': 10000}`）把它顶出来的。修法：先 `group_state = manager.ensure_group_state(...)`
（它才触发视图发布），再拼 status 字典。
**判别法**（可推广）：凡是"状态字段取自另一处**惰性发布**的缓存"，取值的**调用顺序**就是正确性的一部分 ——
`**` 展开看着像"最后一步"，实际在字典字面量里是最后求值。

**红线**：`config.yml` / `auto-qb-data/` 不碰；`VIEW_ARRAYS` 不碰；`status_snapshot()` 不碰。

## 子任务状态表

| 子任务 | 判据 | 状态 |
|---|---|---|
| 复验（现象仍复现 + 锚点有效） | 桩服务 `view=torrent` 响应无 `groups` 键，真值非零 | ✅ 完成（2026-09-20 17:0x） |
| 深入分析（根因定位到符号级） | 链路 5 步全部落地到文件:行号 | ✅ 完成 |
| 修复计划产出 | `docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html` | ✅ 完成 |
| 实施 F1–F4 | 三处 curl 的 `totals` 相等且等于 `groups+singles` 真值 | ✅ 完成 |
| 守阵 F5-1 / F5-2 / F5-3 | 全量测试基线只增不减；冒烟 0 失败 | ✅ 完成（数字见下） |
| 真机走查 | 三个页签下状态栏数值一致且随传输变化 | ⬜ **待用户**（真实 qB 数据） |

## 进度日志

- **2026-09-20 16:46** — 用户报「WEBUI 状态栏上传/下载速度不更新永远显示 0」⇒ 按 create-issue 入池 `26-09-20-1646-bug-webui-statusbar-speed-always-zero`（bug / standard / Open）。取证只做静态代码阅读，根因留「待查」，记三条未验证假设。
- **2026-09-20 16:56** — 用户「认领，先深入分析，写一个修复计划」⇒ 状态置 `In Progress`（封面徽标 + meta 两处同改），索引重跑。
- **2026-09-20 17:0x** — 复验 + 分析：
  - 起桩 `--torrents 300`（150 组）：`view=group` 回 `groups`(150) 合计 15,206,400 / 45,926,400；`view=torrent` 响应键只有 `['rid','status','torrents','updated']`，**无 `groups`**，而 `torrents` 全量合计同为 15,206,400 ⇒ 前端在种子页只能算出 0。
  - 再起桩 `--groups 50`（50 组 + 200 未归组）：前端口径 1,723,392 / 5,068,800 vs 真值 15,206,400 / 45,926,400 ⇒ **少算 88.7% / 89.0%**（次因）。
  - 桩里 `status.server` 为 `null`（FakeClient 不提供 `server_state`）⇒ 候选 C 在 CI 内不可测，列为备选。
  - 根因定位：`VIEW_ARRAYS["torrent"] = ("torrents",)`（`mixins/web_view.py:48`）+ `app.js:883` 的「键不存在保留原引用」+ `decorate.js:136-141` 的 `totalDl/totalUl`。与 2026-09-19 的 BUG-8（追剧页成员索引被裁导致永久空白）同类。
- **2026-09-20 17:02** — 产出修复计划 `docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html`（dark 单文件 HTML，8 节）。**按范围守恒未动任何代码**，等用户确认后实施。
- **2026-09-20 17:2x** — 用户「实施」⇒ 落地 F1~F4 + 三条守阵，实测数字：
  - **桩服务**（`--torrents 300 --groups 50`）：`view=torrent` 的 `status.totals = {"dlspeed": 15206400, "upspeed": 45926400}`，与 `view=group` 一致，等于 `groups + singles` 真值（修复前种子页无此键、合计仅 1,723,392）。
  - **单测**：Windows **1059 → 1062 passed**（+3 新守阵）；WSL **1057 → 1060 passed + 2 skipped**（两侧收集数一致）。
    ⚠ WSL 重测踩到一个**测量陷阱**：仓库副本放在 `/tmp` 下会让 `test_sidefx.py` 的 2 条**假红**（同代码挪到 `~/` 即 0 failed），已记进 `testing.md`。
  - **浏览器冒烟**：双 UI **54 项 0 失败**（+2），新增断言实测 `totalDl=15206400 / DOM="14.50 MiB/s"`（prism 与 atlas 均 PASS）。
  - F5-2 红绿双验过：把 `totalDl` 改回 `this.groups.reduce` ⇒ 守阵立刻红并指名 issue 编号。
- **2026-09-20 17:4x** — 用户要求「用 agent-browser 做真浏览器测试」⇒ 端到端复测（桩服务 + 真 Chrome）：
  - 复现用户**确切场景**：`localStorage.autoqb.ui.view='torrents'` 后 reload，让首屏落在种子页。
    修复后状态栏 `14.50 MiB/s / 43.80 MiB/s`；**红验**（临时改回 `this.groups.reduce` + reload）⇒ `0 B/s / 0 B/s`，
    与用户报的「永远显示 0」逐字一致 ⇒ 真浏览器里闭环。
  - 三视图巡检数值一致（种子 / 辅种 / 追剧均为 14.50 MiB/s）；atlas 皮肤同样正确。
  - 截图存 `.workbuddy-ai/tmp/ab-shots/`。全量测试复跑 **1062 passed**。
  - 实施中额外抓到并修掉**第二个缺陷**（status 字典先求值导致 totals 慢一拍），详见「实现计划」下小节。
  - `yapf` 已跑；issue 状态 → `Fixed`，索引已重跑。
- 当前分支落后 `gitee/develop` 1 个提交（`4249dd5`，知识库文档回写，会与 `activeContext.md` 冲突）；工作区脏（本轮文档改动）⇒ 按「非快进 + 脏 = 必炸」的硬约束，等用户下「提交」触发词时走「先 commit → rebase → push」的顺序。

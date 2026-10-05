# 26-10-06-test-playwright-e2e — 把 Playwright 整合进项目: 修配置瑕疵 / 漂移 + 落地方案 A

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06
**Topics:** playwright-e2e
**Summary:** 把 scaffold 版 `@playwright/test` 落地成项目真冒烟（方案 A）: 修 CI 触发分支缺 `develop` 等 3 处配置瑕疵、`e2e/` 改指向 `ui_harness` 真前端（4 项: 渲染健康 + 数据契约）、修 `browser-env.md` / `ui_smoke.cjs` 的版本漂移、收录 `dev.e2e`；方案 B（迁移 1978 行 `ui_smoke.cjs`）入池不修。
**Refs:** memory-bank/pitfalls/testing/playwright-teardown.md

## 原始请求

> 验证此仓库中的 playwright 是否配置正确, 是否可用
> 分析此项目是否适合使用 playwright, 其作用是什么
> 修复配置瑕疵/飘移, 将 playwright 整合进项目, 先做 A, 将 B 入池

（第一轮为只读核查，结论：配置正确且可用 —— 三浏览器 6/6 全绿；第二轮为适配性分析；
本轮为执行：修瑕疵/漂移 + 方案 A + B 入池。**用户未说「提交」，故未 commit / push**。）

## 思考过程与决策

### 1. 三处配置瑕疵的定性与修法

| # | 瑕疵 | 取证 | 修法 |
|---|---|---|---|
| 1 | `.github/workflows/playwright.yml` 触发分支只有 `[main, master]`，而本仓库主线是 `develop`（既有 `ci.yml` 是 `[develop, master, main]`）⇒ **该 workflow 在日常分支上永不触发** | 读两个 workflow 文件对比 | 触发分支改 `[develop, master, main]`，补 `workflow_dispatch`；顺带只装 chromium（去掉 scaffold 的 firefox+webkit 三浏览器矩阵）、按 `ci.yml` 惯例固定 `setup-uv` 到 commit SHA、加 lockfile 前置判 |
| 2 | `package.json` 是 `"type": "commonjs"`，而 `playwright.config.js` / `e2e/*.spec.js` 用 ESM `import` | 当前能跑（Playwright 自行转译），属潜在不一致 | **不改根 `type`**（会连带把 `extensions/*.js` 按 ESM 解析 —— `tests/test_extension_proxy.py` 对它们跑 `node --check`），改走**显式扩展名**：`playwright.config.mjs` + `e2e/*.mjs`。仓库既有约定就是显式扩展名（`ui_smoke.cjs` 用 `.cjs` 正是同一原因） |
| 3 | `package.json` / `package-lock.json` / `playwright.config.js` / `e2e/` 全部未入库 ⇒ CI 里 `npm ci` 必失败 | `git status --short` | 文件已就绪并配好（含 `scripts`）；**入库要等一次显式「提交」** —— 本轮未提交 |

### 2. 方案 A 的落点：为什么 e2e 只跑 4 项

`e2e/` 的定位是**最小集**（每次改前端都该过一遍），不是替代 `ui_smoke.cjs`：

- 桩服务由 `playwright.config.mjs` 的 `webServer` 自动拉起（真 `create_app` + 合成种子），**不需要人工先起**；
- 端口定 **8137**（避开人工冒烟的惯用 8099 —— 多 clone 下极易撞残留 harness）；
- `reuseExistingServer: false`：**故意**不复用。复用会连上别的 clone 的残留服务，"全 PASS"验的是旧代码（`pitfalls/testing/smoke.md` 已记该假信心事故）；
- 只留 chromium；视口 1440x900 对齐 `ui_smoke.cjs`（版式/窗口化断言对宽度敏感）；
- 断言只钉"页面活没活 + 数据对不对"：`#app` 摘掉 `v-cloak`（Vue 挂载成功）、`.group-row` 渲染、跨一个轮询周期无 `pageerror`/`console.error`、`status.torrents == 桩种子数`。交互时序/几何/数值那四类深水区仍走 `ui_smoke.cjs`。

### 3. 排障实录（两条值得记的）

- **自踩 `js-comment-terminator`**：首版 spec 的 docblock 里写了"星号斜杠"那个符号组合，注释在第 12 行被提前砍断 ⇒ Playwright 报 `Invalid left-hand side in postfix operation` + `No tests found`。而该文件**不在** `test_web.py` 静态守阵的扫描范围（守阵只扫 `src/auto_qb/webui/static`）⇒ 静态全绿、只有真跑才现形 —— 恰好实证了这套 e2e 的存在价值。
- **webServer 收尾挂死**：用例 4/4 PASS 后命令永不退出、桩服务残留占 8137。读 playwright-core 源码定位到 `killProcess()` 用 `spawnSync('taskkill /pid <pid> /T /F', {shell:true})`，而本机 node 的 **`spawnSync` 只要带管道 stdio 就必 `EBUSY`**（`stdio:'ignore'` / `'inherit'` 正常；与可执行文件无关，连 node.exe 自己都一样；重试 5 次 + 延迟全 EBUSY，是**确定性**的不是竞态，也不是文件句柄/杀软占用）⇒ 失败被 try/catch 静默吞掉 ⇒ 管道关不掉 ⇒ `waitForCleanup` 永不 resolve。
  ⚠ **本会话首版结论「是工具 shell 的环境限制、配置层修不掉、只能在真实终端跑」已作废** —— 判据下得早（只测了一种带管道的调用形态），把"某条调用形态失败"升格成了"整个 API 不可用"。**已于 2026-10-06 05:5x 修复**（见下方进度日志），更正版根因与实测数据在 `pitfalls/testing/playwright-teardown.md`。

### 4. 一处回退（避免把猜测写成结论）

排障中途曾把 `HARNESS_CMD` 从 `uv run python …` 改成直接调 `.venv/Scripts/python.exe`（单进程），理由是"uv 会 fork 出子进程、杀不干净"。
**回退**：`spawnSync` 的 EBUSY 对两种写法同样成立，该改动**没有任何已验证的收益**，只是引入了分叉（平台路径逻辑 + 兜底分支）并偏离 `.commands/dev/config.toml` 的 `dev.harness` 单点。已改回 `uv run python`，并在注释里只写**已验证的机制**（`'close'` 事件依赖 stdio 管道全关；Windows 走 `taskkill /T`、非 Windows 走进程组 SIGKILL）与**仓库已记的事实**（`smoke.md` 的 uv 父子进程杀不干净），不写没验证过的因果。

## 实现计划

1. 修 `.github/workflows/playwright.yml`（触发分支 + dispatch + 只装 chromium + lockfile 前置判）
2. `playwright.config.js` → `playwright.config.mjs`（去 firefox/webkit；加 `baseURL` + `webServer` 指向 `ui_harness`）
3. `e2e/` 改指向真前端：新增 `harness.mjs`（参数单点）+ `smoke.spec.mjs`（双皮肤 × 渲染健康/数据契约），删 scaffold 的 `example.spec.js`
4. `package.json` 补 `scripts`（`test:e2e` / `test:e2e:headed` / `report:e2e`）
5. 修 `scripts/ui_smoke.cjs` 的依赖来源与版本对齐注释
6. 修 `memory-bank/testing/browser-env.md` 轨道二环境/版本漂移；修 `pitfalls/testing/smoke.md` 的 "本 clone 无 node_modules" 与 gitignore 口径
7. 收录 `dev.e2e`（commands 包）
8. 方案 B 入池（`refactor` / light）

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| S1 | 修 CI workflow 触发分支与流程 | Done |
| S2 | 统一模块类型（显式 `.mjs`）并重写 playwright 配置 | Done |
| S3 | `e2e/` 改指向 `ui_harness` 真前端 | Done |
| S4 | `package.json` 补 scripts | Done |
| S5 | `ui_smoke.cjs` 依赖来源/版本注释整合 | Done |
| S6 | 修 `browser-env.md` / `smoke.md` 文档漂移 | Done |
| S7 | 收录 `dev.e2e` | Done |
| S8 | 方案 B 入池 | Done |
| S9 | 收尾 DoD（切片 / 基线 / 索引） | Done |
| S10 | 修 webServer 收尾挂死（`e2e/global-teardown.mjs`）+ 更正首版误判 | Done |

## 进度日志

- **2026-10-06 04:2x** — 会话开工同步成功 `37c427fe`。核查既有 playwright 状态：`@playwright/test@1.63.0`、浏览器缓存与 `browsers.json` 完全对齐、三浏览器 6/6 全绿。
- **2026-10-06 04:31** — S1/S2/S3/S4 落地：workflow 重写、配置改 `.mjs` + webServer、新增 `harness.mjs` + `smoke.spec.mjs`、删 `example.spec.js`、`package.json` 补 scripts。
- **2026-10-06 04:3x** — 首跑失败：自踩 `js-comment-terminator`（docblock 里的星号斜杠把注释砍断）⇒ 改成文字表述后 4/4 PASS（2.9s / 56ms / 2.6s / 19ms）。
- **2026-10-06 04:4x** — 排查"PASS 后不退出"：定位到 `spawnSync` EBUSY（工具 shell 限制），记 `pitfalls/testing/playwright-teardown.md`；回退中途的 venv 解释器改动。
- **2026-10-06 04:58** — S8：方案 B 入池 `memory-bank/issues/26-10-06-0458-refactor-e2e-migrate-ui-smoke.html`（refactor / light / topic `playwright-e2e`）。
- **2026-10-06 05:0x** — S7：收录 `dev.e2e`（`timeout = 180`，`doc` 指向 playwright-teardown.md）。S6：`browser-env.md` 轨道二改为"仓库内 node_modules 优先 / NODE_PATH 回退"，修正 chromium 版本（151 → **153.0.8010.12**）与 WorkBuddy 路径结论；`smoke.md` 修正 `node_modules` gitignore 口径与来源优先级。
- **2026-10-06 05:1x** — S9：跑全量测试建基线、重建索引、写 activeContext 切片。
- **2026-10-06 05:2x** — 用户「提交」⇒ 首次 `ship.commit` 被**命令漂移闸门**拦下（新坑档/基线里写了 `npx playwright test` 原文，而它已收录为 `dev.e2e`）⇒ 改写成 task id 并重建索引后通过。为满足「TODO.md 不入库」用**子集提交**（位置参数），并先把 TODO.md `git stash` 挪开（否则脏树挡住内部 rebase），提交后 pop 还原。**提交成功 `e6db1fab`**，推送经 `ls-remote` 核实。
- **2026-10-06 05:4x** — 合并态补验：闸门跑在 rebase **之前**，故对合并后（含 9 个远端提交）的树补跑 `test.full` ⇒ **2662 passed + 4 skipped / 99%**，两次采样 64.45s / 72.45s；新增合并态基线切片 `26-10-06-0547`（用户指示「补一条合并态基线」，**尚未入库**）。
- **2026-10-06 06:1x** — 用户「提交」⇒ `ship.commit` 成功出 `94139d0f`，但**推送未完成**（远端已被别的会话推进，本地缺远端 tip 对象）⇒ 按失败行补跑 `ship.push`：fetch + rebase 到当时远端 tip `825e5221` ⇒ 重写为 **`2be3fe79`** 推成功，`git ls-remote` 核实远端 == 本地 HEAD。
  ⚠ **提交前发现仓库状态被并行会话改动**：HEAD 已从 `3a6e676c` 推进到 `c9ae4853`，且 `M TODO.md` 消失 —— 另一会话把 TODO.md 作为 `c9ae4853 更新TODO` **提交入库了**（此前用户要求过"TODO.md 不入库"，该约束已被覆盖）。因此本次是**全量提交**（树恰好只有我的 9 个文件），**不需要子集提交 + stash 舞蹈**。
  ⚠ **闸门跑在 rebase 之前**（提交先行的固有代价），并入的 `825e5221` 含 Python 生产代码 ⇒ 补跑合并态 `test.full` = **2676 passed + 4 skipped / 99% / 75.06s**，记新基线 `26-10-06-0619`。
- **2026-10-06 05:5x** — **S10：修 webServer 收尾挂死**（用户带来另一会话的 EBUSY 补充信息，据此重查）。**首版判据过窄**：`spawnSync` 并非全线坏，而是**只要带管道 stdio 就 EBUSY** —— `stdio:'ignore'`/`'inherit'` 正常（`status=0`），与可执行文件无关（连 `process.execPath` 即 node.exe 自己都一样），重试 5 次 + 延迟全 EBUSY ⇒ **确定性、非竞态、非文件句柄/杀软占用**。修法：新增 `e2e/global-teardown.mjs`（异步 `exec` + `netstat -ano` 取监听 PID + `taskkill /PID <pid> /T /F` + 轮询等端口释放；非 Windows no-op），`playwright.config.mjs` 挂 `globalTeardown`。顺序依据读 1.63 源码确认：`createGlobalSetupTasks` 把全局 teardown 任务排在 plugin setup **之后**、teardown 按注册**逆序**执行 ⇒ 本函数先于 webServer plugin 的 `killProcess()`，届时 `processClosed` 已 true、整段 force-kill 被跳过。**实测：`commands run dev.e2e` 14.8s / exit 0 / `4 passed (12.3s)`，8137 无 LISTENING、无残留 `ui_harness` 进程。** 另跑端口占用负例：exit 1 + `already used`、**外来服务不被误杀**（webServer setup 失败会中断任务链，`globalTeardown` 根本不被注册）。同步更正 `pitfalls/testing/playwright-teardown.md`（新增「别踩的坑」小节）、`dev.e2e` 的 note、`e2e/harness.mjs` 注释与本任务文件。（该轮改动已于 06:1x 提交为 **`2be3fe79`**。）

## 未做 / 留给用户

- **已提交并推送 `e6db1fab`**（用户显式「提交」，并明确要求 **TODO.md 不入库** —— 已用 `git show --name-only` 断言过）。
  推送经 `git ls-remote gitee refs/heads/develop` 核实 == 本地 HEAD。⇒ 三处瑕疵全部闭环。
- 合并态基线 `26-10-06-0547` **已随 `3a6e676c` 入库**（原记"尚未入库"于 2026-10-06 06:0x 复核更正）。
- **S10 已提交并推送 `2be3fe79`**（用户显式「提交」）：`e2e/global-teardown.mjs`(新) ·
  `playwright.config.mjs` · `e2e/harness.mjs` · `.commands/dev/config.toml`(note) ·
  `pitfalls/testing/playwright-teardown.md`(更正) + `_index.md` · 本任务文件 · activeContext 切片 ·
  新基线 `26-10-06-0605` —— **9 文件 / +180 −35**。
  提交链：`ship.commit` 出 `94139d0f`（此时远端已被别的会话推进，推送未完成）⇒ `ship.push`
  fetch+rebase 到当时远端 tip `825e5221` ⇒ 重写为 **`2be3fe79`** 推成功；
  `git ls-remote gitee refs/heads/develop` 核实远端 == 本地 HEAD。
  闸门跑在 rebase **之前** ⇒ 补跑合并态 `test.full` = **2676 passed + 4 skipped / 99% / 75.06s**
  （新基线 `26-10-06-0619`；+14 全部来自并入的 `825e5221`/`2119931d`，本次零 Python 改动）。
- **未提交（提交后回写 —— 提交 hash 只能在提交后才知道）**：本条更正 + 新基线 `26-10-06-0619` ⇒
  按本仓库惯例随下一次「提交」一并带上。
- ~~**本地在 AI 工具 shell 里跑 `dev.e2e` 会挂死**~~ —— **已修**（2026-10-06 05:5x，新增 `e2e/global-teardown.mjs` + 配置挂 `globalTeardown`）：工具 shell 里 `commands run dev.e2e` 实测 **14.8s / exit 0**、打印 `4 passed (12.3s)`、8137 无 `LISTENING`、无残留 `ui_harness` 进程。原记的"环境限制无法在配置层修掉"是**误判**，已在 `pitfalls/testing/playwright-teardown.md` 更正。
- 方案 B 不修，已入池。

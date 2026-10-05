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
- **webServer 收尾挂死**：用例 4/4 PASS 后命令永不退出、桩服务残留占 8137。读 playwright-core 源码定位到 `killProcess()` 用 `spawnSync('taskkill /pid <pid> /T /F', {shell:true})`，而本工具 shell 里 **`spawnSync` 全线 `EBUSY`**（连全路径 `taskkill.exe`、不带 shell 都一样）⇒ 失败被 try/catch 静默吞掉 ⇒ 管道关不掉 ⇒ `waitForCleanup` 永不 resolve。**是工具 shell 的环境限制，不是配置问题**（`spawn` 异步路径正常，所以起服务/浏览器/用例全不受影响）。已记 `pitfalls/testing/playwright-teardown.md`。

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

## 进度日志

- **2026-10-06 04:2x** — 会话开工同步成功 `37c427fe`。核查既有 playwright 状态：`@playwright/test@1.63.0`、浏览器缓存与 `browsers.json` 完全对齐、三浏览器 6/6 全绿。
- **2026-10-06 04:31** — S1/S2/S3/S4 落地：workflow 重写、配置改 `.mjs` + webServer、新增 `harness.mjs` + `smoke.spec.mjs`、删 `example.spec.js`、`package.json` 补 scripts。
- **2026-10-06 04:3x** — 首跑失败：自踩 `js-comment-terminator`（docblock 里的星号斜杠把注释砍断）⇒ 改成文字表述后 4/4 PASS（2.9s / 56ms / 2.6s / 19ms）。
- **2026-10-06 04:4x** — 排查"PASS 后不退出"：定位到 `spawnSync` EBUSY（工具 shell 限制），记 `pitfalls/testing/playwright-teardown.md`；回退中途的 venv 解释器改动。
- **2026-10-06 04:58** — S8：方案 B 入池 `memory-bank/issues/26-10-06-0458-refactor-e2e-migrate-ui-smoke.html`（refactor / light / topic `playwright-e2e`）。
- **2026-10-06 05:0x** — S7：收录 `dev.e2e`（`timeout = 180`，`doc` 指向 playwright-teardown.md）。S6：`browser-env.md` 轨道二改为"仓库内 node_modules 优先 / NODE_PATH 回退"，修正 chromium 版本（151 → **153.0.8010.12**）与 WorkBuddy 路径结论；`smoke.md` 修正 `node_modules` gitignore 口径与来源优先级。
- **2026-10-06 05:1x** — S9：跑全量测试建基线、重建索引、写 activeContext 切片。

## 未做 / 留给用户

- **未提交**（用户未说「提交」）⇒ 瑕疵 3（配套文件入库）仍未闭环；`git status` 里 `package.json` / `package-lock.json` / `playwright.config.mjs` / `e2e/` / `.github/workflows/playwright.yml` 待入库。
- **本地在 AI 工具 shell 里跑 `dev.e2e` 会挂死**（`spawnSync` EBUSY，见 `pitfalls/testing/playwright-teardown.md`）⇒ 请在自己的终端跑；这条环境限制无法在配置层修掉。
- 方案 B 不修，已入池。

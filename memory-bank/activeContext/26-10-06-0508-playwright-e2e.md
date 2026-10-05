# Playwright 整合进项目 — 方案 A 落地 (修配置瑕疵/漂移 + e2e 指向真前端)

> 摘要: 把 scaffold 版 `@playwright/test` 落地成项目真冒烟。修三处配置瑕疵(CI 触发分支缺 `develop` /
> 模块类型与扩展名不一致 / 配套文件未入库)、`e2e/` 改指向 `scripts/ui_harness.py` 真前端(双皮肤 ×
> 渲染健康 + 数据契约 共 4 项)、修 `browser-env.md` 与 `ui_smoke.cjs` 的版本漂移、收录 `dev.e2e`。
> 方案 B(迁移 1978 行 `ui_smoke.cjs`)入池不修。
> **已提交并推送 `e6db1fab`**(`git ls-remote` 核实远端 == 本地; 20 文件 +723 −31; TODO.md 按要求未入库)。
> 实测 e2e **4/4**; `test.full` 提交前 **2647 / 98%**(@ 37c427fe + 未提交)⇒ 合并态 **2662 / 99%**
> (基线 26-10-06-0508 / 26-10-06-0547); `test.pkg` **103 passed**。
> **05:5x 追加修复**: 原记的"`spawnSync` 全线 EBUSY ⇒ 环境限制、只能在真实终端跑"是**误判** —— 实为
> **只要带管道 stdio 就 EBUSY**(`ignore`/`inherit` 正常)。已新增 `e2e/global-teardown.mjs` 兜底,
> 工具 shell 里 `dev.e2e` **14.8s / exit 0**、`4 passed (12.3s)`、8137 无残留。
> **已提交并推送 `2be3fe79`**(9 文件 +180 −35; `git ls-remote` 核实远端 == 本地 HEAD)⇒ 合并态补验
> `test.full` **2676 + 4 / 99% / 75.06s**(基线 `26-10-06-0619`)。
> 最后活动: 2026-10-06 06:19

**Refs:** memory-bank/tasks/26-10-06-test-playwright-e2e.md, memory-bank/testing/baselines/26-10-06-0508-test-playwright-e2e.md, memory-bank/testing/baselines/26-10-06-0547-playwright-e2e-merged.md, memory-bank/testing/baselines/26-10-06-0605-playwright-e2e-teardown-fix.md, memory-bank/testing/baselines/26-10-06-0619-playwright-e2e-teardown-fix-merged.md

## 现状

- 改动面: `.github/workflows/playwright.yml`(触发分支 + dispatch + 只装 chromium + lockfile 前置判) ·
  `playwright.config.mjs`(新, 原 `.js` 删) · `e2e/harness.mjs`(新, 桩服务参数单点) ·
  `e2e/smoke.spec.mjs`(新, 4 项) · `package.json`(补 scripts) · `scripts/ui_smoke.cjs`(依赖来源 + 版本注释) ·
  `.commands/dev/config.toml`(`dev.e2e`) · `memory-bank/` 文档若干 + 新坑档 + 任务档案。
- **05:5x 新增, 已随 `2be3fe79` 入库**: `e2e/global-teardown.mjs`(Windows 收尾兜底) + `playwright.config.mjs` 挂
  `globalTeardown` + `e2e/harness.mjs` 注释 + `.commands/dev/config.toml` 的 `dev.e2e` note +
  `pitfalls/testing/playwright-teardown.md` 更正版。
- **已入库**: 上述改动随提交 `e6db1fab` 一并落盘(含 `package.json` / `package-lock.json` /
  `playwright.config.mjs` / `e2e/` / `.github/workflows/playwright.yml` —— CI 的 `npm ci` 依赖**已提交**的
  lock 文件, 这下才真正生效), 并已推 Gitee `develop`(远端 ref 经 `git ls-remote` 核实)。
- `TODO.md` 已被**并行会话**作为 `c9ae4853 更新TODO` 提交入库(原"用户要求不提交"的约束已失效);
  本次 `2be3fe79` 因此是**全量提交**, 不需要子集提交 + stash 舞蹈。

## 关键决策

- **根 `package.json` 的 `type` 保持 `commonjs`**, 改走显式扩展名(`.mjs` / `.cjs`)。改成 `module` 会连带把
  `extensions/*.js` 按 ESM 解析, 而 `tests/test_extension_proxy.py` 对它们跑 `node --check`。
- **e2e 只跑最小集**(渲染健康 + 数据契约), 交互时序/几何/数值四类深水区仍走 `scripts/ui_smoke.cjs`
  (105 项)。两条链路分工, 不互相替代。
- **端口 8137 + `reuseExistingServer: false`**: 故意不复用 —— 多 clone 下复用会连上别的 clone 的残留
  harness, "全 PASS"验的是旧代码(`pitfalls/testing/smoke.md` 已记该假信心事故)。
- **只留 chromium**: 内部工具, scaffold 的 firefox+webkit 三浏览器矩阵纯浪费 CI 时间。

## 未闭环 / 下次注意

- **已提交 `e6db1fab`** ⇒ 三处瑕疵全部闭环(原「未提交」条目已消解)。
- 合并态基线 `26-10-06-0547` **已随 `3a6e676c` 入库**(原记"尚未入库"已过期, 2026-10-06 06:0x 复核更正)。
- **本轮新增基线 `26-10-06-0605`**(2662 + 4 / 99%, 零 Python 改动 ⇒ 与 0547 数字一致, 已随 `2be3fe79` 入库)。
- **合并态基线 `26-10-06-0619`**(2676 + 4 / 99% —— 提交后 rebase 并入了别的会话的 `825e5221`/`2119931d`,
  +14 全来自它们; **未入库**, 随下次「提交」带上)。
- ~~**本工具 shell 里 `dev.e2e` 会挂死**~~ —— **已修并入库(`2be3fe79`)**。真因是 `spawnSync`
  **带管道 stdio** 必 `EBUSY`(`ignore`/`inherit` 正常), 而 Playwright 1.63 停 webServer 走的
  `spawnSync('taskkill …', {shell:true})` 正是默认管道 ⇒ 失败被静默吞掉 ⇒ `'close'` 不触发。
  新增 `e2e/global-teardown.mjs` 用**异步** taskkill 抢在 Playwright 之前杀进程树; 实测 **14.8s / exit 0**。
  根因与实测数据见 [pitfalls/testing/playwright-teardown.md](../pitfalls/testing/playwright-teardown.md)。
- 方案 B 已入池 `memory-bank/issues/26-10-06-0458-refactor-e2e-migrate-ui-smoke.html`(未认领)。
- 顺带修正的漂移: `browser-env.md` 的 chromium 版本(151 → **153.0.8010.12**)、WorkBuddy 路径"已失效"
  结论(2026-10-06 复核可用)、轨道一 `agent-browser` 当前不在 PATH; `baseline.md` 常驻警告的包内脚本
  测试条数(47 → **103**)。

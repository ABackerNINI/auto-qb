# 2647 —— Playwright 整合进项目 (方案 A: 修配置瑕疵/漂移 + e2e 指向真前端)

> 摘要: 把 scaffold 版 `@playwright/test` 落地成项目真冒烟 —— 修 CI 触发分支缺 `develop`、模块类型
> 与扩展名不一致、配套文件未入库三处配置瑕疵; `e2e/` 从"打外网 playwright.dev 的脚手架"改成
> "指向 `scripts/ui_harness.py` 真前端"（双皮肤 × 渲染健康 / 数据契约 共 4 项）; 修
> `memory-bank/testing/browser-env.md` 与 `scripts/ui_smoke.cjs` 的版本漂移; 收录 `dev.e2e`。
> 本轮**未增删任何 Python 用例**（改动面是 CI 配置 / e2e / 文档 / commands 包）。
> 实测 2647 passed + 4 skipped / 98% / 67.82s; e2e 4/4; test.pkg 103 passed。
> 基线时间: 2026-10-06 05:08

**Refs:** memory-bank/activeContext/26-10-06-0508-playwright-e2e.md

- 分支: develop @ 37c427fe (+ 本轮未提交改动: `.github/workflows/playwright.yml` ·
  `playwright.config.mjs`(新) · `e2e/harness.mjs`(新) · `e2e/smoke.spec.mjs`(新) ·
  `package.json` · `scripts/ui_smoke.cjs` · `.commands/dev/config.toml` · `memory-bank/` 若干文档)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2647 passed + 4 skipped, 覆盖率 TOTAL 98%**
  (15921 语句 / 170 未覆盖 / 5444 分支 / 144 partial; 门槛 98% 达标)
  —— 本轮两次采样 67.82s / 68.23s(引擎 69.6s / 70.0s) ⇒ 耗时区间约 **67~70s**。
- 相对上一条基线 [26-10-06-0412](26-10-06-0412-webui-settings-card-order.md)
  (2642 passed + 4 skipped @ f9a6d6ab + 未提交, 15916/167/5442/143): passed **+5**, 语句 15916 → 15921(+5),
  未覆盖 167 → 170(+3), 分支 5442 → 5444(+2), partial 143 → 144(+1)。
  ⚠ **这 +5 用例不是本轮改动带来的**: `f9a6d6ab..37c427fe` 之间有 3 个 commit
  (`b32bea2d` S3 批 webui/前端竞态与回执族四条 / `09162deb` 流量抽屉页面守卫 / `37c427fe` 设置页卡片重排),
  用例与源码增量来自它们。本轮**只碰配置 / e2e / 文档 / `.commands/` 包, 未增删任何 Python 用例** ⇒
  passed 相对 HEAD(37c427fe)不变。
- 靶向:
  - **e2e 真浏览器冒烟 4/4**(`commands run dev.e2e`, 桩服务由 `webServer` 自动拉起):
    prism 首屏渲染健康 2.8s + 数据契约 39ms / atlas 2.8s + 43ms(两次采样一致)。
  - `commands run test.pkg` → **103 passed in 134.05s**(改过 `.commands/dev/config.toml`, 包内脚本测试不在
    `testpaths(tests/)` 里, 全量测试收不到)。
  - `node --check` 逐个过 `playwright.config.mjs` / `e2e/harness.mjs` / `e2e/smoke.spec.mjs` / `scripts/ui_smoke.cjs`。
- 已知未闭环(与基线数字无关, 记在这里免得下次重复排查): 本工具 shell 里 `spawnSync` 全线 `EBUSY`,
  导致 Playwright **收尾**杀不掉桩服务 ⇒ 用例全 PASS 但命令永不退出、8137 残留占端口。
  属环境限制不是配置问题, 详见 [pitfalls/testing/playwright-teardown.md](../../pitfalls/testing/playwright-teardown.md)。

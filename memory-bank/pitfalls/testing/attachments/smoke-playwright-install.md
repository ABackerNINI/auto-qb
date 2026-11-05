# 浏览器冒烟 · Playwright 安装与报错错位(外迁)

> 摘要: `pitfalls/testing/smoke.md`「Playwright 从哪来」条的处置与复发现场原文外迁(2026-11-05 压缩), 正文原样照搬。
> 触发: Cannot find module playwright, ERR_MODULE_NOT_FOUND, @playwright/test, npm ci, NODE_PATH, chromium-1243

## 处置与复发

- **处置**: ①仓库内 `node_modules` 在(clone 后 `npm ci` / `npm i` 一次)⇒ `commands run dev.e2e` 直接可用,
  什么都不用设(`package.json` 列了 `@playwright/test@1.63` 作 devDependency, npm 解析不认 `NODE_PATH`);
  ②没有 node_modules 的 clone ⇒ `npm ci`(有 lock)或 `npm i`, **别走旧轨的 `NODE_PATH` 挂载**
  (❗ESM 的 `import` 不认 `NODE_PATH` —— 旧单页脚本是 CJS 才用得了它, e2e 轨道一律走 npm 解析);
  版本对齐 `@playwright/test@1.63` ↔ `chromium-1243`;
  换不到退回 `chromium.launch({channel:"msedge"})`(**Edge 恒可用**)。
  复发: 2 —— **新 clone 从未 npm i** 时跑 `commands run dev.e2e` 直接红: 报头先是一行无害的
  `npm warn exec The following package was not found and will be installed: playwright@1.64.1`,
  跟着 `Error [ERR_MODULE_NOT_FOUND]: Cannot find package '@playwright/test' imported from
  playwright.config.mjs` —— **npx 自作主张装的是 `playwright` 包, 不是配置要的 `@playwright/test`**,
  于是报错对象与真实病因(本 clone 没 node_modules)差了一层, 按报错去查依赖会查错方向。
  处置: 按 browser-env.md 的对齐口径 `npm i --no-save @playwright/test@1.63.0`(10s 内装完;
  `--no-save` 免改 `package.json`, 浏览器二进制复用 cache 里的 chromium-1243, 不必再 install)。
  判据: **新 clone / 换 clone 首次跑 e2e 前先 `ls node_modules | wc -l`, 0 即先 npm i** ——
  多 clone 工作区下 `node_modules/` gitignore, 跨 clone 同步走 Gitee 不会带上它, 每个 clone 各装一次。

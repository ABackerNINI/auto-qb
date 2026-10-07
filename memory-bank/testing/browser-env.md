# 浏览器自动化环境(两条轨道)

> 摘要: 浏览器断言走哪条轨道、浏览器装在哪、版本怎么对齐、换机器怎么一条命令自检 —— 环境侧的全部事实。
> 触发: 浏览器, 冒烟环境, agent-browser, Playwright, e2e, chromium, npm ci, 浏览器版本, 换机器自检

> **轨道政策: WEB UI 浏览器断言只有一条轨道 —— `e2e/`(@playwright/test), 见「轨道二」;**
> `agent-browser` 降级为**人工开页 / 快速看渲染**的辅助工具, 不承载断言。
> 两条轨道的浏览器**各自独立**(agent-browser 用自己下的 Chrome 153, e2e 轨道用 ms-playwright 的
> `chromium-1243` = **Chrome 153.0.8010.12**, 2026-10-06 实测), 互不干扰。
> ⚠ **2026-10-06 复核: 轨道一本机不可用** —— `which agent-browser` 无输出, 且下面记的 npm 全局
> prefix 目录已从 `...\versions\22.22.2-2` 变为 `22.22.2-3`(该目录下没有 agent-browser),
> `npm prefix -g` 现为 `C:\Users\11059\AppData\Roaming\npm` 其中也没有 ⇒ 要用得先重装。
> 「断言怎么跑 / 断言设计坑」见 [smoke.md](smoke.md)。

## 轨道一(辅助, 非断言): `agent-browser` —— 本机要先重装才可用

- **状态**: 插件已更新到 **1.3.0**(`installed_plugins.json` 的 `installPath` 指向 1.3.0), CLI 与 Chromium 已装并跑通(2026-09-20)。
  历史: 1.0.0 的 `SessionStart` hook 判到 `WINDIR` 就打印「不支持 Windows」并 `exit 0` ——
  那是**旧版本的门控**, 1.3.0 没有这个 hook, **别再拿那句输出当结论**。
- **版本与路径**: CLI `agent-browser` **0.27.0**(npm 全局, prefix = `...\binaries\node\versions\22.22.2-2`);
  ❗**2026-10-06 复核: 该 prefix 目录已不存在**(现为 `22.22.2-3`, 其中也没有 agent-browser;
  `npm prefix -g` 现为 `C:\Users\11059\AppData\Roaming\npm`, 同样没有) ⇒ 本轨道**要先重装才可用**;
  浏览器 Chrome **153.0.8010.52** 在 `~/.agent-browser/browsers/`。
- **最小可用序列**(实测: 打开本项目桩服务的 Vue 页面):
  ```powershell
  agent-browser open "http://127.0.0.1:8099/atlas/"   # 7s 返回, 标题「auto-qb · 辅种管理 · 星图」
  agent-browser snapshot                              # 完整无障碍树(导航/搜索框/添加种子/设置)
  agent-browser screenshot <path>                     # 出图 96 KB
  agent-browser close                                 # exit 0, 无残留进程
  ```
  能拿到渲染后的标题 ⇒ **JS 真的执行了**, 不是空壳 HTML。
- **新机器首次启用**: `npm install -g agent-browser` + `agent-browser install`(约 196 MB)。
- **前提**: Windows 11 x64(Build 26200)/ 终端 5.1 / npm 在 PATH /
  PATH 上的 node **能真正执行**(`node -e "console.log('ok')"` —— **只打印版本号不算**)。

### 三个坑(第一次用时白等了 12 分钟)

1. **别把输出接 `Select-Object -Last N`** —— 它会**缓冲到命令结束**才吐字, 看上去活像卡死
   (当时真正的卡点是第 2 条, 被这个缓冲遮住了)。
2. **`wait` 在轮询型页面上不返回**: 本项目 UI 每 1.5s 轮询 `/api/state`, `networkidle` **永不触发**,
   `wait --load load` 实测也不返回 ⇒ **`open` 之后直接 `snapshot`, 不要等**。
3. 若 daemon 静默崩(无任何输出), 先查头号嫌疑: PATH 上的 node 是否真能执行
   (本机 `where node` 两个都通过实测 ⇒ 排除; SIGILL / Exit 133 那条不适用)。

## 轨道二(断言单点): Playwright e2e `e2e/`(@playwright/test)

- **何时用**: 一切 WEB UI 浏览器断言 —— 旧单页冒烟脚本已于 2026-10-06 随迁移计划
  26-10-06-0708 退役, `e2e/` 是唯一轨道(八个 spec 按断言块拆分, 双皮肤, 模式矩阵 env 参数化)。
- **命令**: 桩服务(`scripts/ui_harness.py`)由 `playwright.config.mjs` 的 `webServer` **自动起停**
  (端口 8137, `reuseExistingServer: false`), 不需要人工先起、也不需要人工关:
  ```bash
  commands run dev.e2e      # 全量集(八个 spec × prism/atlas 双皮肤)
  npm run test:e2e:fast     # @fast 门禁子集(分钟级) —— 「每次改前端」的日常口径
  npm run test:e2e:headed   # 有头模式(人工看动作)
  ```
  模式矩阵轮(`E2E_CMD_RESULT / E2E_SKIP_CHECK / E2E_HR_SCENE / E2E_TORRENTS`)是**串行人跑**,
  六行命令见 `.commands/dev/config.toml` 的 `dev.e2e` note。
- **环境(2026-10-06 实测)**: 依赖 = `package.json` devDependency `@playwright/test@^1.63.0`,
  clone 后 `npm ci`(有 lock)或 `npm i` 一次即可; 旧轨的「仓库外 `npm i playwright-core` +
  `NODE_PATH` 挂载」方案随脚本退役**作废**(ESM `import` 本就不认 `NODE_PATH`)。
  浏览器在 `C:/Users/11059/AppData/Local/ms-playwright/`, 现存 **`chromium-1243` /
  `chromium_headless_shell-1243`**(`chromium-1234` 及其 headless shell 已不在)。
- **版本对齐**: **`@playwright/test 1.63` ↔ `chromium-1243`(= Chrome 153.0.8010.12)实测可用**
  (2026-10-06); 历史配对: core 1.62 ↔ `chromium-1234`。装了新包却没下对应浏览器会报
  `Executable doesn't exist` —— `npx playwright install chromium` 补浏览器(只装 chromium)。
- **Python 版没装**: `.venv` / `uv.lock` 里都没有。要在 pytest 里直接驱动浏览器才需要
  `uv add --dev playwright` + `uv run playwright install chromium`
  (**会改 `pyproject.toml` / `uv.lock`, 动之前先问**)。
- **自检(换机器后一条命令)**:
  ```bash
  node -e "require('playwright-core').chromium.launch().then(b=>{console.log(b.version());return b.close()})"
  # 没有 node_modules 的 clone 在 node 前加: NODE_PATH=<装了 playwright-core 的 node_modules>
  ```
  输出判定: 打出 Chromium 版本号(本机现为 `153.0.8010.12`)⇒ 可用; `Cannot find module 'playwright-core'`
  ⇒ 包没了(本 clone 没 `npm i`, 或 NODE_PATH 指向的目录被清 / 路径变了);
  `Executable doesn't exist` ⇒ 浏览器没下载。
  ❗给**轨道一**补浏览器必须用 `agent-browser install`, **别用 `npx playwright install` 顶替** ——
  会拉下与它不匹配的版本。

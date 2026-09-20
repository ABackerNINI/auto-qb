# Tech Context — 技术栈与开发环境

> Memory Bank 核心文件之一: 使用的技术、开发环境、技术约束与依赖。测试命令与基线详见 [testing.md](testing.md); 约束背后的"为什么"见 [systemPatterns.md](systemPatterns.md) 与 [pitfalls.md](pitfalls.md)。

## 技术栈

- **语言**: Python 3.12+ (CI 矩阵 3.12 / 3.13)
- **核心依赖**: `qbittorrent-api` (qB WebUI 客户端), `filelock` (单实例锁), `PyYAML` (配置解析, `yaml.BaseLoader` 全字符串)
- **托盘/GUI** (仅 `--tray` 分支加载): `customtkinter` + `pystray` + `Pillow`
- **WEB UI**: `web.py` (FastAPI 栈) + `web_ui/static` 手写 HTML/CSS/JS；2026-09-15 起双界面目录化并存：星图 `web_ui/static/atlas/`（旧·经典深色单主题）与棱镜 `web_ui/static/prism/`（新·CSS 令牌分层 `tokens/themes/base/components/views` + `js/theme.js` 主题引擎，5 套主题），目录即 URL（`/atlas/`、`/prism/`；`/` 307→默认星图，`/newui/*` 307→`/prism/*` 书签兼容），共享逻辑层三件套 + vendor + 图标单一来源收在 `web_ui/static/shared/`
- **桌面通知**: `notify.py` 零第三方依赖 (win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript)
- **格式化**: yapf (`.style.yapf`: facebook 风格, 列宽 120)

## 开发环境

- 依赖管理: **uv** (2026-09-15 起, pyproject.toml PEP 621 + uv.lock 全量锁; Windows `winget install astral-sh.uv`); `uv sync` 重建 .venv 并把项目 editable 安装; 入口脚本 `auto-qb` = `auto_qb.cli:main`
- 直接依赖 12 个全部 `==` 精确锁定 (升级时改 pyproject 再 `uv lock --upgrade`); 打包后端 hatchling, `uv build` 可出 sdist/wheel
- 入口: `uv run python src/auto-qb.py [config.yml]`; 干跑 `--dry-run`; 托盘 `--tray` (源码入口与 `uv run auto-qb` 等价)
- 测试: `uv run pytest tests -q` (pytest.ini 自带 `--cov-branch` 分支覆盖率; CI 用 astral-sh/setup-uv 固定 commit SHA (v10.1.0) + uv sync —— 该 action 已不发布 `v10` 浮动大版本标签, 只能写 `@v10.1.0` 或 SHA, 写 `@v10` 会报 "unable to find version v10")
- 历史: 2026-09-15 前用 pip 直装 .venv (无锁), requirements-dev.txt 已由 pyproject 取代 (随 e7fb8d9 删除)

## 浏览器自动化环境(两条轨道 · 2026-09-20 实测)

> **选用政策: 优先 `agent-browser`; 它不可用才回退 Playwright 冒烟。**
> 判「不可用」的硬判据(任一命中即回退): ①`agent-browser` 不在 PATH, 且 `npm install -g agent-browser`
> 装不上; ②`agent-browser open` 起不来 daemon(超 60s 无返回, 且已用 `node -e` 排除 Node 本身崩);
> ③要跑的是 `scripts/ui_smoke.cjs` 那 54 项**数值断言**(只有 Playwright 轨道有)。
> 两条轨道的浏览器**各自独立**(agent-browser 用自己下的 Chrome 153, Playwright 用 ms-playwright 的
> chromium 151), 互不干扰。「冒烟共多少项 / 读数时机坑」见 [testing.md](testing.md)。

### 轨道一(首选): agent-browser 1.3.0 —— 已实测可用

- **状态**: 插件已更新到 **1.3.0**(`installed_plugins.json` 的 `installPath` 指向 1.3.0), CLI 与 Chromium
  已装并跑通(2026-09-20)。历史: 1.0.0 的 `SessionStart` hook 判到 `WINDIR` 就打印「不支持 Windows」并
  `exit 0` —— 那是**旧版本的门控**, 1.3.0 没有这个 hook, 别再拿那句输出当结论。
- **版本与路径**: CLI `agent-browser` **0.27.0**(npm 全局, prefix = `...\binaries\node\versions\22.22.2-2`);
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
- **前提**: Windows 11 x64 (Build 26200) / 终端 5.1 / npm 在 PATH / PATH 上的 node **能真正执行**
  (`node -e "console.log('ok')"` —— 只打印版本号不算)。

#### 三个坑(第一次用时白等了 12 分钟)

1. **别把输出接 `Select-Object -Last N`** —— 它会**缓冲到命令结束**才吐字, 看上去活像卡死
   (当时真正的卡点是第 2 条, 被这个缓冲遮住了)。
2. **`wait` 在轮询型页面上不返回**: 本项目 UI 每 1.5s 轮询 `/api/state`, `networkidle` 永不触发,
   `wait --load load` 实测也不返回 ⇒ **`open` 之后直接 `snapshot`**, 不要等。
3. 若 daemon 静默崩(无任何输出), 先查 skill 故障手册的头号嫌疑: PATH 上的 node 是否真能执行
   (本机 `where node` 两个都通过实测 ⇒ 排除; SIGILL / Exit 133 那条不适用)。

### 轨道二(回退): Playwright 冒烟 `scripts/ui_smoke.cjs`

- **何时用**: agent-browser 命中上面任一回退判据; 或需要那 **54 项数值断言**(双 UI × ok/error/hang 三模式)。
- **命令**(**必须带 `NODE_PATH`**, 否则 `require()` 找不到包):
  ```bash
  NODE_PATH="C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules" \
    node scripts/ui_smoke.cjs --base http://127.0.0.1:8099 --torrents 3000
  ```
- **环境**: 包装在 WorkBuddy 托管目录(**不是项目依赖**, 不在 `package.json` 里)
  `C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules` —— `playwright@1.63.0` 与
  `playwright-core@1.62.0`; 浏览器在 `C:/Users/11059/AppData/Local/ms-playwright/`(`chromium-1234` /
  `chromium-1243` 及对应 headless shell), 实测走 `chromium-1234/chrome-win64/chrome.exe`,
  Chromium **151.0.7922.34**。
- **版本对齐**: 用 `playwright-core`(脚本里就是 `try require("playwright-core") catch require("playwright")`)
  —— core 1.62 ↔ `chromium-1234`, 顶层 1.63 要 `chromium-1243`; 装了新包却没下对应浏览器会报
  `Executable doesn't exist`。
- **Python 版没装**: `.venv` / `uv.lock` 里都没有。要在 pytest 里直接驱动浏览器才需要
  `uv add --dev playwright` + `uv run playwright install chromium`(会改 `pyproject.toml` / `uv.lock`, 动之前先问)。
- **自检**(换机器后一条命令):
  ```bash
  NODE_PATH="C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules" \
    node -e "require('playwright-core').chromium.launch().then(b=>{console.log(b.version());return b.close()})"
  ```
  输出判定: 打出 Chromium 版本号 ⇒ 可用; `Cannot find module 'playwright-core'` ⇒ 包没了(托管目录被清
  或路径变了); `Executable doesn't exist` ⇒ 浏览器没下载。❗给**轨道一**补浏览器必须用
  `agent-browser install`, 别用 `npx playwright install` 顶替 —— 会拉下与它不匹配的版本。

## 平台

- **运行主平台 Windows**; GitHub Actions CI 在 Linux 上跑全量测试
- 平台相关测试必须 `monkeypatch` 固定 `sys.platform`, 不依赖运行环境 (见 [testing.md](testing.md))
- Windows 磁盘文件检查走 `utils.add_long_path_prefix_for_win` (`\\?\` 长路径前缀)

## 关键技术约束

- **单一写线程**: 只有主循环线程修改任务队列结构与 state_file
- **状态落盘时机**: 跨轮次状态统一进 state_file, 程序退出时才写盘
- **qB 5.0+ API 语义**: sync/maindata 增量响应、`transfer_*` 限速端点、`TorrentState` 枚举判定 (细节见 [pitfalls.md](pitfalls.md))
- **fail-fast**: 配置全量校验后代码假定配置正确, 不做防御性检查
- **本地 qB 网络**: `qbmanager._new_client()` 对本地地址强制 `trust_env=False` (LocalQbClient), 远程域名保留默认

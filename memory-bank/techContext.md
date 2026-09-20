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

## 浏览器冒烟环境 (Playwright)

> 浏览器驱动的**唯一**入口是 `scripts/ui_smoke.cjs`(配 `scripts/ui_harness.py` 桩服务)。**怎么用冒烟、共多少项、读数时机坑**见 [testing.md](testing.md)「浏览器冒烟已脚本化」; 本节只记**环境事实**(装在哪 / 怎么跑起来 / 怎么自检), 免得下次靠猜。

**结论: 本机可直接用, 不需要安装** (2026-09-20 实测)。

- **Node 侧已就绪** —— 注意它**不是项目依赖**, 装在 WorkBuddy 托管目录(不在仓库里, 也不在 `package.json` 里):
  - 包: `playwright@1.63.0` 与 `playwright-core@1.62.0`, 位于
    `C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules`
  - 浏览器: `C:/Users/11059/AppData/Local/ms-playwright/` 下有 `chromium-1234` / `chromium-1243`
    及对应 headless shell 与 ffmpeg; 实测走的是 `chromium-1234/chrome-win64/chrome.exe`,
    Chromium 版本 **151.0.7922.34**
- **Python 侧没装**: `.venv` 与 `uv.lock` 里都没有 playwright。想在 pytest 里直接驱动浏览器才需要
  `uv add --dev playwright` + `uv run playwright install chromium` —— 那会改 `pyproject.toml` / `uv.lock`
  (提交级改动, 动之前先问)。**当前不需要**: 冒烟是 Node 脚本, 与 Python 环境无关。

### 跑起来的两条硬要求(都踩过)

1. **必须带 `NODE_PATH`**, 否则 `require()` 找不到包:
   ```bash
   NODE_PATH="C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules" \
     node scripts/ui_smoke.cjs --base http://127.0.0.1:8099 --torrents 3000
   ```
2. **优先 `playwright-core`, 而不是顶层 `playwright`** —— 脚本里就是 `try require("playwright-core")
   catch require("playwright")`。原因: **版本要和已下载的 chromium 对齐**, core 1.62 ↔ `chromium-1234`,
   而顶层 1.63 要 `chromium-1243`; 装了新包却没下对应浏览器时会报 `Executable doesn't exist`。

### 与 `agent-browser` 的关系(2026-09-20 **重新核实**, 此前记错了)

❗**"agent-browser 不支持 Windows"是 1.0.0 的旧结论, 不是产品限制**。核到的事实:

- **会话里那句提示的来源**: 插件 `1.0.0` 带一个 `SessionStart` hook(`scripts/setup.sh`), 它一上来就判
  `OSTYPE == msys/cygwin` 或 `WINDIR` 非空 ⇒ 打印「⚠️ agent-browser 目前不支持 Windows 系统」并 `exit 0`,
  **连 CLI 都没装**(所以 PATH 上没有 `agent-browser`)。
- **新版本支持 Windows**: 插件缓存里已经有 `1.3.0`
  (`~/.workbuddy-ai/plugins/cache/codebuddy-plugins-official/agent-browser/1.3.0/`), 它的 `SKILL.md` 明写
  supports **macOS / Linux / Windows x64**(目标环境 Windows 11 x64 + PowerShell + Node 18+), 另有
  `references/windows-support.md`, 且**没有那个平台门控 hook**。
- **当前启用的是旧版**: `~/.workbuddy-ai/plugins/installed_plugins.json` 里 `installPath` 指向 **1.0.0**
  ⇒ 要真正启用 Windows 支持, 得先把插件**更新到 1.3.0**(应用侧动作, 在插件管理里做), 再
  `npm install -g agent-browser` + `agent-browser install`(约 500 MB Chromium)。
- **本机前提全部满足**: Windows 11 专业版 x64 (Build 26200) / PowerShell 5.1 / `node -e` 能实际执行
  (v22.22.2) / npm 在 PATH —— 1.3.0 的 Windows 前提没有一条卡住。

与本项目冒烟的关系: 冒烟走的是 **Playwright**(`scripts/ui_smoke.cjs`), 不依赖 agent-browser, 两者不冲突;
`scripts/ui_harness.py` 头部那句「agent-browser 在 Windows 上不可用」是 1.0.0 时代写的, 现已过时
(**未按范围守恒擅自改**, 要改单独说)。

### 换机器 / 重装后怎么自检(一条命令)

```bash
NODE_PATH="C:/Users/11059/.workbuddy-ai/binaries/node/workspace/node_modules" \
  node -e "require('playwright-core').chromium.launch().then(b=>{console.log(b.version());return b.close()})"
```

- 打印出 Chromium 版本号 ⇒ 环境可用
- `Cannot find module 'playwright-core'` ⇒ 包没了(托管目录被清 / 路径变了)
- `Executable doesn't exist` ⇒ 浏览器没下载, 跑 `npx playwright install chromium`

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

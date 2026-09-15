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
- 测试: `uv run pytest tests -q` (pytest.ini 自带 `--cov-branch` 分支覆盖率; CI 用 astral-sh/setup-uv@v10 + uv sync)
- 历史: 2026-09-15 前用 pip 直装 .venv (无锁), requirements-dev.txt 已由 pyproject 取代 (随 e7fb8d9 删除)

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

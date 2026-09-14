# Tech Context — 技术栈与开发环境

> Memory Bank 核心文件之一: 使用的技术、开发环境、技术约束与依赖。测试命令与基线详见 [testing.md](testing.md); 约束背后的"为什么"见 [systemPatterns.md](systemPatterns.md) 与 [pitfalls.md](pitfalls.md)。

## 技术栈

- **语言**: Python 3.12+ (CI 矩阵 3.12 / 3.13)
- **核心依赖**: `qbittorrent-api` (qB WebUI 客户端), `filelock` (单实例锁), `PyYAML` (配置解析, `yaml.BaseLoader` 全字符串)
- **托盘/GUI** (仅 `--tray` 分支加载): `customtkinter` + `pystray` + `Pillow`
- **WEB UI**: `web.py` (FastAPI 栈) + `web_ui/static` 手写 HTML/CSS/JS
- **桌面通知**: `notify.py` 零第三方依赖 (win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript)
- **格式化**: yapf (`.style.yapf`: facebook 风格, 列宽 120)

## 开发环境

- 项目 venv: `.venv` (Windows, Python 3.12); 无包管理配置, pip 装依赖即用
- 入口: `python src/auto-qb.py [config.yml]`; 干跑 `--dry-run`; 托盘 `--tray`
- 测试: `.venv/Scripts/python.exe -m pytest tests -q` (pytest.ini 自带 `--cov-branch` 分支覆盖率; Linux CI 直接 `python -m pytest`)

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

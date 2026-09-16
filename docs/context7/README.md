# Context7 API 文档快照

> 通过 [Context7 MCP](https://context7.com) 抓取的、本项目直接依赖的库 API 文档快照。
> 抓取日期：2026-09-17。文件名含项目 `pyproject.toml` 锁定的**精确版本号**。
> 说明：Context7 返回的是「按查询抽取的文档片段」而非整本手册，适合速查 API 用法与签名；完整文档请点每文件内 "Source" 链接跳官方站点。

## 目录

| 库 | 锁定版本 | 文件 | 用途（本项目） |
|----|----------|------|----------------|
| [qbittorrent-api](https://qbittorrent-api.readthedocs.io) | 2026.8.1 | [qbittorrent-api-2026.8.1.md](qbittorrent-api-2026.8.1.md) | qBittorrent WebUI 客户端：登录、种子管理、分类、应用偏好（`src/auto_qb/qbclient.py`） |
| [FastAPI](https://fastapi.tiangolo.com) | 0.141.1 | [fastapi-0.141.1.md](fastapi-0.141.1.md) | Web UI 后端：路由、请求体模型、静态文件（`src/auto_qb/web_commands.py` 等） |
| [uvicorn](https://uvicorn.dev) | 0.53.0 | [uvicorn-0.53.0.md](uvicorn-0.53.0.md) | ASGI 服务器：启动 Web UI 服务 |
| [httpx](https://github.com/encode/httpx) | 0.28.1 | [httpx-0.28.1.md](httpx-0.28.1.md) | HTTP 客户端：PT 站点 API 访问、异步请求 |
| [PyYAML](https://pyyaml.org) | 6.0.3 | [pyyaml-6.0.3.md](pyyaml-6.0.3.md) | YAML 解析/序列化：配置加载、`yaml.safe_load` |
| [ruamel.yaml](https://yaml.readthedocs.io) | 0.19.1 | [ruamel.yaml-0.19.1.md](ruamel.yaml-0.19.1.md) | YAML round-trip：保留注释/格式回写配置文件 |
| [Pillow](https://python-pillow.org) | 12.3.0 | [pillow-12.3.0.md](pillow-12.3.0.md) | 图像处理：图标/截图生成（Web UI、托盘图标） |
| [customtkinter](https://github.com/tomschimansky/customtkinter) | 6.0.0 | [customtkinter-6.0.0.md](customtkinter-6.0.0.md) | 桌面 GUI：系统托盘/窗口控件 |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | [pystray-0.19.5.md](pystray-0.19.5.md) | 系统托盘图标：菜单、通知 |
| [filelock](https://github.com/tox-dev/filelock) | 3.32.6 | [filelock-3.32.6.md](filelock-3.32.6.md) | 跨平台文件锁：单实例锁、数据目录并发保护 |

## 刷新方式

```bash
# 依赖版本变更或需更新文档时，用 Context7 MCP 重新抓取并覆盖对应文件
# 每个文件可运行后重建本索引（保持文件名含精确版本号）
```

> 依赖清单见根目录 [pyproject.toml](../../pyproject.toml) `dependencies` 字段。
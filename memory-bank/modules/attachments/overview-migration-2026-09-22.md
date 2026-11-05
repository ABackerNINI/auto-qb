# 迁移映射存档（2026-09-22 方案 C）

> 摘要: 2026-09-22 目录迁移的旧→新映射, 从 overview.md 外迁留痕。
> 触发: 历史路径, 方案 C, 迁移映射, 旧根平铺, mixins 去向

旧路径均为迁移前状态, 现行代码不再存在这些位置; 仅供读旧文档/旧提交时对照。

| 旧 | 新 |
|----|----|
| `qbmanager.py` / `taskqueue.py` / `qbapi.py` / `qbclient.py` / `curves.py` / `episodes.py` / `tvshows.py` / `exporter.py` | `core/` 同名 |
| `mixins/`（rule_engine / tags / checking / grouping / tracker / speed_curve; 新增 ops 危险操作层） | P0-P5 已再迁 `core/modules/` 功能模块(见 plan 26-09-30-1819); 过渡包 `core/mixins/` 已随审计 L1-L3 清扫整体删除(2026-10-01) —— webui 两表现层 mixin 由 qbmanager 直接 import `webui/views`·`webui/commands` |
| `mixins/web_view.py` / `mixins/web_commands.py` | `webui/views.py` / `webui/commands.py`（W3 先行迁出） |
| `errors.py` / `locking.py` / `logging.py` / `utils.py` / `notify.py` / `autostart.py` | `infra/` 同名 |
| `web_runtime.py` | `webui/runtime.py` |
| `web/`（HTTP 层） | `webui/server/` + `webui/server/routes/` |
| `web_ui/static/` | `webui/static/` |
| `ui.py` | `tray/app.py` |

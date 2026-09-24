# 包入口与「在哪里改」速查

> 📅 **内容基线**: 2026-09-05 @ `51374bd`(全库逐文件核实, 见本库 [README.md](../README.md));
> 文内带日期的条目为**增量更新**, 最新易变状态见 [activeContext.md](../activeContext.md)。
> 行数为 2026-09-05 快照。所有路径相对 `src/auto_qb/`(除注明)。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**(plan memory-bank/plans/26-09-22-2112): 本文与库内其它模块文档的
> 单文件路径为迁移前快照, 速查表与迁移映射表已更新; 新结构 = 根目录只剩 cli.py + 分层/域包
> (config / core / infra / rules / torrents / webui / tray), 旧根平铺文件与 mixins/ 的去向见下方映射表。

> 摘要: 包入口在哪、要改某功能该动哪个文件 —— 进本目录前先读这一份。
> 触发: 包入口, 在哪里改, 改哪个文件, 入口, src 布局

## 包入口

| 文件 | 行数 | 职责 |
|------|------|------|
| `../auto-qb.py` | 8 | 兼容入口: `python src/auto-qb.py` → `cli.main` |
| `__init__.py` | 23 | 导出 Config/QbManager/load_config, `__version__="0.2.0"` |
| `__main__.py` | 5 | `python -m auto_qb` 入口 |

## 迁移映射 (2026-09-22 方案 C, 旧路径 → 新路径)

| 旧 | 新 |
|----|----|
| `qbmanager.py` / `taskqueue.py` / `qbapi.py` / `qbclient.py` / `curves.py` / `episodes.py` / `tvshows.py` / `exporter.py` | `core/` 同名 |
| `mixins/`（rule_engine / tags / checking / grouping / tracker / speed_curve） | `core/mixins/` |
| `mixins/web_view.py` / `mixins/web_commands.py` | `webui/views.py` / `webui/commands.py`（W3 先行迁出） |
| `errors.py` / `locking.py` / `logging.py` / `utils.py` / `notify.py` / `autostart.py` | `infra/` 同名 |
| `web_runtime.py` | `webui/runtime.py` |
| `web/`（HTTP 层 16 文件） | `webui/server/` |
| `web_ui/static/` | `webui/static/` |
| `ui.py` | `tray/app.py` |

## 常用"在哪里改"速查

| 需求 | 位置 |
|------|------|
| 新配置键 | `config/models.py` (dataclass 字段+默认值) + `config/loaders.py` (load 函数) + `config/validation.py` (校验+KNOWN 键); 如属 tracker 级加进 `load_tracker_config` |
| 新规则条件 | `rules/conditions.py` 写类 + `@register_condition` (装饰即注册, import 已在 `rules/__init__.py`), 并在 `config/validation.py` 加 spec 校验 |
| 新规则动作 | `rules/actions/` 对应职责模块写类 + `@register_action`, 并在 `actions/__init__.py` import(否则不注册), 并在 `config/validation.py` 加 spec 校验; 需要新变量替换则扩展 `utils.replace_vars` |
| 新集数命名模式 | `core/episodes.py` `_EPISODE_PATTERNS` 列表按优先级插入 |
| 新流量数据源 | `core/curves.py` 加解析 + `core/mixins/speed_curve.py`/`config/validation.py` 扩展 traffic_source 校验 |
| 新全局周期任务 | `core/qbmanager.py` `_create_global_tasks` 加 Task |
| 新种子级内置任务 | `core/qbmanager.py` `_create_torrent_tasks` + handler |
| **HR 在线核实**(取 HR 统计页 / 对账建索引 / 三态判定) | `hr/`(新包): `bencode` infohash · `parse` 表格抽取 · `adapters/` 站点隔离(现只有 NexusPHP `myhr.php`) · `store` 站点文件 + 每站点锁 · `ratelimit` 频控 · `resolve` 三态与收口判定(`judge_record` / `HrJudgement`) · `service` 刷新管道(频控门槛**每次请求**都过; 生产在锁内等满间隔, 复用轮只补下载 —— 见 pitfalls/backend/high-risk-ops) · `report` `--hr-once` 走查 · **`channel`/`queue`/`server`/`worker`/`runtime`(取数通道: 协议与白名单 / 任务队列 / 本地端点 / 取数线程与视图发布 / 运行时门面, 见 `QbManager.hr`)**; **判定消费在 `torrents/record.py`** —— 记录持 `hr_link`(门面稳定引用)、`hr_judgement()` 读取时现算, `check_hr_condition` / `check_hr_satisfied` 站点侧优先(打标 / WebUI / `hr` 规则条件 / `tor.hr_*` 表达式四个消费点共用它们); 配置段在 `config/models.py` `HrCheckConfig`/`SiteHrCheckConfig`, schema 在 `config/schema/hr.py`; 浏览器扩展在 `extensions/hr-fetch-proxy/` |
| 新 WEB 命令处理器 | `webui/commands.py` 加 `_cmd_*` + 命令表登记（单一入口） |
| 新 WEB 端点 | `webui/server/routes/` 对应域 Router |
| 新前端界面 | 与 `webui/` `tray/` 同级新建表现层包（落位规则见计划 §04） |

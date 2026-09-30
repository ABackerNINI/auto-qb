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
| `mixins/`（rule_engine / tags / checking / grouping / tracker / speed_curve; 新增 ops 危险操作层） | `core/mixins/`（P0-P5 已再迁 `core/modules/` 功能模块, 见 plan 26-09-30-1819; 包内只剩 webui views/commands 组合入口） |
| `mixins/web_view.py` / `mixins/web_commands.py` | `webui/views.py` / `webui/commands.py`（W3 先行迁出） |
| `errors.py` / `locking.py` / `logging.py` / `utils.py` / `notify.py` / `autostart.py` | `infra/` 同名 |
| `web_runtime.py` | `webui/runtime.py` |
| `web/`（HTTP 层 16 文件） | `webui/server/` |
| `web_ui/static/` | `webui/static/` |
| `ui.py` | `tray/app.py` |

## 常用"在哪里改"速查

| 需求 | 位置 |
|------|------|
| 新功能模块 / 模块契约 | [conventions/modules.md](../conventions/modules.md)(契约/段认领/相位单点)→ `core/modules/` 写实现 + `core/qbmanager.py` 装配清单挂入(注意消费序) |
| 新配置键 | `config/models.py` (dataclass 字段+默认值) + `config/loaders.py` (load 函数) + `config/validation.py` (校验+KNOWN 键); 如属 tracker 级加进 `load_tracker_config`; **并落到一个认领面**(某模块 `sections()` / `impact.KERNEL_SECTIONS` / `RESTART_SECTIONS` —— 漏登则 test_modules_p6 守阵红 + 运行期兜底 WARN) |
| 新规则条件 | `rules/conditions.py` 写类 + `@register_condition` (装饰即注册, import 已在 `rules/__init__.py`), 并在 `config/validation.py` 加 spec 校验 |
| 新规则动作 | `rules/actions/` 对应职责模块写类 + `@register_action`, 并在 `actions/__init__.py` import(否则不注册), 并在 `config/validation.py` 加 spec 校验; 需要新变量替换则扩展 `utils.replace_vars` |
| 新集数命名模式 | `core/episodes.py` `_EPISODE_PATTERNS` 列表按优先级插入 |
| 新流量数据源 | `core/curves.py` 加解析 + `core/modules/speed_curve_mod.py`/`config/validation.py` 扩展 traffic_source 校验 |
| 新全局周期任务 | 所属功能模块的 `start()` 自注册 + 订阅 `queue_rebuilt` 相位重入队(先例: maintenance_mod 的 delete_tags 族 / speed_curve_mod 的曲线任务); 内核不再点名任务 |
| 新种子级内置任务 | `core/modules/rules_mod.py` `_create_torrent_tasks` + handler(经 torrents_added 相位触发) |
| **HR 在线核实**(取 HR 统计页 / 对账建索引 / 三态判定) | `hr/`(新包): `bencode` infohash · `parse` 表格抽取 · `adapters/` 站点隔离(现只有 NexusPHP `myhr.php`; **接第二个 NexusPHP 站点只改配置**, 非该形态才写 adapter 并在 `adapters/__init__.py` 注册) · `store` 站点文件 + 每站点锁 · `ratelimit` 频控 · `resolve` 三态与收口判定(`judge_record` / `HrJudgement`) · `service` 刷新管道(频控门槛**每次请求**都过; 生产在锁内等满间隔, 复用轮只补下载 —— 见 pitfalls/backend/high-risk-ops) · `status` **站点级现状快照单点**(`site_status()`: CLI 报告与 WebUI 同一套数, 含「现在为什么不放行」) · `events` **四类事件告警文案单点**(`[HR 登录失效]`/`[HR 熔断]`/`[HR 页面改版]`/`[HR 通道静默]`) · `report` `--hr-once` 走查 · **`channel`/`queue`/`server`/`worker`/`runtime`(取数通道: 协议与白名单 / 任务队列 / 本地端点(`tasks`/`result`/`sites` 三路由 —— `sites` 供扩展选项页「勾选站点一键授权」, `runtime._site_origins` 现读配置派生授权清单) / 取数线程与视图发布 / 运行时门面, 见 `QbManager.hr`)**; **判定消费在 `torrents/record.py`** —— 记录持 `hr_link`(门面稳定引用)、`hr_judgement()` 读取时现算; 判定三方法各管一件事(26-09-30-0559 触发语义重构): `check_hr_condition` **纯本地下载触发判据**(展示辅助, 只区分「本机下载 vs 疑似辅种」) / `check_hr_satisfied` **义务已了单点**(站点结论优先, 无触发门 —— 转移种做种满也达标) / `hr_managed` **需管束单点**(考察中 ∨ (无证据/未接入 ∧ 未达标), 放行显式短路, 不能写 `not satisfied`) —— 消费点: 打标(`core/mixins/tags.py` 放行短路+超额跳过+satisfied 分流) / `hr` 规则条件(condition-met=`hr_managed` · satisfied=单条件) / 表达式 `tor.hr_condition_met`(=需管束)与 `tor.hr_local_triggered`(纯本地触发) / WebUI(`hr_triggered`=纯本地展示辅助; 展示三分 safe/danger/warning, 疑似辅种=warning 黄档); **HR 排除表在四入口顶部短路**(`hr_excluded()`, 26-09-28-1805: 命中 `hr.exclude_tags`/`exclude_categories` 的种子不纳入 HR 体系, 取数管道零感知); **站点级状态经 `webui/server/routes/hr.py` 的只读 `GET /api/hr/status` 出到设置页「HR 在线核实」分区页尾的「站点状态」块**(2026-09-25 合并, 单入口); 配置段在 `config/models.py` `HrCheckConfig`/`SiteHrCheckConfig`, schema 在 `config/schema/hr.py`; **站点配置源单点在 `config/site_presets.py` 内置档案表**(26-09-27-1318 收敛): 用户在 `hr_check.sites.<档案 id>` 点选启用, loaders 按「显式 tracker 直取 > 档案已知 announce 域默认映射查表」(26-09-27-1930 映射制, web 域与 tracker 域永不互相比对)派生填充 `TrackerConfig.hr_check`(绑定结果视图; 旧键 `trackers.*.hr_check` 由 schema 迁移链 config v1→v2 一次性改写, 无常驻兼容层), 下游运行链路零感知; 浏览器扩展在 `extensions/hr-fetch-proxy/`(自带**运行日志**: 分级 + 环形上限≤10000 条, 选项页④区过滤查看) |
| 新 WEB 命令处理器 | `webui/commands.py` 加 `_cmd_*` + 命令表登记（单一入口） |
| 新 WEB 端点 | `webui/server/routes/` 对应域 Router |
| 新前端界面 | 与 `webui/` `tray/` 同级新建表现层包（落位规则见计划 §04） |

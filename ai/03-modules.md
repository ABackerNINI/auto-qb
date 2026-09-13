# 03 模块地图

> 行数为 2026-09-05 快照。所有路径相对 `src/auto_qb/` (除注明)。

## 包入口

| 文件 | 行数 | 职责 |
|------|------|------|
| `../auto-qb.py` | 8 | 兼容入口: `python src/auto-qb.py` → `cli.main` |
| `__init__.py` | 23 | 导出 Config/QbManager/load_config, `__version__="0.2.0"` |
| `__main__.py` | 5 | `python -m auto_qb` 入口 |

## 核心模块

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `cli.py` | 90 | argparse 入口 | `--export-yaml/-e`, `--only-missing`, `--dry-run/-n`, `--export-torrents_info`; 导出模式不进主循环; **单点捕获 `AutoQbError` 体系**(ConfigError 输出 `配置错误: ...` 前缀, 锁/qB 兼容等其它 AutoQbError 直接输出消息; 均无堆栈, 退出码 1; 非 AutoQbError 异常照常抛出); 运行期致命错误退出前 best-effort 补发通知 (`notify_fatal`); `--tray` 托盘模式入口(与导出模式互斥; 双开唤起失败回退常规锁错误); 入口 `sys.exit(main())` 使退出码生效 |
| `config/` | 包 | 配置: 按职责分层(模型/校验/解析), `__init__.py` 重导出全部公共名称 —— 调用方 `from auto_qb.config import X` 不变 |
| `config/errors.py` | 11 | `ConfigError`(配置错误统一异常, **AutoQbError 子类**: 文件读取/YAML 解析/校验失败/启动期规则 spec 错误) |
| `config/models.py` | 176 | 数据类字段默认 = **唯一默认值来源**(解析后空间, `Config()` 即全默认实例); `Config`/`TrackerConfig`/`HRRule`/`GroupingConfig`/`AddEpisodeTagsConfig`/`LoggingConfig`/`QbittorrentConfig`/`GlobalSpeedLimitCurve`/`PeriodCurve`/`CurvePoint` (仅声明, 不含逻辑); 仅 2 个非字段默认常量: `DEFAULT_CONFIG_FILE`(cli)/`UNLIMITED_SPEED`(exporter) |
| `config/validation.py` | 554 | fail-fast 全量校验: `validate_config` 入口 + 各段校验器(`_validate_log/qbittorrent/global_hr/grouping/tag_lists/tracker_hr/trackers/rules/plugin_entry` + 曲线) + 插件 spec 深度校验(`_validate_state_condition_spec`/`_validate_checking_action_spec`, 经 `_PLUGIN_SPEC_VALIDATORS` 分发) + 通用助手(`_strip_none`/`_try*`/`_check_*`) + `KNOWN_*`/`RULE_*` 常量; 规则/条件/动作名称经 registry 延迟导入校验 |
| `config/loaders.py` | 309 | 解析加载(先验证再解析, 假定配置正确零检查): `load_config` 入口 + `load_logging/qbittorrent/grouping/add_episode_tags/tracker/global_hr/tracker_hr/global_speed_limit_curve` + `_parse_curve_points` + `_expand_tracker_tags_refs` |
| `config/impact.py` | 64 | 配置变更影响分析(热重载分级, 服务 WEB 保存设置与 `apply_new_config`): `diff_config_impacts` 递归 diff 新旧配置 -> `[ConfigChange(path, level, old, new)]` 按 path 排序; 分级表驱动 —— `SECTION_LEVELS`(L0 运行时动态读: main_tick/max_tasks_per_tick/remove_similar_tags/skip_checking_tag/grouping/add_episode_tags; L1 轻量: logging/notify/qbittorrent/web; L2 结构重建: interval/rules_config/delete_tags*/global_speed_limit_curve; R 需重启: state_file/data_dir; **未列出默认 L2 保守**) + `TRACKER_FIELD_LEVELS`(tracker 字段级: tags/remove_tags/remove_similar_tags/限速/hr = L0, domains/rules = L2); trackers 段工具 `_diff_trackers`(增删站点 = 整项 L2, 同名则逐字段定级); 粒度注意: `_diff_flat` 的**字段级展开仅适用于值为纯 dict 的 L0 段**, 真实 `Config` 的 L0 段均为 dataclass 实例 -> 产出整段单条(L0)变更; `max_level`/`restart_required_paths` 为公共工具但**当前无生产调用**(web.py/qbmanager.py 各自内联推导), 测试已覆盖 |
| `qbmanager.py` | 323 | 主协调者 | `QbManager`(6 mixin 组合): `run`/`_tick`(refresh + `task_queue.run_due` 一次调用)/`_refresh_torrents`/`_create_global_tasks`/`_create_torrent_tasks`/`_handle_maintenance`/`connect`(连接异常日志节流 `_last_conn_ok` 状态机) |
| `taskqueue.py` | 207 | 单任务队列 | 生命周期只有 `add_task`(入队; check 自动登记 `_active_checks` 在途, 重复返回 False)/`run_due`(到期执行+收尾: True 重入队 / False 消亡释放) 两个动词; `Task.reset()` 显式重置断点; 无 defer/resume 挂起态 —— 推迟执行由子任务按情况重新入队; `active_check_hashes`(组内校验串行化依赖) |
| `torrents.py` | 430 | 种子数据层 | `TorrentRecord`(快照记录+惰性缓存 + `check_hr_condition/check_hr_satisfied` HR 判定), `TorrentStore`(refresh/分组索引/全局缓存/写后同步 + `restore_torrent` 跳检重加快照恢复); `QbCompatError`/`missing_torrent_fields`/`REQUIRED_TORRENT_FIELDS`/`RE_ADD_FIELDS` |
| `qbapi.py` | 204 | qB API Facade | `QbApi`: store 必传, 写后同步快照, 读走缓存, `get/set_global_speed_limits`(qB5.0 transfer 端点) |
| `errors.py` (包级) | 13 | `AutoQbError` 致命错误根: CLI 单点捕获(stderr 干净 + 退出码 1); 子类并列: `ConfigError`(config)/`SingleInstanceLockError`(locking)/`QbCompatError`(torrents) |
| `locking.py` | 112 | 单实例锁 | `SingleInstanceLock`(基于第三方 `filelock` + 伴生 `<lock>.meta.json` 记录 PID/启动时间/配置路径); `SingleInstanceLockError(AutoQbError)` 走 CLI 退出码 1; 仅正常 run 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 锁文件路径 `<state_file 去扩展名>.lock` (避免与 state 文件同目录同名冲突) |
| `utils.py` | 334 | 通用工具 | `parse_time/parse_fsize/parse_speed/parse_bool/parse_compare/compare/parse_hr_condition`; `MatchPattern.parse`(regex:/:ignore_case 语法解析唯一入口)+ `match_value`(单值多模式匹配核心); `match_tag_patterns`/`match_path_patterns` 为薄包装; `path_normalize`; `match_tracker_confs`(hostname 精确匹配); `add_long_path_prefix_for_win`; `extract_tracker_hostnames`; `fmt_speed`; `replace_vars`(规则变量替换); `timer` 装饰器 |
| `notify.py` | ~250 | 主动通知(零第三方依赖) | `PlatformChannel`(win32=PowerShell 调 WinRT toast / linux=notify-send / darwin=osascript, 文本经 base64/转义无注入), `NotifyThrottle`(每小时上限+同键去重窗, 内存态), `NotifyHandler`(挂 `auto_qb` logger, min_level/quiet_hours/节流过滤, 防自环, emit 异常不外抛), `setup_notify`(未启用返回 None, 平台不支持抛 AutoQbError), `notify_fatal`(CLI 致命退出补发); Windows toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单 AUMID 快捷方式(失败回退 PowerShell 来源) |
| `ui.py` | ~400 | 托盘常驻 UI(--tray) | `UiLogHandler`(日志环形缓冲 drain), `ShowIpcServer`/`send_show`(单实例唤起, 端口写 state_file 同目录 ui.port), `TrayUi`(CustomTkinter 深色窗口: 状态卡片/暂停恢复/通知热切换/开机自启/日志视图; pystray 托盘 6 项菜单; 100ms 事件轮询, 跨线程仅 queue+Event+只读快照), `run_tray`(入口; GUI 栈仅 tray 分支加载); 通知热开启: `setup_notify(force=True)` 从未配置状态会话级挂载(UI 开关/托盘勾选); toast 点击激活 = 以 launch_arguments 重启应用(AUMID 快捷方式 Arguments, 每次启动幂等重写)经单实例锁唤起窗口; 窗口图标 Windows 走 CTk iconbitmap(.ico, 防被 CTk 默认图标延迟覆盖) |
| `autostart.py` | ~90 | 开机自启(零依赖) | 资源: `assets/icon.png`(256, 托盘)+ `assets/icon.ico`(多尺寸, Windows 窗口图标); ⚠️ **任务栏图标修复的最终结论(四轮实测+对照诊断)**: ①ICO 必须为 BMP 帧 —— Pillow 保存默认 PNG 压缩帧, Tk 8.6 `iconbitmap` 渲染不了(静默失败回退 python 图标), 生成须显式 `bitmap_format="bmp"`; ②**进程须先设显式 AppUserModelID(`_set_windows_appid`, 首窗口前)** —— 诊断对照: A/B/C/D 四窗口全部运行在已设 AUMID 的进程内且均为 orbit, 而无 AUMID 时无论 iconbitmap/iconphoto/WM_SETICON 任务栏恒为 python.exe 图标(AUMID 才是决定性变量, 诊断未隔离该变量曾致误判回退); ③CTk 窗口上 `iconbitmap`(BMP 帧 ico, 16~256 多尺寸)+ `_iconbitmap_method_called = True` 标记配合; ⚠️ **勿叠加 `iconphoto`/ctypes `WM_SETICON`(单尺寸 32px HICON)**: 高 DPI(4K 200%)下任务栏需要 ≥48px 大图标, 单尺寸 HICON 被 explorer 弃用回退 python 图标(诊断: A/B/C=orbit, D=CTk 蓝框); 三平台: Windows HKCU Run 注册表 / Linux XDG autostart desktop / macOS LaunchAgents plist; `is_enabled`/`enable`/`disable`; 启动命令 = 解释器 + 配置绝对路径 + --tray; 失败抛 AutoQbError(UI 提示) |
| `web.py` | ~230 | WEB UI 后端(FastAPI) | `create_app`(API: status/groups/组控制/config 读写/**search 种子搜索**, 全部 Bearer 鉴权; 静态挂载 web_ui/static), `ensure_web_token`(随机生成持久化 data_dir/web.token), `start_web_server`(uvicorn 独立线程, stop 句柄); Web 线程只读快照+投递命令, 写操作经命令队列在主循环线程执行; 搜索索引(hash->name+files)由主循环按需构建并原子替换, Web 线程只读, 种子名匹配即时(读 store.by_hash), 文件列表匹配依赖缓存索引(文件 API 只在主循环线程); 索引按 hash 增量维护(已建条目只刷新名称/新增补拉/已删淘汰) + 单次限流(SEARCH_INDEX_BUILD_BUDGET), 未拉完保持脏由下一 tick 续建, qB 断连时中止不写空 files |
| `web_ui/static/` | — | 前端(Vue 3 CDN 本地托管, 无构建链) | index.html/app.js(顶栏搜索框在真实辅种组上筛选(任一成员命中即保留整组, 组行沿用真实组 key → 组级操作可用; 仅命中成员 search-hit 高亮; 未归组命中以单种子虚拟行 `u-<hash>` 兜底, 右键退化为单种子菜单; 非扁平"站点种子"列表) + 分组列表轮询/展开明细/右键菜单/设置 YAML 编辑)/style.css(深色主题)/vendor/vue.global.prod.js |
| `curves.py` | 124 | 限速曲线纯逻辑 | `parse_history_dat`(Traffic Monitor dat 解析), `aggregate`(day/month/Nd 聚合), `curve_speed`(全程分档覆盖), `merge_direction`(取最严), `normalize_period`, `bytes_to_kib`。无项目内依赖, 便于单测 |
| `episodes.py` | 115 | 集数解析 | `_EPISODE_PATTERNS`(第x集 > S01E05 > EP05 > E05 优先级), `extract_episodes_from_files`(仅视频文件, 排除分辨率/年份), `format_episode_tag`(连续才加, 格式 `zE1-5`), `name_has_episode_marker` |
| `exporter.py` | 139 | YAML 模板导出 | 收集全部 tracker 域名 → 找未配置的 → 生成条目 (默认标签=倒数第二级域名, `hd/pt` 后字母大写), `--only-missing` 最小骨架; 重读原始文件时复用 `_strip_none`(文件已被 load_config 校验) |
| `logging.py` | 47 | 日志配置 | `setup_logging`: 控制台 + RotatingFileHandler(5 备份), **两者均跟随配置 level**; root 跟随配置拦第三方 DEBUG, `auto_qb` logger 放开 DEBUG, `qbittorrentapi` 封顶 INFO(排除请求噪音), `urllib3` 封顶 ERROR(排除断连期间连接重试的 Retry WARNING 刷屏)。注意与 stdlib logging 同名, 包内相对导入 |

## mixins/ (QbManager 的职责拆分, 组合进宿主)

| 文件 | 行数 | 职责 | 关键方法 |
|------|------|------|----------|
| `__init__.py` | 24 | 导出 6 个 mixin | |
| `rule_engine.py` | 161 | 规则加载/状态持久化/规则任务 | `_load_rules`(从 `*_rules` 段构造 Rule, 命名 `{组名}.{规则名}`), `_load_state`/`save_state`, `record_execution`, `begin_round`/`upload_delta`, `_rules_for_torrent`(@refs), `_create_rule_task`(仅 interval 规则建周期任务, on_* 返回 None), `_handle_rule`(周期规则 handler), `_resolve_refs`; **事件分派**: `_dispatch_events`/`_apply_event_rule`(建 rule-event origin + process)/`_handle_event_rule`(断点续跑 handler, 恒 FINISHED)/`_rules_by_trigger`/`_torrent_event_rules`(分流 + tracker 引用交集) — 见 09-roadmap |
| `tags.py` | 228 | 标签/分类/HR/全局清理 | `_add_tags`/`_remove_tags`/`_remove_similar_tags`, `_add_episode_tags`, `_set_category`(auto_categories 覆盖逻辑), `_add_hr_tag_or_category`, `_handle_delete_tags`, `_handle_delete_tags_if_has_no_torrents`(用 store.tag_usage 聚合, 避免逐标签查询) |
| `grouping.py` | 318 | 辅种分组 (事件驱动) | `_assign_new_torrent`/`_assign_to_group`/`_leave_group`(O(1) 成员索引), `_check_size_consistency`, `_handle_removed_torrents`/`_handle_state_transitions`(上传转暂停 / 进入 errored(校验发现缺失)→`_check_missing_files` 磁盘扫描, 代表种=已完成或 errored 且未校验, 2026-09-12 放宽; 组 key 轮内去重 —— 移动种子同轮命中多触发源只扫一次, `_missing_scanned_keys` 每轮清空), `_handle_save_path_changes`, `_check_download_conflicts`(每轮; 带 MISSING 标签的完成成员不计入 mixed, multi-dl 仍拦), `_group_members`/`_group_has_downloading`/`_group_reference_candidates`(已完成且未校验, 供 checking 动作) |
| `checking.py` | 33 | 文件检查 | `check_filelist(api, torrent)`: 文件存在+大小一致, 返回错误串或 None。(辅种跳检已迁移到规则动作, 占位保留) |
| `tracker.py` | 61 | tracker 匹配/单种限速 | `_match_tracker_conf`(hostname 精确匹配, 复用 `utils.match_tracker_confs`, 与规则绑定同语义; 命中多个配置时打 ERROR 日志并用第一个), `_apply_speed_limit`/`_apply_single_speed_limit`(奇数保护) |
| `speed_curve.py` | 146 | 全局限速曲线任务 | `_handle_speed_limit_curve`: 读 dat → 聚合 → 查档 → 取最严 → 奇数保护/幂等 → `api.set_global_speed_limits`; `_record_curve_state` |

## rules/ (插件框架)

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `registry.py` | 30 | 注册表 | `CONDITIONS`/`ACTIONS` dict + `@register_condition`/`@register_action` 装饰器 + `create_condition/create_action`(直接按名索引, 名称合法性由 config.validate_config 保证) |
| `base.py` | 274 | 框架基础 | `ActionResult`(success/failed/skipped/**pending**), `BaseCondition.match(ctx)`, `BaseAction.execute(ctx)→ActionResult`, `RuleContext`(惰性缓存 tracker/files; 变量替换/HR 判定已迁出至 utils.replace_vars 与 TorrentRecord.check_hr_*; `snapshot` 删除前快照副本, `torrent` 属性实时 store 优先、删除后回退 snapshot), `Rule`(解析 enabled/trigger/interval/execute_once/cooldown/stop_if/conditions/actions + `ignore_next_action_error` 处理; `process()` 断点续跑核心逻辑; `_dedup_allowed`) |
| `conditions.py` | 294 | 15 种条件插件 | spec 合法性由 config 校验阶段保证, 插件仅解析不自查; 详见 [04-rule-system.md](04-rule-system.md) |
| `actions/` (包) | 906/6 文件 | 12 种动作插件 | `__init__`(34, 注册入口+公共名重导出, 兼容 `from auto_qb.rules.actions import X`), `basic`(130, 标签/分类/启停/打印详情 ×7), `transfer`(86, move_to/reannounce/单种限速), `checking`(192, `CheckAction` 决策链+参考筛选, 组合 `FullCheckingMixin`+`SkipCheckingMixin`), `full_checking`(225, full-checking 执行+组内校验串行化闸门 1.5/1.6+失败计数), `skip_checking`(239, 跳检四阶段+`_poll_until`); spec 正确性由 config 校验阶段保证; 详见 [04-rule-system.md](04-rule-system.md) |

## tests/ (30 文件 + helpers.py, 详见 07-testing.md)

按模块一一对应命名: `test_config.py`, `test_impact.py`(配置变更影响分级), `test_qbmanager.py`, `test_taskqueue.py`, `test_torrents.py`, `test_actions.py`, `test_conditions.py`, `test_checking.py`(54 个测试函数, 最大), `test_grouping.py`(41), `test_rule_base.py`, `test_rule_engine.py`, `test_rules_core.py`, `test_registry.py`, `test_mixins_tags.py`, `test_hr.py`, `test_delete_tags.py`, `test_tracker.py`, `test_speed_curve.py`, `test_snapshot_sync.py`(QbApi 快照同步), `test_state_matrix.py`(状态映射), `test_episodes.py`, `test_exporter.py`, `test_cli.py`, `test_locking.py`(单实例锁), `test_logging.py`, `test_utils.py`, `test_notify.py`(主动通知), `test_ui.py`(托盘 UI 支撑设施), `test_web.py`(WEB API + 搜索/命令执行/热重载); `helpers.py` 提供全 Fake 基础设施; `test_trigger_events.py` (事件触发规则, 2026-09-12 已落地)。

## 依赖方向 (单向, 无环)

```
cli → qbmanager → {config, taskqueue, torrents, qbapi, mixins/*, rules}
rules/* → {torrents, config, utils, qbapi, taskqueue}   (base.py 不 import qbmanager, manager 以 Any 注入)
mixins/* → {config, torrents, qbapi, utils, taskqueue, curves, episodes}
curves / episodes: 无项目内依赖 (纯逻辑, 独立可测)
```

**注意**: `rules/base.py` 刻意不导入 QbManager (注释掉), `RuleContext.manager` 类型为 `Any` — 避免循环导入。新增跨层引用时遵循此模式。

## 常用"在哪里改"速查

| 需求 | 位置 |
|------|------|
| 新配置键 | `config/models.py` (dataclass 字段+默认值) + `config/loaders.py` (load 函数) + `config/validation.py` (校验+KNOWN 键); 如属 tracker 级加进 `load_tracker_config` |
| 新规则条件 | `rules/conditions.py` 写类 + `@register_condition` (装饰即注册, import 已在 `rules/__init__.py`), 并在 `config/validation.py` 加 spec 校验 |
| 新规则动作 | `rules/actions/` 对应职责模块写类 + `@register_action`, 并在 `actions/__init__.py` import(否则不注册), 并在 `config/validation.py` 加 spec 校验; 需要新变量替换则扩展 `utils.replace_vars` |
| 新集数命名模式 | `episodes.py` `_EPISODE_PATTERNS` 列表按优先级插入 |
| 新流量数据源 | `curves.py` 加解析 + `mixins/speed_curve.py`/`config/validation.py` 扩展 traffic_source 校验 |
| 新全局周期任务 | `qbmanager.py` `_create_global_tasks` 加 Task |
| 新种子级内置任务 | `qbmanager.py` `_create_torrent_tasks` + handler |

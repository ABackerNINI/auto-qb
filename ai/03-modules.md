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
| `cli.py` | ~85 | argparse 入口 | `--export-yaml/-e`, `--only-missing`, `--dry-run/-n`, `--export-torrents_info`; 导出模式不进主循环; **提前捕获 `ConfigError`**(stderr 输出 `配置错误: ...` 无堆栈, 退出码 1; 其它异常照常抛出); 入口 `sys.exit(main())` 使退出码生效 |
| `config/` | 包 | 配置: 按职责分层(模型/校验/解析), `__init__.py` 重导出全部公共名称 —— 调用方 `from auto_qb.config import X` 不变 |
| `config/errors.py` | 9 | `ConfigError`(配置错误统一异常, ValueError 子类: 文件读取/YAML 解析/校验失败/启动期规则 spec 错误) |
| `config/models.py` | ~175 | 数据类字段默认 = **唯一默认值来源**(解析后空间, `Config()` 即全默认实例); `Config`/`TrackerConfig`/`HRRule`/`GroupingConfig`/`LoggingConfig`/`QbittorrentConfig`/`GlobalSpeedLimitCurve`/`PeriodCurve`/`CurvePoint` (仅声明, 不含逻辑); 仅 2 个非字段默认常量: `DEFAULT_CONFIG_FILE`(cli)/`UNLIMITED_SPEED`(exporter) |
| `config/validation.py` | 552 | fail-fast 全量校验: `validate_config` 入口 + 各段校验器(`_validate_log/qbittorrent/global_hr/grouping/tag_lists/tracker_hr/trackers/rules/plugin_entry` + 曲线) + 插件 spec 深度校验(`_validate_state_condition_spec`/`_validate_checking_action_spec`, 经 `_PLUGIN_SPEC_VALIDATORS` 分发) + 通用助手(`_strip_none`/`_try*`/`_check_*`) + `KNOWN_*`/`RULE_*` 常量; 规则名称经 registry 延迟导入校验 |
| `config/loaders.py` | 270 | 解析加载(先验证再解析, 假定配置正确零检查): `load_config` 入口 + `load_logging/qbittorrent/grouping/tracker/global_hr/tracker_hr/global_speed_limit_curve` + `_parse_curve_points` + `_expand_tracker_tags_refs` |
| `qbmanager.py` | 341 | 主协调者 | `QbManager`(6 mixin 组合): `run`/`_tick`/`_refresh_torrents`/`_create_global_tasks`/`_create_torrent_tasks`/`_handle_maintenance` |
| `taskqueue.py` | 192 | 单任务队列 | `Task`, `TaskQueue`; 状态常量 PENDING/RUNNING/DEFERRED; defer/resume/add_check_task |
| `torrents.py` | ~390 | 种子数据层 | `TorrentRecord`(快照记录+惰性缓存 + `check_hr_condition/check_hr_satisfied` HR 判定), `TorrentStore`(refresh/分组索引/全局缓存/写后同步 + `restore_torrent` 跳检重加快照恢复); `QbCompatError`/`missing_torrent_fields`/`REQUIRED_TORRENT_FIELDS`/`RE_ADD_FIELDS` |
| `qbapi.py` | 204 | qB API Facade | `QbApi`: store 必传, 写后同步快照, 读走缓存, `get/set_global_speed_limits`(qB5.0 transfer 端点) |
| `errors.py` (包级) | ~14 | `AutoQbError` 致命错误根: CLI 单点捕获(stderr 干净 + 退出码 1); 子类并列: `ConfigError`(config)/`SingleInstanceLockError`(locking)/`QbCompatError`(torrents) |
| `locking.py` | ~70 | 单实例锁 | `SingleInstanceLock`(基于第三方 `filelock` + 伴生 `<lock>.meta.json` 记录 PID/启动时间/配置路径); `SingleInstanceLockError(ConfigError)` 走 CLI 退出码 1; 仅正常 run 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 锁文件路径 `<state_file 去扩展名>.lock` (避免与 state 文件同目录同名冲突) |
| `utils.py` | 314 | 通用工具 | `parse_time/parse_fsize/parse_speed/parse_bool/parse_compare/compare/parse_hr_condition`; `match_tag_patterns`/`match_path_patterns`/`path_normalize`; `match_tracker_confs`(hostname 精确匹配); `add_long_path_prefix_for_win`; `extract_tracker_hostnames`; `fmt_speed`; `timer` 装饰器 |
| `curves.py` | 122 | 限速曲线纯逻辑 | `parse_history_dat`(Traffic Monitor dat 解析), `aggregate`(day/month/Nd 聚合), `curve_speed`(全程分档覆盖), `merge_direction`(取最严), `normalize_period`, `bytes_to_kib`。无项目内依赖, 便于单测 |
| `episodes.py` | 113 | 集数解析 | `_EPISODE_PATTERNS`(第x集 > S01E05 > EP05 > E05 优先级), `extract_episodes_from_files`(仅视频文件, 排除分辨率/年份), `format_episode_tag`(连续才加, 格式 `zE1-5`), `name_has_episode_marker` |
| `exporter.py` | ~140 | YAML 模板导出 | 收集全部 tracker 域名 → 找未配置的 → 生成条目 (默认标签=倒数第二级域名, `hd/pt` 后字母大写), `--only-missing` 最小骨架; 重读原始文件时复用 `_strip_none`(文件已被 load_config 校验) |
| `logging.py` | 40 | 日志配置 | `setup_logging`: 控制台 + RotatingFileHandler(5 备份)。注意与 stdlib logging 同名, 包内相对导入 |

## mixins/ (QbManager 的职责拆分, 组合进宿主)

| 文件 | 行数 | 职责 | 关键方法 |
|------|------|------|----------|
| `__init__.py` | 24 | 导出 6 个 mixin | |
| `rule_engine.py` | 161 | 规则加载/状态持久化/规则任务 | `_load_rules`(从 `*_rules` 段构造 Rule, 命名 `{组名}.{规则名}`), `_load_state`/`save_state`, `record_execution`, `begin_round`/`upload_delta`, `_rules_for_torrent`(@refs), `_create_rule_task`, `_handle_rule`, `_resolve_refs` |
| `tags.py` | 228 | 标签/分类/HR/全局清理 | `_add_tags`/`_remove_tags`/`_remove_similar_tags`, `_add_episode_tags`, `_set_category`(auto_categories 覆盖逻辑), `_add_hr_tag_or_category`, `_handle_delete_tags`, `_handle_delete_tags_if_has_no_torrents`(用 store.tag_usage 聚合, 避免逐标签查询) |
| `grouping.py` | 318 | 辅种分组 (事件驱动) | `_assign_new_torrent`/`_assign_to_group`/`_leave_group`(O(1) 成员索引), `_check_size_consistency`, `_handle_removed_torrents`/`_handle_state_transitions`/`_handle_save_path_changes`(→`_check_missing_files` 磁盘扫描, 代表种=已完成且未校验), `_check_download_conflicts`(每轮), `_group_members`/`_group_has_downloading`/`_group_reference_candidates`(已完成且未校验, 供 checking 动作) |
| `checking.py` | 33 | 文件检查 | `check_filelist(api, torrent)`: 文件存在+大小一致, 返回错误串或 None。(辅种跳检已迁移到规则动作, 占位保留) |
| `tracker.py` | 61 | tracker 匹配/单种限速 | `_match_tracker_conf`(hostname 精确匹配, 复用 `utils.match_tracker_confs`, 与规则绑定同语义; 命中多个配置时打 ERROR 日志并用第一个), `_apply_speed_limit`/`_apply_single_speed_limit`(奇数保护) |
| `speed_curve.py` | 146 | 全局限速曲线任务 | `_handle_speed_limit_curve`: 读 dat → 聚合 → 查档 → 取最严 → 奇数保护/幂等 → `api.set_global_speed_limits`; `_record_curve_state` |

## rules/ (插件框架)

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `registry.py` | 29 | 注册表 | `CONDITIONS`/`ACTIONS` dict + `@register_condition`/`@register_action` 装饰器 + `create_condition/create_action`(直接按名索引, 名称合法性由 config.validate_config 保证) |
| `base.py` | 294 | 框架基础 | `ActionResult`(success/failed/skipped/**pending**), `BaseCondition.match(ctx)`, `BaseAction.execute(ctx)→ActionResult`, `RuleContext`(惰性缓存 tracker/files; 变量替换/HR 判定已迁出至 utils.replace_vars 与 TorrentRecord.check_hr_*), `Rule`(解析 enabled/interval/execute_once/cooldown/stop_if/conditions/actions + `ignore_next_action_error` 处理; `process()` 断点续跑核心逻辑; `_dedup_allowed`) |
| `conditions.py` | 294 | 15 种条件插件 | spec 合法性由 config 校验阶段保证, 插件仅解析不自查; 详见 [04-rule-system.md](04-rule-system.md) |
| `actions.py` | 682 | 11 种动作插件 | 详见 [04-rule-system.md](04-rule-system.md); `CheckAction`(checking) 最复杂, spec 正确性由 config 校验阶段保证 |

## tests/ (24 文件 + helpers.py, 详见 07-testing.md)

按模块一一对应命名: `test_config.py`, `test_qbmanager.py`, `test_taskqueue.py`, `test_torrents.py`, `test_actions.py`, `test_conditions.py`, `test_checking.py`(47 用例, 最大), `test_grouping.py`(41), `test_rule_base.py`, `test_rule_engine.py`, `test_rules_core.py`, `test_registry.py`, `test_mixins_tags.py`, `test_hr.py`, `test_delete_tags.py`, `test_tracker.py`, `test_speed_curve.py`, `test_snapshot_sync.py`(QbApi 快照同步), `test_state_matrix.py`(状态映射), `test_episodes.py`, `test_exporter.py`, `test_cli.py`, `test_config.py`, `test_logging.py`, `test_utils.py`; `helpers.py` 提供全 Fake 基础设施。

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
| 新配置键 | `config.py` (dataclass + load 函数 + 校验); 如属 tracker 级加进 `load_tracker_config` |
| 新规则条件 | `rules/conditions.py` 写类 + `@register_condition` (装饰即注册, import 已在 `rules/__init__.py`) |
| 新规则动作 | `rules/actions.py` 写类 + `@register_action`; 需要新变量替换则扩展 `RuleContext.replace_vars` |
| 新集数命名模式 | `episodes.py` `_EPISODE_PATTERNS` 列表按优先级插入 |
| 新流量数据源 | `curves.py` 加解析 + `speed_curve.py`/`config.py` 扩展 traffic_source 校验 |
| 新全局周期任务 | `qbmanager.py` `_create_global_tasks` 加 Task |
| 新种子级内置任务 | `qbmanager.py` `_create_torrent_tasks` + handler |

# 核心模块 · config 包

> 行数为 2026-09-05 快照。所有路径相对 `src/auto_qb/`(除注明)。

> 摘要: 配置层: 模型 / 校验 / 解析 / 写回 / UI 元数据 / 影响分级。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: config, 配置, 模型, 校验, 解析, 写回, schema, impact

## 核心模块

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `config/` | 包 | 配置: 按职责分层(模型/校验/解析), `__init__.py` 重导出全部公共名称 —— 调用方 `from auto_qb.config import X` 不变 |
| `config/errors.py` | 11 | `ConfigError`(配置错误统一异常, **AutoQbError 子类**: 文件读取/YAML 解析/校验失败/启动期规则 spec 错误) |
| `config/models.py` | 176 | 数据类字段默认 = **唯一默认值来源**(解析后空间, `Config()` 即全默认实例); `Config`/`TrackerConfig`/`HRRule`/`GroupingConfig`/`AddEpisodeTagsConfig`/`LoggingConfig`/`QbittorrentConfig`/`GlobalSpeedLimitCurve`/`PeriodCurve`/`CurvePoint` (仅声明, 不含逻辑); 仅 2 个非字段默认常量: `DEFAULT_CONFIG_FILE`(cli)/`UNLIMITED_SPEED`(exporter) |
| `config/validation/` (包) | 817/5 文件 | fail-fast 全量校验(2026-09-15 由单文件 687 行转包): `core.py`(validate_config 入口 + `_strip_none`/`_try*`/`_check_*` 通用助手 + KNOWN_CONFIG_KEYS; **各段校验器延迟导入防环**)/`sections.py`(log/qbittorrent/hr/grouping/web/notify/trackers 等各段校验器 + 段级 KNOWN_* 键表)/`rules.py`(规则 spec 校验 + 插件 spec 深度校验 `_PLUGIN_SPEC_VALIDATORS` 分发 + 规则常量)/`curves.py`(全局限速曲线段)/`__init__.py`(重导出 validate_config/KNOWN_*/_strip_none); 经 registry 延迟导入校验规则/条件/动作名称 |
| `config/loaders.py` | 309 | 解析加载(先验证再解析, 假定配置正确零检查): `load_config` 入口 + `load_logging/qbittorrent/grouping/add_episode_tags/tracker/global_hr/tracker_hr/global_speed_limit_curve` + `_parse_curve_points` + `_expand_tracker_tags_refs` |
| `config/schema/` (包) | 932/5 文件 | 图形化配置编辑器 UI 元数据(2026-09-15 由单文件 855 行转包): `fields.py`(Field/Group/Plugin + KINDS/单位与选项常量, 零依赖)/`trackers.py`(HR 输出/站点 hr/站点字段表)/`rules.py`(RULE_FIELDS/CONDITION_PLUGINS/ACTION_PLUGINS)/`groups.py`(GROUPS 顶层分组表)/`__init__.py`(config_fields/schema_payload 等访问函数 + 全量重导出); `from auto_qb.config import schema` 调用方零改动 |
| `config/writer.py` | ~215 | 配置写回(图形化编辑器专用): `read_tree`(`BaseLoader` 读为 YAML 同构树, 标量全字符串)/`write_tree(config_path, tree, old_config, backup_path)`(结构自检 → 临时文件 `load_config` 校验 → `diff_config_impacts` → **R 级字段回退磁盘旧值** → 备份到调用方给的 `backup_path`(生产 = `<data_dir>/<配置名>.bak`) → ruamel round-trip 写盘)/`preview_tree`(同前置逻辑, **不备份**不落盘, 供只读预览)/`_sync_mapping`(递归同步 CommentedMap: 保注释, 值未变则跳过赋值以保留原标量形态)/`_plain_scalar`(数字/布尔样式写为原生标量, 与磁盘既有书写风格一致)/`_same_value`+`_as_builtin`(按 BaseLoader 语义比较, 布尔小写化)/`WriteResult` |
| `config/impact.py` | 64 | 配置变更影响分析(热重载分级, 服务 WEB 保存设置与 `apply_new_config`): `diff_config_impacts` 递归 diff 新旧配置 -> `[ConfigChange(path, level, old, new)]` 按 path 排序; 分级表驱动 —— `SECTION_LEVELS`(L0 运行时动态读: main_tick/max_tasks_per_tick/remove_similar_tags/skip_checking_tag/grouping/add_episode_tags; L1 轻量: logging/notify/qbittorrent/web; L2 结构重建: interval/rules_config/delete_tags*/global_speed_limit_curve; R 需重启: state_file/data_dir; **未列出默认 L2 保守**) + `TRACKER_FIELD_LEVELS`(tracker 字段级: tags/remove_tags/remove_similar_tags/限速/hr = L0, domains/rules = L2); trackers 段工具 `_diff_trackers`(增删站点 = 整项 L2, 同名则逐字段定级); 粒度注意: `_diff_flat` 的**字段级展开仅适用于值为纯 dict 的 L0 段**, 真实 `Config` 的 L0 段均为 dataclass 实例 -> 产出整段单条(L0)变更; `max_level`/`restart_required_paths` 为公共工具但**当前无生产调用**(web.py/qbmanager.py 各自内联推导), 测试已覆盖 |

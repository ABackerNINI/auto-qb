# 核心模块 · config 包

> 行数为 2026-10-01 实测(`wc -l`)。所有路径相对 `src/auto_qb/`(除注明)。

> 摘要: 配置层: 模型 / 校验 / 解析 / 写回 / UI 元数据 / 影响分级。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: config, 配置, 模型, 校验, 解析, 写回, schema, impact

## 核心模块

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `config/` | 包 | 配置: 按职责分层(模型/校验/解析), `__init__.py` 重导出全部公共名称 —— 调用方 `from auto_qb.config import X` 不变 |
| `config/errors.py` | 11 | `ConfigError`(配置错误统一异常, **AutoQbError 子类**: 文件读取/YAML 解析/校验失败/启动期规则 spec 错误) |
| `config/models.py` | 362 | 数据类字段默认 = **唯一默认值来源**(解析后空间, `Config()` 即全默认实例); `Config`/`TrackerConfig`/`HRRule`/`HrChannelConfig`/`HrCheckConfig`/`SiteHrCheckConfig`/`GroupingConfig`/`AddEpisodeTagsConfig`/`WebConfig`/`NotifyConfig`/`FsConfig`/`PathMapEntry`/`LoggingConfig`/`QbittorrentConfig`/`GlobalSpeedLimitCurve`/`PeriodCurve`/`CurvePoint` (仅声明, 不含逻辑); 仅 2 个非字段默认常量: `DEFAULT_CONFIG_FILE`(cli)/`UNLIMITED_SPEED`(exporter) |
| `config/validation/` (包) | 1341/5 文件 | fail-fast 全量校验(2026-09-15 由单文件 687 行转包): `core.py`(validate_config 入口 + `_strip_none`/`_try*`/`_check_*` 通用助手 + KNOWN_CONFIG_KEYS; **各段校验器延迟导入防环**)/`sections.py`(log/qbittorrent/hr/grouping/web/notify/trackers 等各段校验器 + 段级 KNOWN_* 键表)/`rules.py`(规则 spec 校验 + 插件 spec 深度校验 `_PLUGIN_SPEC_VALIDATORS` 分发 + 规则常量)/`curves.py`(全局限速曲线段)/`__init__.py`(重导出 validate_config/KNOWN_*/_strip_none); 经 registry 延迟导入校验规则/条件/动作名称 |
| `config/loaders.py` | 550 | 解析加载(先验证再解析, 假定配置正确零检查): `load_config` 入口 + `load_logging/qbittorrent/grouping/web/notify/hr_check/site_hr_check/fs/tracker/global_hr/tracker_hr/global_speed_limit_curve` + `normalize_schema_version`(YAML 标量归一 int)/`migrate_config_schema`(schema 版本迁移分派入口: 内存迁移, 磁盘落盘单点在 `writer.materialize_schema_migration` run() 启动期完成) + `_get_episode_tags`(原 `load_add_episode_tags` 更名)/`_parse_curve_points`/`_expand_tracker_tags_refs`/`_resolve_hr_site_bindings` |
| `config/schema/` (包) | 1396/6 文件 | 图形化配置编辑器 UI 元数据(2026-09-15 由单文件 855 行转包): `fields.py`(Field/Group/Plugin + KINDS/单位与选项常量, 零依赖)/`hr.py`(HR 在线核实分区字段表, 2026-09-27 随 hr_check 站点映射制新增)/`trackers.py`(HR 输出/站点 hr/站点字段表)/`rules.py`(RULE_FIELDS/CONDITION_PLUGINS/ACTION_PLUGINS)/`groups.py`(GROUPS 顶层分组表)/`__init__.py`(config_fields/schema_payload 等访问函数 + 全量重导出); `from auto_qb.config import schema` 调用方零改动 |
| `config/site_presets.py` | 111 | HR 站点**内置档案表**(代码写死, plan 26-09-27-1318 REV2): 站点 → (adapter/web 域/announce 域/页面路径/种子下载路径/翻页参数名) —— 程序已知、人易配错的内容不进配置, 用户只在 HR 分区点选启用 + 微调; **三命名空间纪律判定单点**(plan 26-09-27-1930): web 域仅展示永不参与匹配, announce 域是唯一匹配空间, tracker 条目名按显式覆盖键字符串相等引用 |
| `config/migrations.py` | 146 | config schema 迁移函数(plan 26-09-26-0506 版本链; 依赖纪律落 config 层而非 infra —— 迁移需 `SITE_PRESETS` 做档案定位): 版本链上**一次性纯函数变换**, 不是常驻兼容层 —— v1→v2 把旧 `trackers.<名>.hr_check` 翻成 `hr_check.sites.<档案 id>` 后即不再伺候旧键; import 即注册, 经 `loaders.migrate_config_schema` 分派 |
| `config/writer.py` | 427 | 配置写回(图形化编辑器专用): `read_tree`(`BaseLoader` 读为 YAML 同构树, 标量全字符串)/`write_tree(config_path, tree, old_config, backup_path)`(结构自检 → 临时文件 `load_config` 校验 → `diff_config_impacts` → **R 级字段回退磁盘旧值** → 备份到调用方给的 `backup_path`(生产 = `<data_dir>/<配置名>.bak`) → ruamel round-trip 写盘)/`preview_tree`(同前置逻辑, **不备份**不落盘, 供只读预览)/`materialize_schema_migration`(run() 启动期迁移**落盘**单点: 版本号备份后立即原子写回, plan 26-09-27-2252)/`_sync_mapping`(递归同步 CommentedMap: 保注释, 值未变则跳过赋值以保留原标量形态)/`_plain_scalar`(数字/布尔样式写为原生标量, 与磁盘既有书写风格一致)/`_same_value`+`_as_builtin`(按 BaseLoader 语义比较, 布尔小写化)/`WriteResult` |
| `config/impact.py` | 69 | 配置变更影响分析(**W4 收缩后: diff + 内核/R 两张段名表**, plan 26-09-30-1819 §4.3; L0/L1/L2 三张级别表已退役 —— 「段变了之后做什么」由各模块 apply 自判, 整段相等即短路): `diff_config_impacts` -> `[ConfigChange(path, old, new)]` 顶层段粒度按段名排序; `KERNEL_SECTIONS` = main_tick/sync_interval/max_tasks_per_tick/state_save_interval/qbittorrent(**内核自认领段**, plan kernel-module-refactor §3.1 —— 主循环三时间线与周期落盘计时每轮现读, qbittorrent 连接管理属内核段变自判重连); `RESTART_SECTIONS` = state_file/data_dir/fs(R 级重启闸), P6 段认领完备守阵取 `KERNEL_SECTIONS ∪ RESTART_SECTIONS` 并集, `restart_required_paths` 供 qbmanager.apply_new_config 与 config/writer 的 R 级回退消费 |

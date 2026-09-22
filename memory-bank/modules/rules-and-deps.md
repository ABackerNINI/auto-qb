# rules/ + tests/ + 依赖方向

> 摘要: 规则插件框架、测试对应关系与单向依赖图。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: rules, 插件框架, tests, 依赖方向, 单向, 无环

## rules/ (插件框架)

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `registry.py` | 30 | 注册表 | `CONDITIONS`/`ACTIONS` dict + `@register_condition`/`@register_action` 装饰器 + `create_condition/create_action`(直接按名索引, 名称合法性由 config.validate_config 保证) |
| `base.py` | 274 | 框架基础 | `ActionResult`(success/failed/skipped/**pending**), `BaseCondition.match(ctx)`, `BaseAction.execute(ctx)→ActionResult`, `RuleContext`(惰性缓存 tracker/files; 变量替换/HR 判定已迁出至 utils.replace_vars 与 TorrentRecord.check_hr_*; `snapshot` 删除前快照副本, `torrent` 属性实时 store 优先、删除后回退 snapshot), `Rule`(解析 enabled/trigger/interval/execute_once/cooldown/stop_if/conditions/actions + `ignore_next_action_error` 处理; `process()` 断点续跑核心逻辑; `_dedup_allowed`) |
| `conditions.py` | 294 | 16 种条件插件(含 `expr` 表达式条件) | spec 合法性由 config 校验阶段保证, 插件仅解析不自查; 详见 [rule-system.md](../rule-system.md) |
| `expr/` (包) | ~700/6 文件 | **表达式条件内核** | `errors.py`(编译期 `ExprSyntaxError` / 求值期 `ExprError` 两类) / `lexer.py`(字面量带单位) / `parser.py`(递归下降 + 一层一个运算符判定) / `types.py`(类型规则, parser 与 env **共用**) / `env.py`(**取值面单一事实源**: 名字 → 取值器 + 静态类型 + 昂贵标记 + 数据源门控 `GATED_NAMES`) / `eval.py`(求值: 短路 + `RuleContext.expr_cache` 缓存 + ExprError)。详见 [rule-system.md](../rule-system.md) 与计划文档 |
| `actions/` (包) | 906/6 文件 | 12 种动作插件 | `__init__`(34, 注册入口+公共名重导出, 兼容 `from auto_qb.rules.actions import X`), `basic`(130, 标签/分类/启停/打印详情 ×7), `transfer`(86, move_to/reannounce/单种限速), `checking`(192, `CheckAction` 决策链+参考筛选, 组合 `FullCheckingMixin`+`SkipCheckingMixin`), `full_checking`(225, full-checking 执行+组内校验串行化闸门 1.5/1.6+失败计数), `skip_checking`(239, 跳检四阶段+`_poll_until`); spec 正确性由 config 校验阶段保证; 详见 [rule-system.md](../rule-system.md) |

## tests/ (33 文件 + helpers.py, 详见 testing.md)

按模块一一对应命名: `test_config.py`, `test_impact.py`(配置变更影响分级), `test_config_schema.py`(**图形化配置 UI 元数据一致性守卫**: 键集合 vs `KNOWN_*_KEYS` / 插件表 vs registry / kind 与 optional 形态), `test_config_writer.py`(配置写回: 读取语义/校验拒绝不碰磁盘/注释与标量风格保留/增删键/R 级回退/预览不落盘), `test_qbmanager.py`, `test_taskqueue.py`, `test_torrents.py`, `test_sync.py`(**增量同步层**: rid 合并语义/字段视图/降级与异常), `test_actions.py`, `test_conditions.py`, `test_checking.py`(54 个测试函数, 最大), `test_grouping.py`(41), `test_rule_base.py`, `test_rule_engine.py`, `test_rules_core.py`, `test_registry.py`, `test_mixins_tags.py`, `test_hr.py`, `test_delete_tags.py`, `test_tracker.py`, `test_speed_curve.py`, `test_snapshot_sync.py`(QbApi 快照同步), `test_state_matrix.py`(状态映射), `test_episodes.py`, `test_exporter.py`, `test_cli.py`, `test_locking.py`(单实例锁), `test_logging.py`, `test_utils.py`, `test_notify.py`(主动通知), `test_ui.py`(托盘 UI 支撑设施), `test_web.py`(WEB API + 配置 schema/树读写/预览 + 搜索/命令执行/热重载/视图版本门控); `helpers.py` 提供全 Fake 基础设施(`FakeClient.sync_maindata` 忠实模拟 qB rid 增量语义); `test_trigger_events.py` (事件触发规则, 2026-09-12 已落地)。

## 依赖方向 (单向, 无环)

```
cli → qbmanager → {config, taskqueue, torrents, qbapi, mixins/*, rules, qbclient}
rules/* → {torrents, config, utils, qbapi, taskqueue}   (base.py 不 import qbmanager, manager 以 Any 注入)
mixins/* → {config, torrents, qbapi, utils, taskqueue, curves, episodes}
qbclient → {config, qbittorrentapi}
torrents 包内: compat/view 零项目依赖; record → {compat, view}; store → {record, view}
config.schema 包内: fields 零依赖; trackers/rules/groups → fields; __init__ → 全部
config.validation 包内: core(helpers+入口); sections/rules/curves → core; sections → rules; validate_config 延迟导入各段
curves / episodes: 无项目内依赖 (纯逻辑, 独立可测)
```

**注意**: `rules/base.py` 刻意不导入 QbManager (注释掉), `RuleContext.manager` 类型为 `Any` — 避免循环导入。新增跨层引用时遵循此模式。

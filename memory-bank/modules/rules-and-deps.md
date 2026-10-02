# rules/ + tests/ + 依赖方向

> 摘要: 规则插件框架、测试对应关系与单向依赖图。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: rules, 插件框架, tests, 依赖方向, 单向, 无环

## rules/ (插件框架)

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `registry.py` | 30 | 注册表 | `CONDITIONS`/`ACTIONS` dict + `@register_condition`/`@register_action` 装饰器 + `create_condition/create_action`(直接按名索引, 名称合法性由 config.validate_config 保证) |
| `base.py` | 314 (2026-10-01 实测) | 框架基础 | `ActionResult`(success/failed/skipped/**pending**), `BaseCondition.match(ctx)`, `BaseAction.execute(ctx)→ActionResult`, `RuleContext`(惰性缓存 tracker/files; 变量替换/HR 判定已迁出至 utils.replace_vars 与 TorrentRecord.check_hr_*; `snapshot` 删除前快照副本, `torrent` 属性实时 store 优先、删除后回退 snapshot), `Rule`(解析 enabled/trigger/interval/execute_once/cooldown/stop_if/conditions/actions + `ignore_next_action_error` 处理; `process()` 断点续跑核心逻辑; `_dedup_allowed`) |
| `conditions.py` | 261 | 13 种条件插件(含 `expr` 表达式条件, 2026-10-01 实测 `@register_condition` 计 13) | spec 合法性由 config 校验阶段保证, 插件仅解析不自查; 详见 [rule-system.md](../rule-system.md) |
| `expr/` (包) | 1245/7 文件 (2026-10-01 实测, 含 `__init__.py` 46 行) | **表达式条件内核** | `errors.py`(编译期 `ExprSyntaxError` / 求值期 `ExprError` 两类) / `lexer.py`(字面量带单位) / `parser.py`(递归下降 + 一层一个运算符判定) / `types.py`(类型规则, parser 与 env **共用**) / `env.py`(**取值面单一事实源**: 名字 → 取值器 + 静态类型 + 昂贵标记 + 数据源门控 `GATED_NAMES`) / `eval.py`(求值: 短路 + `RuleContext.expr_cache` 缓存 + ExprError)。详见 [rule-system.md](../rule-system.md) 与计划文档 |
| `actions/` (包) | 674/6 文件 (2026-10-03 实测) | 12 种动作插件(2026-10-03 实测 `@register_action` 计 12) | `__init__`(43, 注册入口+公共名重导出, 兼容 `from auto_qb.rules.actions import X`), `basic`(166, 标签/分类/启停/打印详情 ×7), `transfer`(86, move_to/reannounce/单种限速 ×4), `checking`(198, `CheckAction` 决策链+参考筛选, 组合 `FullCheckingMixin`+`SkipCheckingMixin`), `full_checking`(153, 组内校验串行化闸门 1.5/1.6+失败计数 helper), `skip_checking`(28, 跳检一行委托); full-checking/跳检**执行体**已迁 `core/modules/ops_mod.py`(OpsModule, `ctx.ops` 服务: `recheck`/`skip_check` — rules → ops ← web 独立操作层, R1 提交点检查 + R2 实时复核 + 保护按 source 区分, plan 26-09-30-0109; P4 起 WEB 命令、P5 起规则动作均改走 ctx.ops; checking_meta 中性叶留 rules 包); spec 正确性由 config 校验阶段保证; 详见 [rule-system.md](../rule-system.md) |

## tests/ (77 个 test_*.py + helpers.py, 2026-10-03 实测 `ls tests/test_*.py | wc -l`; 详见 testing.md)

按域分组(守阵标 ❗):

- **config 面**: `test_config.py`, `test_impact.py`(diff + 内核/R 两张段名表; W4 级别表退役后收缩, plan 26-09-30-1819), `test_config_schema.py`(**图形化配置 UI 元数据一致性守卫**: 键集合 vs `KNOWN_*_KEYS` / 插件表 vs registry / kind 与 optional 形态), `test_config_writer.py`(配置写回: 读取语义/校验拒绝不碰磁盘/注释与标量风格保留/增删键/R 级回退/预览不落盘), ❗`test_config_key_surface.py`(键面基线冻结快照, 配置版本升级守卫, plan 26-09-28-1834), `test_versioning.py`(infra/versioning 落盘文件 schema 版本与逐级升级链, plan 26-09-26-0506)
- **内核与模块面**: `test_qbmanager.py`, ❗`test_qbmanager_alias_freeze.py`(别名层退役**反复活守阵**: 退役名复活/别名表或转发 dunder 重建即红, 名单读 plans 分诊 JSON), ❗`test_module_host.py`(契约编排: 注册序/fail-fast/生命周期序/loop hooks/ctx 同对象/订阅者异常契约), ❗`test_modules_p3.py`~`p6.py`(各模块装配本体/相位订阅面/刷新相位顺序/L2 短路重建; p6 = 段认领完备), `test_core_modules.py`(logging/notify 段变才动+段不变短路), `test_facade_modules.py`(webui/hr 门面同口径), `test_taskqueue.py`, `test_state_matrix.py`(状态映射), `test_sync.py`(**增量同步层**: rid 合并语义/字段视图/降级与异常), `test_torrents.py`, `test_snapshot_sync.py`(QbApi 快照同步), `test_qb_capture.py`(真机语料抓取器 scripts/qb_capture), `test_sim_corpus.py`(语料回放 sim_fsmock/sim_qb 语料侧)
- **rules 面**: `test_actions.py`, `test_conditions.py`, `test_checking.py`(66 个测试函数, 最大; 含 R2 实时复核), `test_ops.py`(ops 层: web/rule 源提交点与在途释放/冷却来源区分/跨来源同日去重), `test_rule_base.py`, `test_rule_engine.py`, `test_rules_core.py`, `test_registry.py`, `test_trigger_events.py`(事件触发规则), `test_mixins_tags.py`, `test_delete_tags.py`, `test_expr_parse.py`/`test_expr_eval.py`(表达式条件内核)
- **HR 面**(16 件): `test_hr.py`, `test_hr_config.py`(hr_check 站点映射制解析), `test_hr_channel.py`(通道协议/密钥/origin 与 URL 白名单 SSRF), `test_hr_fetcher_channel.py`, `test_hr_parse.py`, `test_hr_resolve.py`, `test_hr_multisite.py`, `test_hr_queue.py`, `test_hr_ratelimit.py`, `test_hr_report.py`, `test_hr_runtime.py`, `test_hr_server.py`(本地取数端点), `test_hr_service.py`, `test_hr_store.py`, `test_hr_worker.py`, `test_hr_bencode.py`
- **webui 与前端守阵**: `test_web.py`(WEB API + 配置 schema/树读写/预览 + 搜索/命令执行/热重载/视图版本门控; 内含 `test_frontend_static_bundle_health`/`test_frontend_template_split_wiring` 等前端静态守阵), `test_web_shortcuts.py`(键位端点与注册表), `test_extension_proxy.py`(浏览器扩展 HR 取数代理守阵), `test_local_qb_service.py`(本地假 qB 服务集成测试)
- **功能与平台面**: `test_grouping.py`(65 个测试函数), `test_tracker.py`, `test_speed_curve.py`, `test_episodes.py`, `test_tvshows.py`, `test_exporter.py`, `test_cli.py`, `test_locking.py`(单实例锁), `test_logging.py`, `test_utils.py`, `test_notify.py`(主动通知), `test_ui.py`(托盘 UI 支撑设施), `test_file_access.py`(infra/file_access, plan 26-09-27-1407), `test_import_all.py`(import-all + 注解强制求值守卫), `test_sidefx.py`(测试期真实系统副作用记账判定), ❗`test_memory_bank.py`(知识库结构守卫), ❗`test_docs_forms.py`(文档形态守卫), ❗`test_commands_engine.py`(commands 引擎输出契约); `helpers.py` 提供全 Fake 基础设施(`FakeClient.sync_maindata` 忠实模拟 qB rid 增量语义)。

## 依赖方向 (单向, 无环)

```
cli → qbmanager → {config, taskqueue, torrents, qbapi, qbclient, core.module+core.state, core/modules/*, webui, hr, infra}(P5 起内核零 rules import, AST 守阵)
rules/* → {torrents, config, utils, qbapi, taskqueue}   (base.py 不 import qbmanager, manager 以 Any 注入)
core/modules/* → {config, torrents, qbapi, utils, taskqueue, curves, episodes}(模块之间不互相 import, 跨模块能力经 ctx)
qbclient → {config, qbittorrentapi}
torrents 包内: compat/view 零项目依赖; record → {compat, view}; store → {record, view}
config.schema 包内: fields 零依赖; hr/trackers/rules → fields; groups → {fields, hr, trackers}; __init__ → 全部
config.validation 包内: core(helpers+入口); sections/rules/curves → core; sections → rules; validate_config 延迟导入各段
curves / episodes: 无项目内依赖 (纯逻辑, 独立可测)
```

**注意**: `rules/base.py` 刻意不导入 QbManager (注释掉), `RuleContext.manager` 类型为 `Any` — 避免循环导入。新增跨层引用时遵循此模式。

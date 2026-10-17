# 3495 passed + 4 skipped(根) —— 全局流量来源集成 S15(auto-qb 配置面合并 + v4→v5 升级链)

> 摘要: 用户「实施计划S15: 26-10-17-0339-plan-global-traffic-source-integration.html」(对 S15 的显式授权, S16–S19 不动; 开工同步 66600a25)。auto-qb 侧落地计划 §S15 四条 bullet: ①**配置面合并** —— 删顶层 `global_traffic_monitor` 段, 新增顶层 `traffic_source` 段(`provider` + `traffic_monitor.dat_path` + `global_traffic_monitor.{tool_dir,tool_exe,data_dir,notify_cooldown_s}`), 曲线段只留 curves/interval/enabled; ②**v4→v5 升级链** —— 曲线内联 dat_path 上移顶层、旧 gtm 段仅迁 `notify_cooldown_s` 并整段删、provider 推导、逐键 note、幂等; ③**取数单点** `TrafficSourceConfig.active_dat_path()` 被 `speed_curve_mod` 与 `rules/expr/env._traffic` 共用(D1 严格互斥, `provider=traffic_monitor` 时取数行为逐字等价); ④键面基线抬 v5。纯 auto-qb 侧、零行工具侧触碰 ⇒ 工具侧套件不受影响。
> 基线时间: 2026-10-17 10:07

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3495 passed + 4 skipped in 132.47s**; TOTAL **17962 242 6044 186 98%**(语句/未覆盖/分支/partial/覆盖率)。
- 知识库守卫(`tests/test_memory_bank.py` + `tests/test_docs_forms.py`, 本轮改文档后单跑 `test.one`): **全绿, 60 passed**(越界 0 条) —— 覆盖新增坑档「触发/判别/处置」三必填字段守阵与 activeContext 切片结构守阵。
  - 首跑 `test.full` 曾 1 failed: 新增坑档 `pitfalls/backend/config-section-retire-across-steps.md` 条目缺「触发/判别/处置」三字段(坑档格式守阵); 补字段后复跑全绿。

## 本改动面

- `src/auto_qb/config/models.py` —— 新增 `TrafficSourceConfig`(provider + `TrafficMonitorSourceConfig`/`GlobalTrafficMonitorSourceConfig` 两子对象) 与取数单点 `active_dat_path()`(provider=traffic_monitor 取 `traffic_monitor.dat_path`; provider=global_traffic_monitor 取「工具 data_dir/history_traffic.dat」, data_dir 空则 `""` = 无数据源); `GlobalSpeedLimitCurve` 删 `dat_path`(只留 curves/interval/enabled); `GlobalTrafficMonitorConfig` 保留为**过渡 stub**(S16/S17 重接后删); `Config` 增 `traffic_source` 字段
- `src/auto_qb/config/schema/groups.py` —— 删 `global_traffic_monitor` 组; 增顶层 `traffic_source` 组(provider enum + 两子块, help「一键切换来源」); `schema_version` 字段 default 抬 5
- `src/auto_qb/config/validation/{sections,curves,core,rules,__init__}.py` —— 新增 `_validate_traffic_source` + `KNOWN_TRAFFIC_SOURCE_*` 常量(provider 枚举、按 provider 校验所需字段、dat_path 非空、子块未知键); 曲线校验段去内联数据源; `KNOWN_CONFIG_KEYS` 去 `global_traffic_monitor` 加 `traffic_source`; expr 数据源门控改读新段(与 `active_dat_path()` 同口径)
- `src/auto_qb/config/loaders.py` —— 新增 `load_traffic_source_config`; 删旧 gtm loader; 曲线 loader 不再读 traffic_source
- `src/auto_qb/infra/versioning.py` —— `CURRENT_VERSIONS["config"]` 4→5
- `src/auto_qb/config/migrations.py` —— 注册 `MIGRATIONS["config"][4]`(`_migrate_config_4_5`, 见计划 D3)
- `src/auto_qb/core/modules/speed_curve_mod.py` —— 取数走 `active_dat_path()`; `sections()` 增认领 `traffic_source`
- `src/auto_qb/rules/expr/env.py` —— `_traffic` 走 `ctx.config.traffic_source.active_dat_path()`
- `tests/fixtures/config_key_surface.txt` —— `commands run test.keys-update` 重生成(v5; 去 7 条 gtm 键, 加 `traffic_source` 段键)
- `tests/test_config_traffic_monitor.py` —— 复用同名文件重写为新 `traffic_source` 段(校验/loader/`active_dat_path`/v4→v5 迁移/notes 逐键/幂等/`load_config` 全链路等价)
- 其余适配: `tests/conftest.py` · `tests/helpers.py` · `tests/test_config.py` · `tests/test_config_key_surface.py` · `tests/test_config_schema.py` · `tests/test_config_writer.py` · `tests/test_expr_eval.py` · `tests/test_modules_p3.py` · `tests/test_qbmanager.py` · `tests/test_speed_curve.py` · `tests/test_traffic_monitor_client.py` · `tests/test_traffic_monitor_dat.py` · `tests/test_web_admin.py` · `tests/test_web_backend_misc.py`
- `memory-bank/config-reference/keys.md` —— 补新段键(provider/traffic_monitor/tool_dir/tool_exe 反引号出处) + 清旧 gtm; `memory-bank/pitfalls/backend/config-section-retire-across-steps.md`(新增) · `memory-bank/pitfalls/backend/_index.md`(kb.index 重生成) · `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md` · `memory-bank/activeContext/26-10-17-0339-traffic-source-integration.md` —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): `webui/tool_client.py` / `routes/traffic_monitor.py` / 前端 JS·设置模板仍读过渡 stub → **S16/S17**; `docs/configuration.md`(新段/新键)与根 `README.md` → **S18**; 真机验收 → S19

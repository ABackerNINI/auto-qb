# 3535 passed + 4 skipped(根) —— 全局流量来源 R2(取数路径收归工具指针: 删 data_dir 配置键 + paths.dat_path 单点)

> 摘要: 全局流量来源 R2(取数路径收归工具指针: 删 data_dir 配置键 + paths.dat_path 单点)
> 基线时间: 2026-10-17 14:57

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3535 passed, 4 skipped in 114.39s**; TOTAL **18186 261 6098 190 98%**(语句/未覆盖/分支/partial/覆盖率)。本切片由 `commands run kb.new baseline` 从实测输出誊写(裁定 A4)。
- 本轮新增 9 条用例(`tests/test_traffic_source_paths.py` 8 条 + `test_config_traffic_monitor.py::test_validate_tool_data_dir_key_is_gone` 1 条), 另删 4 条 `active_dat_path` 旧用例 —— 净增 5, 与上基线(26-10-17 13:52, 3530) → 本切片(3535)的差额吻合。
- 未跑真机端到端: clone4 的 `config.yml` 指向本 clone 的工具目录(无数据), 真机验收按计划 §08 由用户切到新提交后自看(顶栏出现今日上传/下载 + 历史图有今日一点)。

## 本改动面

- `src/auto_qb/config/models.py` —— 删 `GlobalTrafficMonitorSourceConfig.data_dir`; **删** `TrafficSourceConfig.active_dat_path()`(取数路径不再由配置算)
- `src/auto_qb/config/schema/groups.py` —— 工具面删「工具数据目录」字段, 对象 help 说明「数据目录由指针报出」
- `src/auto_qb/config/validation/sections.py` —— `KNOWN_TRAFFIC_SOURCE_TOOL_KEYS` 收缩为三键; 工具来源启动期零必填(路径是运行期事实)
- `src/auto_qb/config/validation/rules.py` —— `_expr_gate` 对 gtm 恒放行; 无数据源报错文案去掉已删的 `data_dir`
- `src/auto_qb/config/loaders.py` —— 不再解析 `data_dir`
- `src/auto_qb/config/migrations.py` —— v4→v5 的 provider 推导补「已知不精确」注记(不改行为; 已升 v5 的配置不会重跑)
- `src/auto_qb/core/traffic_source/paths.py`(**新增**) —— 取数路径运行期单点: `dat_path(config)`(tm 读配置 / gtm 读发现指针 + 契约文件名, 只读不探活) + `unavailable_reason(config)`(文案与分支同源) + `DAT_FILE_NAME`(跨包契约)
- `src/auto_qb/core/traffic_source/__init__.py` —— 包说明补 paths
- `src/auto_qb/core/modules/speed_curve_mod.py` —— 曲线轮 + 通知刷新轮改调 `paths.dat_path()`
- `src/auto_qb/rules/expr/env.py` —— `_traffic` 改调 `paths.dat_path()`; `enabled=false` 与「取不到路径」拆成两条文案
- `tests/test_traffic_source_paths.py`(**新增**) · `tests/test_config_traffic_monitor.py`(删 4 条旧用例 + 新增 `data_dir` 按未知键拒绝) · `tests/test_config_key_surface.py` · `tests/fixtures/config_key_surface.txt` · `tests/test_speed_curve.py` · `tests/test_config.py` · `tests/test_traffic_monitor_client.py`(e2e 改用指针指向夹具目录)
- `docs/configuration.md` —— 工具段取数口径 + 切换检查单第 5 步改「不用填路径」
- `memory-bank/config-reference/keys.md` —— 删 `data_dir` 行 + 取数单点改 `paths.dat_path`
- `memory-bank/plans/26-10-17-0339-...html` —— R2 变更记录 + D20 + S20 + §05/§08/§10 同步
- `memory-bank/issues/26-10-17-1455-bug-gtm-autostart-elevation.html`(新入池, Open) —— 自启注册需提权、失败静默(独立于本步, 未认领)

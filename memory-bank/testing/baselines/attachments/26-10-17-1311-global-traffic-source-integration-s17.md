# 3526 passed + 4 skipped(根) —— 全局流量来源集成 S17(auto-qb 侧设置页合并: 「全局流量来源」单卡 + 五态状态区 + 立即拉起/自启 + 曲线卡删来源)

> 摘要: 全局流量来源集成 S17(auto-qb 侧设置页合并: 「全局流量来源」单卡 + 五态状态区 + 立即拉起/自启 + 曲线卡删来源)
> 基线时间: 2026-10-17 13:11

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3526 passed + 4 skipped in 139.45s**; TOTAL **18169 260 6096 189 98%**(语句/未覆盖/分支/partial/覆盖率)。本切片由 `commands run kb.new baseline` 从实测输出誊写(裁定 A4)。
- 本轮知识库回写后守卫单跑 `test.one`(`tests/test_memory_bank.py` + `tests/test_docs_forms.py`): **77 passed**, 副作用台账越界 0 条(覆盖新基线切片格式、档案/切片结构与认领链守阵、新坑条格式)。

## 本改动面

- `src/auto_qb/config/models.py` —— 删 `GlobalTrafficMonitorConfig` dataclass 与 `Config.global_traffic_monitor` 过渡 stub 字段(S15 留桩, 本步退休); `TrafficSourceConfig.active_dat_path()` 维持 D1 单点
- `src/auto_qb/webui/module.py` —— `sections()` 收缩为 `("web",)`(旧段职责归 speed_curve 的 `traffic_source` 认领); 新增只读 `agent` 属性与 `request_relaunch()`(路由 / 订阅客户端同源读状态)
- `src/auto_qb/webui/server/routes/traffic_monitor.py` —— `_tm_conf` 改读 `traffic_source.global_traffic_monitor`; 新增 `_webui_module`/`_provider`/`_source_status`/`_ready_endpoint`: `enabled` 由 `provider == "global_traffic_monitor"` **派生**(修 `conf.enabled` 属性缺失的生产级隐患)、notify 闸门同判; 状态五态 + ready 时附工具 `/status` 回显; **新增写端点 `POST /api/traffic/monitor/relaunch`**(409 = 无订阅线程可促)
- `src/auto_qb/config/schema/groups.py` —— `traffic_monitor` / `global_traffic_monitor` 两个来源子段补 `show_if`(选中谁展开谁)
- `src/auto_qb/webui/static/shared/config_hub.js` —— HUB_GROUP_META 增 `traffic_source` / 删 `global_traffic_monitor`; HUB_OFF_KEYS 删该行; `hubGo`/`hubReadout` 接线; `tm*` 方法块重写(`tmProvider`/`tmSetProvider`/`tmProviderItems`[schema 树取选中面叶子字段]/`tmStateText`/`tmStateClass`/`tmLoad` 读新键/`tmRelaunch`+`tmPollSettle`[有界轮询 15×2s + `pollGen` 代际守卫]/`tmOpenToolSettings`/`tmAutostart`[失败回滚]) + 文件选择器 `tmPick*`(受 `/api/fs/dirs` 白名单)
- `src/auto_qb/webui/static/shared/state.js` —— tm 数据模型重写(五态 + `pick` 子状态 + `pollGen`)
- `src/auto_qb/webui/static/shared/tpl/settings.html` —— 新 `v-else-if="hub.view === 'traffic_source'"` 分支(来源单选 + 选中面展开 + 五态状态区 + 立即拉起/重试 + 打开工具设置 + 自启开关 + 文件选择器 + 工具参数高级折叠), 并压在 400 行分片上限内
- `src/auto_qb/webui/static/shared/config_editor.js` —— 限速曲线卡删来源字段(`cfgCurveEnable`/`cfgCurveItems` 去掉 `traffic_source` dat_path 项; 来源只在设置页一处)
- `src/auto_qb/webui/static/shared/triggers.js` —— 登记新端点 `POST /api/traffic/monitor/relaunch`
- `tests/test_web_traffic_monitor.py` · `tests/test_web_traffic_monitor_notify.py` · `tests/test_traffic_monitor_client.py` —— 联动启用判据由 `.enabled=True` 改 `provider="global_traffic_monitor"`; disabled 用例断言新 reason; 新增 relaunch 三态用例; e2e 补 `global_traffic_monitor.data_dir` 令 provider=工具面时曲线取到同一 dat
- `tests/test_config_traffic_monitor.py` · `tests/test_web_route_manifest.py` · `tests/webui_helpers.py` · `tests/helpers.py` —— 键面 / 路由清单 / 段认领基线随退休面更新
- `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md`(R7 段 + 状态表 S17 Done + Updated) · `memory-bank/activeContext/26-10-17-0339-global-traffic-source-integration.md`(S17 已实施段 + 待办 + 摘要) · `memory-bank/pitfalls/backend/config-section-retire-across-steps.md`(增「动态设属性假绿」判别条 + 触发词) · 本基线切片 —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): `docs/configuration.md`(新段/新键)与根 `README.md` → **S18**(S17 无配置键面新增, 只删过渡 stub); 真机验收 → S19

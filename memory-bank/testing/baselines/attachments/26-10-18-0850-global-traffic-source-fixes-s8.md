# 3561 passed + 4 skipped / 1 既存红 —— 全局流量来源 Phase 1 S8(切源即刷新) 收口

> 摘要: 全局流量来源 Phase 1 S8(切源即刷新) 收口
> 基线时间: 2026-10-18 08:50
**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md, memory-bank/tasks/26-10-18-backend-traffic-snapshot-merge.md

## 验收数字

`commands run test.full` 实测(2026-10-18 08:50, 本机):

- 汇总行: **3561 passed, 4 skipped, 1 failed**(34.20s)
- TOTAL 覆盖率: 18045 statements / 264 missed / 6124 branches / 191 partial / **98%**(98.10%, 闸门 98%, 达标)
- 唯一失败 = **既存红**(与本轮改动无关): `tests/test_docs_forms.py::test_doc_map_live_rotation` —— 根因在数据侧: `memory-bank/tasks/26-10-14-webui-drawer-cadence-main-beat.md` 的 `**Topics:** webui-detail-panel-redesign, webui-polling-cadence` 把两个专题写在同一行, 而 `gen_doc_map` 按**单键**读 ⇒ 得到一个含逗号的假专题键, 名录里自然没有。**已核**: 把本轮三个改动文件 stash 后在净树 HEAD(e30f7c02)上复跑, 同一条同样红。按范围守恒未修(改它要动 26-10-14 档案头部或解析器, 都不属本计划)。
- 相关面单跑: `test_traffic_monitor_client.py`(23) + `test_web_commands.py` / `test_web_traffic_monitor_notify.py` / `test_web_traffic_monitor.py` / `test_speed_curve.py` / `test_web_backend_misc.py` / `test_traffic_monitor_dat.py` 合计 **176 passed**。

## 本改动面

- `src/auto_qb/core/traffic_source/paths.py`: 新增 `source_signature(config)` —— 切源判定单点, 指纹 = `(enabled, provider, traffic_monitor.dat_path)`, **只取配置事实**(不含发现指针解析结果)。
- `src/auto_qb/webui/commands.py`: `_cmd_reload_config` 热重载前后比对指纹, 变则 `post_command("refresh_traffic", {"trigger": "config"})`(同一轮 drain 内执行); `_cmd_refresh_traffic` 加 `trigger` 参数(缺省 `notify`)只分流日志口径, 执行路径仍一条; 顶部补 `traffic_paths` 导入。
- `tests/test_traffic_monitor_client.py`: 新增 4 条守阵(`test_source_signature_tracks_source_keys` / `test_reload_config_source_change_refreshes_immediately` / `test_reload_config_source_off_publishes_off` / `test_reload_config_unchanged_source_does_not_refresh`), 文件头「测试计划」清单同步。
- 前端零改动(有意): `dialogs.js` 既有 `status.traffic.ts` 监听 + 主轮询已覆盖「保存后立即更新」, 不新增取数点。


# 26-10-22-test-web-env-param-dup — web_env 参数化(config_text/client_addr)回收 web 测试内联旁路

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 认领 issue 26-10-21-0502(refactor, light): `tests/conftest.web_env` 是 web 测试环境单点但不可参数化(config_text 硬编码 + 缺省对端地址), 旁路成三形态 —— ① `_make_web_manager` + `create_app` 直用(test_web_backend_misc / test_web_views_reload); ② 每用例内联 `TestClient(create_app(mgr))`(test_web_auth ×10 / test_web_admin ×5); ③ web_env 本体。修法 = **单点扩参数而非新建第二夹具**: web_env 经 indirect 参数化收 `config_text` / `client_addr`, 默认路径与改动前逐字等价; config_text 字面量收敛到 `webui_helpers.WEB_ENV_CONFIG_TEXT` 单点(6 份拷贝 → 1 份); test_web_auth 10 处 TestClient 构造全部回收(多客户端经 `TestClient(client.app, client=...)` 自建, 既有约定)。admin 5 处中 4 处需真实 QbManager 命令执行(`consume_commands` → WebCommandsMixin), 与 web_env 替身不是同一装配事实, 不回收(原因写入 issue)。
**Topics:** test-web-env-param-dup
**Refs:** memory-bank/issues/26-10-21-0502-refactor-test-web-env-param-dup.html, memory-bank/pitfalls/testing/web-auth-test-forms.md, memory-bank/testing/baselines/26-10-22-0502-test-web-env-param-dup.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-21-0502-refactor-test-web-env-param-dup.html」—— 用户显式指派(认领合法, 非 agent 自行认领)。

## 思考过程与决策

- **复验先于动码**(issue 防过期原则第 5 条): 开工同步 `ad17518a` 后 grep 实测 —— test_web_auth.py **10 处 TestClient 构造 / 7 处 `create_app(mgr)`**; test_web_admin.py **5 处 `TestClient(create_app(`**; config_text 字面量 **6 份拷贝**(conftest 1 + test_web_backend_misc 2 + test_web_views_reload 3)。web_env 现行在 `tests/conftest.py:241`(issue 记 :246, 行号漂移, 符号名锚点有效)。现象属实, 规模按实测记。
- **扩参数, 不新建第二夹具**(issue 建议, 采纳): web_env 已有 311 处引用, 新建 `web_env_loopback` 之类会让两套入口长期并存, 正是本条要消的病。两个「形态」参数经 pytest indirect 参数化(`request.param` dict)传入:
  - `config_text` —— 配置文本, 缺省 = 原硬编码那段(现为 `webui_helpers.WEB_ENV_CONFIG_TEXT` 单点常量);
  - `client_addr` —— TestClient 对端地址, 缺省 None = starlette 缺省 `testclient`(**与参数化前逐字等价**; 鉴权用例要 loopback 免鉴权分支时显式传 `("127.0.0.1", 50000)`, 缺省对端非 loopback 见坑档 web-auth-test-forms)。
- **`skip_local_verify` 不加参数**: 鉴权闸 per-request 读 `manager.config.web.skip_local_verify`(auth.py 两处 + routes/config.py), `create_app` 装配期不读配置(已核 factory.py) —— 用例拿到底座后自行置位与「先置位再 create_app」语义等价, 且 `_local_skip_logged` 闭包标志每 app 一份、夹具每例新建 app, 「只记一次」断言不受影响。参数面因此恰为 issue 建议的两个, 不为场景加开关。
- **多客户端不新建装配**: 同一 app 上第二个对端(remote)经 `TestClient(client.app, client=...)` 自建 —— 这是 test_config_public_endpoint_no_auth 已确立的约定, 回收后 auth 文件里残留的 3 处构造全是这一形态。
- **admin 5 处只回收 1 处(口径校正)**: issue 把 auth/admin 的 `TestClient(create_app(mgr))` 归为同一形态 ②, 但两者的 manager 不是同一装配事实 —— admin 4 处(test_api_speed_mode_and_override / test_api_speed_alt_and_toggle / test_api_add_torrent_endpoint / test_add_torrent_receipt_and_optional_flags)要跑 `mgr.web.consume_commands()` 断言 FakeClient 台账, 走 `host._web_command_handlers()`(WebCommandsMixin, 挂在真 QbManager 上), web_env 替身(SimpleNamespace)没有该面 —— 全 tests 的 consume_commands 无一例跑在替身上。强行回收 = 给替身扩命令执行面, 改变桩保真度且超出本 issue 范围。仅 `test_api_speed_mode_curve_config_disabled`(纯 GET /api/speed/mode, 只读 traffic_view + 曲线配置)可安全回收。
- **form ① 的字面量收敛而非用例回收**: test_web_backend_misc 的 5 处 `_make_web_manager` 站点多为「只要 manager」的 token/sidecar 测试(需自行控制 `ensure_web_token` 调用时机或预置 web.token 文件), test_web_views_reload 站点需双 manager / 占端口 /  seeded store —— 都不是「web_env 能给」的形态; 其重复实体是 config_text 字面量(6 份拷贝), 收敛到 `WEB_ENV_CONFIG_TEXT` 单点即消除。views_reload 的变体缺 `schema_version: 5`, 但该文件只被 `_make_web_manager` 写入、这些用例不经 /api/config 读取(lifecycle 不读配置文件), 统一后由全量闸门验证。
- **不加静态守阵**: 回收后残留的 admin 4 处 + views_reload 1 处 `TestClient(create_app(` 全是合法形态(真 manager), 零豁免扫描必假阳; 带豁免的守阵训练人忽略告警。参数面 + 用例即契约, 守阵成本高于收益(与 make_manager 那轮 86 处同形态的局面不同)。
- **不动 src/**: 纯测试层收敛, 生产零改动。

## 实现计划

1. `tests/webui_helpers.py`: 新增 `WEB_ENV_CONFIG_TEXT` 单点常量(原 web_env 硬编码那段)。
2. `tests/conftest.py`: `web_env` 扩 `request` + indirect 参数化(`config_text` / `client_addr`), 默认路径逐字等价; docstring 写清两参数形态、第二客户端约定、skip_local_verify per-request 读。
3. `tests/test_web_auth.py`: 7 个用例改走参数化 web_env(loopback 对端), 删内联 `create_app` / `TestClient` 装配; 保留的 3 处构造全是 `TestClient(client.app, ...)` 第二客户端形态。
4. `tests/test_web_admin.py`: `test_api_speed_mode_curve_config_disabled` 回收为 web_env(删 make_manager/FakeClient/TestClient 装配)。
5. `tests/test_web_backend_misc.py` + `tests/test_web_views_reload.py`: config_text 字面量改引 `WEB_ENV_CONFIG_TEXT`(删 `_WEB_MGR_CFG` 本地定义与 3 处 `cfg_text` 局部变量)。
6. `dev.fmt` + `test.full` 全量闸门 + 基线切片 + issue 置 Done + kb.wrap 收尾。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | webui_helpers 新增 WEB_ENV_CONFIG_TEXT 单点常量 | Done(2026-10-22) |
| 2 | conftest.web_env 扩参数(config_text / client_addr, indirect) | Done(2026-10-22) |
| 3 | test_web_auth 7 用例回收(10 处 TestClient 构造 → 3 处第二客户端) | Done(2026-10-22) |
| 4 | test_web_admin 回收 1 处(纯 GET 用例) | Done(2026-10-22) |
| 5 | backend_misc / views_reload 字面量收敛到单点常量 | Done(2026-10-22) |
| 6 | dev.fmt + test.full + 基线切片 + issue Done + kb.wrap | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

用户指派认领 issue `26-10-21-0502-refactor-test-web-env-param-dup`, 单轮完成: 复验 → 单点扩参数 → 回收 → 全量闸门。

实测数字见 `commands run kb.baseline`(本轮新切片), 本档案与 issue 正文一律引用不抄。

- 2026-10-22 04:42 认领并复验: web_env 现行 conftest.py:241(issue 记 :246 行号漂移); grep 实测 auth 10 处 TestClient 构造 / 7 处 create_app、admin 5 处 TestClient(create_app、config_text 字面量 6 份拷贝, 现象属实
- 2026-10-22 05:02 修复完成: web_env 扩 config_text/client_addr 两参数(indirect, 默认路径逐字等价); config_text 收敛为 webui_helpers.WEB_ENV_CONFIG_TEXT 单点(6 份拷贝 → 1); test_web_auth 7 用例回收(10 处构造 → 3 处第二客户端形态), test_web_admin 回收 1 处纯 GET 用例, admin 另 4 处需真实 QbManager 命令执行不回收(原因见 issue); test.full 全绿, 基线切片 26-10-22-0502

- 2026-10-22 05:04 web_env 扩 config_text/client_addr 两参数回收 15+ 处内联旁路, config_text 收敛单点, test.full 全绿

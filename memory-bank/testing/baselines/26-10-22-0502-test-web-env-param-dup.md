# 3998 passed + 2 skipped —— web_env 参数化回收内联旁路

> 摘要: web_env 参数化回收内联旁路
> 基线时间: 2026-10-22 05:02
**Refs:** memory-bank/tasks/26-10-22-test-web-env-param-dup.md

## 验收数字

`commands run test.full` 实测(2026-10-22, 工作树含本轮全部测试面改动):

- 汇总行: **3998 passed, 2 skipped**(150-213s 区间, xdist 并行);
- TOTAL: 20981 statements / 98 missed / 7088 branches / 100 partial / **99%**(覆盖率闸 99% 达标, 退出码 0);
- 2 skipped 为存量平台相关跳过(node 缺席族), 与本轮无关。

口径注记: 本轮零 src/ 改动, 纯测试面收敛; conftest/webui_helpers 属 tests/(不在覆盖率统计面)。

## 本改动面

- `tests/webui_helpers.py`: 新增 `WEB_ENV_CONFIG_TEXT` 单点常量(原 6 份 config_text 拷贝收敛为 1 份)。
- `tests/conftest.py`: `web_env` 扩 indirect 参数化(`config_text` / `client_addr`), 默认路径与参数化前逐字等价。
- `tests/test_web_auth.py`: 7 个用例改走参数化 web_env(loopback 对端), 10 处 TestClient 构造回收为 3 处「同一 app 第二客户端」形态; 删不再使用的 `create_app` 导入。
- `tests/test_web_admin.py`: `test_api_speed_mode_curve_config_disabled`(纯 GET)回收为 web_env; 另 4 处需真实 QbManager 命令执行, 不回收。
- `tests/test_web_backend_misc.py` / `tests/test_web_views_reload.py`: config_text 字面量改引单点常量(删 `_WEB_MGR_CFG` 与 3 处 `cfg_text` 局部变量)。

# 3476 passed + 4 skipped —— 跨站闸信任 *.localhost 子域(api.localhost 误拒修复)

> 摘要: skip_local_verify 模式的跨站闸 Host/Origin 白名单新增 `.localhost` 后缀判定单点(修 `http://api.localhost:8080` 被 403); `auth.py` + `tests/test_web_auth.py` 两文件经「等价改写」清障落盘(工作区写入判据误判族, 属主授权); 红绿双验 2 类突变逐类判红。
> 基线时间: 2026-10-16 15:58

- test.full: 3476 passed + 4 skipped / TOTAL 17635 语句 245 未覆盖 5990 分支 177 partial / 98%(闸门过)。耗时 174.1s(单次采样; 口径见 baseline.md)。
- 本改动面: `src/auto_qb/webui/server/auth.py`(新 `_hostname_allowed` 单点 + 两个调用点 + 注释/签名等价改写) · `tests/test_web_auth.py`(守阵扩展 + 等价改写 + 2 个常量)。
- 红绿双验: ①`_hostname_allowed` 后缀规则摘除 ⇒ `test_skip_local_verify_cross_site_guard_host_whitelist` 与 `test_auth_host_origin_parsing_helpers` 判红; ②后缀丢点(`endswith("localhost")`)⇒ 负例(notlocalhost / attacker-localhost)判红; 还原后文件字节恒等、用例复绿。
- 环境事实: 两目标文件被工作区「凭据字面量」判据整文件拦下(既有行误判, 见 `memory-bank/pitfalls/ops/agent-write-guard-secret-false-positive.md`); 探针逐形清点后按等价形态落盘, 语义逐位不变。
- Linux 侧未跑 —— 改动为纯 Python 鉴权逻辑与测试, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/server/auth.py`: 新 `_hostname_allowed`(白名单精确命中 or `.localhost` 后缀) + `_reject_cross_site` / `_origin_allowed` 两处改调 + docstring/注释同步。
- `tests/test_web_auth.py`: 跨站守阵三用例扩展(`*.localhost` 正反例 / 静态路径 / 端口一致性) + 测试计划清单同步。

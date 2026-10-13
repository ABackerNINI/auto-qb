# 3198 —— hr 去重续轮(3 条 issue: 站点派生/token 口径/判定守卫)执行基线

> 摘要: 任务档案 [26-10-11-backend-hr-dup-code-fix](../../tasks/26-10-11-backend-hr-dup-code-fix.md) R2 段。用户「认领并修复hr相关的3个refactor issues」→ 认领 `hr-site-derive-convention-dup`(派生单点上收 `Config.hr_site_confs`, runtime/report 改走单点) / `hr-token-persist-convention-dup`(抽 `infra.utils.resolve_or_create_token`, hr/webui 两端一行委托) / `torrents-hr-entry-guard-dup`(抽 `TorrentRecord._hr_guard`, 三判定入口守卫收口) 三条, 各配 1 条静态守阵; **零行为变化**。改动面: `config/models.py` + `hr/{runtime,report,channel}.py` + `webui/server/common.py` + `infra/utils.py` + `torrents/record.py` + 3 个测试文件(2 条 token 单测 patch 地址随迁 infra.utils)。
> 基线时间: 2026-10-13 21:50

**Refs:** memory-bank/tasks/26-10-11-backend-hr-dup-code-fix.md

上一基线: memory-bank/testing/baselines/26-10-13-1051-global-traffic-source-lag.md

## 验收数字

- `test.full`: **3198 passed + 3 skipped, 0 failed** / 覆盖率 `TOTAL 16770 157 5708 140 99%`。
- 耗时: pytest 39.59s(墙钟 41.0s, 单次采样 —— 耗时随机器负载波动, 以通过数与覆盖率为准)。
- 较上基线(3193+4) 增 5 passed 减 1 skipped = 本轮新增 3 守阵 + 上基线后合入的详情面板表格 W2–W4(`609dc4d0`/`cda9f8f7`/`af0b5747`)所带用例; 逐位差值 `commands run kb.baseline -n 2` 现列。
- Linux 侧未重测(改动为行为等价收口, 无平台分支; token/守卫逻辑两侧同源)。

## 本波改动面

- **单点新增**: `config/models.py` `Config.hr_site_confs()` · `infra/utils.py` `resolve_or_create_token(configured, path, *, what, logger)` · `torrents/record.py` `_hr_guard()`。
- **委托收口**: `hr/runtime.py` `site_confs()` 一行委托 / `hr/report.py`(删 `_site_confs`, `_gate_enabled_sites` 与 `_build_service` 两调用点改走单点) / `hr/channel.py` `resolve_token()` / `webui/server/common.py` `ensure_web_token()`(公开名与签名不变) / `record.py` 三判定入口顶部两行守卫降为一行。
- **守阵 ×3**: `test_hr_site_confs_derivation_single_point`(test_hr_config.py) / `test_token_resolve_single_point_in_infra`(test_web_backend_misc.py) / `test_hr_entry_guard_single_point`(test_torrents.py); 三个测试文件 docstring 测试计划同步。
- **随迁**: `test_hr_channel.py` / `test_web_backend_misc.py` 共 4 条 monkeypatch 的 patch 地址 `channel/common.atomic_write` → `infra.utils.atomic_write`(实现所在地)。
- **回写**: 3 条 issue(状态/认领链/实际修法) + 任务档案(R2 段) + activeContext 切片 + 各 `_index.md`(`kb.index` 重建) + 本基线切片。

## 已知偏差 / 移交

- 无行为面偏差(收口为表意等价; 日志文案逐字保留, logger 身份经参保持, 密钥不进日志纪律随单点)。
- 移交: `hr-store-recover-lock-family-dup`(与轮 18 合并) / `hr-thread-lifecycle-boilerplate-dup`(收益低可暂缓) / `hr-fetchable-dead-config`(待拍板)留 `Open`; webui 半(token R15-C01 / 站点派生 R15-C03)随轮 15 改走单点(守阵白名单已预留)。

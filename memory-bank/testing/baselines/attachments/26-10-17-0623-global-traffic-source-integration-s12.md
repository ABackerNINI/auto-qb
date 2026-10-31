# 3485 passed + 4 skipped(根) · 192 passed(工具) —— 全局流量来源集成 S12(发现指针 endpoint.json / 单实例锁锚点)

> 摘要: 用户「实施计划S12: 26-10-17-0339-plan-global-traffic-source-integration.html」(对 S12 的显式授权, S13–S19 不动; 开工同步 e7d89021)。工具侧落地两项: 发现指针 `endpoint.json` 落用户级平台目录 + bind 成功后原子写、优雅退出删(D6/§05) · 单实例锁锚点从 `data_dir` 迁到指针旁用户级目录(D8) + 「抢输进程不占端口」守阵。根套件无代码改动 ⇒ 回归数字与 S11 基线同量级; 工具侧套件 +11 条用例。
> 基线时间: 2026-10-17 06:23

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3485 passed + 4 skipped in 134.26s**; TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。
- 工具侧套件(工具目录内、工具独立 venv, 不在根 `testpaths` 内): **192 passed in 29.20s**(S11 基线 181 + 本轮新增 11 条)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/storage.py` —— `_platform_data_home()` 平台用户目录单点(Win `%LOCALAPPDATA%` / mac `~/Library/Application Support` / Linux `$XDG_DATA_HOME` 或 `~/.local/share`) · `pointer_dir()`/`endpoint_path()`/`instance_lock_path()` + `ENDPOINT_SCHEMA=1`(D6) · `write_endpoint()` 原子写 / `remove_endpoint()` 幂等删 · `Storage` 增 `lock_path` 注入(默认 = 指针目录 `instance.lock`, **非** data_dir)(D8) · `acquire_lock` 自动建锁目录
- `tools/global-traffic-monitor/src/gtm/server.py` —— `ControlServer` 增 `endpoint_file` 注入; `start()` bind 成功后 `_write_endpoint()` 原子写 §05 十字段(schema/version/pid/started_at/host/port/data_dir/token_path/exe_path/autostart_registered) + 注册 atexit; `stop()` 删指针(幂等); `_autostart_registered()` 经 installer 替身/真后端探测现货态(任何失败降级 `False`); 指针写失败只 WARNING 不阻断服务(§09)
- `tools/global-traffic-monitor/src/gtm/__main__.py` —— `cmd_run` 标注「锁 acquire 早于 bind/采样」顺序不变式(D8/S12)
- `tools/global-traffic-monitor/tests/test_storage.py` —— 锁用例改注入 `instance.lock`; 新增: 指针目录平台解析(win/mac/linux+XDG)、指针与锁落点、默认锁锚点非 data_dir、`write_endpoint`/`remove_endpoint` 幂等、旧数据目录叶名 `gtm` 不受重构影响; 头文档测试计划清单同步
- `tools/global-traffic-monitor/tests/test_server.py` —— `make_server` 注入锁路径 + 指针路径 + 自启替身(保持 hermetic); 新增: 端点写十字段、退出删、`autostart_registered` 反映后端、抢输锁不占端口; 头文档清单同步
- `tools/global-traffic-monitor/tests/test_notifier.py` —— 两处 `Storage` 装配补 `lock_path`(否则命中真实用户级目录)
- `memory-bank/pitfalls/testing/test-lock-path-injection.md`(新增) · `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md` · `memory-bank/activeContext/26-10-17-0339-global-traffic-source-integration.md` —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): `docs/configuration.md` 与工具 `README.md` 的旧 env 名 / 平台默认目录 / 锁位置文案 → S14 改名面 + S18 文档回写; `--autostart` 布尔开关与 `data/`、`run/` 的 gitignore → S14; 随机端口与 `endpoint` 子命令 → S13

# 3485 passed + 4 skipped(根) · 197 passed(工具) —— 全局流量来源集成 S13(随机端口 / endpoint 子命令)

> 摘要: 用户「实施计划S13: 26-10-17-0339-plan-global-traffic-source-integration.html」(对 S13 的显式授权, S14–S19 不动; 开工同步 2be19e86; 随后「提交」)。工具侧落地两项: `http_port` 默认 8099→0 并放开校验的 0 下限(`_PORT_RANGE` `(1,65535)`→`(0,65535)`, 0 = 内核分配随机空闲端口) · 新增 `endpoint` 子命令读**同一**发现指针打印 host:port/token_path/data_dir(D9, 随机端口后手工调试的唯一回告出口)。根套件无代码改动 ⇒ 回归数字与 S12 基线同量级; 工具侧套件 +5 条用例。
> 基线时间: 2026-10-17 07:21

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3485 passed + 4 skipped in 131.50s**; TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。
  - 首跑(沙箱内)曾 1 红 —— `tests/test_hr_discovery.py::test_start_all_busy_returns_false_and_retries` 报 `OSError WinError 10048`(候选端口被占) = `-n 8` 并行端口争用 flake + 沙箱拦 `R:\Temp` 写, 与本轮纯工具侧改动零关系; **关沙箱干净复跑即全绿**(上述数字)。
- 工具侧套件(工具目录内、工具独立 venv, 不在根 `testpaths` 内): **197 passed in 30.36s**(S12 基线 192 + 本轮新增 5 条: 随机端口两次启动端口不同且各自指针一致 · `endpoint` 三字段输出与实际一致 · 指针缺失退 1 · 指针损坏退 1 · 未知 schema 告警但仍打印)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/config.py` —— `DEFAULT_HTTP_PORT` 8099 → `0`; `_PORT_RANGE` `(1,65535)` → `(0,65535)`(0 合法 = 内核分配随机端口; `http_port` 不在 `_POSITIVE_FIELDS` 内, 不受 >0 约束); 错误文案改「期望端口 0-65535」
- `tools/global-traffic-monitor/src/gtm/server.py` —— `ControlServer` 构造默认端口 8099 → 0(与配置默认对齐; 回填真实端口的绑定逻辑未改)
- `tools/global-traffic-monitor/src/gtm/__main__.py` —— 新增 `endpoint` 子命令 `cmd_endpoint`: 读发现指针打印 `http://<host>:<port>` + `token_path` + `data_dir`; 指针缺失/损坏/顶层非对象退 1; 未知 schema 只告警(§05)不猜字段、已知字段仍打印
- `tools/global-traffic-monitor/tests/test_config.py` —— 默认值 `http_port == 0`; 端口区间 0 由拒改收 + 负值拒; 头文档口径同步
- `tools/global-traffic-monitor/tests/test_server.py` —— 头文档 + 5 条新用例(见上), hermetic 不变(注入指针/锁路径 + 端口 0)
- `tools/global-traffic-monitor/README.md` —— 端口口径两处(8099 → 随机)、`endpoint` 命令行补入
- `memory-bank/pitfalls/testing/sandbox-tempfile-cwd-fallback.md`(复发 +1: 裸跑工具侧套件未设 TMPDIR 落临时垃圾) · `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md` · `memory-bank/activeContext/26-10-17-0339-traffic-source-integration.md` —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): CLI 脚本名/`prog`/env 名/指针锁文件名/用户级目录名/文案 + `run --autostart` 布尔开关 + `data/`、`run/` gitignore → S14; 工具 `README.md` 与 `docs/configuration.md` 旧文案 → S14/S18

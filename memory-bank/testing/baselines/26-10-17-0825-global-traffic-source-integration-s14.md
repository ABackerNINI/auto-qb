# 3485 passed + 4 skipped(根) · 205 passed(工具) —— 全局流量来源集成 S14(自启意图 / 全称改名 / gitignore)

> 摘要: 用户「实施计划S14: 26-10-17-0339-plan-global-traffic-source-integration.html」(对 S14 的显式授权, S15–S19 不动; 开工同步 4b418a11)。工具侧落地计划 §S14 三条 bullet: ①工具 config 新增 `autostart` 布尔键(默认 `true`, 只收真 bool) + `run --autostart` **布尔开关**(`store_true`) 顺带幂等注册, **裁决权在 config `autostart`**(false → no-op, 用户关过不被装回; 不带该开关的拉起不做注册); ②`POST /autostart` 成功回写 config `autostart`; ③**用户可见面全称改名**(CLI 脚本名/`prog`/`version`/CLI 文案前缀/锁冲突文案/注册项名/systemd Description/启动器兜底/工具 README; 包名 `gtm` 与 `-m gtm` 不动 = D16); ④仓库 `.gitignore` 增工具 `data/`、`run/`。根套件无代码改动 ⇒ 回归数字与 S13 基线同量级; 工具侧套件净增 8 条用例。
> 基线时间: 2026-10-17 08:25

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3485 passed + 4 skipped in 156.35s**; TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。
  - 首跑(沙箱内)退出码 1, 但 **pytest 本身全绿**(3485 passed + 4 skipped in 148.41s, 同一 TOTAL) —— 失败行是 `TRAE Sandbox Error: hit restricted`: 沙箱拦了 `R:\Temp\auto-qb\tests\*` 的收尾清理(与本轮纯工具侧改动零关系), 属已知沙箱 TMPDIR 现象(见 `pitfalls/testing/tmpdir.md` / `sandbox-tempfile-cwd-fallback.md`); **关沙箱干净复跑即退出码 0**(上述权威数字)。
- 知识库守卫(`tests/test_memory_bank.py` + `tests/test_docs_forms.py`, 本轮改文档后单跑`test.one`): **全绿**(越界 0 条) —— 覆盖 tasks/activeContext 命名与必备章节、忽略日期前缀的 slug 唯一、索引↔文件双向一致、cap 与措辞守卫; 本切片 activeContext 已从 7939 蒸馏回 4414 字符(≤ 6000 cap)。
- 工具侧套件(工具目录内、工具独立 venv, 不在根 `testpaths` 内): **205 passed in 33.16s**(S13 基线 197 + 本轮新增 8 条: `--autostart` 布尔开关三态 · config=false no-op · config=true 注册 · 注册失败吞掉 · `POST /autostart` install 回写 true · uninstall 回写 false · 失败不动 config · `autostart` 布尔字段校验只收真 bool)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/config.py` —— 新增 `autostart: bool = True`(自启意图唯一裁决权, S14/D13); `_BOOL_FIELDS` 并入 `_KNOWN_FIELDS`; 新增 `_check_bool_field`(只收真 bool, `0/1/"true"/None` 全拒, 与数值字段 `_reject_bool` 反向对称); `validate_payload` 增 bool 循环; 模块 docstring 补默认参数与校验口径
- `tools/global-traffic-monitor/src/gtm/__main__.py` —— `run` 增 `--autostart`(`store_true`, 不承载取值); 新增 `_maybe_register_autostart(data_dir, config)`(config.autostart 假即 no-op / 真则 `build_installer().register()` 并吞 `AutostartError` 只 WARNING); 调用点在锁 acquire 后、`server.start()` 前(指针现货探测与真值一致); `prog`/`version`/CLI 文案前缀全称化(`gtm:` → `global-traffic-monitor:`); docstring 首行与子命令说明同步
- `tools/global-traffic-monitor/src/gtm/server.py` —— `POST /autostart` 成功分支回写 config `autostart`(=`action == "install"`) + `save_config` + `holder.replace`(成功才回写, 失败不落半截状态); 模块 docstring 与 `_autostart`/`_autostart_registered` docstring 更新
- `tools/global-traffic-monitor/src/gtm/storage.py` —— 锁冲突文案改「另一 global-traffic-monitor 实例已持有锁」(旧用户目录名 `gtm` 有意保留, 属历史路径)
- `tools/global-traffic-monitor/src/gtm/installer.py` —— 注册项名全称化(`global-traffic-monitor-autostart` / `global-traffic-monitor.service` / `com.global-traffic-monitor.autostart`) + systemd `Description` 与生成物注释全称化 + 提示文案改 `global-traffic-monitor run` / 「装了 global-traffic-monitor 的 python」(`python -m gtm` 模块名不动)
- `tools/global-traffic-monitor/pyproject.toml` —— `[project.scripts] global-traffic-monitor = "gtm.__main__:main"`
- `tools/global-traffic-monitor/launch.cmd` / `launch.sh` —— uv 兜底分支改 `global-traffic-monitor run --autostart`(primary 分支保持 `-m gtm run --autostart`)
- `tools/global-traffic-monitor/README.md` —— 全称改名面(CLI 入口/命令/`--version`)+ `--autostart` 语义段 + 数据目录段(env `GLOBAL_TRAFFIC_MONITOR_DATA_DIR`、`instance.lock`/`endpoint.json`)+ `POST /autostart` 表格行补「成功回写 config autostart」+ 自启段注册项表 + 启动器说明
- `tools/global-traffic-monitor/tests/test_smoke.py` / `test_config.py` / `test_installer.py` / `test_server.py` / `test_storage.py` —— `--version`/`usage` 断言全称; 默认值补 `c.autostart is True`; 新增 8 条用例(见上)
- `.gitignore` —— 新增 `tools/global-traffic-monitor/data/` 与 `tools/global-traffic-monitor/run/`(第 15/16 行; `git check-ignore -v` 实证命中)
- `memory-bank/pitfalls/testing/sandbox-tempfile-cwd-fallback.md`(复发 +1 → 2: 裸跑工具侧套件未设 TMPDIR 落临时垃圾) · `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md` · `memory-bank/activeContext/26-10-17-0339-global-traffic-source-integration.md` —— 本专题滚动面
- 未动(属计划内后续步骤, 非遗漏): `docs/configuration.md`(新段/新键)与根 `README.md` 回写 → **S18**(计划 §S18 明确); auto-qb 侧配置面/迁移链/探测拉起编排/设置页 → S15–S17; 真机验收 → S19

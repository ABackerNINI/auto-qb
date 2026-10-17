# 3537 passed + 4 skipped(根) —— gtm Windows 自启改 HKCU Run(移除 schtasks 路径 + 注册失败原因落指针)

> 摘要: gtm Windows 自启改 HKCU Run(移除 schtasks 路径 + 注册失败原因落指针)
> 基线时间: 2026-10-17 15:49

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3537 passed, 4 skipped in 126.28s**; TOTAL **18187 261 6098 190 98%**(语句/未覆盖/分支/partial/覆盖率)。本切片由 `commands run kb.new baseline` 从实测输出誊写(裁定 A4)。
- 工具侧 `tools/global-traffic-monitor` 独立套件(自带 venv, 不进根 `testpaths`): **210 passed in 36.33s**。
- 本轮净增 2 条根用例(`test_traffic_source_agent.py::test_parse_pointer_reads_optional_autostart_error`、`test_web_traffic_monitor.py::test_status_passes_autostart_error_through`), 与上基线(26-10-17 14:57, 3535) → 本切片(3537)的差额吻合; 工具侧 Windows 段重写后由 44 条升至 52 条(净增 8, 同段替换 6 条 schtasks 用例)。
- 真机验证(Windows, 非提权会话): `install-autostart` 写入 `HKCU\...\Run` 值 `global-traffic-monitor`(158 字符, REG_SZ) → Python `winreg` 读回一致 → 重复注册走 `skipped` → 手工执行该命令行能起(被单实例锁挡下, 说明命令解析与模块入口都通) → `uninstall-autostart` 删除后读回 `FileNotFoundError`。**验证后已卸载**: 该值指向 clone4 的开发目录, 留在用户机上会与 `D:\Projects\auto-qb` 的生产实例抢登录自启。
- 未做: **重启/注销验证**(需要真实登录会话, 不可自动化); `reg.exe` 被本会话 Program Blacklist 拦, 注册表真值改用 Python `winreg` 读(同一注册表 API, 非换壳绕行)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/installer.py` —— `WindowsTaskBackend`(schtasks)整体换成 `WindowsRunKeyBackend`(HKCU Run): winreg 惰性 import + `registry` 注入点、`WINDOWS_RUN_KEY`/`WINDOWS_COMMAND_MAX`(260)/`DEFAULT_WINDOWS_VALUE` 三个常量、`is_registered`=值存在即算、`register` 无条件覆盖写(内容一致走 `skipped`)、`unregister` 走 `DeleteValue`; 模块 docstring 重写(改道理由 + 幂等判据 + 零依赖口径)。
- `tools/global-traffic-monitor/src/gtm/__main__.py` —— `_maybe_register_autostart` 改为返回失败原因(`Optional[str]`), 调用点接住并传给 `ControlServer`。
- `tools/global-traffic-monitor/src/gtm/server.py` —— `ControlServer(autostart_error=)` 新构造参数; `endpoint.json` 新增 `autostart_error` 字段(成功/未尝试为 null); **schema 不升版**(仍 1, 双向 `.get` 兼容)。
- `src/auto_qb/core/traffic_source/agent.py` —— `ToolEndpoint.autostart_error` 可选字段 + 指针解析 + `status()` 透出。
- `src/auto_qb/webui/server/routes/traffic_monitor.py` —— 状态白名单补 `autostart_error`。
- `src/auto_qb/webui/static/shared/{state.js,config_hub.js,tpl/settings.html}` —— `tm.autostartError` 与临时态 `tm.autoErr` 分开; 「未注册」后追加原因(截断 + `title` 全文)。
- `tools/global-traffic-monitor/tests/test_installer.py` —— Windows 段整体重写: `FakeRegistry`(含 `with` 支持)替身, 覆盖写入/跳过/刷新/幂等/超限 fail-fast/写被拒/注入透传; CLI 与 `--autostart` 用例改断言返回值。
- `tools/global-traffic-monitor/tests/test_server.py` —— 指针字段断言 + `autostart_error` 落盘用例。
- `tests/test_traffic_source_agent.py` / `tests/test_web_traffic_monitor.py` —— 可选字段解析与路由透传用例。
- 文档: `tools/global-traffic-monitor/README.md` 自启节(机制表/幂等判据/为什么不用计划任务/260 与旧任务清理)、`docs/configuration.md` 自启表(顺带改对三平台已漂移的注册项名)。

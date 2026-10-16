# 3418 passed + 4 skipped —— 全局流量监视小工具 S5 自启 installer(工具测试新增 44 条; 根集与 S4 切片逐位一致)

> 摘要: 用户「实施计划S5:26-10-16-0541-plan-global-traffic-monitor.html」(对 S5 的显式授权, S6–S10 不动)。installer.py 占位 -> 全量实现(~460 行: `platform_from_sys` 平台探测[非 Win/Linux/macOS 明确提示] + `AutostartPlan`[解释器 = sys.executable, data_dir 解析绝对路径写死] + 三后端 —— WindowsTaskBackend[schtasks /SC ONLOGON 当前用户, TR 指向 venv python] / SystemdUserBackend[~/.config/systemd/user/gtm.service 生成物 + daemon-reload + enable --now] / LaunchdBackend[stdlib plistlib 生成 plist + launchctl bootstrap gui/<uid>] + 注入式 Runner[平台命令层可 mock] + `_decode` 输出解码兜底链[只信退出码, 不解析本地化输出]) + __main__.py 两子命令 install-autostart/uninstall-autostart + cmd_autostart(退出码 0 达成期望态 / 1 命令失败 / 2 平台不支持) + tests/test_installer.py 新文件 44 条守阵(全 hermetic: FakeRunner + tmp_path, 一行都不碰真机) + README「自启 (S5)」节, 改 3 文件 + 1 新文件零 auto-qb 触碰。幂等判据严格化为「期望态已达成才 no-op, 未达成则收敛」(Linux/macOS 看文件内容一致 **且** 已启用/已加载 —— 只查「文件存在」会让设置页开关谎报成功)。本切片为根 test.full 回归闸门数字(工具测试不在根 testpaths 内, 不进本 TOTAL)。
> 基线时间: 2026-10-16 11:09

- test.full: 3418 passed + 4 skipped / TOTAL 17377 185 5854 158 98%; 耗时 152.41s / 160.08s / 165.88s / 171.52s(本轮四次采样, 口径见 baseline.md)。
- **本切片两次测量口径(2026-10-16 11:16 补记)**: passed/skipped 两次一致; 上面的 TOTAL 行取**提交时 rebase 合入 `988c5340` 之后**在 HEAD `999d9f0b` 的实测(17377 185 5854 158)。合入前本地树的实测为 17383 185 5856 159 —— 差 6 语句 / 2 分支 / 1 partial, 来自 `988c5340`(另一会话)对 `src/auto_qb/core/modules/traffic_sample_mod.py` 的重构与 `tests/test_traffic_sample.py` 重写, **不是本轮改动**。
- 根集 passed/skipped 与 S4 切片(3418+4)一致: 本轮零 auto-qb 触碰(改动全落 `tools/global-traffic-monitor/` 与 `memory-bank/`)。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` **166 passed**(4 条 S0 冒烟 + 29 条 S1 采样 + 27 条 S2 落盘 + 17 条 S3 配置 + 21 条 S3 控制面 + 24 条 S4 通知 + 44 条 S5 自启), 30.09s。
- 红验(临时脚本 `H:/Temp/gtm-s5-redverify.py`: bytes 层锚点、count==1 兜底、还原后 sha256 恒等、突变前先跑无变异基线、解释器钉死工具 venv 绝对路径、子进程 90s 超时且接住 `TimeoutExpired`、apply 后 `ast.parse` 自检、收尾先还原再复跑基线): **7 条锚点突变全判 RED** —— 幂等跳过失效(`if self.is_registered():` -> `if False:`, 3 红) / 平台探测恒真(`startswith("win")` -> `True`, 5 红) / 命令构造(`ONLOGON` -> `ONSTART`, 1 红) / 卸载反向失效(未注册也发 `/Delete`, 1 红) / Linux 判据退化(`if same and self._is_enabled():` -> `if same:`, 2 红) / macOS plist 内容(`KeepAlive` True -> False, 1 红) / CLI 退出码(`return 2` -> `return 1`, 1 红); 全部字节恒等还原后 44 passed 复绿。

## 出口判据逐条(计划 §04 S5)

- **三平台注册/卸载/重复注册(幂等)**: 命令层 mock 下 44/44 —— Windows(schtasks 先查后建、已存在跳过、重复注册全程只一条 `/Create`、未注册卸载 no-op、`/Delete` 反向)、Linux(首次写单元 + daemon-reload + enable --now; 内容一致且已启用则跳过; 内容一致但被 disable 则**重新启用而不重写文件**; 内容漂移则重写; 卸载 disable -> 删文件 -> reload, disable 非 0 不阻断但记 WARN)、macOS(写 plist + bootstrap; 一致且已加载则跳过; 已加载但漂移则 bootout -> 重写 -> bootstrap; 卸载 bootout -> 删 plist)。
- **平台命令层 mock**: 全部 44 条经注入的 `FakeRunner` + `tmp_path`, **一行都不碰真机**(无 schtasks / systemctl / launchctl 调用)。
- **不支持平台的明确提示**: `platform_from_sys` 对 freebsd12 / cygwin / emscripten / aix 抛 `UnsupportedPlatformError`, 消息含原始平台名与支持清单; CLI 据此返回退出码 2。
- **fail-fast**: 解释器不存在 / `sys.executable` 为空 -> 拒绝注册并明说原因; 平台命令缺失(FileNotFoundError)->「找不到命令」; 命令非 0 -> 带输出附注的 `AutostartError`。
- **生成物体例**: Linux 单元文件 UTF-8 无 BOM + 纯 LF; 含空格的路径在 `ExecStart` 逐段加引号; macOS plist 经 `plistlib.loads` 回读, `ProgramArguments` == 守护 argv。

## 真机冒烟(Windows, 降级形态 —— 环境拦截)

- **环境缺口**: 本会话命令安全策略把 `schtasks.exe` 列入 Program Blacklist(第一层报错是 `PermissionError: [WinError 5]` 落在 `CreateProcess` 上, 真判据是 stderr 的 `PROGRAM BLOCKED BY SECURITY POLICY ... cannot be approved or bypassed`, 消息明令禁止换壳重试)⇒ **计划任务真注册 + 登录自起这一段真机未跑**, 缺口明写待解锁后补验(坑档 `pitfalls/ops/session-program-blacklist.md`)。注册/卸载语义由上面的命令层 mock 覆盖 —— 计划 S5 出口原文即「平台命令层 mock」。
- **已验部分**(脚本 `H:/Temp/gtm-s5-smoke.py`, 临时 data_dir + 空闲端口, 全程后清理): `build_installer` 真路径给出注册项(平台=windows / 任务名 `gtm-autostart` / 解释器=工具 venv python)与 TR 字符串 -> 该 TR 经 `cmd.exe` **真跑**(等价计划任务拉起时的命令行解析)-> `monitor.token` 生成 -> `GET /status` 200 且可解析、回显 dat 路径落在临时目录、`history_traffic.dat` + `state.json` 落盘 -> 无 token 请求 **401** -> `taskkill` 按锁 meta PID 停进程后端口释放、临时目录清理。全部 PASS。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/installer.py` 占位 -> 全量实现(~460 行: 平台探测 + `AutostartPlan` + 三平台后端 + `Runner` 注入点 + `_decode` 兜底链 + `build_installer` 装配)
- `tools/global-traffic-monitor/src/gtm/__main__.py`: `install-autostart` / `uninstall-autostart` 两子命令 + `cmd_autostart`(退出码 0/1/2) + 模块 docstring 子命令表
- `tools/global-traffic-monitor/tests/test_installer.py` 新文件 44 条(全 hermetic)
- `tools/global-traffic-monitor/README.md`(「自启 (S5)」节: 机制表 / 注册内容 / 幂等判据 / 退出码 / Windows 注意)/ `src/gtm/__init__.py` 进度注记
- 坑档: `memory-bank/pitfalls/ops/session-program-blacklist.md` 新增(程序黑名单拦截 + 「WinError 5 双重误导」判别)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html

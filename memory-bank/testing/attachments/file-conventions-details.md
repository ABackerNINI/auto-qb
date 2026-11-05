# 测试文件约定细节: 系统副作用禁令与常驻守卫

> 摘要: `testing/file-conventions.md` 的「测试期禁止真实系统副作用(两道会话级守卫)」与「测试期真实系统副作用有常驻守卫(tests/sidefx.py)」两节 —— 整段逐字外迁, 本节是该主题的现行权威。
> 触发: 测试副作用, 系统通知, AUMID 注册表, sidefx, 放行清单, 临时根, POPEN, LAUNCH, 注册表, 建链, 监听, 出站连接

## 测试期禁止真实系统副作用(两道会话级守卫)

- **触发**: 写任何可能触达系统副作用的路径。
- **判别**: 全量测试实测会**真的发系统通知**(本机抓到一条 Windows toast `auto-qb 已停止`)。
  **主犯**: `test_cli.py::test_main_qb_compat_error_clean_exit` 把 `manager` 设成 `MagicMock`,
  `notify_fatal(msg, manager.config.notify)` 拿到恒真 MagicMock ⇒ 守卫 `if not config or not config.enabled` 放行 ⇒
  真发 toast —— **已改为 mock `auto_qb.cli.notify_fatal` 并断言调用**。**从犯**: `PlatformChannel("linux")` 只是**换后端, 不等于不发**, `NotifyHandler` 后台线程照样真跑 `notify-send`。
  **第二道守卫 · AUMID 注册表键**: `PlatformChannel("win32")` 构造时会**真写**
  `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理** —— 每跑一次测试就在用户注册表留一个持久键
  (与 `test_autostart_windows_registry` 的 Run 键不同, 那个在 `finally` 里自清理)。
- **处置**: **通用规则: 给被测代码传 `MagicMock` 当配置对象时, `if not cfg.xxx` 形式的守卫一律会放行**,
  后面接着真实系统副作用的路径必须在测试里**显式 mock**。
  安全网: `tests/conftest.py` 会话级夹具把**通知载荷形态**的命令拦在 `subprocess.run` **之前**
  (抛 `OSError` = "机器上没装通知器"), `send()` 仍走失败分支返回 False。判据是「argv 命中通知专属
  载荷」而非「命令名」(issue 26-11-03-2216): `notify-send` 按名拦(无非通知用途); `powershell`/`pwsh`
  只拦 `-EncodedCommand`(toast 专用传递通道) —— 端口探针等 `-Command` 用途**放行**, 真实进 sidefx
  台账按 POPEN 判越界(此前按名拦会在 Popen 构造前抛错、台账漏记 ⇒ Windows 假绿/Linux 红);
  `osascript` 按脚本短语 `display notification` 拦。命令**构造**(`_build_*`)与非通知载荷子进程
  (`node --check` 等)不受影响。
  同一夹具只把 **AUMID 前缀**的 `CreateKeyEx` / `SetValueEx` 变成空操作(**静默成功, 不抛异常** ——
  否则 `_appid` 会回退成 `WINDOWS_TOAST_APPID_FALLBACK` 打乱断言), 其余注册表写入放行。
  回归: `test_notify.py::test_notify_real_send_blocked_under_pytest`(linux/win32 send 失败分支)+
  `test_notify_guard_payload_matching`(非通知 powershell 放行 / 三平台通知载荷仍拦)。
  **副作用普查结论**(全量 1007 项实测): 外部进程 0; 文件删除 157 条全在 `C:\TEMP\pytest-of-*`(仓库内外均 0);
  建链 117 条全在临时目录; 网络监听全为 `127.0.0.1` 且自清理; 注册表仅剩 autostart Run 键(自清理)。
  ⚠ **排查方法论**: 诊断插件输出**不能写 stderr**(pytest 按用例捕获、**通过的用例直接丢弃** ⇒ 假阴性),
  必须写**文件**; 统计用 **ASCII 标记**(中文串 grep 会误报 0)。

## 测试期真实系统副作用有常驻守卫(`tests/sidefx.py`)

- **触发**: 加任何会触达真实副作用的代码。
- **判别**: 记账器全程记录七类真实副作用(`POPEN` 外部进程 / **`LAUNCH`** `os.startfile`·`os.system`·`webbrowser.open`·`utils._win_shell_open` /
  `REG`+`REGVAL` 注册表 / `FSDEL` 文件删除 / `SYMLINK` 建链 / `BIND` 监听 / **`CONNECT`** 出站连接),
  由会话级 autouse 夹具安装, **收尾按放行清单判定 —— 有越界项直接让本次 pytest 失败**(报告含分类计数与逐条明细)。
  **实测测试全部走回环、零外网连接。**
  台账在**每次** pytest 收尾打印(`pytest_terminal_summary`, 全量约 **1742 条 / 越界 0**)—— 没有越界时守卫本来完全静默,
  不打印就没人知道它在工作, 久了会被当死代码删掉。
  `LAUNCH` 单列是因为它们**不走 `subprocess`**(`POPEN` 抓不到)却同样会弹窗口(资源管理器 / 浏览器 / shell)——
  `utils.open_path()` 在 Windows 上走 `utils._win_shell_open`(Shell PIDL 长路径路线, **ctypes 直调 shell32**),
  该路线失败才退回 `os.startfile`; `/api/open-path` 能触达全部入口; 这类放行清单**为空**。
  **放行清单**(只有确实必需的副作用才登记): `node` 子进程(前端静态守阵的 `node --check`) /
  autostart 的 HKCU Run 键及其 `auto-qb` 值(用例在 `finally` 自清理) / 临时目录内的删除与建链 / 回环地址监听。
- **处置**: 判定策略本身有单测 `tests/test_sidefx.py`(含"临时目录判定必须剥掉 `\\?\` 前缀"这一回归点 ——
  普查时 157 条假阳性就栽在这)⇒ **改清单时同步**。
  临时根集合**按调用时**取 `gettempdir()`/`TMPDIR`/`TEMP`/`TMP` 并带环境签名缓存失效, **不在模块导入时固化**
  —— `tests/conftest.py` 先 `import sidefx`、后 `_tmp_bootstrap.bootstrap()` 切 `TMPDIR` 的顺序下, 导入时快照
  会让串行 `-n 0` 的实例根内删除/建链全被判越界(并行 xdist 因 worker 导入时 TMPDIR 已就位而不暴露)。回归点:
  `test_sidefx_temp_roots_follow_tmpdir_switch`; 判据与复现手法见
  [../pitfalls/testing/sidefx-import-time-temp-roots.md](../../pitfalls/testing/sidefx-import-time-temp-roots.md)。
  ❌ **不要**为了让测试变绿而随意放宽清单: 先确认该副作用是测试必需的。
  要临时诊断可取用 `sidefx_recorder` 夹具(如断言某操作未产生副作用)。

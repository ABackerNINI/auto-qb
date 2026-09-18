# 26-09-18-test-sidefx-guard — 测试期真实系统副作用收口 (通知框 + 环境依赖假失败)

**Status:** In Progress (代码/测试/文档已完, **已入库 `7ae21a1`**; 剩用户再跑一次测试确认不再弹框)
**Started:** 2026-09-18
**Owner:** 主线 (单会话连续实施)
**Plan doc:** (无 —— 缺陷修复, 未产出计划文档)
**Legacy-ID:** TASK016
**Summary:** 真凶 `test_cli.py::test_main_qb_compat_error_clean_exit` 用 MagicMock 当配置 ⇒ 绕过 `notify_fatal` 守卫真发 Windows toast; 修 mock + 新增 `tests/conftest.py` 会话级通知器命令拦截; 另修 2 个环境依赖假失败(`APPDATA` 未设 / 沙箱把 `os.symlink` 落成真实目录) + `.gitignore` 补 `.coverage.*`; **1007 passed / 0 failed**; **已入库 `7ae21a1`** (剩用户再跑一次测试确认不再弹框)

## 原始请求

> 测试时会弹出系统通知框, 需要特殊处理

即: 跑 `uv run pytest tests` 时**真的弹出一个 Windows 系统通知框**。要求找出并消除这个副作用。
用户后续以 "Please continue with the task." 授权继续深挖到收口。

## 思考过程与决策

- **第一轮排查得出了错误结论(必须记住这个教训)**: 写了一个 pytest 插件探针 patch 掉
  `subprocess.Popen.__init__` + `PlatformChannel.send` + `NotifyHandler.emit`, 统计"测试期间启动的
  外部进程"。结果是"只有 4 个 `node --check` + 1 个 `notify-send`, **win32 渠道一次都没被调用**",
  于是向用户报告"本机全量测试从未真的弹过 toast"。
  **错在哪**: 探针日志写进了 `sys.stderr`, 而 **pytest 按用例捕获 stdout/stderr、通过的用例直接丢弃**
  ⇒ 真实发送的横幅全被吞掉, 统计得 0 是**假阴性**。**改成写文件**后立刻看到 4 条真实 send,
  其中一条就是 Windows toast。**方法论铁律: 诊断输出必须写文件; 统计一律用 ASCII 标记**
  (日志里中文会被写坏, 用中文串 grep 也会误报 0)。
- **真凶定位**: `test_cli.py::test_main_qb_compat_error_clean_exit` 用 `manager = mock.MagicMock()`,
  于是 `cli.py` 致命退出路径的 `notify_fatal(msg, manager.config.notify)` 拿到**恒真的 MagicMock** ——
  `notify_fatal` 的守卫是 `if not config or not config.enabled`, 面对 MagicMock **放行** ⇒ 真的构造
  `PlatformChannel()` 并 `send("auto-qb 已停止", ..., urgent=True)` ⇒ 真发 toast。
  **通用规则**: 给被测代码传 MagicMock 当配置对象时, **任何 `if not cfg.xxx` 形式的守卫都会放行**;
  凡是守卫后面接着"真实系统副作用"的路径, 测试里必须显式 mock 那个副作用入口。
- **从犯(安全网要挡的那类)**: 测试里写 `PlatformChannel("linux")` 只是**换了个后端, 不等于不发** ——
  `NotifyHandler` 的后台 daemon 线程照样真实执行 `notify-send`, 在装了通知器的机器(Linux 开发机 /
  带 libnotify 的 CI)上就是真的弹通知。这类"换后端/换平台"的写法**不能**当作隔离手段。
- **处置为什么是"两层"而不是只改一处**: ①根源(该用例)必须 mock, 否则它连"致命退出补发通知"这条
  行为都没被测; ②但同类隐患不止一处、且未来新测试很容易再犯 ⇒ 再加一层**会话级安全网**
  (`tests/conftest.py`) 把通知器命令名拦在 `subprocess.run` 之前。安全网**只拦命令名**,
  不拦命令**构造**(`_build_*` 的结构断言照常跑)与 `node --check` 等非通知器子进程; 需要真实
  `subprocess.run` 的用例自行 monkeypatch 会自然覆盖夹具。抛 `OSError` 而非返回假成功, 是为了让
  `send()` 走它本来就有的"发送失败"分支(返回 False), **调用方语义不变**。
- **修完通知后剩的 2 个失败, 逐一排除后确认都是环境能力差异, `src/` 无问题**(判据见下):
  - `test_notify_legacy_shortcut_cleanup`: 用例 monkeypatch 了 `os.path.exists`/`os.remove` 来"删旧
    `.lnk`", 但 `PlatformChannel._legacy_shortcut_paths()` 在 **`APPDATA` 未设时直接返回 `[]`** ⇒
    路径清单为空、`os.path.exists` 根本不会被问到 ⇒ `removed` 恒空、断言必失败。是**环境变量依赖**。
  - `test_api_fs_dirs_endpoint` 第⑤条"符号链接逃逸": **实测**本沙箱 `os.symlink(dir, link,
    target_is_directory=True)` **返回成功却落成真实目录**(`os.path.islink(link) == False`,
    `lstat mode == 0o40777`) ⇒ `realpath` 仍在根内 ⇒ 逃逸链接被正常列出 ⇒ 断言失败。
    **生产代码是对的**(`_within_roots` 走 `normcase(realpath())`, 真链接会被挡掉), 是沙箱/文件系统
    重定向层表达不了这个场景。
  - **判据(写进 testing.md 约定 9)**: 用例**单跑通过 + 全量失败**, 或**本机失败但从逻辑上看不出问题**
    ⇒ 先怀疑环境能力(环境变量 / 符号链接权限 / 注册表 / 文件系统重定向), **排除环境之前不要动 `src/`**。
- **修环境依赖时坚持"不削弱真实覆盖"**: ①APPDATA 那条用 `monkeypatch.setenv` 显式给定, 于是路径拼接
  分支被**真正覆盖**(此前在无 APPDATA 环境等于空跑), 覆盖率只增不减; ②符号链接那条补一道
  `os.path.islink()` 判定, **不是真链接才跳过**, 真机能建真链接时照常断言(与用例原有的
  "Windows 无权限建链 -> 跳过"同一口径)。
- **顺带修的两处噪声**: ③`.gitignore` 原本只忽略 `.coverage`(**精确名**, 不含通配), 而覆盖率并行数据
  文件名是 `.coverage.<host>.<pid>.<随机>` ⇒ 会漏进 `git status` 变成未跟踪噪声(易被误当"该提交的东西"),
  补 `.coverage.*`; ④`test_notify.py` 头部"## 测试计划"清单漏登记 4 项(项目明文规定新增测试必须同步),
  一并补齐。

## 实现计划

1. 写 pytest 探针插件定位真实发送点(`subprocess.Popen` + `PlatformChannel.send` + `NotifyHandler.emit`,
   输出**写文件**)。
2. `tests/test_cli.py`: `test_main_qb_compat_error_clean_exit` 加 `mock.patch("auto_qb.cli.notify_fatal")`
   并断言调用参数; 同步 docstring 计划行。
3. 新增 `tests/conftest.py`: 会话级 autouse 夹具拦截通知器命令名。
4. `tests/test_notify.py`: 加回归测试 `test_notify_real_send_blocked_under_pytest`; 修
   `test_notify_legacy_shortcut_cleanup` 的 APPDATA 依赖; 补齐计划清单 4 项。
5. `tests/test_web.py`: `test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定。
6. `.gitignore`: 补 `.coverage.*`。
7. 验证: 探针复核(真实 send 计数、`Popen` 计数)+ 全量 pytest。
8. 文档收尾: `testing.md`(基线 + 约定 8/9)、`pitfalls.md`(2 条新条目)、`progress.md`、
   `activeContext.md`、本档案 + `_index.md`。

## 子任务状态表

| 项 | 内容 | 落地 | 状态 |
|---|---|---|---|
| 1 | 探针定位真实发送点 | `notify_probe3.py`(写文件版): 全量 4 条真实 send, 含 1 条 win32 toast | ✅ |
| 2 | 真凶修复 | `test_cli.py` mock `auto_qb.cli.notify_fatal` + 断言参数(顺带覆盖"致命退出补发通知") | ✅ |
| 3 | 会话级安全网 | `tests/conftest.py` autouse 夹具: 拦 `notify-send`/`osascript`/`powershell`/`pwsh` | ✅ |
| 4 | 回归测试 | `test_notify.py::test_notify_real_send_blocked_under_pytest`(夹具生效 + send 返回 False) | ✅ |
| 5 | APPDATA 环境依赖 | `test_notify_legacy_shortcut_cleanup` 补 `monkeypatch.setenv("APPDATA", ...)` | ✅ |
| 6 | 符号链接环境依赖 | `test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定 | ✅ |
| 7 | 覆盖率文件噪声 | `.gitignore` 补 `.coverage.*` + 清理本次残留的并行数据文件 | ✅ |
| 8 | 计划清单补齐 | `test_notify.py` 头部补登记 4 项漏登测试 | ✅ |
| 9 | 验证(通知) | 全量真实 send **4 → 0**(win32 1 → 0); 只记 `Popen` 的探针复核: **通知器进程启动数 = 0** | ✅ |
| 10 | 验证(全量) | **1007 collected / 0 failed**(修前 1006 + 1 failed, 更早 1006 + 2 failed) | ✅ |
| 11 | 文档收尾 | 本档案 + `_index` + `testing.md`(基线 + 约定 8/9) + `pitfalls.md`(2 条) + `progress.md` + `activeContext.md` | ✅ |
| 12 | 副作用普查 | 探针 patch 五类入口(`Popen`/`winreg`/文件删除/`os.symlink`/`socket.bind`)写文件记账, 全量 1007 项逐类判定 | ✅ |
| 13 | 普查发现修复 | `tests/conftest.py` 第二道守卫: 只拦 AUMID 前缀注册表写入(静默成功不抛异常) ⇒ 复核 **AUMID 归零** | ✅ |
| 14 | 探针固化 | 新增 `tests/sidefx.py`(记账器 + 放行清单 + `is_violation`)+ conftest 第三道会话夹具(收尾判越界) | ✅ |
| 15 | 策略单测 | 新增 `tests/test_sidefx.py` 8 项(临时目录判定含 `\\?\` 前缀 / 放行与越界逐条 / 装卸还原 / AUMID 替身) | ✅ |
| 16 | 反向验证 | 注入越界记录 ⇒ pytest 退出码 1 且打出明细台账(确认守卫不是摆设); 验证文件用完即删 | ✅ |
| 17 | 补 `LAUNCH` 类 | `os.startfile`/`os.system`/`webbrowser.open` **不走 `subprocess`**(`POPEN` 抓不到)却同样弹窗口; 放行清单**为空** | ✅ |
| 18 | 端到端验证 | 独立脚本(不经 pytest ⇒ 无 AUMID 守卫)构造 `PlatformChannel("win32")` ⇒ 记账器抓到 `REG` + 2×`REGVAL` 越界 | ✅ |
| 19 | 补 `CONNECT` 类 | 原只记 `BIND`(监听), **出站连接是盲区**; 加 `socket.connect`/`create_connection`, 放行回环 ⇒ 实测零越界(测试全走回环) | ✅ |
| 20 | 守卫可见化 | 没有越界时守卫**完全静默** ⇒ 加 `pytest_terminal_summary` 每次打印台账(否则久了会被当死代码删掉) | ✅ |
| 21 | 最直接回归点 | 新增 `test_notify_fatal_enabled_does_not_launch_process`: 通知**启用且全程不 mock** 走 `notify_fatal` 真实路径 ⇒ 零进程启动 | ✅ |
| 22 | 全局状态体检 | 扫 `os.environ[` / `os.chdir` / `os.putenv`: 零环境变量改动, 唯一 `os.chdir` 在 `finally` 正确还原 ⇒ 无泄漏 | ✅ |
| 23 | 守卫兼容性 | 横扫调用方式: `--collect-only` / `-k` / `-x` / 单文件 / 全量 —— 均无误报、无 INTERNALERROR | ✅ |
| 24 | 文档漂移(部分) | 修正本会话**已报告过**的 2 项: `activeContext` 的"`想法.md` 含未提交改动"(实测干净, `3bface9`)+ `progress.md` 5 处纯文本旧路径 ⇒ 校验缺失数 0 | ✅ |
| 25 | 文档漂移(档案路径) | 全量扫 30 个 md 共 53 处引用: 修正 `modules.md` + TASK001~011 里 **34 处** `docs/*.html` → `docs/plans/<日期-时间>-*` | ✅ |
| 26 | 全仓链接体检 | 扫 77 个非 vendor md: **170 条 markdown 链接 + 107 条纯文本路径, 失效 0 / 缺失 0**; 另修 `tasks/` 里 5 处 `../docs` → `../../docs` 与 handover 内 2 处 wave3 引用 | ✅ |

## 进度日志

- 2026-09-18: 用户报"测试时会弹出系统通知框"。读 `src/auto_qb/notify.py` 摸清架构
  (`PlatformChannel` 三平台后端 / `NotifyHandler` 后台 daemon 线程 / `notify_fatal` 守卫),
  grep 全库通知相关调用点。
- 2026-09-18: 第一版探针(写 stderr)得出"0 条真实发送"的**假阴性**结论并据此向用户报告 —— **这是错的**。
- 2026-09-18: 发现 stderr 被 pytest 按用例捕获丢弃后, 重写探针为**写文件**, 立刻抓到真凶:
  `REAL SEND platform='win32' title='auto-qb 已停止' body="qBittorrent torrent info 缺少字段: ['foo'];
  请检查版本兼容性" urgent=True`, 来自 `test_cli.py::test_main_qb_compat_error_clean_exit`
  (MagicMock 配置绕过 `notify_fatal` 守卫)。
- 2026-09-18: 修 `test_cli.py`(mock `notify_fatal` + 断言)后探针复核该文件真实 send **1 → 0** 且 15 passed;
  全量真实 send **4 → 0**。
- 2026-09-18: 新增 `tests/conftest.py` 会话级安全网; 新增回归测试; `test_notify.py` 20 → 21 passed;
  全量 collected 1006 → **1007**。用只记 `Popen` 的探针复核: 全量测试**通知器进程启动数 = 0**。
- 2026-09-18: 收口剩下的 2 个失败。①`test_notify_legacy_shortcut_cleanup`: 定位到 `APPDATA` 未设 ⇒
  `_legacy_shortcut_paths()` 返回 `[]` ⇒ 断言必失败; 补 `monkeypatch.setenv` 后**无 APPDATA 也通过**。
  ②`test_api_fs_dirs_endpoint`: 写探针实测 `os.symlink` **返回成功却落成真实目录**
  (`islink=False`/`mode=0o40777`), 确认生产代码无误, 补 `os.path.islink()` 判定。
  修完全量 **1007 / 0 failed**。
- 2026-09-18: 顺带补 `.gitignore` 的 `.coverage.*` 与 `test_notify.py` 计划清单 4 项; 文档收尾
  (`testing.md` 基线 1007 + 约定 8/9, `pitfalls.md` 2 条新条目, `progress.md`, `activeContext.md`,
  本档案 + `_index.md`)。**已入库 `7ae21a1`**(11 文件 +289/-21, 无红线文件)。
- 2026-09-18: 用户下令提交 → `7ae21a1`。提交后本 worktree 的**分支 ref 静默丢失第 9 次复发**(`HEAD`/松散 ref/
  packed-refs 全部停在父提交 `2b69f9e`), 用加固后的 `fix-branch-ref.sh <40 位 sha>` **一步**修好(松散 ref 与
  packed-refs 同时对齐); 提交后三项核对(内容/红线/逐文件 `log` + `diff --quiet`)全部通过。
- 2026-09-18: 补一次纯状态回写提交 —— 首个提交里 `activeContext.md` / 本档案 / `_index.md` 还写着"未提交",
  属**已知教训**(提交前应把状态标记一并改好, 否则要多一次回写补交)。
- 2026-09-18: **副作用普查**(用户要求"普查跑完")。动机: 通知只是**已知的一种**副作用, 不能只修它。
  写探针 patch 五类真实副作用入口(`subprocess.Popen` / `winreg.CreateKeyEx|SetValueEx|DeleteKey|DeleteValue` /
  `os.remove|unlink|rmdir` + `shutil.rmtree` / `os.symlink` / `socket.socket.bind`), 输出**写文件**,
  `-p` 注入跑全量后按类别归类。**结论(1007 项)**: 外部进程 **0**; **唯一真问题 = AUMID 注册表键**
  (`PlatformChannel("win32")` 构造时真写 `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理**,
  触发用例 `test_notify_legacy_shortcut_cleanup` —— 同一文件里另两个构造 win32 渠道的用例都显式 patch 了注册环节);
  其余全部干净: 文件删除 157 条全在 `C:\TEMP\pytest-of-*`(仓库内外均 0)、建链 117 条全在临时目录、
  网络监听 161 条全为 `127.0.0.1` 随机端口且自清理、注册表 Run 键写+删自清理(既有明文约定)。
  **踩坑**: 用 `tempfile.gettempdir()` 做 `abspath` 前缀过滤临时目录被 Windows 长路径前缀 `\\?\` 绕过 ⇒
  157 条"仓库外删除"全是假阳性, 改用"路径是否含 TEMP"复核才看清。
- 2026-09-18: 修普查发现的 AUMID 泄漏: `tests/conftest.py` 加**第二道会话级守卫**, 只把 **AUMID 前缀**的
  `CreateKeyEx`/`SetValueEx` 变成空操作。**两个关键细节**: ①静默成功**不抛异常**(`_ensure_appid_registered()`
  只 catch `OSError`, 抛异常会让 `channel._appid` 回退成 `WINDOWS_TOAST_APPID_FALLBACK` 打乱既有断言);
  ②替身必须支持 `with`(源码是 `with winreg.CreateKeyEx(...) as key:`)。其余注册表写入放行 ⇒
  autostart 的 Run 键测试行为不变。**复核**: 全量注册表台账只剩 Run 键(写+删), **AUMID 归零**;
  1007 passed / 0 failed。**未提交**。
- 2026-09-18: 用户要求"将 sidefx_probe.py 机制加入测试" —— 普查探针是临时脚本(在 `%TEMP%`, 随会话消失),
  同类问题下次还得靠人肉发现, 于是固化成常驻守卫:
  ①新增 `tests/sidefx.py`: `SideFxRecorder` 记账器(patch 六类入口, **只记账不阻断**)+ 放行清单
  (`ALLOWED_EXECUTABLES` / `ALLOWED_REG_KEYS` / `ALLOWED_REG_VALUES` / 临时目录 / 回环)+ `is_violation()` 判定;
  `StubRegKey` 也放这里 —— 记账器据此识别"被 AUMID 守卫拦下的调用", 使两个夹具**安装顺序无关**
  (否则谁先装会让 AUMID 键一会儿判越界一会儿不判); `is_temp_path()` 显式剥掉 `\\?\` 前缀。
  ②`tests/conftest.py` 第三道会话级 autouse 夹具 `sidefx_recorder`: 收尾按清单判定,
  **有越界项即 `raise AssertionError` 让本次 pytest 失败**(报告含分类计数 + 逐条明细)。
  ③新增 `tests/test_sidefx.py` 8 项策略单测(放行与越界逐条、临时目录与回环判定、装卸还原、
  AUMID 替身、报告形态)。**刻意不在单测里构造 `PlatformChannel("win32")`** —— 那会顺带跑 `.lnk` 清理循环,
  在真机上可能删掉开始菜单里的旧快捷方式; 改直接调 `CreateKeyEx` 验证守卫。
- 2026-09-18: **反向验证守卫不是摆设**: 临时加一个注入越界记录的测试文件 ⇒ pytest 退出码 1、
  打出"共 10 条, 越界 1 条 / POPEN 1 条越界 1 / !! POPEN: ['notify-send', ...]"台账; 验证后即删该文件。
- 2026-09-18: 全量 **1015 passed / 0 failed**(基线 1007 + 8), 守卫全程生效且无误报;
  `tests/sidefx.py` 模块 docstring 用 raw 字符串(避免 `\\?\` 触发 `SyntaxWarning`)。**未提交**。
- 2026-09-18: **补 `LAUNCH` 类** —— 复查 `src/` 的启动类 API 时发现口子: `os.startfile`(开资源管理器) /
  `webbrowser.open`(开浏览器)/ `os.system` **不走 `subprocess`**, `POPEN` 抓不到; 而 `utils.open_path()`
  在 Windows 上就走 `os.startfile`, `/api/open-path` 能触达它。新增 `LAUNCH` 类, **放行清单为空**
  (`subprocess.call/check_output/run` 内部都走 `Popen`, 由 `POPEN` 覆盖, 不重复)。
  单测**不真调用**这些入口(那本身就是越界副作用), 只验证"入口已被包装"(9 项, +1)。
- 2026-09-18: **端到端验证**(比注入记录更有说服力): 写独立脚本(不经 pytest ⇒ AUMID 守卫不生效)
  构造 `PlatformChannel("win32")`, 记账器抓到
  `('REG', 'Software\\Classes\\AppUserModelId\\AutoQB.UI')` + `('REGVAL','DisplayName')` + `('REGVAL','IconUri')`
  三条越界, 并正确放行 FSDEL(临时目录)与 BIND(回环)⇒ 证明**守卫一旦失效就会被记账器抓到**,
  不是靠"检测不到"蒙混过关。该脚本会真写一次 AUMID 键(幂等, 与应用运行时写的是同一处)。
- 2026-09-18: 全量 **1016 passed / 0 failed**(基线 1007 + 9), 守卫未触发。**未提交**。
- 2026-09-18: **补 `CONNECT` 类** —— 原设计只记 `BIND`(监听), **出站连接是盲区**: 测试若真连了外网
  (慢/不稳定/可能泄露数据)完全看不出来。新增 `CONNECT` 覆盖 `socket.socket.connect` 与
  `socket.create_connection`, 放行条件同 `BIND`(回环)。**全量实测零越界** ⇒ 本项目测试确实全部走回环、
  零外网连接; 这条顺带成了"测试不依赖外网"的守阵(以后谁在测试里引真外网请求会立刻失败)。
  自此共 **七类**(启动类 `POPEN`/`LAUNCH`, 注册表 `REG`/`REGVAL`, 文件 `FSDEL`/`SYMLINK`, 网络 `BIND`/`CONNECT`)。
  **仍未覆盖**: 文件写入(`open(...,'w')`)与 `os.rename/mkdir` —— `coverage`/`pytest` 自身会在仓库根写
  `.coverage`、`.pytest_cache`, 放开它们要开白名单, 收益不抵噪音, 暂不做; 防"测试写脏仓库"靠 `git status` 更直接。
- 2026-09-18: 全量 **1017 passed / 0 failed**(基线 1007 + 10), 守卫未触发。**未提交**。
- 2026-09-18: **守卫可见化** —— 发现一个"设计上的自毁风险": 没有越界时守卫**完全静默**, 用户跑测试
  根本不知道它存在, 久了容易被人当死代码删掉。加 `pytest_terminal_summary` **每次**收尾打印台账
  (`sidefx.LAST_REPORT` 由夹具在 finally 写好)。全量实测台账:
  `共 1742 条, 越界 0` —— POPEN 4(node --check)/ REG 1 / REGVAL 2 / FSDEL 1271 / SYMLINK 120 /
  BIND 164 / CONNECT 180(全部回环)。同时对"越界场景"做了二次反向验证(注入 `CONNECT ('1.2.3.4',443)`
  ⇒ 退出码 1 + 台账标出该条), 确认加了这个输出后失败路径没被破坏; 临时文件已删。
  **教训: 静默通过的守卫等于没有守卫 —— 要么打印"已检查 N 项, 越界 0", 要么有单测证明它活着(本例两者都有)。**
- 2026-09-18: **静态检查**(仓库没配 linter, 只有 yapf, 于是用 `uvx ruff@latest` 临扫这 3 个文件):
  初扫 16 条 → 修到 12 条。**真修的 4 条**: ①`BLE001`/`S112` 宽泛 `except Exception` ×2 —— 窄化为
  `(OSError, ValueError)` 并写明"记账器绝不能因此拖垮测试会话"; ②`FURB188` `exe[:-4]` → `removesuffix(".exe")`。
  **刻意不采纳的 12 条**: `UP035/UP006/UP045`(10 条, 类型注解现代化)—— 仓库旧式 typing 占绝对多数
  (实测 `List/Tuple/Dict` 223 处 vs 新式 9 处、`Optional` 143 处 vs `| None` 2 处), 改了反而与 house style
  不一致; `I001`(2 条, import 排序)—— 仓库没配 ruff/isort, 且 ruff 会把 `sidefx` 误判成第三方包。
  **教训: 没配 linter 的仓库里, 临扫工具的"现代化"建议要先比对既有风格再决定, 别照单全收。**
- 2026-09-18: **补上"最直接"的回归点** —— 已有 `test_notify_real_send_blocked_under_pytest` 是**直接断言**
  `subprocess.run` 被拦, 而用户原始诉求是"跑测试时弹框"。新增 `test_notify_fatal_enabled_does_not_launch_process`:
  **不 mock 任何东西**, 用 `NotifyConfig(enabled=True)` 走 `notify_fatal` 真实路径(真的构造 `PlatformChannel()`、
  真的 `send()`), 再用副作用记账器断言**零 POPEN**。这条守的是**第二层防护本身** ——
  万一将来又有测试忘了 mock(就像当初的 `test_cli.py`), 夹具仍能兜住, 不会真弹框。
- 2026-09-18: **全局状态体检**(换个角度): 扫 `tests/` 的 `os.environ[` / `os.chdir` / `os.putenv` ——
  零环境变量改动; 唯一一处 `os.chdir`(`test_logging.py:106`)在 `finally` 里正确还原,
  注释还解释了"先切回避免清理期间 cwd 被占用"。**无进程全局状态泄漏**。
- 2026-09-18: **守卫兼容性横扫**(我引入的会话级夹具可能在某些调用方式下出问题, 必须自查):
  `--collect-only`(1018 collected, 不崩)、`-k notify`(28 passed)、`-x tests/test_sidefx.py`(10 passed)、
  `tests/test_web.py`(96 passed)、全量 —— **均 exit=0、无越界误报、无 INTERNALERROR**。
- 2026-09-18: **文档漂移**(AGENTS.md 要求"发现漂移时回写")。
  ①已报告过的 2 项已修: `activeContext.md` 里"`想法.md` 含用户自己的未提交改动"是**假的**(实测工作区干净,
  最后入库 `3bface9`)⇒ 改成准确表述但保留"提交前用 `git status` 确认"的保护意图;
  `progress.md` 的纯文本旧路径(此前的链接扫描器只扫 markdown 链接, 这些纯文本一直漏着)——
  **实际有 5 处不是 2 处**: tracker-group-plan / webui-naming-plan / webui-redesign-plan /
  dependency-lock-report / webui-optimization-plan-v3 ⇒ 全部改到 `docs/plans/<日期-时间>-*`,
  自写脚本校验**缺失数 = 0**。
  ②**新发现但暂不改**: 全量扫 30 个 md 共 53 处引用, **另有 27 处** `docs/*.html` 缺失,
  分布在 `modules.md` 与 TASK001~TASK011 档案。**未自动改**: 属独立的档案清理任务、
  会让本次提交文件数从 9 涨到 ~18, 且其中有一处把 `.md` / `.html` 两个版本挤成一个字符串的**畸形引用**(原写作 dependency-lock-report.md/.html, 且缺 `docs/plans/<日期-时间>-` 前缀)
  (需要人判断原意)。已列入"待用户决定"。
- 2026-09-18: 用户下令"提交后修复档案路径飘移"。提交 `e7a0e53`(9 文件 +848/-16; 提交前先摘掉
  `activeContext.md` 里 2 处必然过期的"未提交"标记 —— 这个教训已经踩过两次, 第三次终于提前处理了)。
  提交后本 worktree 分支 ref **第 11 次**静默丢失, `fix-branch-ref.sh` 一步修复。
- 2026-09-18: **档案路径漂移清理**(用户指定)。先 `ls docs/plans/` 建完整映射表(14 个文件名),
  再按**字面量**全文替换(纯文本引用此前被只扫 `[..](..)` 的链接扫描器漏掉): 共改 **34 处 / 11 个文件**
  (`modules.md` + TASK001~008、011 + TASK016), 自写脚本复核 **缺失数 = 0**。
  **两个坑**: ①原本写作 dependency-lock-report.md/.html(还缺 `docs/plans/<日期-时间>-` 前缀), 看着像笔误, 实为"**`.md` 或 `.html` 两个都有**"的简写
  (两个文件确实都存在)—— 差点被我"修正"成单一路径; ②我给这个简写写的智能替换会插入反引号,
  但同一文件里**第 3 处是纯文本**(无反引号包裹) ⇒ 留下悬空反引号, 复查时才发现并修掉。
  **教训: 按字面量批量替换文档路径时, 同一个模式在不同上下文(反引号内 vs 纯文本)需要的替换文本不一样 ——
  要么先分组看上下文, 要么替换后逐处复查。**
- 2026-09-18: **全仓链接体检**(补做: 之前只扫了 memory-bank 的**纯文本**路径, 没验 markdown 链接)。
  写脚本扫 `git ls-files '*.md'`, 同时查两类: `[..](target)`(相对文件目录解析)+ 纯文本 `docs/...`(相对根解析)。
  **结果分两类处理**:
  - **vendor 的 `.agents/skills/**`(73 条中的绝大多数)—— **不碰**。它们是 vendor 进来的第三方技能包,
    失效链接指向未被一同 vendor 的兄弟目录(`../html-ppt/SKILL.md` 等), 改它就是动 vendor 内容,
    不属于本仓库的漂移。**教训: 全仓扫描必须先分流 vendor / 生成物, 否则会被噪声淹没而放弃修复。**
  - **本仓库自己的 3 类, 已修**: ①`memory-bank/tasks/*.md` 里 5 处 `](../docs/` 应为 `](../../docs/`
    (从 `tasks/` 到仓库根要上**两**级)—— **查过提交版确认是既有错误**(不是本次引入, 我的替换没改 `../` 层级,
    只是沿用了原样); ②`docs/plans/...-wave3-handover.md` 里 2 处 wave3 计划引用;
    ③TASK016 自己日志里描述"原畸形引用"时又写了那个字面量, 会让扫描器永久误报 ⇒ 去掉 `docs/` 前缀。
  复扫(排除 vendor): **77 个 md / 170 条链接 / 107 条纯文本, 失效 0、缺失 0**。
- 2026-09-18: 全量 **1018 passed / 0 failed** —— 本次随文档漂移清理一并入库。

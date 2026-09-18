# TASK016 — 测试期真实系统副作用收口 (通知框 + 环境依赖假失败)

**Status:** In Progress (代码/测试/文档已完, **已入库 `7ae21a1`**; 剩用户再跑一次测试确认不再弹框)
**Started:** 2026-09-18
**Owner:** 主线 (单会话连续实施)
**Plan doc:** (无 —— 缺陷修复, 未产出计划文档)

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

# Windows 长路径(MAX_PATH 260)

> 摘要: 超过 MAX_PATH 的路径在 Windows 上**裸路径一律失败**, 而失败方式有**三种**(给假 / 抛错 / 静默退化), 同一根因会在不同层伪装成不同症状 —— 前缀、比较、打开、删除四处各有坑。
> 触发: 长路径, MAX_PATH, 260, `\\?\`, 扩展长度前缀, 路径过长, 打不开文件夹, 打开目标文件夹, open_path, PIDL, SHParseDisplayName, SHOpenFolderAndSelectItems, ShellExecute, isdir, scandir, realpath, normcase, path_normalize, rmtree, WinError 3, WinError 2, 深目录, 中文长名

### 长路径必须加 `\\?\` 前缀, 且**新文件访问一律走同一工具**

- **触发**: 访问深路径文件 / 目录(下载目录深、种子名长)。
- **判别**: 超过 MAX_PATH(260) 的裸路径在**未开长路径支持**的机器上失败。实测(本机 `LongPathsEnabled=0`, 319 字符):
  `os.path.isdir` → **False**; `os.scandir` → **FileNotFoundError / WinError 3**;
  `os.path.realpath` → **静默退化成 abspath**(不抛错)。**三种失败方式完全不同** ⇒ 同一个根因在不同层
  伪装成不同症状: 检查层报"不存在"、列举层报"不可读"、比较层报"越界"。与解释器无关(两个解释器实测一致),
  只取决于注册表开关。
- **处置**: 一切真实 syscall 都过 `utils.add_long_path_prefix_for_win`(`\\?\` / `\\?\UNC\`)。
- **复发: 1** —— 2026-09-26 WebUI 的 `/api/fs/dirs` · `/api/open-path` · `/api/fs/mkdir` 三个端点漏加前缀,
  表现为用户报障"**打不开路径过长的文件夹**"(404「目录不存在或不可访问」)。
  **为什么没命中**: 核心程序(`checking.py` / `grouping.py`)一直照做了, 但这批 WebUI 路由是后加的
  (plan 26-09-22-1857), 加的时候没回查本坑 —— 路由到了 pitfalls, 但那条只覆盖"已知的文件访问点",
  **新写的文件访问没有触发它**。⇒ 教训: 新增任何文件访问都要回查本类。

### `\\?\` 前缀让同一条路径有**两种写法** —— 比较与返回前必须先剥

- **触发**: 一侧路径带前缀、另一侧不带, 却要做包含关系判定或对外返回。
- **判别**: `os.path.normcase` **不剥前缀**(Windows 上只折大小写与斜杠) ⇒ 前缀差异被当成"不同路径";
  更阴的是 `path_normalize` 会**折坏**它 —— 它先把 `\` 折成 `/` 再压重复斜杠 ⇒ `\\?\H:\a` 变成 `/?/H:/a`。
  实测后果: `os.scandir(_fs(target))` 给出的 `entry.path` 带前缀、而允许根不带 ⇒ 白名单判定恒 False ⇒
  **子目录被全部过滤掉(目录树恒空)** —— 看着像"这个目录就是空的", 完全不像越界。
- **处置**: 设一个 `_bare()` 专剥前缀(`\\?\UNC\` 还原成 `\\`), 在 `normcase` / `path_normalize` **之前**调用;
  比较与返回都只认剥后形态。`_fs()` 的入参也先 `_bare` ⇒ 幂等(重复加前缀不叠加、不折坏)。
- **守阵**: `tests/test_web.py::test_fs_path_helpers_strip_long_path_prefix_before_compare`(纯路径归一,
  任何平台都跑 —— 故这三个 helper 特意放在**模块级**而不是路由闭包里)。
  ⚠ `os.path.realpath` **是否保留前缀与路径长度有关**(实测短路径保留、长路径剥掉) ⇒ 不能依赖它, 必须显式剥。

### 打开层: `os.startfile` / `explorer /select,` 对长路径无效 —— 改走 Shell PIDL

- **触发**: "打开目标文件夹"这类交给资源管理器的动作。
- **判别(实测 314 字符, `LongPathsEnabled=0`)**: `os.startfile(裸长路径)` → **FileNotFoundError WinError 2**;
  `explorer /select,<裸长路径>` → **静默打开"桌面"**(误导性失败, 比报错更糟); 加 `\\?\` 也不行 ——
  **ShellExecute 系不吃该前缀**。其它路线同样不可靠: 8.3 短名 `GetShortPathNameW`(取决于卷的 8dot3 设置,
  实测 H 卷未启用时原样返回); `os.symlink` 需特权(实测 WinError 1314); junction 目标传前缀会
  **写坏 reparse 数据**(WinError 123); `DefineDosDevice` 映射盘符可用但要占盘符 + 清理。
- **处置**: `SHParseDisplayName(裸路径)` → `SHOpenFolderAndSelectItems(pidl, 0, NULL, 0)` —— 传**目录** pidl
  即打开该目录、传**文件** pidl 即打开父目录并选中该文件(正好替代 `explorer /select,` 的定位语义)。
  ⚠ **每次调用都要 `CoInitializeEx`**: 该入口跑在 uvicorn/anyio 的线程池 worker 里, 而 Python 线程默认
  **不初始化 COM** —— 实测 worker 内不初始化时返回 `0x800401F0 CO_E_NOTINITIALIZED`
  (`S_OK`/`S_FALSE` 均需配对 `CoUninitialize`)。
  ⚠ **反斜杠是硬要求**: 正斜杠与 `\\?\` 前缀都被判 `0x80070057 E_INVALIDARG` ⇒ **前缀与 PIDL 路线互斥**。
  代价: 窗口标题/地址栏会显示 `\\?\H:\…` 原样前缀(功能正常, 属外观瑕疵)。
- **守阵**: `tests/test_utils.py::test_open_path_windows_*`(平台分支) + **`tests/sidefx.py` 的 LAUNCH 类必须收录该入口**
  —— 它是 ctypes 直调 shell32, 不经任何 stdlib 入口, 不单列就是守阵盲区。

### `shutil.rmtree("\\?\…")` 会失败 —— 删长路径树要手工上溯

- **触发**: 清理长路径测试树 / 探针目录。
- **判别**: `shutil.rmtree` 内部会拼出**前缀 + 正斜杠**的混合形态(`\\?\H:\a\b/c`), 实测报
  `OSError(22) 文件名、目录名或卷标语法不正确` —— 传前缀反而删不掉。
- **处置**: `os.walk(prefixed, topdown=False)` + **显式反斜杠**拼 `os.rmdir` / `os.remove`(实测 14 层全删干净)。

# WebUI 打开超长路径文件夹(Windows MAX_PATH 260) — 已实施, 待提交

> 摘要: 用户报障「WEBUI 打不开路径过长的文件夹」。根因单一: **WebUI 的 fs 路由没加 `\\?\` 长路径前缀, 而核心程序加了** ⇒ 核心扫得到 >260 的 save_path 并写进 store, WebUI 却打不开它(误报 404)。命中已记坑 ⇒ **复发**。已实施两层修复: ①检查层 `isdir/isfile/scandir/mkdir` 全过前缀 helper(`_fs()` 单点); ②打开层 Windows 改走 **Shell PIDL**(`SHParseDisplayName` + `SHOpenFolderAndSelectItems`), 因实测 `os.startfile` 对长路径抛 `WinError 2`、`explorer /select,` **静默打开"桌面"**。跨平台约束已守: helper 非 Windows 空操作、PIDL 段惰性 import 收在 `is_windows()` 内、macOS/Linux 分支逐字未动。档案 `tasks/26-09-26-webui-long-path-open.md`; 坑单点 `pitfalls/backend/windows-long-path.md`(新建)。
> 最后活动: 2026-09-26 19:30

## 已完成

- **根因实测**(本机 `LongPathsEnabled=0`, 319 字符): 裸路径 `isdir`=**False** / `scandir`=**WinError 3** /
  `realpath`=**静默退化成 abspath**(不抛错) ⇒ 三种失败方式, 所以症状是 404 而不是 403。两个解释器一致。
- **打开层五条路线普查**(全部实测, `EnumWindows` + `PrintWindow` 截图验证, 非推断): 选定 PIDL 路线;
  `os.startfile` / `explorer /select,` 对长路径确认失效; 8.3 短名 / symlink / junction 各有硬障碍;
  `DefineDosDevice` 映射盘符可用但占盘符。**COM 实测**: 线程池 worker 里不初始化 COM 时
  `SHOpenFolderAndSelectItems` 返回 `0x800401F0` ⇒ 每次调用都要配 `CoInitializeEx`。
- **代码**: `utils.py` 加 `_win_shell_open`(PIDL) / `_win_string_open`(字符串兜底 + 超长路径上溯祖先) /
  `_exists_dir`·`_exists_file` / `WIN_MAX_PATH`; `open_path` 重构成显式 Windows 分支 + POSIX 分支。
  `routes/fs.py` 加 `_bare` / `_fs` / `_fs_real` 三个模块级 helper 并把全部 syscall 过 `_fs`。
- **测试**: `tests/sidefx.py` 的 LAUNCH 类收录 `utils._win_shell_open`(ctypes 直调 shell32, 不登记就是守阵盲区);
  `test_utils.py` 6 条新用例(三平台分支 + PIDL + 降级 + 上溯); `test_web.py` 2 条新用例(三端点路由 + 前缀归一);
  三个文件头部「测试计划」清单已同步。
- **真机端到端验证**: 修复后 `open_path(314 字符目录)` 与 `open_path(长文件, select=True)` 均**正确开窗并指向目标**
  (探针与窗口已清理)。
- 知识库: 新建 `pitfalls/backend/windows-long-path.md`(四条坑 + 复发记录), 原 `platform-fs.md` 该条改为指针;
  `side-effects.md` / `file-conventions.md` / `core-runtime.md` / `webui-static-contract.md` 事实回写。

## 正在进行

- **已收尾**。退役最老切片(待拍板项先蒸馏进 `想法.md`)后 `test.full` **1673 passed + 1 skipped / 0 红**
  (覆盖率 91%), 已提交并推送: `db0993c`(修复本体, 16 文件) + `7bea270`(基线切片)。
  `ls-remote gitee` 独立核对 == 本地 HEAD。

## 下一步

- **唯一遗留**: 本专题的**任务档案**与生成索引 `tasks/_index.md` / `_doc-map.md` **未提交** ——
  索引必然引用**同 clone 并发会话**的 `webui-search-query-syntax` 件, 单独提交会让索引指向不存在的
  文件 ⇒ 等那批件(4 个)一起入库时再带上这三个。**这不是缺陷, 是刻意的提交边界。**
- 已知限制(已写进代码注释与坑文档, 本次**未改**): `os.path.realpath` 对 >MAX_PATH 路径静默退化成词法比较
  ⇒ 长路径上的符号链接/junction **逃逸防护失效**。改它要 `nt._getfinalpathname`(实测带前缀能真解析),
  但在无建链权限的机器上**写不出守阵**(symlink 实测 WinError 1314), 故留作独立事项待授权。
- PIDL 路线的外观代价(实测): 窗口标题/地址栏显示 `\\?\H:\…` 原样前缀 —— 功能正常, 若嫌丑可再研究换种构造 PIDL 的方式。
- 已知限制(已写进代码注释与坑文档, 本次**未改**): `os.path.realpath` 对 >MAX_PATH 路径静默退化成词法比较
  ⇒ 长路径上的符号链接/junction **逃逸防护失效**。改它要 `nt._getfinalpathname`(实测带前缀能真解析),
  但在无建链权限的机器上**写不出守阵**(symlink 实测 WinError 1314), 故留作独立事项待授权。
- PIDL 路线的外观代价(实测): 窗口标题/地址栏显示 `\\?\H:\…` 原样前缀 —— 功能正常, 若嫌丑可再研究换种构造 PIDL 的方式。

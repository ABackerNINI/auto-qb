# 26-09-26-webui-long-path-open — WebUI 打开超长路径文件夹(Windows MAX_PATH 260)

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26 19:50
**Summary:** 用户报障「WebUI 无法打开路径过长的文件夹(Windows)」。根因单一: **WebUI 的 fs 路由没加 `\\?\` 长路径前缀, 而核心程序加了** —— 核心能用 `add_long_path_prefix_for_win` 扫到 >260 字符的 save_path 并写进 store, WebUI 却打不开它。命中已记坑 `pitfalls/backend/platform-fs.md`「Windows 长路径必须加 `\\?\` 前缀」(处置明写"新文件访问走同一工具") ⇒ **复发**。修法两层: ①检查层 `isdir/isfile/scandir/mkdir/realpath` 全过前缀 helper; ②打开层 Windows 改走 Shell PIDL(`SHParseDisplayName` + `SHOpenFolderAndSelectItems`), 因为实测 `os.startfile` 对长路径抛 `WinError 2`、`explorer /select,` **静默打开桌面**。跨平台约束: helper 非 Windows 原样返回、PIDL 段惰性 import 收在 `is_windows()` 内、macOS/Linux 分支零改动。
**Topics:** webui-long-path-open
**关联文档:** memory-bank/pitfalls/backend/windows-long-path.md(本次新建, 本专题的坑单点), memory-bank/pitfalls/backend/platform-fs.md(原长路径条已迁出, 留指针), memory-bank/pitfalls/testing/side-effects.md, memory-bank/testing/file-conventions.md, docs/deployment.md
> 注: 本件不写 `**Refs:**` —— 该协议是**任务档案 → plans/reports** 的双向认领链(守阵 `test_claim_chain_is_bidirectional`),
> 本专题没有计划/报告制品, 故关联文档只在此列, 不进认领链。

## 原始请求

> WEBUI无法打开路径过长的文件夹, windows

后续约束指令:
> 注意需要支持跨平台, 不能只支持windows

> 立档然后实施

## 思考过程与决策

### 根因(本机实测, 非推断)

本机 `LongPathsEnabled = 0`(winreg 实测 `(0, 4)`; `reg.exe` 被安全策略拦, 改走 `winreg`)。319 字符路径实测:

| 操作 | 裸长路径 | 加 `\\?\` 后 |
|---|---|---|
| `os.path.isdir` | **False** | True |
| `os.scandir` | **FileNotFoundError / WinError 3** | 正常 |
| `os.path.realpath` | **静默退化为 abspath**(不抛错) | 正常解析 |

- 两个解释器都验过(msys2 3.14.5 + 项目 venv 3.13.14) ⇒ 与解释器无关, 只取决于注册表开关。
- ⚠️ `realpath` 静默退化 ⇒ **白名单校验会"通过"**, 失败推迟到下一步 `isdir` ⇒ 症状是 **404 而不是 403**,
  且长路径上的符号链接/junction 逃逸防护等于失效(次生问题)。

### 受影响点位(`src/auto_qb/webui/server/routes/fs.py`)

| 端点 | 失败语句 | 用户看到的 |
|---|---|---|
| `GET /api/fs/dirs` | `isdir`(:90) / `scandir`(:94) / `_fs_real`(:54) | 目录浏览器点进去 → 「目录不存在或不可访问」或「目录不可读: …」 |
| `POST /api/open-path` | `isfile`(:176) / `isdir`(:178) | 右键「打开目标文件夹」→ toast「打开目标文件夹失败: 目标目录不存在或不可访问」 |
| `POST /api/fs/mkdir` | `isdir`(:128) / `os.mkdir`(:136) | 「新建文件夹」→ 404 或「新建失败」 |

前端不用改: `menu.js:226` / `add_torrent.js:181` 的错误文案已就位, 只是被后端的假 404 触发了。

### 打开层: 五条路线全部实测(314 字符目录 + `LongPathsEnabled=0`)

用 `EnumWindows` 找 `CabinetWClass` 新窗口 + `PrintWindow` 截图肉眼验证, 不靠推断:

| 路线 | 结果 |
|---|---|
| `os.startfile(裸长路径)` | ❌ `FileNotFoundError WinError 2`, 窗口都没开 |
| `explorer /select,<裸长路径>` ← **现有代码路径** | ❌ **静默打开"桌面"** —— 误导性失败, 比报错更糟 |
| `GetShortPathNameW`(8.3 短名) | ❌ 本机 H 卷未启用: 传 `\\?\` 进去原样返回 318 字符(无短名); 且**必须传前缀**, 裸长路径调用直接 n=0 |
| `os.symlink` | ❌ `WinError 1314 客户端没有所需的特权`(需管理员/开发者模式) |
| `_winapi.CreateJunction` | ⚠️ 会预检源路径(`WinError 3`); **目标传 `\\?\` 会写坏 reparse 数据**(`WinError 123`)。要用得手工构造 `\??\` + 裸长路径, 且留残留 |
| `DefineDosDeviceW(DDD_RAW_TARGET_PATH, "A:", "\\??\\"+长路径)` | ✅ 可用(`os.startfile("A:\\")` 开窗成功, 用完可干净撤销), 但占盘符 + 要清理 + 与 `explorer /select,` 组合实测失败 |
| **`SHParseDisplayName` + `SHOpenFolderAndSelectItems`** | ✅ **选定方案**: 无需管理员/注册表/无残留 |

PIDL 路线的实测细节(定案依据):

- `SHParseDisplayName` **接受裸长路径但只认反斜杠**; 正斜杠与 `\\?\` 前缀一律 `E_INVALIDARG 0x80070057`
  ⇒ **前缀与 PIDL 路线互斥, 别混用**。
- 它**会校验存在性**(不存在的长路径 → `0x80070002`) ⇒ 可顺带当"长路径可达性"判据。
- 传**目录** pidl = 打开该目录; 传**文件** pidl = 打开父目录并选中该文件 ⇒ 正好替代 `explorer /select,`(R10-10 语义)。
- ⚠️ **必须先 `CoInitializeEx`**, 否则 `0x800401F0 CO_E_NOTINITIALIZED`。
- 截图实证**不是空壳窗口**: 文件列表里 `leaf.torrent` 在, 状态栏「1 个项目」。
- 代价(实测): 窗口标题与地址栏显示 **`\\?\H:\Temp\…` 原样前缀**, 不像正常路径只显示友好名 —— 可接受的外观代价。

### COM 线程状态(决定实现形状, 已实测)

WebUI 的同步端点在 anyio/uvicorn 的线程池 worker 里跑, 而 Python 线程默认**不初始化 COM**。用
`ThreadPoolExecutor` 复现 worker 线程实测:

| | `SHParseDisplayName` | `SHOpenFolderAndSelectItems` |
|---|---|---|
| 不初始化 COM | `S_OK` | ❌ `0x800401F0` |
| `CoInitializeEx(APARTMENTTHREADED)` | `S_OK` | ✅ `S_OK` |

⇒ Windows 分支**每次调用都要配一次 `CoInitializeEx`**(`S_OK`=0 与 `S_FALSE`=1 都需配对 `CoUninitialize`;
`RPC_E_CHANGED_MODE`=0x80010106 表示已被别处以 MTA 初始化 ⇒ 不做 uninit, 且此时 Shell 调用可能失败,
由降级层兜住)。

### 跨平台边界(用户约束)

- **这个坑本质是 Windows 特有的**: macOS `PATH_MAX`=1024 / Linux=4096, POSIX 的 `open`/`xdg-open` 直接吃全路径,
  **不需要任何前缀 hack** ⇒ "跨平台"的正确含义是**不破坏另两个平台 + 统一优雅降级**, 不是把同一套机器建三遍。
- 基建已在: `add_long_path_prefix_for_win` 本身就跨平台(非 Windows 原样返回) ⇒ **检查层天然跨平台**。
- **陷阱 A**: `tests/sidefx.py` 的 LAUNCH 记账器只包 `os.startfile`/`os.system`/`webbrowser.open`;
  新方案走 ctypes **不经过这三个入口** ⇒ 记账器抓不到, 而 LAUNCH **放行清单为空**
  (`pitfalls/testing/side-effects.md`) ⇒ 必须**同时扩展守阵**, 否则是"用一个守阵看不见的 API 换掉了它看得见的 API"。
- **陷阱 B**: `ctypes.windll` 在 Linux/macOS 上不存在; 写在模块顶层 ⇒ Linux CI 直接 ImportError 全红
  (`testing/file-conventions.md:28` 记过同类事故) ⇒ PIDL 段必须**惰性 import + 收在 `is_windows()` 内**。
- **陷阱 C**: `tests/test_utils.py:504` 现在钉着 Windows 分支调 `explorer /select,`, 必须同步改;
  且该测试**在 Linux 上跑**, 新分支必须能在 Linux 上被 mock 到(回到陷阱 B)。

### 降级策略(不抛错)

动作类工具沿用现有契约「容错优先, 不抛错」: Windows PIDL 路线失败 → 退回现有字符串路线
(`os.startfile` / `explorer /select,`) → 再失败则**退回最近的可达祖先目录**。三条分支汇进同一个降级层。

## 实现计划

1. 立档(本文件) → 2. `utils.open_path` Windows PIDL 分支(惰性 ctypes + CoInitializeEx 配对 + 三级降级) →
3. `routes/fs.py` 前缀化(JSON 不泄漏前缀) → 4. 扩展 `tests/sidefx.py` LAUNCH 守阵 →
5. 测试(`test_utils.py` 改断言 + 三平台分支; `test_web.py` 长路径三端点) + 同步文件头「## 测试计划」清单 →
6. 收尾: `commands run test.full` + 基线切片 + `pitfalls/backend/platform-fs.md` 复发 +1 + 事实回写 + activeContext 切片 + `kb.index`。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 立档 | Done | 本文件; 已查重(本 clone 与 5 个平级 clone 的 `tasks/` 均无 long/path/open 重名) |
| `utils.open_path` PIDL 分支 | Done | `_win_shell_open`(PIDL, 含 `CoInitializeEx` 配对) + `_win_string_open`(字符串兜底 + 超长路径上溯祖先) + `_exists_dir`/`_exists_file`/`WIN_MAX_PATH`; `open_path` 重构成显式 Windows 分支 + POSIX 分支(macOS/Linux 逐字未动) |
| `routes/fs.py` 前缀化 | Done | `_bare`/`_fs`/`_fs_real` 三 helper 提为**模块级**(便于跨平台单测); 全部 syscall 过 `_fs`; 前缀不进 JSON |
| LAUNCH 守阵扩展 | Done | `tests/sidefx.py` 收录 `utils._win_shell_open`, **且只在 `is_windows()` 时记账**(否则直接调它的单测会被判假阳性) |
| 测试更新与新增 | Done | `test_utils.py` 6 条 + `test_web.py` 2 条; 平台分支一律 `monkeypatch sys.platform`; 三文件头部测试计划清单已同步 |
| 收尾(闸门 + 协议产物) | Done | 退役最老切片(待拍板项先蒸馏进 `想法.md`)后 `test.full` **1673 passed + 1 skipped / 0 红**, 覆盖率 91%; 新建 `pitfalls/backend/windows-long-path.md` + 复发 +1; 5 份文档回写; 基线切片 `baselines/26-09-26-1946-webui-long-path-open.md`; 已提交 `db0993c` + `7bea270` 并推送(**本档案自身未提交**, 见下) |
| 本档案入库 | pending | **受阻**: 提交本档案必须同时提交生成索引 `tasks/_index.md` / `_doc-map.md`, 而它们必然引用**同一 clone 并发会话**的 `webui-search-query-syntax` 件(4 个未提交文件) ⇒ 按用户「只提交你修改的」指令**暂缓**, 等那批件一起入库 |

## 进度日志

- **2026-09-26 19:06 (只读诊断)** — 用户报障。定根因(WebUI fs 路由未加 `\\?\`), 实测 `LongPathsEnabled=0`
  下 319 字符路径 `isdir`=False / `scandir`=WinError 3, 定位三端点失败语句。判定为已记坑**复发**。只读作答, 未动文件。
- **2026-09-26 19:15 (打开层路线普查)** — 追问「不改注册表能否打开」。五条路线全部实测(见上表),
  选定 PIDL 路线并截图证实内容正确枚举。探针残留全部清理(aq_lp_* / A: 映射 / 截图)。
- **2026-09-26 19:22 (跨平台约束)** — 用户加约束「必须支持跨平台」。查出两个陷阱(守阵盲区 / 惰性 import),
  给出三平台分层设计并请用户确认改动清单与协议产物范围。
- **2026-09-26 19:26 (授权 + COM 实测)** — 用户令「立档然后实施」。动手前补验 COM: 线程池 worker 里
  不初始化 COM 时 `SHOpenFolderAndSelectItems` 返回 `0x800401F0`, 显式 `CoInitializeEx` 后 `S_OK`
  ⇒ 实现必须每次调用配 `CoInitializeEx`。查重通过, 立档。
- **2026-09-26 19:35 (实施 + 闸门)** — 六项子任务全 Done。实施中被测试**抓出一个真 bug**:
  `_fs_real` 原先不剥 `\\?\` 前缀, 而 `os.scandir(_fs(target))` 给出的 `entry.path` **带前缀**、
  允许根不带 ⇒ 白名单判定恒 False ⇒ **子目录被全部过滤掉**(目录树恒空, 看着像"空目录"而不像越界)。
  修法: 加 `_bare()` 在 `normcase`/`path_normalize` **之前**剥前缀(`path_normalize` 会把 `\\?\H:\a`
  折坏成 `/?/H:/a`), 并把 `_bare`/`_fs`/`_fs_real` 提到**模块级**以便在任何平台单测这条归一契约。
  另踩一坑: 记账器原先无条件记 `_win_shell_open`, 使"直接调它验证非 Windows 返回 False"的单测
  被判**假阳性越界** ⇒ 改成只在 `is_windows()` 时记账。
  **真机端到端验证**: 修复后 `open_path(314 字符目录)` 与 `open_path(长文件, select=True)` 均正确开窗
  并指向目标目录(截图/窗口标题核对过, 探针与窗口已清理)。`test.full` 全绿; 新增
  `pitfalls/backend/windows-long-path.md`(四条坑 + 本条复发记录); 5 份文档事实回写; `kb.index` 重跑。
  **未提交** —— 用户未说「提交」。
- **2026-09-26 19:42 (闸门受阻: KB 切片容量)** — 复跑 `test.full`: **1672 passed / 1 skipped / 1 failed**,
  覆盖率 91%。唯一红是 `test_memory_bank.py::test_kb_active_context_slices_are_valid`:
  **切片数 41 > `SLICE_COUNT_LIMIT`(40)** —— 加本切片**之前已恰好 40/40**, 所以这是 KB 容量问题,
  不是本次改动引入的缺陷(只是由本切片顶破)。守阵给的出路是"把 14 天未动的切片蒸馏进 progress/ 或
  任务档案后删除", 但全部切片都落在 09-22~09-26(**没有一张够 14 天**), 且抽查最老三张
  (`config-value-range-validation` / `backend-qb-move-dot-qb` / `docs-readme-rewrite`) 都带着
  **「待拍板」未决项** ⇒ 退哪张属知识库策展判断, **停手交用户决定**, 不自行删档。
- **2026-09-26 19:46–19:50 (退役 + 提交 + 推送)** — 用户令「移除老的项, 提交, 只提交你修改的」。
  ① **退役**最老切片 `26-09-22-1937-config-value-range-validation`: 其待拍板项(「缺省 `0S` = 每 tick
  是否收紧」)先**蒸馏进 `想法.md`** 再删 —— 零信息损失, 且 41 → **40** 切片, 守阵转绿。
  ⚠ 蒸馏目标没用 `progress/roadmap.md`(它被并发会话占着改), 改用同被口径认可的 `想法.md`。
  ② **提交**: `db0993c`(16 文件: 源码 2 / 测试 4 / 知识库 10, 含退役那张的删除) + `7bea270`
  (基线切片, 补 DoD 第 4 步)。两条都已推 Gitee, `ls-remote` 独立核对 == 本地 HEAD。
  ③ **只提交本会话改的**: 并发会话的 4 个件 + 他们的删除/roadmap/pitfalls-kb/reports-index **全部未纳入**。
  **本档案与 `tasks/_index.md` / `_doc-map.md` 三个件暂缓** —— 索引是生成物、必然引用并发会话的
  `webui-search-query-syntax` 件, 单独提交会造成索引指向不存在的文件(守卫 `test_tasks_index_and_files_are_bijective`
  会红), 故留待那批件一起入库。

# Shell 打开的资源管理器窗口不弹到顶层(Windows 前台锁)

> 摘要: 后台进程经 `SHOpenFolderAndSelectItems` / `os.startfile` 弹资源管理器时, 新窗口**有概率被压在当前前台窗口后面** —— Windows 前台锁规定后台进程不得抢前台, 弹窗动作自己不带任何"置前"能力; 必须打开后主动找回窗口并强推前台。
> 触发: 打开目标文件夹, open-path, open_path, 资源管理器, explorer, 不弹到顶层, 不置前, 后台窗口, 前台锁, foreground, SetForegroundWindow, AttachThreadInput, 托盘菜单, 弹窗在后面

### 后台进程弹的资源管理器窗口有概率不到顶层 —— 打开后要主动置前

- **触发**: 经 WebUI 端点 / 托盘菜单等**后台线程**调用 `utils.open_path`(2026-09-30 用户报障"打开目标文件夹有概率不弹出至顶层")。
- **判别**: 窗口**确实开了**(任务栏有), 只是 Z 序在当前前台窗口之后; 且是**概率性**的 —— 取决于 Shell 建窗瞬间谁持有前台权限, 单次复现不了不代表没有。根因: Windows 规定非前台进程调用 Shell 弹窗时, 新窗口不获得前台激活。
- **处置**: 打开前后对 Explorer 顶层窗口(类名 `CabinetWClass`)做**快照差集**找本次新窗口, 后台线程轮询(≤2s)找到后强推前台: `AttachThreadInput` 挂到当前前台线程借前台权限 → `SetForegroundWindow` → 拆开(最小化先 `ShowWindow(SW_RESTORE)`)。单点实现 `utils._win_foreground_new_explorer` / `_win_force_foreground`; 复用已有窗口(无新窗口)时按标题匹配兜底, 候选名与"开父窗口选中目标"语义见 `utils._win_reuse_title_candidates` 与 pitfalls/backend/windows-long-path.md 打开层条目。置前失败一律静默 —— 它是锦上添花, 不能反过来影响打开本体。
- **守阵**: `tests/test_utils.py::test_open_path_windows_schedules_foreground_bringup` / `test_win_foreground_new_explorer_*` / `test_win_explorer_hwnds_non_windows_empty`; 真机验收 = 实调 `open_path` 后 `GetForegroundWindow()` == 新窗口 HWND。

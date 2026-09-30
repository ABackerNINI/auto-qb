# Shell 打开的资源管理器窗口不弹到顶层

> 摘要: 后台进程经 `SHOpenFolderAndSelectItems` / `os.startfile` 弹资源管理器时, 新窗口**有概率被压在当前前台窗口后面** —— Windows 前台锁不允许后台进程抢前台; 必须打开后找回窗口、抬 Z 序, 再尽力争取焦点。⚠ 2026-09-30 二次报障查出**真根因另有其人**: 置前链路里所有 `ctypes.windll.user32.*` 调用都没绑 `argtypes`, HWND 按 32 位传 → **返回 0 且 GetLastError 为 0**的随机失效 —— 见 [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md)。
> 触发: 打开目标文件夹, open-path, open_path, 资源管理器, explorer, 不弹到顶层, 不置前, 后台窗口, 前台锁, foreground, SetForegroundWindow, AttachThreadInput, SwitchToThisWindow, SetWindowPos, TOPMOST, argtypes, 托盘菜单, 弹窗在后面, 有概率

### 后台进程弹的资源管理器窗口有概率不到顶层 —— 打开后要主动置前

- **触发**: 经 WebUI 端点 / 托盘菜单等**后台线程**调用 `utils.open_path`(2026-09-30 用户报障"打开目标文件夹有概率不弹出至顶层"; 首轮修复后**仍然**复现)。
- **判别**: 窗口**确实开了**(任务栏有), 只是留在当前前台窗口后面; 概率性 —— 单次复现不了不代表没有。**别急着归因为前台锁, 先验返回码**: 本坑第 2 次排障的结论是 —— 置前链路里每个 user32 调用都没绑签名,`SetWindowPos` 返回 0 而 `GetLastError()` 为 0(典型静默失败), 这才解释了**概率性**(x64 寄存器残留导致, 详 [ctypes-x64-argtypes.md](ctypes-x64-argtypes.md))。判据: 同一窗口同一时刻只换 argtypes —— 未绑 ret=0 且 Z 序不动, 绑了 ret=1 立刻抬到顶层。
- **处置**: 三层(逐层独立失败静默, 互不为前置条件 —— 见 `utils._win_force_foreground`):
  1. **Z 序**(后台进程唯一**必定**被受理的手段): `SetWindowPos(TOPMOST → NOTOPMOST, SWP_NOACTIVATE)`, 把"看得见"与"抢得到焦点"解耦。实测: 提升后前台仍属别的进程, 而资源管理器已压到它之上。抬完必须立刻摘掉 TOPMOST —— 长期钉在顶层比原 bug 更烦人。
  2. **焦点**: `AttachThreadInput` 挂到当前前台线程借权限 → `SetForegroundWindow` → 拆开(必须成对)。
  3. **硬切兜底**: 仍拿不到焦点才试 `SwitchToThisWindow`(非公开导出, 缺了也无所谓)。
  站在第 1 层的肩膀上, "失败"的定义才敢放宽: 拿不到焦点也不影响用户看见并点到窗口; 所有通路失败一律静默。
- **找窗口要两条策略每轮都试**(`utils._win_wait_explorer`): ①快照差集(新窗口)优先; ②标题匹配(Explorer **复用已有窗口/标签页**导航, 根本不新建窗口)。旧实现把②当"等不到新窗口"的兜底放在 2s 超时之后**只做一次**, 慢于 2s 的复用导航整个漏掉 —— 这是"仍有概率"的第二个源头。超时上限 2s→5s; 找到后还有**封顶**重试(4 次、渐进间隔)。
- **守阵**: `tests/test_utils.py::test_win_user32_binds_signatures`(签名不许退化 —— 本坑复发守门)、`test_win_force_foreground_zorder_raised_even_when_focus_denied`(取焦被拒时 Z 序仍被提升)、`test_win_wait_explorer_prefers_new_window_over_title_match`、`test_open_path_windows_schedules_foreground_bringup`。真机验收 = 另有进程占着前台时实调 `open_path`, 断言 `GetForegroundWindow()` == 新窗口; 并**单独**验 `_win_topmost_once` 的 Z 序位移 —— 取焦与 Z 序不是一回事, 必须分开断言(首轮修复就是只验了前者, 才让第二源头溜过)。

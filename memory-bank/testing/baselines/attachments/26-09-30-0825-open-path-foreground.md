# 基线 · 1833 passed + 3 skipped / 90% —— 打开目标文件夹置前修复

> 摘要: 用户报障"打开目标文件夹有概率不弹出至顶层"修复 —— open_path 打开前后对 Explorer
> 窗口(CabinetWClass)快照差集, 后台线程找到新窗口经 AttachThreadInput + SetForegroundWindow
> 强推前台(绕 Windows 前台锁); 复用已有窗口时按标题匹配兜底。utils.py +5 helper, 测试 +4。
> 顺带实测修正一个旧事实: SHOpenFolderAndSelectItems 传**目录** pidl 也是打开**父窗口**并
> 选中该条目(并非"打开进入该目录") —— 代码注释与 pitfalls 双双更正。
> 基线时间: 2026-09-30 08:25 (develop @ 7279e846 + 本轮未提交改动) 制品: 无计划文档(单点小修)。

TOTAL **1833 passed + 3 skipped / 90%**(12731 语句 / 1042 未覆盖 / 4344 分支 / 432 partial,
test.full 26.47s, rc=0) —— 较上基线 26-09-30-1210(1829 passed + 3 skipped / 91%)增 4,
全部在 tests/test_utils.py: test_open_path_windows_schedules_foreground_bringup(打开后调度置前,
参数 = 快照 + 目标路径; 非 Windows 不调度)、test_win_foreground_new_explorer_new_window(快照差集
命中新窗口)、test_win_foreground_new_explorer_reused_window_title_match(复用窗口标题匹配兜底 +
不匹配不误推)、test_win_explorer_hwnds_non_windows_empty(非 Windows 快照恒空)。既有 open_path
四条测试补 `_win_foreground_explorer_async` stub(真跑会起线程碰真实窗口)。覆盖率 91%→90% 是
分母扩大(新分支多、单测只覆盖编排逻辑, 真实 Win32 调用无法在 CI 验证), 非回归。

## 本轮改动面

- `src/auto_qb/infra/utils.py`(681→870 行): 新增 `_EXPLORER_WND_CLASS` / `_EXPLORER_FG_TIMEOUT(2.0)`
  / `_EXPLORER_FG_POLL(0.1)` 常量与 `_win_explorer_hwnds`(EnumWindows 按类名快照, 只读无副作用,
  失败返回空集)/`_win_force_foreground`(IsIconic 先还原 + AttachThreadInput 借前台权限 +
  SetForegroundWindow + BringWindowToTop, 全失败静默)/`_win_reuse_title_candidates`(复用窗口标题
  候选 = 目标名 + 父目录名)/`_win_foreground_new_explorer`(同步编排: 轮询新窗口 → 标题兜底 →
  置前)/`_win_foreground_explorer_async`(daemon 线程包装, 不挂 WebUI/托盘调用方); `open_path`
  Windows 分支包 try/finally, finally 里带打开前快照调度置前。顶部 +`import threading`。
- 实测修正(2026-09-30, Win11 实机两次弹窗验证): ①目录 pidl 同样是"开父窗口选中条目" ——
  `_win_shell_open`/`open_path` docstring 与 pitfalls/backend/windows-long-path.md 打开层条目已更正;
  ②Win11 窗口标题 = `<父目录名> - 文件资源管理器`, 兜底匹配用 `名字 + " - "` 前缀绕开本地化后缀;
  ③真机验收: open_path 后 `GetForegroundWindow()` == 新窗口 HWND, 两次全中。
- 文档: 新建 pitfalls/backend/explorer-foreground.md(前台锁坑, 三必填 + 守阵);
  modules/core-runtime.md utils.py 行回写(行数 + 置前能力)。
- 无新配置键、无 state_file schema 变更; 新线程仅为 daemon 置前线程(生命周期 ≤2s, 不碰任务
  队列与 state_file, 不违反单一写线程假设)。

# 基线 · 1890 passed + 3 skipped / 91% —— 打开目标文件夹置前 · 第二轮(真根因)

> 摘要: 二次报障"资源管理器仍有概率不弹出至顶层"收口。首轮(26-09-30 08:25)把处置停在
> "AttachThreadInput + SetForegroundWindow", 真根因却不在前台锁: 置前链路里每个
> `ctypes.windll.user32.*` 调用都**没绑 argtypes**, HWND 按 32 位 int 传而它是指针宽度 ——
> 同一窗口同一时刻实测, 未绑 `SetWindowPos` ret=0 且 `GetLastError()` 仍为 0(静默失败),
> 绑了 ret=1 立刻抬到顶层; 这是"**有概率**"的来源。修复: 单点收编 `_win_user32` /
> `_win_kernel32` 并按签名表逐个绑 argtypes+restype(user32 14 个 / ole32 2 个 / kernel32 1 个),
> 再把置前拆成**三层互不为前置条件**的升级链(Z 序 TOPMOST 开关 / 焦点 / SwitchToThisWindow 硬切),
> 并把找窗口的两条策略(新窗口差集 / 复用窗口标题匹配)改成**每轮都试** + 超时 2s→5s + 封顶重试。
> 基线时间: 2026-09-30 23:54 (develop @ 73cdc793 + 本轮改动; 会话起手已 sync)
> 档案: 未立新任务档案(沿既有 issue 收尾); 坑 pitfalls/backend/ctypes-x64-argtypes.md(新)
> + explorer-foreground.md(根因更正)

TOTAL **1890 passed + 3 skipped / 91%**(13377 语句 / 1056 未覆盖 / 4420 分支 / 435 partial,
test.full 29.0s, rc=0) —— 较上基线 26-09-30-2253(1881 passed + 4 skipped / 91%)净 +9:
本轮 **+9**(签名绑定守阵 / 双策略优先与超时 / TOPMOST 成对 / 取焦被拒仍抬 Z 序 / 取焦成功即短路
/ 死句柄零调用 / 封顶重试 / 非 Windows 早退 2 条), 无其它改动。

## 本轮改动面

- `src/auto_qb/infra/utils.py`(552→~630 语句): 新增 `_WIN_USER32_SIGNATURES()` 签名表、
  `_win_bind()`、`_win_user32()` / `_win_kernel32()`(带模块级绑定缓存, 先过 `is_windows()` 再取缓存
  —— 否则单测 patch 平台后仍会拿到真句柄)、`_win_topmost_once()`、`_win_switch_to_this_window()`;
  `_win_force_foreground` 改三层升级并返回是否真取到焦点; `_win_explorer_hwnds` 改走绑定后的句柄;
  `_win_wait_explorer` 抽出双策略轮询; `_win_foreground_new_explorer` 加封顶重试; `_win_shell_open`
  补绑 ole32.CoInitializeEx / CoUninitialize。常量: `_EXPLORER_FG_TIMEOUT` 2.0→5.0, 新增
  `_EXPLORER_FG_RETRY=4` / `_EXPLORER_FG_RETRY_GAP=0.12`。
- `tests/test_utils.py`: 测试计划清单 +7 行; 原两条置前用例(Mock 假 user32)加超时/轮询打短;
  新增 8 条, 含 `_FakeUser32` 替身(前台结果可控, 能钉住"取焦被拒 / 成功"两条分支)。
- 无新配置键、无新线程(原先的 daemon 置前线程不变)、无 state_file schema 变更、无端点变化。

## 真机验收(本机 Win11)

- 别的应用(notepad)占着前台 → `open_path`: 新窗口场景与**复用窗口**场景都在首个 0.25s 采样点
  成为前台窗口。
- `_win_topmost_once` 单独验证: Z 序 index 63→56(已压过 notepad), 且**前台仍属 notepad**
  —— 证明"看得见"与"抢得到焦点"确实解耦。
- 首轮修复之所以"验过又失败": 只验了 `GetForegroundWindow()`(焦点), 没验 Z 序; 且当时
  argtypes 未绑, 命中与否取决于寄存器残留。

# ctypes windll 调用不绑 argtypes: x64 上静默失效

> 摘要: 用 `ctypes.windll.user32.XXX(...)` 直调 Windows API 时**不声明 argtypes/restype**, 参数按 32 位 int 传, 而 `HWND` / `HWND_TOPMOST` 这类"指针宽度"参数的高 32 位是寄存器残留值 —— 调用**返回失败却 GetLastError 为 0**, 且是否翻车取决于残留值 ⇒ 表现为"有概率失效"。2026-09-30 实测: `SetWindowPos(hwnd, HWND_TOPMOST, ...)` 同一窗口同一时刻, 未绑签名 ret=0 且 Z 序纹丝不动, 绑了签名 ret=1 立刻抬到顶层。
> 触发: ctypes, windll, WinDLL, argtypes, restype, 静默失败, GetLastError 为 0, x64, 传参, HWND, 指针宽度, 寄存器残留, 有概率, SetWindowPos, SetForegroundWindow, GetClassNameW, GetWindowTextW, Shell API, 封装注册键

### 每个 API 都得绑死 argtypes —— 不绑时是"随机失效"而不是"报错"

- **触发**: 任何 `ctypes.windll.<dll>.<fn>(...)` 形式的 Windows API 调用(2026-09-30 用户二次报障"打开目标文件夹仍有概率不弹出至顶层", 第一次修复没找到根因)。
- **判别**(与"被系统拒绝"区分开, 关键是**取返回码**): 同一窗口、同一时刻、同一参数, 唯一的变量是有没有 argtypes —— 未绑 ret=0 + `GetLastError()==0`(user32 大量函数不写 LastError, 所以不报错也不生效); 绑了 ret=1 且效果立刻出现。症状因此是**概率性**的: 多次重试、换个调用顺序、甚至在 flourishing 环境里都有可能"碰巧通过" ⇒ 极易被误判成"前台锁/时序/窗口找不到"这类应用层原因。
- **根因**: 不声明 argtypes 时 ctypes 把参数当作 **32 位 int** 传(x64 MS ABI 下寄存器 widnth 是 64 位), 而 `HWND`(以及 `HWND_TOPMOST = (HWND)-1`、`LPARAM`、`LPVOID`)是**指针宽度**。寄存器高 32 位保留着上一次调用的残留值, 于是目标 hwnd / -1 都变成畸形句柄。
- **处置**: 收编出单点取用函数(本项目 `utils._win_user32` / `_win_kernel32`), 在里面按**签名表**逐个绑 `argtypes` + `restype`(返回的具体函数对象再被单测 monkeypatch 成替身 —— 顺带把这条链路变得可测)。凡取句柄参数的都要绑: `GetClassNameW` / `GetWindowTextW` / `IsWindow` / `IsIconic` / `IsWindowVisible` / `ShowWindow` / `SetWindowPos` / `GetForegroundWindow` / `SetForegroundWindow` / `BringWindowToTop` / `AttachThreadInput` / `GetWindowThreadProcessId` / `CoInitializeEx`。
  - 注意 `restype = wintypes.HWND` 拿回来是**纯 int**(NULL 时为 None), 可与 EnumWindows 回调里的 hwnd(也是 int)直接比较;
  - 老系统可能没有某个导出(如 `SwitchToThisWindow`), 绑签名要逐个 `try` 跳过, 别让绑不上变成致命;
  - `ctypes.windll` 是按 dll 名缓存的, 绑一次全进程生效 —— 别以为你在对象上改的参数会被副本吃回去。
- **排查手法**(没啥): 怀疑这类问题时不要靠推理, 用**同进程双句柄对照** —— `ctypes.WinDLL("user32")` 各取一份, 一份绑签名一份不绑, 在同一窗口上跑同一个调用, 比 `GetLastError` 更可信的是**看返回码 + 看实际效果(Z 序 / 标题)**。
- **守阵**: `tests/test_utils.py::test_win_user32_binds_signatures`(Windows 上跑, 断言签名表逐条绑上; POSIX 跳过)。**别指望注入假 user32 的用例能发现这类问题** —— 那是它们的价值所在, 也是它们的盲区。

# ctypes windll 调用不绑 argtypes: x64 上静默失效

> 摘要: 用 `ctypes.windll.user32.XXX(...)` 直调 Windows API 时**不声明 argtypes/restype**, 参数按 32 位 int 传, 而 `HWND` / `HWND_TOPMOST` 这类"指针宽度"参数的高 32 位是寄存器残留值 —— 调用**返回失败却 GetLastError 为 0**, 且是否翻车取决于残留值 ⇒ 表现为"有概率失效"。2026-09-30 实测: `SetWindowPos(hwnd, HWND_TOPMOST, ...)` 同一窗口同一时刻, 未绑签名 ret=0 且 Z 序纹丝不动, 绑了签名 ret=1 立刻抬到顶层。
> 触发: ctypes, windll, WinDLL, argtypes, restype, 静默失败, GetLastError 为 0, x64, 传参, HWND, 指针宽度, 寄存器残留, 有概率, SetWindowPos, SetForegroundWindow, GetClassNameW, GetWindowTextW, Shell API, 封装注册键, 实参求值顺序, 安全网, WINFUNCTYPE 缺失, 签名表工厂, _win_dll, Linux CI 红

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

### 签名表的**构造**别写在实参位 —— 求值早于 windll 探测, "取不到返回 None" 成死代码

- **触发**: 2026-10-13 Linux CI 单轮红 4 条(`test_utils` 的 3 条 `open_path` + `test_win_user32_binds_signatures`),
  报错一律 `AttributeError: module 'ctypes' has no attribute 'WINFUNCTYPE'`; 本机(Windows)全绿。
- **判别**: 调用链 `open_path`(Windows 分支) → `_win_explorer_hwnds()` → `_win_user32()`。取句柄函数本有
  "`ctypes.windll` 取不到 → 返回 None" 的安全网(函数体内 `except (ImportError, AttributeError, OSError)`),
  但骨架单点 `_win_dll(name, sigs)` 的签名表是**实参**: `_win_dll("user32", _WIN_USER32_SIGNATURES())`。
  Python **先求值实参再进函数体** ⇒ 签名表里的 `ctypes.WINFUNCTYPE`(POSIX 不存在)在 windll 探测**之前**就抛,
  那句 `except` 一次都没执行。用例把 `sys.platform` 固定成 `win32`(测试主体是平台逻辑, 不是当前真实平台)
  ⇒ `is_windows()` 早退这层也不生效, 两层安全网全废。第 4 条用例自己写着 `if u32 is None: pytest.skip(...)`
  —— **契约本来就是 None**, 抛错是契约破裂, 不是"用例忘了补门面"。本机绿只是上界(Windows 上 `WINFUNCTYPE`
  存在, 这条路径永不现形), 真值在 Linux。
- **处置**: 签名表改**工厂(可调用)**传参, 构造推到探测成功之后: `_win_dll(name, sigs_of)` + 调用点去括号
  `_win_dll("user32", _WIN_USER32_SIGNATURES)`; docstring 写明"别顺手改回传现成元组"。
  守阵 `tests/test_utils.py::test_win_dll_missing_windll_returns_none`: **两平台**都删掉 `ctypes.windll` +
  `ctypes.WINFUNCTYPE` 造出 POSIX 等价形态, 断言返回 None 不抛错(红验: 退回实参写法即红, 报错与 CI 逐字一致)。
- **❗别与"用例补门面"混为一谈**: `pitfalls/testing/patching.md` 那条(缺 `windll`/`WINFUNCTYPE` → 用例补
  `_shim_posix_ctypes`)治的是"**用例**要跑 Windows 分支而 POSIX 无门面" —— 那里缺门面**不是**被测代码的缺陷。
  本条相反: "取不到返回 None" 是**被测代码的契约**, 补门面只把契约破裂盖住, 生产侧那句 `except` 依旧是死代码。
  **先判"缺的东西是环境的还是契约的", 再决定补哪一侧。**
- **泛化**: 凡"拿不到就返回 None/False"的安全网, 都要问**它的判据是在哪一刻求值的** —— 把判据依赖的构造放进
  **实参位 / 默认值 / 装饰器参数 / 模块级常量**, 求值就发生在安全网之外; 这类缺陷在能拿到该属性的平台上
  永远不现形, 只有平台差异把它逼出来。

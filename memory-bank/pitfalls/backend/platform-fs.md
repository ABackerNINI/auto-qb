# 平台与文件系统

> 摘要: Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。
> 触发: 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, CRLF, OEM 码页, PATH, MSYS, Git Bash

### Windows 脚本三坑(批处理 rem / 行尾 / 码页) + PATH 条目的 MSYS 形态

- **触发**: 写跨平台脚本(wrapper / 生成器), 或解析 `os.environ["PATH"]`(2026-09-24 实测)。
- **判别(批处理)**: ①**`rem` 行里出现引号 / 括号 / 反引号 → 整份批处理静默退出、无任何输出** ——
  同一份逻辑换成干净 rem 立刻正常; 症状是"退出码 2 却什么都不打印", 极难定位, 所以**注释只写纯 ASCII 短句**。
  ②**行尾必须 CRLF**(LF 会被拆错行, 报 `'exist' 不是内部或外部命令` 这类怪错)。
  ③**消息一律 ASCII** —— cmd 按 OEM 码页(本机 GBK)读批处理, 中文变 mojibake。
  另: Windows 下 **CreateProcess 不认 shebang**, `.cmd` 只能经 shell(→ cmd.exe)跑;
  直接 `subprocess.run([...cmd])` 报 `WinError 193 不是有效的 Win32 应用程序`。
- **判别(PATH)**: Git Bash 里 `os.environ["PATH"]` 是 **MSYS 形态**(`/c/Users/x/bin`), 而 `Path.home()` 给
  `C:\Users\x` ⇒ 直接比**永远不相等**(实测把"已在 PATH 上"误判成"不在 PATH 上", 于是"装到 PATH"静默跳过)。
  `/usr/bin` 这类 MSYS 内部路径与 Windows 目录不可比, 要显式跳过。
- **处置**: 批处理保持**最小特征集**; 行尾按扩展名分(`.cmd` → CRLF, sh → LF, 都无 BOM);
  PATH 比较先归一(正则把 `/c/x` 折成 `c:\x`, `normcase` 后比); 目录可写性用**真实写探测**,
  别用 `os.access(W_OK)`(它在 Windows 目录上会给假否定)。

### Windows Proactor 的 `_call_connection_lost` WinError 10054 是断连噪音, 不是崩溃

- **触发**: 日志里出现 `ERROR - Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)`
  + 整段 traceback, 末行 `ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。`
  (2026-09-24 用户报障, WEB UI 在跑)。
- **判别**: Python 3.12 `_ProactorSocketTransport._call_connection_lost` **无条件**调
  `self._sock.shutdown(socket.SHUT_RDWR)`; 对端已经 RST(浏览器关页面 / SSE 重连 / 断网抖动)时这一句就抛
  10054, asyncio 默认处理器把它按 **ERROR + traceback** 打出, 看着像崩溃。
  ❗**参数是 `(None)` = 走的优雅关闭路径**(`_force_close(exc)` 那条会带实参) ⇒ 语义是
  "服务端已在关连接, 对端又补了个 RST" —— **正常断连**。反过来说: 若 traceback 里是**别的异常类型**
  (ValueError / KeyError…)或参数带实参, **不是噪音**, 得当真查。
- **处置**: 已由 `webui/server/lifecycle.py` 的 `_web_loop_exception_handler` 降级成一行 INFO
  (60s 窗口节流, 出窗口附被抑制条数), 经 `_QuietLoopConfig.get_loop_factory()` 挂到 uvicorn 事件循环上;
  **其它异常一律 `loop.default_exception_handler(context)` 交回默认处理器, 不吞**。
  ⚠ 循环是在 `asyncio.run` 内部才创建的, 服务线程里 `asyncio.get_event_loop()` 拿不到它 ——
  只能从 `get_loop_factory`(uvicorn ≥0.36 替代 `setup_event_loop` 的扩展点)注入。
- **本机复现**(不依赖时序竞态): 在一个请求处理里 `loop.call_soon(cb)`、`cb` 抛
  `ConnectionResetError(10054, ...)` —— 原生 `uvicorn.Config` 打 ERROR + traceback, 换 `_QuietLoopConfig`
  后只剩一行 INFO。守阵见 `tests/test_web.py` 的 5 条 `*_loop_exception* / *_noise_* / *_fluctuation`。

### 锁文件残留随平台不同 (是 `filelock` 语义, 不是 bug)

- **触发**: 改 `locking.py` / 写"锁文件该不该存在"的断言。
- **判别**: `locking.release()` 只删伴生 `meta.json`; `state.lock` 由 `filelock` 底层处理 ——
  **Windows(msvcrt) 释放时删, POSIX(flock) 不删**(flock 标准语义, 删锁文件反而不安全)。
  ⇒ Linux CI 上残留是**正常行为**。
- **处置**: 测试按 `os.name == "nt"` **分平台断言**。

### Windows 长路径必须加 `\\?\` 前缀

- **触发**: 访问深路径文件。
- **判别**: 超过 MAX_PATH 的路径在 Windows 上直接失败。
- **处置**: 磁盘文件检查走 `add_long_path_prefix_for_win`(`\\?\` 前缀); **新文件访问走同一工具**。

### NTFS 稀疏文件: 只有 `FSCTL_SET_SPARSE` → `SetEndOfFile` 才是稀疏的

- **触发**: 建大文件 / 建测试用树(2026-09-21 实测, 100 文件 × 64 MiB 对照)。
- **判别**: **正确序列** `CreateFileW` → `DeviceIoControl(h, FSCTL_SET_SPARSE)` →
  `SetFilePointerEx` + `SetEndOfFile` ⇒ 实占 **0 字节/文件**(仅 MFT ≈205 B), **0.23 ms/文件**(6 万文件 ≈ 14 s)。
  ❗**三种"看着对"的写法全部满额分配**: ①标记稀疏后再 `os.truncate` —— **truncate 会让稀疏标志失效**,
  实占整个逻辑大小; ②朴素 `f.seek(n); f.write(b"\0")` —— 非稀疏文件向后扩展时 NTFS 必须让新区域读到 0 ⇒ 满额;
  ③`fsutil file createnew` 先建再 `sparse setflag` —— **setflag 不回收**已分配的簇(256 MiB 实测先占 166 MB 且不释放)。
- **处置**: 走 `ctypes` + `DeviceIoControl`(**`fsutil` 是进程派生不是系统调用**, 每文件一次 spawn 在数万文件规模上不可接受)。
  ⚠ **踩过的现场**: 按错误写法在 R 盘(70 GB 虚拟盘, 当时仅剩 7.2 GB)建树, 第一个 4 GiB 文件实占 4 GiB、
  第二个文件 `OSError: 112 (ERROR_DISK_FULL)` —— **把盘写满**。**大文件稀疏建树前先建 1 个并校验分配量。**

### 本机"删除拦截层"只在 D 盘生效, 且 R 盘无回收站

- **触发**: 想真释放磁盘空间 / 删大目录(2026-09-21 实测)。
- **判别**: 工具环境删除 **D 盘**大目录会**进回收站而不释放空间**(360sd 在跑) ⇒ `shutil.rmtree` 后 `df` 纹丝不动。
  但 **R 盘 `$RECYCLE.BIN` 实测 0.00 MB、删除即释放** —— **别套用同一条经验**去 R 盘找回收站。
- **处置**: D 盘要真释放必须按 `$I` 元数据定位自己的条目再删(`$I` 偏移 16-24 是 FILETIME **UTC**、
  偏移 28 起是 UTF-16LE 原始路径; 同名 `$R` 是载荷 ——
  ❗**`$R` 若是目录必须 `shutil.rmtree`, 用 `os.remove` 只会报 `WinError 5`**)。

### 判断"两套 API 读数矛盾"前先确认是同一时刻

- **触发**: 比较两个来源的磁盘 / 内存读数(2026-09-21 教训)。
- **判别**: 曾拿"写入前"的 `Get-PSDrive` 读数与"写满后"的 `shutil.disk_usage` 读数对比,
  得出"三套空间 API 互相矛盾"的结论 —— **完全错误**; 同刻复核三口径**逐字节相同**
  (`GetDiskFreeSpaceExW` / `shutil` / `df`)。
- **处置**: 涉及"环境事实"的结论必须**同刻取样**, 否则会把两次状态差当成工具不一致。

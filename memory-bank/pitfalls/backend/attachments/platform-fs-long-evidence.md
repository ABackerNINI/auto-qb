## Windows Proactor 断连噪音: 处置与本机复现

- **处置**: 已由 `webui/server/lifecycle.py` 的 `_web_loop_exception_handler` 降级成一行 INFO
  (60s 窗口节流, 出窗口附被抑制条数), 经 `_QuietLoopConfig.get_loop_factory()` 挂到 uvicorn 事件循环上;
  **其它异常一律 `loop.default_exception_handler(context)` 交回默认处理器, 不吞**。
  ⚠ 循环是在 `asyncio.run` 内部才创建的, 服务线程里 `asyncio.get_event_loop()` 拿不到它 ——
  只能从 `get_loop_factory`(uvicorn ≥0.36 替代 `setup_event_loop` 的扩展点)注入。
- **本机复现**(不依赖时序竞态): 在一个请求处理里 `loop.call_soon(cb)`、`cb` 抛
  `ConnectionResetError(10054, ...)` —— 原生 `uvicorn.Config` 打 ERROR + traceback, 换 `_QuietLoopConfig`
  后只剩一行 INFO。守阵见 `tests/test_web_*.py` 的 5 条 `*_loop_exception* / *_noise_* / *_fluctuation`。


## open() FileNotFoundError: 处置、守阵与复发

- **处置**: 降级语义是「缺失 = 没有对象可操作」时, 把两种形态一并按缺失静默
  (gtm `server._patch_endpoint_autostart` 的选择: patch 不是 create, 不补写);
  真要区分只能额外 stat 父路径。用例要验「可观测的读失败降级」时选**可区分形态**
  (坏 JSON → `ValueError`), 别用「父路径是文件」造 `FileNotFoundError` —— 会静默走
  缺失分支, 用例误判成降级失效。
- **守阵**: `tools/global-traffic-monitor/tests/test_server.py::test_autostart_pointer_patch_failure_only_warns`
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)


## NTFS 稀疏文件: 处置与实占现场

- **处置**: 走 `ctypes` + `DeviceIoControl`(**`fsutil` 是进程派生不是系统调用**, 每文件一次 spawn 在数万文件规模上不可接受)。
  ⚠ **踩过的现场**: 按错误写法在 R 盘(70 GB 虚拟盘, 当时仅剩 7.2 GB)建树, 第一个 4 GiB 文件实占 4 GiB、
  第二个文件 `OSError: 112 (ERROR_DISK_FULL)` —— **把盘写满**。**大文件稀疏建树前先建 1 个并校验分配量。**


## 原子写 replace 重试: 主仓复发记录

- **复发 +1 (2026-10-16, 主仓单点)**: 用户实报 HR 心跳 `PermissionError: [WinError 5] ...:
  'instances.json.o7e7o6ed.tmp' -> 'instances.json'` —— 本坑当天已在 gtm 侧记档并实现重试,
  但**主仓 `infra/utils.atomic_write` 没同步这层**, 同一根因换到 HR 心跳的写侧又打了一次
  (单次、下一周期自愈; 切片 `activeContext/26-10-16-0935-atomic-write-replace-retry.md`)。
  **为什么没命中**: 处置当初被写成「某个实现的指针」(gtm 的工具内函数), 而不是「必须全覆盖的
  模式」—— 记了没做的是「主仓同一模式还有哪些写点」这一步, 属「读了没照做」。
  **下沉**: 重试进了主仓 `atomic_write` 单点(所有原子写受益, 含 state.json), 守阵 3 条
  (`test_utils`)+ 读侧分档 2 条(`test_hr_discovery`)。


## Windows 脚本: PATH 的 MSYS 形态判据

- **判别(PATH)**: Git Bash 里 `os.environ["PATH"]` 是 **MSYS 形态**(`/c/Users/x/bin`), 而 `Path.home()` 给
  `C:\Users\x` ⇒ 直接比**永远不相等**(实测把"已在 PATH 上"误判成"不在 PATH 上", 于是"装到 PATH"静默跳过)。
  `/usr/bin` 这类 MSYS 内部路径与 Windows 目录不可比, 要显式跳过。

## HTTPServer 端口冲突: 副作用与守阵

- **副作用**: 这样“端口占用”才会真的报错, 而**报错本身是产品行为**(提示“同机多实例请错开端口”),
  必须测: 起一个端点 → 同端口再起一个 → 断言抛错(见 `test_hr_server.py::test_port_conflict_fails_fast`)。


## Windows 脚本三坑与 PATH 条目


- **触发**: 写跨平台脚本(wrapper / 生成器), 或解析 `os.environ["PATH"]`(2026-09-24 实测)。
- **判别(批处理)**: ①**`rem` 行里出现引号 / 括号 / 反引号 → 整份批处理静默退出、无任何输出** ——
  同一份逻辑换成干净 rem 立刻正常; 症状是"退出码 2 却什么都不打印", 极难定位, 所以**注释只写纯 ASCII 短句**。
  ②**行尾必须 CRLF**(LF 会被拆错行, 报 `'exist' 不是内部或外部命令` 这类怪错)。
  ③**消息一律 ASCII** —— cmd 按 OEM 码页(本机 GBK)读批处理, 中文变 mojibake。
  另: Windows 下 **CreateProcess 不认 shebang**, `.cmd` 只能经 shell(→ cmd.exe)跑;
  直接 `subprocess.run([...cmd])` 报 `WinError 193 不是有效的 Win32 应用程序`。
- **处置**: 批处理保持**最小特征集**; 行尾按扩展名分(`.cmd` → CRLF, sh → LF, 都无 BOM);
  PATH 比较先归一(正则把 `/c/x` 折成 `c:\x`, `normcase` 后比); 目录可写性用**真实写探测**,
  别用 `os.access(W_OK)`(它在 Windows 目录上会给假否定)。


## 两套 API 读数矛盾: 同刻取样


- **触发**: 比较两个来源的磁盘 / 内存读数(2026-09-21 教训)。
- **判别**: 曾拿"写入前"的 `Get-PSDrive` 读数与"写满后"的 `shutil.disk_usage` 读数对比,
  得出"三套空间 API 互相矛盾"的结论 —— **完全错误**; 同刻复核三口径**逐字节相同**
  (`GetDiskFreeSpaceExW` / `shutil` / `df`)。
- **处置**: 涉及"环境事实"的结论必须**同刻取样**, 否则会把两次状态差当成工具不一致。


## 锁文件残留随平台不同


- **触发**: 改 `locking.py` / 写"锁文件该不该存在"的断言。
- **判别**: `locking.release()` 只删伴生 `meta.json`; `state.lock` 由 `filelock` 底层处理 ——
  **Windows(msvcrt) 释放时删, POSIX(flock) 不删**(flock 标准语义, 删锁文件反而不安全)。
  ⇒ Linux CI 上残留是**正常行为**。
- **处置**: 测试按 `os.name == "nt"` **分平台断言**。


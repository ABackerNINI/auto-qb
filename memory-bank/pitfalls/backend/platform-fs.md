# 平台与文件系统

> 摘要: Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。
> 触发: 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, cmd, .cmd, 行尾, CRLF, OEM 码页, PATH, MSYS, Git Bash, HTTPServer, 端口被占, SO_REUSEADDR, allow_reuse_address, getfqdn, 原子写, os.replace, 并发读者, WinError 5, 拒绝访问, 退避重试, 心跳, 实例注册表, 读不到不等于空表, taskkill, MSYS pid, 目录 nlink, st_nlink, 进程表, tasklist, 平台分派, FileNotFoundError, NotADirectoryError, ENOTDIR, 异常类型分流

### Windows 上 `HTTPServer` 默认的 `allow_reuse_address = 1` 会让「端口被占」检测失效

- **触发**: 用 stdlib `http.server.HTTPServer` / `socketserver` 起监听, 并希望「端口被占就报错」
  (`hr/server.py` 的本地取数端点就是这样, 2026-09-24 M2 实测)。
- **判别**: `HTTPServer.allow_reuse_address = 1`(类属性默认值); 它在 Windows 上映射成 `SO_REUSEADDR`,
  而 Windows 的语义与 POSIX **不同** —— 它允许**第二个进程抢绑已经在监听的同一端口**(不是只绕过 TIME_WAIT)。
  于是「同机第二个实例配了同一个 port ⇒ 启动即 fail-fast」这条守卫会**静默失效**: 两个进程都“启动成功”,
  请求随机落到其中一个(实测表现为“扩展拉不到清单/时好时坏”)。
- **处置**: 子类里 `allow_reuse_address = False`(**不要**靠 `SO_EXCLUSIVEADDRUSE` 自己折腾)。
  Windows 上关掉它不会引来 TIME_WAIT 重绑难题 —— 监听端被 TIME_WAIT 阻住的场景实际上不出现在 Windows;
  为了让重绑更干净, 响应带 `Connection: close`(每请求关连接)即可。
- **副作用**: 这样“端口占用”才会真的报错, 而**报错本身是产品行为**(提示“同机多实例请错开端口”),
  必须测: 起一个端点 → 同端口再起一个 → 断言抛错(见 `test_hr_server.py::test_port_conflict_fails_fast`)。

### `HTTPServer.server_bind` 会顺手查一次 FQDN(无网机器上会拖启动)

- **触发**: 同上, 起 stdlib HTTP 服务。
- **判别**: `HTTPServer.server_bind` 除了 `bind` 还调 `socket.getfqdn(host)` 填 `server_name`;
  127.0.0.1 也不例外 —— 无网/弱网机器上那次反向查询可能抱几秒(启动路径上不必要的等待)。
- **处置**: 只服务回环时重写 `server_bind`: 直接调 `socketserver.TCPServer.server_bind(self)`,
  再手动把 `server_name/server_port` 填成 `server_address` 的值。

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
  后只剩一行 INFO。守阵见 `tests/test_web_*.py` 的 5 条 `*_loop_exception* / *_noise_* / *_fluctuation`。

### 锁文件残留随平台不同 (是 `filelock` 语义, 不是 bug)

- **触发**: 改 `locking.py` / 写"锁文件该不该存在"的断言。
- **判别**: `locking.release()` 只删伴生 `meta.json`; `state.lock` 由 `filelock` 底层处理 ——
  **Windows(msvcrt) 释放时删, POSIX(flock) 不删**(flock 标准语义, 删锁文件反而不安全)。
  ⇒ Linux CI 上残留是**正常行为**。
- **处置**: 测试按 `os.name == "nt"` **分平台断言**。

### Windows 长路径必须加 `\\?\` 前缀

> 已**独立成篇**(2026-09-26 拆分: 本文件已到 cap, 且该专题长成了四条): 见 [windows-long-path.md](windows-long-path.md) ——
> 前缀 / "同一路径两种写法" / 打开层 Shell PIDL / `shutil.rmtree` 前缀, 四处坑 + 复发记录。
> 一句话底线不变: 磁盘文件检查走 `add_long_path_prefix_for_win`(`\\?\` 前缀), **新文件访问走同一工具**。

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

### Windows 原子写 (`os.replace`) 与并发读者的双向瞬时拒绝 (WinError 5/32)

- **触发**: 「同目录临时文件 + fsync + `os.replace`」的原子写模式, 且有**并发读者**
  周期性打开目标文件 —— gtm 工具写 `history_traffic.dat` / `state.json`, auto-qb
  多实例经 `curves.py` 解析读 dat(2026-10-16 S2 实测, 热读循环下每次写都撞)。
- **判别**: 两个方向的瞬时 `PermissionError` (errno 13): ①**写侧** —— 读者正持目标
  文件打开时 (`MoveFileEx` 拒绝替换: Python `open()` 的 share mode 不含
  `FILE_SHARE_DELETE`); ②**读侧** —— replace 事务窗口内, 读者的 `open()` 被瞬时
  拒绝。两者都是开-读-关的微秒~毫秒级窗口, **不是持久故障**。
- **处置**: 写侧把 `os.replace` 包进退避重试 (仅 PermissionError, 5 次 × 50ms;
  耗尽抛错, 由调用方在下一周期容错) —— **两个独立单点、常量必须同值**: gtm 工具
  `tools/global-traffic-monitor/src/gtm/storage.py::_replace_retry` 与主仓
  `src/auto_qb/infra/utils.py::_replace_retry`(主仓这层 2026-10-16 复发后补齐, 见下「复发」)。
  读侧打开失败**重试**, 不要当内容损坏 —— 看不到内容 ≠ 看到半截内容, **也 ≠ 读到空表**:
  主仓 HR 注册表 `hr/discovery.py::_read_registry_text` 重试耗尽按「读不到」返回 `None`
  (upsert 本轮不写, 免得把别家实例条目静默抹掉; 只读面当空列表)。POSIX 上 replace 不受
  读者影响, 不触发重试。
- **复发 +1 (2026-10-16, 主仓单点)**: 用户实报 HR 心跳 `PermissionError: [WinError 5] ...:
  'instances.json.o7e7o6ed.tmp' -> 'instances.json'` —— 本坑当天已在 gtm 侧记档并实现重试,
  但**主仓 `infra/utils.atomic_write` 没同步这层**, 同一根因换到 HR 心跳的写侧又打了一次
  (单次、下一周期自愈; 切片 `activeContext/26-10-16-0935-atomic-write-replace-retry.md`)。
  **为什么没命中**: 处置当初被写成「某个实现的指针」(gtm 的工具内函数), 而不是「必须全覆盖的
  模式」—— 记了没做的是「主仓同一模式还有哪些写点」这一步, 属「读了没照做」。
  **下沉**: 重试进了主仓 `atomic_write` 单点(所有原子写受益, 含 state.json), 守阵 3 条
  (`test_utils`)+ 读侧分档 2 条(`test_hr_discovery`)。

### Git Bash 两个会骗人的环境事实 (MSYS pid / grep 行尾计数)

- **触发**: 在 Bash 工具里对 Windows 原生进程做生命周期管理, 或检查文件行尾。
- **判别**: ①后台 `"$PY" ... &` 的 `$!` 是 **MSYS pid**, 拿它去 `taskkill //PID`
  永远「没有找到进程」—— 要 Windows pid (可从 filelock meta / fail-fast 消息里的
  `PID nnnnn` 提取); ②`grep -c $'\r' file` 在该 shell 里可能**不展开成 CR**, 退化
  成数全部行数, 输出恰好等于文件行数, 极易误判「全 CRLF」。
- **处置**: 行尾事实一律用 python bytes 层 (`read_bytes().count(b"\r\n")`), 不信
  grep 计数; 杀 Windows 进程先拿到真 Windows pid。

### POSIX 目录的 `st_nlink` 恒 ≥ 2(Windows 目录 = 1): 拿目录当「代表文件」的探测只在 Linux 炸

- **触发**: 对 `save_path` 这类**目录** `os.lstat` 后按 `st_nlink > 1` 判硬链接; 或写只在本机跑过的平台分支用例。
- **判别**: Linux 目录 `nlink = 2 + 子目录数`(**恒 > 1**), Windows NTFS 目录 `nlink = 1`(本机实测目录 1 / 普通文件 1)
  ⇒ 同一段 `elif st.st_nlink > 1:` 在 Windows 走不到、在 Linux 必进。2026-10-19 GitHub Actions 实测:
  `relocate_mod._group_facts` 空文件表时 `first_native` 兜底成 `save_path`(目录), 随后 `names[0]` → `IndexError`,
  而本机全绿。
- **处置**: 「代表文件」只对**真文件**成立 —— 空文件表(读不到文件列表)整段探测跳过(`if names:`), 不要用
  `save_path` 兜底; 守阵用「录 `os.lstat` 探针 + 断言目录零探测」的写法, 让 Windows 也能红验
  (`tests/test_relocate_paths.py::test_precheck_empty_file_table_skips_representative_probe`)。

### 跨平台分派函数别按「本机那支」写用例

- **触发**: 被测函数内部按 `os.name` / `/proc` 分派(如 `finalize_watch._qb_process_names`: `nt` → tasklist,
  `/proc` → comm, 其它 POSIX → `ps`), 用例只 mock 其中一支的外部调用。
- **判别**: 在 Linux CI 上那个 mock 根本不生效, 断言拿到的是**真机结果**(2026-10-19: `test_guardian_process_names_parsing`
  Linux 恒红、本机绿)。
- **处置**: 分三层测 —— ①解析本体(平台无关, 直接调 `_names_from_tasklist`/`_names_from_proc`/`_names_from_ps`);
  ②**分派**(三支都换替身, 按 `os.name` + `os.path.isdir("/proc")` 现查判据断言选中哪支); ③异常吞噬(三支都抛
  `OSError` → 返回空)。别用 `skipif` 绕 —— 跳过会让另一侧的专属行彻底不覆盖。

### open() 的 FileNotFoundError 在 Windows 上区分不了「文件缺失」与「路径组件不是目录」

- **触发**: 读侧降级按「异常类型分流失败形态」时 —— 例: 读发现指针文件, 想把
  `FileNotFoundError` = 静默(没有对象可操作)、其它 `OSError` = WARNING(2026-10-31 实测,
  issue 26-10-31-0537 的 patch 失败用例首跑红)。
- **判别**: POSIX 上 `open("普通文件/子路径")` 抛 `NotADirectoryError`(ENOTDIR);
  Windows 的 `CreateFile` 对同形路径返回 `ERROR_PATH_NOT_FOUND` → Python 映射成
  **`FileNotFoundError`** —— 于是「目标文件不存在」与「父路径是普通文件」在 Windows
  **同型不可辨**。对照: `os.makedirs` 不吃这套映射, 父路径是文件抛 `FileExistsError`
  (WinError 183), 别拿一个 API 的实测外推另一个。
- **处置**: 降级语义是「缺失 = 没有对象可操作」时, 把两种形态一并按缺失静默
  (gtm `server._patch_endpoint_autostart` 的选择: patch 不是 create, 不补写);
  真要区分只能额外 stat 父路径。用例要验「可观测的读失败降级」时选**可区分形态**
  (坏 JSON → `ValueError`), 别用「父路径是文件」造 `FileNotFoundError` —— 会静默走
  缺失分支, 用例误判成降级失效。
- **守阵**: `tools/global-traffic-monitor/tests/test_server.py::test_autostart_pointer_patch_failure_only_warns`
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/testing/baselines/26-10-16-0855-global-traffic-monitor-s2.md

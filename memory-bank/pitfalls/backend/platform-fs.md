# 平台与文件系统

> 摘要: Windows / Linux 差异、长路径、稀疏文件、删除拦截层、事件循环断连噪音、批处理与 PATH 条目的写法坑 —— 与宿主环境强相关的一类坑。
> 触发: isabs, ntpath.isabs, 绝对路径, 盘符补全, pathlib, 锁文件, 长路径, 稀疏文件, 删不掉, 磁盘空间, 盘满, WinError 10054, proactor, 断连噪音, asyncio, 批处理, .cmd, CRLF, OEM 码页, PATH, MSYS, Git Bash, HTTPServer, 端口被占, SO_REUSEADDR, allow_reuse_address, getfqdn, 原子写, os.replace, 并发读者, WinError 5, 拒绝访问, 退避重试, 心跳, 实例注册表, 读不到不等于空表, taskkill, MSYS pid, 目录 nlink, st_nlink, 进程表, tasklist, 平台分派, FileNotFoundError, NotADirectoryError, ENOTDIR, 异常类型分流

### Windows 上 `HTTPServer` 默认的 `allow_reuse_address = 1` 会让「端口被占」检测失效

- **触发**: 用 stdlib `http.server.HTTPServer` / `socketserver` 起监听, 并希望「端口被占就报错」
  (`src/auto_qb/hr/server.py` 的本地取数端点就是这样, 2026-09-24 M2 实测)。
- **判别**: `HTTPServer.allow_reuse_address = 1`(类属性默认值); 它在 Windows 上映射成 `SO_REUSEADDR`,
  而 Windows 的语义与 POSIX **不同** —— 它允许**第二个进程抢绑已经在监听的同一端口**(不是只绕过 TIME_WAIT)。
  于是「同机第二个实例配了同一个 port ⇒ 启动即 fail-fast」这条守卫会**静默失效**: 两个进程都“启动成功”,
  请求随机落到其中一个(实测表现为“扩展拉不到清单/时好时坏”)。
- **处置**: 子类里 `allow_reuse_address = False`(**不要**靠 `SO_EXCLUSIVEADDRUSE` 自己折腾)。
  Windows 上关掉它不会引来 TIME_WAIT 重绑难题 —— 监听端被 TIME_WAIT 阻住的场景实际上不出现在 Windows;
  为了让重绑更干净, 响应带 `Connection: close`(每请求关连接)即可。
- **副作用**: 同机多实例必须真的报错, 工序与守阵见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

### `HTTPServer.server_bind` 会顺手查一次 FQDN(无网机器上会拖启动)

- **触发**: 同上, 起 stdlib HTTP 服务。
- **判别**: `HTTPServer.server_bind` 除了 `bind` 还调 `socket.getfqdn(host)` 填 `server_name`;
  127.0.0.1 也不例外 —— 无网/弱网机器上那次反向查询可能抱几秒(启动路径上不必要的等待)。
- **处置**: 只服务回环时重写 `server_bind`: 直接调 `socketserver.TCPServer.server_bind(self)`,
  再手动把 `server_name/server_port` 填成 `server_address` 的值。

## Windows 脚本三坑(批处理 rem / 行尾 / 码页) + PATH 条目的 MSYS 形态

完整判据与处置见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

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
- **处置**: 降级实现、循环注入与本机复现见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

## 锁文件残留随平台不同 (是 `filelock` 语义, 不是 bug)

判据与分平台断言见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

## Windows 长路径必须加 `\\?\` 前缀

> 已**独立成篇**(2026-09-26 拆分: 本文件已到 cap, 且该专题长成了四条): 见 [windows-long-path.md](windows-long-path.md) ——
> 前缀 / "同一路径两种写法" / 打开层 Shell PIDL / `shutil.rmtree` 前缀, 四处坑 + 复发记录。
> 一句话底线不变: 磁盘文件检查走 `add_long_path_prefix_for_win`(`\\?\` 前缀), **新文件访问走同一工具**。

NTFS 稀疏文件条目(只有 `FSCTL_SET_SPARSE` → `SetEndOfFile` 才是稀疏的)已外迁: [attachments/26-11-08-platform-fs-sparse-file.md](attachments/26-11-08-platform-fs-sparse-file.md)(26-11-08 cap 清零)。

### 本机"删除拦截层"只在 D 盘生效, 且 R 盘无回收站

- **触发**: 想真释放磁盘空间 / 删大目录(2026-09-21 实测)。
- **判别**: 工具环境删除 **D 盘**大目录会**进回收站而不释放空间**(360sd 在跑) ⇒ `shutil.rmtree` 后 `df` 纹丝不动。
  但 **R 盘 `$RECYCLE.BIN` 实测 0.00 MB、删除即释放** —— **别套用同一条经验**去 R 盘找回收站。
- **处置**: D 盘要真释放必须按 `$I` 元数据定位自己的条目再删(`$I` 偏移 16-24 是 FILETIME **UTC**、
  偏移 28 起是 UTF-16LE 原始路径; 同名 `$R` 是载荷 ——
  ❗**`$R` 若是目录必须 `shutil.rmtree`, 用 `os.remove` 只会报 `WinError 5`**)。

## 判断"两套 API 读数矛盾"前先确认是同一时刻

判别与处置见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

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
  主仓 HR 注册表 `src/auto_qb/hr/discovery.py::_read_registry_text` 重试耗尽按「读不到」返回 `None`
  (upsert 本轮不写, 免得把别家实例条目静默抹掉; 只读面当空列表)。POSIX 上 replace 不受
  读者影响, 不触发重试。
- **复发记录**: 见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

### Git Bash 两个会骗人的环境事实 (MSYS pid / grep 行尾计数)

- **触发**: 在 Bash 工具里对 Windows 原生进程做生命周期管理, 或检查文件行尾。
- **判别**: ①后台 `"$PY" ... &` 的 `$!` 是 **MSYS pid**, 拿它去 `taskkill //PID`
  永远「没有找到进程」—— 要 Windows pid (可从 filelock meta / fail-fast 消息里的
  `PID nnnnn` 提取); ②`grep -c $'\r' file` 在该 shell 里可能**不展开成 CR**, 退化
  成数全部行数, 输出恰好等于文件行数, 极易误判「全 CRLF」。
- **处置**: 行尾事实一律用 python bytes 层 (`read_bytes().count(b"\r\n")`), 不信
  grep 计数; 杀 Windows 进程先拿到真 Windows pid。

> 已外迁: POSIX 目录 st_nlink 恒 ≥2 / Windows=1，「拿目录当代表文件」的探测只在 Linux 炸 → [attachments/26-11-22-platform-fs-nlink-dir-probe.md](attachments/26-11-22-platform-fs-nlink-dir-probe.md)(26-11-22 cap 清零)
### 跨平台分派函数别按「本机那支」写用例

- **触发**: 被测函数内部按 `os.name` / `/proc` 分派(如 `tools/recycle_daemon._qb_process_names`(原 `finalize_watch`, 该文件已删): `nt` → tasklist,
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
- **处置**: 降级语义与可区分形态用例见 [attachments/platform-fs-long-evidence.md](attachments/platform-fs-long-evidence.md)。

### Python 3.13 起 Windows 侧 `os.path.isabs('/x')` 返回 False(根锚定形态不再算绝对)

- **触发**: 用 `os.path.isabs`(Windows 上即 `ntpath.isabs`)判定配置里的路径要不要原样采用还是拼上仓库根
  (2026-11-18 issue 26-11-18-0210: `scripts/sync_agent_skills.py` 的 link_targets 判定在 Windows 3.13 上把
  `/abs/nowhere/skills` 走了 `REPO_ROOT / p` 分支, 测试断言「绝对路径原样采用」恒红)。
- **判别**: Python 3.13 起 `ntpath.isabs('/x')` 由历史语义 True 改为 **False**(根锚定无盘符不再算绝对);
  3.12 及以前为 True —— 同一份配置跨解释器版本解析结果不同。且走拼接分支时
  `PureWindowsPath('C:/repo') / '/abs'` 保留左操作数盘符 → `C:/abs`, 静默改写配置意图。
  `Path('/x').is_absolute()` 在 Windows 3.13+ 同样 False, 不能拿来替代。
- **处置**: 跨平台钉「绝对形态原样采用」不要依赖 `os.path.isabs` 的平台/版本语义: 盘符/UNC 交
  `ntpath.isabs`(本次变更未波及, 语义稳定), 根锚定 `/x`、`\x` 交纯字符串判定 `p[:1] in ("/", "\\")`
  (与解释器版本无关); 实测核对面: 8 类形态(相对/盘符相对/POSIX 根锚定/反斜杠根锚定/盘符正反斜杠/UNC 两种写法)。

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/testing/baselines/26-10-16-0855-global-traffic-monitor-s2.md

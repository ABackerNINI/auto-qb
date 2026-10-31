# 管道下按错的编码出/解中文 = 乱码但静默(子进程 + 引擎自身)

> 摘要: Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Python 子进程(如 node)输出就是 UTF-8, 而 `text=True` 按 locale 去解 ⇒ 直接抛 `UnicodeDecodeError`。再一变体(2026-10-02): AI 工具壳大输出落盘预览在截断点切进多字节字符时整段按 GBK 重解 —— 数据无损, 读落盘日志即真值。
> 等级: L0
> 触发: 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subprocess text=True, node 输出, encoding, 引擎自身 stdout, run.py 打印, 管道输出, 部分终端乱码, reconfigure, _utf8_self_stdio, PowerShell 捕获, Console.OutputEncoding, -NoProfile, AI 工具终端乱码, chcp 无效, 鍒涘缓, ConPTY, 大输出落盘, persisted output, 预览乱码, outputLimit, 截断点, 30KB, 块缓冲, line_buffering, flush, 输出滞留, 常驻服务无输出, 看不到 log, 无输出, netstat, 表头本地化, 解析恒 0, 探针假 0, 外部命令表头, 测量脚本零值自检, 重定向, UTF-16, Out-File, cmd 转发, FF FE

## 反向: 非 Python 子进程输出是 UTF-8, 别用 `text=True` 让 locale 去猜

- **触发**: 在测试或工具里 `subprocess.run(["node", ...], capture_output=True, text=True)`(2026-09-24 实测:
  `tests/test_extension_proxy.py` 用 node 跑 JS 归一化用例, 期望值里含中文报错)。
- **判别**: 抛的是 `UnicodeDecodeError: 'gbk' codec can't decode byte 0xaf ...`(不是 mojibake), 而且**抛出点很怪** ——
  堆栈落在 `subprocess._readerthread` 的后台线程里, 以 `PytestUnhandledThreadExceptionWarning` 的形式出现;
  不看警告就会误以为是“断言写错”。
- **处置**: 子进程收输出一律**显式指定** `encoding="utf-8"`(+ `errors="replace"`); 两边工具都写 UTF-8 时, 写死比“让 locale 猜”安全。
  与上一条合起来的口径: **要么收字节自己走兑底链解, 要么显式声明 UTF-8 —— 永远不要依赖 locale。**

## 打印外部输出时不要假定它是 UTF-8

- **触发**: 自己写的运行器 / 包装脚本把子进程输出收上来再打印(本仓: `.agents/skills/commands/scripts/run.py` 的 `_shell`)。
- **判别**: 输出里**中文变 `������`(U+FFFD) 而 ASCII 部分完好**(路径、`[ok] kb.index` 都正常) —— 这一条就能把"编码坏"与"命令真失败"分开。
  取证**不要靠控制台肉眼**: 同一串字节在 GBK 控制台与工具捕获下表现不同。用一句话抓原始字节:
  `python -c "import subprocess; p=subprocess.run([...], capture_output=True); print(repr(p.stdout[:80]))"`
  —— 看到 `\xd2\xd1\xc9\xfa` 这种**双字节**序列(GBK)而不是 UTF-8 多字节, 即可定案。实测 2026-09-24:
  `b'\xd2\xd1\xc9\xfa\xb3\xc9 16 \xb8\xf6\xcb\xf7\xd2\xfd'` = 「已生成 16 个索引」, 被解成 `������ 16 ������`。
- **处置**: ①给子进程环境注入 `PYTHONIOENCODING=utf-8` —— 它**只影响 stdio**, 不会像 `PYTHONUTF8=1` 那样连 `open()` 的默认编码一起改
  (后者会静默改变子脚本读文本文件的行为, 是更大的雷); ②**收字节不收文本**(`text=True` / `encoding=` 等于把编码写死, 一旦猜错就永久 U+FFFD);
  ③解码走兜底链 `UTF-8 → locale.getpreferredencoding(False) → errors="replace"`, 非 Python 子进程仍可能按本地码页输出, 这一层兜住。
  ④注入的 env 要放在**包自己 env 之前**合并 —— 包若确有理由指定编码, 仍要能覆盖。

## 引擎自身的 stdout 同理 —— "部分终端乱码"的另一半(2026-09-30 补)

- **触发**: 用户报「部分终端跑 `commands run kb.active` 中文是乱码, 另一些正常」—— 子进程方向 2026-09-24 已修,
  这轮发现**引擎自己 print 的中文**(协议行 `[ok]`、包摘要 `何时用`、透传的子进程正文)还有同族漏网。
- **判别**: 分界线 = 引擎的 stdout 是不是**真控制台**。真控制台走 `WriteConsoleW`(Unicode, 与码页无关)永不乱;
  stdout 一旦是**管道**(mintty/Git Bash、AI 工具捕获、`| tee`、CI 日志), Python 自身 stdio 就按本地码页 cp936
  **编码**输出 —— 实测剥离 `PYTHONUTF8`/`PYTHONIOENCODING` 后 `show kb.active` 的首段中文是 GBK 字节
  (`\xba\xce\xca\xb1` 开头 = "何时"), 按 UTF-8 解的对端即乱, 退出码照旧 0。会话工具 shell 里的 UTF-8 变量是
  **会话级注入**(注册表 HKCU/HKLM 均无) —— 用户自己的终端裸奔在码页回退里, 所以"部分终端"。
- **处置**: 引擎入口锁自身 stdio —— `run.py` 的 `_utf8_self_stdio()`(stdout+stderr
  `reconfigure(encoding="utf-8", errors="replace")`), `main()` 第一行调用(先于任何 print/argparse 输出)。
  真控制台不受影响(本来就是 Unicode); 管道对端从 GBK 变 UTF-8 —— 会乱的对端本来就按 UTF-8 解, 只修不破。
  与子进程侧(上面两条)合起来才是闭环: 引擎对内(收)对外(发)都显式 UTF-8, 永不依赖 locale。
- **守阵**: `test_engine.py` +2 —— ①单测: cp936 文本层经 `_utf8_self_stdio` 重配后中文按 UTF-8 出(全平台确定);
  ②端到端: 子进程剥全局 UTF-8 变量 + 管道跑 `show no-such.task`, stderr strict UTF-8 解码必须过
  (系统码页本就是 UTF-8 的机器上失去分辨力, 与 `_local_codepage` 口径一致, 不假红)。
- **为什么 9-24 那轮没修到**: 本档案当时的「同族旧账, 别只修一处」只点名了崩打印层与写盘方向两族,
  没把"引擎自身 stdout"列为待查向 —— 用户 6 天后从"部分终端"打进来的正是这一向。
- **复发**: 1 —— 2026-10-01 用户再报「代码已同步的仓库中仍乱码」: 引擎侧修复本身有效(管道字节实测已
  是 UTF-8), 乱码源在**解码侧消费端** —— 上轮「管道对端本来就按 UTF-8 解, 只修不破」的假设漏掉了
  按控制台码页解管道的消费端(PowerShell 捕获类 / AI 工具外壳), 见下节。

## 解码侧: PS 捕获类按 GBK 解 UTF-8, 运行中 chcp 救不了(2026-10-01 补)

- **触发**: 引擎已锁 UTF-8 后, 用户报「已同步的仓库里, AI 编码工具的终端跑 `commands run kb.active`
  仍乱码」。乱码形如 `创建` → `鍒涘缓`(合法汉字但全错), 不是 U+FFFD —— 这是「按 GBK 去解 UTF-8 字节」
  的指纹, 与上节「按 GBK 出、按 UTF-8 解」的 U+FFFD 指纹方向相反。
- **判别**: 分界线不在引擎, 在**消费端怎么解管道字节**。ConPTY 伪控制台实测(2026-10-01): 交互真控制台
  (cmd / PS5.1 / pwsh7)直连渲染全干净(WriteConsoleW); 乱的是**捕获后再解**路径 —— PS 的管道 / 赋值 /
  `-Command` 外壳把原生命令 stdout 接进自己管线, 按 `[Console]::OutputEncoding`(中文 Windows = GBK)
  去解。AI 编码工具若经 `powershell -NoProfile -Command` 跑命令, 内层 PS 同样按 GBK 解, 工具本身再按
  UTF-8 读 → 必乱, 与工具自身无关。自检一句话: 乱码终端里跑
  `powershell -Command "[Console]::OutputEncoding.WebName"`, `gb2312` 即中此条, `utf-8` 即已修。
- **机制**: PS 在**进程启动瞬间**快照控制台码页 —— 实测: PS 运行中 `chcp 65001` 后再捕获仍乱; 而
  **启动前**控制台已是 65001 时, 连 `-NoProfile` 的捕获解码都正确。⇒ 运行中改码页对 PS 无效,
  唯一杠杆是「PS 启动前」(profile 在加载时机上赶得上, wrapper 内的 chcp 赶不上)。
- **处置**: ①引擎侧**无可修也不许回退** —— 管道对端按什么码解无法从字节流探测, 引擎回退 GBK 会打碎
  mintty / AI 工具链(9-30 修复的对象), 别走回头路; ②profile 一行锁解码(用户已授权, PS7+PS5.1 两份
  均落地): `try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}` —— 覆盖交互
  PS 与加载 profile 的外壳, 对 git / node 等 UTF-8 工具链同为净收益; ③`-NoProfile` 外壳类(AI 工具
  常见)profile 不加载: 系统级「区域设置 → Beta: 使用 Unicode UTF-8」(全局生效, 有旧 GBK 程序兼容
  代价, 需用户自拍板)或把该工具的 shell 换 Git Bash; ④cmd 侧捕获(`for /f`、`| more`)吃的是**实时**
  控制台码页, wrapper 内 `chcp 65001` 对它们有效 —— 但对 PS 无效(见机制条), 两个结论别混用。
- **守阵**: 解码侧属环境问题, 引擎行为无变化, 不设常规守阵; 修复验证走真机(2026-10-01 实测: 改
  profile 前后, `pwsh -Command "commands run kb.active | Select-Object -First 2"` 由 `鍒涘缓` 变
  `创建`, PS5.1 同)。

## 解码侧变体: 工具壳大输出落盘预览按「截断完整性」选码(2026-10-02 补)

- **触发**: AI 工具壳跑输出超大的命令(本仓实测 `commands run kb.active` ≈ 51KB) —— ZCode Bash 工具内联上限 **30,000 字节**(`outputLimit.maxInlineBytes` 硬编码 3e4), 超限即全量落盘 + 只回前 2000 字符预览; 若内联前缀在分块边界截断时**切进多字节 UTF-8 字符中间**, 预览整段变 `鍒涘缓` 形乱码且稳定复现。与终端无关 —— 纯 ASCII 超大输出预览不乱。
- **判别**: ①落盘日志逐字节完好(`iconv -f UTF-8 -t UTF-8` 整文件校验通过) ⇒ 数据无损, 坏的只是预览解码; ②同会话对照探针: 正文连续 ASCII(截断点必落单字节)预览完好, 含中文且截断点切进汉字(kb.active 在 30,000 字节附近「的」= e7 9a ae 横跨截断区)预览全乱; ③工具源码定案: 解码函数 kme 对「干净且完整 UTF-8」按 UTF-8 解, 否则整段按 legacy(本机 GBK)重解 —— 截断留下的不完整序列尾巴就是触发器。注意显示口径: 工具报的 KB 数按 1024 进制, 30,343 字节显示 29.7KB 仍会落盘, 判定只认字节。
- **处置**: ①预览乱不丢数据 —— 直接 Read 落盘的 `*-stdout.log` 即原文; ②要内联可读就把输出压到 30,000 字节以内(≈9,900 汉字); ③天然大输出的命令(kb.active 类)加截断/精简, 或接受落盘读文件; ④引擎/工具侧无可修也不许回退(同上节口径); 后台任务 persistOutput=always 与大小无关必落盘。
  ③已落地(2026-10-02 当日): `gen_active_recent.py`(kb.active)默认按 20,000 字节预算取最近 K 条, 总数/待归档/省略数进页脚, `--all` / `-n N` 逃生 —— 守阵 `tests/test_memory_bank.py::test_kb_active_render_respects_byte_budget`。同族大输出命令若再中招, 照此模式办。

## 重定向变体: PowerShell 5.1 `>` 落盘 = UTF-16LE, UTF-8 读方直接当二进制拒收(2026-10-19 补)

- **触发**: 在 AI 工具壳(Windows PowerShell 5.1)里把大输出重定向到文件再读, 实测 `python map.py 1> out.txt 2> err.txt` ——
  想绕 30KB 内联上限落盘排障(同上节动机)。
- **判别**: UTF-8 读方报「binary file」/ 读出乱码成对 NUL 字节; `Format-Hex out.txt` 首字节 `FF FE`(BOM)
  且 ASCII 段每字节跟一个 `00` —— PS 5.1 的 `>` 重定向默认按 **Unicode(UTF-16LE)** 编码, 与控制台码页无关。
  数据无损: `Get-Content -Encoding Unicode` 能读对, 坏的是「假设落盘 = UTF-8」的消费方。
- **处置**: ① 要拿**原样字节**落盘, 绕开 PS 重定向层: `cmd /c 'python x.py > out.txt 2> err.txt'`(cmd 重定向是字节级透传,
  配合脚本内 `reconfigure(encoding="utf-8")` 即得 UTF-8 文件); ② 或 PS 侧 `| Out-File -Encoding utf8`
  (PS5.1 仍带 BOM, 严格按字节的读方仍会挑剃); ③ 已产生的 UTF-16 文件不必重跑, `Get-Content -Encoding Unicode`
  转读即可。与捕获族(上两节)合起来的口径: **PS 5.1 的输出经过自己的哪一层(管道捕获 / 文件重定向)就按哪一层的默认编码改写,**
  想要字节级原样就别让 PS 碰 —— cmd 转发或显式 `-Encoding`。

## 测量探针变体: 表头被本地化 + 解析器按英文字面匹配 ⇒ 读数静默为 0(2026-10-15 补)

- **触发**: 探针脚本解析 Windows 原生命令输出做**测量**(实测: `netstat -e` 的字节计数行、`netstat -ano` 的连接表),
  Python 侧 `subprocess.run(..., capture_output=True, text=True)`。
- **判别**: 两个方向都中, 且都可**不报错**:
  ① 按 UTF-8 收 GBK 字节 → `UnicodeDecodeError` 抛在 `subprocess._readerthread` 后台线程(本族旧例,
    实测连带表现为 `AttributeError: 'NoneType' object has no attribute 'splitlines'`, 因为 stdout 是 None);
  ② **更阴的一层**: 解码侥幸通过, 但解析器写的是 `p[0] == 'Bytes'` / `'Interface'` 这类**英文字面**,
    中文 Windows 的表头是「字节」「接口统计」⇒ 匹配失败 → 计数器初值保持 0 → **两次采样相减得 0 B/s,
    看上去就是「这个接口没有流量」**。2026-10-15 的 qB 流量取证中, 这条一度支撑出「alltime 在涨而网卡零流量
    ⇒ 纯记账幻觉」的错误中间结论; 改成按「行内两个 6 位以上整数」取值后, 真相是该机 rx 227 KB/s / tx 271 KB/s
    真实存在(= 结论被反转)。
- **处置**: ① 收外部命令输出**显式指定码页**(`encoding="gbk", errors="replace"`), 不靠 locale 也不假定 UTF-8;
  ② 解析**不按表头文字定位** —— 按结构(字段数 / 纯数字列), 或直接换结构化来源(`Get-NetAdapterStatistics`、
  `Get-NetTCPConnection` 返回对象, 与码页无关; 若走 PowerShell 工具而非从 Bash 里 spawn);
  ③ **测量脚本必须做零值/量级自检**: 某计数器连续两次为 0, 或与预期量级差 3 个数量级 ⇒ 先当**解析失败**查,
  不得当结论用; ④ 结论若是否定命题(「没有 X 流量」), 至少两条独立路径交叉(netstat + 进程连接表 + 应用日志)。
- **守阵**: 属探针/环境侧, 常规守阵无可挂; 复验方式 = 同一命令同时跑「结构化来源」与「解析文本」两路, 数字应吻合。



- **崩在打印层**: [../git/message.md](../git/message.md)「流水线脚本在 GBK 控制台打印 emoji 直接崩」—— 那类是 `UnicodeEncodeError` **抛出来**, 反而容易被发现; 本条是**静默**的那种。
- **写盘方向**: [../git/editing-traps.md](../git/editing-traps.md)「合并冲突处理不要把 UTF-8 当 GBK 写入」—— 那类会**不可逆**地写坏文件, 检测要按 `U+FFFD` 计数, 别用 Git Bash 管道下结论。
## 缓冲侧: 管道下 stdout 块缓冲, 常驻服务的启动行「永远出不来」(2026-10-04 补)

- **触发**: 长跑/常驻脚本(本仓: `nav_server.py`, 经 `commands run kb.nav` 起服务)明明 `print` 了启动行,
  捕获方(引擎 `capture_output` / AI 工具管道 / `| tee`)却一个字都看不到, 进程活着但输出像死了。
- **判别**: 代码里有 print、进程没退、捕获端零输出 —— 不是编码问题(字节对不对是另一层), 是
  **stdout 被管道接住时 Python 自动切块缓冲**(isatty 真终端才是行缓冲), 少量输出在缓冲区里滞留,
  进程不退不出。编码 `reconfigure(encoding=...)` **不改变缓冲策略**, 修完编码还是看不见。
- **处置**: 常驻/长跑脚本入口对 stdio 一并 `reconfigure(line_buffering=True)`(同一次 reconfigure 里给,
  见 nav_server.py `_utf8_stdout`); 或者关键行改 `print(..., flush=True)`。守阵:
  `tests/test_kb_nav.py::test_log_filters_polling` 旁的冒烟路径 + 引擎 stream 通道
  (commands run.py, 2026-10-04) —— stream 模式 stdio 直连不落管道, 是另一条独立防线。

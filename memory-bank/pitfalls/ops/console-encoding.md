# 管道下按错的编码出/解中文 = 乱码但静默(子进程 + 引擎自身)

> 摘要: Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Python 子进程(如 node)输出就是 UTF-8, 而 `text=True` 按 locale 去解 ⇒ 直接抛 `UnicodeDecodeError`。再一变体(2026-10-02): AI 工具壳大输出落盘预览在截断点切进多字节字符时整段按 GBK 重解 —— 数据无损, 读落盘日志即真值。
> 触发: 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subprocess text=True, node 输出, encoding, 引擎自身 stdout, run.py 打印, 管道输出, 部分终端乱码, reconfigure, _utf8_self_stdio, PowerShell 捕获, Console.OutputEncoding, -NoProfile, AI 工具终端乱码, chcp 无效, 鍒涘缓, ConPTY, 大输出落盘, persisted output, 预览乱码, outputLimit, 截断点, 30KB, 块缓冲, line_buffering, flush, 输出滞留, 常驻服务无输出, 看不到 log, 无输出, netstat, 表头本地化, 解析恒 0, 探针假 0, 外部命令表头, 测量脚本零值自检, 重定向, UTF-16, Out-File, cmd 转发, FF FE
**Refs:** memory-bank/tasks/26-11-07-test-legacy-review4-scripts-fix.md

## 反向: 非 Python 子进程输出是 UTF-8, 别用 `text=True` 让 locale 去猜

- **触发**: 在测试或工具里 `subprocess.run(["node", ...], capture_output=True, text=True)`(2026-09-24 实测:
  `tests/test_extension_proxy_*.py` 用 node 跑 JS 归一化用例, 期望值里含中文报错)。
- **判别**: 抛的是 `UnicodeDecodeError: 'gbk' codec can't decode byte 0xaf ...`(不是 mojibake), 而且**抛出点很怪** ——
  堆栈落在 `subprocess._readerthread` 的后台线程里, 以 `PytestUnhandledThreadExceptionWarning` 的形式出现;
  不看警告就会误以为是“断言写错”。
- **处置**: 子进程收输出一律**显式指定** `encoding="utf-8"` **且** `errors="replace"`(两项都必填, 不是可选项);
  两边工具都写 UTF-8 时, 写死比“让 locale 猜”安全。
  与上一条合起来的口径: **要么收字节自己走兑底链解, 要么显式声明 UTF-8 —— 永远不要依赖 locale。**
- **判别补**: 只写 `encoding="utf-8"` 而漏 `errors` 同样会炸 —— stderr 混入码页字节时严格解码把
  `_readerthread` 打死, 管道再没人读, 子进程卡在写管道上 → `TimeoutExpired`; stdout 侧则是
  `proc.stdout is None` → `json.loads(None)` 报 `NoneType` / `.strip()` 报 `AttributeError`,
  表象离根因很远, 别当成 JS 探针死循环去调超时。
- **复发**: +3; 最近 (2026-11-10, issue 26-11-07-1216 修复批): 守阵 2026-11-06 落地时扫描面只 rglob `tests/**`,
  `scripts/` 存量 5 处同病长期漏扫(CI 不红但同病); 本批把扫描面扩成 `tests/ + scripts/` 并钉码,
  扩面守卫当场抓出单行 grep 漏掉的多行调用 `sim_run.py:813` —— **静态守卫的扫描面本身也要随目录面走全**。
  上次 +1 (2026-11-07, R4 scripts 批): 批内新测试红验回放又一处 `text=True` 缺 encoding/errors
  —— 为何没命中: 任务书未列该坑/路由没到; 守阵机检当场兜住(首跑红补钉即绿)。
  上次 +1 (2026-11-06, CI `windows-latest` cp1252 一次红 6 条 node 探针): 为什么没命中 ——
  坑档早就写了, 但 `处置` 把 `errors="replace"` 写成括号里的“可加”, 全仓 12 处 `text=True` 漏声明、
  另 4 处只声明 `encoding`, 也没有机检 ⇒ 新用例照抄旧写法。此处把口径收成**两项必填**, 并落
  `tests/test_platform_tolerance_guards.py::test_repo_text_subprocess_calls_pin_utf8` 全仓 AST 对账
  (带合成源活性探针)。本机复现: `PYTHONUTF8=0` 把 preferred encoding 压回 cp936。

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

判据、修复、守阵与复发记录见 [attachments/console-encoding-engine-stdout.md](attachments/console-encoding-engine-stdout.md)。

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

判据、处置与守阵见 [attachments/console-encoding-shell-preview.md](attachments/console-encoding-shell-preview.md)。

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

详细判据、处置与守阵见 [attachments/console-encoding-measure-probe.md](attachments/console-encoding-measure-probe.md)。

## 缓冲侧: 管道下 stdout 块缓冲, 常驻服务的启动行「永远出不来」(2026-10-04 补)

- **触发**: 长跑/常驻脚本(本仓: `nav_server.py`, 经 `commands run kb.nav` 起服务)明明 `print` 了启动行,
  捕获方(引擎 `capture_output` / AI 工具管道 / `| tee`)却一个字都看不到, 进程活着但输出像死了。
- **判别**: 代码里有 print、进程没退、捕获端零输出 —— 不是编码问题(字节对不对是另一层), 是
  **stdout 被管道接住时 Python 自动切块缓冲**(isatty 真终端才是行缓冲), 少量输出在缓冲区里滞留,
  进程不退不出。编码 `reconfigure(encoding=...)` **不改变缓冲策略**, 修完编码还是看不见。
- **处置**: 常驻/长跑脚本入口对 stdio 一并 `reconfigure(line_buffering=True)`(同一次 reconfigure 里给,
  见 nav_server.py `_utf8_stdout`); 或者关键行改 `print(..., flush=True)`。守阵:
  `tests/test_kb_nav_shell.py::test_log_filters_polling` 旁的冒烟路径 + 引擎 stream 通道
  (commands run.py, 2026-10-04) —— stream 模式 stdio 直连不落管道, 是另一条独立防线。

## CLI 入口的同一兜底: gtm 非控制台 print 中文会崩(2026-11-03 补, 同因不另立坑档)

- **触发**: 工具的 `python -m gtm` (或 console script) 被管道 / 服务日志捕获时, 帮助与告警里的中文
  经 `print` / `argparse.print_help` / `logging StreamHandler` 写 stdout/stderr; 英文 Windows
  把 stdio 码页定成 cp1252 ⇒ `UnicodeEncodeError: 'charmap' codec can't encode characters`,
  **本该展示的告警变成进程崩溃** (实测 `python -m gtm` 帮助退出码 1、stdout 为空)。
- **判别**: 与「引擎自身的 stdout」同指纹 —— 真控制台正常, 被管道接住就崩; 本机一行复现:
  `PYTHONIOENCODING=cp1252 PYTHONUTF8=0 python -m gtm`。注意方向: 这**不是**子进程收输出
  (上面两条), 是本进程往外写。
- **处置**: CLI 入口第一行 `_utf8_stdio()`(gtm `	ools/global-traffic-monitor/src/gtm/__main__.py`): 对 `io.TextIOWrapper`
  且 `encoding` 非 utf-8 的 stdout/stderr 做 `reconfigure(encoding="utf-8", errors="replace")`。
  只换编码, 不动缓冲 / `-u` / 重定向语义; 中文都在 UTF-8 码表内, `replace` 只兜孤立代理项
  ⇒ 原文不丢; 退出码仍由业务 `return` 决定, 不因编码改变。真控制台本来就是 utf-8
  (WriteConsoleW), 天然跳过。**不要**用全局 `PYTHONUTF8` 假设, 也不要用 `try/except: pass`
  吞编码异常。
- **守阵**: `test_main_run.py` +3 —— ①cp1252 `TextIOWrapper` 重配后按 UTF-8 出整行中文;
  ②`PYTHONIOENCODING=cp1252` 子进程 `python -m gtm` 的 stdout 帮助可见且 exit 0;
  ③同环境 `endpoint` 的 stderr 中文错误行可见且 exit 1(日志前缀契约不变)。前两档修复前必红
  (实测崩在 `argparse.print_help` 的 `file.write`)。

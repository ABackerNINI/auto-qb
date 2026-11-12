# CI 另一侧才现形的守阵: 写死平台前缀长度 / 活性阈值绑机器速度

> 摘要: 多类守阵/用例**只在与开发机不同的那一侧 CI job 上现形**, 本机单平台绿不构成"守阵成立"的证据 —— ①跨平台断言把**前缀切片长度写死**(`args[:2]`), nt 侧凑巧成立而 POSIX 侧恒红; ②并发守阵的**活性阈值绑机器速度**("写者写满 300 次…读者必读 >50 次"), 写耗时跨平台差一个量级 ⇒ 快机器上读者根本没读几轮就撞活性断言; ③断言引用**仅一侧存在的模块常量**(POSIX 无 `subprocess.CREATE_NO_WINDOW`); ④测试自起子进程 `print` 中文, **中文 Windows 本机 cp936 绿 / 英文 runner cp1252 红**(`UnicodeEncodeError` 把子进程退出码变成 1); ⑤收 node 探针输出时 `text=True` 让 cp1252 猜 UTF-8 字节(`UnicodeDecodeError` 打死 `_readerthread`, 见 [../ops/console-encoding.md])。五条都不是被测行为破了, 是**守阵/用例自身的平台/速度/码页依赖**。2026-10-22 gtm 子项目 (`tools/global-traffic-monitor`) 双平台 job 实证。
> 触发: CI 红本机绿, 跨平台断言, os.name, sys.platform, 写死切片长度, 前缀长度, 仅一侧存在的模块常量, CREATE_NO_WINDOW, 活性阈值, 并发守阵, 读次数, flaky, gtm, atomic_write, 双平台 job, cp1252, cp936, 码页, PYTHONIOENCODING, 子进程 print 中文, UnicodeEncodeError, UnicodeDecodeError, charmap, 英文 Windows runner, PytestUnhandledThreadExceptionWarning, proc.stdout None, json.loads NoneType, TimeoutExpired, node 探针, text=True, errors=replace, PYTHONUTF8=0

### 跨平台断言写死切片长度: nt 侧凑巧成立, POSIX 侧恒红

- **触发**: 给"拼命令再 spawn"这类动作写守阵, 断言命令**前缀**时按一侧的元组长度写死切片 (`args[:2]`), 而前缀长度本身随平台不同 (Windows `["cmd.exe", "/c"]` 两项 / POSIX `["/bin/sh"]` 一项); 或排查"本机 (Windows) 恒绿、CI ubuntu 恒红, 红因是列表长度不等"。
- **判别**: 失败 diff 显示**左边多一项** (`['/bin/sh', '<launcher>'] == ['/bin/sh']`), 且只在非开发机那一侧出现; 实现里前缀就是按平台分支拼的, 两侧长度天然不同 —— 写死的长度对一侧是巧合, 对另一侧是恒假。**别**当成"实现换了平台分支"去改实现。
- **处置**: 按前缀**实际长度**切片 —— `prefix = [...] if sys.platform.startswith("win") else [...]`; `assert args[: len(prefix)] == prefix`。平台判据与被测实现**同口径** (实现读 `sys.platform` 就别在测试里用 `os.name`, 两套判据本身也是隐患)。本地验证另一侧: 导入完成后再 `sys.platform = "linux"` 调被测函数 —— 必须在**按平台加载的第三方模块 import 之后**改 (psutil 会据此去 import `resource`, 先改必 `ModuleNotFoundError`), 一次性脚本跑完即删。
- **守阵**: 无机检; 长度对齐后两侧都钉住前缀, 判别力由断言本身承担。

### 并发守阵的活性阈值绑机器速度: 「写 N 次期间读者必读 >M 次」在快机器上必红

- **触发**: 为"写者高频原子重写期间读者只见完整文件"这类并发守阵配活性守卫 (`reads > 50 / > 100`), 靠**写者固定写 N 次**间接推断读者读够了多少轮。
- **判别**: 红的**不是**被守行为 (`violations == []` / `bad == 0` 恒绿), 而是活性计数 (实测 29 / 41, 阈值 50 / 100); 本机恒绿 ⇒ 单机 fsync 比 CI 慢一个量级, 写者收工时读者还没读几轮。**别**把阈值一路往下调 —— 那只是把守阵校准到本机速度, 换台机器照样红, 且判别力随阈值一起被稀释。
- **处置**: 把"期望读够"换成"**确保读够**" —— 写者循环条件改成「读者计数 < 门槛 且 写次数 < 上限(20000) 且 未过 deadline(15s)」: 线程版读内存计数器, 进程版让读者每轮把读次数写进**心跳文件**供父进程读 (读到写半途的空串按 0 处理, 不误判达标), 写完再置 done。活性语义保留且更强: 读者不干活时循环撞 deadline, 断言照红。实测注入"读者比写者慢 20 倍"仍达标 (约 7s), 正常路径 0.x 秒。
- **守阵**: 被守断言 (无半行/截断/空文件) 一字不改; 红验动作 = 把 `atomic_write_text` 改成 truncate 后分片直写 (非原子) → 两条守阵都红在 `bad` / `violations` 上 (2026-10-22 实证 `bad=90`), 改完用 `sha256sum -c` 复核实现已还原。

### 2026-11-03 三次实证: 跨平台断言引用一侧才有的模块常量(`CREATE_NO_WINDOW`)

- **触发**: 用例 `monkeypatch.setattr(infra_utils, "is_windows", lambda: True)` 强制走 Windows 分支后, 断言
  `kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW`; POSIX 的 `subprocess` 模块**不定义**该常量
  ⇒ CI ubuntu 恒红, 本机 Windows 绿。
- **判别**: 失败是 `AttributeError: module 'subprocess' has no attribute 'CREATE_NO_WINDOW'`, 不是断言值不等;
  强制分支只换了**实现判定**, 常量仍由当前平台的模块提供 —— Windows 专属常量不能照名直接取。
- **处置**: 与被测实现同口径兜底取常量 —— `getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)`
  (`relocate_mod._spawn` 本就是这款写法); **别**整体 skip 掉用例, 否则 Windows 正分支在 Linux 上失去守阵。
- **守阵**: `tests/test_relocate_exec_misc.py::test_spawn_args_pinned`; 无 WSL/容器时复现 Linux 语义:
  先 `del subprocess.CREATE_NO_WINDOW` 再同进程 `pytest.main(...)`(实测改前 AttributeError、改后绿)。
- **复发**: +1 (2026-11-03): 为什么没命中 —— 见到用例已用 monkeypatch 造平台差异, 就默认"两侧都覆盖了",
  没检查断言里引用的**模块常量**是否也随平台存在; 判别法当时只写了"切片长度/阈值", 没泛化到"仅一侧存在的符号"。
- **复发**: +2 (2026-11-13, 镜像方向: POSIX 专属常量在 nt 宿主被钉桩激活) —— port_kill 双支守阵把
  `os.name` 钉成 `posix` 激活 POSIX 实杀支, 生产表达式 `os.kill(pid, signal.SIGKILL)` 与测试断言引用
  `signal.SIGKILL`, Windows CPython 的 signal 模块**不定义**该属性 ⇒ 批次同步回 Windows 主 clone 跑
  test.full 必 AttributeError(与 CREATE_NO_WINDOW 同形反方向); 抓在评审 blocker, 未实际红。为什么没命中:
  本批只知道 recycle-obs 的 os.name 钉桩先例(platform-fs.md), 没回头扫本档「仅一侧存在的符号」判别面 ——
  钉桩时检查了**函数桩**, 没检查**实参表达式与断言里引用的常量**是否随平台存在。处置同款: 生产侧模块级
  单点 `_SIGKILL = getattr(signal, "SIGKILL", 9)`(兜 POSIX 实杀数值), 生产实杀与测试断言同源引用。

### 2026-11-03 实证: 测试自起子进程 print 中文 —— 本机 cp936 绿, 英文 runner cp1252 红

- **触发**: 用例用 `subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)` 起子进程,
  子进程脚本里 `print('BUSY', e)` 打印含中文的异常消息; 开发机 (中文 Windows, cp936) 绿, GitHub
  `windows-latest` (英文 Windows, cp1252) 红, 失败行是 `assert proc.returncode == 0`。
- **判别**: 失败 stderr 里被测行为**已经正确发生** (单实例锁抛出 `SingleInstanceLockError`), 挂在
  `print` 的编码上 —— 子进程 stdout 是管道时 Python 按 locale 码页编码, 本机 cp936 能编码中文所以绿,
  cp1252 编不了 ⇒ `UnicodeEncodeError: 'charmap' codec can't encode characters` ⇒ 子进程退出码 1。
  红的是**宿主码页依赖**, 不是被测语义; **别**把 `returncode == 0` 放宽成 `!= 0` 或吞掉错误来"修"。
- **处置**: 子进程显式 UTF-8 stdio —— `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`; 捕获端同编码
  `encoding="utf-8"` 替代 `text=True`(让 locale 猜)。`PYTHONIOENCODING` 只影响 stdio, 不会像
  `PYTHONUTF8=1` 那样改子进程 `open()` 的默认编码; 与 [../ops/console-encoding.md] 的"子进程收输出
  显式编码"同口径, 方向是**测试自产输出**。断言顺序把「被拒信号」(BUSY + 持有者 PID) 放到退出码之前:
  只看退出码分不清「编码/导入崩溃」与「锁正常拒绝」。
- **守阵**: `tools/global-traffic-monitor/tests/test_storage.py::test_single_instance_lock_blocks_second_process`
  及同文件另一条子进程用例 (子脚本异常文案也含中文); 本机复现 = 父进程注入 `PYTHONIOENCODING=cp1252`
  再跑用例 —— 实测改前红 (退出码 1 + `charmap` 报错), 改后绿。

### 2026-11-06 实证: 同族第 ⑤ 变体 —— 收端解码(不是发端编码), 一次红 6 条 node 探针

- **触发**: `tests/` 里 `subprocess.run([node, ...], capture_output=True, text=True)` 收 JS 探针输出;
  中文开发机 (cp936 + `PYTHONUTF8=1`) 绿, GitHub `windows-latest` (cp1252) 一次红 6 条。
- **判别**: 与上面 ④ **方向相反** —— ④ 是子进程往外 `print` 中文 `UnicodeEncodeError`,
  本变体是父进程按 locale 解 UTF-8 字节 `UnicodeDecodeError: 'charmap' codec can't decode byte`
  (警告落在 `subprocess._readerthread`); 症状是 `proc.stdout is None` → `json.loads` 报 `NoneType`、
  `.strip()` 报 `AttributeError`, 以及严格解码打死读线程后的 `TimeoutExpired`。**别**当成 JS 死循环去调超时。
- **处置**: 收端 `encoding="utf-8", errors="replace"` 两项都写(口径单点见 [../ops/console-encoding.md]
  「反向」节, 本变体的 `复发 +1` 记在那条); node 电池超时统一 60s。
- **守阵**: `tests/test_platform_tolerance_guards.py` 新增全仓 AST 对账 + 合成源活性探针,
  12 处漏声明与 4 处漏 `errors` 一次收口; 本机复现 = `env -u TMPDIR PYTHONUTF8=0` 跑用例
  (改前 5 failed 1 passed → 改后 6 passed; 全量 `test.quick` 5479 passed)。
- **反面证据 / 复现局限**: 本机 `PYTHONUTF8=0` 压回的是 cp936, **不是** runner 的 cp1252 ——
  两种码页对同一串 UTF-8 字节的失败点不同, 6 红里本机只复现出 5 红; 超时那条
  (`test_search_excluded_matches_hint_computed`) 改前本机就绿, 它的修复依据只有 CI 日志。
  别把本机全绿当成等价验证, 最终判据仍是 `windows-latest` 实跑。

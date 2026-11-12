# 26-11-13-test-port-kill-posix-branch — port_kill/e2e_selfcheck POSIX 平台双支修复(issue 26-11-13-0234)

**Status:** Done
**Added:** 2026-11-13
**Updated:** 2026-11-13
**Summary:** port_kill.py/e2e_selfcheck.py 按 os.name 双支修 POSIX 面(原 Windows-only 必炸), 守阵双支钉桩 8 条新/改, env3 实机三连验, issue 翻 Done
**Topics:** test-port-kill-posix-branch

**Refs:** memory-bank/issues/26-11-13-0234-bug-port-kill-linux-no-posix-branch.html

## 本篇只回答

issue 26-11-13-0234 怎么修的: port_kill.py(查询两函数+实杀)与 e2e_selfcheck.py(_proc_info)从 Windows-only 改为按 os.name 双支, POSIX 支如何零外部依赖实现且不削弱「先核身份再定点杀」豁免语义, 守阵如何两支钉桩在任一平台都跑。

## 原始请求

1. 用户: 「fix memory-bank/issues/26-11-13-0234-bug-port-kill-linux-no-posix-branch.html」—— 认领并修复该入池 issue(显式授权认领; 未说「提交」, commit/push 不在本轮动作内)。

## 思考过程与决策

- 方案采 issue §06 候选 A: POSIX 支 /proc 直读零外部依赖(/proc/net/tcp{,6} Listen 态 inode -> /proc/*/fd socket 反查; comm/cmdline 归属), 不引 ss 文本耦合(B 项); pyproject 无 psutil, 也不新增依赖。
- 豁免语义(AGENTS.md「🔴进程安全」)两平台原样: kill_decision 纯函数闸不动, 实杀收进 _kill_pid 单点(nt=taskkill /F /PID 原样 / posix=os.kill SIGKILL), process_info 缺席=verify-failure 两支一致(POSIX /proc 读不了即缺席, 调用方拒杀)。
- e2e_selfcheck 第三处 powershell 位按 issue 建议收编: _proc_info 改为复用 port_kill.process_info, 不复制第二份查询; 静态钉(e2e_selfcheck 无 powershell/Win32_Process 字面量)防复活。
- 守阵按 recycle-obs os.name 桩先例: 两支各 os.name 桩钉住在任一平台都跑; POSIX 查询单测用假 /proc 树(PROC_ROOT 模块常量注入)+ readlink 桩(fd 文件内容即目标), 免 Windows symlink 权限差异; main 接线用例沿用函数级桩。
- 评审 blocker 修法: Windows CPython 无 signal.SIGKILL, 守阵钉 posix 支会在 nt 宿主触雷 -> 生产侧模块级 `_SIGKILL = getattr(signal, "SIGKILL", 9)` 单点, 生产实杀与测试断言同源引用。
- rc 语义: main 实杀段从 `rc |= taskkill.returncode` 改为失败置 1, 调用方(commands 引擎)只判非零, 无兼容面。

## 实现计划

1. port_kill.py: listening_pids/process_info 按 os.name 分派(nt 支逐字节保留), 新增 _listening_pids_posix/_process_info_posix/_kill_pid, 模块常量 PROC_ROOT/_SIGKILL。
2. e2e_selfcheck.py: _proc_info 复用 process_info 单点; CLONE_HINT_RE 扩 posix 绝对路径形态; 摘要统一截 160。
3. 守阵 tests/test_legacy_review4_scripts.py: 既有 4 条旧用例(3 main 接线 + 1 process_info 解析)补 os.name="nt" 钉; 新增 8 条(proc 全链/归属/posix main 接线含 verify-failure/posix 实杀失败面/nt 实杀失败面/nt listening 解析钉/收编静态钉/_check_port 显示链行为钉); 测试计划清单同步。
4. 验证: env3 红锚复现 -> 修复 -> 实机三连(dev.e2e-check 绿 / --blocking 归属行 / dev.port-kill 实杀自置桩后复位绿); test.quick/test.full 全绿(见 kb.baseline)。
5. 评审: 分面 3 派遣(正确性/安全/测试缺口)+ 复评 4 轮(轮 2 头段 nit / 轮 3 零发现 / 轮 4 文档面 4 条 / 轮 5 终验), 送检过检 9/9 全修零 actionable; issue 翻 Done; 坑档 ci-only-guard 复发 +2 与 env3-test-run-prereqs 新档入档。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | port_kill.py 平台双支+实杀单点 | Done(2026-11-13) |
| 2 | e2e_selfcheck 收编单点+CLONE_HINT_RE 双平台 | Done(2026-11-13) |
| 3 | 守阵 8 条新/改+4 条补钉+清单同步 | Done(2026-11-13) |
| 4 | env3 实机验证+全量回归 | Done(2026-11-13) |
| 5 | 分面评审+复评 2 轮+修复 | Done(2026-11-13) |
| 6 | issue 翻 Done+基线切片+坑档+kb.index | Done(2026-11-13) |

## 进度日志

### R0 · 立档 (2026-11-13)

认领 issue 26-11-13-0234(用户显式 fix 指令)并一轮修完: 红锚复现(dev.e2e-check 0.1s 即 FileNotFoundError: powershell) -> os.name 双支落地 -> env3 实机三连验 -> 评审 5 轮: 轮 1 分面 3 派遣(正确性/安全/测试缺口)送检 8(1 blocker: Windows 无 signal.SIGKILL, 守阵钉 posix 支在 nt 宿主必 AttributeError -> 生产 _SIGKILL=getattr 单点; 4 minor: 守阵对称性欠账; 3 nit)全修; 轮 2 补报 1 nit(头段桩面表述过宽)已修; 轮 3 零发现; 收尾文档面(翻 Done/坑档/基线切片)进可评面后轮 4 报 4 条(1 major: 基线切片引用不存在的坑档名(改道残留死指针) + 1 minor: TZ 红谓词过宽(仅美制 DST 时区红, 非「非 +08:00 必红」) + 2 nit)全修; 轮 5 终验零发现, 零 actionable 出口。机械账: 送检过检 9/9 全修(轮 1 x8 + 轮 4 x1); 轮 2/轮 4 余 4 条修在引文校验前, 按修后树 REFUTE 不入账, 属自发修; trailer 留痕随提交信息入库。issue 翻 Done 补复验/修复后补充; 全量绿(见 kb.baseline); 真机自检: 本修复即真机轨(真进程/真端口操作), env3 本机已实测三连(dev.e2e-check 绿、占口归属行、dev.port-kill 实杀自置桩后复位绿)。

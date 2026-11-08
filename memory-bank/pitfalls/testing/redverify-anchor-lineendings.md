# 红验脚本按 LF 拼锚点，在 CRLF 文件上静默匹配不上（且手抄缩进易差 1 空格）

> 摘要: 变异审计的**红验**要靠「把源码某段文本替换成变异体 → 跑目标用例 → 还原」。主仓相当一部分 `.py` 是 **CRLF** 行尾(如 `src/auto_qb/config/schema/__init__.py`), 而红验脚本通常 `read_bytes().decode()` 后直接拿**带 `\n` 的多行字符串**当锚点 —— CRLF 文件里这种锚点 `count == 0`, 替换**根本没发生**, 但脚本若只按「跑完绿不绿」判 KILLED/SURVIVED, 就会把「没变异」的绿当成「变异存活」(假 SURVIVED), 或反过来把空转的探针当通过。第二个同源陷阱: 锚点里的**缩进空格靠手抄**, 极易差 1 个(实测 52 vs 51 字符), 同样静默失配。判别: 红验结果里出现 `ANCHOR-MISS` 就停手; 没有这个兜底时, 表现为「明明写了对的守阵却仍 SURVIVED」。处置: ①锚点先 `replace("\r\n", "\n")` 归一到 LF 空间再匹配、写盘前转回; ②缩进一律用 `" " * N` 拼接, 不手抄; ③锚点 `count != 1` 必须报错停手(数量 >1 说明锚点不唯一, 也不可用)。
> 触发: 红验, 变异测试, mutmut, apply, 同构变异, 锚点, 锚点失配, ANCHOR-MISS, 源码替换, 还原, CRLF, LF, 行尾, newline, 缩进, 空格数, 差一空格, read_bytes, write_bytes, 假绿, 假存活, 守阵空转, 探针空转, dump 行块, 函数相对行号, hunk 头, qualname, 分隔符字形, docstring 续行, 子进程超时, 解释器漂移, venv 解释器, sys.executable, 假红, 环境坏, 基线复跑, TimeoutExpired, 超时未接住, 脚本崩在中途, 收尾自证被跳过, 守阵挂起, 挂起也算红, 死锁, 非重入锁

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-08-1229-mutants-config-schema-surface.md, memory-bank/testing/baselines/26-10-10-0925-mutants-config-loader-defaults.md, memory-bank/testing/baselines/26-10-10-1408-mutants-hr-service.md, memory-bank/testing/baselines/26-10-10-1458-mutants-hr-serialization.md, memory-bank/testing/baselines/26-10-10-2044-mutants-hr-judgment-core.md, memory-bank/testing/baselines/26-10-15-0927-mutants-hr-channel-server.md, memory-bank/testing/baselines/26-10-16-1016-global-traffic-monitor-s4.md, memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

**复发**: 9(2026-10-10 ~ 10-16 九轮, 逐轮首版踩坑流水已并入本档形态三~十二(三/四/五/六/七/九/十原文见下方附件指针)的触发/根因/处置; 四类兜底信号贯穿全档: 输出 `ANCHOR-MISS` 即停手 / apply 后 `ast.parse` 自检记 `APPLY-ERROR` / 红验数字与 S6 逐文件对差 / 突变循环前先跑一次无变异基线且必须绿)。只记在流水里的两条判据: ①**单行锚点撞「函数级重复」在委托型包装类里是高发区** —— `acquire`/`release` 这类簿记方法天然成对出现(形态三第二例与 gtm S2 轮 `self._lock.acquire()` 两度命中, 均被 `count != 1` 兜底拦下), 首版写锚点前先 grep 全文件数一遍; ②守阵**挂起**也是一型(gtm S4 轮: 派发同步化突变撞非重入锁死锁, 设了 timeout=300 却没接住 `TimeoutExpired`, 脚本崩在中途、「还原后基线复跑」被跳过) —— 处置见形态十二(挂起 = 未绿, 与 mutmut timeout 同口径, 保证「还原 -> 基线复跑」恒被执行)。

## 已外迁的形态(原文见附件)

- 形态一/二(config schema 键面轮): CRLF 让多行锚点静默失配、手抄缩进差 1 空格 — [attachments/redverify-forms-crlf-indent.md](attachments/redverify-forms-crlf-indent.md)
- 形态三/四/五/九: 字节层类型失配、dump 整体去缩进/续行不归一、hunk 函数相对行号/`ǁ` 字形/docstring 续行、`min` 位移伪判 SURVIVED — [attachments/redverify-dump-and-hunk-forms.md](attachments/redverify-dump-and-hunk-forms.md)
- 形态六/七(hunk 上下文行 / `add` 行缩进基准取首行 ⇒ `IndentationError` 伪判 KILLED) — [attachments/redverify-hunk-context-forms.md](attachments/redverify-hunk-context-forms.md)
- 形态十(写侧 `write_text` 反向污染行尾 + `read_text` 探针洗白 + KB 回写同型)与不可达分支上的空转探针 — [attachments/redverify-write-side-and-probe.md](attachments/redverify-write-side-and-probe.md)

### 形态十一: 红验脚本解释器漂移 —— 环境坏的"测试"被按"守阵杀死变异"判红（global-traffic-monitor S3 轮）
- **触发**: 临时红验脚本放在工具 venv 之外(H:/Temp), 跑测试用 `sys.executable`(系统 python)——系统 python 无 pytest/psutil, 每条突变的「跑目标用例」都以**环境错误**退出(rc!=0), 脚本按「未绿 = 被杀」判 KILLED ⇒ 6/6 全判红**全是假红**(守阵压根没参与; 被测代码连 import 都没成)。
- **同源第二面**: 基线复跑同样假红(末行输出为空 —— 环境错误在用例收集之前), 这是本轮唯一的暴露点; 若基线复跑也显示"绿"(比如脚本吞了输出), 假红会一路走进基线切片数字。
- **判别**: 与「尾部同源陷阱」那句同口径 —— 红验唯一可信信号是「锚点命中数==1 **且** 跑完变红 **且** 环境本身无变异时基线绿」, 缺最后一半都不能算验过。**凡结果与预期不符, 先怀疑脚本/环境, 再怀疑守阵**(形态七/九的同一判别纪律, 方向相反: 那两条是代码坏被伪判, 这条是环境坏被伪判)。
- **处置**: ①红验脚本显式钉死**目标 venv 解释器绝对路径**, 不用 sys.executable(工具包场景尤其: 脚本常驻仓库外); ②突变循环之前先跑一次**无变异基线**(本环境干净), 不绿就停手; ③bytes 层锚点/还原纪律不变(形态一/十), 与本形态正交。

### 形态十二: 设了子进程超时却没接住 `TimeoutExpired` —— 脚本崩在中途, 收尾自证被跳过（global-traffic-monitor S4 通知轮）

- **触发**: 突变体让守阵**挂起**(见下「挂起也是一种红」), `subprocess.run(..., timeout=300)` 抛 `TimeoutExpired` —— 脚本没接, 异常穿透突变循环(还原那步在 `finally` 里执行了)后直接终结进程, **突变循环剩余条目与「还原后基线复跑」全被跳过**。
- **判别**: 输出里出现 traceback 且汇总表缺失/不完整 ⇒ 本轮红验**不可信**(流程没走完); 这是形态五那句「子进程必须设超时」的**第二半 —— 设了超时还必须接住**。
- **处置**: ①`run_tests` 捕获 `TimeoutExpired` -> 返回哨兵码 + 文案「TIMEOUT(守阵挂起 -> 按未绿计 RED)」; ②超时值按目标用例规模收紧(本轮 300s -> 90s); ③突变循环体内再包一层 `except Exception` 兜 harness 侧异常, 保证「还原 -> 基线复跑」恒被执行。
- **配套认识(挂起也是一种红, 但不是断言级信号)**: 同步派发突变下采样线程持锁内联执行推送、与自身 `finally` 抢**非重入锁** -> 死锁 -> 守阵永不返回。这类「未绿」与 mutmut 的 timeout 同口径计入被杀, **但报告里必须写明红因是挂起而非断言失败** —— 与「红因分布逐条核对目标断言」(见 [red-verify-must-hit-behavior.md](red-verify-must-hit-behavior.md))同一条纪律。

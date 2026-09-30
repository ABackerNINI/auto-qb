# commands 引擎自身 stdout 乱码修复(部分终端)

> 摘要: 用户报「部分终端 `commands run kb.active` 中文乱码」—— 子进程方向 9-24 已修, 这轮是引擎**自身** stdout 在管道下按本地码页出中文; 已修(`_utf8_self_stdio()` 在 main() 入口锁 UTF-8)并加 2 条守阵。**2026-10-01 复发轮**: 用户报「已同步仓库仍乱码」—— 引擎侧修复有效, 乱码源在**解码侧**(PowerShell 捕获类 / AI 工具 `-NoProfile` 外壳按 GBK 解 UTF-8), 已修两份 PS profile 并回写坑档; 引擎侧不变。
> 触发: 输出乱码, 部分终端, commands 引擎, 自身 stdout, 管道, cp936, reconfigure, run.py, mintty, PowerShell 捕获, -NoProfile, AI 工具终端
> 最后活动: 2026-10-01 07:20

## 状态

**Done**(2026-09-30, 小修, 未立项 —— 低于立档阈值)。用户报「部分终端运行 `commands run kb.active` 显示乱码」。

**根因(取证, 非猜测)**: 9-24 修的是**子进程→引擎**方向; 引擎**自己 print 的中文**(协议行 / 包摘要 / 透传正文)走 Python 自身 stdio —— 真控制台是 `WriteConsoleW`(Unicode, 永不乱), stdout 一旦被**管道**接住(mintty / AI 工具捕获 / CI)编码回退本地码页 cp936。实测: 剥离 `PYTHONUTF8`/`PYTHONIOENCODING` 后 `show kb.active` 首段中文是 GBK 字节, strict UTF-8 解码当场炸, 退出码照旧 0; 会话里的 UTF-8 变量是工具 shell 会话级注入(注册表 HKCU/HKLM 均无), 用户终端裸奔 —— 这就是"部分终端"的分界线。

**修法**(引擎单点 `run.py`, 与 9-24 同文件): `_utf8_self_stdio()` —— stdout+stderr `reconfigure(encoding="utf-8", errors="replace")`, `main()` 第一行调用(先于任何 print / argparse 输出)。真控制台不受影响; 管道对端从 GBK 变 UTF-8, 只修不破。

**守阵**: `test_engine.py` +2(cp936 文本层单测 / 剥变量+管道子进程端到端 strict 解码)。test.pkg 74 passed。

- [坑 (ops/console-encoding)](../pitfalls/ops/console-encoding.md)
- [上一轮: 子进程方向](../pitfalls/ops/console-encoding.md)（原切片 26-09-24-2029 已随 26-09-30 切片数守卫蒸馏, 内容归坑档）
- [测试基线](../testing/baseline.md)

## 实测

修后剥离全部 UTF-8 环境变量 + 管道跑 `show kb.active`: strict UTF-8 解码 OK, 首行「何时用: 看会话滚动状态…」完好;
全量数字只认单点 [testing/baseline.md](../testing/baseline.md)(本切片不复述)。

## 2026-10-01 复发轮: 解码侧(PS 捕获类 / AI 工具外壳)

用户纠错「代码已同步的仓库中仍乱码」→ 取证推翻「旧 clone 未同步」的初判(本机 clone3/4/5 确实旧, 但不是用户场景)。ConPTY 伪控制台探针逐类实测: 交互真控制台(cmd / PS5.1 / pwsh7)全干净; 乱的是 **PS 捕获路径**(管道 / 赋值 / `-Command` 外壳)——按 `[Console]::OutputEncoding`(GBK)解引擎的 UTF-8, `创建`→`鍒涘缓`。用户指认场景 = **AI 编码工具的终端**(此类工具多经 `powershell -NoProfile -Command` 跑命令, 内层 PS 按 GBK 解, 工具按 UTF-8 读 → 必乱)。

机制实测: PS 在**启动瞬间**快照控制台码页 —— 运行中 `chcp 65001` 救不了; 启动前已是 65001 时连 `-NoProfile` 捕获都正确。

**修法**(解码侧, 引擎不动): 两份 PS profile 加 `try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}`(用户授权); 端到端验证改前 `鍒涘缓` → 改后 `创建`(pwsh 7.6.6 + PS 5.1 双验)。`-NoProfile` 工具类 profile 救不了 —— 系统级「Beta: UTF-8」或该工具换 Git Bash shell, 用户自拍板(未做)。

- [坑档新增「解码侧」节](../pitfalls/ops/console-encoding.md)(含复发标记与 chcp/cmd/PS 三方结论的边界)
- 本轮无仓库代码改动(仅坑档 + 用户级 profile), 未跑 test.full, 未提交

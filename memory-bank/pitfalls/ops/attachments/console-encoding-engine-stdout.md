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


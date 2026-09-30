# 基线 · 1832 passed + 3 skipped / 90% —— commands 引擎自身 stdout 锁 UTF-8(部分终端乱码修复)

> 摘要: 用户报「部分终端 `commands run kb.active` 中文乱码」—— 9-24 修的是子进程→引擎方向, 本轮补上引擎**自身**
> stdout/stderr 的同族漏网: 真控制台走 WriteConsoleW(Unicode)永不乱, stdout 被管道接住(mintty / AI 工具捕获 /
> `| tee` / CI)时 Python 自身 stdio 回退本地码页 cp936。修法 `run.py` 的 `_utf8_self_stdio()`(main() 首行
> reconfigure utf-8+replace); 守阵 +2 落在 pkg 收集面。端到端红验: 修前同场景 GBK 字节 strict 解码当场炸, 修后完好。
> 基线时间: 2026-09-30 10:31 (develop @ bfef758c + 本轮未提交改动)
> 档案: [activeContext/26-09-30-1007-commands-engine-self-stdio.md](../../activeContext/26-09-30-1007-commands-engine-self-stdio.md)

TOTAL **1832 passed + 3 skipped / 90%**(12731 语句 / 1042 未覆盖 / 4344 分支 / 431 partial,
rc=0, 同树两采样 26.5 / 36.9s) —— 较上基线 26-09-30-1210(1829 passed + 3 skipped)增 3:
全部出自远端 87f3437..bfef758c 六笔提交(07:49–09:47)的 tests/ 变更(+133/-45: test_commands_engine
重排 80 行 / test_utils +83 / test_web_shortcuts +15)。**本轮 +2 守阵落在 pkg 收集面**
(.agents/skills/commands/scripts/test_engine.py, testpaths 之外)—— test.pkg 74 passed 含之, 不进本计数。
覆盖率 91%→90%: 语句 12650→12731(+81)同出远端六笔; 本轮只动 .agents/(--cov=src 之外, 对 TOTAL 零贡献)。

> 注(时间戳): 时间取本机钟(与远端提交钟一致)。上一切片 26-09-30-1210 的 12:40 戳出自偏快 ~2.5h 的实例钟 ——
> 因果证据: 该切片在本机 10:07 前首次同步的树内已存在, 而其后续提交 author date 均 ≤09:47。文件名排序在
> timekit(已入档 bfef758c, 暂不实施)落地前会把 1210 误排在本切片之前 —— 人读以基线时间为准, 本切片为当前事实源。

## 本轮改动面

- `.agents/skills/commands/scripts/run.py`: +`_utf8_self_stdio()`(stdout+stderr
  `reconfigure(encoding="utf-8", errors="replace")`), `main()` 首行调用; docstring 编码口径一行。+22 行。
- `.agents/skills/commands/scripts/test_engine.py`: +2 守阵(cp936 文本层单测 / 剥全局 UTF-8 变量 + 管道
  子进程 strict 解码端到端)+ 测试计划清单同步。+38 行。
- `memory-bank/pitfalls/ops/console-encoding.md`: 标题扩口径 + 触发词 + 「引擎自身的 stdout」新节(+23/-2)。
- test.pkg 74 passed; dev.fmt 两文件已过。

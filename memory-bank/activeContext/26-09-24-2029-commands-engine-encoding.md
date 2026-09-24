# commands 引擎子进程输出乱码修复

> 摘要: 引擎(commands)按 UTF-8 硬解子进程输出, 而 Windows 上被管道接住的 Python 子进程按 cp936 输出 ⇒ `commands run kb.index` 的中文变 `������`; 已修(强制子进程 UTF-8 stdio + 解码兜底)并加 7 条守阵。
> 触发: 输出乱码, commands 引擎, kb.index 乱码, 子进程编码, cp936, PYTHONIOENCODING, U+FFFD, run.py, _shell, _decode
> 最后活动: 2026-09-24 20:29

## 状态

**Done**(2026-09-24, 小修, 未立项 —— 低于立档阈值)。用户报「跑 `commands run kb.index` 输出乱码」。

**根因(取证, 非猜测)**: `uv run` 下引擎自己 stdout = UTF-8(所以 `[ok] ...` 与引擎自己的中文行都正常), 但它 `shell=True` 起的**孙进程**(`kb.index` 那两条包脚本)的 stdout 被管道接住时按**本地码页 cp936** 输出; 引擎 `text=True, encoding="utf-8", errors="replace"` 硬解 ⇒ `已生成 16 个索引` 变 `������ 16 ������`。抓原始字节确认是 GBK(`b'\xd2\xd1\xc9\xfa\xb3\xc9 16 \xb8\xf6\xcb\xf7\xd2\xfd'`), **退出码照旧 0** —— 静默的坏。

**修法**(引擎单点 `.agents/skills/commands/scripts/run.py`, 不动任何包脚本):
- 子进程环境注入 `PYTHONIOENCODING=utf-8`(`_CHILD_ENV`; 只影响 stdio, 不用 `PYTHONUTF8=1` 那个会改 `open()` 默认编码的; 放在 pack env **之前** ⇒ 包仍可覆盖);
- `_shell` 改为**按字节**收输出(`text=True` 等于把编码写死), 解码走 `_decode`: `UTF-8 → locale.getpreferredencoding(False) → errors="replace"`(非 Python 子进程仍可能给 GBK, 这一层兜住)。

**守阵**: `tests/test_commands_engine.py` +7(GBK 回退 / UTF-8 优先 / 任意字节不抛 / env 注入与按字节收 / GBK 子进程输出可读 / 失败 rc 不吞)。测试里**不真起子进程**(`tests/sidefx.py` 的 POPEN 记账判越界) ⇒ 用假 `subprocess.run` 直接给字节。**红验**: A/B 对照 —— 修前解出 `������ 16 个索引`, 守阵对该差异敏感。

**追记(同轮)**: 计划文档两处错字「兵底」→「兜底」一并修掉(记入计划 v1.8 变更行)。

- [坑 (ops/console-encoding)](../pitfalls/ops/console-encoding.md)
- [引擎收录协议](../../.agents/skills/commands/references/howto-add-command.md)
- [测试基线](../testing/baseline.md)

## 实测

修后 `commands run kb.index` 正常输出「已生成 memory-bank\tasks\_index.md / 已生成 16 个索引」;
本文件单跑 `tests/test_commands_engine.py` = 24 passed / sidefx 越界 0;
全量数字只认单点 [testing/baseline.md](../testing/baseline.md)(本切片不复述)。

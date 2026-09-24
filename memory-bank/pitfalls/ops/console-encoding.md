# 子进程输出按错的编码解 = 乱码但静默

> 摘要: Windows 上被管道接住的 Python 子进程按**本地码页(cp936)**输出 stdout, 而调用方按 UTF-8 硬解 ⇒ 中文变一串 U+FFFD; 退出码照旧 0, **一个报错都没有** —— 只有人读输出时才发现。**反方向也一样会炸**: 非 Python 子进程(如 node)输出就是 UTF-8, 而 `text=True` 按 locale 去解 ⇒ 直接抛 `UnicodeDecodeError`。
> 触发: 输出乱码, 乱码, 中文变问号, U+FFFD, 子进程 stdout, cp936, GBK, PYTHONIOENCODING, 引擎打印外部输出, 包装脚本, 命令行工具输出, UnicodeDecodeError, subprocess text=True, node 输出, encoding

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

## 同族旧账(互补, 别只修一处)

- **崩在打印层**: [../git/message.md](../git/message.md)「流水线脚本在 GBK 控制台打印 emoji 直接崩」—— 那类是 `UnicodeEncodeError` **抛出来**, 反而容易被发现; 本条是**静默**的那种。
- **写盘方向**: [../git/editing-traps.md](../git/editing-traps.md)「合并冲突处理不要把 UTF-8 当 GBK 写入」—— 那类会**不可逆**地写坏文件, 检测要按 `U+FFFD` 计数, 别用 Git Bash 管道下结论。

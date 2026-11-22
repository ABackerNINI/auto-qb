# port-kill-gbk-mojibake

> 摘要: 修复 issue 26-11-23-0012: port_kill._kill_pid nt 支收字节改按 mbcs(系统 ANSI 码页)解码, GBK 原因行不再 mojibake, POSIX 支零改动; 新增 1 条真 GBK 字节守阵(红绿双验), 16 条 port_kill 用例定向绿; 评审零发现(检 0/0), test.full 全绿见 kb.baseline 26-11-23-0131; 中文 Windows 真字节本机对照实测, 未对真实进程触发 taskkill; issue 翻 Done; 零 commit/push(用户未授权)
> 最后活动: 2026-11-23 01:31

**R0(2026-11-23 01:31):** 修复 issue 26-11-23-0012: port_kill._kill_pid nt 支收字节改按 mbcs(系统 ANSI 码页)解码, GBK 原因行不再 mojibake, POSIX 支零改动; 新增 1 条真 GBK 字节守阵(红绿双验), 16 条 port_kill 用例定向绿; 评审零发现(检 0/0), test.full 全绿见 kb.baseline 26-11-23-0131; 中文 Windows 真字节本机对照实测, 未对真实进程触发 taskkill; issue 翻 Done; 零 commit/push(用户未授权)

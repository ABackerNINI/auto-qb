# 工具沙箱内跑全量会假红: 沙箱拒写 R:\Temp, TMPDIR 等于没设

> 摘要: 沙箱内跑 `commands run test.full` 等自带 `TMPDIR=R:/Temp/...` 的测试命令, 沙箱拒写 R 盘 ⇒ `TMPDIR` 建不了目录 ⇒ pytest 回落 `H:\Temp`(重解析点读不了) ⇒ **点号全过却在收尾崩**, 看着像回归实为沙箱拦截; 关沙箱即消失。
> 触发: 沙箱, 沙箱假红, TRAE Sandbox, R:\Temp, TMPDIR 没设, 跑全量, test.full, preflight, 闸门假红

## 现象与处置(2026-09-24 实测; 从 testing/tmpdir.md 拆出)

- **触发**: 沙箱内跑 `commands run test.full` 等自带 `TMPDIR=R:/Temp/...` 的命令, 2026-09-24 实测。
- **判别**: 点号全打完、**一条都没失败**, 却在收尾 `cleanup_dead_symlinks` 抛
  `PermissionError [WinError 5] … pytest-current`; 输出另有 `TRAE Sandbox Error: hit restricted` +
  `Not allow operate files: R:\Temp\…`。链路: 沙箱拒写 R 盘 ⇒ `TMPDIR` 也建不了目录 ⇒
  pytest 回落 `H:\Temp`(重解析点读不了, 机制见 [tmpdir.md](tmpdir.md))。⚠ 与该文件的成因**不同** ——
  这是**沙箱拦截**, 关沙箱即消失。
- **处置**: 跑全量时**关沙箱**, **不是改命令**(命令是对的, 改了反而失去 TMPDIR 收口)。
  ⚠ 沙箱内的 `preflight` 命中 pytest 闸门时同样假红 —— 闸门继承调用方的沙箱。

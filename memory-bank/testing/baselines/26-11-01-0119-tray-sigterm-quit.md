# 4344 passed, 10 skipped (coverage 99%: 21814 stmts, 163 miss, 7394 br, 127 pb) —— 托盘 SIGTERM 优雅退出落地(issue 26-10-31-1030)

> 摘要: 托盘模式 SIGTERM 优雅退出落地 —— handler 换装投递 quit 事件与托盘菜单「退出」合流 + run() 收尾挂 finally 兜底; 红绿双验 + 真机 3 连
> 基线时间: 2026-11-01 01:19
**Refs:** memory-bank/tasks/26-11-01-backend-tray-sigterm-quit.md

## 验收数字

`commands run test.full` (199.5s, 2026-11-01 实测):

```text
TOTAL                                                21814    163   7394    127    99%
4344 passed, 10 skipped in 199.48s (0:03:19)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
真机面(独立轨, 不进本数字): graceful 跑壳(进程内 raise_signal)SIGTERM@25s 对 `--tray` 进程 3/3 于 27.0s 退出 rc=0, 无「主循环未在 10s 退出预算内收尾」WARNING, ui.port 清理, stderr 无堆栈; 修复前同法 3/3 观测 70s 不退(issue 26-10-31-1030 复验一致)。skipped 与上条切片同环境口径(node/平台性跳过)。

## 本改动面

- `src/auto_qb/tray/app.py`: SIGTERM 换装 —— 新增 `_sigterm_to_quit`(首个信号改 SIG_IGN 后投递 quit 事件, 与托盘菜单「退出」走同一条停止编排)与 `_install_sigterm_quit`(注册失败静默, 与 cli 同口径); `run()` 开头换装 + mainloop 收尾移入 `finally`(异常路径也收尾 —— pystray run_detached 线程非 daemon, 异常跳过收尾会把进程退出挂在 threading._shutdown); 模块 docstring 线程模型补信号一行。
- `src/auto_qb/cli.py`: `_install_sigterm_handler` docstring 与 main() 注释如实化(「所有模式一致」改为非托盘经 KeyboardInterrupt / 托盘由 TrayUi 换装交接, 本 handler 只覆盖托盘启动早期窗口)。
- `tests/test_tray.py`: 新增 4 条(SIGTERM handler 本体 / 注册失败静默 / run 正常退出编排含换装断言 / run 异常路径收尾) —— 红绿双验: raise 突变(测试进程被 KeyboardInterrupt 打断)与 finally 退化突变(`except BaseException: raise`, stop_event 未置位)双双命中后精确还原; 头部测试计划同步。
- `tests/test_ui.py`: `test_run_join_timeout_warns` 补 SIGTERM 处置进出恢复(run() 现会换装 handler, 进程全局态不外泄)。
- 用例增量: 本件新增 4 条, 其余来自会话开工同步的远端提交(8 笔)。

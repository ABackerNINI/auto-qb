# 26-11-01-backend-tray-sigterm-quit — 托盘模式 SIGTERM 优雅退出: handler 换装 quit 事件合流 + run() 收尾挂 finally 兜底(issue 26-10-31-1030)

**Status:** Done
**Added:** 2026-11-01
**Updated:** 2026-11-01
**Summary:** 托盘 SIGTERM 优雅退出落地: handler 换装 quit 事件与托盘菜单「退出」合流 + run() 收尾挂 finally 兜底(异常路径不丢收尾); 根因修正 —— 不是「Tk 吞 KeyboardInterrupt」, 是异常跳过 TrayUi.run 收尾 + pystray 非 daemon 线程把进程退出挂在 threading._shutdown; 红绿双验 + 真机 3 连 + 全量绿(数字见 kb.baseline); issue 26-10-31-1030 置 Done
**Topics:** backend-tray-sigterm-quit
**Refs:** memory-bank/issues/26-10-31-1030-bug-tray-sigterm-ignored.html, memory-bank/testing/baselines/26-11-01-0119-tray-sigterm-quit.md, memory-bank/pitfalls/backend/tray-sigterm-teardown.md

## 原始请求

1. 「认领并修复26-10-31-1030-bug-tray-sigterm-ignored.html」 —— 用户显式指派认领该 issue(合法认领)并实施修复。

## 思考过程与决策

- **复验修正了根因认知**: issue 推测「KeyboardInterrupt 被 Tk 回调层(report_callback_exception)吞掉」不成立。复验日志在 SIGTERM 后已见 `Shutting down...`(cli.py 的 KeyboardInterrupt 捕获点); 纯 tkinter 最小实验(withdraw 窗口 + after 链 + 定时 raise_signal)亦证 after 回调里的 KeyboardInterrupt 能从 mainloop 传播出来。真断点: 异常把 `TrayUi.run()` 里 mainloop 之后的收尾编排(停托盘/停 manager/清 IPC)整段跳过, 而进程退出挂在 pystray `run_detached` 非 daemon 线程(`pystray/_win32.py:130`, `threading.Thread(target=...)` 无 daemon 参数)上 —— 解释器收尾在 threading._shutdown 无限等待, daemon 的 manager 线程还在继续重试连接(复验日志可见)。
- **D1 修法拍板(双保险, 修一案兼收官)**: ①SIGTERM 在托盘模式换装为「投递 quit 事件」—— 与托盘菜单「退出」走完全同一条停止编排(quit 事件 -> _poll -> root.quit -> mainloop 返回 -> 收尾), 即 issue 建议方向 a/b 的合流; handler 在主线程字节码边界执行、只向事件队列投递意图, 不碰共享状态(并发坑档「信号处理器是违规写点」的合规形态)。②`run()` 收尾移入 `finally` —— 任何异常路径(Ctrl+C 形态的 KeyboardInterrupt 等)都保证收尾后照常上抛, 交 cli 统一捕获; 这条关的是「异常跳过收尾」这一类, 不是只有 SIGTERM 一案。
- **D2 SIG_IGN 语义保留**: 首个信号后改 SIG_IGN, 收尾期间再到的 SIGTERM 不打断收尾(与 cli 版 `_sigterm_to_keyboardinterrupt` 同口径)。
- **残余窗口(记录, 不工程化)**: `_build_tray` 启动 pystray 线程到 `run()` 换装之间的微秒级窗口内, SIGTERM 仍走 KeyboardInterrupt 版 handler 且收尾编排尚未建立 —— 常驻期(实际语义面)已全闭, 启动头几百毫秒的窗口代价大于收益, 留注释说明。
- **真机回归的环境适配**: RM02 官方用例 conftest 要求 qB 实例在线, 本轮 36595/36596 均未运行; issue 证据已声明「qB 进程无关」, 故复验与回归走 `tests-real/lib/app.py` 跑壳的独立脚本(配置指向 36596 且其不在线, 与 RM02-06 的 dead-port 等价), stderr 落盘取证。

## 实现计划

总体思路: 让 SIGTERM 与托盘真实停止路径合流(handler 不再 raise), 并把「收尾」从顺序代码变成 finally 义务; 守阵钉两条行为(handler 只投递 / 收尾不可跳过)。

1. `src/auto_qb/tray/app.py`: 新增 `_sigterm_to_quit`(SIG_IGN + 投递 quit 事件)与 `_install_sigterm_quit`(注册失败静默, 与 cli 同口径); `run()` 开头换装, mainloop + 收尾改 try/finally; 模块 docstring 线程模型补信号一行。
2. `src/auto_qb/cli.py`: `_install_sigterm_handler` docstring 与 main() 内「所有模式一致」注释如实化(非托盘经 KeyboardInterrupt / 托盘由 TrayUi 换装交接, 本 handler 只覆盖托盘启动早期窗口)。
3. `tests/test_tray.py`: 新增 4 条守阵(handler 本体 / 注册失败静默 / run 正常退出编排含换装断言 / run 异常路径收尾), 替身打桩沿 `test_ui.py` 的 run 先例; 头部测试计划同步。
4. `tests/test_ui.py`: 既有 `test_run_join_timeout_warns` 补 SIGTERM 处置进出恢复(run() 现会改进程全局 handler)。
5. 红绿双验两轮: raise 突变、finally 退化突变(`except BaseException: raise`)各命中对应守阵后精确还原。
6. 真机回归: graceful 跑壳 SIGTERM@25s × 3 连(判据: 退出 rc=0 / 无「10s 退出预算」WARNING / ui.port 清理 / stderr 无堆栈)。
7. `test.full` 全量 + 新基线切片; issue 翻 Done 留修法/验证; 主题文档回写(real-machine.md 托盘行)与 RM02-06 docstring 过期句修正; 新坑入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验锚点: 独立复验脚本(graceful 跑壳 SIGTERM@25s, 观测 70s + stderr 取证) | Done(2026-11-01) |
| 2 | 认领: 置 In Progress + 复验行留痕 + kb.index | Done(2026-11-01) |
| 3 | 修法实施: tray/app.py 换装 + finally 收尾; cli.py 注释如实化 | Done(2026-11-01) |
| 4 | headless 守阵 4 条(test_tray) + 既有 run 用例恢复补丁(test_ui) | Done(2026-11-01) |
| 5 | 红绿双验: raise 突变 + finally 退化突变双双命中后精确还原 | Done(2026-11-01) |
| 6 | 真机回归: SIGTERM@25s × 3 全过(退出 rc=0/收尾干净/无堆栈) | Done(2026-11-01) |
| 7 | test.full 全量绿 + 基线切片 26-11-01-0119 | Done(2026-11-01) |
| 8 | issue 翻 Done + 修复留痕; real-machine.md / RM02-06 docstring 回写; 新坑 tray-sigterm-teardown 入库 | Done(2026-11-01) |

## 进度日志

### R0 · 立档 (2026-11-01)

- 开工同步: 远端领先 8 笔快进(60044d07→c32a0bdc)。
- 复验: 仍复现; 根因认知修正(见「思考过程与决策」首条), issue 状态日志已留复验行。
- 实施与验证全程在本轮完成: 修法两处(4 源文件) → 红绿双验 → 真机 3 连 → 全量绿。
- 实测数字单点在基线切片(见 Refs), 本档案不手抄。

- 2026-11-01 01:24 认领并修复 issue 26-10-31-1030: 托盘 SIGTERM handler 换装投递 quit 事件与托盘菜单「退出」合流 + run() 收尾挂 finally 兜底; 根因修正(异常跳过收尾+pystray 非 daemon 线程挂死 threading._shutdown, 非「Tk 吞 KeyboardInterrupt」); 红绿双验两突变命中 + 真机 3 连全过 + 全量绿(数字见 kb.baseline 26-11-01-0119); issue 置 Done; 坑档 backend/tray-sigterm-teardown 入库; real-machine.md/RM02-06 docstring 回写

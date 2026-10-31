# GUI mainloop 里 raise 版信号 handler + 非 daemon 第三方线程: 异常跳过收尾且进程退出挂死

> 摘要: 主线程阻塞在 GUI mainloop 时, 「raise KeyboardInterrupt」版信号 handler 的异常会跳过 mainloop 之后的收尾编排; 只要进程里还有非 daemon 线程(如 pystray run_detached), 进程退出就挂在 threading._shutdown 永不完成
> 触发: 信号 handler, SIGTERM, KeyboardInterrupt, 托盘, mainloop, Tk, pystray, 非 daemon 线程, threading._shutdown, 进程不退出, 收尾被跳过, 退出挂死
**Refs:** memory-bank/tasks/26-11-01-backend-tray-sigterm-quit.md

### 托盘模式 SIGTERM「handler 不生效」的真断点是收尾被异常跳过, 不是异常被吞

- **触发**: 给「主线程阻塞在 GUI mainloop(Tk/pystray 等) + 内部有非 daemon 后台线程」的进程装「信号 -> raise KeyboardInterrupt」式 handler(issue 26-10-31-1030 实证: `--tray` + graceful 跑壳, 3/3 观测 70s+ 不退)。
- **判别**: 三连症状缺一不可 —— ①退出日志/收尾断言打出来了(异常**没有被吞**, `report_callback_exception` 也不拦 after 回调里的 KeyboardInterrupt, 纯 tkinter 最小实验可证传播); ②mainloop 之后的清理代码一行没跑(托盘没停/锁文件残留/状态没落盘); ③进程活着但 daemon 线程还在打日志 —— 主线程卡在 `threading._shutdown` 等**非 daemon**线程(pystray `_win32.py` 的 `threading.Thread(target=...)` 不带 daemon 参数)。「疑似被 Tk 吞」是错的: 吞不吞看 `_tkinter` 的 errorInCmd 机制, 本案根本没走到那。
- **处置**: 两条都要做 —— ①**GUI 模式下信号 handler 不 raise**: 换装为「向主线程事件队列投递退出意图」(托盘即投递 quit 事件, 与托盘菜单「退出」同一条停止编排; handler 主线程执行、只投递意图, 单一写线程纪律不破), 首个信号后 SIG_IGN 防收尾被打断; ②**mainloop 之后的收尾挂 `finally`**: 任何异常路径(Ctrl+C 等)都保证收尾后照常上抛交统一捕获点。别只做②: 异常从 Tk 回调栈冒出的落点不可控, ①才是把信号语义收进单一停止路径的正解。
- **守阵**: `tests/test_tray.py` 4 条(handler 本体只投递 / 注册失败静默 / run 正常退出编排含换装断言 / run 异常路径收尾, 红绿双验过 raise 突变与 finally 退化突变)。

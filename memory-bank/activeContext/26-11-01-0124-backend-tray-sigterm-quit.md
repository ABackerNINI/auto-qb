# backend-tray-sigterm-quit

> 摘要: 认领并修复 issue 26-10-31-1030: 托盘 SIGTERM handler 换装投递 quit 事件与托盘菜单「退出」合流 + run() 收尾挂 finally 兜底; 根因修正(异常跳过收尾+pystray 非 daemon 线程挂死 threading._shutdown, 非「Tk 吞 KeyboardInterrupt」); 红绿双验两突变命中 + 真机 3 连全过 + 全量绿(数字见 kb.baseline 26-11-01-0119); issue 置 Done; 坑档 backend/tray-sigterm-teardown 入库; real-machine.md/RM02-06 docstring 回写
> 最后活动: 2026-11-01 01:24
**Refs:** memory-bank/tasks/26-11-01-backend-tray-sigterm-quit.md

**R0(2026-11-01 01:24):** 认领并修复 issue 26-10-31-1030: 托盘 SIGTERM handler 换装投递 quit 事件与托盘菜单「退出」合流 + run() 收尾挂 finally 兜底; 根因修正(异常跳过收尾+pystray 非 daemon 线程挂死 threading._shutdown, 非「Tk 吞 KeyboardInterrupt」); 红绿双验两突变命中 + 真机 3 连全过 + 全量绿(数字见 kb.baseline 26-11-01-0119); issue 置 Done; 坑档 backend/tray-sigterm-teardown 入库; real-machine.md/RM02-06 docstring 回写

# 后台 dev.run 实例外部优雅停机三路全堵(Windows)

> 摘要: 经 `commands run dev.run` 后台(run_in_background)起的 auto-qb 实例, agent 从外部**没有优雅停机路径**: ①CTRL_C_EVENT 广播无效(后台任务链整树继承「忽略 Ctrl+C」旗标); ②组定向 CTRL_C 无效(产品非进程组长, 新组默认禁 CTRL_C); ③CTRL_BREAK 广播可达但默认致命(CPython 对 SIGBREAK 无 handler → 0xC000013A 控制台级硬终止, SIGTERM→KeyboardInterrupt 优雅路径不经过); Windows os.kill(SIGTERM)=TerminateProcess 同样不通。只能硬停(丢 ≤state_save_interval 状态窗口)或前台控制台 Ctrl+C。
> 触发: dev.run, 后台实例, 优雅停机, CTRL_C_EVENT, CTRL_BREAK, 0xC000013A, GenerateConsoleCtrlEvent, SIGTERM, os.kill, 停机, 硬停, run_in_background, TaskStop
**Refs:** memory-bank/tasks/26-11-11-webui-group-hash-ref.md (R1 坑4, 2026-11-11)

- **触发**: agent 经 `commands run dev.run` 挂后台起真机实例, 验证/测量完要从外部停它, 想走产品自己的优雅退出(SIGTERM→KeyboardInterrupt→落盘)。
- **判别/实测三路(Windows, 各自为什么堵)**: ①`CTRL_C_EVENT` 广播无效 —— 后台任务链(cmd→uv→python)整树继承「忽略 Ctrl+C」旗标(SetConsoleCtrlHandler(NULL,TRUE) 可继承, 只豁免 CTRL_C); ②组定向 CTRL_C(`GenerateConsoleCtrlEvent(0, pid)`)无效 —— 产品非进程组长, 新组 CREATE_NEW_PROCESS_GROUP 默认禁 CTRL_C 同样绕不开; ③`CTRL_BREAK` 广播**可达但默认致命** —— CPython 对 SIGBREAK 无 handler → 0xC000013A 控制台级终止, 产品的优雅路径根本不经过; Windows `os.kill(SIGTERM)`=TerminateProcess 同样不通。实测两次均硬停。
- **处置**: 经 dev.run 后台起的实例, agent 外部只能控制台事件硬停(丢失 ≤120s state 窗口 = state_save_interval 上限量级; 测试态可弃; 锁由 OS 自动释放); 要优雅停机: **前台控制台直接 Ctrl+C**, 或将来在 cli 装 SIGBREAK handler / webui 停机端点(产品面改动, 另行立项)。清场收尾用 `dev.port-kill` 定点(杀前核监听进程归属, 非 python 监听者须显式 --yes)。
- **关联**: testing/bg-process-cleanup.md(TaskStop 只杀外层包装, python 子进程持锁/端口存活的另一面); ops/taskkill-image-name-ban.md(taskkill 一律禁止, 定点杀只走 dev.port-kill); ops/port-kill-prod-instance.md(杀前核归属)。

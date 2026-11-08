# xdist-js-bundle-temp-race

> 摘要: 认领并修复 issue 26-11-08-1955(xdist bundle 竞态, 已翻 Done): 三处临时聚合脚本落点统一掺 os.getpid()(bundle_file / background_bundle / head 探针), 加两条行为守阵 test_bundle_file_is_process_private / test_background_bundle_is_process_private(head 探针在用例内联断言); 根因经 WSL Linux 复现证实(共享路径 1600+ 次坏读 -> 进程隔离 0 次); 坑档 parallel-run 新增该条; 全量数字见 kb.baseline; 顺带同步远端 SyntaxWarning 修复(2543a603)并复验零命中
> 最后活动: 2026-11-09 05:00

**R0(2026-11-08 19:58):** 按用户指派入池 xdist bundle 竞态: memory-bank/issues/26-11-08-1955-test-xdist-js-bundle-temp-race.html(test/standard, Open 未修); 证据为两次 ship.commit 闸门假红(PermissionError 与 node 电池挂) + 单跑与合流树全绿对照; 根因留待查(共享实例临时根 + 固定文件名的推断, 已排除本批改动与远端合流回归); 三条候选修法与 flaky 台账归因提示; 本轮零代码改动, 随本专题入库

**R1(2026-11-09 05:00):** 认领并修复 issue 26-11-08-1955: bundle_file 落点按 pid 隔离(各 worker 只读写自己的聚合脚本), 新增守阵 test_bundle_file_is_process_private 并红绿双验; Linux 侧 WSL 复现竞态(共享路径 1600+ 次坏读 -> 进程隔离 0 次); 坑档 parallel-run 新增该条; 全量数字见 kb.baseline; issue 翻 Done; 顺带同步远端 SyntaxWarning 修复(2543a603)并复验全树零命中

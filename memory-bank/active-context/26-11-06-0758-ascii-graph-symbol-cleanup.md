# ascii-graph-symbol-cleanup

> 摘要: 非 ASCII 图形符号专题: 全库只读扫描后用户拍板「先入池等排期」-> 判据定案为码位三表(表 A 禁用 / 表 B 豁免 / 表 C ASCII 参考) + 机械闸门 -> 13 批存量清偿至归零, 守阵 13 条, 闸门现为纯只拦新增; 收口档案 memory-bank/tasks/26-11-09-docs-ascii-symbol-cleanup.md, 批次明细见计划 §04
> 最后活动: 2026-11-09 21:42

**R0(2026-11-06 07:58):** 用户指派修同类存量 -> 全库只读扫描命中 395 文件/2358 行禁用图形符号(剔除功能性数据/夹具镜像/历史快照/第三方设计骨架后, 项目自身候选池 300 文件/1868 行) -> 用户拍板一次修太多先入池等排期 -> 新建 issue 26-11-06-0756-refactor-ascii-graph-symbol-backlog 留 Open 未认领, 零代码改动

**R1(2026-11-06 08:01):** 收尾验证: kb.check 全项通过; test.quick 唯一红为 tests/test_free_port.py::test_hold_run_discards_run_whose_offset_is_refused(既有端口环境 flake, flaky-ledger 有同族记录), 本轮零代码改动且串行单跑转绿、文档守阵全绿; 按范围守恒未修未入池

**R2(2026-11-09 21:42):** 收尾 DoD 回写: 存量清偿完成 + 守阵 13 条 + FROZEN 归零; 补 2 条坑档(闸门并发假红 / 单文件 -n 8 挂死) + 单文件覆盖率坑复发计数, 补建收尾档案

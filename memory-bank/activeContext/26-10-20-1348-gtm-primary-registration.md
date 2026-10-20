# gtm-primary-registration

> 摘要: 新建 plan 26-10-20-1316《gtm 正主注册与让位代拉设计》: 三处 ID + 启动判定矩阵 + ④让位代拉 + claim 人工易主通道 + deferred.json 状态注记; auto-qb 零记录读写
> 最后活动: 2026-10-20 16:15

**R0(2026-10-20 13:48):** 新建 plan 26-10-20-1316《gtm 正主注册与让位代拉设计》: 三处 ID + 启动判定矩阵 + ④让位代拉 + claim 人工易主通道 + deferred.json 状态注记; auto-qb 零记录读写

**R1(2026-10-20 15:56):** P1-P4 实施完成: identity 模块+启动矩阵插桩+测试(303), claim 子命令+双启动器, auto-qb 侧编排/路由/设置页(根 3790), 文档; e2e 真进程复算通过(代拉同一 dat + claim 两态护栏)

**R2(2026-10-20 16:15):** hermetic 收口: identity/storage 各持一份 pointer_dir 引用, 单边 patch 对身份层无效 —— P1 cmd_run 身份门使缺口显形 (primary.json/deferred.json 落真实指针目录)。修 test_server 单例锁用例同址补 patch + test_identity write_deferred 移至 patch 之后; 新增 tests/conftest.py autouse 守阵 (每用例前后真实目录快照比对, 落文件即红; instance.lock 独占读记 <unreadable> 不误报)。工具侧 303 全绿且真实目录零改动, 根 3790 passed (cov 97.65% 存量)

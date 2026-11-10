# relocate-probe-async

> 摘要: 认领 issue 26-11-10-0638(relocate run_probe 三段 time.sleep 同步阻塞主循环, FS 不可达单次 ~25s+)并 grilling 三轮拍板 D1-D10 全按推荐: 案B daemon 线程跑 run_probe 本体零改动 + 意图重放自动续跑 + state pending(relocate.probe_pending)重启可续 + 全局单飞 FIFO 等位(同指纹合并去重, 整组移动零退化/跨组自动排队) + web 两段回执 + on_task_line 先消费后步进每 tick ≤1 条含 env=True 防自环; 计划 26-11-10-2350 入库(Open, S1-S6 等显式开工, issue 认领链双向已补、状态仍 Open); 评审两轮: 轮1 5 发现(1 major 共享 qB client 并发面漏记→§07 增行+独立 client 处置+隔离断言, 4 minor 计数/漂移/先例/撞号)检 5 过 5 全修, 轮2 零 actionable; 零代码改动
> 最后活动: 2026-11-11 00:49

**R0(2026-11-11 00:49):** 认领 issue 26-11-10-0638(relocate run_probe 三段 time.sleep 同步阻塞主循环, FS 不可达单次 ~25s+)并 grilling 三轮拍板 D1-D10 全按推荐: 案B daemon 线程跑 run_probe 本体零改动 + 意图重放自动续跑 + state pending(relocate.probe_pending)重启可续 + 全局单飞 FIFO 等位(同指纹合并去重, 整组移动零退化/跨组自动排队) + web 两段回执 + on_task_line 先消费后步进每 tick ≤1 条含 env=True 防自环; 计划 26-11-10-2350 入库(Open, S1-S6 等显式开工, issue 认领链双向已补、状态仍 Open); 评审两轮: 轮1 5 发现(1 major 共享 qB client 并发面漏记→§07 增行+独立 client 处置+隔离断言, 4 minor 计数/漂移/先例/撞号)检 5 过 5 全修, 轮2 零 actionable; 零代码改动

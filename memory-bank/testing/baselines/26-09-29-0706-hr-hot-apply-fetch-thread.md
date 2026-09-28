# 1741 passed / 3 skipped —— HR 站点接入热重载「取数线程未启动」修复

> 摘要: 修复 HR 在线核实站点接入热重载后取数线程永不启动(用户实报)。两缺陷叠加:
> ①`apply_new_config` 只在 L1 分支调 `hr.apply`, 而站点接入(`hr_check.sites` / `trackers.X.hr_check`)
> 是 L0 —— 热重载只换 config 对象, HR 运行时收不到; ②`HrRuntime.apply` 的 L0 重建路径
> `running = worker is not None` —— 启动时无站点则 worker 从未建过, 热接入也不补启动。
> 修复: apply 移出 L1 分支每次热重载都调; apply 内加「无变化短路」; enabled 时必补启动。
> 附带反转旧守阵 `test_apply_l0_rebuilds_service_without_worker_running`(钉的是反语义)。
> 基线时间: 2026-09-29 (develop @ 7351acf5, 本次改动未提交)
> 档案: tasks/26-09-29-backend-hr-hot-apply.md

- test.full: **1741 passed / 3 skipped**, TOTAL **90%**(12,299 语句 / 1,004 未覆盖 / 4,170 分支 /
  407 partial), 耗时 ~23s。较上一基线(26-09-29-0550, 1739/3): +2 passed —— HR runtime 反转
  1 例改名 + 新增 2 例(短路不重启 / 运行中热接入新站点), test_web 加 1 条 L0 路由守阵断言。
- test.quick 同数字全绿(提交闸门口径)。
- 未提交(等用户显式指令)。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。

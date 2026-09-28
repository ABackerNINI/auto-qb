# 26-09-29-backend-hr-hot-apply — HR 站点接入热重载「取数线程未启动」修复

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29
**Summary:** HR 在线核实站点接入热重载后取数线程永不启动(两缺陷: hr.apply 只挂 L1 分支而站点接入是 L0; HrRuntime.apply 的 running 守卫挡住「从无到有」)。修复: apply 每次热重载都调 + 内部无变化短路 + enabled 必补启动; 反转钉反语义的旧守阵。test.full 1741 passed / 3 skipped (90%)。

## 原始请求

用户实报: 「HR在线核实站点接入热启动后"取数线程未启动"」——热重载接入 HR 站点后, `/api/hr/status` 显示取数线程未启动, 站点数据不刷新。

## 思考过程与决策

- 提示语单点在 `webui/server/routes/hr.py:65`: `conf.enabled` 为真但 `runtime.service is None` 时返回「取数线程未启动」⇒ 服务对象根本没建出来, 不是线程死了。
- **缺陷 1(调用点漏挂)**: `QbManager.apply_new_config` 只在 L1 分支调 `self.hr.apply(old_hr_check)`; 而站点接入(`hr_check.sites` / `trackers.X.hr_check`)在 `config/impact.py` 是 **L0** ⇒ 热重载只替换 config 对象, HR 运行时收不到任何通知。
- **缺陷 2(从无到有被挡)**: `HrRuntime.apply` L0 重建路径 `running = self.worker is not None`, 只在「原来就在跑」时才重启线程。启动时无站点 ⇒ `start()` 直接返回、worker 从未建过 ⇒ 热接入第一个站点永远起不来。
- **附带发现**: 已运行实例热接入第二个站点也不生效 —— `HrRefreshService.__init__` 把站点表 `dict(site_confs)` **按值拷贝**, 不重建看不到新站点。impact.py 注释声称「取数线程每轮现读」与实现相反。
- **决策**: 挂载口(`hr.apply`)改为**每次热重载都调**(不限 L1), 由它自判重建/短路 —— 调用方做级别裁剪就是漏调的温床; 无变化短路保证无关配置保存不重启取数线程; L0 路径收敛「enabled ⇒ 在跑」。旧守阵 `test_apply_l0_rebuilds_service_without_worker_running` 钉的正是反语义(「未启动时 apply 不得拉起线程」), 是本 bug 成因之一, 随修复反转。

## 实现计划

1. `core/qbmanager.py`: `self.hr.apply(old_hr_check)` 移出 L1 分支(每次热重载都调) + docstring 更新。
2. `hr/runtime.py` `apply()`: 加无变化短路(服务在 && 全局段/派生站点表与新配置相等 ⇒ return); L0 重建路径 worker 不在也 `start()`。
3. `config/impact.py`: 回写 `HR_CHECK_FIELD_LEVELS` 上方机制注释(按值持有 + 挂载口每次都调)。
4. 测试: 反转旧守阵并改名 + 新增「无变化短路」「运行中热接入新站点」两例; `test_web.py` 加 L0 下 `hr.apply` 必被调的路由守阵。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 定位根因(两缺陷叠加) | Done | 2026-09-29 本轮 |
| 修复 qbmanager 调用点 + HrRuntime.apply | Done | 无变化短路 + enabled 必启动 |
| impact.py 机制注释回写 | Done | 原注释与实现相反 |
| 测试反转 + 新增守阵 | Done | 反转 1 例 + 新增 2 例 + web 路由守阵 |
| 收尾回写(基线/坑档/切片/索引) | Done | 基线 26-09-29-0706; 坑档 pitfalls/backend/hot-reload-held-config.md |

## 进度日志

- **2026-09-29**: 实报定位 → 修复 → 测试全绿(test.full 1741 passed / 3 skipped, TOTAL 90%, ~23s; test.quick 同数字) → 收尾回写 → 随「提交」入库。

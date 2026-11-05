# 5343 passed, 10 skipped, 1 warning in 156.69s; coverage 99.63% —— HR 取数侧强制 fetchable(issue 26-10-05-0922 清偿)后全量基线

> 摘要: HR 取数侧强制 fetchable(issue 26-10-05-0922 清偿)后全量基线
> 基线时间: 2026-11-05 08:34
**Refs:** memory-bank/tasks/26-11-05-backend-hr-fetch-gating.md

## 验收数字

- `commands run test.full`: **5343 passed, 10 skipped, 1 warning in 156.69s**
- 覆盖率: **99.63%**(TOTAL 24475 statements, 74 miss / 8396 branch, 40 partial)—— 过 99.5% 闸
- 口径注记: 全量含本轮新增 2 条取数侧过滤回归(test_hr_service_misc / test_hr_worker_lifecycle); 中途一轮 2 个 memory_bank_structure 守卫失败为索引过期(issue HTML 改动晚于 kb.index), 重建索引后全绿, 与代码无关。

## 本改动面

- `src/auto_qb/hr/service.py`: 新增 `fetchable_sites()`(取数集合单点: enabled 且 listing=="list"); `refresh_all` 改用它。
- `src/auto_qb/hr/worker.py`: `run_once` 取数循环 / `request_refresh` 受理集合改按 fetchable; 通道静默「受影响站点」改 fetchable_sites(评审 minor ②)。
- `src/auto_qb/hr/runtime.py`: `request_refresh` 汇合点 note 在 requested 空时如实说明, 消除 WebUI 409 detail 自相矛盾(评审 minor ③)。
- `src/auto_qb/hr/report.py`: 走查头部改取数口径计数 + 全站型-only 时如实退出(评审 minor ①)。
- `src/auto_qb/config/models.py`: `fetchable` property docstring 补消费方单点指向(无行为变更)。
- `tests/hr_runtime_support.py`: 假配置补 `listing="list"` 贴近生产派生形态(空 listing = 未绑定不取数)。
- `tests/test_hr_service_misc.py` / `tests/test_hr_worker_lifecycle.py`: 各 +1 取数侧过滤回归。
- `memory-bank/issues/26-10-05-0922-refactor-hr-fetchable-dead-config.html`: Open→Done + 复验行 + 状态日志(修法/验证)。

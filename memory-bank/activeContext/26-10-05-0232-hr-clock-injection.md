# HR 时钟注入收编 — issue 26-10-02-0526 认领完成 (Done)

> 摘要: 认领 issue 26-10-02-0526 (hr/service.py 构造器注入 now_fn, 但 `_note_dl_fail` 与
> `_advance_observation` 直调 time.time() 绕过注入 —— 假时钟下冷却记账 `fail.last_ts` 与观察期放行
> `verified_ts` 不可控)。复验(基线 4f9f1f09): 直调点两处, 行号漂移 :956→:1013 / :1152→:1268;
> :344 `now_fn=time.time` 为注入默认值不收编。实际修法: 按 `_merge_seen` 同款收编 —— 两个
> staticmethod 增 `now: float` 参数, 调用方传 `self._now()`(下载失败记账点各取当下; 观察期复用
> `_finish_wave` 已算的 now, 放行 `verified_ts` 与波次收尾时刻对齐), 生产行为不变。
> 守阵: `test_download_invalid_blob_counted_as_fail` 钉 `fail.last_ts ==` 注入时钟 +
> `test_freeze_and_observation_guards` 新增带身份出口子例钉 `verified_ts ==` 注入 now, 测试计划同步 1 处。
> 红验: 探针临时改回墙钟, 两条新断言全红(1791138444.x ≠ 1700000000.0 / 1234.5), 恢复后绿。
> test.full 2540 passed + 4 skipped / 99% / 36.39s+27.69s (基线
> [26-10-05-0232](../testing/baselines/26-10-05-0232-hr-clock-injection.md))。不满足立档阈值, 无任务档案。
> 最后活动: 2026-10-05 02:32

**Refs:** memory-bank/issues/26-10-02-0526-refactor-hr-service-clock-injection-inconsistent.html, memory-bank/testing/baselines/26-10-05-0232-hr-clock-injection.md

## 现状

- issue Done: hr/service.py 时钟获取全量统一走 now_fn 注入, 全文件直调 time.time() 仅剩 :344 注入默认值。
- 改动未提交: src/auto_qb/hr/service.py / tests/test_hr_service.py / issue HTML / 基线切片 / 本切片, 等用户显式提交指令。

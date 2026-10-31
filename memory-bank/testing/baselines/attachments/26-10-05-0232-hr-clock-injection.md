# 基线切片 26-10-05-0232 — HR 时钟注入收编 (issue 26-10-02-0526 认领)

> 摘要: 认领 issue 26-10-02-0526 (hr/service.py 直调 time.time() 绕过 now_fn 注入, 假时钟测试不可控)。
> 复验仍复现: 直调点两处(:1013 `_note_dl_fail` 的 `fail.last_ts` / :1268 `_advance_observation` 的 `now =`)。
> 按 `_merge_seen` 同款收编: staticmethod 增 `now` 参数, 调用方传 `self._now()`; 生产行为不变。
> 基线时间: 2026-10-05 02:32

**Refs:** memory-bank/issues/26-10-02-0526-refactor-hr-service-clock-injection-inconsistent.html, memory-bank/activeContext/26-10-05-0232-hr-clock-injection.md

- 分支: develop @ 4f9f1f09 (+ 本轮未提交改动: src/auto_qb/hr/service.py / tests/test_hr_service.py / issue HTML / 本切片)
- 命令: `commands run test.full`(Windows, 两次采样)
- **实测 (Windows)**: **2540 passed + 4 skipped, 36.39s / 27.69s, 覆盖率 TOTAL 99%**
  (14870 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标, total 98.63%)
- 靶向 (tests/test_hr_service.py): 84 passed。红验: 探针把两处临时改回墙钟直调,
  两条新钉断言全红(`fail.last_ts` 1791138444.x ≠ 1700000000.0 / 出口 `verified_ts` 1791138444.x ≠ 1234.5),
  其余 82 绿; 恢复后整文件 84 passed。
- 相对上基线 (26-10-05-0209: 2540 passed + 4 skipped / 99% / 27.60s+27.52s): passed 持平
  (本轮只扩展 2 条既有用例不加数); 语句 14871→14870 = 摘除 `now = time.time()` 一句。
  过程插曲: issue 置 In Progress 后、`kb.index` 重建前采过两轮(1 failed = `test_gen_all_check_is_green`
  报 issues/_index.md 漂移, 属预期守卫行为), 重建后两轮全绿, 非代码问题。
- 改动面: src/auto_qb/hr/service.py(两处直调收编) + tests/test_hr_service.py(扩展 2 条 +
  测试计划同步 1 处) + issue HTML / 基线切片 / activeContext 切片。

# 5457 passed + 10 skipped in 126.9s (TOTAL 24538 stmts, 99% cover, 41 miss) —— ui_harness relocate 注入轮全量基线

> 摘要: ui_harness relocate 注入轮全量基线
> 基线时间: 2026-11-06 05:11
**Refs:**

## 验收数字

- 汇总行: **5457 passed + 10 skipped** in 126.9s(TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 41 miss / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 相对上基线(26-11-06-0427, 5462 passed + 2 skipped)passed −5 / skipped +8(collected 5464 → 5467, 本轮未增删 pytest 用例, 改动仅在 dev-only 桩脚本; 差额来自会话中途同步入的远端提交, 归因未逐笔核对); 全绿。本切片数字取收口评审修复(len<4 守卫)后的提交时刻实测。
- e2e 面(同轮实测, 数字仅此处存证): `npx playwright test e2e/views.spec.mjs` **36 passed**(双皮肤, 含原恒红的「种子页筛选器有数据」); 全量 e2e `commands run dev.e2e` **430 passed / 2 failed / 18 skipped**(2 failed = gtm-alert 双皮肤, stash 对照 HEAD 同红, 存量失败与本轮无关, 已另行报告)。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- `scripts/ui_harness.py`: 新增 `_inject_relocate_jobs` + `_FakeRelocateJobs` 模块句柄最小替身 —— 桩补灌 relocate job 快照(4 job 覆盖 moving/armed/failed/done 四筛选桶, 前两个落同一组对出组级跨状态多 job 聚合: state 取最高优先级=moving, pending=2/total=2), `config.relocate.enabled=True` + `ctx.relocate` 挂替身; 修复 issue 26-11-06-0330(views.spec「种子页筛选器有数据」因 relocate kind 恒空双皮肤恒红)。
- `memory-bank/issues/26-11-06-0330-test-e2e-views-relocate-kind-empty.html`: 复验行 + 根因 + 状态 In Progress → Done。
- `memory-bank/pitfalls/testing/stubs-sim.md`: 新条目「桩的合成数据面与新功能的数据依赖不同步」(第 4 例: peers/trackers/add-options 之后)。

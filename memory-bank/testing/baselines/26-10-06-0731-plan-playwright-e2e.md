# 2676 —— 迁移计划入库前基线(纯文档轮, 零代码改动)

> 摘要: 撰写并提交方案 B 分步实施计划
> [plans/26-10-06-0708-plan-playwright-e2e.html](../../plans/26-10-06-0708-plan-playwright-e2e.html)
> (基于 issue 26-10-06-0458) 的收尾基线。本轮改动**全部为文档**(计划 HTML / issue doc-refs /
> 任务档案 / activeContext 切片 / 索引), 零 Python 改动 ⇒ 数字应与上一条
> [26-10-06-0619](26-10-06-0619-playwright-e2e-teardown-fix-merged.md) 的 2676 + 4 持平 —— 实测一致。
> 基线时间: 2026-10-06 07:31

**Refs:** memory-bank/activeContext/26-10-06-0508-playwright-e2e.md, memory-bank/tasks/26-10-06-test-playwright-e2e.md

- 分支: develop @ **0e278f12**(开工 sync 后; 工作树含本次文档改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**, 单次采样 **37.55s**(wrapper 38.5s)
  - 语句 15823 / 未覆盖 163 / 分支 5472 / partial 143。
- 相对上一条基线 [26-10-06-0619](26-10-06-0619-playwright-e2e-teardown-fix-merged.md)
  (2676 + 4 / 16021 / 166 / 5472 / 144): passed **±0**, 分支 ±0; 语句 16021 → 15823(**−198**)、
  未覆盖 166 → 163、partial 144 → 143 —— **全部来自并行会话已入库的代码提交**
  (0619 基线 @ `2be3fe79` 之后远端推进到 `0e278f12`, 含流量 v3 / 测试清理等), 与本次纯文档改动无关。
- ⚠ 耗时 37.55s 与 0619 的 75.06s 差 2×: 同为单次采样, 机器负载态不同(并行会话活跃度),
  按 baseline.md 口径单次数字不作基准; 事实锚点以 passed 数与覆盖率分布为准。
- 旁证: `commands run kb.active` 与 `kb.index` 正常; 提交闸门(`gen_doc_map.py --check` 认领链)随
  `ship.commit` 验证 —— plan ↔ issue 0458 ↔ 任务档案三向 doc-refs/Refs 已闭合。

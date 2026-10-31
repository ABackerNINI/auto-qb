# 4297 passed + 10 skipped(根) —— relocate 对账退避哨兵修复: 开机窗口内首次重建/首拉不再被 0.0 哨兵吞掉

> 摘要: relocate 对账退避哨兵修复: 开机窗口内首次重建/首拉不再被 0.0 哨兵吞掉
> 基线时间: 2026-10-31 10:03

## 验收数字

`commands run test.full`(pytest `-n 8 --cov=src --cov-branch --cov-fail-under=99`, pytest.ini addopts; 2026-10-31 实测, 单次采样 292.83s —— 本机 09:22 开机后冷态首跑, 不进区间结论):

```
  TOTAL                                                21805    163   7400    127    99%
  4297 passed, 10 skipped in 292.83s (0:04:52)
```

- 汇总行: **4297 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 163)。
- 逐条口径注记:
  - 本轮**新增 2 条 pytest 用例**(全在 `tests/test_relocate_exec.py`): 重建首建开机窗口 ×1(monotonic 钉 120.0)、guardian 首拉开机窗口 ×1(钉 30.0); 既有用例判据零改动(退避窗口内/外两条用例显式设 `rebuild_ts` / `respawn_ts`, 与 None 哨兵修法天然兼容)。
  - 树内还含 26-10-30 0706 基线之后并线的其它轮次用例(差额看 `commands run kb.baseline -n 2`), 与本次改动无关。
  - 红绿双验: 修复前探针把 `monotonic` 钉 120.0 复跑锚点, 精确复现 issue 原文签名 `('removed', '')`; 修复后同探针转绿。
  - 不新增配置键(config/schema.py 无涉); 未跑 e2e(不涉前端面)。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/core/modules/relocate_mod.py` | 重建退避(ACT_REBUILD 分支)与 guardian 重拉退避(`_respawn_guardian`)的哨兵 `or 0.0` → None 哨兵: 「从未重建/从未拉起」不吃退避(旧写法把开机后前 300s/60s 全算成退避窗口 —— monotonic 0 点是开机时刻, issue 26-10-31-0932); 退避语义与常量逐字不变 |
| `tests/test_relocate_exec.py` | 新增 2 条开机窗口守阵 + 头部「测试计划」清单同步 |
| `memory-bank/issues/26-10-31-0932-test-relocate-reconcile-flaky.html` | 复验(出窗已消失 + 探针复现)→ Done(实际修法/验证方式/测试数字) |
| `memory-bank/pitfalls/testing/monotonic-warn-sentinel.md` | 复发 +1(2026-10-31, 镜像形态) + 触发词补重启/退避入口 |

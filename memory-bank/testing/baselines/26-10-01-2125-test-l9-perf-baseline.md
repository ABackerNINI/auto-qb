# 基线 · 1916 passed + 3 skipped / 91% —— 审计 L9 清偿: 5000 种子守阵阈值基线化 + L4-L9 收尾

> 摘要: 审计 (reports/26-10-01-0918) 低严重度观察项 L4-L9 四阶段清偿的收官基线。本笔 = Phase 4
> (L9 计时断言基线化) + 收尾回写; Phase 1-3 数字见各自提交与档案
> [tasks/26-10-01-test-audit-observation-clearance.md](../../tasks/26-10-01-test-audit-observation-clearance.md)。
> 基线时间: 2026-10-01 21:25, develop @ f3564847 (工作树含 L9 改动与本次收尾回写, 未提交)。

TOTAL **1916 passed + 3 skipped / 91%**(13278 语句 / 1030 未覆盖 / 4410 分支 / 435 partial,
test.full 24.8s, **0 warnings**, rc=0)。+2 与 L9 无关(9f73b6d8 托盘 join 超时守阵进
test_ui.py); L9 本身零新增用例(改造既有守阵 test_rebuild_benchmark_5000_seeds)。
test.quick 连跑 3 次全绿(1916+3, 21.78 / 21.87 / 21.79s)—— 稳定性证据。

## L9 基线化要点 (单点: tests/fixtures/perf_baseline.json + 测试 docstring)

- **实测采样** (coverage 插桩, 与 pytest-cov 断言环境同源, 插桩使重建约慢 2x; 2 进程 × 10 轮,
  每进程第 1 轮冷, n=20/操作; 机器 Ryzen 9 7950X / Win 10.0.26300 / CPython 3.13.14 /
  commit f3564847 / 2026-10-01):
  短路 min 0.01 / 中位 0.01 / max 0.03ms; 重建 min 0.74 / 中位 0.85 / max 1.48ms。
  裸跑对照 10 样: 短路 <0.01ms; 重建中位 0.43ms。
- **阈值** = 实测中位 × 安全系数, 断言运行时从基线 JSON 读入(无手抄副本):
  短路 **0.1ms**(中位 ×5, 向上取整到 0.1ms 整刻度); 重建 **4.0ms**(中位 ×~4.7, 3-5x 带内,
  2.7x 于 20 样最大值)。旧灾难线 1s/30s 保留为第二道兜底(数字也收进 JSON)。
- **防 flaky**: 测试内 median-of-5 计时口径(单次调度/GC 毛刺被中位吸收, 持续劣化才触发);
  短路/重建均幂等(纯比较 / 全新队列+reset), 重复计时无状态漂移。
- **重采样流程**: 零脚本 —— `uv run pytest tests/test_modules_p5.py -k rebuild_benchmark
  -q -rP -n 0` 连跑 ≥6 次从 PASSES 段抓 `[5000-seed benchmark]` 行(中位数 print 在
  capsys.readouterr() 之后, 只有 -rP 能看到), 步骤与"何时重采"写进测试 docstring。
- 审计原文的「只拦灾难 / 数字入档靠人工无强制」两点均闭环: 回归阈值有数据依据;
  数字单点机器可读, 不再依赖任务档案手抄。

## L4-L9 四阶段通过数演进

1909+3 (P1, 7e48e122) → 1912+3 (P2, 036a3617) → 1914+3 (P3, 35d31469, warnings 6→0)
→ **1916+3 (P4 本笔)**; 覆盖率恒 91%, 耗时在近期全量采样区间(21-31s)内。

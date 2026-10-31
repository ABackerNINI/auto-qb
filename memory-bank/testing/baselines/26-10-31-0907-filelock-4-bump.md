# 4302 passed, 2 skipped in 243.00s —— filelock 4.2.5 bump 全量基线

> 摘要: filelock 4.2.5 bump 全量基线
> 基线时间: 2026-10-31 09:07

## 验收数字

- `commands run test.full`(2026-10-31, filelock 4.2.5 锁定后):
  - 汇总行: `4302 passed, 2 skipped in 243.00s (0:04:02)`
  - TOTAL: `21803 stmts, 145 miss, 7400 branch, 121 partial, 99%`
- 口径注记: filelock 3.32.6 → 4.2.5(major, issue 26-10-31-0830)后全量;调用面仅 `infra/locking.py` 单点,零码改道。升级后额外 smoke(本轮临时命令,非测试套件): 竞争路径 `timeout=0` 二次 acquire 抛 `Timeout` 如期、释放后重取正常。

## 本改动面

- `pyproject.toml:30`: `filelock==3.32.6` → `filelock==4.2.5`(唯一代码改动)
- `uv.lock`: filelock 条目随 `commands run env.sync` 重锁(4.2.5 wheel/sdist, 2026-10-30 上游发布)
- 无测试文件改动;静态守阵 `test_filelock_dependency_single_point_in_infra_locking` 未受影响

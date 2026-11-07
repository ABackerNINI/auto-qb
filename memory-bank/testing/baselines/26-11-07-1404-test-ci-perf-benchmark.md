# 5651 passed + 2 skipped(根) —— CI 性能基准两档阈值 + runpy 告警根因修复收尾基线

> 摘要: CI 性能基准两档阈值 + runpy 告警根因修复收尾基线
> 基线时间: 2026-11-07 14:04

## 验收数字

`commands run test.full` 实测 (2026-11-07, 命令整体 124.0s):

```text
TOTAL                                                25511      5   8802     27    99%
5651 passed, 2 skipped in 123.94s (0:02:03)
```

- 差值看上片: `commands run kb.baseline -n 2`。相对上片 26-11-07 12:48(R4 scripts 收尾基线): passed **+2**, 全部来自本批新增的 2 条参数化选档守阵, 既有 0 改写; 覆盖率 TOTAL 99%, 生产 `src/` 零改动。
- 上片记录的 `1 warning`(runpy `found in sys.modules`)在本片归零, warnings summary 洁净。
- 靶向: `tests/test_modules_p5.py` + `tests/test_recycle_daemon.py` 两文件 **79 passed**; 两档切换打印行 `limits=threshold:0.1/4.0ms` / `limits=ci_threshold:1.0/20.0ms`。
- 红绿双验三条: CI 档阈值临时压到 0.01ms → 断言真红; 选档判据改回通用 `CI` → 选档守阵 `1 failed`; 删 `delitem` → `recwarn` 守阵 `1 failed`; 全部原子复原。
- 未验证面: 本机 Docker 不可用, `test.linux` Linux 容器复现与 GitHub Actions 侧实跑未做, 以 CI 为准。

## 本改动面

- `tests/test_modules_p5.py`: 5000 种子性能基准改两档阈值(开发机严格 / CI 宽松), 抽 `_perf_limit_key()` 只认 `GITHUB_ACTIONS`, 新增 2 条参数化选档守阵, 文件头「## 测试计划」清单 +1 行; docstring 补双 OS 共用代码约束 / Linux 未实测 / 已知取舍。
- `tests/fixtures/perf_baseline.json`: 新增 `ci_threshold` 两档 + `threshold_profiles` / `ci_profile` 口径; 开发机档 0.1/4.0ms 原值不动。
- `tests/test_recycle_daemon.py`: `python -m` 入口测试执行前 `monkeypatch.delitem(sys.modules, ...)` 消除 `RuntimeWarning`, 加 `recwarn` 零告警守阵, 头部清单同步。
- `memory-bank/pitfalls/testing/timing-tolerance.md`: 「挂钟上界 + CI 抢占」复发 1→2, 补双 OS 交集判据与评审补钉指针。
- `memory-bank/pitfalls/testing/ci-env-var-profile.md`(新): 通用 `CI` 变量判档致假绿的根因、判别与处置单点。
- 建件: 会话切片 `26-11-07-1400-test-ci-perf-benchmark.md`、任务档案 `26-11-07-test-ci-perf-benchmark.md`(Status Done)、本基线切片; 各 `_index.md` 生成物随 `kb.new` / `kb.index` / `kb.status` 重建。
- 评审: `review.pack` base `f7ac0e46`; 1 只读子代理 5 发现(blocker 1 / major 1 / minor 3), `review.check` 引文 5/5, 全部当场修, 入池 0, blocker 清零。

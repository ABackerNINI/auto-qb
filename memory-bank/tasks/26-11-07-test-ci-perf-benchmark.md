# 26-11-07-test-ci-perf-benchmark — 修复 GitHub CI 性能基准挂钟假红与 runpy RuntimeWarning

**Status:** Done
**Added:** 2026-11-07
**Updated:** 2026-11-07
**Summary:** 修复 GitHub CI 性能基准挂钟假红与 runpy RuntimeWarning: 两档阈值 + 选档/warning 双守阵, 分批评审 5 发现全修
**Topics:** test-ci-perf-benchmark

## 本篇只回答

用户给的两条 GitHub CI 失败/告警怎么定性、怎么修、为什么没有改用 CPU 时间计时, 以及评审发现的假绿风险如何钉死。只记本专题的执行与验证; 计时口径判据在坑档, 阈值数字单点在 `tests/fixtures/perf_baseline.json`。

## 原始请求

1. 「修复 github ci 报错和 warnings」: ① `tests/test_modules_p5.py::test_rebuild_benchmark_5000_seeds` 在 ubuntu-latest / Python 3.13.18 上 `重建 median-of-5 8.158ms >= 回归阈值 4.0ms`; ② `RuntimeWarning: 'auto_qb.tools.recycle_daemon' found in sys.modules after import of package ...`。
2. 「收尾然后提交」: 走完 DoD(分批评审 / 切片 / 立档 / 回写 / 全量 + 基线切片 / 坑档 / 索引)并 commit+push。

## 思考过程与决策

- **定性假红**: 基线采于本机 7950X / CPython 3.13.14, 本机同口径复测 rebuild 中位 0.864ms; CI 是少核 runner + `-n 8` xdist 抢占 + coverage 插桩, 挂钟被合法调度放大近 10x, 非回归。命中既记坑档 `pitfalls/testing/timing-tolerance.md`「挂钟上界 + CI 抢占」形态(复发 1→2)。
- **不换 `time.process_time`**: 本机实测该钟最小刻度 **15.625ms**(与 `WIN_TIMER_TICK_S`=15.6ms 数值接近但不同源), 而被测操作亚毫秒级; `ci.yml` 的 ubuntu / windows 两 job 跑同一测试函数, 口径须取两 OS 交集, Windows 侧换 CPU 时间会把测量打废。Linux 侧通常纳秒级但本轮 Docker 不可用**未实测**, 不声称它也不可用; 若只跑 Linux 一侧, 改 CPU 时间是更优解。故走 `tests/platform_tolerance.py` 规范第 2 条「非用挂钟不可 → 放宽到不可撞线量级」分支。
- **两档而非统一放宽**: 开发机严格档 0.1/4.0ms 原值不动, CI 档 1.0/20.0ms 只由 `GITHUB_ACTIONS` 启用。已知取舍: 只放宽上界、未从测量层消除抢占放大, CI 侧需 ~23x 中位劣化才报; 本地严格档保留检测力, 灾难线 1s/30s 第二道兜底保留, 打印行带档位与阈值可追溯。
- **warning 修根因不屏蔽**: 文件级 import 使模块先入 `sys.modules`, `runpy.run_module` 据此告警; 用 `monkeypatch.delitem` 按 `python -m` 首次执行语义摘除(teardown 还原), 不加 `filterwarnings` 例外。实验先证: 摘除前 1 warning / 后 0, `sys.exit` 恒 0。
- **评审拍板**: 分批评审(base `f7ac0e46`, 89 行全能档 1 只读子代理) 5 条发现全部引文校验通过、全部当场修、入池 0。blocker = 通用 `CI` 变量判档会让开发机严格档永不生效(假绿), 改只认 `GITHUB_ACTIONS` 并加 2 条参数化守阵; major = 补双 OS 共用代码约束 / Linux 未实测 / 已知取舍; minor×3 = 去掉 `WIN_TIMER_TICK_S` 等号挂靠、选档守阵、warning `recwarn` 守阵。新坑 `pitfalls/testing/ci-env-var-profile.md`。

## 实现计划

1. 复现并量出本机同口径数字, 核坑档与规范 → 定性假红。
2. `perf_baseline.json` 加 `ci_threshold` 两档 + 口径/取舍说明; 测试按环境选档, docstring 同步。
3. `test_recycle_daemon.py` 摘 `sys.modules` 条目消除 warning。
4. 评审 → 修 5 条 → 加 2 条选档守阵 + `recwarn` 守阵, 同步文件头「## 测试计划」清单。
5. 红绿双验 → `test.full` → 基线切片 → 提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 定位假红 / warning 根因, 实测本机数字与计时器刻度 | Done (2026-11-07) |
| 2 | 两档阈值 + docstring / 基线 json 同步 | Done (2026-11-07) |
| 3 | runpy warning 根因修复 | Done (2026-11-07) |
| 4 | 分批评审 5 条全修 + 双守阵 + 测试计划清单 | Done (2026-11-07) |
| 5 | 红绿双验三条 + 两文件全量 | Done (2026-11-07) |
| 6 | 坑档复发 +1 / 新坑 / 索引 / 切片 / 立档 | Done (2026-11-07) |
| 7 | `test.full` 全量 + 基线切片 | Done (2026-11-07) |
| 8 | commit + push | Done (2026-11-07) |

## 进度日志

### R0 · 立档 (2026-11-07)

- 开工 `my-commit-flow.sync`: 快进 76b56fa1→f7ac0e46(远端 17 笔, 均为其它专题, 本批 4 文件无冲突); `kb.active` / `kb.baseline` 核对滚动状态。
- 靶向验证: 两文件全绿(见 `kb.baseline` 同批全量); 两档切换打印行 `limits=threshold:0.1/4.0ms` / `limits=ci_threshold:1.0/20.0ms`; `CI=true` 落严格档、`GITHUB_ACTIONS=true` 落宽松档。
- 红绿双验三条: CI 档阈值临时压到 0.01ms → 断言真红; 选档判据改回通用 `CI` → 守阵 `1 failed`; 删 `delitem` → `recwarn` 守阵 `1 failed`; 全部原子复原。
- review: base `f7ac0e46`, `review.pack` 89 行全能档; 1 只读子代理 5 发现(blocker 1 / major 1 / minor 3), `review.check` 5/5 引文通过, 全部当场修, 入池 0, blocker 清零; `review:` trailer 随提交走。
- 回写判断: 本批只动 `tests/` 与坑档, 生产 `src/` 零改动; 根 README 与 `memory-bank/conventions/` 对本批行为零命中, 不回写; 计时口径判据与环境变量判档判据各归对应坑档。
- 基线数字: 全绿(见 `kb.baseline`), 新建基线切片随本批入库; 未验证面 = Docker 不可用, Linux 容器复现(`test.linux`)与 CI 侧实跑以 GitHub Actions 为准。
- 已知存量债务(非本批引入, 转告用户另开会话清理): `kb.index` 告警 `issues/_index.md` 8192 > 8000 预算, 勿抬 cap。

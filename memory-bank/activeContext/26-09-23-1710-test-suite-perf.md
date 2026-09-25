# 全量测试耗时归因与优化
> 摘要: 全量 **75s → 默认并行 7.6s**。大头是**环境**(用户调好系统层排除项后四类文件操作全部 <1ms)不是代码; 代码侧另修三处框架开销。**已上并行**(`pytest.ini` 默认 `-n 4` + conftest 台账回传); 代码侧改动已提交推送 `1bde85d`, 并行部分已入库 `f469492`
> 触发: 测试慢, 耗时, 跑全量, 性能, 优化收益, 度量, 并发跑, 并行, xdist, -n, node --check, 临时目录泄漏, 白名单, 排除项, 台账回传
> 最后活动: 2026-09-23 18:37

## 状态

**已交付**: 代码侧三处优化已提交推送 **`1bde85d`**(Gitee 与 GitHub 的 `develop` 均一致, 无幽灵 diff);
**并行已落地并入库 `f469492`**(`pyproject.toml` / `uv.lock` / `pytest.ini` / `tests/conftest.py`)。

| 项 | 结果 |
|---|---|
| A `sidefx.report()` 单次求值 | teardown 4.71~8.97s → **1.04~1.20s** |
| B 前端 JS 语法守阵单进程批量 | 7.375s → **0.378s**; 语义与 `node --check` **8/8 一致** |
| C basetemp 钉进 TMPDIR | **撤回未实施**(只把删除从收尾挪到起始, 总量不变) |
| D 临时目录泄漏 | **3 处**(`test_web` / `test_expr_eval` / 新发现 `test_trigger_events`); 残留 2 → 1 |
| E 过期耗时画像 | `run.md` + 连带 `tmpdir.md` / `techContext.md` |
| **上并行** | `pytest-xdist==3.8.0` + `pytest.ini` 的 `addopts = -n 4`(**默认**) + conftest 台账回传 |

**耗时(带覆盖率)**: 默认并行 `-n 4` **7.61 / 7.79 / 8.87s**; 串行 `-n 0` **21.15 / 21.56s**;
`-n 4 --no-cov` 5.00 / 5.06 / 5.17s。全部 `1191 passed + 1 skipped`, TOTAL 91%。

**文件操作三段状态**(全部 `TMPDIR=R:/Temp/auto-qb/tests`):

| 操作 | ① 初始 | ② 只加白名单 | ③ 调好设置后 |
|---|---|---|---|
| `os.mkdir` | — | 0.64ms | **0.13ms** |
| 写 512B | 20.19ms | 0.58ms | **0.21ms** |
| `os.remove` | 43.02ms | 14.60ms | **0.16ms** |
| `os.rmdir` | — | 52.72ms | **0.14ms** |

- **沙箱假设已彻底排除**: ②③ 两轮都是同一沙箱状态, 差别来自用户设置。
- **并行的关键补丁**: sidefx 台账靠 `config.workeroutput` → `pytest_testnodedown` 回传到控制器汇总,
  否则并行跑看不到「越界 0 条」(拦截一直在 —— 注入越界删除实测串行与并行**都**报错)。
- **覆盖率口径**: 并行 `623 未覆盖 / 219 分支` vs 串行 `623 / 218`, TOTAL 都 91%(**分支 partial 差 1**)。

## 待办(下一步从这里接)

1. **提交并行改动** —— `pyproject.toml` / `uv.lock` / `pytest.ini` / `tests/conftest.py` + 本轮文档回写。
   **用户尚未对这一批说「提交」**。
2. **遗留: 闸门命令自带 `TMPDIR`** —— `.commit-flow.toml` 的闸门不设 `TMPDIR`, 从工具 shell 跑
   `preflight.py` / `commit.py` 忘导出就**假红**(本轮已复现一次, 是已记的坑)。属配置改动, 待拍板。
3. **若哪天又变慢**: 先按**操作类型逐项复测**(别只测"写文件"), 注意白名单**粒度**(要按 Temp 目录加),
   并用关沙箱对照排除工具沙箱。三步定位法与探针见下面的单点指针。

## 单点指针

- 耗时成因 / 度量纪律 / **定位三步** → [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md)
- 并行(默认 `-n 4`、台账回传机制、结论为何曾翻转) → [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)
- 完整归因与决策 → [../tasks/26-09-23-test-suite-perf.md](../tasks/26-09-23-test-suite-perf.md)
- 基线数字 → [../testing/baseline.md](../testing/baseline.md)

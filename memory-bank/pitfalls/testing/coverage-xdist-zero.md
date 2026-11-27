# 全量 `pytest tests` 形态覆盖率 0% 且闸静默放行(环境2 实测)

> 摘要: 环境2(VM)上 `uv run pytest tests` 全量恒 0% 覆盖率且提交闸静默放行(rc=0), 等价收集面 `pytest tests/unit` 覆盖率正常(99.51% 闸过)。全量绿的「绿」不含覆盖率背书。
> 触发: coverage 0%, 覆盖率闸, pytest tests, tests/unit, xdist, fail_under 静默, rc=0, 环境2, 全量绿不信覆盖率, pytest-cov 7.1.0

**Refs:** memory-bank/pitfalls/testing/tmpdir.md, memory-bank/issues/26-11-28-0521-perf-perf-threshold-env-relative.html

### `pytest tests`(arg 形态)覆盖率恒 0% + cov_fail_under 疑未生效; `pytest tests/unit` 正常(2026-11-28, 环境2 实证)

- **触发**: 环境2(VM, 本机)跑 `commands run test.full`(= `uv run pytest tests -q`, -n 8)。
- **判别**:
  · 实证矩阵(全部 2026-11-28 实跑): `pytest tests` 恒 **TOTAL 0%**(6 连跑全 0%, 402-646s), rc=0 且无「Required test coverage」行 —— **闸静默放行**;
    `pytest tests/unit` 恒 **99.51%**(3 连跑全绿闸过, 339-404s); 中等切片/-n 2/单文件/串行均正常(16-24% 真实, 闸正常红);
    collect-only 形态两 arg 均出真实表格(16.49%)且闸行在。
  · 收集面**等价**: `tests` = `tests/unit` + 138 条 real_machine 恒 deselect 项(collect-only 实测 7202/7064, 两形态可跑集同为 7064)。
  · 数据文件**不是变量**: 0% 轮的实例根留档含全量弧线(207 files / ~22-24k 执行行, 路径全盘符形态无 UNC) —— 与 99.5% 轮同形, 差异纯在**报表期读取**。
  · 非数据期因素已排除: 引擎子进程 env(只注入 PYTHONIOENCODING)/repo 根 `.coverage` 存在与否/worker 数(2 vs 8)/嵌套 pytest.main 用例/时长(402s vs 403s 一真一零)。
  · **未解**: 0% 轮 rc=0 说明 `cov_fail_under` 判定被跳过(pytest-cov 7.1.0 plugin.py 语义上 0% 必应 testsfailed++), 与「表格打印了 0%」并立 —— 机制未定位, 限于 pytest-cov 私有面, 不再深挖。
- **处置**:
  · 环境2 上要覆盖率背书: **`uv run pytest tests/unit -q`(等价收集面)替代 `pytest tests`** —— 数字与闸均真实;
  · `commands run test.full` 在环境2 的 [ok] **只背 7058P/6S 的用例绿, 不背覆盖率** —— 基线切片与「全绿」结论照常可用, 覆盖率面引用 unit 形态实测;
  · 仓库侧不做改动: test.full 的 `tests` arg 是环境1 正确口径(real_machine 收集面靠它), 不为本机怪癖改公共任务。
- **边界**: 与 26-11-28 的 Z:\R 改动**无关** —— 改动后 coverage 相关代码路径(`_tmp_bootstrap.py` 候选/retarget)与改前逐字节等价, 0% 在改动前首轮即复现。
- **复发**: 0(首记 2026-11-28)。

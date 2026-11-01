# 4808 passed + 2 skipped(根) —— W7 no-tests 与 W5 零块存疑两件闭合(issue 26-11-01-0953 / 26-11-01-0050)

> 摘要: W7 no-tests 与 W5 零块存疑两件闭合(issue 26-11-01-0953 / 26-11-01-0050)
> 基线时间: 2026-11-02 02:17
**Refs:** memory-bank/issues/26-11-01-0953-test-core-w7-mutation-run-foreground-notests.html, memory-bank/issues/26-11-01-0050-test-core-w5-mutation-dayfile-zeroblock-doubt.html, memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮回写的**工作树**(未执行 git commit)。
- `commands run test.full` 实测(wrapper 墙时 127.3s, 2026-11-02 02:20, Windows 本机):
  - 汇总行: `4808 passed, 2 skipped in 125.40s (0:02:05)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **目标用例**: `commands run test.one -- tests/test_traffic_source_agent.py tests/test_traffic_sample.py` 全绿(首跑曾因新用例构造「3 列无基线 B 块后接 r 行」被判坏, 改 5 列基线块后通过)。
- **变异复跑(W7 件)**: WSL mutmut 3.8.0, 目标 `**/core/traffic_source/agent.py`, 池 = W7 的 7 文件, `--no-refresh --no-sync --children 4`; 修后 **566 变异 / 杀 541 / 存活 25 / no tests 0 / 超时 0**(10.28 mutations/second, 墙时 69.8s); `mutmut results --all true` 过滤 `_run_foreground` = **18/18 killed**。
- **变异侧注记(W5 件)**: 本轮**未重跑** W5 全量变异; 等价判定基于现码静态不可达性 + 两条定向解析/入账用例实测, 两条变异均**未杀死、如实标注等价**。
- **环境 / 工具**: Windows 本机(win32)· Python 3.13.15 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)。
- **口径注记**: 首次全量跑(issue 状态已改但 `kb.index` 未重建的中间态)曾出现 `test_gen_all_check_is_green` 红(2 条 issues 生成物漂移)+ 覆盖率 98.97%; `kb.index` 重建后复跑即全绿 —— 属测量时序问题, 非代码面缺陷。

## 本改动面

- `tests/test_traffic_source_agent.py`: 新增 `test_run_foreground_subprocess_contract_with_probe`(issue 26-11-01-0953) —— 注入 `agent.subprocess.run` 记录器探针, 让 `_run_foreground` 函数体在无 node 环境也必然执行, 逐位断言 `args/cwd/stdin/stdout/stderr/text/timeout/close_fds`; 同步头部「测试计划」清单。
- `tests/test_traffic_sample.py`: 新增 `test_parser_never_emits_zero_slot_block` 与 `test_agg_credit_hours_never_creates_empty_bucket`(issue 26-11-01-0050) —— 实测零槽块与空桶生产点不存在, 为两条等价变异判定提供证据; 同步头部「测试计划」清单。
- 知识库回写: 两件 issue 各置 `Done`(根因/修法/验证/遗留分别落账, W5 两变异如实标注等价未杀)、任务档案 `26-10-08-test-mutation-audit.md` R37 轮次条目与 Summary 精修、本基线切片、索引重建。
- **零 `src/` 改动**; `config.yml` / `auto-qb-data/` 红线未触碰; 未扩池; 未执行 git commit。


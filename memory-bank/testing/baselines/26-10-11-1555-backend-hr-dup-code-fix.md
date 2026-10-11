# 3112 —— hr 重复代码重构(低风险子集)执行基线

> 摘要: 任务档案 [26-10-11-backend-hr-dup-code-fix](../../tasks/26-10-11-backend-hr-dup-code-fix.md)。用户「修复hr部分问题: 26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」→ 按拍板**只做低风险高收益子集(5 条 refactor issue)+ 保守口径(无行为变化的收口)**。改动面: hr 包内 9 个源文件(`adapters/{nexusphp,carpt,btschool,__init__}.py` / `fetcher.py` / `report.py` / `channel.py` / `service.py` / `worker.py`)+ 1 个测试文件(`test_hr_report.py`)。**数字较上基线(`26-10-11-0354`)少 1 passed**(3113→3112)= 删掉的死件单测 `test_stamp_text_ts_zero_is_dash`(连同其生产侧零调用的 `stamp_text_ts`); 语句数 16586→16562(−24, 收口 + 删件)。
> 基线时间: 2026-10-11 15:55

**Refs:** memory-bank/tasks/26-10-11-backend-hr-dup-code-fix.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已快进 `ca2606fe`→`c0038049`; 工作树含本轮全部改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3112 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16562 语句 / 156 未覆盖 / 5712 分支 / 143 partial; 门槛 98% 达标; 本轮三次采样 29.1 / 36.2 / 57.9s —— 耗时随机器负载波动, 以通过数与覆盖率为准)
- 增量明细(本轮真正新增 / 改动):
  - `src/auto_qb/hr/adapters/nexusphp.py`(+`parse_header_counters`)、`carpt.py` / `btschool.py`(委托)、`adapters/__init__.py`(+`_standard_kwargs`)
  - `src/auto_qb/hr/fetcher.py`(+`query_param`,`_scope_of`/`_tid_of` 复用)
  - `src/auto_qb/hr/report.py`(+`_gate_enabled_sites` / `_build_service`,`_scope_of` 复用 `query_param`,删 `stamp_text_ts`)
  - `src/auto_qb/hr/channel.py`(删本地 `_as_int/_as_float`,改从 `model` 导入)
  - `src/auto_qb/hr/service.py`(+`warn_gap_floor` / `_warn_once` / `_abort_wave` / `_settle_lane`;三组骨架收口)
  - `src/auto_qb/hr/worker.py`(`warn_gap` 改走 `warn_gap_floor`)
  - `tests/test_hr_report.py`(删 `test_stamp_text_ts_zero_is_dash` 与其测试计划清单行)
  - `memory-bank/` 回写: 本档案 + activeContext 切片 + 5 条 issue(状态/认领链/修复后补充)+ 各 `_index.md`(`kb.index` 重建)+ 本基线切片
- 机检(本轮相关): hr 相关 9 个测试文件 462 passed; `kb.index` 重建生成物; `kb.check` 主键纪律 / 认领链闭环 / 日期守卫全过; `test_docs_forms.py` + `test_memory_bank.py` 全过。
- 未纳入本轮(刻意不越界): 跨包 3 条(store/token/site-derive)与低收益 1 条(thread-lifecycle)暂缓留 `Open`; 跨包(webui/core/infra)零源码改动; `config.yml` / `auto-qb-data/` 未触碰。

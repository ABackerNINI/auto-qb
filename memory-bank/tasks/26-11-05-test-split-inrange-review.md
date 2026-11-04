# 26-11-05-test-split-inrange-review — 拆分承载区间改动归属与逐行评审(认领 26-11-03-0704)

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** 认领 issue 26-11-03-0704: 拆分承载区间改动源→目标归属比对(7,067 行/45 个 move-only 目标) + 30 污染源区间增量逐行评审(26 clean/4 发现), 4 条入池(1 P2+3 P3), 源 issue 置 Done, 零代码改动
**Topics:** test-split-inrange-review
**Refs:** memory-bank/issues/26-11-03-0704-test-split-carried-inrange-changes.html, memory-bank/issues/26-11-05-0343-test-relocate-dryrun-gate-guard-hole.html, memory-bank/issues/26-11-05-0343-test-ops-skip-rec-start-dead-code.html, memory-bank/issues/26-11-05-0344-test-qbmanager-tasks-missing-assert.html, memory-bank/issues/26-11-05-0344-test-rule-compat-mapping-dup-assert.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s3.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s1.md

## 原始请求

1. 用户指令:「认领并实施 26-11-03-0704-test-split-carried-inrange-changes.html」。
2. 该 issue 的建议修法:对污染源的拆分目标做源→目标内容归属比对;若含区间新增内容,则并入 B5/B9 逐行评审,或在任务档案标注「move-only(含区间改动)」并扩大核验范围。
3. 收尾拍板(AskUserQuestion):4 条评审发现**入池**(不本轮修);**立档并提交**。

## 思考过程与决策

- **先归后筛,不按 180 目标全量评审**:归属比对先把区间增量分流——落入实质(A 类已全文过目)目标的不计缺口,只对落入 move-only 目标的承载增量逐行评审,载荷从约 13.9k 行收到 7,067 行。
- **R4 整组免审的依据**:归属比对显示 R4 的 22 个污染源(12 个 static 根 + 10 个测试文件)的区间增量全部落入实质目标(B5 逐文件过目 / B9 实质面),与 issue 影响面预判一致,无需扩大。
- **复验口径修正**:污染计数必须排除 4 个拆分提交自身的触达,否则 R3 记成 7/9、R4 记成 34/38(其它拆分提交创建/改动了这些文件);修正后与 issue 取证逐条吻合。
- **评审执行方式**:30 个污染源的区间累计 diff(12,401 行)按组分 3 个只读子代理并行逐行读完(不抽样),协调人对每条发现做引文逐字校验与反事实推演(如 F1 逐分支核验 `_load_jobs`/`_recover`/FakeClient 行为后才定 P2)。
- **零代码改动**:本轮只读 git + 写文档;4 条发现全部入池留待认领。

## 实现计划

1. 复验锚点:重跑 4 组污染源 `git log` 计数(排除拆分提交)。
2. 量化:各污染源区间 diff 规模(numstat)。
3. 归属比对:行多重集法(目标@拆分提交 − 源@bf9920d3 基线,与源区间新增行集取交集),脚本在 `%TEMP%\cr3_inrange`(不入库)。
4. 逐行评审:R1 / R2 大源 / R2 小源+R3 三个只读评审分片并行,发现逐字校验。
5. 回写:源 issue 复验行+修复后补充+S3 档案标注;4 条发现入池。
6. 收尾:本档 + kb 收尾 + 提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验锚点(4 组计数逐条吻合) | Done (2026-11-05) |
| 2 | 区间增量量化(R1 7,090 / R2 6,710 / R3 146 新增) | Done (2026-11-05) |
| 3 | 源→目标归属比对(7,067 行/45 个 move-only 目标;R4 全落入实质) | Done (2026-11-05) |
| 4 | 逐行评审(30 源 26 clean;4 发现逐字校验成立) | Done (2026-11-05) |
| 5 | 回写 issue/S3 档案 + 4 条入池 | Done (2026-11-05) |
| 6 | 收尾(本档 + kb + 提交推送) | Done (2026-11-05) |

## 进度日志

### R0 · 立档与实施完成 (2026-11-05)

- **开工同步**:「已同步 d01f0c0d」。
- **复验**:R1 9/10、R2 18/25、R3 3/9、R4 22/38,逐源笔数与 issue 取证逐条吻合;口径=排除 4 个拆分提交。
- **归属比对**:承载进 move-only 目标的区间行 R1 2,249 / R2 4,672 / R3 146,合计 7,067 行 / 45 个目标;重灾区 R1 `test_relocate_exec_*` 1,260、R2 `test_rule_compat_*` 1,751。
- **逐行评审**:30 源区间累计 diff 12,401 行全量读完;26/30 clean,4 条发现(P1 0 / P2 1 / P3 3),全部经协调人引文逐字校验:
  - P2 `tests/test_relocate_exec_run.py:616` `test_on_task_line_holds_in_dry_run` dry-run 闸守阵空洞(删 `relocate_lifecycle.py:240` 的闸仍全绿;反事实推演核验 `_recover` 补发分支要求 `move_issued=False`、FakeClient 只记 calls);
  - P3 `tests/test_ops_skip.py:887` `rec_start` 死代码;
  - P3 `tests/test_qbmanager_tasks.py:497/:513` 缺 `assert` 的元组表达式;
  - P3 `tests/test_rule_compat_mapping.py:111/:113` 逐字重复断言,注释语义无断言承载。
- **入池**:4 条 test 类(topic `split-inrange-review`,doc-refs 反向链本档)。
- **回写**:源 issue 复验行+修复后补充+状态 Done;S3 档案附录 A 补归属完成标注。
- **基线**:零代码改动,不新建基线切片。

- 2026-11-05 03:48 认领 issue 26-11-03-0704: 复验锚点(4 组计数吻合)+归属比对(move-only 目标承载 7067 行/45 目标)+30 污染源区间增量逐行评审(26 clean/4 发现); 4 条入池(1 P2+3 P3, topic split-inrange-review); 源 issue 置 Done; S3 档案标注; 零代码改动

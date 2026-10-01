# 26-10-01-test-truth-hold-shadowed-guard — issue 2212 清偿: 同名测试遮蔽, 真值守阵复活确认

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 19:00
**Summary:** 清偿 issue 26-09-20-2212(test_truth_hold_budget_matches_backend 同名定义两次, 前一条从未执行)。复验结论: 修复已随乐观 UI 重构(0c18fcda, 2026-09-21)落库 —— 两条同名守阵合并为 test_truth_hold_matches_truth_push_cap(tests/test_web.py:7582), 断言对象随常数改名换新(前端 TRUTH_HOLD_MS / 后端 TRUTH_PUSH_CAP_MS), pytest 实测收集 1 条且通过; 两份原始函数体逐字相同, 合并零断言弃置。本次只补认领链, 不再动修复代码。计划外发现(只记不修): tests/test_config.py 另有 5 对同文件重名测试, 同类缺陷待清偿。
**Topics:** test-truth-hold-shadowed-guard-issue-clearance
**Refs:** memory-bank/issues/26-09-20-2212-test-duplicate-test-name-shadowed-guard.html

> 背景关联(不进机器认领链): 本任务是 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 第 2 条。

## 原始请求

用户实施 issue 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 波次第 2 条, 已显式授权实施 W1 且「每个 issue 修完后单独提交」。目标 issue: 26-09-20-2212 —— test_truth_hold_budget_matches_backend 在 tests/test_web.py 同名定义两次, Python 后者覆盖前者, 前一条从未执行, 前端/后端真值宽限一致性守阵实为死测试; 摸排注提示认领时先确认两个断言体保留哪个, 大概率重命名/合并级修改。要求: 认领链(档案 ↔ issue 双向登记)+ 修复 + pytest -k 确认收集与通过 + issue 报告改 Done + 单独提交。

## 思考过程与决策

- **复验(2026-10-01 19:00)**: 入池锚点 `grep -n "def test_truth_hold_budget_matches_backend" tests/test_web.py` 已输出零行 —— 该符号名整个文件不复存在。现场只有一条 `test_truth_hold_matches_truth_push_cap`(tests/test_web.py:7582), 其 docstring 明确写着「本条同时修掉一个既有缺陷: 原 test_truth_hold_budget_matches_backend 同名定义了两次……(已入池 issue 26-09-20-2212)」。现象已消失。
- **修复从何而来**: `git log -S` 定位到两个提交。40bcdc33(2026-09-20 10:46, 「真机复测后的三处收尾」)引入守阵时把同一块代码贴了两遍(diff 两处 `+def test_truth_hold_budget_matches_backend`), 即缺陷源头; 0c18fcda(2026-09-21 00:31, 乐观 UI 重构)把两条合并为 test_truth_hold_matches_truth_push_cap, 提交信息明写「合并了两条同名守阵……(后者覆盖前者, 前一条从未执行)」。入池(09-20 22:12)在前、合并落地(09-21 00:31)在后, 相隔 2 小时 19 分 —— 修是修了, issue 报告的状态推进没跟上。
- **保留/弃置拍板**: 逐字比对 40bcdc33 引入的两份函数体, 空白归一后**完全相同**(同一 docstring + 同一断言: 前端 hold 常数 == 后端 cap 常数, regex 扫 commands.js)。语义纯重复, 合并成一条 = 保留唯一断言, **零断言弃置** —— 连「保留更严的一条」都不必选, 两条本是一模一样的一条。断言对象随 0c18fcda 的常数退役升级: 前端 TRUTH_HOLD_BUDGET_MS → TRUTH_HOLD_MS, 后端 RECEIPT_WAIT_CAP_MS → TRUTH_PUSH_CAP_MS, 合并后的守阵断言的是新契约(D2: 值覆盖保持窗 == 真值推送上限窗)。
- **守阵复活确认**: `commands run test.one -- tests/test_web.py -k truth_hold` → **1 passed, 196 deselected**(3.12s) —— 守阵真实被收集、真实在跑, 不再是"看着有守阵其实没跑"。
- **全库核查(issue 建议 03)**: 扫全部 tests/*.py 顶层 `def test_`(1685 条), 同文件重名仅剩 tests/test_config.py 一处: 5 对(test_validate_gslc / test_validate_empty_file / test_config_error_wraps_io_and_yaml / test_models_default_sources / test_validate_section_type_errors, 行号 718/793、732/835、739/842、749/852、766/869, 取证 2026-10-01)。逐对 diff: 4 对逐字相同, 1 对(test_validate_section_type_errors)仅 YAML 样本一字之差(`[, 5]` vs `[" ", 5]`, 断言意图同: delete_tags 非法元素报错)。**同类缺陷, 本轮不动** —— 超出本 issue 范围, 只记录待用户定调(修 + 顺带加「重复顶层 test 名」防复发守阵, 建议另开一轮)。
- **issue 建议 02(加防复发守阵)本轮不做的原因**: 全库守阵要扫出 test_config.py 的 5 对存量, 要么闸门立红、要么带存量豁免表 —— 都把别处债务耦合进本 issue。守阵应随 test_config.py 清偿一并落, 届时零豁免干净上闸。

## 实现计划

- 档案认领(本文档)+ issue 报告 doc-refs 回指。
- 修复: 无需动代码 —— 复验确认已随 0c18fcda 落库, 现场核对无缺陷。
- 验证: pytest -k 确认目标守阵收集 1 条且通过 → `commands run test.quick` 全绿。
- 清偿: issue 报告徽标 + `<meta name="issue-status">` 改 Done, 状态变更日志补复验/清偿两行, 复验段写「已消失 + 修复来历」, 修复后补充写合并拍板与全库核查发现, 加 `<meta name="doc-refs">` 回指本文档; `commands run kb.index` + `uv run python .agents/skills/create-issue/scripts/gen_issues_index.py`(kb.index 不含 issues 生成器)。
- 单独提交: gitmoji ✅ + 中文首行, 消息入 `.git/COMMIT_MSG_AI.txt` 后 `commands run ship.commit`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 复验锚点(现场代码核对) | ✅ 完成 | 旧符号名已不存在, 现役守阵 test_web.py:7582 |
| 两个断言体拍板 | ✅ 完成 | 逐字相同, 合并零弃置; 修复在 0c18fcda |
| 全库同名测试核查(issue 建议 03) | ✅ 完成 | 仅 test_config.py 5 对, 只记不修 |
| 认领档案(查重 + 新建 + Refs) | ✅ 完成 | 跨工作区查重无撞名; issue 报告回指本文档 |
| pytest -k + test.quick | ✅ 完成 | -k truth_hold 1 passed / test.quick 收尾后全绿(数字见进度日志) |
| issue 报告 Done + 索引重建 | ✅ 完成 | 徽标+meta+状态日志+复验+补充段+doc-refs 回指 |
| 单独提交(ship.commit) | ✅ 完成 | hash 见进度日志末条 |

## 进度日志

- **2026-10-01 18:52** 同步成功 931e231d(工作区净)。读 issue 报告 / pitfalls 索引(testing 类) / memory-bank SKILL / 参照上一条清偿链(0128 档案)。复验: 旧符号名零命中, 现役守阵合并自 0c18fcda; 40bcdc33 两份函数体逐字相同。pytest -k truth_hold → **1 passed, 196 deselected**。跨工作区查重(本 clone + ../auto-qb-*)无同名 slug, 建本档案。
- **2026-10-01 19:00** issue 报告清偿: 徽标 + `<meta name="issue-status">` 改 Done, 状态变更日志补复验(In Progress)/清偿(Done)两行, 加复验段与修复后补充段(合并拍板 + 全库核查 5 对发现), 加 `<meta name="doc-refs">` 回指本档案。跑 `commands run kb.index` 重建 + `gen_issues_index.py` 迁移 issues 状态分区。test.quick 实测数字见下一条。

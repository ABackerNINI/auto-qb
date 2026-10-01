# 26-10-01-test-fakeconfig-shared-state-isolation — issue 2311 清偿: FakeConfig 共享可变类属性顺序污染

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 19:13
**Summary:** 清偿 issue 26-09-22-2311(FakeConfig.grouping 类级共享实例被 test_web 原地改写, test_refresh_removed_grouping_disabled 顺序敏感)。复验结论: 修复已随内核化重构 P5(54c83ac3)落库 —— FakeConfig.__init__ 对每个非标量类属性 copy.deepcopy 成实例属性(与真实 Config 每次构造独立实例同形), 污染面从 grouping 一处扩展到全部可变段一并根除。原必红顺序(tests/test_web.py 先、tests/test_qbmanager.py 后)实测 240 passed, 1 skipped; 单文件 44 passed。本次只补认领链, 未再动修复代码。计划外发现(只记不修): tests/test_ui.py:41 注释仍按"FakeConfig.logging 是类属性共享实例"给理由, 修复后已过时(保守无害)。
**Topics:** test-fakeconfig-shared-state-isolation-issue-clearance
**Refs:** memory-bank/issues/26-09-22-2311-test-fakeconfig-shared-state-order-pollution.html

> 背景关联(不进机器认领链): 本任务是 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 第 3 条。

## 原始请求

用户实施 issue 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 波次第 3 条, 已显式授权实施 W1 且「每个 issue 修完后单独提交」。目标 issue: 26-09-22-2311 —— FakeConfig.grouping 为类级共享实例, test_web 两处在实例上改 enabled=True 后残留全局, test_qbmanager 的 test_refresh_removed_grouping_disabled 在 test_web 先跑的自定义顺序下必红(全量字母序不触发)。要求: 先复现确认现场, 再实施隔离修复(以现场最小改动为准), 原必红顺序复跑证明不再顺序敏感 + 全量字母序不回归, 认领链(档案 ↔ issue 双向登记), issue 报告改 Done, 单独提交。

## 思考过程与决策

- **复验(2026-10-01 19:08)**: 按入池给出的原必红顺序跑 `commands run test.one -- tests/test_web.py tests/test_qbmanager.py`(-n 0 保序)→ **240 passed, 1 skipped**(11.64s), 受害用例 test_refresh_removed_grouping_disabled 在其中; 单文件 `commands run test.one -- tests/test_qbmanager.py` → **44 passed**(3.78s)。入池时的一红一绿(顺序跑 1 failed / 单文件 44 passed)已变成两绿 —— 现场不再顺序敏感。
- **修复从何而来**: `git log -S "copy.deepcopy(default)" -- tests/helpers.py` 定位到 commit **54c83ac3**(内核化重构 P5: rules 模块化 + 刷新管线收口)。现役代码(tests/helpers.py:861-872)是 `FakeConfig.__init__` 遍历 `vars(type(self))`, 对每个非下划线开头、非标量(str/int/float/bool/None)的类属性 `copy.deepcopy` 成实例属性, 并留注释点名本 issue 的污染路径(test_web 改 grouping.enabled 泄漏给 test_refresh_removed_grouping_disabled)。pitfalls/testing/fake-config-shared-mutables.md 记录该处置于 2026-10-01 P5 期间实施, 当时实报的正是同一受害用例(test_build_group_view 污染 test_refresh_removed_grouping_disabled, xdist 分布改变让跨 worker 污染显形)。
- **覆盖面评估(issue 影响面提的同类风险一并根除)**: 深拷贝按"非标量"一刀切, grouping / trackers / delete_tags / delete_tags_if_has_no_torrents / add_episode_tags / web / hr_check / logging / notify / rules_config / qbittorrent / hr 等全部可变段每实例独立; 标量(state_file / interval 等)仍走类属性但不可变, 实例上重绑无污染 —— 不是只修 grouping 一处的最小补丁, 而是把 issue 影响面表里"其余可变类属性谁先改谁污染"的整类风险收掉。
- **类级直改核查**: `grep -rn "FakeConfig\.<段>" tests/` 现场只剩两类残留: test_web.py:6069-6115 的 6 处**读**类属性当 SimpleNamespace 入参(热重载测试, 不改写), test_ui.py:41 的注释引用 —— 无任何 `FakeConfig.grouping.enabled = True` 式类级写, 污染入口只剩实例级原地改, 已被深拷贝隔离。
- **本次零代码改动的拍板**: 修先于清偿落库(与 W1 第 2 条 issue 2212 / 0c18fcda 同模式), 现场最小改动 = 不再动代码; 也不加防复发守阵 —— issue 建议修法②(test_web 加还原 fixture)已被更彻底的方案①(实例级独立)覆盖, fixture 属重复防线; 深拷贝纪律已写进 pitfall(新增测试禁止依赖「改类属性影响其它实例」), 守阵再单独立闸收益为负(见 scope-guard)。

## 实现计划

- 档案认领(本文档)+ issue 报告 doc-refs 回指。
- 修复: 无需动代码 —— 复验确认已随 54c83ac3(P5)落库, 现场核对无缺陷。
- 验证: 原必红顺序两文件连跑 + 受害用例单文件 → `commands run test.quick` 全绿。
- 清偿: issue 报告封面徽标(Open→Done)+ kicker(未修→已修)+ `<meta name="issue-status">` 改 Done + `<meta name="doc-refs">` 回指本文档, 复验/修复后补充两段落地, 状态变更日志补两行; `commands run kb.index` + `uv run python .agents/skills/create-issue/scripts/gen_issues_index.py`(kb.index 不含 issues 生成器)。
- 单独提交: gitmoji ✅ + 中文首行, 消息入 `.git/COMMIT_MSG_AI.txt` 后 `commands run ship.commit`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 复验(原必红顺序复跑) | ✅ 完成 | 两文件 -n 0 保序 240 passed, 1 skipped; 单文件 44 passed |
| 修复来历定位 | ✅ 完成 | 54c83ac3 P5; pitfall fake-config-shared-mutables.md 同日记录 |
| 覆盖面与类级直改核查 | ✅ 完成 | 全部非标量段每实例深拷贝; 类级写零残留 |
| 认领档案(查重 + 新建 + Refs) | ✅ 完成 | 跨工作区查重无撞名; issue 报告回指本文档 |
| test.quick 全量回归 | ✅ 完成 | **1909 passed, 3 skipped**(21.07s); 首跑 1 failed 为认领链守阵(当时 doc-refs 回指未落), 回指后复跑全绿 |
| issue 报告 Done + 索引重建 | ✅ 完成 | 徽标+kicker+meta+状态日志+复验/补充段+doc-refs 回指; kb.index + gen_issues_index.py 均跑 |
| 单独提交(ship.commit) | ✅ 完成 | hash 以本仓库 git log 为准(提交无法携带自身 hash) |

## 进度日志

- **2026-10-01 19:08** 同步成功 2fc34fc2(工作区净)。读 issue 报告 / pitfalls 索引(testing 类, 命中 fake-config-shared-mutables)/ memory-bank SKILL / 参照 W1 第 2 条清偿链(26-10-01-test-truth-hold-shadowed-guard)。复验: 原必红顺序 `test.one -- tests/test_web.py tests/test_qbmanager.py` → **240 passed, 1 skipped**(11.64s); 单文件 test_qbmanager → **44 passed**(3.78s)。`git log -S` 定位根修在 54c83ac3(P5 的 FakeConfig.__init__ 非标量深拷贝)。跨工作区查重(../auto-qb-*)无同名 slug, 建本档案。
- **2026-10-01 19:13** issue 报告清偿: 徽标 Open→Done, kicker 未修→已修, `<meta name="issue-status">` 改 Done, 状态变更日志补复验(In Progress)/清偿(Done)两行, 复验段与修复后补充段落地(实际修法 = 建议方案①的彻底版, ②不再需要), 加 `<meta name="doc-refs">` 回指本档案。`commands run kb.index` + `gen_issues_index.py` 跑过, issue 迁入 issues/_index.md 的 Done 分区。test.quick 首跑 1 failed(test_docs_forms::test_claim_chain_is_bidirectional —— 认领链守阵抓的正是「档案→issue 已声明、issue 未反向声明」的单向态, doc-refs 落地后复跑)→ **1909 passed, 3 skipped**(21.07s), 全量字母序不回归。计划外发现(只记不修): tests/test_ui.py:41 注释按旧共享语义给理由, 深拷贝根修后已过时(保守无害, 建议随下次触碰 test_ui 时顺手校正)。合流: ship.commit 内部同步预检因 overlap(远端 58a88928 与本地 tasks/_index.md 同文件异行)拒绝 → 按 failure 行指引 stash(-u) 移出 → sync 快进 58a88928 → pop 自动合并取回 → 索引在新基线重建后提交。

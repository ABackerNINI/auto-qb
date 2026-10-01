# issue-clearance-roadmap — Issue 全量清偿路线图(计划交付)

> 摘要: 用户要求摸排全部未决 issue、分类排序并出计划(**已出计划**:
> [plans/26-10-01-1758-plan-issue-clearance-roadmap.html](../plans/26-10-01-1758-plan-issue-clearance-roadmap.html))。
> 入列时范围 **31 条未决**(30 Open + 1 In Progress;28 Done 不入列):bug 8 · feat 5 · docs 5 · test 4 ·
> chore 4 · perf 3 · refactor 2;档位 standard 18 / light 13。
> 分七波:W1 流程与闸门卡点(5)→ W2 状态完整性与数据安全(4)→ W3 WebUI 健壮性与安全(5)→
> W4 性能(2)→ W5 设计拍板大件(1)→ W6 轻量收尾(9,可穿插)→ W7 挂靠与缓做(5,不排期)。
> 关键挂账: 两条 26-10-01 docs issue 已确认被 doc-drift-repair 计划(26-10-01-1728)覆盖;
> 3 条 HR P3 缓做依赖 D4;In Progress 的 26-09-21-0219 报告无 doc-refs,认领前先对齐前史。
> **已完成: W1 流程与闸门卡点 5/5 全清**(每条单独提交, 复验/修复/清偿链见各自 tasks/ 档案, 此处不复写):
> ①26-09-28-0128 → 931e231d(根修已在库, 补守阵 test_unstaged_delete_uses_rm_cached);②26-09-20-2212
> → 2fc34fc2(根修 0c18fcda 合并同名守阵);③26-09-22-2311 → 9486a7cd(根修 54c83ac3 deepcopy, 零代码改动);
> ④⑤26-09-30-0602 两条 → 9aeb4400(colwidth 用例选键)/ 59725443(ctx03 点击落点), 同档案
> tasks/26-10-01-test-ui-smoke-clearance.md。收尾基线切片见 `commands run kb.baseline` 最新一条。
> **计划外事项(只记录, 均未修、未建新 issue, 待用户定调)**:
> a) `commands run kb.index` 的三条生成器不含 issues 索引 —— 改 issue 状态后须单独跑
> `uv run python .agents/skills/create-issue/scripts/gen_issues_index.py`(S1, 已记各档案);
> b) tests/test_config.py 另有 **5 对同文件重名测试遮蔽**(4 对逐字相同, 同类缺陷;S2, 已记
> issue 26-09-20-2212 报告补充段与档案)—— 清偿轮(含防复发守阵)待授权;
> c) tests/test_ui.py:41 注释仍按旧「FakeConfig 类属性共享」理由写, deepcopy 根修后过时(保守无害;S3);
> d) 冒烟「行内交互后代(@click.stop 的 site-chip)吞修饰键点击」新坑已按动作写进
> pitfalls/testing/smoke.md(S4)。
> **待办**: W2 状态完整性与数据安全(4)起逐波推进, 每波待用户显式授权;路线图口径余 26 条
> (其后又有新入池, 实时以 issues/_index.md 为准;路线图 HTML 本体不改, 未全清不转 Done)。
> 最后活动: 2026-10-01 20:05

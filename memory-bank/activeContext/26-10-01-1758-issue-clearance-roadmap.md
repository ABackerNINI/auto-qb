# issue-clearance-roadmap — Issue 全量清偿路线图(计划交付)

> 摘要: 用户要求摸排全部未决 issue、分类排序并出计划(**已出计划**:
> [plans/26-10-01-1758-plan-issue-clearance-roadmap.html](../plans/26-10-01-1758-plan-issue-clearance-roadmap.html))。
> 范围 **31 条未决**(30 Open + 1 In Progress;28 Done 不入列):bug 8 · feat 5 · docs 5 · test 4 ·
> chore 4 · perf 3 · refactor 2;档位 standard 18 / light 13。
> 分七波:W1 流程与闸门卡点(5)→ W2 状态完整性与数据安全(4)→ W3 WebUI 健壮性与安全(5)→
> W4 性能(2)→ W5 设计拍板大件(1)→ W6 轻量收尾(9,可穿插)→ W7 挂靠与缓做(5,不排期)。
> 关键挂账: 两条 26-10-01 docs issue 已确认被 doc-drift-repair 计划(26-10-01-1728)覆盖;
> 3 条 HR P3 缓做依赖 D4;In Progress 的 26-09-21-0219 报告无 doc-refs,认领前先对齐前史。
> 方法: 只读 issues/_index.md + 31 份报告 issue-* meta 扫描,**零代码分析**(留到认领时)。
> **正在进行**: W1 逐条清偿中(每条单独提交)。已完成: 第 1 条 26-09-28-0128(931e231d)、
> 第 2 条 26-09-20-2212(同名守阵遮蔽, 修复早随 0c18fcda 落库, 本轮补清偿链; 档案
> tasks/26-10-01-test-truth-hold-shadowed-guard.md)。计划外发现待用户定调:
> tests/test_config.py 5 对同文件重名测试(4 对逐字相同, 同类缺陷)。
> **待办**: W1 余 3 条;test_config.py 重名清偿轮待授权。
> 最后活动: 2026-10-01 19:05

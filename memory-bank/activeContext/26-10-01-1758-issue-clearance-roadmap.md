# issue-clearance-roadmap — Issue 全量清偿路线图(计划交付)

> 摘要: 用户要求摸排全部未决 issue、分类排序并出计划(**已出计划**:
> [plans/26-10-01-1758-plan-issue-clearance-roadmap.html](../plans/26-10-01-1758-plan-issue-clearance-roadmap.html))。
> 入列时范围 **31 条未决**(30 Open + 1 In Progress;28 Done 不入列):bug 8 · feat 5 · docs 5 · test 4 ·
> chore 4 · perf 3 · refactor 2;档位 standard 18 / light 13。
> 分七波:W1 流程与闸门卡点(5)→ W2 状态完整性与数据安全(4)→ W3 WebUI 健壮性与安全(5)→
> W4 性能(2)→ W5 设计拍板大件(1)→ W6 轻量收尾(9,可穿插)→ W7 挂靠与缓做(5,不排期)。
> 关键挂账: 两条 26-10-01 docs issue 已确认被 doc-drift-repair 计划(26-10-01-1728)覆盖;
> 3 条 HR P3 缓做依赖 D4;In Progress 的 26-09-21-0219 报告无 doc-refs,认领前先对齐前史。
> **已完成: W1 流程与闸门卡点 5/5 全清**(持久层 = 四份 tasks/ 档案 + issues Done 分区, 收尾基线
> 26-10-01-2003; 此处只留路标, 明细不在切片)。
> **已完成: W2 状态完整性与数据安全 3/4 清偿**(明细已迁 progress/implemented-core.md ·
> implemented-webui.md + issues Done 分区, 此处只留路标): ①1347-token(web.token 非原子写)
> → 5965cc07(ensure_web_token 改走 utils.atomic_write, +3 守阵); ②1347-tray(托盘 join 超时弃落盘)
> → 9f73b6d8(join 5s→10s + 超时 WARNING, +1 守阵); ③0219(.!qB 过渡态误判缺文件) → c353e899
> (按计划 26-09-22-2038 过渡态容忍, grouping_mod 汇聚点 + store/utils/ops_mod 配套, +8 守阵,
> 计划 doc-status 已完档 Done)。**W2 第 4 条 26-09-22-2221(feat 跨组文件交叉冲突)用户明确排除, 未动待后续**。
> **计划外事项 a-d 已全部了结**(后续轮次清偿, 状态以 issues/_index.md Done 分区为准):
> a) kb.index 已收编 issues 索引生成器(f3564847); b) test_config 5 对重名死测试已清偿 + 全仓
> 防复发守阵(d1c25fcb); c) test_ui 过时注释已随漂移修复批次校正(2501698e); d) 冒烟「行内交互
> 后代吞修饰键点击」新坑已入 pitfalls/testing/smoke.md。
> **待办**: W3 WebUI 健壮性与安全(5)起逐波推进, 每波待用户显式授权;路线图 HTML 本体不改,
> 未全清不转 Done(W1/W2 同口径);实时以 issues/_index.md 为准。
> 最后活动: 2026-10-01 21:36

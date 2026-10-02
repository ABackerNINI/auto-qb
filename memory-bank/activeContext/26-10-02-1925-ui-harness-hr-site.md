# ui_harness --hr-site 起盘崩溃修复(issue 26-10-02-1900) — Done

> 摘要: 用户指派认领。复验仍复现; 漂移面比入池取证多两处: `EXEMPT`/`UNKNOWN` 两成员同样已删, 且 v3 `HrJudgement.is_hr` 由构造 kwarg 变 property(只改枚举成员仍 TypeError)。`scripts/ui_harness.py` `_mk` 重写为 v3 四行判定表 7 场景轮转(行1 考察中 / 行2 B·C·D 终态 / 行3 放行记录 / 行4 本地兜底 / judged=None 回落; 身份与 facts.lane 耦合, reason 直抄 `resolve_identity`, site_satisfied 按 `HrEntry.satisfied_verdict` 档位即结论口径); LANE_*/SOURCE_* 改从 `auto_qb.hr.model` import。「考核未通过」failed 档 v3 下替身可构造(RELEASED+facts.lane=C), 从盲区变必渲染桶。验证: 桩真跑起盘 200(atlas/groups/state), 20 行种子六 src 桶全铺满(failed×3 / warning×2 首现); 生产代码零改动; test.full 2292 passed + 3 skipped / 99%(37.0s, @ 2a9932d9, 基线切片 26-10-02-1925)。新坑 pitfalls/testing/stubs-sim.md「替身引用生产 API 符号」; issue 置 Done。未提交(等用户指令)。
> 最后活动: 2026-10-02 19:25

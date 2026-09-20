# Issues Index

> **本文件是生成物, 不要手改** —— 由 `../../.agents/skills/create-issue/scripts/gen_issues_index.py` 扫描 `memory-bank/issues/*.html` 的 meta
> (`issue-status` / `issue-stamp` / `issue-title` / `issue-summary` / `issue-type`)生成;
> 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **类型 · 简述 · 报告链接**(分区即状态); 状态改在报告 HTML 的封面徽标与
> `<meta name="issue-status">`(两处一起改)。状态取值: `Open` / `In Progress` / `Fixed` / `WontFix` / `Duplicate`。
> 文件名 = `<YY-MM-DD-HHMM>-<type>-<slug>.html`, type 取值: bug / perf / docs / test / refactor / feat / chore / question。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 create-issue skill (../../.agents/skills/create-issue/SKILL.md)
> (该不该现在修, 见 scope-guard skill)。


## 待处理分布（Open）

| 类型 | 条数 |
|---|---|
| perf | 1 |
| docs | 1 |
| test | 3 |
| chore | 2 |

## Open

- [test] [test_truth_hold_budget_matches_backend 同名定义了两次, 前一条守阵从未执行](26-09-20-2212-test-duplicate-test-name-shadowed-guard.html) — 同名函数后者覆盖前者, 前端/后端真值宽限一致性守阵实际是死测试
- [test] [sim_qb 缺「/sync/maindata 快照滞后」模型, 本地无法复现/验证真值直查的收益](26-09-20-2145-test-sim-qb-maindata-snapshot-lag.html) — 仿真端状态瞬时翻转, 掩盖一切'真值尚未落地'类缺陷; 需加 1.5s 快照滞后模型
- [chore] [grill-me skill 是 2 行占位 stub](26-09-20-1427-chore-skill-grill-me-empty-stub.html) — grill-me 仅含 openai.yaml 与 2 行 SKILL.md, 无实际内容却占一个技能位
- [chore] [hatch-pet 调付费 OpenAI 图像 API 且无成本提示](26-09-20-1427-chore-skill-hatch-pet-api-cost.html) — hatch-pet 生成图会直连 api.openai.com 计费接口, skill 未标注费用风险
- [docs] [两个 skill 对写 USER.md 的口径相反](26-09-20-1427-docs-skill-user-md-write-conflict.html) — aesthetic-preset-library 要求写入 USER.md, autoclaw INTERACTIONS.md 明令禁止回写
- [test] [主循环节拍断言无容差: 机器负载高时偶发假红](26-09-20-0952-test-mainloop-tick-timing-flaky.html) — test_qbmanager.py:186 断言 elapsed >= 0.05 无容差, 负载下实测 0.046s 即假失败
- [perf] [节拍门控未减少总重建次数: 一半只是从主循环搬到请求路径](26-09-19-2122-perf-webui-poll-gate-no-net-saving.html) — 节拍门控(95fb673)在 3s 客户端档实测 41→40 次重建, 未省 CPU; 省下的 50% 只出现在 6s 档

## In Progress

(暂无)

## Fixed

- [bug] [状态栏今日流量: 图标与数值同色且非真图标, 易被读成数值的一部分](26-09-20-1840-bug-webui-statusbar-traffic-icon.html) — 今日流量块图标(#i-chart)与 ↑/↓ 数值同色同排, 易误读为数值一部分; 棱镜侧同病且图标无颜色
- [bug] [WebUI 列设置(顺序/显示/宽度)经常被重置](26-09-20-1800-bug-webui-column-prefs-reset.html) — 表格列的顺序/显隐/宽度偏好偶发丢失, 刷新后回到默认布局
- [bug] [状态栏上传/下载速度不更新, 恒显示 0](26-09-20-1646-bug-webui-statusbar-speed-always-zero.html) — 状态栏速度由前端对 groups 求和(totalDl/totalUl), 真机有下载/上传时仍恒为 0
- [docs] [conventions.md 的『绝对不要 push』与 AGENTS.md 现行『提交=commit+自动推送』矛盾](26-09-19-2359-docs-memory-bank-push-rule-drift.html) — 知识库 Git 约定仍写禁 push, 与 2026-09-19 用户新规相反, 会让 agent 拒绝推送
- [bug] [3s 兜底超时后补丁值永久留在行上: 「不再贴、等下轮服务端」在 rid 门控下不成立](26-09-19-2141-bug-webui-pending-timeout-stale-patch.html) — isPending() 超时只 delete pendingOps[hash], 注释称'下轮以服务端为准'; 但 rid 未变时服务端不回传数组、行对象不被替换 ⇒ 乐观补丁(kind=paused)留在行上不走。hang 模式实测: 3.66s 清 pending 后行仍 s-paused, 真值 s-downloading
- [bug] [乐观态要挂满 3 秒才消除: 「真值匹配即清」从未实现, 且回执后不立即拉真值](26-09-19-2024-bug-webui-truth-convergence.html) — pendingOps 只有超时/失败两个清除点(app.js:2315/2361), 真值到了也不清; 且 act*/bulk 回执后无 refresh, 真值要等下一轮轮询(>3000 种子 3s) —— 用户报的「乐观后 2-4s 才恢复」
- [bug] [整剧(show 级)操作在剧行上没有 is-pending 标记: 补丁 0ms 贴上但用户看不到任何即时反馈](26-09-19-1959-bug-webui-show-row-no-pending.html) — 剧行 .show-row 不绑 is-pending(只有集行 .ep-row 绑), 整剧暂停/开始时剧行折叠 ⇒ 补丁 0ms 也无可见反馈; 与 BUG-3 同类的漏绑
- [perf] [乐观 UI 反应迟缓: 真机点击后约 2-4 秒才看到变化(补丁被 POST 往返挡在后面)](26-09-19-1939-perf-webui-optimistic-latency.html) — 乐观补丁在 await POST 之后才贴(app.js:3319→3327 等 4 处), 真机点击到界面变化 2-4s, 违背「点击即变」设计; 需先定测量口径再定位 POST 慢还是命令消费慢
- [bug] [sync_interval 与前端分档轮询错配: >3000 种子时约一半视图重建无人消费](26-09-19-1900-bug-webui-poll-cadence-mismatch.html) — 服务端固定 1.5s 重建四视图, 前端 >3000 种子时 3s 才取一次 ⇒ 约一半 rebuild_views 无人消费; 需先拍板方向
- [perf] [/api/search 等热端点仍返回裸 dict: 服务端白跑 jsonable_encoder(实测 82.6 ms)](26-09-19-1900-perf-webui-hot-endpoints-jsonable-encoder.html) — /api/state 与 /api/groups 已改 JSONResponse 直返(189→23.5ms), /api/search(1.46MB/82.6ms)与详情族未改

## WontFix

(暂无)

## Duplicate

(暂无)

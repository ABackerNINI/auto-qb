# HR 排除未落到取数侧 · 稳态降频失效 (取证轮) — 已闭环

> 摘要: 用户报「按标签/分类排除 HR 管理的种子似乎打破稳态触发拉取 (稳态设 24H)」。取证结论: HR 排除的判据单点 <code>TorrentRecord.hr_excluded()</code> 只被判定侧 (hr_judgement / check_hr_condition / hr_managed) 与 WebUI 展示侧消费, <b>取数/对账侧从不读它</b> —— <code>HrRuntime._anchors</code>(runtime.py:358-383) 按站点接入无差别采集本地种子, <code>_build_objects</code>(service.py:1375-1413) 的排除链只有 终态/放行/超额 三档。⇒ 被排除种子仍进对账对象集 ⇒ <code>steady = anchors_known and not objects</code>(service.py:497) 恒假 ⇒ 间隔闸永远取 refresh_interval (用户 5H), idle 24H 永不生效。纠正归因: 排除在取数侧是空操作, 破稳态的真因是<b>新增 IYUU 种子</b>(新种子进对象集, 属设计本意)。日志侧证: 相邻两波间隔 16h55m &lt; 24H。修复方向 (A 锚点剔除 / B 锚点带排除位只出对象集 / C 站点开关) → 用户拍板 <b>方案 B</b>, <b>已落地并全链闭环</b>(计划 [26-10-08-1249](../plans/26-10-08-1249-plan-hr-exclude-steady.html) S1–S6; S5 真机复核 26-10-17 用户确认生效)。报告 [26-10-08-1235](../reports/26-10-08-1235-report-hr-exclude-steady.html)。
>
> 最后活动: 2026-10-17 05:27

**Refs:** memory-bank/tasks/26-10-08-backend-hr-exclude-steady.md

## 正在进行

- 无 —— 专题已闭环 (2026-10-17)。

## 闭环记录 (2026-10-17)

- S5 真机复核用户确认生效(`wave.idle_mode=true` / 日志「稳态降频」/ 稳态期请求量下降) ⇒ 计划 [26-10-08-1249](../plans/26-10-08-1249-plan-hr-exclude-steady.html) 与档案 [26-10-08-backend-hr-exclude-steady](../tasks/26-10-08-backend-hr-exclude-steady.md) 均置 Done。
- 闭环纪要蒸馏: progress/implemented-core.md「HR 排除落到取数侧」条目; 各轮次明细见档案「进度日志」(取证轮 12:35 / 计划轮 12:49 / 实施轮 13:05 / 收口轮 26-10-17)。

# Issues Index

> **本文件是生成物, 不要手改** —— 由 `.agents/skills/create-issue/scripts/gen_issues_index.py` 扫描
> `issues/*.html` 的 meta 生成; 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **状态 · 日期 · 简述 · 报告链接**; 状态改在报告 HTML 的封面徽标与 `<meta name="aqb-issue-status">`(两处一起改)。
> 状态取值仅五种: `Open` / `In Progress` / `Fixed` / `WontFix` / `Duplicate`。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 [create-issue skill](../../.agents/skills/create-issue/SKILL.md)
> (该不该现在修, 见 [scope-guard skill](../../.agents/skills/scope-guard/SKILL.md))。

## Open

- `Open` · 26-09-19 · [sync_interval 与前端分档轮询错配: >3000 种子时约一半视图重建无人消费](26-09-19-1900-webui-poll-cadence-mismatch.html) — 服务端固定 1.5s 重建四视图, 前端 >3000 种子时 3s 才取一次 ⇒ 约一半 rebuild_views 无人消费; 需先拍板方向

## In Progress

(暂无)

## Fixed

- `Fixed` · 26-09-19 · [/api/search 等热端点仍返回裸 dict: 服务端白跑 jsonable_encoder(实测 82.6 ms)](26-09-19-1900-webui-hot-endpoints-jsonable-encoder.html) — /api/state 与 /api/groups 已改 JSONResponse 直返(189→23.5ms), /api/search(1.46MB/82.6ms)与详情族未改

## WontFix

(暂无)

## Duplicate

(暂无)

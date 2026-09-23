# 部分种子 HR 在线核实
> 摘要: 计划 v1.1 待拍板（开放 4 条）；BTSchool 实验脚本 --auto-cookie 全自动 CDP 通道实测通过
> 触发: 部分种子, HR 核实, auto-cookie, BTSchool
> 最后活动: 2026-09-23 00:15

## 状态

计划 v1.1 待拍板，开放问题 4 条：首批站点 / 频度默认 / unknown_policy / cookie 分期；
字段与防重下已确认入模（HR 页八字段确认入模：HR 编号/名称/上传量/下载量/分享率/还需做种/完成/剩余达标，
(站点, tid) 主键跨站隔离 + infohash 回填 + hr_downloaded 防重下永久层）。

BTSchool 实验脚本已产出（`scripts/`），`--auto-cookie` 全自动 CDP 通道实测通过
（无头拉起 → CDP 抓取 → 干净报错 → 清理零残留），仅剩首次人工登录。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html)
- [档案](../tasks/26-09-22-backend-partial-hr-verify.md)

## 实测

selftest 11/11 + 离线样张解析 1 行全字段正确 + 全量 1189 passed + 1 skipped（TOTAL 91%）。

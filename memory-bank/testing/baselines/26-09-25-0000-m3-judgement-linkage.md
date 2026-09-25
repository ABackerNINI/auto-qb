# 1504 → 1520 (+16) —— M3 判定联动

> 摘要: 三态判定接进 TorrentRecord(判定桥 hr_link 稳定引用), 四个消费点调用点一行未动; 16 条用例; 时分不可考; 当日序位第 5
> 基线时间: 2026-09-25 00:00
> 档案: 26-09-22-backend-partial-hr-verify

- ↑ 收集数 **1504 → 1520**(**+16**; 2026-09-25 **M3 判定联动**):
  三态判定接进 `TorrentRecord` —— 记录侧只加 `hr_link`(判定桥 = `QbManager.hr` 门面的**稳定引用**,
  由 `TorrentStore` 在记录构建/变更时挂上)/ `hr_judgement()` / `hr_anchor()`, 而 `check_hr_condition` 与
  `check_hr_satisfied` 改成「站点侧优先、站点没给再回落本地」⇒ **四个消费点(打标 / WebUI 视图 / `hr` 规则条件 /
  `tor.hr_*` 表达式)调用点一行未动**; 判定收口在 `hr/resolve.py::judge_record`(多 infohash 取更保守者 +
  `HrJudgement` / `HrSiteFacts`), 门面入口 `HrRuntime.judge()`; `mode: all` 升为站点侧驱动(未核实恒受管束);
  `manager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`; WebUI 透出三态/依据/达标来源 + 站点侧值。
  新增用例 16 条(收口判定 7 · 门面 3 · 记录接入 4 · 锚点 1 · WebUI 1) —— 收集数 1504 → 1520。
  ★红验 2 处反证(旁路判定桥 / 站点未接入返回判定) ⇒ 4 条守阵变红, 回滚后 89 绿。
  全量 **1519 passed + 1 skipped** / TOTAL 91%(10534 / 779 / 3494 / 310~311) / sidefx ≈2447 / 越界 0。

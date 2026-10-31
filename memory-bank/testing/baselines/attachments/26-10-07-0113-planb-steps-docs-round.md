# 2686 —— tracker URL 源头脱敏: 方案B 分步实施计划产出轮(纯文档, 未入库)

> 摘要: 把可行性报告 26-09-22-1801 的方案 B(单轨 + 瞬时原文 + mask 形态)转成 S1–S4 分步实施计划
> (`memory-bank/plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html`), 并立档 `tasks/26-10-07-webui-tracker-url-sanitize.md`
> + 更新 activeContext 切片 + 旧计划档回写(doc-refs/状态修正)。**本轮零代码改动**, 数字与上一条的
> 差异全部来自开工前 sync 带入的远端提交(e2e 迁移收尾等)。基线时间: 2026-10-07 01:13。

**Refs:** memory-bank/activeContext/26-09-23-1915-tracker-url-source-sanitize.md

- 分支: develop @ **20bd2157**(开工 `commands run my-commit-flow.sync` = 远端领先 14 笔快进
  `779cf088→20bd2157`; 本轮产物未入库, 待用户说「提交」)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2686 passed + 4 skipped, 覆盖率 TOTAL 99%**; pytest 自报 **38.69s**。
  语句 **15823** / 未覆盖 **163** / 分支 **5472** / partial **143**。
- 相对上一条 [26-10-06-2027](26-10-06-2027-webui-esc-order-history-first.md)
  (2682 + 4 / 16021 / 163 / 5472 / 143): 未覆盖 / 分支 / partial **三项逐位相同**; passed +4、
  语句 −198 全部来自 sync 带入的远端改动(本轮未碰 `src/`)。
- 本轮过程记录: 首跑曾被 `test_new_artifact_naming` 判红——新件命名协议(26-09-24 起)要求
  **type token 在前**(`YY-MM-DD-HHMM-plan-<topic>.html`), 首拟名 `-planb-steps.html` 缺 type token;
  已改名 `26-10-07-0055-plan-tracker-url-sanitize-planb.html` 并同步全部引用后重跑全绿。
  `kb.docmap --check`: 471 份文档 / 255 专题, 主键与认领链双向闭环 OK。

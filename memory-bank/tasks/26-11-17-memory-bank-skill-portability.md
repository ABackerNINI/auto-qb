# 26-11-17-memory-bank-skill-portability — 自制 skill 轨道可移植性改造

**Status:** In Progress
**Added:** 2026-11-17
**Updated:** 2026-11-17
**Summary:** 自制 skill 轨道可移植性改造
**Topics:** memory-bank-skill-portability
**Refs:** memory-bank/plans/26-11-17-0010-plan-skill-portability.html, memory-bank/reports/26-11-17-0010-report-skill-portability.md

## 本篇只回答

自制 skill 轨道(skill 目录 + commands 引擎 + `.commands/` 包 + sync 脚本 + KB 数据件骨架 + PORTING)的可移植性改造: 改造方案与执行进度到哪了。方案与拍板单点在计划, 摩擦证据单点在收编报告 —— 本篇只记「怎么修、修到哪」。

## 原始请求

1. 自制 skills 的可移植性改造: skills 需要尽量通用, 理论上移植后不需要修改 skills 本身(表述/代码等), 只需要修改配置。
2. `PTSKIT-farm-helper` 中包含一次真实移植示例, 其 `docs/skill-portability-report.md` 可做参考。
3. grilling 然后出一个可移植性改造计划。
4. (grilling R1) 报告收编: 用户授权 copy 进本仓。
5. (grilling R3/R4) 每个 skill 需要有一个移植帮助文档; 帮助文档中需要对新项目/正在开发中的项目做移植指导, 特别是后者; 配置/帮助文档放相应子目录, 不放 skill 根目录。

## 思考过程与决策

- 四轮 grilling(D1-D20)全部拍板, 结论表与依据单点: `memory-bank/plans/26-11-17-0010-plan-skill-portability.html` §06。
- 关键口径: 改造单位=轨道级(报告 §2.6-1 实证一半工作量在 skill 外); 配置分散自管+宽容回落; fail-closed 守卫摘默认链改显式挂载; red_lines 升级 glob; review_lane 留包内做纯数据外置(支持存量评审); 每 skill 一份 `references/PORTING.md`(双场景, 重点存量项目); 验收五条全收, 场地=仓内沙箱(跨仓红线零消耗)。
- 本轮(立档轮)零代码改动: 报告收编(D6)+计划入库+本档案; S1-S11 未开工。

## 实现计划

计划 `26-11-17-0010-plan-skill-portability.html` §04 三波次 S1-S11(每步验收判据见计划, 此处不重抄):

- 波次 1 (P0 防复发): S1 memory-bank 配置化 / S2 锚守卫摘链+空库恒绿审计 / S3 全包 rmtree 复核。
- 波次 2 (P1 降手工): S4 红线 glob 化 / S5 PORTING 轨道 runbook / S6 配置模板四件+数据件骨架三件 / S7 review_lane 数据外置 / S8 每 skill PORTING.md / S9 sync 配置化。
- 波次 3 (P2 机械面+收口): S10 出厂配置环境中立 / S11 沙箱重放+grep 白名单审计收口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 报告收编+grilling 拍板+计划入库 | Done(2026-11-17) |
| S1 | memory-bank 配置化(config/project.toml + 宽容回落) | Open |
| S2 | 锚守卫摘链+kb.check 空库恒绿全链审计 | Open |
| S3 | 全包 rmtree/unlink 复核 | Open |
| S4 | red_lines/warn_lines glob 化+存量迁移审计 | Open |
| S5 | PORTING 升级轨道 runbook(双场景, 重点存量) | Open |
| S6 | 出厂配置模板四件+数据件骨架三件 | Open |
| S7 | review_lane 数据外置 lane.toml(存量评审开箱) | Open |
| S8 | 每 skill references/PORTING.md | Open |
| S9 | sync 配置化(.config/sync.toml) | Open |
| S10 | 出厂配置环境中立(uv→python3) | Open |
| S11 | 沙箱重放+grep 白名单审计收口 | Open |

## 进度日志

### R0 · 立档 (2026-11-17)

- 开工同步: 远端领先 77 笔, 快进 dbfed3b4→2e2ffe1f。
- 盘点: 收编报告 §2 改造清单在本仓基本零落地(逐项核实见计划 §02); T4 rmtree 主案已修(33e3a3d6)。
- 报告收编: 经用户授权拷入 `memory-bank/reports/26-11-17-0010-report-skill-portability.md`(直拷 .md+来源注记, D8)。
- 四轮 grilling D1-D20 拍板全记录; 计划 `26-11-17-0010` 入库(Open); 本档案立档。
- 零代码改动, 未入池 issue(演进史下沉缓行待实施开工轮入池, R-6), 本轮产物随本专题入库。
- review 三轮(全能档 1 子代理连续派遣, 322 行): 11 发现(1 major/7 minor/3 nit)检 11/11 过零弃, 修 10 零入池, 1 nit 不阻塞留痕(R 符号一行三义, 版次/评审轮/grilling 轮各处有先行词可消解) —— R1 修 6(半自制口径对齐/kb uv run 例证/轮次计数/S6 补 kb 包模板/D15 Windows 场地声明/引证 §2.6-1); R2 修 4(D2 拆面表述/§03 S6 子项数/33e3a3d6 定语改锚定防呆守阵/修正轮次 R2+R4); R3 验证 4 修未回退+R1 行自洽。计划改版留痕经 kb.bump R1 行(doc-updated 0042)。

- 2026-11-17 00:14 grilling 四轮 D1-D20 拍板 + 计划 26-11-17-0010 入库(Open, 三波次 S1-S11 待显式开工) + PTSKIT 移植摩擦报告授权收编 + 档案立档; 零代码改动

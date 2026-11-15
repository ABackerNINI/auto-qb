# 26-11-15-webui-drawer-tooltip-prune — WEBUI 种子详情 tooltip 清理

**Status:** In Progress
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** WEBUI 种子详情 tooltip 清理: 重复/低价值移除(46 源), 文案手术 6, 增量/长文本保留(112 挂点), 静态守阵收口
**Topics:** webui-drawer-tooltip-prune
**Refs:** memory-bank/plans/26-11-15-0717-plan-webui-drawer-tooltip-prune.html

## 本篇只回答

本专题怎么做: 种子详情抽屉面 tooltip 的清理方案、拍板账(D1-D13)与实施状态; 逐挂点移除/保留清单单点在计划 §04。

## 原始请求

1. 「WEBUI种子详情模板tooltip清理: 部分tooltip只是重复信息没有价值, 除了长文本tooltip防止原元素过长导致被裁剪的, 其余的重复/低价值tooltip一律移除」
2. 「grilling然后出一个计划,包含哪些要移除,哪些保留」

## 思考过程与决策

- 只读取证先行: 全站 title 由 ui_feedback.js 单向迁 data-aq-tip(.aq-tip); 扫描面 157 模板挂点(drawer_tpl 84 / 壳层 7 / 空帧 1 / xtpl-cells-dt 52 / peers 段 13)+ JS 载荷 7(dt04/05 tracker 统计格); 测试面排雷(e2e 仅钉 dt10:311、静态守阵钉空帧 esc, 均在保留面)。
- grilling 两轮 13 问全按推荐拍板(D1-D13): 范围=全抽屉面+引擎单元格面; 字段名/自指/复述/色彩自述/实现细节句/纯折叠提示 → 移除 46 源(模板 41 + JS 载荷 5); 内部计划编号(P-04/P-02)与 num_xxx: 前缀 → 文案手术 6(解释正文保留); 长文本/数据承载/语义增量/图标钮 a11y → 保留 112; 静态守阵钉零回潮(D13)。
- 关键取舍: 引擎文件只动抽屉专用段(dt 单元格 + peers 段), 主视图零牵连; 复述与增量的分界逐点核(如 dt07 IPv6 移 / 加密 uTP 内网留; dt10 复述三条移 / 有源可补、保留数据两条留)。
- 计划: memory-bank/plans/26-11-15-0717-plan-webui-drawer-tooltip-prune.html(Open, 即冻结执行版)。

## 实现计划

S1-S5 见计划 §04 步骤分期表: S1 通用面字段名/自指/折叠(dt01/02/03, 30 处) → S2 通用面其余(dt04 pills/dt05 fold/dt07+dt08 手术/dt10 复述/dt11 机制句, 7 处) → S3 tracker+engine 面(9 处) → S4 静态守阵(黑名单+手术新串+保留抽查) → S5 回归验收(test.quick → e2e drawer 五 spec → test.full + 新基线切片 → 四皮肤真机目检)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 取证 + grilling 两轮拍板 D1-D13 + 计划/档案立档 | Done(2026-11-15) |
| S1 | dt01/dt02/dt03 移除 30 处 | Open |
| S2 | dt04/dt05/dt07/dt08/dt10/dt11 移除 7 处 + 手术 2 处 | Open |
| S3 | tracker JS 载荷 + xtpl-cells-dt 移除 9 处 + 手术 4 处 | Open |
| S4 | 静态守阵(黑名单/手术新串/保留抽查) | Open |
| S5 | 回归验收 + 新基线切片 + 四皮肤真机目检 | Open |

## 进度日志

### R0 · 立档 (2026-11-15)

开工同步(2fe93ed8→b03dbbdf 快进); 只读取证(挂点全扫, 补发现引擎单元格面 52+13 挂点与 JS 载荷 7 处); grilling 两轮 13 问, 用户逐轮「按推荐」拍板 D1-D13; 计划 26-11-15-0717 入库(Open)+ 本档案立档。本轮零代码改动、零 commit; S1-S5 待显式开工。

- 2026-11-15 08:18 grilling 两轮 13 问拍板 D1-D13 全按推荐 + 计划 26-11-15-0717 入库(Open, 移除46源/手术6/保留112挂点) + 档案立档; 零代码改动, S1-S5 待显式开工

- 2026-11-15 08:47 评审 3 轮收敛: 轮1 九发现(2major+6minor+1nit, 聚合双计51→46/107→112+补列dt02:257+九件/表头口径)全修过检9/9; 轮2 复验无回退+新发现S4残留51已修(先修后检被机械REFUTE留叙事); 轮3 零发现; 检9/10 修9 入池0; 提交入库

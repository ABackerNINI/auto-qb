# 26-10-20-webui-menu-label-unify — WEBUI右键菜单文案统一:动词+灰色种子计数

**Status:** In Progress
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** WEBUI右键菜单文案统一:动词+灰色种子计数
**Topics:** webui-menu-label-unify
**Refs:** memory-bank/plans/26-10-20-0145-plan-webui-menu-label-unify.html, memory-bank/issues/26-10-20-0148-test-webui-ctx-menu-left-edge.html

## 原始请求

> 用户(2026-10-20 01:21): 「WEBUI 启动该种子/批量启动/启动整组, 几种不同的叫法需要统一, 初步想法: 统一改为启动, 后面跟灰色描述"x个种子". 停止/删除菜单类似; grilling」

诉求拆解:
1. 启动/停止/删除三族动作在右键菜单里的多种叫法需要统一;
2. 用户给的初步形态: 动词 + 灰色「x个种子」计数描述;
3. 显式要求 grilling(设计决策逐条烤问)后再动。

## 思考过程与决策

- **请求边界判定**: 本轮 = grilling 讨论 + 出计划(Q&A/计划轮); 实施(改生产文件)是下一轮, 须用户对计划拍板后开工。
- **grilling 两轮 13 问(D1–D13)全部按推荐拍板(2026-10-20)**: 五处菜单变体全收(含整剧/整集, D1); toast 同轮同形(D2); N=实际受作用种子总数(D3); N=1 不特例(D4); 打开时快照+权威选择(D5); 确认框构成分解保留+底层计数单点(D6); 强制重新汇报/检查、更多操作状态开关、快捷键面板不动(D7); 测试/文档同轮闭环+先出 plan 再动手(D8); e2e scope 断言改挂 data-kind/data-count(D9); selTargets() 收口 selection.js + ctxScopeCount() 模板方法四分支收敛(D10); 后缀格式各按既有先例(D11); .ctx-note 新类三皮肤各加(D12); 不新增 clamp+左缘缺口入池不修(D13)。完整结论表见计划 §06。
- **关键取舍**:
  - 计数单位取「种子总数」而非「选择构成」——动作原子对象永远是种子, HR/带宽风险按种子计; 构成分解留给删除确认框(信息更全且是最后一道防线);
  - 计数单点用既有 delete_flow 的「权威选择」口径(selGroups/selMembers), 不新造数据源——该口径有既有实现与注释背书, 且符合 doc-forms「每条事实只在一个工位有权威」;
  - 测试挂 data 属性而非继续挂文案——文案统一后四支菜单可见文案趋同, 挂属性才能保住 scope 契约; :data-xxx 是本仓成熟范式(groups/torrents/drawer 先例)。
- **词汇线定位**: 动词(启动/停止)本身是 2026-10-10 webui-wording-unify 专题对齐 qB GUI 的产物; 本轮统一的是动词后面的 scope 修饰词与计数, 是同一词汇线的下半场, 不重复该专题。
- **blow radius 已核**: e2e 六 spec 按精确文案断言(改即红); Python 守阵均为结构断言(原理上不破); conventions/webui.md:10 自身术语漂移(「开始/暂停」, 操作栏 2026-10-05 已退役)。

## 实现计划

单波次 S1–S9 顺序执行, 每步独立可验(完整落点/证据/验收判据见计划 §04):

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | selection.js 新增 selTargets()(自 commands.js _bulkTargets 迁移); commands.js 改调用 | Open |
| S2 | ctxScopeCount() 模板方法四分支计数; 容器绑 :data-kind/:data-count | Open |
| S3 | ctx-menus.html 15 处文案改写 + `<span class="ctx-note">` 后缀 | Open |
| S4 | 三皮肤 CSS 新增 .ctx-note(11.5px + --fg-muted) | Open |
| S5 | toast 同形: _actCore what/countSuffix 参数化; shows.js:106-107 同改 | Open |
| S6 | delete_flow.js bulkCountText 改从 selTargets() 派生(构成式保留) | Open |
| S7 | e2e 六 spec: scope 断言改挂 data 属性 + 形态正则 | Open |
| S8 | 文档: webui.md:10 术语行修正 + 补菜单动作文案口径约定 | Open |
| S9 | 全量: test.full + e2e; kb.new baseline 誊实测数字 | Open |

## 进度日志

### R0 · 立档 (2026-10-20)

- 开工同步: 快进 e6429cfe→d2f6d993。
- grilling 两轮 13 问全部拍板(按推荐); 事实核查两轮(菜单五变体清点 / 实施面核查: 水平 clamp 已有两级、data-* 范式先例、strip-note 规格、bulkCountText 单点候选、e2e/Python blast radius)。
- 产出: 计划 `26-10-20-0145-plan-webui-menu-label-unify.html`(Open, 待用户过目); 左缘测试存量缺口入池 `26-10-20-0148-test-webui-ctx-menu-left-edge`(Open, D13: 不在本计划修)。
- 下一步: 用户过目计划并拍板 → 实施轮按 S1–S9 执行。

- 2026-10-20 01:51 grilling两轮13问全部按推荐拍板; 计划26-10-20-0145-plan-webui-menu-label-unify落盘(Open待用户过目); 任务档案立档(S1-S9全Open); 左缘测试存量缺口入池(test/light/Open, D13不顺手修); 本轮未动任何生产文件

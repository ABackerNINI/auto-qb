# 26-10-20-webui-menu-label-unify — WEBUI右键菜单文案统一:动词+灰色种子计数

**Status:** Done
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** 四支右键菜单的 启动/停止/删除 文案统一为「动词 + 行内灰色 N 个种子」(scope 词 批量/该种子/整组/整剧/整集 全部退场), toast 回执同形「已执行: 动词(N 个种子)」, 删除确认框的构成分解保留; N = 实际受作用种子总数, 计数单点 `selection.js::_seedCountOf` 派生到菜单后缀 / 确认框 / 回执三处。grilling 两轮 13 问按推荐拍板后出计划, 实施轮撞上游 W1–W3 把菜单改成注册表驱动, 决策不变只换落点(12 项 label + `note` 字段); 测试挂点从文案迁到 `data-kind`/`data-count`/`data-item`。验证: test.full 3769 passed(98%)+ dev.e2e 322 passed。
**Topics:** webui-menu-label-unify
**Refs:** memory-bank/plans/26-10-20-0145-plan-webui-menu-label-unify.html, memory-bank/issues/26-10-20-0148-test-webui-ctx-menu-left-edge.html, memory-bank/testing/baselines/26-10-20-0403-webui-menu-label-unify.md

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

单波次 S1–S9 顺序执行, 每步独立可验(完整落点/证据/验收判据见计划 §04)。

**实施轮开始时的落地位置修正(2026-10-20 03:30)**: 提交方案后同步进来远端 8 笔(W1–W3),
`ctx-menus.html` 已 v-for 化、标签全部搬进 `shared/ctx_menu.js` 注册表, 作用域解析已由
`selection.js::_scopeResolve` 收口(契约 C1)—— 原 S1「新建 selTargets()」与 S3「模板 15 处改写」
的挂点整体位移。**决策不变(D1–D13 全部照旧), 只换落点**: S1 退化为"补一个种子基数函数复用
C1 单点", S3 改为"注册表 label + note 字段"。计划本身不重写, 差异记在 §07 变更记录与本节。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 计数单点: `selection.js::_seedCountOf(keys, hashes)`(复用 C1 `_scopeResolve` 描述符, 组展开去重) | Done |
| S2 | `menu.js::_ctxScope/ctxMenuKind/ctxSeedCount`; 模板容器绑 `:data-kind` / `:data-count` | Done |
| S3 | 注册表 12 项(四支×启动/停止/删除)label 统一 + `note` 灰色后缀; 模板渲染 `.ctx-note` + `:data-item` | Done |
| S4 | 三皮肤 `.ctx-note`(并入 `.strip-note` 同一条声明, 规格逐字同源) | Done |
| S5 | toast 同形: `_actCore` 收掉 `what`/`countSuffix`, 恒 `已执行: 动词(N 个种子)`; shows.js 同改 | Done |
| S6 | 删除确认框: `bulkCountText` 已走 C1 投影(W3 前既有), 核验无第二套计数 | Done |
| S7 | e2e 五 spec + 手势库: scope 断言改挂 data 属性, 点击改挂 `data-item` | Done |
| S8 | 文档: `conventions/webui.md` 术语行修正 + 补「动词 + 灰色种子数」口径约定 | Done |
| S9 | 全量: `test.full` 3769 passed + `dev.e2e` 322 passed; 基线切片 `26-10-20-0403` | Done |

## 进度日志

### R0 · 立档 (2026-10-20)

- 开工同步: 快进 e6429cfe→d2f6d993。
- grilling 两轮 13 问全部拍板(按推荐); 事实核查两轮(菜单五变体清点 / 实施面核查: 水平 clamp 已有两级、data-* 范式先例、strip-note 规格、bulkCountText 单点候选、e2e/Python blast radius)。
- 产出: 计划 `26-10-20-0145-plan-webui-menu-label-unify.html`(Open, 待用户过目); 左缘测试存量缺口入池 `26-10-20-0148-test-webui-ctx-menu-left-edge`(Open, D13: 不在本计划修)。
- 下一步: 用户过目计划并拍板 → 实施轮按 S1–S9 执行。

- 2026-10-20 01:51 grilling两轮13问全部按推荐拍板; 计划26-10-20-0145-plan-webui-menu-label-unify落盘(Open待用户过目); 任务档案立档(S1-S9全Open); 左缘测试存量缺口入池(test/light/Open, D13不顺手修); 本轮未动任何生产文件

### R1 · 实施 (2026-10-20 03:30–04:10)

- **用户指令**: 「提交后实施, 全部实施完毕后再提交」→ 方案轮 KB 制品先提交(`df92f785`), 再实施, 全部完成后第二次提交。
- **开工即撞上游改写**: `ship.commit` 内部同步合流远端 8 笔(W1–W3 右键菜单定制 + 设置页卡), `ctx-menus.html` 已 v-for 化、标签搬进 `shared/ctx_menu.js`、作用域解析已由 `selection.js::_scopeResolve` 收口(C1)。**决策 D1–D13 一条未改, 落点整体位移**, 差异逐条记在计划 §10 R1。
- **实际落点**(S1–S9 完成):
  - 计数单点 `selection.js::_seedCountOf`(复用 C1 描述符, 组展开去重; 不新建 `selTargets` —— 上游已让 `_bulkTargets` 变成 C1 的投影);
  - `menu.js::_ctxScope/ctxMenuKind/ctxSeedCount`; 模板容器绑 `:data-kind`/`:data-count`(取值用注册表分支名 multi|episode|member|group —— 放弃了 D9 原文的 `single`, 理由: 同一批四个分支不该有两套词表);
  - 注册表 12 项(四支×启动/停止/删除)label 改动词 + 新 `note` 字段; 模板渲染 `.ctx-note`, 且用 `.ctx-text` 把标签与后缀圈成同一个 flex 项(否则吃 `.ctx-item` 的 9px gap, innerText 也会被拆开);
  - `.ctx-note` 三皮肤并入 `.strip-note` 同一条声明(atlas 已顶 700 行单文件上限, 共用声明零增行且规格不可能漂);
  - toast 同形: `_actCore` 收掉 `what`/`countSuffix`, 恒 `已执行: 动词(N 个种子)` / `动词失败: …`, 四个调用点删参; `shows.js::actEpisode` 同改;
  - e2e 五 spec + 手势库: scope 断言改挂容器属性, 动词项点击改挂 `:data-item`(`ctxItemById`), `pausableRow` 去掉文案参数;
  - 注册表守阵 ⑫ 改口径 + 新增 ⑭ 段(四支 12 项后缀齐、其余项无后缀、分隔线 note 恒空);
  - 文档: `conventions/webui.md` 术语行修正 + 新增「动作文案口径 = 动词 + 灰色种子数」约定(含 scope 词禁令、N 的定义、三处同源、排除项)。
- **验证**: `test.quick` 3769 passed(首跑撞到本档案自身缺 `## 子任务状态表` —— 上一轮立档漏章节, 已补); `dev.e2e` 322 passed / 10 skipped(11.0m); `test.full` TOTAL 20362 · 98%, 3769 passed / 10 skipped; 基线切片 `26-10-20-0403`。
- **顺手核过未改**: `delete_flow.js::bulkCountText` 早已走 `_bulkTargets`(C1 投影), 无第二套计数(S6 由"改"降为"核"); 删除确认框标题/构成分解按 D6 保留; 限速/移动的「N 个目标」回执不属本轮口径(D7)。

- 2026-10-20 04:04 实施轮完成 S1-S9(落点随上游 W1-W3 位移到注册表): 12 项 label+note、ctxSeedCount/_seedCountOf 计数单点、data-kind/data-count/data-item 测试挂点、toast 同形、三皮肤 .ctx-note；e2e 五 spec 改挂点; test.full 3769 passed(98%)+dev.e2e 322 passed; 计划与档案翻 Done, 基线 26-10-20-0403

# 26-10-21-webui-drawer-variant-renderer-dup — 抽屉变体渲染器族三族重复收敛: 三态空帧单点 + peers 判据共用 + dt 值格模板合一 (issue 26-10-20-2231 认领修复)

**Status:** Done
**Added:** 2026-10-21
**Updated:** 2026-10-22
**Summary:** 抽屉变体渲染器族三族重复收敛: 三态空帧单点 + peers 判据共用 + dt 值格模板合一 (issue 26-10-20-2231 认领修复)
**Topics:** webui-drawer-variant-renderer-dup
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-drawer-variant-renderer-dup.html, memory-bank/testing/baselines/26-10-22-0039-webui-drawer-variant-renderer-dup.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-20-2231-refactor-fe-drawer-variant-renderer-dup.html」——
   用户显式指派认领(create-issue skill 的「用户指派」口径), 同时授权修复这一件。
2. 开工同步 `my-commit-flow.sync`: 首跑被脏树挡路(上一轮 busy-skeleton 完工物未入库 + 远端
   领先 13 笔且同改 dialogs.js) → stash 保命 → 快进 95baf46b→8f39b625 → apply 后解两处
   dialogs.js 冲突(_mgrRun 单点 × 远端 mgrNew.* 改名合并) + 重生两索引 → test.full 全绿
   (3982 passed / 10 skipped / 99%)。旧完工物保持未入库(stash@{0} 留底)。
3. 收尾按 AGENTS.md DoD: 全量测试 + 基线切片 + issue 状态流转 + 索引重建。用户**未**说「提交」,
   本轮不 commit / 不 push。

## 思考过程与决策

**复验(改前, 以同步后 8f39b625 为准)**: issue 三族锚点逐处重读源码 ——
① 三态空帧: 04-12 九件桥变体各手抄「加载态(沙漏+正在加载…)/ 错态(警告+err title)/
空态(纯文案)」三块 + 整帧替换, 27 块除槽类名(dt04-empty…dt12-load)与文案外逐字同;
**general 三件无三态**(仅 `!d` 裸 `replaceChildren()` + lastSig 记账, 形状不同)——
入池记录「general 三件各 1 次」指的是其整帧换帧那一次(已走 H.withScroll), 非三态块。
12 号件换帧点实测 5 处(比入池记录多 1, 第 5 处是 treemap 的 mapEl 独立换帧, 非态块)。
② peers 判据: 07/08/09 的 FLAG_META / flagTokens / isBad / bucketOf / isLanIp 五件
(四件 + bucketOf 依赖的 flagTokens)程序化 diff 三份逐字同; BUCKETS/FILTERS(07≠09 多
hand 档)/flagHas/clientName/countsOf 为变体私有不动。
③ dt 值格: dt07 与 dt08 逐字同(仅 CSS 前缀), dt09 差在三处(无 files 列/占用条/
dlspeed 平铺)——issue 记「仅 upspeed 一处特化」略保守, 实为 upspeed+dlspeed+files 三处。

**决策 1 · ①族落 `H.emptyFrame`(reg.helpers), 只收 9 件桥变体的 27 块**: helper 认
`{cls, has, loading, err, errText, emptyText}` 六个参, `has` 为真直接返 false(调用方继续
整帧), 否则按 loading→err→empty  precedence 渲槽并返 true(调用方 return) —— 与原三块
if 的判定序和 `!length` 合并语义逐位对齐; err 进 title 走 esc(与 dtHtml 插值同口径)。
general 三件的裸空态刻意不入(无槽无文案 + lastSig 复位是变体记账, 强入要加 clear 特例)。

**决策 2 · ②族落 `reg.peers` 命名空间(drawer_templates.js), 不新建清单文件**: helpers/
kit 同款先例(变体层共用单点都住核心文件), 零 manifest  churn(新文件要改三皮肤 index.html
且过装载序守阵); TPL_REG 按文件既有约定「先建局部量再引用」书写(防 _scan_mixin_wiring 误判)。

**决策 3 · ③族一份 x-template + pfx/occ 两 prop, 组件名不动**: 组件名由描述符 rowModel
动态拼出(`'aq-' + rowModel + '-cells'`), 保留三个组件名 = app.js 注册行/skins 守阵组件
清单/DEFS 全不动; 三组件共享 `#tpl-aq-dt-peer-cells`, pfx 默认值各表自己(dt07/dt08/
dt09), occ 仅 dt09  true —— 类名渲染结果与旧逐字同(不撞三皮肤 CSS), dt09 的 files 死
分支无害(其列模型 9 列无 files, 且 _colsOmitEmpty 已废)。CSS 计算用数组形式保 dt09 的
`z` 类落点(div 上)与 dt07 的 `<b>` 包裹差异。

**决策 4 · skins 守阵⑨同步改口径**: 原守阵要求三份分片在册且各含 9 键分支 —— 合一后改为
「单一 tpl-aq-dt-peer-cells 覆盖三变体列键并集(10 键)」, 保护意图不减反增(加列漏分支 =
三变体齐空白, 一把守全盯)。

## 实现计划

1. 核心: HELPERS 加 emptyFrame; TPL_REG 加 peers 命名空间(五件判据)。
2. 07/08/09: 删本地判据副本, 改 `const P = reg.peers` 消费(含 07 的 flagHas/countsOf 内部引用)。
3. 04-12: 27 个三态块 → 9 个 emptyFrame 调用(文案/类名逐件誊)。
4. xtpl-cells.html: 三份 dt 模板合一(prefix/occ); table.js: 三组件共享模板+各自默认 prop。
5. skins 守阵⑨改并集口径; dom_panel 加新守阵(emptyFrame 在册+9 接线+判据单点+无本地副本反向断言+dt 模板合一), 文件头测试计划同步。
6. node --check 全改 js; 新守阵 + 相关 python 单测; e2e peers 三 spec; test.full + 基线切片。
7. 收尾: issue 置 Done(含改道说明) + 索引重建 + 档案进度 + kb.wrap。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 复验三族锚点(含 general 无三态/12 号 5 处/five 件判据面) | Done(2026-10-21) |
| S2 | 核心: emptyFrame + reg.peers | Done(2026-10-21) |
| S3 | 07/08/09 判据副本删除改单点消费 | Done(2026-10-21) |
| S4 | 04-12 三态块收敛为 emptyFrame 调用 | Done(2026-10-21) |
| S5 | dt07/08/09 值格模板合一 + 三组件 prop 化 | Done(2026-10-21) |
| S6 | 守阵(skins⑨改口径 + dom_panel 新守阵) + 红验 | Done(2026-10-21) |
| S7 | e2e + test.full + 基线切片 | Done(2026-10-22) |
| S8 | issue Done + 索引 + 档案 + kb.wrap | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-21)

- 认领 issue 26-10-20-2231(用户指派「认领并修复」), 开工同步解脏树(旧 busy-skeleton 完工物
  stash 保命后快进 13 笔, dialogs.js 两冲突以「_mgrRun 单点 × mgrNew.* 改名」解法重组,
  test.full 3982 passed 全绿), 复验三族锚点在位。

### R1 · 三族收敛完成 + 守阵红验 (2026-10-21)

- 核心层(drawer_templates.js): HELPERS 加 emptyFrame(has 闸 + loading→err→empty 优先级,
  err 进 title 走 esc); TPL_REG 挂 peers 命名空间(FLAG_META/flagTokens/isBad/bucketOf/
  isLanIp 五件, 按文件约定先建局部量再引用)。
- 07/08/09: 删判据本地副本(五件逐字同实锤), 改 `const P = reg.peers` 消费; 07 私有的
  flagHas/clientName/countsOf/BUCKETS/FILTERS 留件内。
- 04-12: 27 个三态块 → 9 个 emptyFrame 调用(槽类名/文案逐件誊, 判定序与 !length 合并
  语义住在 helper); general 三件裸空态形状不同刻意不收编。
- xtpl-cells.html(356→310 行): dt07/08/09 三模板合一为 tpl-aq-dt-peer-cells, 类名经
  pfx prop 计算(渲染结果与旧逐字同), dt09 特化(占用条/dlspeed 平铺)经 occ prop;
  table.js 三组件同名不变共享模板, pfx/occ 默认值各表自己。
- 守阵: skins⑨改「单一模板覆盖三变体列键并集」口径; dom_panel 新增
  test_drawer_variant_skeleton_single_point(三族单点在册 + 9 接线 + 判据无本地副本 +
  模板合一 + general 钉 0), 文件头测试计划同步; 三处破坏红验(05 接线改名/08 本地 isBad
  复活/旧模板 id 回潮)全部命中即红, 还原后复绿。
- 验证: dom_panel+dom_page 86 passed、skins 23 passed; e2e 定向子集 94 passed
  (peers-columns/variant-tables/sticky-flush/dt-table-face-bg/layout-parity/bridge-stub/
  content-dt11-sticky/drawer-peers/switch-no-flash, 3.1m + 31s)。
- test.full(88.8s): 3983 passed / 10 skipped / 覆盖率 99%(上一轮重组后 3982, +1 = 本轮新增
  守阵函数被计入)。契约事实回写 memory-bank/modules/webui-static-contract.md(P6 条目后
  新增「三族重复收敛」条)。
- 待办: e2e 全量(后台 GXIyCS 进行中) → 基线切片 → issue Done + kb.wrap。

### R2 · 收尾 (2026-10-22)

- e2e 全量: 336 passed / 10 skipped(11.6m) —— 与上轮基线逐位持平(验收口径即「类名渲染
  结果与旧逐字同」, 数字不动是预期, 非漏测)。
- 基线切片: testing/baselines/26-10-22-0039-webui-drawer-variant-renderer-dup.md
  (test.full 3983 passed / 10 skipped / 99% 实测誊写 + e2e/定向/红验口径注记 + 改动面表)。
- 契约回写: modules/webui-static-contract.md P6 条目后新增「抽屉变体渲染层三族重复收敛」条。
- issue 26-10-20-2231 置 Done(2026-10-22 00:41), 状态日志含改道说明(general 不收编 /
  判据五件 / dt09 三处特化 / 12 号 5 处)。
- 用户未说「提交」: 本轮改动 + 上一轮 busy-skeleton 完工物均留在工作区未入库,
  stash@{0} 保留作安全网。

- 2026-10-22 00:43 认领并修复 issue 26-10-20-2231: 抽屉变体渲染层三族重复收敛 —— ①27 块三态空帧骨架入 drawer_templates.js::HELPERS.emptyFrame 单点(9 件桥变体各一处接线, general 三件刻意不收编); ②07/08/09 五件 peers 判据(FLAG_META/flagTokens/isBad/bucketOf/isLanIp)逐字副本提为 reg.peers 命名空间, 删本地副本改单点消费; ③dt07/08/09 三份 x-template 合一为 tpl-aq-dt-peer-cells, 接 pfx/occ 两 prop 且不改 CSS 类名, 渲染结果与旧逐字同。守阵 dom_panel 新增 test_drawer_variant_skeleton_single_point + skins⑨ 改并集口径, 红验三支命中即红; test.full 3983 passed/10 skipped/99%, e2e 全量 336 passed/10 skipped 逐位持平; issue 置 Done, 契约回写 webui-static-contract.md, 基线切片 26-10-22-0039 已建。工作区未提交(用户未授权)。

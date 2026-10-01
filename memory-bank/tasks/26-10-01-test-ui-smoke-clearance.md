# 26-10-01-test-ui-smoke-clearance — issue 0602 双案清偿: 冒烟列宽守阵选键 + CTX-03 多选落点

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01 19:42
**Summary:** 同一认领清偿两条 26-09-30-0602 UI 冒烟失败。A(隐藏列宽度保留): 定性为用例选键缺陷 —— 2026-09-28 辅种扩列加 hide:true 默认隐藏列后 colHidden[0] 常驻 amount_left, 从未固化过意图宽度, 读不回是双轨模型正确行为; 修 harness 改为隐藏前直取 _visibleCols[2].key, prism 实测 key=upspeed 前=后="88px" 转绿。B(CTX-03 多选): 定性为 harness 落点缺陷 —— 行几何中心被行内 .site-chip(@click.stop=按站点筛选, 设计行为)占据, 修饰键点击被芯片吞掉到不了行 handler; 排除 ElementHandle 脱挂(节点 24/24 存活)与真实 UI 缺陷(改落点后语义不变)。B 修复随第二笔提交。
**Topics:** test-ui-smoke-clearance-issue-clearance
**Refs:** memory-bank/issues/26-09-30-0602-test-ui-smoke-colwidth-hidden-preserve.html, memory-bank/issues/26-09-30-0602-test-ui-smoke-ctx03-multiselect.html

> 背景关联(不进机器认领链): 本任务是 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 第 4 条, W1 最后两条真红; 用户已显式授权实施 W1 且「每个 issue 修完后单独提交」。

## 原始请求

实施 issue 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W1 波次第 4 个工作包: 两条 26-09-30-0602 UI 冒烟失败同一认领一起查。要求: 先复现、再定性、再修; B 必须区分「harness 竞态(ElementHandle 被轮询重渲染作废)」与「真实 UI 缺陷(Ctrl+click 在真实链路真不生效)」, 若定性非缺陷则停手; 认领链一条档案同时 Refs 两条 issue、issue 报告 doc-refs 双向回指; 改动只限两条 issue 范围; 每个 issue 修完单独提交。

## 思考过程与决策

- **复现(2026-10-01 19:30)**: `commands run my-commit-flow.sync` 同步 9486a7cd 后, 起 `scripts/ui_harness.py --port 8139` 桩服务 + `node scripts/ui_smoke.cjs --base http://127.0.0.1:8139 --ui prism`: 三条 FAIL 与 issue 记录逐字一致 —— CTX-03 追剧集行(菜单单目标)/CTX-03 辅种组行(选中 0 组, 本轮间歇)/隐藏列宽度保留(key=amount_left 前=undefined 后="92px")。确定性复现成立。
- **A 定性(用例选键缺陷, 产品无缺陷)**: 仪器化探针 + 代码走读。`GROUP_COLUMNS` 自 2026-09-28 辅种扩列(plan 26-09-28-0354 档案)起给 amount_left/seeding_time/availability/ratio 加 `hide:true`, `loadColState` 空存储时按 hide 标志播种 colHidden —— 冒烟用例 `clearCols` 后 colHidden.group = ["amount_left","seeding_time","availability","ratio"], 用例再隐藏第 3 个可见列(upspeed)后取 `k = colHidden.group[0]` = amount_left, 而**固化只固化可见列**(startResize up 分支 `intent = {...colW, ...widths(可见), ...lastWidths}`), 默认隐藏列从未有过意图 px, `s1.w.group[k]` = undefined 是**双轨模型的正确行为**; 后="92px" 是 `toggleColumn` 显示分支按 `templateMinPx("minmax(92px, 1fr)")` 合成的默认意图(columns.js:408-414 注释即此语义)。issue §5 的候选假设(用例前置假设错误)成立, §6 方向一的前半句(改用例)成立, 「toggleColumn 隐藏分支升格」不采纳 —— 固化页可见列在拖拽时已全部升格, 自动页升格反而违反守阵 2(全自动页不落 px)。
- **A 修法(harness)**: 被隐藏列的 key 在隐藏**前**直取 `${INST}._visibleCols("group")[2].key`, 断言补 `s2.h.group.includes(k)` 防漏检; 断言语义升级为真正的守阵目标 —— "被用例隐藏的那一列"的意图 px 在隐藏→再拖→重显后原样回来。
- **B 定性(harness 落点缺陷; 排除 a 脱挂竞态与 b 真实缺陷)**: 仪器化探针(.workbuddy-ai/tmp/probe-ctx03.cjs, gitignored)在 document 捕获级记录 mousedown/mouseup/click 落点 + vm 方法覆写(onShowEpClick/onGroupClick/_toggleUnit)+ 行 DOM expando 存活检查 + $watch(selMembers/selGroups/kbCursor)。实测: ①ctrl#0 点击追剧集行 ep-1 的 mousedown/mouseup/click **全部落在行内 `.site-chip`**(722,551), onShowEpClick 未被调用(kbCursor 不变), 芯片 `@click.stop="filterFromChip('site',...)"`(tpl/shows.html:87)按设计吞掉事件; ctrl#1 落在 ep-2 行(芯片未盖住中心)正常选中 46 hash —— 右键 ep-1 时选择集不含 ep-1 → `_ctxMulti` inSel=false → 单目标菜单, 断言失败的每一环都是**选择根本没发生**, 不是菜单判据错。②辅种组行两次 ctrl+click 同样全落 .site-chip(tpl/groups.html:79 同款), 且附赠把 siteFilter 置 f-on —— 间歇性来自行 0/1 的芯片布局随前序步骤(成员 paused 状态文案/筛选 f-on)变化, 几何中心是否被芯片盖住随之漂移。③DOM 节点 24/24 存活(data-probe expando), ElementHandle 未脱挂, issue §5 假设 a 不成立; 修饰键路径在点击真正到达行 handler 时工作正常(孤立探针 + 本探针 ep-2 均证), 假设 b(真实缺陷)不成立。点击行内芯片触发"按站点筛选"是芯片自身的交互设计, 不改产品代码。
- **B 修法(harness)**: 两处 CTX-03 的 Ctrl+click 加 `position: { x: 8, y: 8 }` 落到行左缘名称列(g-name/g-name-text, 无任何 .stop 交互后代, tpl/groups.html + tpl/shows.html 核对), 真实修饰键路径(selection.js `_toggleUnit`/`toggleGroupSel`)不变; 右键不动(chip 无 contextmenu.stop, 冒泡到行, 实测一直正常)。
- **提交拆分**: 两案根因不同(选键 vs 落点)但同在 scripts/ui_smoke.cjs, 按用户口径分两笔: 第一笔 = A 修复 + issue A Done + 本档案(Refs 两条); 第二笔 = B 修复 + issue B Done + 档案状态翻 Done, 提交信息互指。

## 实现计划

- 档案认领(本文档, 一份 Refs 两条)+ 两份 issue 报告 doc-refs 回指。
- 修 A: ui_smoke.cjs 守阵 3 选键逻辑(隐藏前取 key)+ 断言补 includes。
- 修 B: ui_smoke.cjs 两处 CTX-03 Ctrl+click 落点改 (8,8)。
- 验证: 逐条 prism 冒烟转绿 → 双 UI 全量冒烟全绿 → `commands run test.quick`(认领链守阵 test_claim_chain_is_bidirectional 在内)。
- 清偿: 两份 issue 徽标+meta Done、状态变更日志、复验/修复后补充段、doc-refs; `commands run kb.index` + `uv run python .agents/skills/create-issue/scripts/gen_issues_index.py`。
- 提交: 两笔 ship.commit, 消息入 .git/COMMIT_MSG_AI.txt(gitmoji ✅)。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 复现(桩服务 + prism 冒烟) | ✅ 完成 | 三条 FAIL 与入池记录一致; 同步 9486a7cd |
| A 定性(选键缺陷, 产品正确) | ✅ 完成 | hide:true 播种 + 固化只含可见列; 92px=templateMinPx 合成 |
| A 修复 + 验证 | ✅ 完成 | 守阵 3 改隐藏前取 key; prism key=upspeed 前=后="88px" PASS |
| B 定性(落点缺陷, 非产品) | ✅ 完成 | 探针实测点击落 .site-chip 被 @click.stop 吞; 节点未脱挂 |
| B 修复 + 验证 | ⬜ 待第二笔 | 落点 (8,8); 提交 2 前实测 |
| 双 UI 全量冒烟 + test.quick | ⬜ 待第二笔后 | 全绿数字随第二笔 |
| issue A 清偿 + 索引 + 提交 1 | ✅ 完成 | 见进度日志 |
| issue B 清偿 + 索引 + 提交 2 | ⬜ 待第二笔 | 档案随提交 2 翻 Done |

## 进度日志

- **2026-10-01 19:30** 同步成功 9486a7cd。读两份 issue / pitfalls 索引(web-ui+testing: columns-persist / smoke)/ memory-bank SKILL / 参照 2212 清偿链写法。起桩服务(8139)复现三条 FAIL。跨工作区查重(5 个 clone)无 ui-smoke 同名 slug, 建本档案。
- **2026-10-01 19:52** A 修复落盘(守阵 3 隐藏前取 key); prism 实测 **列设置·隐藏列宽度保留 PASS — key=upspeed 前="88px" 后="88px"**, 其余用例无回归(CTX-03 辅种组行本轮自绿, 间歇性再次佐证)。issue A 报告 Done + doc-refs 回指本档案, 索引重建, 待提交 1。

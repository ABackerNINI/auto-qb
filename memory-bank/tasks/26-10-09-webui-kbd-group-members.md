# 26-10-09-webui-kbd-group-members — 辅种/追剧页展开分组后键盘上下键选中分组成员

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** 用户命题「WEBUI 当辅种/追剧打开分组时需要支持键盘上下键选中分组成员」。真浏览器复验: **光标链本身早已可用**(`_kbRows` 自 2026-10-09 `51654e44` 起已纳入展开组/展开集的成员行, 双皮肤双视图实测 ↓ 均可落成员行), 真正缺失的是**选中**那条链 —— `_kbExtend`(Shift+↑↓)把 `kind==="torrent"` 一律交给 `shiftTorrentSel`, 而它的候选是**种子页平铺列表** `filteredTorrents`: 辅种/追剧页上该列表为空(懒加载)或与屏幕行无关 ⇒ 范围选择**静默落空**; 鼠标路径同族, `shiftMemberSel` 硬编码查 `expandedKey`, 追剧页该字段恒空 ⇒ 集明细行 Shift+点击同样选不中。修法 = 候选列表收成按上下文解析的单点 `selection.js::_memberRangeList`(种子页平铺 / 辅种页展开组 / 追剧页展开集), 键盘与鼠标两个入口都吃它, 取序与 `_kbRows`/`winMembers` 同源(`sortedMembers`)。新增静态守阵 `test_kb_member_range_context_aware` + 新 e2e `e2e/kbd-members.spec.mjs`(此前键盘导航**零**浏览器覆盖)。实测数字见 `commands run kb.baseline`。
**Topics:** webui-kbd-group-members
**Refs:** memory-bank/pitfalls/web-ui/kbd-range-view-scope.md,memory-bank/testing/baselines/26-10-09-1038-webui-kbd-group-members.md

## 原始请求

用户(2026-10-09 09:44): 「WEBUI当辅种/追剧打开分组时需要支持键盘上下键选中分组成员」。属执行任务(功能命题), 非问答。

复验后追问「选中」的确切含义, 用户澄清: 「展开分组后, ↑↓ 不能把「光标」(虚线框)移到分组成员行, 只能在分组间跳动」—— 与真浏览器实测不符(见下), 故本轮按"实测事实 + 补齐真实缺口"落地。

## 思考过程与决策

- **先复验再动手(避免把"已实现"当"待实现")**: 用 Playwright 桩服务(`scripts/ui_harness.py`)在 prism/atlas 双皮肤、辅种页/追剧页、鼠标展开/纯键盘展开四种路径上按键实测 —— `↓` **都能**把 `kb-cursor` 落到 `.member-row`(辅种页)/`.ep-row`+`.member-row`(追剧页), 截图亦确认虚线框在成员行上。结论: 用户报的"光标不进去"在 HEAD 上不复现, 疑为其运行实例早于当日 `51654e44`(成员行入链的那笔) —— 该仓库静态资源带 no-cache 中间件, 浏览器缓存不是原因, 需重启/更新其服务端。
- **真缺口在"选中"那条链**: 实测 `Space` 选中成员 ✓, 但 `Shift+↓` **选中数不增长**(双视图均如此)。定位: `_kbExtend` 的 `kind==="torrent"` 分支调 `shiftTorrentSel`, 其候选 `filteredTorrents` 在辅种页为 **0**(懒加载, 未进过种子页) ⇒ `indexOf` 全 -1 ⇒ 提前 return, **静默**无操作。
- **同族第二处(鼠标)**: `shiftMemberSel` 硬编码 `filteredGroups.find(expandedKey)` —— 只对辅种页成立; 追剧页 `expandedKey` 恒 null(追剧用 `expandedShows`/`expandedShowEp`) ⇒ 集明细行 Shift+点击也选不中。
- **修法选择: 候选列表单点化, 不改光标/选中模型**。`selection.js` 增 `_memberRangeList()` 按 `viewMode` 分流(种子页平铺 / 辅种页展开组 / 追剧页展开集), `shiftMemberSel` 与 `_kbExtend` 都吃它。**刻意不动** `↑↓` 的语义 —— 本仓库"光标(focus) ≠ 选中(selection)"是拍板设计(见 `overlays.md`「起点与光标是两件事」), 让 ↑↓ 直接选中会推翻既有键位契约与守阵。
- **取序与渲染同源**: 单点里用 `sortedMembers`(与 `_kbRows`、`winMembers` 同源), 顺带修掉旧 `shiftMemberSel` 用原始 `g.members` 序、明细表排序后范围错位的隐患。
- **补 e2e**: 该链此前**零**浏览器断言(静态守阵只查"方法在不在"), 用户报的正是这类"静态看不出"的形态 ⇒ 新增 `e2e/kbd-members.spec.mjs` 钉住"↓ 进成员行 + Shift+↓ 扩选"。

## 实现计划

单会话单轮: 复验(双皮肤双视图, 定"光标可用/选中不可用") → `selection.js` 增 `_memberRangeList` 并改造 `shiftMemberSel` → `shortcuts.js::_kbExtend` torrent 分支改走它 + 修陈旧注释 → 静态守阵 + e2e 规格(红验) → `test.full` + `dev.e2e` → 收尾回写。

## 子任务状态表

| 子任务 | 内容 | 状态 |
|---|---|---|
| S1 | 真浏览器复验: 光标链是否可用 / 选中链是否可用(双皮肤 × 双视图 × 两种展开路径) | Done |
| S2 | `selection.js`: 新增 `_memberRangeList()`(按视图分流) + `shiftMemberSel` 改吃它 | Done |
| S3 | `shortcuts.js`: `_kbExtend` 的 torrent 分支改走 `shiftMemberSel`; 修 `§B` 陈旧注释(成员行 vNext 已兑现) | Done |
| S4 | 守阵 `test_kb_member_range_context_aware` + e2e `kbd-members.spec.mjs`(均红验) | Done |
| S5 | `test.full` + `dev.e2e` 复跑 + 收尾回写(档案 / 切片 / 基线 / 坑档 / kb.index) | Done |

## 进度日志

- **2026-10-09 09:44**: 用户命题。开工先 `my-commit-flow.sync`(已同步 `9aa4aea7`)。
- **2026-10-09 09:5x–10:2x**(复验): 桩服务双皮肤双视图按键实测 —— 光标 ↓ 入成员行**可用**(截图存档 `tmp-analysis/kbd-*.png`), `Space` 选中可用, `Shift+↓` 范围选中**不可用**。向用户追问「选中」含义, 用户澄清为光标不动(与实测不符, 判为其实例版本旧)。
- **2026-10-09 10:3x**(S2–S4): 落地 `_memberRangeList` 单点 + 两个入口接线; 守阵红验通过(临时把 `_kbExtend` 退回 `shiftTorrentSel` → 静态守阵与 e2e 双红, 已还原); 改动 JS 过 `node --check`。
- **2026-10-09 10:38**(S5, 收尾): `test.full` 全绿(数字见 `commands run kb.baseline`), `dev.e2e` 新规格 4 条(双皮肤)全绿。本档案立档 + activeContext 切片 + 基线切片 + 坑档 `pitfalls/web-ui/kbd-range-view-scope.md` + `kb.index` 重建。

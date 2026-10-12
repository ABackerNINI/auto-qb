# 26-10-13-memory-bank-kb-nav-esc — kb.nav Esc 退栈 (借鉴 webui 退栈设计)

**Status:** Done
**Added:** 2026-10-13
**Updated:** 2026-10-13
**Summary:** kb.nav 导航页 Esc 管制移植 webui 退栈链: 用户两报 (①「为 kb.nav 添加 esc功能, 参考 auto-qb 的 esc 设计, 先写一个计划」②「拉取失败导致全屏无法操作一段时间, 加入 esc 管制」) —— 计划件出厂 (plans/26-10-13-0324), 代码零改动, 待拍板四拍点.
**Topics:** kb-nav-esc
**Refs:** memory-bank/plans/26-10-13-0324-plan-kb-nav-esc.html, memory-bank/pitfalls/web-ui/overlays.md

## 原始请求

1. 「为 kb.nav 添加 esc功能, 参考 auto-qb 的 esc 设计, 先写一个计划」
2. 「目前的拉取失败会导致全屏无法操作一段时间, 也需要加入 esc 管制中」

## 思考过程与决策

- **参考口径单点** = webui `lifecycle.js` Esc 退栈链 (一次按键退视觉最上档 / IME 组合期不劫 / 判据用可见性不状态位 / 兜档门条件 + 点名 toast). 26-10-06 实测报障同根: 遮罩层先于被盖住的抽屉, 退栈 order = visual z-order.
- **现状缺口实测** (nav_page.html): Esc 现只两处 (ctxMenu closeCtx, gq/cq per-input 清词); 无 drawer/sel/IME 路径.
- **用户报②坐实单点**: doPull 失败分支弹 `#overlay` (`position:fixed; inset:0; z-index:50` 全屏遮罩, 压 drawer z-30 / ctxMenu z-40 之上), dismiss 路径只 `applyData()` 即下一现算轮, `POLL_MS=30000` ⇒ 失败即整页 ≤30s 不可点击. 修法 = 遮罩退栈**最上档** + Esc 即收.
- **拍板四点** (plan §04, 默认保守): P1 退栈 order overlay→ctxMenu→drawer→sel (z 50→40→30) · P2 兜档**不**清筛选 (localStorage 持久 prefs) · P3 gq/cq 清词 keep per-input · P4 IME guard yes.

## 实现计划

见 plan 件 `plans/26-10-13-0324-plan-kb-nav-esc.html` (拍板后冻结): 改动面 = nav_page.html wire() 段一条 `escRetreat()` chain + IME guard + overlay/drawer 档; 数据层/服务层零改动; 守阵 +4 (单点链 / IME 守卫 / overlay 档先于 ctxMenu+drawer 钉 / drawer 档清 S.sel+closeDrawer).

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 计划件出厂 (含用户报②全屏锁并入退栈) | done |
| 2 | 拍板四拍点 (P1-P4) —— 默认保守口径全采纳 | done |
| 3 | 实施 nav_page.html 链 + 守阵 +4 | done |
| 4 | 闸门 test.full + 基线切片 | done |

## 进度日志

- 26-10-13 03:24 计划初版出厂 (Open).
- 26-10-13 03:33 用户报② (拉取失败全屏锁) 实测坐坐, 同计划件内变更记录并入: overlay z-50 退栈最上档 + 守阵 +1 (`test_esc_closes_overlay_first`).
- 26-10-13 03:36 随本专题入库: 档案 + 计划 + 坑档条 + activeContext 切片同步; 代码零改动 (计划待拍板, 实施子任务 3 未开).
- 26-10-13 04:34 用户「实施计划」= 拍板默认保守口径全采纳 (P1 as proposed / P2 兜档不清筛选 / P3 keep per-input / P4 IME guard yes), 实施出厂: nav_page.html wire() 段 `escRetreat()` 单点退栈链 (overlay→ctxMenu→drawer→sel→兜档收展开态+清 selTopic, IME 守卫, 判据可见性) + 既有 document-level Esc 监听并入链; test_kb_nav.py 守阵 +4 (single_point / ime_guard / overlay_first / closes_drawer). 闸门: 单文件预跑 43 passed, test.full **3176 passed + 4 skipped** (基线切片 26-10-13-0434).

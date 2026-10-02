# 26-10-02-webui-esc-clear-filters — WEBUI ESC 清除筛选兜底

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02 18:15
**Summary:** ESC 绑「清除全部筛选」已按方案 A 落地(实现 `0d286cc5`): lifecycle.js 退栈链终端兜底(门五件套 authOk / page=groups / 无 hrPop 卡 / 非输入态 / facetsActive)+ toast 点名; filters.js 新增 facetsActive(七项面筛同源, 不含 searchQuery); shortcuts.js 三处文案; 守阵 test_esc_chain_clear_filters_fallback。桩服务走查 8/8 项 / 34 断言通过(IME 组合态 CDP 真实组词态验证), 收尾基线 2291 passed + 3 skipped / 99%(baselines/26-10-02-1815)。issue 26-10-01-2108 与计划 26-10-02-1632 置 Done; 计划 §5.5 TODO.md 勾选落空 —— 该行已随 c1b6d53f(2026-10-01 TODO 清理, 因已入池 issue)整体移除, 跟踪点在 issue。
**Topics:** webui-keyboard-shortcuts
**Refs:** memory-bank/plans/26-10-02-1632-plan-webui-esc-clear-filters.html

## 原始请求

用户: 「分析 issue: 26-10-01-2108-question-webui-esc-clear-filter.html, esc绑定到清除筛选器会不会造成混乱, 如果不会, 写一份修改计划」。

## 思考过程与决策

- **归属取证**(基线 c02e9e14): ESC 是唯一固定键 —— 注册表 `clear-esc`(def Escape, fixed, run null)归 lifecycle.js 退栈链(FIX-07), 引擎 `_kbOnKeyDown` 首行对 Escape 早退(shortcuts.js:402), 守阵 test_web_shortcuts.py:221/228 断言级; 录制器按 Esc = 取消, 用户无法把任何动作绑到 Esc。
- **退栈链形状**(lifecycle.js:48-73): else-if 链一次按键只走一个分支 —— 16 层浮层 pop + 4 兜底(清选择 → 收组展开 → 收集展开 → 收剧展开); 链 handler 无 stopPropagation、无输入态门(既有 quirk)。
- **混乱性五向量分析**: ①双触发 ②面板/录制器语义 ③浮层关闭冲突 ④反射连按误清 ⑤输入态/非数据页误触。①②③在「引擎键表」路线下真实存在(链不 stopPropagation → 同按键关浮层+清筛选并发; fixed 不进冲突检测 → 改键死区; 守阵 :228 要改 = 设计倒退), 在「退栈链终端兜底」路线下结构性不存在; ④由链位减速带 + toast + 非破坏性(纯前端态)化解; ⑤由门条件挡死。**判定: 不混乱, 条件式**。
- **方案取舍**: 采纳 A 退栈链终端兜底(LIFO 心智自洽 —— clearFilters 本身就复位 expandedKey, 与兜底段同族); 否决 B 引擎键表(§04 四条); 不采 C 其它默认键(不答本题)。
- **守阵合规**: 计划 doc-refs 只声明 tasks 档案(双向闭环) —— issue/前案 0354/TODO.md 不入 doc-refs, 免改 Done 文档与 issue(issue 反向声明留到实现轮收尾)。

## 实现计划

计划文档 [plans/26-10-02-1632-plan-webui-esc-clear-filters.html](../plans/26-10-02-1632-plan-webui-esc-clear-filters.html), 方案 A 三处代码 + 一处测试 + 一处 TODO:

| # | 改动 | 主点 |
|---|---|---|
| 1 | filters.js computed `facetsActive` | 七项面筛不含 searchQuery(与 clearFilters 字段同源, filtersActive 含搜索词不能直接当门) |
| 2 | lifecycle.js 链尾分支 | `authOk && page==="groups" && !hrPop.open && !inInput && facetsActive` → clearFilters + toast |
| 3 | shortcuts.js 三处注释/label | clear-esc label 补「清筛选」; clear-filters 注明 Esc 走链不走键表; 头注补句 |
| 4 | test_web_shortcuts.py 守阵 | 链序 / 门条件五件套 / Escape 唯一默认绑定 / facetsActive 纯度 |
| 5 | TODO.md 勾选 | `[?]` → `[x]`(实现合并后) |

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 混乱性分析 + 修改计划产出 | Done |
| 2 | 用户拍板(方案 A/B) | Done |
| 3 | 三处代码改动 + 守阵 | Done |
| 4 | 真机走查 8 条 + TODO 勾选 | Done |
| 5 | 收尾(基线 + issue 反向声明 + 回写) | Done |

> 注: #4 走查以桩服务(ui_harness.py)承载, 8/8 项全过; TODO.md 勾选落空(行已移除, 跟踪点在 issue 26-10-01-2108)。

## 进度日志

- 2026-10-02 16:46 — 分析轮完成: 同步 c02e9e14 → 证据链取证(引擎/退栈链/filters/hrPop/escBusy/守阵六段) → 五向量混乱性分析 → 计划 plans/26-10-02-1632(Proposed) → 立档本档案。生产文件零改动, 待拍板后实施。
- 2026-10-02 — 拍板 + 实现轮(阶段1): 拍板方案 A; 实现 `0d286cc5` —— filters.js 新增 computed `facetsActive` / lifecycle.js 链末兜底 + inInput 门 + toast / shortcuts.js 三处文案 / test_web_shortcuts.py 新增守阵; test.quick 实测 2291 passed + 3 skipped 全绿。计划 §5.5 TODO.md 勾选落空: 该行已被 c1b6d53f(2026-10-01 TODO 清理, 因已入池 issue)整体移除, 跟踪点在 issue 26-10-01-2108, 未重新加行。阶段1 命中路由 pitfalls/web-ui/js-comment-terminator.md 成功规避注释雷(未踩雷, 不算复发)。
- 2026-10-02 — 桩服务走查轮(阶段2): ui_harness.py 桩服务 + 浏览器走查计划 §08 八条, **8/8 项 / 34 断言通过, 实现零缺陷**, 无提交; 第 8 项 IME 组合态用 CDP 真实组词态验证, 页面侧契约(inInput 门)已全验, 真实 OS 输入法候选窗交互属人工残留面。
- 2026-10-02 18:15 — 收尾轮(阶段3): sync cfbfa712 → test.full **2291 passed + 3 skipped / 99%**(13,259 语句 / 86 未覆盖 / 4,442 分支 / 81 partial, 38.3s, rc=0)→ 基线切片 [baselines/26-10-02-1815](../testing/baselines/26-10-02-1815-webui-esc-clear-filters-done.md); issue 26-10-01-2108 补收尾行、计划 26-10-02-1632 置 Done、progress/implemented-webui.md 迁出、browser-env.md 回写(chromium-1234 已不在 / WorkBuddy NODE_PATH 线索失效 / playwright-core@1.63 + chromium-1243 配对可用)。阶段2 计划外发现(ui_harness --hr-site 崩溃、覆盖率语句数高低轮替波动)按范围守恒不入池不修, 留汇报。

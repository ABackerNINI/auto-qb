# 辅种/追剧页成员行 ← 收起所属单元(光标进组后可收起分组) · 已闭环

> 摘要: 用户报「收起当前行快捷键无法在键盘光标进入分组后收起分组」。诊断: `row-collapse`(←)的落点 `shortcuts.js::_kbCollapseRow` 只按 kind 分派 group/show/ep 三种行, 而成员行 kind=torrent —— 按 ↓ 进展开组/展开集后三个分支全不命中, **静默无反应**(不报错、无 toast)。根因是"成员行纳入键盘光标链"(计划 26-10-08-1217 §3.5)时同族的展开/收起分派未同步(该计划当时把此缺口记为"接受"), 从用户视角是缺陷。修法(用户拍板「直接收起并回组行」): 成员行 ← 收起**所属单元**并把光标带回其行 —— 新增父行解析单点 `_kbParentRow`(判据复用 `selection.js::_memberRangeList`, 与 `_kbRows` 渲染同源), 收起后走 `_kbApplyCursor` 落父行。1 源文件 + 1 静态守阵 + 2 e2e 场景(双皮肤)。实测数字见 `commands run kb.baseline`。
>
> 最后活动: 2026-10-09 13:47

**Refs:** memory-bank/pitfalls/web-ui/kbd-row-kind-dispatch.md,memory-bank/testing/baselines/26-10-09-1347-webui-kbd-collapse-parent.md

## 本轮完成

- **会话开工同步**: `my-commit-flow.sync` 快进 `df61f920 → 9e520322`。
- **诊断(只读)**: 定位 `_kbCollapseRow` 的 kind 分派缺口(成员行落空); 与用户确认「现在就修 + 直接收起并回组行」。
- **`shortcuts.js`**: 新增 `_kbParentRow(c)`(辅种页父行 = 展开的组行 / 追剧页父行 = 展开的集行 / 种子页平铺行无父行); `_kbCollapseRow` 增成员行分支(收起所属单元 + `_kbApplyCursor` 落父行 —— 成员行随收起消失, 不把光标留在链外); 注册表 `row-collapse` 条目与文件头补注。
- **守阵**: 新增 `tests/test_web_shortcuts.py::test_kb_collapse_parent_row`(静态, 已登记进该文件头部「测试计划」); `e2e/kbd-members.spec.mjs` 增 2 条 @fast(辅种页分组 / 追剧页集, 双皮肤 4 条)。**两组均红验**(短路成员行分支 → 静态 1 红 + e2e 4 红, 已还原)。
- **收尾**: `test.full` 全绿(数字见 `commands run kb.baseline`); 坑档 `pitfalls/web-ui/kbd-row-kind-dispatch.md`; 基线切片 + `kb.index`。

## 待办 / 移交

- 无代码遗留。未立任务档案(单会话、单文件小修、无计划/报告, 未达立档阈值)。
- **同类面复核**: 其它按 `kind` 分派的键盘动作(`_kbToggleSelect` / `_kbOpenRow` / `_kbMeta` / `_kbOpenDrawer` / `_kbOpenFolder` / `_kbTargets` / `_kbExpandRow`)逐个看过 —— 均已覆盖 torrent, 本轮未发现第二个落空点。

# 键盘光标链新增行种后, 按 kind 分派的兄弟动作会静默落空 (逐个过一遍)

> 摘要: `shortcuts.js` 的键盘动作大量按 `c.kind` 分派(group / show / ep / torrent)。把一种新行种纳入 `_kbRows()` 光标链时, 只在**新增那一条链**上接线(如"成员行能 ↓ 走到""成员行能 Shift 扩选"), 而同族的**其它分派**若没同步, 症状全是**静默无反应**(不报错、无 toast, 只是"按了没动静")。2026-10-09 实证: 成员行(展开组/展开集的成员, kind=torrent)入链后, ← 收起当前行(`_kbCollapseRow`)只认 group/show/ep, 光标按 ↓ 进组后 ← 收不起任何东西 —— 用户报「收起当前行快捷键无法在键盘光标进入分组后收起分组」。
> 触发: 新增行种/成员行入光标链, 改 `_kbRows` 或任一 `_kb*` 动作, 快捷键按了没反应, 收起当前行不生效, 光标进组后 ← 无效, kind 分派漏分支

**Refs:** memory-bank/activeContext/26-10-09-1347-webui-kbd-collapse-parent.md

### 新行种入链 = 把所有 `c.kind` 分派逐个过一遍 (2026-10-09 实测)

- **触发**: 往 `_kbRows()` 里加一种 `kind`, 或给某动作加/改 `c.kind === "..."` 分支。
- **判别**: 症状**静默** —— 不报错、无 toast, 只是"按了没反应"; 且**只在某种行上**复现(组行正常、成员行不灵)是本坑指纹。静态守阵只查"方法在不在", 查不出"这条 kind 走没走到分支", 必须真实按键 + 读 DOM 观感。
- **处置**: 入链改动落地时, 把**全部** `c.kind ===` 分派点列一遍逐个确认覆盖: 展开/收起(`_kbExpandRow`/`_kbCollapseRow`)、选中(`_kbToggleSelect`/`_kbExtend`)、打开(`_kbOpenRow`/`_kbOpenDrawer`)、目标解析(`_kbTargets`/`_kbMeta`/`_kbOpenFolder`/`_kbSingleHash`)。无自身语义的行(叶子)要**显式**给出替代语义 —— 如成员行 ← 收起**所属单元**并把光标带回其行(`_kbParentRow`, 父行判据复用 `_memberRangeList` 与渲染同源), 而不是靠"落到 else 什么都不做"。
- **守阵**: `tests/test_web_shortcuts.py::test_kb_collapse_parent_row`(静态: 成员行分支在 + 走父行单点 + 光标带回父行) + `e2e/kbd-members.spec.mjs`(真浏览器: 光标进成员行后 ← 收起所属单元并回父行, 双视图双皮肤)。

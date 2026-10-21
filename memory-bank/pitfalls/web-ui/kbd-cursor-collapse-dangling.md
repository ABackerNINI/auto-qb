# 收起展开态时键盘光标悬空在链外

> 摘要: 收起展开态只复位展开态、不动 `kbCursor` ⇒ 光标仍指着已随收起卸载的明细行, 虚线框被宿主连坐带走, 观感是"锚点被清了"
> 触发: Esc 收起, 展开态收起, 光标消失, kb-cursor 悬空, 明细行卸载

**Refs:** memory-bank/tasks/26-10-22-webui-kbd-esc-collapse-cursor.md

### 收起展开态(明细表 / 集 / 剧)时既不清除也不归位光标 ⇒ 光标悬空指向链外 hash

- **触发**: 键盘光标(`kbCursor`)落在**展开单元的子行**上(辅种页明细成员行 / 追剧页集版本行 / 集行), 此时任何把该展开态置空的路径(Esc 退栈链三档、切视图复位、筛选后复位)只复位展开态而不动光标 —— 子行随 `v-if` 一起卸载, 光标却仍指向它。
- **判别**: 表面症状是"虚线框没了 / 键盘锚点被清除", 但 `vm.kbCursor` 仍非 null, 且 `kind==="torrent"` 指向一个已不在 `_kbRows()` 链上的 hash。判别式 = 收起后按一次 ↑/↓, 光标**不**落在被收起行的相邻行, 而是走 `_kbViewportRow` 无光标回落(落视口内首/末行) —— 观感即"光标丢了, 下次按键跳到别处"。⚠ 别误判成"Esc 清了光标": `lifecycle.js` 退栈链从不清 `kbCursor`, 清的是 `selAnchor*`(Shift 连选起点, 另一套语义)。
- **处置**: **谁被收起, 光标就退回谁** —— 在复位展开态的同一处就地写 `kbCursor = { kind: <父行 kind>, id: <被收起的 key> }`(辅种页 `expandedKey`→`group` / 追剧集 `expandedShowEp`→`ep` / 追剧剧 `expandedShows`→`show`)。多支同时展开(追剧页 `expandedShows` 是数组)优先退回**光标所在那一支**(走 `_kbParseEpId` 解析 ep id 的 showKey, 不手抄 id 形态), 否则退回首支。就地赋值, 不调快捷键引擎的 `_kbCollapseRow` —— 退栈链自成一体, 不反向依赖引擎。
- **守阵**: `tests/test_web_shortcuts.py::test_esc_collapse_returns_cursor_to_parent`(三档各自归位 + 禁真调 `_kbCollapseRow` + 清选择仍先于收展开 + 多剧选支走单点); 浏览器侧 `e2e/kbd-members.spec.mjs` 两条 @fast 用例(辅种页退回组行 / 追剧页逐层退回集行·剧行)。
- **复发**: 1 (2026-10-22): `←` 路径(`shortcuts.js::_kbCollapseRow`)早在 2026-10-09 就收编了「收起后把光标带回父行」, 但 Esc 退栈链在**另一个文件**(`lifecycle.js`)里独立实现了同一件事, 没被一并覆盖 —— 为什么没命中: 收起归位当时被记成「快捷键引擎内部行为」, 坑档与守阵的扫描面都只盯引擎, 退栈链这条平行路径不在视野里。

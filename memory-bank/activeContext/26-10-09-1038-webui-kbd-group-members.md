# 辅种/追剧页展开分组后键盘上下键选中分组成员 · 已闭环

> 摘要: 用户命题「WEBUI 当辅种/追剧打开分组时需要支持键盘上下键选中分组成员」。真浏览器复验: **光标链早已可用**(`_kbRows` 自 `51654e44` 起纳入展开组/展开集的成员行, 双皮肤双视图实测 ↓ 均落成员行), 真正缺的是**选中**链 —— `_kbExtend`(Shift+↑↓)把 torrent 一律交给 `shiftTorrentSel`, 其候选是**种子页平铺列表** `filteredTorrents`, 在辅种/追剧页为空(懒加载)或与屏幕行无关 ⇒ 范围选择静默落空; 鼠标同族: `shiftMemberSel` 硬编码 `expandedKey`, 追剧页恒空 ⇒ 集明细行 Shift+点击也选不中。修法 = 候选列表收成按上下文解析的单点 `_memberRangeList`(种子页平铺 / 辅种页展开组 / 追剧页展开集), 键盘与鼠标两入口都吃它, 取序与 `_kbRows`/`winMembers` 同源。**刻意不改 ↑↓ 语义**(光标 ≠ 选中是既有拍板设计)。
>
> 最后活动: 2026-10-09 10:38

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-group-members.md,memory-bank/pitfalls/web-ui/kbd-range-view-scope.md,memory-bank/testing/baselines/26-10-09-1038-webui-kbd-group-members.md

## 本轮完成

- **复验先行**: 桩服务真按键实测(prism/atlas × 辅种页/追剧页 × 鼠标展开/纯键盘展开) —— 光标 ↓ 入成员行可用, `Space` 选中可用, `Shift+↓` 范围选中不可用。用户所报"光标进不去成员行"在 HEAD 不复现(判为其运行实例早于当日 `51654e44`; 静态资源有 no-cache 中间件, 非浏览器缓存)。
- **`selection.js`**: 新增 `_memberRangeList()`(按 `viewMode` 分流: 种子页 = `filteredTorrents`; 辅种页 = 展开组成员; 追剧页 = 展开集版本); `shiftMemberSel` 改吃它(顺带修掉"用原始成员序、明细表排序后范围错位")。
- **`shortcuts.js`**: `_kbExtend` 的 `kind === "torrent"` 分支由 `shiftTorrentSel` 改走 `shiftMemberSel`; 修 `§B` 陈旧注释(成员行 vNext 已兑现)。
- **守阵**: 新增 `tests/test_web_shortcuts.py::test_kb_member_range_context_aware`(静态); 新增 `e2e/kbd-members.spec.mjs`(真浏览器, 双皮肤 4 条) —— 该链此前**零**浏览器覆盖。两组均红验通过。
- 实测数字见 `commands run kb.baseline`。

## 待办 / 移交

- 用户侧: 若其运行实例仍复现"光标进不去成员行", 需重启/更新服务端到含 `51654e44` 的版本。
- 无代码遗留。

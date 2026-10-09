# 键盘范围选择的候选列表必须随视图解析 (别硬编码单一视图的数据源)

> 摘要: 成员行的 Shift+↑↓ 范围选择, `_kbExtend` 曾**一律**调 `shiftTorrentSel` —— 它的候选是**种子页平铺列表** `filteredTorrents`。在辅种页/追剧页该列表要么为空(懒加载, 未进过种子页)、要么与屏幕上的行无关, 于是范围选择**静默落空**(不报错、不提示, 只是"选不中"), 而同一功能在种子页完全正常 —— 只在跨视图时露头。鼠标路径同族: `shiftMemberSel` 硬编码查 `expandedKey`(辅种页字段), 追剧页 `expandedKey` 恒空 ⇒ 集明细行 Shift+点击也选不中。
> 触发: 键盘 Shift+↑↓ 选不中, 范围选中没反应, 辅种页/追剧页范围选择失效, shiftMemberSel, shiftTorrentSel, _kbExtend, filteredTorrents, 成员行范围, 选中集合不增长, 选中数不涨
**Refs:** memory-bank/tasks/26-10-09-webui-kbd-group-members.md

### 范围/集合类操作的候选列表: 随上下文取, 别硬编码 (2026-10-09 实测)

- **触发**: 改键盘选择 / 范围选择 / 批量目标解析; 或任何"候选列表随视图或展开态变化"的操作。
- **判别**: 症状**静默** —— 不报错、无 toast, 只是选中集合不增长; 且**只在部分视图复现**(种子页正常、辅种/追剧页失效)是本坑指纹。静态守阵看不出来(它只查"方法在不在 / 调用顺序对不对"), 必须真实按键 + 读选中态。
- **处置**: 候选列表收成**一个按上下文解析的单点**(本仓库 = `selection.js::_memberRangeList`: 种子页 = `filteredTorrents`; 辅种页 = 展开组的成员; 追剧页 = 展开集的版本), 键盘 `_kbExtend` 与鼠标 `shiftMemberSel` 两个入口都吃它。取序与渲染 / 光标链同源(`sortedMembers`), 保证"屏幕上下 = 选择上下"。
- **守阵**: `tests/test_web_shortcuts.py::test_kb_member_range_context_aware`(静态: 三分支齐全 + `_kbExtend` 走单点) + `e2e/kbd-members.spec.mjs`(真浏览器: 辅种页 Space 选中后 Shift+↓ 选中数 1→2)。

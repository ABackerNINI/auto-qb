# 2838 —— 辅种/追剧页键盘选中分组成员(范围选择随视图解析)

> 摘要: 修「辅种/追剧页成员行键盘 Shift+↑↓ 范围选择静默落空」的收尾基线。范围候选列表收成按上下文解析的单点 `selection.js::_memberRangeList`(种子页平铺 / 辅种页展开组 / 追剧页展开集), 键盘 `_kbExtend` 与鼠标 `shiftMemberSel` 都吃它; 新增静态守阵 + 新 e2e `e2e/kbd-members.spec.mjs`。
> 档案: memory-bank/tasks/26-10-09-webui-kbd-group-members.md
> 基线时间: 2026-10-09 10:38

**Refs:** memory-bank/tasks/26-10-09-webui-kbd-group-members.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2838 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 40.14s(墙时 42.1s)
- **新增测试**: 1 个静态守阵函数(`test_kb_member_range_context_aware`, 挂在 `tests/test_web_shortcuts.py`, 并登记进该文件头部「测试计划」)。
- **e2e**: 新增 `e2e/kbd-members.spec.mjs`(双皮肤 × 2 条 = 4 条 @fast), 真浏览器全绿 —— 该链此前**零**浏览器覆盖。红验: 把 `_kbExtend` 临时退回 `shiftTorrentSel` 时, 静态守阵与 e2e 的 `Shift+↓` 断言双双转红(已还原)。

# WEBUI 键鼠割裂调研 — activeContext

> 摘要: 用户报「WEBUI 快捷键上下移动与鼠标点击割裂感很强, 鼠标在顶部按一下键盘跳到最下方」。调研轮: 代码取证三场景 + 业界调研(APG / VS Code / Gmail / 文件管理器 / 组件库) → 报告 [reports/26-09-30-1806-report-webui-keymouse-cohesion.html](../reports/26-09-30-1806-report-webui-keymouse-cohesion.html), 推荐方案 B。实施轮(2026-09-30, 用户指令「实施计划…按推荐方案」直接拍板): 方案 B 已落地并随主提交入库(2026-09-30 20:1x) —— ①无光标回落极值行→视口就近行(shortcuts.js `_kbViewportRow`: 窗口化走 `_rowPre` 前缀和同源校验, 其余扫渲染行可见性, 解析失败退回旧口径) ②selection.js 五个点击入口回写 kbCursor(写在修饰键分支之前, 落光标≠选中) ③groups/shows 两处明细成员行补 kb-cursor 视觉(报告口径偏差: 双轨对成员行原不成立) ④_kbHint 文案与注释同步 ⑤守阵 16→17(test_click_lands_cursor_and_viewport_fallback)。实测 test.full **1851+3 / 90%**(基线 [26-09-30-1953](../testing/baselines/26-09-30-1953-webui-keymouse-planb.md), 合流内核 P1 2174a568 后复核)。
> 最后活动: 2026-09-30 19:53

## 已完成

- 调研轮(细节在报告 §02-§05 与 tasks/26-09-28-webui-keyboard-shortcuts.md 进度日志 18:06 条): 三场景取证、六方向业界调研、方案比选(A/B/C)。
- 实施轮(细节在 tasks 档案进度日志 19:53 条): 改动 6 文件(shortcuts.js / selection.js / state.js 注释 / tpl-groups / tpl-shows / test_web_shortcuts.py), 全绿未提交。
- 决策: 报告原建议「拍板后另出计划文档再实施」—— 本轮按用户直接指令实施, 未另出计划 HTML, 以报告 §06/§07 为实施口径, 决策细节记 tasks 档案。

## 正在进行

- 等用户真机验收(走查点: 列表顶部按 ↑ 不再跳底 / 鼠标点击某行后 ↑↓ 从该行出发 / 被点行出现虚线光标环); 方案 C(roving tabindex)仍缓议。

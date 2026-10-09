# WEBUI 弹窗键盘操作调研

> 摘要: 用户命题「WEBUI 弹窗内无法通过键盘操作(添加种子/删除种子, 无法通过键盘选择保存位置等), 先调研成熟的解决方案, 写报告」。产出报告 `reports/26-10-09-2136-report-webui-dialog-keyboard-accessibility.html`。**核心结论**: 病根不是键位缺失而是缺「焦点管理」层 —— 行为层已完成大半(确认框初始焦点+Enter/Esc、三下拉 ↑↓/Enter/Esc、Esc 退栈链), 三个根因是 ①打开时焦点不进窗(除 modal/限速外) ②无 Tab 循环/背景无 inert ③目录浏览器(选择位置面板)纯鼠标。成熟方案 = WAI-ARIA APG Dialog/Combobox 模式 + focus-trap 库 + 原生 dialog+inert 三路线, 推荐自研焦点管理单点(P0) + 复用仓内 roving tabindex 成法键盘化目录浏览器(P1) + combobox ARIA 语义与危险框初始焦点改「取消」(P2); 不建议迁原生 dialog 或引 reka-ui(承载层重写与三皮肤/自绘遮罩/Esc 链冲突)。**零 `src/` / `tests/` 改动**。
> 最后活动: 2026-10-09 21:41

## 状态

- 已完成: 现状代码级取证(`ui_feedback.js` / `add_torrent.js` / `dialogs.js` / `lifecycle.js` / `shortcuts.js` / `dialogs-mgr.html` / `drawer_templates.js`) + 外部调研(APG Dialog/Combobox、MDN dialog/inert、focus-trap、reka-ui) + 报告入库(`reports/_index.md` 重建)。
- 未做: 零代码改动; 未拍板是否实施。
- 下一步(待用户拍板): 若推进按报告 §05 立实施计划(P0 焦点单点 + P1 目录浏览器键盘化建议一并立项, 共享焦点栈设计; P2 语义收尾)。

**Refs:** memory-bank/reports/26-10-09-2136-report-webui-dialog-keyboard-accessibility.html

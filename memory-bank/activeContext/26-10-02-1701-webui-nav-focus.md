# WEBUI 键盘切页旧页签残留焦点框（修复轮）

> 摘要: 用户报的残留高亮框已修复入库 —— 根因是 Chromium 在 keydown 分发时把鼠标遗留的页签焦点重估为 :focus-visible(分发期间 matches 已翻转, 不能区分来源), 修法走不变式 view.js::syncNavFocus(切页后导航焦点==活动页签否则 blur)。档案 [tasks/26-10-02-webui-nav-focus](../tasks/26-10-02-webui-nav-focus.md); 坑单 pitfalls/web-ui/nav-focus-stale-ring.md; 基线 26-10-02-1705。
> 最后活动: 2026-10-02 17:05

## 正在进行

- 无(待提交入库)。

## 本轮产出

- 修复: tpl/topbar.html(data-view) + view.js::syncNavFocus + ui_smoke.cjs「导航焦点」双断言。
- 待用户定夺: 同机制的「点页签后 Ctrl+, 进设置页」残留路径未动(不在报障复现内)。

# 站点页搜索实施(webui-sites-page-search)

> 摘要: 专题完结态 —— 搜索本体(96671860)/方案C 聚焦搜索层(55a6b66)均已入库; 26-09-29 深夜追加修上下键选中项闪烁(档案 tasks/26-09-29-webui-tracker-focus-layer.md 子任务 6, 本轮提交)。
> 最后活动: 2026-09-29 21:45

## 已完成

- 实施史与决策单点在档案 [tasks/26-09-29-webui-tracker-focus-layer.md](../tasks/26-09-29-webui-tracker-focus-layer.md)(26-09-28 搜索本体/跳转器、26-09-29 方案C 聚焦层、同日深夜闪烁修复), 不在此复述。
- 闪烁修复(2026-09-29 21:45): hover/act 同源打架 → hubTrackerHoverIdx(mousemove+3px 位移门限接管) + CSS 摘 :hover 单路高亮 + 收层复位门限坐标; 坑 pitfalls/web-ui/hover-keynav-fight; 同族隐患入池 26-09-29-2142 两条 bug; 基线 26-09-29-2145。

## 进行中

- 无 —— 待用户真机复验闪烁修复效果; 两条 Open issue(滚动跟随缺口 / 弹窗同族隐患)待排期。

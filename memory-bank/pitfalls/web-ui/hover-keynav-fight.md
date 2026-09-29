# 键盘导航与悬停高亮同源打架(下拉/列表选中项闪烁)

> 摘要: 下拉/列表组件把悬停(@mouseenter 直写高亮状态 + CSS :hover 与活动项同款样式)与键盘活动项(↑↓)接到同一个高亮状态上 —— 静止光标钉住旧高亮, 且浏览器在行动画/滚动/DOM 变更后给静止光标补发合成 hover 事件把活动项拽回光标行, 上下键时选中项交替闪烁。处置 = 悬停接管走 mousemove + 位移门限(3px), CSS 只留活动项类一条高亮路。
> 触发: 改下拉列表键盘导航, 加悬停高亮, 上下键选中项闪烁乱跳, mouseenter, 双高亮, 合成 hover 事件, scrollIntoView, combobox, 活动项

## 条目

- **触发**: 组件同时存在「悬停高亮」(@mouseenter 直写高亮状态, 且 CSS `:hover` 与活动项类共用同款样式)与「键盘活动项」(↑↓ 移动)两路输入, 且光标可能静止停在下拉/列表上。站点搜索命中面板(2026-09-29 用户实测报障, 已修)与弹窗分类/标签下拉(同构推定, issue 26-09-29-2142-bug-dialog-hover-keynav-fight)都是此形态。
- **判别**: ①纯键盘(鼠标不在面板上)不闪, 鼠标停在下拉里就闪或出现双行高亮 = 本坑; ②代码上 grep `@mouseenter` 直写高亮状态 + CSS 里 `:hover` 与活动项类共用样式; ③容易漏的放大器: 浏览器在元素移动(入场动画 translateY)/列表滚动/DOM 变更后会向静止光标**补发合成 hover 事件** —— 不动鼠标也会触发, 纯键盘路径复现不出来, 代码审查时容易以为"只在鼠标移动时才发生"。
- **处置**: ①悬停接管改 `@mousemove` + 位移门限(距上次接管 <3px 不接管 —— 合成事件位移恒 0 天然被挡, 真实移动才交出活动项), 单点 `hubTrackerHoverIdx(i, ev)`; ②CSS 摘掉 `:hover`, 高亮只走活动项类一条路(双高亮从样式层根除); ③收层/关闭时复位门限坐标(下次打开首个动作不被旧坐标误挡); ④给列表加 scrollIntoView 反而**依赖**①的门限 —— 滚动后浏览器补发的合成 mousemove 正是靠它挡住, 修滚动跟随前先确认门限已就位。参考实现: config_hub.js `hubTrackerHoverIdx` + console_hub.css `.hb-tr-hit.act` 单路。
- **守阵**: test_web.py::test_frontend_tracker_search_wiring —— 模板必须挂 `@mousemove="hubTrackerHoverIdx(i, $event)"`、`@mouseenter="hub.trackerHitIdx` 零残留、收层单点复位 `trackerMouseAt`、CSS 高亮只走 `.hb-tr-hit.act` 且无 `hb-tr-hit:hover`。
- **复发**: 0

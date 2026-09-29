# 基线 · 1751 passed + 2 skipped —— 站点搜索上下键选中项闪烁修复轮 (悬停接管位移门限)

> 摘要: 用户报「设置-站点-搜索框结果上下键选中项偶尔异常闪烁」⇒ 根因 hover/act 两套高亮同源打架
> (@mouseenter 直写 trackerHitIdx + CSS :hover 与 .act 同款; 行入场动画/滚动/DOM 变更后浏览器给静止
> 光标补发合成 hover 事件, 活动项被拽回光标行, 交替即闪烁) ⇒ hubTrackerHoverIdx(mousemove + 3px
> 位移门限, 合成事件位移恒 0 天然被挡) + CSS 摘 :hover 单路高亮(.act 唯一) + box-shadow 补进
> transition + 收层单点复位门限坐标; 守阵 4 断言。同轮入池 2 条 bug(命中列表滚动跟随缺口 / 弹窗
> 分类标签下拉同族隐患) + 新坑 pitfalls/web-ui/hover-keynav-fight。
> 基线时间: 2026-09-29 21:45 (develop @ e0a8b721, 开工前 commands run my-commit-flow.sync 已同步)
> 档案: tasks/26-09-29-webui-tracker-focus-layer.md

TOTAL 1751 passed + 2 skipped / 91%(12442 语句 / 999 未覆盖, test.full 31.32s, rc=0) —— 0 failed。
数字与远端 fe28dc6 提交时自带记录(1751+2)完全一致; 较上轮切片 26-09-29-2004 第四轮段(1749+3 @
ae29a4f 时代)的 collected +1 来自 fe28dc6 根路径重定向测试扩 6 种 cookie 场景(+1 用例), 与本轮
改动无关 —— 本轮 = 三份前端静态资源 + 守阵断言并入既有函数(不增用例数)。改动面: config_hub.js /
tpl/settings.html / console_hub.css / tests/test_web.py。

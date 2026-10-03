# 基线切片 26-10-04-0329 — 状态栏双 tooltip 修复 (aq-tip 祖先链摘除 + 悬浮期补摘)

> 摘要: 用户报「WEBUI 状态栏多数元素有两个 tooltip」。根因 = 全局自绘 tooltip(.aq-tip,
> shared/ui_feedback.js)靠 hover 时摘 title 属性压原生气泡, 但 statusbar.html 是**嵌套带
> title 结构**(.sb-today > .sb-hist/.sb-qb、.sb-stats > .sb-item、.sb-speed > .sb-alt/.sb-spd),
> 旧实现只摘 `closest("[title]")` 最内层 —— 原生气泡借外层祖先 title 还魂, 与 350ms 自绘浮层
> 叠出双气泡; 同源触发: 状态栏 `:title` 随轮询逐轮变值, Vue patch 悬浮期间写回 title 而
> mouseover 不再触发。修法: enter() 沿 parentElement **整条祖先链**摘(hide() 单点还原),
> 另设 250ms 周期补摘(补摘捕获即最新值, 还原不丢 Vue 写回的新值)。改动单文件 ui_feedback.js。

- 时间: 2026-10-04 03:29 (GMT+8); 会话起点 sync 至 64316c09(远端无更新, 基线即此)
- 分支: develop @ 64316c09(+ 本轮未提交改动: ui_feedback.js + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 29.14s, 覆盖率 TOTAL 99%**(14416 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0308: 2423 passed)用例数持平: 纯前端行为层修复, 无新增/删改用例;
  test.quick 先行 2423 passed / 20.3s
- 未验证面: 真机三皮肤状态栏 hover 走查(历史入口/速度组悬浮 >2s 只见一个气泡、移开 title
  恢复)待用户确认; 坑档 pitfalls/web-ui/aq-tip-nested-title-double.md 守阵无静态断言(行为层
  逻辑字符串钉不住), 复验方式记录在坑档

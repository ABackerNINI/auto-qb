# 基线切片 26-10-04-0414 — 状态栏双 tooltip 三轮修复 (aq-tip 断供式: title→data-aq-tip 单向迁移)

> 摘要: 前两轮「hover 时摘 title + 祖先链 + 250ms 补摘」后用户仍报两 tooltip **交替**出现。
> 第三条触发路径(前两轮模型未覆盖): Vue 轮询把指针下节点整个替换时指针不动、mouseover
> 不触发, 新节点带着 title 直接入 DOM, 原生气泡还魂; 补摘定时器与原生 ~1s 起跳另有竞态。
> 定稿修法 = 原生 tooltip 断供式: MutationObserver 盯全文档, title 属性任何时刻出现即刻
> 迁进 data-aq-tip 并删掉原属性(启动先 sweep 一遍现存 DOM), DOM 里不存在 title, 原生气泡
> 从根上无从弹出; 浮层委托改命中 [data-aq-tip], 文案 show() 现读最新值; title 不再还原。
> 改动单文件 ui_feedback.js。

- 时间: 2026-10-04 04:14 (GMT+8); 会话起点 sync 至 800ccba2(远端有更新, 快进合并)
- 分支: develop @ 800ccba2(+ 本轮未提交改动: ui_feedback.js + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 30.21s, 覆盖率 TOTAL 99%**(14416 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0329: 2423 passed)用例数持平: 纯前端行为层修复, 无新增/删改用例;
  另做 Playwright 冒烟 8 断言全过(动态插入 title / 悬浮出泡 / 悬浮期重写截走 / 移开收起 /
  节点替换无鼠标事件 / 空串 title / 嵌套组 / 全文档无残留 title)
- 未验证面: 真机三皮肤状态栏 hover 走查(悬浮 >2s 只见一个自绘气泡、DevTools 现查 DOM 无
  title 属性)待用户确认

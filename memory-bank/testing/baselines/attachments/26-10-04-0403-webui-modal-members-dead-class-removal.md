# 基线切片 26-10-04-0403 — .modal-members 死类清除 (存量观察清偿)

> 摘要: 清偿基线 26-10-04-0353 记录的存量观察 —— `.modal-members` 及其子选择器
> `.modal-member-row` / `.mm-site` / `.mm-name` / `.mm-path` 全库零构造点 (delete_flow.js:202
> 注释「DLG-01 成员明细已移除」即废弃锚点), 三处移除: atlas/css/views.css 成员明细整块 10 行 +
> console/css/views.css 整块 11 行 + ui_feedback.js 白名单摘除 "modal-members" (8 类内滚区 → 7 类,
> 注释同步)。CSS 仅删行, 700 行守卫无碰撞风险; 白名单摘除项本就无节点命中, 兜底行为零变化。

- 时间: 2026-10-04 04:03 (GMT+8); 会话起点 sync 至 2ab1f6a3 (远端无更新)
- 分支: develop @ 2ab1f6a3 (改动留工作树, 等用户提交指令)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 29.88s, 覆盖率 TOTAL 99%**(14282 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0353: 2423 passed)用例数持平: 纯静态资源 (CSS/前端 JS) 死代码清除,
  无新增/删改用例; test.quick 预检一次绿 (2423 passed / 24.83s)
- 未验证面: 白名单行为等价性为静态推断 (摘除项无构造点 ⇒ 不会命中), 未做老 Safari 特征模拟;
  残余同类风险: 无 —— 全库 grep "modal-member" 仅余零命中 (docs 里的历史报告/计划不算构造点)

# 无 node 环境下用 IAB 浏览器做前端验证 (与 evaluate 序列化假象)

> 摘要: 本机没有 node 时 Playwright e2e 链路不可用, 可用 ZCode IAB 浏览器 + evaluate 替代 —— 但 evaluate 返回嵌套对象是序列化假象 `{}`。
> 触发: 浏览器验证, IAB, evaluate, 无 node, 冒烟跑不了, 序列化, 假空对象, cfgRaw, 绑定状态
> 最后活动: 2026-09-27

### 本机无 node ⇒ Playwright 冒烟链路整体不可用, 用 IAB 浏览器替代

- **触发**: `node: command not found` 且无 npx 缓存(2026-09-27 实测, plan 26-09-27-1318 M2 验证)。
- **判别**: `node`/`npm`/`npx` 全不在 PATH; Playwright 链路连依赖解析都过不了。
- **处置**: 起 `dev.harness` 桩服务后, 用 ZCode 浏览器能力(IAB)打开 `http://127.0.0.1:8099/prism/`,
  `tab.playwright.evaluate` 直调前端方法 + 读 DOM 断言。能覆盖渲染/交互/写树; 截图对重页面
  可能超时(1500 种子页两次 30s 超时), DOM 级断言够用就别追截图。

### evaluate 返回 Vue 响应式对象是**序列化假象** —— 嵌套内容丢成 `{}`

- **触发**: 在 evaluate 里返回 `vm.cfgRaw([...])` / `vm.cfg.tree...` 等嵌套对象, 跨内核序列化后内容丢失。
- **判别**: 同一个键 `cfgExists` 说 `true`、`cfgRaw` 说 `{}`; 明明 cfgSetPath 成功却"读不回来" ——
  看着像写入失败, 实为序列化假象(顶层键在、嵌套值丢)。
- **处置**: 断言在**页面内完成**: evaluate 里先 `JSON.stringify(...)` 成串再返回(串是准的),
  或直接返回布尔/字符串标量; 别把嵌套 Proxy 原样抛出内核。

### 桩服务配置树没有 trackers 段 —— 验绑定类逻辑要先注入正规站点

- **触发**: 验「域名交集绑定状态翻转」时发现 `cfgTrackerNames()` 为空。
- **判别**: 合成配置(harness)的 `/api/config/tree` 里 trackers 就是空的, 不是前端坏了。
- **处置**: evaluate 里 `cfgSetPath(["config","trackers"], { BTSchool: {...} })` 注入后再验;
  ❗别写 `names[0]` 兜底取名字 —— 空数组取值变 `undefined`, 会写出名为 `"undefined"` 的垃圾键。

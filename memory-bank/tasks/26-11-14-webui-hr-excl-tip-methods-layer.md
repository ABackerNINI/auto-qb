# 26-11-14-webui-hr-excl-tip-methods-layer — webui HR 排除 chip 每行渲染 TypeError 刷屏: 判定门跨文件调用少写 methods 层

**Status:** Done
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** webui HR 排除 chip 每行渲染 TypeError 刷屏: 判定门跨文件调用少写 methods 层
**Topics:** webui-hr-excl-tip-methods-layer

## 本篇只回答

只回答一个问题: cd14ffe6 之后 webui 每行渲染刷 `window.AQB_DECORATE.hrExclClass is not a function` 的根因是什么、怎么修、为什么静态测试没拦住。环境侧排查(缓存/部署/双实例)的取证过程不在此展开, 只留结论性教训(见 pitfalls/web-ui/mixin-method-call-misses-methods-layer.md)。

## 原始请求

1. 「WEBUI大量报错: TypeError: window.AQB_DECORATE.hrExclClass is not a function at Proxy.hrExclTip (hr.js:193:34) …」+ 「columns_grid.js:117 [dt_table.assertLayout] [torrent] 轨道 22 / 列头 22 / 行格 0 vs 列数 22」
2. 「Ctrl+F5 强刷没用」
3. 「报错的实例不在本机, git pull形式部署, 不存在部分同步」
4. (DevTools 取证数轮: Response 里能搜到 hrExclClass / 探测 undefined / 304 / Disable cache 仍 undefined / 三态指纹 tagClass+catClass+hrExclClass 全 undefined)
5. 「提交」

## 思考过程与决策

- **排查弯路(如实记)**: 前期按「浏览器混载旧 decorate.js」假设走了 8 轮环境侧取证(强刷/远端部署纯净性/304 缓存/双实例 loopback/字符数指纹), 各轮证据都真实但全是无关变量。决定性转折是三态指纹(tagClass 也 undefined)——任何已提交版本的 decorate.js 根层都该有这些方法(经 mixin 读 methods 层), 与「根路径直调」假设矛盾, 回读代码即锁定。
- **根因**: `decorate.js:122-123` 的 `window.AQB_DECORATE = { methods: {...} }`(根层仅 methods/computed 两键, hrExclClass 在 313 行 methods 层内); `hr.js:193`(cd14ffe6)调用写成根路径 `window.AQB_DECORATE.hrExclClass(...)` —— 根对象无此键, 任何干净新版页面加载必抛「is not a function」。assertLayout「行格 0」是行内格子渲染中断的下游症状, 非独立缺陷。
- **为什么静默上线**: pytest 静态守阵不执行 JS 调用路径; e2e 该批未跑(cd14ffe6 影响面仅 hr.js +7/-6, 零新增测试); cd14ffe6 动机里「无断言钉扎」的缺口以更硬的形态兑现了。
- **修法取舍**: 保持判定门单点化意图, 调用补 `.methods` 层(不用 `this.hrExclClass`, 维持原「不依赖 this」的直调语义); 守阵断言同批落地(修法经评审 3 轮收敛: 顶层片段锚定 → methods 不锚首键 → 定义缩进敏感锚定)。
- **评审口径**: 分面 2 派发(正确性+安全 / 测试缺口), 3 轮, 检 2/2 · 修 2 · 入池 0(轮 2 发现的引文校验因修复替换了被引行判 REFUTE 按纪律弃, 其修复面由轮 3 零发现覆盖)。

## 实现计划

1. 修 `hr.js:193` 调用路径补 `.methods` 层, 注释同步层级纪律 —— 可验: 守阵断言 + 页面刷新不再刷 TypeError。
2. `test_frontend_hr_safety_wiring` 新增第 5 组机械断言(结构/定义/调用路径/根路径直呼归零) —— 可验: 回退修复即红(评审员变异推演证实)。
3. 收尾: 坑档 pitfalls/web-ui/mixin-method-call-misses-methods-layer.md + test.full 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | hr.js 调用路径补 `.methods` 层 | Done(2026-11-14) |
| 2 | 守阵第 5 组断言(经评审 3 轮收敛) | Done(2026-11-14) |
| 3 | 坑档 + 基线切片 + 收尾回写 | Done(2026-11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

- 用户实报 → 8 轮环境侧排查(全部证伪) → 三态指纹转折 → 根因锁定 hr.js:193 调用层级 → 修复 + 守阵钉扎 → test.quick 6105 passed / 2 skipped → 评审 3 轮(分面 2 派发, 检 2/2 · 修 2) → 提交。

- 2026-11-14 10:03 修复 hr.js:193 判定门调用补 .methods 层; test_frontend_hr_safety_wiring 第 5 组断言钉扎层级(顶层片段锚定/methods 存在性/定义缩进敏感锚/调用路径+根路径直呼归零); 评审 3 轮(分面 2 派发, 检 2/2 修 2 入池 0, 轮 3 零发现); test.quick 6105 passed / 2 skipped; 坑档 pitfalls/web-ui/mixin-method-call-misses-methods-layer.md

# 26-09-25-2015-webui-hr-site-blank-screen — 站点接入数据白屏修复

> 摘要: 用户报「webui 无任何显示」, 定位为 441ffe4 踩中 `hr.js::hrSiteLine` 三处裸调用 `fmtDuration`/`fmtSize`(漏 `this.`)—— 未接入站点时分支恒提前返回 + 冒烟替身恒 None, 雷埋两轮不响; BTSchool 站点接入后随 `hrDurTitle` 挂进列表每行 title, 生产首屏渲染 ReferenceError, Vue 3 卸整树 = 全页白屏。修复 = 补三处 `this.`; 桩服务新增 `--hr-site` 站点判定注入开关堵替身盲区。**修复已验证, 已入库 `c00fc94`**。

## 已完成

- 定位: 生产 clone(D:/Projects/auto-qb, web.port=38080)代码与本 clone 逐字节一致(editable install)、后端日志零异常且搜索索引构建成功 ⇒ 白屏在前端; 本 clone 桩服务(无注入)冒烟 96 项全绿 ⇒ 差异在数据形态。
- 复现: `scripts/ui_harness.py --hr-site` 注入真实 `HrJudgement` 轮转全分支(站点命中/放行/豁免/未核实/None 回落) ⇒ 冒烟 10 项即崩(双 UI 同死「切种子视图」, `elementHandle.click: Element is not attached`); 浏览器实测切种子视图后 `#app` children=0(白屏), viewMode 持久化 ⇒ 刷新也白; 错误栈 `ReferenceError: fmtDuration is not defined @ hr.js:133 hrSiteLine ← hrDurTitle`。
- 修复: `hr.js::hrSiteLine` 三处裸调用补 `this.`(fmtDuration×2 / fmtSize×1), 全 shared 扫描确认无同类雷。
- 验证: `--hr-site` 桩上冒烟 **96 项全绿** + 三视图轮切 0 console 错误; pytest 1607 passed + 1 skipped(基线一致)。
- 坑回写: pitfalls/web-ui/vue-reactivity.md(+第四类静默白屏: methods 裸调用跨模块 methods, 数据分支不进就埋着)、pitfalls/testing/stubs-sim.md(+替身恒默认分支 = 功能域整体缺席); `--hr-site` 用法已写进两条坑。

## 待办

- ✅ 提交已完成 `c00fc94`(修复 + `--hr-site` harness 开关 + 两处 pitfalls + 本切片) —— 无遗留。

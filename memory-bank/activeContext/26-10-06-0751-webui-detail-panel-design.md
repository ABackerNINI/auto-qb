# WEBUI 种子详情面板重构 · 设计模板轮 + 实施轮 + 摸排轮

> 摘要: 用户命题 —— 详情面板抽屉改下方面板后: ①常规页竖排右边空一大块 ②Tracker/用户/内容三页平铺没设计感 ③收起状态疑似无用需论证。设计轮已闭环: `resources/detail-panel-templates/` 15 份可交互单文件模板 + `_brief.md` + 汇总报告 26-10-06-0723。**用户已拍板(26-10-06): 15 套全量实施可切换、每套挂载点尽量少、选择存 localStorage** —— 实施计划 [26-10-06-0838](../plans/26-10-06-0838-plan-webui-detail-panel-redesign.html) 已按 S1-S7 全量实施完成(实施结论与试用期使用说明见任务档案; 基线 26-10-06-1620)。〔摸排轮 26-10-07〕对实施产物(计划 26-10-06-0838 重构后的新版种子详情面板)做问题摸排, 产出汇总报告 [26-10-07-0542](../reports/26-10-07-0542-report-webui-detail-panel-variants-audit.html): 用户点名 4 问题全部确认(4K 横向比例失调 / general·traffic 变体缺图标 / 收起态不随点击切换种子 drawer.js:848 守卫误伤 / 15 变体 label 混入档位后缀透传 UI 下拉), 另新发现 P2×3(渲染抛错页签空白无降级 / 宽表格 scrollLeft 重渲染归零 / 收起摘要条陈旧数据)+ P3×5; 两项复核通过(S2 监听摘除干净、三皮肤接入无缺口)。报告含分阶段修复顺序建议。〔修复轮 26-10-07〕8 个子任务串行完成 8 笔提交(`9726b12f..2367555d`, 分支 feat/webui-detail-panel-audit-fixes), 修复全部点名问题(Q1-Q4 + P2×3 + P3-4..P3-7; P3-8 重复代码重构属重构批次未做, content 组可点击行键盘化需单独立项), 新增守阵 7 个测试函数; 收口 test.full 2712 passed + 4 skipped / TOTAL 99% / 52.13s(基线 26-10-07-0836)。结论与逐笔一览见任务档案 [26-10-07-webui-detail-panel-audit-fixes](../tasks/26-10-07-webui-detail-panel-audit-fixes.md)(用户拍板独立立档)。〔followups 修复轮 26-10-07〕用户再点名 4 个缺陷修复完毕: 4 笔提交(`039ea285`→`8677a415`, 分支 fix/webui-detail-panel-followups)—— 模板选择器定宽 240px 页签无关 / 切设置页返回变体宿主重挂(v-if 拆建后 `_dtMounted` 持旧节点, watch 进场补 `$nextTick(_dtSync)` / 显式换种子交棒 `_switchDrawerTarget` 软切换不闪空态(冷启动 loading 按 initialTab 同帧置位) / tooltip 锚定保活(place 单点 + reacquire 重解析 + rAF 帧环, 键盘 NaN 坐标由矩形基准兜住); 每项红验守阵 1 个测试函数, 真机 qB 116 种子浏览器实测四项全 PASS、零 console 错误; 收口 test.full 2717 passed + 4 skipped / TOTAL 99% / 42.08s(基线 26-10-07-1142)。见任务档案 [26-10-07-webui-detail-panel-followups](../tasks/26-10-07-webui-detail-panel-followups.md)。
> 最后活动: 2026-10-07 11:42

**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md, memory-bank/reports/26-10-06-0723-report-webui-detail-panel-redesign.html, memory-bank/plans/26-10-06-0838-plan-webui-detail-panel-redesign.html, memory-bank/reports/26-10-07-0542-report-webui-detail-panel-variants-audit.html, memory-bank/tasks/26-10-07-webui-detail-panel-audit-fixes.md, memory-bank/testing/baselines/26-10-07-0836-webui-detail-panel-audit-fixes.md, memory-bank/tasks/26-10-07-webui-detail-panel-followups.md, memory-bank/testing/baselines/26-10-07-1142-webui-detail-panel-followups.md

## 立档与闸门口径

- **立档: 已立** `memory-bank/tasks/26-10-06-webui-detail-panel.md`(Topics: webui-detail-panel-redesign, Status: Done)。依据: 命中 skill 立档阈值 #4(`reports/` HTML 报告制品)。各轮会话按「一个专题一个档案」在**该档案追加**, 不另新建。
- **摸排轮(26-10-07)**: 零代码改动(静态走查 + 报告), 基线 commit 332c1587(快进自 296d5223); `test.full` 实测记基线切片(收尾时随本专题入库); 摸排方式为静态代码走查(两个子智能体串行: 只读摸排 → 报告撰写), 未真机渲染验证。
- **设计轮/实施轮历史口径**: 已随各轮收尾固化进任务档案, 此处不再复述。

## 下一步

1. 修复轮: **已完成(2026-10-07)**, 逐笔一览与实测见任务档案 26-10-07-webui-detail-panel-audit-fixes; 后续候选 —— P3-8 变体重复代码重构(重构批次)与 content 组可点击行键盘化(需单独立项)。
2. 试用期使用(切换器位置 / 增删变体 = 1 文件 + 3 行 manifest)见任务档案「试用期使用说明」。

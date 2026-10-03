# 26-10-03-webui-drawer-redesign — WEBUI 种子详情抽屉重设计

**Status:** Open
**Added:** 2026-10-03
**Updated:** 2026-10-03
**Summary:** 主会话只委派: 阶段1调研子智能体出报告+3个选型模板(方案A底部停靠/B主从分栏/C非模态浮层, 推荐C先行); 拍板时用户改判「只写报告」, 实施波次未排期; 3个池内issue保持Open; 交付物未提交等指令。
**Topics:** webui-drawer-redesign
**Refs:** memory-bank/reports/26-10-03-0759-report-webui-drawer-redesign.html

## 原始请求

用户指派 (2026-10-03): 解决 3 个池内 issue —— 26-10-01-2108-feat-webui-shortcuts-drawer-nav (抽屉打开时上下键切种子) / 26-10-01-2108-feat-webui-shortcuts-drawer-open (Alt+1~4 列表侧直接开抽屉定位页签) / 26-10-01-2119-feat-webui-drawer-redesign (抽屉整体重做); 追加关键约束: 目前抽屉显示时模糊种子列表, 键盘切换时看不清当前选中行, 重设计必须解决; 要求调研成熟方案, 做 3 个简单模板供选择, 写一份报告。流程要求: 主会话只委派总结不实施, 串行派单防超并发, 代码任务每阶段单独提交, 非代码交付物等提交指令。

## 思考过程与决策

- 拆解为 4 阶段串行: ①调研(报告+3模板, 不提交) → ②拍板选型 → ③实施(按选型分波, 每波单独提交) → ④收尾(测试/issue关闭/回写)。
- 阶段1调研一次成功, 关键取证 (2026-10-03 @ develop 112baefc, 报告内含全行号): blur 病灶为三皮肤各一处 `.drawer-mask` 的 `backdrop-filter: blur(2px)` (atlas/console 的 css/dialogs.css L3-4/L6-7, prism 的 css/views.css L546-547), 是 PERF-01 后全站仅存 blur; 抽屉模板单点 `shared/tpl/drawer.html` 三皮肤共用; 快捷键注册表 `shortcuts.js` L266-279 (Alt+Digit1-4, scope drawer), 派发浮层分支 L433-438 是「列表侧 Alt+1~4 无效」的实现层原因; 既有列表光标模型 `_kbMove/_kbApplyCursor/_kbScrollRowIntoView` 可直接复用。
- 三方案: A 底部停靠面板 (qBt 式, 改造面 M-L) / B 主从分栏 (L, 宽表压缩+行窗口化几何回归面最大, 不推荐) / C 非模态浮层 (摘 blur+遮罩降档~0.15+高亮行跟随自动滚动, 改造面 S-M, 模板不动, 页签记忆/长文本截断/FX-22 全保留)。调研推荐: C 先行落地三个 issue, A 列为 issue 2119 的终态演进另立计划。
- **拍板 D1: 用户改判「只写报告」** —— 阶段②③④ (选型/实施/收尾实施) 全部取消; 报告与模板留在工作区不提交, 等用户提交指令; 实施波次仅在报告中备查, 需要时须用户再授权。

## 实现计划 (仅备查, 未排期, 来自报告 §建议实施波次)

1. 波1 (S): 抽屉内上下键切种子 —— shortcuts.js 注册 2 动作 + drawer.js `drawerNav(delta)` + 防抖 → 关 issue drawer-nav
2. 波2 (S): Alt+1~4 列表侧开抽屉定位页签 —— scope 调整/拆双条目 + 无选中兜底 → 关 issue drawer-open
3. 波3 (S-M): 去 blur + 遮罩降档 + kb-cursor 增强 + 抽屉收窄 (三皮肤各 1-2 行, 完成 PERF-01 全站归零) → issue drawer-redesign 轻量部分
4. 波4 (M, 可选): 常规页信息密度微调 → issue drawer-redesign
5. 波5 (L, 长期): 方案 A 底部停靠终态, 单独立计划

## 子任务状态表

| 子任务 | 状态 | 产出 |
|---|---|---|
| 阶段1 调研 (现状取证+成熟方案+报告+3模板) | Done | reports/26-10-03-0759-report-webui-drawer-redesign.html + reports/26-10-03-drawer-redesign-templates/ 三模板 |
| 阶段2 拍板选型 | Dropped | 用户改判「只写报告」, 不选型 |
| 阶段3 实施 (波1-3 按选型) | Dropped | 未排期, 待用户再授权 |
| 阶段4 收尾 (测试/issue关闭/回写) | Open | 随未来实施轮执行 |

## 进度日志

- 2026-10-03 08:27 — 建档。开工 sync 成功 112baefc; 阶段1调研子智能体一次成功 (55 次工具调用, 零异常), 产出 4 个新文件 (报告 + 3 模板, 均过 HTML 标签配平与 node --check 静态校验; 子代理环境无浏览器, 可视化冒烟未做); 相邻 issue selection-follow-mouse (用户未点名) 只在报告 04 节提关联未纳入。拍板 D1 = 用户选「只写报告」→ 阶段2-4 实施面取消, 本档案转 Open 备查。零代码改动, 测试基线沿用 26-10-03-0542 (2309 passed + 3 skipped / 99%), 未跑新基线; 3 个 issue 保持 Open 未认领; 交付物 untracked 等提交指令。

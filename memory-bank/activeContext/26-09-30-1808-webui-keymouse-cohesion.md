# WEBUI 键鼠割裂调研 — activeContext

> 摘要: 用户报「WEBUI 快捷键上下移动与鼠标点击割裂感很强, 鼠标在顶部按一下键盘跳到最下方」。本轮纯调研未动代码: 代码取证三场景(无光标 ↑ 落末行的极值回落 / 鼠标点击入口不回写 kbCursor / 残留光标跳回) + 业界调研(APG / VS Code / Gmail / 文件管理器 / 组件库)收敛三法则 → 报告 [reports/26-09-30-1806-report-webui-keymouse-cohesion.html](../reports/26-09-30-1806-report-webui-keymouse-cohesion.html), 推荐方案 B(点击落光标 + 回落口径改视口就近), 方案 C(roving tabindex)缓议。
> 最后活动: 2026-09-30 18:08

## 已完成

- 代码取证: shortcuts.js 引擎 / selection.js 鼠标路径 / 四视图模板视觉双轨(kb-cursor 与 selected 已分立) / hover-keynav-fight 坑档先例, 三场景定位完毕(取证细节见报告 §02 与档案 tasks/26-09-28-webui-keyboard-shortcuts.md 进度日志 18:06 条)。
- 业界调研(后台代理 42 次检索取证): 六方向来源齐全, 收敛「光标三分 / 点击衔接 / 最小滚动」三法则; 对照本项目六项达标四项, 差距仅「点击衔接」与「回落口径」两处状态口径, 不需要重构。
- 报告落盘 memory-bank/reports/26-09-30-1806-report-webui-keymouse-cohesion.html(doc-topic=webui-keyboard-shortcuts, 恒 Done); tasks 档案追加子任务 #6 + 进度日志 + 双向 Refs。

## 正在进行

- 等用户拍板: 方案 B(推荐, 含唯一口径决策点——普通点击出现 kb-cursor 视觉反馈是否接受) / 仅改回落口径(A) / 含 a11y 的 C(缓议)。
- 拍板后另出计划文档(memory-bank/plans/, delivery-artifact)再实施; 实施注意项已写报告 §07(禁 scrollIntoView 红线 / 守阵联动 / 注释与 _kbHint 文案同步)。

## 附带: 切片数守卫触发的一次蒸馏 (2026-09-30 18:08)

- 本切片新建后 activeContext 达 71 > 上限 70(test_kb_active_context_slices_are_valid 红), 按守卫提示蒸馏: 删除 5 份**已完结且归宿明确**的切片 —— 26-09-24-2029-commands-engine-encoding(坑档 ops/console-encoding.md + 引擎代码)、26-09-25-0555-webui-ext-hr-logging(自注「已立档+已推送, 无未完事项」→ tasks/26-09-25-webui-ext-hr-logging.md)、26-09-25-0643-test-gbk-false-red(已入库 a760da0, KB 已回写)、26-09-25-1805-webui-deadcode-cleanup(已入库 c4fcc0c)、26-09-25-1835-webui-expand-state-across-views(已入库 2541c4e, 判据在 pitfalls/web-ui/ui-location-persist.md)。逐份核实无独有未完事项后才删; 含待办的老切片(tracker-url-source-sanitize 等)一律未动。现 66 份。

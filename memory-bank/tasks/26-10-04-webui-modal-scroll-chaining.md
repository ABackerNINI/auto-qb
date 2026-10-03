# 26-10-04-webui-modal-scroll-chaining — WebUI 弹窗滚轮穿透背景滚动 (分析报告轮)

**Status:** Open
**Added:** 2026-10-04
**Updated:** 2026-10-04
**Summary:** 用户报「WEBUI 弹窗上滚鼠标滚轮会连带滚动下方种子列表」: 阶段 1 代码盘点定性成因 —— 种子列表纵向滚动由 document 承担 (html/body 无 overflow), 遮罩弹窗是 #app 子节点且 .modal-mask/.modal 无 overflow, 全库无 overscroll-behavior/滚动锁/wheel 拦截, 滚轮沿 DOM 链直达 document; 遮罩模态共 12 个预计全部复现 (有内滚区 8 个滚到边界后连锁, 无内滚区立即连锁)。「列」窗口实为无遮罩 .col-menu 弹层, 连锁观感≈正常页面滚动 → 用户「添加种子要改 / 列窗口不改」假设经机制裁决成立, 遮罩/无遮罩分界线即改动面天然边界。阶段 2 联网调研四流派 (overscroll-behavior / 锁 document 派 / JS 拦截派 / dialog·inert) + qB 官方与 VueTorrent 先例。产出分析报告 reports/26-10-04-0128-report-webui-modal-scroll-chaining.html (8 节 dark 单文件): 推荐 三皮肤 .modal-mask 加 overflow:hidden + overscroll-behavior:contain 为主 (11/12 由共享壳一处覆盖, HR 专属遮罩 .hr-full-mask 补一行, 模板零改动) + ui_feedback._openModal 单点 CSS.supports 特征检测兜底老 Safari/iOS<16。主会话只委派, 3 个子智能体串行一次成功 0 异常失败。**停在 3 项拍板: ① JS 兜底本期做/拆二期 (推荐做) ② 遮罩 overflow hidden/auto 变体 (推荐 hidden) ③ 无遮罩浮层确认不改 (推荐维持); 拍板后另出实施 plan。**

**Topics:** webui-modal-scroll-chaining

## 原始请求

用户指令: 「WEBUI弹窗窗口滑动鼠标滚轮会导致下方的种子窗口滑动, 先分析主流的做法, 然后决定怎么改, 哪些要改。比如添加种子弹窗需要改, 但"列"窗口应该不需要改。写一个分析报告」。工作方式: 主会话先拆解任务再派子智能体分阶段串行实施 (强关联合并、特大拆小防 O(n²) token 与进度全丢, 不并列防超并发), 待拍板先询问, 主会话只委派总结不实施; 完成后等提交指令; 子智能体非正常失败 3 次即停待人工。

## 思考过程与决策

- **三阶段串行委派** (强关联合并后): 阶段1 代码盘点 (弹窗清单+滚动链机制) → 阶段2 主流做法联网调研 → 阶段3 汇总决策+报告撰写; 阶段间发现落盘 `tmp-analysis/modal-scroll/phase{1,2}-findings.md` (gitignore) 防出错进度全丢。全部一次成功, 子智能体异常失败 0 次。
- **机制定案** (阶段1, file:line 证据见报告 §3): document 承担列表纵向滚动 + 弹窗节点无 overflow + 全库零滚动锁 → 滚轮按 DOM 链直达 document 带滚背景。有内滚区弹窗 (添加种子 `.add-dialog-body{overflow-y:auto}` 等 8 个) 滚到边界后连锁, 无内滚区 (历史流量/短确认框等) 立即连锁。
- **弹窗分型**: 遮罩模态 12 个 (添加种子/选择位置/管理分类标签/标签与分类/通用确认输入/历史流量/快捷键帮助/qB 流量图/qB 分组流量/统计/HR 全屏); 无遮罩浮层 (列选择器 `.col-menu`/限速/筛选右键菜单) 不在缺陷语义内。
- **用户假设裁决**: 成立 —— 添加种子=遮罩模态要改; 列窗口=无遮罩弹层不改; 遮罩/无遮罩分界线既是缺陷判据也是改动面天然边界 (视觉隔绝语义 vs 正常页面滚动语义)。
- **方案推荐** (阶段3, 报告 §5): 主 = 三皮肤 `.modal-mask` `overflow:hidden` + `overscroll-behavior:contain` (MDN 背书, 零 JS 零布局位移、不误伤无遮罩浮层; 11/12 共享壳一处覆盖, 12 号 HR `.hr-full-mask` 补一行, 全部模板零改动); 辅 = `ui_feedback._openModal` 单点 `CSS.supports` 特征检测的非 passive wheel/touchmove 捕获拦截 (≈40 行, 仅老 Safari/iOS<16 生效)。不选锁 document 派 (遮罩断链无滚动条位移, 无补偿必要), 不选 `<dialog>`/Teleport 重构 (不值)。
- **残留风险** (报告 §7): JS 兜底 allow-list 漏登记会误锁弹窗内滚; overscroll-behavior caniuse 标 partial support, 需三皮肤真机验证。
- **本档案不声明 `**Refs:**`**: 报告出厂冻结且本轮可改文件清单不含报告 doc-refs meta, 单向声明会触发认领链守卫「目标未反向声明」; 报告 ↔ 本档案由同键 `webui-modal-scroll-chaining` 在 doc-map 专题视图归组, 正文链接不构成声明 (check_claim_chain 只扫声明方)。

## 实现计划

未出 —— 报告停在拍板: 3 项分叉 (① JS 兜底本期做/拆二期 ② 遮罩 overflow hidden/auto 变体 ③ 无遮罩浮层维持不改) 由用户裁决后, 另出 plans/ 单文件 HTML 实施计划 (预计改动面: 三皮肤 css/dialogs.css + ui_feedback.js, 全部模板零改动; 报告 §5/§6/§7 为先导)。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| 1 | 阶段1 代码盘点: 弹窗清单+滚动链机制 | Done | tmp-analysis/modal-scroll/phase1-findings.md (12 模态+机制定案) |
| 2 | 阶段2 主流做法联网调研 | Done | tmp-analysis/modal-scroll/phase2-findings.md (四流派+先例+URL) |
| 3 | 阶段3 汇总决策+分析报告 | Done | reports/26-10-04-0128-report-webui-modal-scroll-chaining.html |
| 4 | 用户拍板 3 项分叉 | Open | 报告 §5/§6 待裁决 |
| 5 | 实施计划 plans/ + 实施轮 | Open | 拍板后启动 |

## 进度日志

- **2026-10-04 01:47** 会话开工 sync 成功 3c7df550 (远端有更新快进)。三阶段串行子智能体全部一次成功 (0 异常失败): 盘点 → 调研 → 报告。报告验收通过: doc-* meta 5 项 / color-scheme:dark (--bg #0f1420 / --ink #dce4f4 合规) / 零外链 / 8 节 / 标签配平零错误 (git-bash grep 对 `</` 前缀模式失灵, 以 Python html.parser 权威核验)。回写件 (本档案 + activeContext 切片 + kb.index 重建) 留工作树未提交, 等用户提交指令; 纯文档轮零代码改动, 未跑 test.full 未出基线 (同可行性轮先例)。

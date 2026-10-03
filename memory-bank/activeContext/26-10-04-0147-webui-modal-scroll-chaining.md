# WebUI 弹窗滚轮穿透背景滚动 (报告已出, 停在拍板)

> 摘要: 2026-10-04 用户报「弹窗上滚滚轮会连带滚动下方种子列表」, 要求先析主流做法再判哪些要改并出
> 分析报告。成因 = document 承担列表纵向滚动 + .modal-mask/.modal 无 overflow + 全库零滚动锁,
> 滚轮沿 DOM 链直达 document; 遮罩模态 12 个全部复现 (8 个有内滚区滚到边界后连锁, 其余立即连锁)。
> 「列」窗口是无遮罩 .col-menu 弹层 → 用户「添加种子要改 / 列窗口不改」假设经机制裁决成立。
> 推荐: 三皮肤 .modal-mask overflow:hidden + overscroll-behavior:contain (共享壳一处覆盖 11/12,
> HR 专属遮罩 .hr-full-mask 补一行, 模板零改动) + ui_feedback._openModal 特征检测 JS 兜底
> 老 Safari/iOS<16。报告 reports/26-10-04-0128-report-webui-modal-scroll-chaining.html (8 节 dark)。
> 最后活动: 2026-10-04 01:47

## 本轮产出 (2026-10-04)

- 三阶段串行子智能体 (主会话只委派): 代码盘点 → 联网调研 → 决策+报告, 一次成功 0 异常失败;
  中间发现落盘 tmp-analysis/modal-scroll/ (gitignore, 报告已自含全部事实, 不依赖临时件)。
- 逐弹窗判定: 12/12 遮罩模态要改 (共享壳一处改 + HR 遮罩一行, 全部模板零改动); 无遮罩浮层全部不改。
- 档案: [tasks/26-10-04-webui-modal-scroll-chaining](../tasks/26-10-04-webui-modal-scroll-chaining.md)
  (Open); 回写件全部留在工作树未提交, 等用户提交指令。

## 状态

停在 3 项拍板: ① JS 兜底本期做/拆二期 (推荐做) ② 遮罩 overflow hidden/auto 变体 (推荐 hidden)
③ 无遮罩浮层确认不改 (推荐维持)。拍板后另出实施 plan → 实施轮。提交待用户显式指令。

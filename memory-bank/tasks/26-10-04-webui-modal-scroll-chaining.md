# 26-10-04-webui-modal-scroll-chaining — WebUI 弹窗滚轮穿透背景滚动 (报告 + 实施, 已完成)

**Status:** Done
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

实施轮未另出 plans/ 单文件 HTML —— 用户在报告 §5.4 三项分叉上直接拍板 (① JS 兜底本期一并做
② hidden + 6 号壳 max-height 加固子项纳入 ③ 无遮罩浮层确认不改) 后, 按报告 §7.1 落点清单
拆三阶段串行子智能体直接实施 (报告即计划): P1 CSS 主案 → P2 JS 兜底 → P3 验证。

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| 1 | 阶段1 代码盘点: 弹窗清单+滚动链机制 | Done | tmp-analysis/modal-scroll/phase1-findings.md (12 模态+机制定案) |
| 2 | 阶段2 主流做法联网调研 | Done | tmp-analysis/modal-scroll/phase2-findings.md (四流派+先例+URL) |
| 3 | 阶段3 汇总决策+分析报告 | Done | reports/26-10-04-0128-report-webui-modal-scroll-chaining.html |
| 4 | 用户拍板 3 项分叉 | Done | ①JS 兜底本期做 ②hidden+加固子项 ③无遮罩浮层不改 |
| 5 | P1 CSS 主案 (遮罩壳+HR 特例+内滚区+6 号壳加固) | Done | 提交 fdb97468: 8 CSS 文件, overscroll 0→30 处 |
| 6 | P2 JS 兜底 (CSS.supports 门控拦截) | Done | 提交 b989df10: ui_feedback.js +52 行 IIFE |
| 7 | P3 验证 (静态核查+测试) + 守卫修复 | Done | 提交 e5a59841 压回 700 行; test.full 2423 passed 基线 26-10-04-0353 |
| 8 | 真机验收 (报告 §7.3 走查) | Open | 待用户真机/DevTools 确认, 静态验证不可替代 |

## 进度日志

- **2026-10-04 01:47** 会话开工 sync 成功 3c7df550 (远端有更新快进)。三阶段串行子智能体全部一次成功 (0 异常失败): 盘点 → 调研 → 报告。报告验收通过: doc-* meta 5 项 / color-scheme:dark (--bg #0f1420 / --ink #dce4f4 合规) / 零外链 / 8 节 / 标签配平零错误 (git-bash grep 对 `</` 前缀模式失灵, 以 Python html.parser 权威核验)。回写件 (本档案 + activeContext 切片 + kb.index 重建) 留工作树未提交, 等用户提交指令; 纯文档轮零代码改动, 未跑 test.full 未出基线 (同可行性轮先例)。

- **2026-10-04 03:53** 实施轮完成。三项拍板落地, 3 个实施子智能体串行 0 异常失败: P1 CSS 主案
  (提交 fdb97468: 8 文件, overscroll-behavior 全库 0→30 处; .modal-mask×3 + .hr-full-mask×3 加
  overflow:hidden+contain, 8 类内滚区补 contain, 6 号壳 .modal×3 补 max-height 内滚加固) →
  P2 JS 兜底 (提交 b989df10: ui_feedback.js +52 行, CSS.supports 注册期门控 + document 级捕获
  wheel/touchmove {passive:false} + 白名单 8 内滚区+modal 壳, 豁免 Ctrl+滚轮) → P3 验证
  (提交 e5a59841)。每阶段完成即本地 commit (未走 ship), 完毕 rebase 到新基线后线性快进合并回
  develop。**与报告原稿的两处实施偏差**: ① 兜底挂点从 _openModal 改 document 级捕获 (报告 §5.1
  第四层已自纠 —— _openModal 只驱动 6 号壳, 覆盖不了 12/12); ② 6 号壳加固从「.modal-body 内滚」
  改「.modal 壳内滚」—— 通用 .modal 是块布局, body 加 overflow 是 no-op, flex 化会改 margin 塌缩
  引发全站确认框间距回归; 壳内滚内容不超高时逐像素等价。**守卫拦截一次**: atlas components.css
  701 行超单 CSS 700 行上限 (test_web.py::test_frontend_template_split_wiring), 追加行并入上一行
  压回 700 (属性零删减)。P3 顺带发现 .modal-members 类无模板/JS 构造点 (疑似遗留死类, 白名单含之
  无害), 按范围守恒未处理。基线 26-10-04-0353: test.full 2423 passed + 3 skipped, 28.82s, TOTAL 99%。
  真机 §7.3 走查未做 (子任务 #8 Open)。收尾回写件随主提交入库。

- **2026-10-04 04:03** 遗留观察清偿轮: 用户指令「确认后移除死类」。全库核查确认 `.modal-members`
  连同子选择器 `.modal-member-row` / `.mm-site` / `.mm-name` / `.mm-path` 均零构造点 (HTML 模板/JS
  classList 均无; `.member-row` 无前缀版是活类勿混; 废弃锚点 = delete_flow.js:202 注释「DLG-01
  成员明细已移除」), prism 皮肤本就无此类。三处移除: atlas/css/views.css 成员明细整块 10 行 +
  console/css/views.css 整块 11 行 + ui_feedback.js 白名单摘 "modal-members" (8 内滚区 → 7 类)。
  基线 [26-10-04-0403](../testing/baselines/26-10-04-0403-webui-modal-members-dead-class-removal.md):
  test.full 2423 passed + 3 skipped, 29.88s, TOTAL 99% (与 0353 持平)。改动留工作树等用户提交指令。

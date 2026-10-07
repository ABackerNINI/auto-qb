# 26-10-04-webui-tooltip-declutter — WEBUI 复述型 tooltip 全量移除(67 处)+ 不复活守卫(含 26-10-07 二轮去冗与锚定下放)

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-07
**Summary:** 按判定报告 reports/26-10-04-0815 全量移除 webui 复述型 tooltip 67 处(A-G 组 66 处散在 10 个共享模板 + H1 columns.js; dialogs.js A5 按报告「精简」而非全删), 新增守卫 test_removed_redundant_tooltips_stay_removed 钉死已删文案; 全量 2462 passed + 4 skipped / 99%(基线 26-10-04-0900)。二轮(2026-10-07): 详情面板去冗 45 处 + 容器级 title 锚定下放 6 组(修 tracker 状态卡片栅格错位), 真浏览器 12 场景全 PASS(基线 26-10-07-2313)。
**Topics:** webui-tooltip-declutter
**Refs:** memory-bank/reports/26-10-04-0815-report-webui-tooltip-declutter.html, memory-bank/testing/baselines/26-10-04-0900-webui-tooltip-declutter.md, memory-bank/issues/26-10-07-2309-test-webui-peers-harness.html, memory-bank/testing/baselines/26-10-07-2313-webui-tooltip-declutter-r2.md

## 原始请求

用户主诉: 复述型 tooltip 纯冗余且可能遮挡元素; 图标/文字自明且误点无害的也应移除。先出判定报告再实施。

## 思考过程与决策

- **判定报告先行**(reports/26-10-04-0815, doc-status Done): 全量枚举三皮肤共享模板 title / :title + JS 动态赋值共 **133 处**, 按 R1 复述 / R2 自明+无害 / R3 截断兜底 / R4 信息增量 / R5 不可发现交互+后果预告 五类判据逐条判定: **移除 67(50.4%) / 保留 66**。
- **机制前提**: 全站悬浮提示统一由 shared/ui_feedback.js `.aq-tip` 拦截层渲染(唯一 tooltip 通道), 移除 = 纯删属性, 不动渲染机制, 三皮肤零成对改。
- **A5 例外**: statusbar 统计项是「精简」不是全删 —— dialogs.js sbStats 两处 title 只去掉「当前 peer 连接总数 · 」复述半句。
- **守卫形态**: 读模板/JS 源码断言代表性已删文案不复现(哪个文件写回去即红), 而非逐处快照 —— 判定为保留的 tooltip(截断兜底/操作说明/后果预告等)不在列, 误报面最小。

## 实现计划

分组实施(每分支一组提交): 状态栏 A 组(7 处 + A5 精简) → 顶栏 B 组(12) → 追剧/详情抽屉(12) → 对话框族(19) → 设置页/配置编辑器(16) → columns.js H1(1) → 补不复活守卫测试。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 判定报告(133 处全量清点, 移除 67 / 保留 66) | ✅ `72a7d274` |
| A 组 状态栏 7 处 + A5 sbStats 精简 | ✅ `80220a82` |
| B 组 顶栏页签 12 处 | ✅ `5c0412ff` |
| 追剧/详情抽屉 12 处 | ✅ `ae919a39` |
| 对话框族 19 处 | ✅ `728f92ab` |
| 设置页/配置编辑器 16 处 | ✅ `a33db037` |
| H1 columns.js 末处 + 守卫测试 | ✅ `e8203a3c` |
| 收尾 DoD(基线 / 索引 / progress 迁出) | ✅ |
| 遗留清理(孤儿 computed todayTrafficTitle / distTitle 删除; statusbar.html 3 处失实 title 注释改写; drawer.html:267 漏网 title「修改优先级」删除; qbTrafficTitle 核实仍被 drawer strong 消费, 保留) | ✅ |
| 二轮清点(详情面板 19 文件 + B区 qb_traffic_chart.js; 机械 17 / 边缘 37 / 错位 7 组) | ✅ |
| 二轮去冗 45 处(机械 17 + 边缘 28, 保留 5 组增量; 守阵 I 组 37 needle) | ✅ `94013201` |
| 锚定下放 6 组(dt04 色族胶囊 / 01 横幅 chips / 12 画布删 / 14 栏头 / 摘要条族 5 变体 / 04 虚拟卡) | ✅ `99fa6eef` |
| 验证(test.full 2757+4 / e2e fast 6 passed / 真浏览器悬浮 12 场景 PASS) | ✅ |
| 计划外发现入池(ui_harness FakeClient.peers_map 恒空, peers 页签 e2e 零覆盖) | ✅ |

## 进度日志

- **2026-10-04**: 判定报告落文(133 处清点 → 移除 67 / 保留 66), 待用户拍板两处边界或全量实施。
- **2026-10-04**: 用户拍板全量实施; 6 个实施提交落地(A-G 组 66 处模板 + H1 columns.js + A5 dialogs.js 精简), 守卫 `test_removed_redundant_tooltips_stay_removed`(tests/test_web.py)入库。改动面: 10 个共享模板(shared/tpl/ 下 statusbar / topbar / drawer / dialogs / dialogs-mgr / popovers / settings / settings-detail / shows / xtpl)+ columns.js + dialogs.js, tests/test_web.py +35 行。分支 webui-tooltip-declutter。
- **2026-10-04**: 收尾 DoD 完成 —— test.full **2462 passed + 4 skipped / 28.54s / TOTAL 99%**(基线 [testing/baselines/26-10-04-0900](../testing/baselines/26-10-04-0900-webui-tooltip-declutter.md); 相对上基线净增 2 = 本分支守卫 1 条 + 判定报告 HTML 落盘后 docs-forms 收集 +1); `kb.index` 重建; 完成条目迁出 [progress/implemented-webui.md](../progress/implemented-webui.md)。

### 二轮(2026-10-07, 分支 webui-tooltip-fix2, 两提交随本专题入库)

- **2026-10-07**: 用户报「tracker-状态卡片栅格-全部1/正常1 等tooltip位置不正确」, 命题先参照首轮口径去冗、再修位。只读审计: 详情面板 19 文件约 160 处 title 全量清点(qb_traffic_chart.js 本身 0 处, 图内悬浮是自绘 .hist-tip 不走 title 通道)—— 机械 R1/R2 命中 17、边缘 37、错位 7 组; 错位根因 = .aq-tip 锚点取 closest("[data-aq-tip]") 最内层, title 挂全宽容器时悬浮子元素以容器为锚弹到容器中上方。
- **2026-10-07**: 用户三拍板 —— ①范围=详情面板+qb流量图; ②边缘 37 条按信息增量分组执行(移除约 28 / 保留 5 组: IP 连接类型 / 对端自身进度 / 按进度估算 / 清除作用域 / 高亮澄清); ③dt04 总览行色族说明下放各胶囊、05 健康摘要条子胶囊删除后条级 title 一并删(防回退锚新错位)、错位 7 组全修(13/15 kpis 组随移除顺带解决)。
- **2026-10-07**: `94013201` 移除 45 处(A 组机械 17 + B 组拍板 28), 纯删 title 不动渲染机制; 守卫测试新增 I 组 37 needle(02:267 dt02-flag 的 title="${label}" 不在清单, needle 收窄避误伤); 09 表头核实有同口径 title 后其「会话累计」照删。`99fa6eef` 锚定下放 6 组: dt04 色族说明按 PILLS 拆 tip 字段 / 01 横幅 hr_reason 下放全部徽章与 chips / 12 画布教学 title 删除(.dt12-hint 静态位已含同要点) / 14 侧栏 title 下放栏头 h4 / 06·09·10·11·12 收起摘要条构成说明下放各计数 span / 04 虚拟合并卡 title 下放卡头 .dt04-st; ui_feedback.js 与 CSS 零改动。
- **2026-10-07**: 验证 —— test.full **2757 passed + 4 skipped / TOTAL 99%**(基线 [26-10-07-2313](../testing/baselines/26-10-07-2313-webui-tooltip-declutter-r2.md)); `npm run test:e2e:fast` 6 passed; 真浏览器(ui_harness 桩 + Playwright)悬浮实测 **12/12 PASS**(浮层与悬浮元素中心水平距 0.1~29.4px, 04 胶囊/01 徽章/06·09 摘要条/05 删净无弹/保留项在位/console 零错误), 9 张截图存 .zcode-tmp/(临时证据, 已随工作区清理)。计划外发现 ui_harness FakeClient.peers_map 恒空(peers 页签 e2e 零覆盖, 当时靠 route 拦截注入合成数据完成实测)→ 入池 [issue 26-10-07-2309](../issues/26-10-07-2309-test-webui-peers-harness.html)(Open); 「DOM 中 title 渲染帧即迁 data-aq-tip」经核已有坑档 [injected-dom-title-migrated-to-aq-tip](../pitfalls/web-ui/injected-dom-title-migrated-to-aq-tip.md) 覆盖, 未新增、未计入复发(零返工成本)。

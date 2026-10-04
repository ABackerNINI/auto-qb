# 26-10-04-webui-tooltip-declutter — WEBUI 复述型 tooltip 全量移除(67 处)+ 不复活守卫

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04
**Summary:** 按判定报告 reports/26-10-04-0815 全量移除 webui 复述型 tooltip 67 处(A-G 组 66 处散在 10 个共享模板 + H1 columns.js; dialogs.js A5 按报告「精简」而非全删), 新增守卫 test_removed_redundant_tooltips_stay_removed 钉死已删文案; 全量 2462 passed + 4 skipped / 99%(基线 26-10-04-0900)。

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

## 进度日志

- **2026-10-04**: 判定报告落文(133 处清点 → 移除 67 / 保留 66), 待用户拍板两处边界或全量实施。
- **2026-10-04**: 用户拍板全量实施; 6 个实施提交落地(A-G 组 66 处模板 + H1 columns.js + A5 dialogs.js 精简), 守卫 `test_removed_redundant_tooltips_stay_removed`(tests/test_web.py)入库。改动面: 10 个共享模板(shared/tpl/ 下 statusbar / topbar / drawer / dialogs / dialogs-mgr / popovers / settings / settings-detail / shows / xtpl)+ columns.js + dialogs.js, tests/test_web.py +35 行。分支 webui-tooltip-declutter。
- **2026-10-04**: 收尾 DoD 完成 —— test.full **2462 passed + 4 skipped / 28.54s / TOTAL 99%**(基线 [testing/baselines/26-10-04-0900](../testing/baselines/26-10-04-0900-webui-tooltip-declutter.md); 相对上基线净增 2 = 本分支守卫 1 条 + 判定报告 HTML 落盘后 docs-forms 收集 +1); `kb.index` 重建; 完成条目迁出 [progress/implemented-webui.md](../progress/implemented-webui.md)。

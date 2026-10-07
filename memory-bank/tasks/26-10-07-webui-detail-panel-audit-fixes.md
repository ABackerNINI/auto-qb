# 26-10-07-webui-detail-panel-audit-fixes — 详情面板变体审计问题修复轮

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 08:36
**Topics:** webui-detail-panel-audit-fixes
**Summary:** 摸排报告 26-10-07-0542 的修复轮: 8 个子任务串行完成 8 笔提交(`9726b12f..2367555d`, 分支 feat/webui-detail-panel-audit-fixes), 修复 Q1-Q4 + P2×3 + P3-4..P3-7; 未做 P3-8(重复代码重构, 属重构批次)。每步 test.quick 全绿(2706→2712), 收口 test.full **2712 passed + 4 skipped / TOTAL 99% / 52.13s**(基线 26-10-07-0836), 新增守阵 7 个测试函数。
**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md,memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md,memory-bank/testing/baselines/26-10-07-0836-webui-detail-panel-audit-fixes.md

## 原始请求

按摸排报告 26-10-07-0542(报告本体见 `memory-bank/reports/`, 是「出厂即冻结」的证据快照, 不随修复回写)的分阶段修复顺序拆 8 个子任务, 派子智能体串行执行, 修复全部点名问题: 用户点名 4 问题(Q1-Q4)+ 新发现 P2×3 + P3 项。

## 思考过程与决策

- **拍板记录(用户)**:
  - Q3(收起态点行)= 仅换目标不展开 —— peek 行快照同步摘要, 不自动展开面板;
  - Q1(4K 比例失调)= 按「最大可读宽度」口径 —— 变体内容层限宽 1400px 居中;
  - 范围 = 报告全部 5 批修复顺序全做(逐批拆子任务派子智能体串行);
  - P3-6(content 组折叠口径)= 跨种子保持 —— 删 render() 开头显式清账行, 同名目录(剧集系列)延续折叠选择; dt11 勾选集(批量优先级是真提交)保留重置。
- **未做项**: P3-8(变体重复代码重构, 属重构批次不入本轮); content 组可点击行/树图块键盘化(嵌套交互语义冲突, 需单独立项, 记于提交 `8d63f565`)。
- **报告冻结不回写** ⇒ 本档案与报告不建正式认领链(报告 doc-refs 只指专题前史档案), 以正文引用。
- **立档形态(用户拍板)**: 独立新档案, 不并入专题前史档案 `26-10-06-webui-detail-panel.md`(与「一个专题一个档案」口径的冲突由用户当场裁决; 两档案互引)。

## 实现计划

报告修复顺序拆 8 个子任务串行执行, 每步 test.quick 全绿后提交; 全部改动限于 WebUI 静态层(drawer.js / selection.js / `shared/drawer_tpl/*.js` / 核心层 CSS 注入单点)与 test_web.py 守阵, Python 产品代码零改动。

## 子任务状态表

| # | 提交 | 问题 | 改动 | 状态 |
|---|------|------|------|------|
| 1 | `9726b12f` | Q3+P2-3 | 收起态鼠标点行实时换目标: peek 行快照同步摘要不展开; 非常规页签静默补拉防陈旧摘要 | Done |
| 2 | `1f478379` | P2-1 | 变体渲染抛错五步回落经典层(摘挂载+destroy+清宿主+复位选择+落盘), 消灭空白页签 | Done |
| 3 | `58026d47` | Q1 | 变体内容层限宽 1400px 居中(.dt-host 单点) + 摘除 5 处 label/value space-between; traffic 双宿主不限宽 | Done |
| 4 | `5579050f` | Q4 | 变体展示名去「(高/矮/收起)」档位后缀改描述性命名, 15 处下拉项正名(变体 id/文件名/tab 零改动) | Done |
| 5 | `bbb66d36` | Q2 | 变体字段行消费既有 icon 数据 + traffic KPI 补图标 + 修 icoSvg 双重转义; sprite 36 id 三皮肤两两相等 | Done |
| 6 | `7514edbf` | P2-2 | 表格变体(dt06-09)重渲染保 scrollLeft, 5s 轮询刷新不再把横向滚动位打回最左 | Done |
| 7 | `8d63f565` | P3-4+P3-5 | 可访问性补齐(8 变体纯 div 控件 role=button+tabindex+keydown 委托+aria 随态) + 三列表 fetcher 失败态标记与九变体错误态分支 | Done |
| 8 | `2367555d` | P3-6+P3-7 | content 组折叠态跨种子保持(删清账行) + .dt-select 上限 160→240px + min-width:0 弹性收缩 | Done |

## 实测汇总

- 逐笔 test.quick 全绿: 2706→2707→2708→2708→2709→2710→2711→**2712** passed(各笔均 4 skipped; 第 4 笔守阵断言并入既有 registry wiring 守阵, passed 不变)。
- 收口 test.full: **2712 passed + 4 skipped / 覆盖率 TOTAL 99%(16061 语句 / 163 未覆盖 / 5496 分支 / 143 partial)/ 52.13s** —— 基线切片 `26-10-07-0836-webui-detail-panel-audit-fixes`(相对上基线 26-10-07-0548: passed +7 = 新增守阵, 语句/分支全同, 无回归信号)。
- 新增守阵 7 个测试函数(`git diff 75b0b890..2367555d -- tests/` 计数): test_frontend_drawer_collapsed_click_peek_target / test_drawer_tpl_render_error_fallback_classic / test_drawer_tpl_variant_width_discipline / test_drawer_tpl_variant_field_icons / test_drawer_tpl_table_variants_scrollleft_restore / test_drawer_tpl_a11y_and_fetch_error_states / test_drawer_tpl_cross_seed_fold_and_select_width。
- 各笔改动 JS 均过 `node --check`; sprite 核对 36 个 `#i-*` id 三皮肤两两相等。

## 进度日志

- 2026-10-07 06:26-08:23: 8 个子任务串行完成 8 笔提交(逐笔内容见上表, 提交信息含各笔实测数字), 每步 test.quick 全绿。
- 2026-10-07 08:36: 收尾 DoD —— test.full 实测记基线切片 `26-10-07-0836`; 本档案按用户拍板独立立档(与专题前史档案互引); activeContext 切片 26-10-06-0751 修复轮条目更新; kb.index 重建。回写核对: 根 README 与 memory-bank 主题文档无与新行为矛盾的表述(旧变体档位名仅命中报告/基线等冻结件), 无需额外回写。

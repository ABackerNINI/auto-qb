# 26-11-22-memory-bank-kb-nav-working-zone — kb.nav 正在处理区: 立项拍板与实施

**Status:** Done
**Added:** 2026-11-22
**Updated:** 2026-11-22
**Summary:** kb.nav 正在处理区: 立项拍板与实施
**Topics:** memory-bank-kb-nav-working-zone
**Refs:** memory-bank/plans/26-11-22-1742-plan-kb-nav-working-zone.html,memory-bank/active-context/26-11-22-1750-kb-nav-working-zone.md

## 本篇只回答

本篇记录 kb.nav「正在处理区」专题从立项拍板到实施验证的进度; 方案与取舍的权威在计划 `memory-bank/plans/26-11-22-1742-plan-kb-nav-working-zone.html`, 本篇只追「做到哪了」。

## 原始请求

1. 为 kb.nav 添加一个类似置顶区的「正在处理区」, 用于显示哪些件正在被处理。
2. 不依赖文档状态 `In Progress` 来决定成员资格 —— 手动加入。
3. 件转 `Done` 后自动从该区退出。
4. 操作类似置顶区, 入口放右键菜单, 位置放在置顶区下面。
5. 添加一个合适的图标 (类似置顶图标)。
6. 用户指定走 grilling → 建计划 → 提交三步流程。

## 思考过程与决策

- 三轮 grilling 拍板 D1–D11 (全档见计划 §06): 成员手动加入 (D1); 终态永久移除而非显示层过滤, 避免状态改回后「复活」(D2); 终态含 `Done / Dropped / Superseded` (D3); boot + 每次 30s 刷新都检查 (D4); 行内不加第二个图标, 改用整行左侧暖橙 `--amber` 色条 (D5); 色条让位于交互态, 优先级 多选 > 预览 > 工作 (D6); 右键批量完全对齐 pin, 冻结快照 + 幂等 + 落盘 (D7); 专区照置顶区同栏/可折叠/空则隐藏/不受筛选 (D8); pin 与 working 独立共存 (D9); 仅台账视图 (D10); 标题「处理中 · WORKING (n)」+ 闪电内联 SVG (D11)。
- 用户两处改判 (相对最初推荐): 行内图标 → 左色条 (嫌 pin 旁再加图标凌乱); 只认 Done → 三种终态都退出。
- 核心取舍: 工作集存 localStorage 纯个人偏好, 零后端; 终态退出落在 `pruneTerminalWorking()`, `derive()` 只删不增, 守住 30s 轮询不重播种的黄金法则。
- 评审: 1 轮 2 发现 (1 major `--warn` 令牌名错 / 1 minor `applyWorkCollapse` 函数归属错), 均经机械核验属实并修, 复评零 actionable; review.check 2/2 通过。

## 实现计划

计划文件: `memory-bank/plans/26-11-22-1742-plan-kb-nav-working-zone.html` (状态 Done)。四步 S1–S4 见计划 §04: 结构与样式 → 渲染与接线 → 终态自动退出 → 守阵与收尾; 三轮实施全部完成 (P1=S1+S2 / P2=S3 / P3=S4), 代码落点仅单文件壳 `nav_page.html`, 数据层 / 服务层零改动。

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| S0 | 立项: 三轮 grilling D1–D11 + 计划入库 + 档案立档 | Done | 2026-11-22 | 提交 `839eb6e5` |
| S1 | 结构与样式: DOM/CSS/常量/状态/工具函数 | Done | 2026-11-22 | P1 提交 `36078fc2` (S1+S2) |
| S2 | 渲染与接线: 专区渲染 + 右键/折叠/boot 装载 | Done | 2026-11-22 | P1 提交 `36078fc2` (S1+S2) |
| S3 | 终态自动退出: pruneTerminalWorking 在 boot + derive | Done | 2026-11-22 | P2 提交 `741f16bf` (boot 装载后 + derive 末尾各剪一次, derive 只删不增不 load) |
| S4 | 守阵与收尾: 新增 8 条守阵 + test.full 全绿 + 基线切片 + 文档回写 | Done | 2026-11-22 | P3 本轮; 实测数字见 kb.baseline |

## 进度日志

### R0 · 立档 (2026-11-22)

用户请求 → 三轮 grilling 拍板 D1–D11 (用户两处改判: 左色条替代行内图标 / 三种终态退出) → 只读调研确认落点 (单文件壳 `nav_page.html`, 数据层/服务层零改动) → 计划 `26-11-22-1742` 入库 Open + 本档案立档 → 评审 1 轮 2 发现全修零 actionable。零代码改动; S1–S4 待显式开工。

### R1 · 实施完成与守阵收尾 (2026-11-22)

三轮实施落地: P1 (`36078fc2`) 完成 S1+S2 —— `#workZone` 骨架 / 闪电内联 SVG / 双存储键 / 专区渲染 / 右键 + 折叠 + boot 装载接线; P2 (`741f16bf`) 完成 S3 —— `pruneTerminalWorking()` 在 boot 装载后与 `derive()` 末尾各调一次, derive 只删不增不 load (30s 轮询不重播种黄金法则); P3 本轮完成 S4 —— 先读代码与计划确认实现事实 (与计划 §04/D1–D11 一致, 未发现不符), 再在两份 kb-nav 测试文件 docstring 测试计划清单同步新增 8 条专题条目并补守阵: 骨架/键/闪电内联 SVG + 位置、boot 唯一装载 + derive 只 prune、终态三词严格删/NO_ST 不删/状态改回不回区 (node 回放)、双区独立 (node 回放)、隐藏件双重挡、色条层级 wip < sel < msel、折叠持久化 + aria 焦点、右键批量 + 冻结快照 + 幂等 + saveWorking + 移出按钮不误开抽屉 (node 回放)。顺带补回本档案缺的 `## 子任务状态表` 章节 (修掉 test_task_file_naming_and_sections 既有红)。`commands run test.full` 全绿, 实测数字见 kb.baseline 最新切片; 计划翻 Done, 活动切片按规程收尾。

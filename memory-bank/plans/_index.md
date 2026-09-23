# 计划 Index

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描 `plans/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: `In Progress` / `Open` / `Done` / `Dropped` / `Superseded`。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图见 [_doc-map.md](../_doc-map.md)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。

## In Progress

- [26-09-23-2008] [commands — 项目命令统一调用面 · 工程方案](26-09-23-2008-commands-plan.html) — `commands-unified-command-surface`
- [26-09-22-2350] [activeContext 多 clone 冲突治理 — 工程方案](26-09-22-2350-activecontext-conflict-plan.html) — `memory-bank-activecontext-conflict`
- [26-09-22-2318] [auto-qb 软件版本管理方案 · 版本号 / Tag / CHANGELOG / 发版流程](26-09-22-2318-version-management-plan.html) — `deps-version-management`
- [26-09-22-2038] [qB 移动已完成种子误判缺文件 · .!qB 过渡态容忍修复计划](26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html) — `backend-qb-move-dot-qb`
- [26-09-22-1801] [tracker URL 源头脱敏 · 可行性分析与实施计划](26-09-22-1801-tracker-url-source-sanitize-plan.html) — `tracker-url-source-sanitize`

## Open

- [26-09-22-2204] [部分种子 HR 的在线核实 — 可行性分析与实施计划](26-09-22-2204-partial-hr-site-verify-plan.html) — `backend-partial-hr-verify`

## Done

- [26-09-23-1959] [文档形态统一 — 计划与报告入库 · 工程方案](26-09-23-1959-memory-bank-doc-forms-plan.html) — `memory-bank-doc-forms`
- [26-09-22-2112] [src/auto_qb 目录结构优化 · 分层归拢计划（方案 C 定稿）](26-09-22-2112-src-layout-restructure-plan.html) — `src-layout-restructure`
- [26-09-22-1912] [运行期状态周期落盘 · 修复「非优雅终止丢失整个运行期状态」](26-09-22-1912-backend-state-periodic-flush-plan.html) — `backend-state-persistence`
- [26-09-22-1857] [修复计划 · 热重载 L2 分支重读磁盘 state, 运行期内存态被回滚](26-09-22-1857-hot-reload-l2-state-rollback-fix-plan.html) — `hot-reload-l2-state-rollback-fix`
- [26-09-22-1857] [web.py create_app 拆分计划 · 926 行工厂函数 → web/ 包 + 按域 Router](26-09-22-1857-web-create-app-split-plan.html) — `web-create-app`
- [26-09-22-1248] [知识库目录化重构 · memory-bank 全库分类 + 二级指针方案](26-09-22-1248-memory-bank-dir-refactor-plan.html) — `memory-bank-dir-refactor`
- [26-09-22-0812] [闸门自动运行 · my-commit-flow 修改方案](26-09-22-0812-commit-gate-auto-run-plan.html) — `commit-gate-auto-run`
- [26-09-21-1551] [列设置重置 · 双轨模型重设计计划](26-09-21-1551-column-prefs-intent-redesign-plan.html) — `webui-column-prefs`
- [26-09-21-0257] [审查报告 · 真机语料抓取 / 脱敏 / 离线回放 计划](26-09-21-0257-qb-corpus-capture-replay-plan-review.html) — `qb-corpus-capture-replay`
- [26-09-21-0024] [真实 qB 语料抓取 · 脱敏 · 离线回放 · 改造计划](26-09-21-0024-qb-corpus-capture-replay-plan.html) — `qb-corpus-capture-replay`
- [26-09-20-2225] [规则条件表达式化 · 重构计划](26-09-20-2225-rule-conditions-expression-plan.html) — `rule-conditions-expression`
- [26-09-20-2139] [真值改 torrents/info 直查 + 事件驱动 + 乐观 UI 简化 · auto-qb 计划](26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html) — `webui-optimistic-ui`
- [26-09-20-1836] [列设置被重置 · 多标签页同步修复计划](26-09-20-1836-webui-column-prefs-sync-plan.html) — `webui-column-prefs`
- [26-09-20-1702] [WEBUI 状态栏速度恒为 0 · 修复计划 · auto-qb](26-09-20-1702-webui-statusbar-speed-fix-plan.html) — `webui-statusbar`
- [26-09-20-1128] [把提交流程固化成 skill · 提案](26-09-20-1128-git-ship-skill-proposal.html) — `git-ship-skill-proposal`
- [26-09-20-0941] [Issue 分类型与表单瘦身 · 修改计划](26-09-20-0941-issue-typing-plan.html) — `issue-typing`
- [26-09-20-0906] [app.js 按域拆分 — 可行性分析与实施计划](26-09-20-0906-appjs-split-plan.html) — `appjs-split`
- [26-09-20-0234] [主循环 × WebUI 解耦 · 重构计划](26-09-20-0234-webui-decoupling-plan.html) — `webui-decoupling`
- [26-09-19-2245] [乐观 UI「撤下」修复计划 — auto-qb](26-09-19-2245-webui-optimistic-settle-plan.html) — `webui-optimistic-ui`
- [26-09-19-1745] [WEB UI 响应性计划 · 实施评估报表 — auto-qb](26-09-19-1745-webui-responsiveness-review.html) — `webui-responsiveness`
- [26-09-19-1433] [5000 种子仿真客户端 · 独立测试设计与可行性分析](26-09-19-1433-sim-client-5000-plan.html) — `sim-client-5000`
- [26-09-19-1241] [WEB UI 操作跟手性优化计划 · auto-qb](26-09-19-1241-webui-responsiveness-plan.html) — `webui-responsiveness`
- [26-09-19-0413] [auto-qb · 架构审查与优化修复计划](26-09-19-0413-architecture-audit-plan.html) — `architecture`
- [26-09-18-1928] [Memory Bank 任务档案命名 · 多 worktree 协作优化计划](26-09-18-1928-memory-bank-task-id-plan.html) — `memory-bank-task-id`
- [26-09-18-1743] [WEB UI 种子速度刷新滞后 · 根因定位与修复计划](26-09-18-1743-webui-speed-refresh-fix-plan.html) — `webui-speed-refresh-fix`
- [26-09-17-0901] [WEB UI 修复计划 · 第十轮 — 16 项分类拆解 · 根因定位 · 分阶段实施](26-09-17-0901-webui-fix-plan-round10.html) — `webui-fix-plan-round10`
- [26-09-17-0847] [WEB UI 修复计划 · 第九轮 — 25 项分类拆解 · 根因定位 · 分阶段实施](26-09-17-0847-webui-fix-plan-round9.html) — `webui-fix-plan-round9`
- [26-09-17-0346] [WEBUI 替代 qB 界面 · 波次三 实施交接文档](26-09-17-0346-webui-qb-replace-wave3-handover.html) — `webui-qb-replacement`
- [26-09-16-1128] [WEBUI 替代 qB 界面 · 波次三 需求拆解与修改计划 — auto-qb](26-09-16-1128-webui-qb-replace-wave3-plan.html) — `webui-qb-replacement`
- [26-09-16-0123] [WEB UI 替代 qB 界面 · 功能差距调研与可行性计划 — 只计划不改代码](26-09-16-0123-webui-qb-replacement-plan.html) — `webui-qb-replacement`
- [26-09-15-1534] [追剧视图 · 方案计划 — auto-qb WEB UI](26-09-15-1534-webui-shows-view-plan.html) — `webui-shows-view`
- [26-09-15-1504] [Tracker 分组与规则筛选 · auto-qb 实施计划](26-09-15-1504-tracker-group-plan.html) — `tracker-group`
- [26-09-15-1302] [TorrentRecord 全字段缓存 · 实施计划](26-09-15-1302-record-full-fields-plan.html) — `backend-torrentrecord-fields`
- [26-09-15-1241] [星图与棱镜 · auto-qb 两套 UI 命名与目录迁移计划](26-09-15-1241-webui-naming-plan.html) — `webui-naming`
- [26-09-15-1150] [依赖版本调研与锁定建议 — auto-qb](26-09-15-1150-dependency-lock-report.html) — `dependency-lock`
- [26-09-15-1124] [后端大文件拆分计划 — qbmanager 瘦身 · schema/torrents/validation 转包 · 只列计划不改代码](26-09-15-1124-backend-file-split-plan.html) — `backend-file-split`
- [26-09-15-1042] [WEB UI 优化计划 · 第八轮 (旧 UI) — 诊断定案 · 吸顶贴合 · 确认框补全 · 视图扩展](26-09-15-1042-webui-optimization-plan-v3.html) — `webui-optimization`
- [26-09-15-0956] [auto-qb · 新一代 WEB UI 实施计划](26-09-15-0956-webui-redesign-plan.html) — `webui-redesign`

## Dropped

(暂无)

## Superseded

- [26-09-15-0910] [auto-qb · WEB UI 第七轮优化计划](26-09-15-0910-webui-optimization-plan-v2.html) — `webui-optimization`
- [26-09-15-0658] [auto-qb · WEB UI 优化计划](26-09-15-0658-webui-optimization-plan.html) — `webui-optimization`

# 报告 Index

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描 `reports/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: `In Progress` / `Open` / `Done` / `Dropped` / `Superseded`。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图用 `commands run kb.docmap` 查(不落盘)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。

## In Progress

(暂无)

## Open

(暂无)

## Done

- [26-10-07-2031] [流量图曲线过陡的口径调研: 瞬时速度 · 区间平均 · 移动平均](26-10-07-2031-report-qb-traffic-rate-basis.html) — `qb-traffic-rate-basis`
- [26-10-07-0542] [WEBUI 详情面板 15 变体摸排 · 问题清单汇总报告](26-10-07-0542-report-webui-detail-panel-variants-audit.html) — `webui-detail-panel-redesign`
- [26-10-07-0208] [my-commit-flow 自我改写版本撕裂 · 临时目录快照自举可行性分析 · auto-qb](26-10-07-0208-report-my-commit-flow-self-snapshot.html) — `my-commit-flow-self-snapshot`
- [26-10-07-0204] [可行性报告 · auto-qb ↔ auto-qb.webui 采用 qB rid 式增量同步 · auto-qb](26-10-07-0204-report-webui-delta-sync-feasibility.html) — `webui-delta-sync`
- [26-10-07-0054] [复验报告 · 两条 WebUI perf issue 在内核化重构后是否仍成立 · auto-qb](26-10-07-0054-report-webui-perf-issues-recheck.html) — `webui-perf-issues-recheck`
- [26-10-06-0945] [WEBUI 表头 / 数值列对齐缺陷取证 · auto-qb](26-10-06-0945-report-webui-column-alignment.html) — `webui-column-alignment`
- [26-10-06-0723] [种子详情面板重构 · 设计模板轮 — 汇总报告](26-10-06-0723-report-webui-detail-panel-redesign.html) — `webui-detail-panel-redesign`
- [26-10-06-0620] [修复汇总报告 · 全项目 Code Review 分批修复(六批 28 issue) · auto-qb](26-10-06-0620-report-full-code-review-remediation.html) — `full-code-review-remediation`
- [26-10-05-1946] [块头基线 + Delta 行编码与按落盘切块 · 可行性分析](26-10-05-1946-report-qb-traffic-v4-delta.html) — `qb-traffic-v4-delta`
- [26-10-05-1036] [审计报告: 全项目全面 Code Review — 分批评审发现与分流(终版) · auto-qb](26-10-05-1036-report-full-code-review.html) — `full-code-review`
- [26-10-05-0854] [调研报告: 强制汇报确认机制与 qB 汇报状态接口](26-10-05-0854-report-reannounce-confirm-api.html) — `reannounce-confirm-api`
- [26-10-04-1730] [qB 流量历史 dat v3 设计报告 · auto-qb](26-10-04-1730-report-qb-traffic-storage-v3.html) — `qb-traffic-storage-v3`
- [26-10-04-1639] [WEBUI qB 流量图折线断裂取证报告 · auto-qb](26-10-04-1639-report-webui-qb-traffic-line-breaks.html) — `qb-traffic-line-breaks`
- [26-10-04-0815] [WEBUI tooltip 全量清点与去留判定 · auto-qb](26-10-04-0815-report-webui-tooltip-declutter.html) — `webui-tooltip-declutter`
- [26-10-04-0636] [qB 流量历史存储压缩与「速度 0 vs 断线」语义调研报告 · auto-qb](26-10-04-0636-report-qb-traffic-storage.html) — `torrent-traffic-stats`
- [26-10-04-0128] [WebUI 弹窗滚轮穿透背景滚动 · 分析报告](26-10-04-0128-report-webui-modal-scroll-chaining.html) — `webui-modal-scroll-chaining`
- [26-10-03-1505] [HR 波次引擎四现象故障取证 · 一直在拉取 / 核实「未核实」/ 失踪 0 波 · auto-qb](26-10-03-1505-report-hr-fetch-verify-forensics.html) — `backend-partial-hr-verify`
- [26-10-03-0759] [WEBUI 种子详情抽屉重设计 · 调研报告](26-10-03-0759-report-webui-drawer-redesign.html) — `webui-drawer-redesign`
- [26-10-03-0757] [WebUI 新增 qB 口径流量图可行性分析 · 全局/单种/分组三图 · auto-qb](26-10-03-0757-report-qb-traffic-charts.html) — `torrent-traffic-stats`
- [26-10-03-0504] [「删除类似标签」全局/站点作用域混淆: 三层根因取证与方案选型 · auto-qb](26-10-03-0504-report-webui-site-scope-confusion.html) — `webui-delete-tag-scope-confusion`
- [26-10-02-0508] [设置页未保存改动防护: 成熟方案调研与「刷新弹框 + 刷新后清零」对比 · auto-qb](26-10-02-0508-report-webui-unsaved-changes-guard.html) — `webui-settings-unsaved-changes`
- [26-10-01-2347] [兼容 Transmission 可行性分析 · qB 耦合面盘点 · auto-qb](26-10-01-2347-report-transmission-compat-feasibility.html) — `transmission-compat-feasibility`
- [26-10-01-2125] [memory-bank 生成物实时化与四工位专题目录化 · 可行性分析](26-10-01-2125-report-kb-artifacts-realtime-and-layout.html) — `memory-bank-dir-refactor`
- [26-10-01-0918] [审计报告 · QbManager 内核化重构实施评估](26-10-01-0918-report-kernel-module-refactor-audit.html) — `kernel-module-refactor`
- [26-09-30-1806] [WEBUI 列表键鼠交互割裂 · 业界成熟方案调研与推荐 · auto-qb](26-09-30-1806-report-webui-keymouse-cohesion.html) — `webui-keyboard-shortcuts`
- [26-09-29-1803] [HR 计数: 数据完整性的校验和 — 可行性分析](26-09-29-1803-report-hr-counter-verify.html) — `backend-partial-hr-verify`
- [26-09-29-0404] [HR 在线核实 v3 · 重构后全面复审(安全/稳定性/缺陷) · 审查报告 · auto-qb](26-09-29-0404-report-hr-verify-v3-audit.html) — `backend-partial-hr-verify`
- [26-09-28-2345] [WEBUI 表格列对齐审计 · auto-qb](26-09-28-2345-report-webui-column-alignment.html) — `webui-column-alignment`
- [26-09-28-0030] [HR 在线核实 v2 · 实施核对 + 安全/稳定性审计 · 审查报告 · auto-qb](26-09-28-0030-report-hr-verify-v2-impl-audit.html) — `backend-partial-hr-verify`
- [26-09-27-1547] [报告 · plans / reports 实施状态清点与漂移审计 — auto-qb](26-09-27-1547-report-docs-implementation-audit.html) — `docs-implementation-audit`
- [26-09-27-1352] [报告 · 「文件访问层包装 + 下载目录只读挂载 + 路径映射」可行性验证](26-09-27-1352-report-docker-fs-wrapper-pathmap.html) — `docker-deploy`
- [26-09-27-1143] [报告 · 双模板逐片差异评估(W3) — 单一语义模板收敛可行性](26-09-27-1143-report-webui-template-diff.html) — `webui-frontend-file-split`
- [26-09-27-0047] [规则系统可行性实验 · 「禁止 IYUU辅种 分类的种子开始下载」 · auto-qb](26-09-27-0047-report-rule-iyuu-stop-guard.html) — `rule-iyuu-stop-guard`
- [26-09-26-1918] [WEBUI 搜索强化 · 查询语法调研(成熟方案对比与推荐设计) · auto-qb](26-09-26-1918-report-webui-search-query-syntax.html) — `webui-search-query-syntax`
- [26-09-26-1628] [HR 在线核实 · 触发模型 / 访问节奏 / 安全可靠性 · 设计审查报告 · auto-qb](26-09-26-1628-report-hr-online-verify-audit.html) — `backend-partial-hr-verify`
- [26-09-25-0853] [full-checking 误报「校验未通过」与批量不触发 · 故障取证分析 · auto-qb](26-09-25-0853-report-full-checking-verdict-poison.html) — `full-checking-verdict`
- [26-09-21-1329] [后端崩溃安全性调查报告 · auto-qb](26-09-21-1329-backend-crash-safety-report.html) — `backend-state-persistence`
- [26-09-21-1248] [列设置重置 · 历次修复复盘与失败原因分析](26-09-21-1248-column-prefs-fix-failure-analysis.html) — `webui-column-prefs`
- [26-09-21-1158] [auto-qb 项目审计调查报告 · 2026-09-21](26-09-21-1158-auto-qb-project-audit.html) — `auto-qb-project`
- [26-09-21-0408] [辅种组状态 → 种子状态 对应表 · auto-qb](26-09-21-0408-seed-group-status-mapping.html) — `seed-group-status`
- [26-09-20-2131] [乐观 UI 撤下改为事件驱动 · 可行性报告 · auto-qb](26-09-20-2131-optimistic-ui-event-driven-feasibility.html) — `webui-optimistic-ui`
- [26-09-20-1806] [乐观 UI「撤下」修复只覆盖了一半入口 · auto-qb 调查报告](26-09-20-1806-optimistic-ui-half-fix-report.html) — `webui-optimistic-ui`
- [26-09-20-1429] [skill-vetter 全量审查报告 · .agents/skills（26 个技能）](26-09-20-1429-skill-vetter-audit.html) — `skill-vetter`
- [26-09-15-1150] [依赖版本调研与锁定建议 — 报告](26-09-15-1150-report-dependency-lock.html) — `deps-env-modernization`

## Dropped

(暂无)

## Superseded

(暂无 —— 被新版取代的计划落这里)

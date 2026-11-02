# 计划 Index

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描 `plans/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: `In Progress` / `Open` / `Done` / `Dropped` / `Superseded`。
> **已完结状态**(Done / Dropped / Superseded)只列**最近** `CLOSED_KEEP` 条(更老的**制品原地不动**, 只是不出本索引):
> 条数涨到 172 时索引 23,678 已贴 cap(25,200) 92%, 全量清单见
> [attachments/_archive.md](attachments/_archive.md), 该目录不计 cap。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图用 `commands run kb.docmap` 查(不落盘)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。

## In Progress

- [26-10-31-1119] [qBittorrent 5.3.x 双版本支持落地计划(facade 修复→升库→升 qB→走查→回写)](26-10-31-1119-plan-qb-5-3-support.html) — `qb-5-3-support`
- [26-10-10-2001] [计划 · WEBUI 选中 × 触发 一致性](26-10-10-2001-plan-webui-selection-trigger-parity.html) — `webui-selection-trigger-parity`
- [26-09-22-2318] [auto-qb 软件版本管理方案 · 版本号 / Tag / CHANGELOG / 发版流程](26-09-22-2318-version-management-plan.html) — `deps-version-management`

## Open

- [26-11-02-2342] [大文件多轮拆分实施计划（&gt;1000 行候选 80 个）](26-11-02-2342-plan-big-file-split.html) — `big-file-split`
- [26-10-01-1758] [Issue 全量清偿路线图 — 摸排 · 分波 · 执行顺序](26-10-01-1758-plan-issue-clearance-roadmap.html) — `issue-clearance-roadmap`

## Done

- [26-11-03-0120] [WEBUI 搜索结果随新增种子自动更新](26-11-03-0120-plan-webui-search-auto-refresh.html) — `webui-search-auto-refresh`
- [26-11-02-0657] [测试临时目录自举与互斥锁方案 — R→H→%TEMP% 固定探测 · 禁静默降级 · 禁外部 TMPDIR · 锁自举 · 评审稿](26-11-02-0657-plan-testing-tmpdir-bootstrap.html) — `testing-tmpdir-bootstrap`
- [26-11-02-0351] [WEBUI 大文件列表性能统一优化(抽屉千级文件 + 主表千级复测)](26-11-02-0351-plan-webui-large-filelist-perf.html) — `webui-large-filelist-perf`
- [26-11-02-0134] [整组迁移 qb_temp 闸门按归属收窄](26-11-02-0134-plan-relocate-qbtemp-narrow.html) — `relocate-qbtemp-narrow`
- [26-11-01-2212] [RM09 WebUI 写侧 漂移复测轮排期计划](26-11-01-2212-plan-real-rm09-drift.html) — `real-rm09-drift`
- [26-11-01-2123] [RM08 WebUI 读侧 漂移复测轮排期计划](26-11-01-2123-plan-real-rm08-drift.html) — `real-rm08-drift`
- [26-11-01-2033] [RM04 辅种与分组 漂移复测轮排期计划](26-11-01-2033-plan-real-machine-rm04-drift-plan.html) — `real-machine-rm04-drift-plan`
- [26-11-01-1921] [RM02 主循环·调度·持久化 · 真机实测分步计划(漂移复测轮)](26-11-01-1921-plan-real-machine-rm02-drift-plan.html) — `real-machine-rm02-drift-plan`
- [26-11-01-1031] [RM03 规则引擎 · 真机实测分步计划(漂移复测轮)](26-11-01-1031-plan-real-machine-rm03-drift-plan.html) — `real-machine-rm03-drift-plan`
- [26-11-01-0553] [WEBUI 主表横向滚动条隐藏与底部紧凑指示条](26-11-01-0553-plan-webui-hscroll-indicator.html) — `webui-hscroll-indicator`
- [26-11-01-0434] [提交闸门按改动收窄优化](26-11-01-0434-plan-commit-gate-scope.html) — `commit-gate-scope`
- [26-11-01-0106] [规则引擎重设计方案](26-11-01-0106-plan-rule-engine-redesign.html) — `rule-engine-redesign`
- [26-10-31-2354] [reannounce 确认跟踪改消解等待模型:废除在途直证,成功凭 working/前跳正证据](26-10-31-2354-plan-webui-write-side.html) — `webui-write-side`
- [26-10-31-2316] [WEBUI 动效皮肤 flux 分步实施计划](26-10-31-2316-plan-webui-fx-skin.html) — `webui-fx-skin`
- [26-10-31-1922] [RM10 通知·外部集成 · 真机实测分步计划](26-10-31-1922-plan-real-rm10.html) — `real-machine-rm10-plan`
- [26-10-31-1754] [RM08 WebUI 读侧 · 真机实测分步计划](26-10-31-1754-plan-real-rm08.html) — `real-machine-rm08-plan`
- [26-10-31-1710] [RM09 WebUI 写侧 · 真机实测分步计划](26-10-31-1710-plan-real-rm09.html) — `real-machine-rm09-plan`
- [26-10-31-1605] [RM07 限速·流量曲线·全局流量 · 真机实测分步计划](26-10-31-1605-plan-real-rm07.html) — `real-machine-rm07-plan`
- [26-10-31-1350] [RM06 HR 在线核实 · 真机实测分步计划(L1 数据面)](26-10-31-1350-plan-real-rm06.html) — `real-machine-rm06-plan`
- [26-10-31-1312] [RM05 tracker·标签与分类清理 · 真机实测分步计划](26-10-31-1312-plan-real-rm05.html) — `real-machine-rm05-plan`
- [26-10-31-1228] [RM03 规则引擎 · 真机实测分步计划](26-10-31-1228-plan-real-rm03.html) — `real-machine-rm03-plan`
- [26-10-31-1042] [RM04 辅种与分组 · 真机实测分步计划](26-10-31-1042-plan-real-rm04.html) — `real-machine-rm04-plan`
- [26-10-31-0927] [RM02 主循环·调度·持久化 · 真机实测分步计划](26-10-31-0927-plan-real-rm02.html) — `real-machine-rm02-plan`
- [26-10-31-0819] [真机实测 RM01 连接·认证·启动: 锁/端口/token/托盘/自启](26-10-31-0819-plan-rm01-startup.html) — `real-machine-rm01-startup`
- [26-10-31-0705] [真机实测 RM00 基建: 守卫/伪 tracker/双实例互传](26-10-31-0705-plan-real-machine-test.html) — `real-machine-test`
- [26-10-31-0534] [知识库过时信息分级清理 (R0-R4)](26-10-31-0534-plan-kb-cleanup-tiers.html) — `kb-cleanup-tiers`
- [26-10-31-0446] [全局流量来源 S19 真机验收计划(桩测 · 仅 Windows 侧)](26-10-31-0446-plan-global-traffic-source-acceptance.html) — `global-traffic-source-acceptance`
- [26-10-31-0306] [种子转移到其它下载器: 后端移动管线 + per-target 配置 + 四支右键菜单](26-10-31-0306-plan-torrent-transfer.html) — `torrent-transfer`
- [26-10-31-0143] [kb.nav 多选与批量右键菜单](26-10-31-0143-plan-kb-nav-multiselect.html) — `kb-nav-multiselect`
- [26-10-31-0128] [core/ 包变异测试审计 · 分步执行计划](26-10-31-0128-plan-mutation-core.html) — `mutation-core`
- [26-10-30-2359] [WebUI 分组行左条区分全选与半选——三模板选型](26-10-30-2359-plan-webui-sel-bar-partial-full.html) — `webui-sel-bar-partial-full`
- [26-10-30-0610] [乐观UI扩面: 重命名乐观补丁+主备速度切预翻转](26-10-30-0610-plan-webui-optimistic-ui.html) — `webui-optimistic-ui`
- [26-10-30-0221] [实施计划: 全项目第二次全面 Code Review — 增量优先分批评审与发现分流](26-10-30-0221-plan-full-code-review-2.html) — `full-code-review-2`
- [26-10-30-0217] [WebUI 主表暗主题背景重设计: 可交互模板选型](26-10-30-0217-plan-webui-main-table-dark-bg.html) — `webui-main-table-dark-bg`
- [26-10-30-0049] [rules/ 包变异测试审计 · 分步执行计划](26-10-30-0049-plan-mutation-audit.html) — `mutation-audit`
- [26-10-29-0308] [WEBUI 种子状态修复:新增 moving 类并封堵遗漏状态](26-10-29-0308-plan-webui-torrent-moving-state-kind.html) — `webui-torrent-moving-state-kind`
- [26-10-29-0231] [qB 流量图 3d+ 视图空闲零值区显示无采样修复计划](26-10-29-0231-plan-qb-traffic-agg-idle-zero.html) — `qb-traffic-agg-idle-zero`
- [26-10-29-0147] [HR 扩展缺站点权限的可见化与失败分类修正](26-10-29-0147-plan-hr-ext-site-permission.html) — `hr-ext-site-permission`
- [26-10-29-0041] [WEBUI 设定位置对话框 · 点选只回填 + 几何平滑过渡](26-10-29-0041-plan-webui-move-dialog-pick-geometry.html) — `webui-move-dialog-pick-geometry`
- [26-10-21-2323] [命令后状态写入的边界收口 · 实施计划 — 计时副作用 + 移除提交前复核 + 字段边界 + 守阵扩容](26-10-21-2323-plan-command-writeback-boundary.html) — `post-command-state-writes`
- [26-10-21-1857] [跳检机制重构 · 执行计划 — 上报驱动 + 主循环微步 + 批量并行](26-10-21-1857-plan-skip-check-async-refactor.html) — `skip-check-arch`
- [26-10-21-0120] [gtm 工具侧覆盖率门槛实施计划 — 88% 起步 · 双平台同口径 · 阶梯到 96](26-10-21-0120-plan-gtm-coverage-gate.html) — `gtm-coverage-gate`
- [26-10-20-2101] [测试覆盖率提升 · 第二轮 — 门槛清偿与 99% 冲刺 (97.66% → 99%)](26-10-20-2101-plan-test-coverage-uplift-2.html) — `test-coverage-uplift-2`
- [26-10-20-1316] [global-traffic-monitor 正主注册与让位代拉设计](26-10-20-1316-plan-gtm-primary-registration.html) — `gtm-primary-registration`
- [26-10-20-0145] [WEBUI右键菜单文案统一:动词+灰色种子计数](26-10-20-0145-plan-webui-menu-label-unify.html) — `webui-menu-label-unify`
- [26-10-20-0024] [WEBUI 右键菜单自定义重排(重排/显隐/跨层)实施计划](26-10-20-0024-plan-webui-ctx-menu-custom-layout.html) — `webui-ctx-menu-custom-layout`
- [26-10-19-2341] [WEBUI 弹窗语义配色分级(删除/跳检警示醒目化)](26-10-19-2341-plan-webui-dialog-tone-color.html) — `webui-dialog-tone-color`
- [26-10-19-2206] [站点问题改色表达与 chip 图标收口](26-10-19-2206-plan-webui-site-chip-color.html) — `webui-site-chip-color`
- [26-10-19-2007] [WEBUI 站点列状态提醒与逐目标汇报回执](26-10-19-2007-plan-webui-site-alerts.html) — `webui-site-alerts`
- [26-10-18-2013] [WEBUI 选中摘要: 种子个数 + 合计/实际占用大小](26-10-18-2013-plan-webui-selection-size-summary.html) — `webui-selection-size-summary`
- [26-10-18-1604] [免重启整组迁移(A/C)分步实施计划](26-10-18-1604-plan-group-relocate-restart-free.html) — `group-relocate-restart-free`
- [26-10-18-0813] [流量与限速合并与流量快照解耦 (Phase 2)](26-10-18-0813-plan-global-traffic-source-phase2.html) — `global-traffic-source-phase2`
- [26-10-17-1737] [全局流量来源联动缺陷修复 (Phase 1)](26-10-17-1737-plan-global-traffic-source-integration-fixes.html) — `global-traffic-source-integration-fixes`
- [26-10-17-0527] [memory-bank 文档流水线:统一模板 × 命令化创建/更新 · 修改计划 · auto-qb](26-10-17-0527-plan-memory-bank-doc-pipeline.html) — `memory-bank-doc-pipeline`
- [26-10-17-0339] [全局流量来源:一键切换与自动拉起 · 集成层改版计划 · auto-qb](26-10-17-0339-plan-global-traffic-source-integration.html) — `global-traffic-source-integration`
- [26-10-16-1509] [agg 行 totals 归属错位 · 修法三形态对照 · auto-qb](26-10-16-1509-plan-agg-hour-totals-attribution.html) — `qb-traffic-restart-spike-gap`
- [26-10-16-0541] [全局流量监视小工具(TrafficMonitor 替代)· 分步实施计划 · auto-qb](26-10-16-0541-plan-global-traffic-monitor.html) — `global-traffic-monitor`
- [26-10-16-0453] [HR 取数代理 · 工具栏图标候选 · 2026-10-16](26-10-16-0453-plan-hr-ext-icons.html) — `hr-ext-icons`
- [26-10-16-0214] [HR 扩展「连接后端」区重排 + 实例状态入表 修改计划 · auto-qb](26-10-16-0214-plan-hr-ext-connect-ui.html) — `hr-ext-connect-ui`
- [26-10-15-2357] [HR 扩展「连接自愈 + 手动优先 + 不静默」修改计划 · auto-qb](26-10-15-2357-plan-hr-ext-connect-selfheal.html) — `hr-ext-connect-selfheal`

> 更早的 **133** 条已出本索引 —— 制品仍在 `plans/` 目录(未搬动), 全量清单见 [attachments/_archive.md](attachments/_archive.md).

## Dropped

(暂无)

## Superseded

- [26-10-13-0413] [种子状态双写通道重构 · B2 实施计划 — 真值回写 + 显式自写变更发射](26-10-13-0413-plan-seed-state-writeback-truth-emission.html) — `seed-state-writeback`
- [26-10-09-0856] [HR 取数通道「外部扩展 / 跨机」支持 · 分步实施计划 · auto-qb](26-10-09-0856-plan-hr-channel-remote.html) — `hr-channel-remote`
- [26-09-30-1751] [计划 · 热重载机制简化: 统一挂载口 vs 保存即重启](26-09-30-1751-plan-hot-reload-simplify.html) — `hot-reload-simplify`
- [26-09-26-0822] [计划 · WEB UI 键盘快捷键（可自定义）· 可行性分析与实施计划](26-09-26-0822-plan-webui-keyboard-shortcuts.html) — `webui-keyboard-shortcuts`
- [26-09-25-2043] [HR 悬停弹窗模板 · T1 档案卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t1-spec-card.html) — `webui-hr-popup-t1`
- [26-09-25-2043] [HR 悬停弹窗模板 · T2 结论卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t2-verdict-card.html) — `webui-hr-popup-t2`
- [26-09-15-0910] [auto-qb · WEB UI 第七轮优化计划](26-09-15-0910-webui-optimization-plan-v2.html) — `webui-optimization`
- [26-09-15-0658] [auto-qb · WEB UI 优化计划](26-09-15-0658-webui-optimization-plan.html) — `webui-optimization`

# 计划 Index

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描 `plans/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: `In Progress` / `Open` / `Done` / `Dropped` / `Superseded`。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图用 `commands run kb.docmap` 查(不落盘)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。

## In Progress

- [26-10-08-1249] [HR 排除落到取数侧 (方案 B) 分步实施计划 · auto-qb](26-10-08-1249-plan-hr-exclude-steady.html) — `hr-steady-throttle`
- [26-09-22-2318] [auto-qb 软件版本管理方案 · 版本号 / Tag / CHANGELOG / 发版流程](26-09-22-2318-version-management-plan.html) — `deps-version-management`

## Open

- [26-10-09-0856] [HR 取数通道「外部扩展 / 跨机」支持 · 分步实施计划 · auto-qb](26-10-09-0856-plan-hr-channel-remote.html) — `hr-channel-remote`
- [26-10-01-1758] [Issue 全量清偿路线图 — 摸排 · 分波 · 执行顺序](26-10-01-1758-plan-issue-clearance-roadmap.html) — `issue-clearance-roadmap`

## Done

- [26-10-09-0821] [HR 故障归属分层拆分 · 分步实施计划 · auto-qb](26-10-09-0821-plan-hr-fault-domain.html) — `hr-fault-domain`
- [26-10-08-1217] [计划 · 辅种页/追剧页支持种子详情面板](26-10-08-1217-plan-webui-drawer-groups-shows.html) — `webui-detail-panel-redesign`
- [26-10-08-0720] [config/ 包变异测试审计 · 分步执行计划](26-10-08-0720-plan-mutation-config.html) — `mutation-audit`
- [26-10-07-2336] [tests/test_web.py 拆分实施计划](26-10-07-2336-plan-test-web-split.html) — `test-web-split`
- [26-10-07-2127] [实施计划 · qB 流量图区间平均口径 + 万桶级治理 · auto-qb](26-10-07-2127-plan-qb-traffic-rate-basis.html) — `qb-traffic-rate-basis`
- [26-10-07-0414] [实施计划 · WebUI rid 式增量同步 · auto-qb](26-10-07-0414-plan-webui-delta-sync.html) — `webui-delta-sync`
- [26-10-07-0055] [tracker URL 源头脱敏 · 方案B 分步实施计划](26-10-07-0055-plan-tracker-url-sanitize-planb.html) — `tracker-url-source-sanitize`
- [26-10-06-1009] [WEBUI 列对齐彻底修复 · 分步实施计划](26-10-06-1009-plan-webui-column-alignment.html) — `webui-column-alignment`
- [26-10-06-0838] [种子详情面板重构 · 15 模板全量实施(可切换) — 实施计划](26-10-06-0838-plan-webui-detail-panel-redesign.html) — `webui-detail-panel-redesign`
- [26-10-06-0708] [实施计划 · ui_smoke.cjs 分批迁移到 @playwright/test · auto-qb](26-10-06-0708-plan-playwright-e2e.html) — `playwright-e2e`
- [26-10-06-0103] [实施计划 · 全项目 Code Review 发现分批修复(六批 28 issue) · auto-qb](26-10-06-0103-plan-full-code-review-remediation.html) — `full-code-review-remediation`
- [26-10-05-2200] [实施计划 · qB 流量 v4 · 块头基线 delta + 按落盘切块(空闲块不关) + 自然推算结算 · auto-qb](26-10-05-2200-plan-qb-traffic-v4-delta.html) — `qb-traffic-v4-delta`
- [26-10-05-2026] [WEBUI 错误信息历史: toast 环形缓冲 + 后端错误环 + 常驻入口面板 · 实施计划](26-10-05-2026-plan-webui-toast-error-history.html) — `webui-toast-error-history`
- [26-10-05-0951] [实施计划: 全项目全面 Code Review — 分批评审与发现分流](26-10-05-0951-plan-full-code-review.html) — `full-code-review`
- [26-10-05-0923] [实施计划: 强制汇报确认机制重构 — epoch 前跳证据门控](26-10-05-0923-plan-reannounce-confirm-rework.html) — `reannounce-confirm-api`
- [26-10-05-0555] [HR 稳态降频 (idle_refresh_interval) 分步实施计划 · auto-qb](26-10-05-0555-plan-hr-steady-throttle.html) — `hr-steady-throttle`
- [26-10-05-0314] [WEBUI 危险动作防护: 重新校验确认框 + 跳检前置条件 · 实施计划](26-10-05-0314-plan-webui-danger-guards.html) — `webui-danger-guards`
- [26-10-04-1957] [实施计划 · qB 流量历史 dat v3 · 块化稀疏 delta + 批量落盘 + 按天文件 + 聚合分层 · auto-qb](26-10-04-1957-plan-qb-traffic-storage-v3.html) — `qb-traffic-storage-v3`
- [26-10-04-1830] [方案 · kb.nav 右键置顶 (pin) · 置顶专区 + 双向显示 · auto-qb](26-10-04-1830-plan-kb-nav-pin.html) — `kb-nav-pin`
- [26-10-04-1824] [recheck 轮询生效确认整体重设计 · 修改计划](26-10-04-1824-plan-ops-recheck-effect-confirmation.html) — `ops-recheck-false-success`
- [26-10-04-0952] [实施计划 · memory-bank 四工位导航页 · 三视图可切换 · auto-qb](26-10-04-0952-plan-kb-nav-page.html) — `kb-nav-page`
- [26-10-04-0721] [实施计划 · qB 流量历史 dat v2 零值行程行（z 行）· 单种空闲 0 平线 · auto-qb](26-10-04-0721-plan-qb-traffic-v2-zrow.html) — `torrent-traffic-stats`
- [26-10-04-0312] [修改计划 · WEBUI HR 在线核实 — 拉取历史详情表](26-10-04-0312-plan-webui-hr-fetch-history.html) — `webui-hr-fetch-history`
- [26-10-04-0107] [实施计划 · 跨组文件交叉检测与紧急处置 · auto-qb](26-10-04-0107-plan-cross-group-file-conflict.html) — `cross-group-file-conflict`
- [26-10-03-1544] [实施计划 · 同步时自动化解生成物索引冲突 · auto-qb](26-10-03-1544-plan-sync-generated-index-autoresolve.html) — `sync-generated-index-autoresolve`
- [26-10-03-0946] [实施计划 · qB 口径流量图方案C · dat 落盘（全局/单种）+ 分组读侧推算 · auto-qb](26-10-03-0946-plan-qb-traffic-charts-c.html) — `torrent-traffic-stats`
- [26-10-03-0917] [计划 · WEBUI 种子详情抽屉重设计 方案A (底部停靠属性面板) · 分步实施计划](26-10-03-0917-plan-webui-drawer-redesign.html) — `webui-drawer-redesign`
- [26-10-03-0436] [修复计划 · HR 在线核实热重载后 WebUI 停留「本地·达标」](26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) — `hr-hotreload-stale-display`
- [26-10-02-1955] [计划 · WEBUI 多选右键菜单: 限速 / 移动 / 跳检 / 导出 + 跳检菜单配置开关](26-10-02-1955-plan-webui-multi-ctx-actions.html) — `webui-multi-ctx-actions`
- [26-10-02-1936] [修改计划 · WEBUI HR 站点状态区展示层二轮改造 — 折叠 · 全屏 · 筛选排序 · 信息重组](26-10-02-1936-plan-webui-hr-status-display-rework.html) — `webui-hr-status-display`
- [26-10-02-1632] [计划 · WEBUI 把 ESC 定为「清除全部筛选」兜底键 — 混乱性分析与修改计划](26-10-02-1632-plan-webui-esc-clear-filters.html) — `webui-keyboard-shortcuts`
- [26-10-02-1621] [修改计划 · 站点引用规则拒绝重复 — auto-qb](26-10-02-1621-plan-rules-ref-duplicate-reject.html) — `rules-ref-duplicate-reject`
- [26-10-02-0608] [修改计划 · WEBUI Shift 连选起点与键鼠联动统一 — auto-qb](26-10-02-0608-plan-webui-shift-anchor.html) — `webui-keyboard-shortcuts`
- [26-10-01-2216] [修改计划 · WEBUI HR 在线核实详情表 — 全量详情表与排障视图](26-10-01-2216-plan-webui-hr-detail-table.html) — `backend-partial-hr-verify`
- [26-10-01-2157] [测试覆盖率提升 — 分阶段执行计划 (91% → 96%)](26-10-01-2157-plan-test-coverage-uplift.html) — `test-coverage-uplift`
- [26-10-01-1728] [计划 · 知识库文档漂移分段修复 — 内核化重构后四波欠账的回写路线](26-10-01-1728-plan-doc-drift-repair.html) — `doc-drift-repair`
- [26-10-01-0350] [计划 · 别名层处置 — _WEB_STATE_ALIAS 与旧名委托层的退役路线](26-10-01-0350-plan-web-state-alias-disposal.html) — `web-state-alias-disposal`
- [26-09-30-2112] [cap 守卫改债务制 · 工程计划 · auto-qb](26-09-30-2112-plan-memory-bank-cap-debt.html) — `memory-bank-cap-debt`
- [26-09-30-1819] [计划 · QbManager 内核化重构 — 微内核 + 插件式模块](26-09-30-1819-plan-kernel-module-refactor.html) — `kernel-module-refactor`
- [26-09-30-0931] [memory-bank 取时间标准化 · 工程计划 · auto-qb](26-09-30-0931-plan-memory-bank-timekit.html) — `memory-bank-timekit`
- [26-09-30-0559] [修改计划 · HR 触发语义重构 — 移除「本地不触发」,全量纳入管理](26-09-30-0559-plan-hr-trigger-semantics.html) — `backend-hr-verify`
- [26-09-30-0240] [修改计划 · HR 在线核实三参数解耦 — 拉取间隔 / 复用窗 / 立即拉取](26-09-30-0240-plan-hr-reuse-window-decouple.html) — `backend-partial-hr-verify`
- [26-09-30-0109] [危险操作独立操作层 · 工程计划 · auto-qb](26-09-30-0109-plan-dangerous-op-consolidation.html) — `dangerous-op-consolidation`
- [26-09-29-2036] [HR 计数对平集成 — 修改计划 (v3.1)](26-09-29-2036-plan-hr-counter-integration.html) — `backend-partial-hr-verify`
- [26-09-29-1905] [HR 来源标记 · 非文字化设计模板](26-09-29-1905-plan-webui-hr-src-underline.html) — `webui-hr-src-underline`
- [26-09-29-0323] [站点搜索 × 列表交互 · 三方案(计划)](26-09-29-0323-plan-webui-sites-search-3-proposals.html) — `webui-sites-page-search`
- [26-09-29-0003] [计划 · WEBUI 设置页「?」说明全面核对与改写](26-09-29-0003-plan-webui-settings-help-rewrite.html) — `webui-settings-help`
- [26-09-28-1932] [HR 在线核实 · 模型推翻重建计划 · auto-qb](26-09-28-1932-plan-hr-verify-rebuild.html) — `backend-partial-hr-verify`
- [26-09-28-1834] [计划 · 配置版本升级守卫: 键面基线冻结快照](26-09-28-1834-plan-config-version-guard.html) — `config-version-guard`
- [26-09-28-1805] [计划 · HR 排除功能: 按标签/分类把种子排除出 HR 体系](26-09-28-1805-plan-hr-exclude-tag-category.html) — `hr-exclude-tag-category`
- [26-09-28-0354] [计划 · WEB UI 键盘快捷键: 成熟方案调研与存储定案 (可自定义)](26-09-28-0354-plan-webui-keyboard-shortcuts.html) — `webui-keyboard-shortcuts`
- [26-09-28-0201] [auto-qb WEB UI · 搜索框帮助按钮 · 3 版模板(供挑选)](26-09-28-0201-plan-search-help-button-3-proposals.html) — `webui-search-query-syntax`
- [26-09-28-0157] [沉默即成功 — my-commit-flow 输出契约 v3 (26-09-28-0157)](26-09-28-0157-plan-commands-shipflow-v3.html) — `commands-shipflow-v3`
- [26-09-28-0037] [备用速度切换按钮 · 三套设计模板 (26-09-28-0037)](26-09-28-0037-plan-alt-speed-toggle.html) — `webui-alt-speed-toggle`
- [26-09-27-2252] [计划 · config schema 迁移物化重构: 加载即迁移 + 版本号备份 + 立即落盘](26-09-27-2252-plan-config-migration-materialize.html) — `config-hr-binding-mapping`
- [26-09-27-1930] [计划 · HR 在线核实绑定改映射制: 档案双域硬编码 + 已知映射零配置 + 旧键迁移 v1→v2](26-09-27-1930-plan-hr-binding-tracker-mapping.html) — `hr-binding-tracker-mapping`
- [26-09-27-1852] [计划 · 站点页搜索: 全字段匹配与多命中展示](26-09-27-1852-plan-sites-page-search.html) — `webui-sites-page-search`
- [26-09-27-1815] [HR 在线核实 · 审计修复 + v2 方案实施 · 修改计划 · auto-qb](26-09-27-1815-plan-hr-verify-audit-fixes.html) — `backend-partial-hr-verify`
- [26-09-27-1438] [计划 · 字段变化触发时机 on_torrent_field_changed 与维护任务 tags 迁移](26-09-27-1438-plan-field-changed-trigger.html) — `field-changed-trigger`
- [26-09-27-1407] [计划 · 文件访问层包装 + 下载目录只读挂载 + 路径映射(docker 兼容)](26-09-27-1407-plan-docker-fs-wrapper-pathmap.html) — `docker-deploy`
- [26-09-27-1318] [计划 · HR 在线核实配置收敛: 内置站点档案 + 配置全部上收「HR 在线核实」分区](26-09-27-1318-plan-hr-check-site-presets.html) — `hr-check-site-presets`
- [26-09-27-1232] [计划 · 暂时移除不成熟的限速统计设计 (upload_size 四条件 + begin_round)](26-09-27-1232-plan-remove-upload-stats.html) — `remove-upload-stats`
- [26-09-27-1126] [计划 · 日志等级整改 — 危险情况归 ERROR，通知默认只推 ERROR](26-09-27-1126-plan-log-level-notify-error.html) — `log-level-notify-error`
- [26-09-26-2345] [commands × my-commit-flow v2 — 输出契约与零参数化设计](26-09-26-2345-plan-commands-shipflow-v2.html) — `commands-shipflow-v2`
- [26-09-26-2233] [计划 · WEB UI 前端大文件拆分](26-09-26-2233-plan-webui-frontend-file-split.html) — `webui-frontend-file-split`
- [26-09-26-0538] [auto-qb WEB UI · 按钮体系重构 · 3 组方案模板(供挑选)](26-09-26-0538-plan-webui-button-3-proposals.html) — `webui-button-system`
- [26-09-26-0529] [测试基线切片化 · 单文件改每条一档](26-09-26-0529-plan-baseline-slice-per-file.html) — `baseline-slice-per-file`
- [26-09-26-0506] [落盘文件 schema 版本号与逐级升级链 · 工程计划](26-09-26-0506-plan-schema-version-chain.html) — `backend-schema-version-chain`
- [26-09-26-0031] [HR 取数代理 · 选项页风格选型(三选一)](26-09-26-0031-plan-hr-ext-options-style.html) — `backend-partial-hr-verify`
- [26-09-25-2241] [auto-qb · Docker 部署方案](26-09-25-2241-plan-docker-deploy.html) — `docker-deploy`
- [26-09-25-2043] [HR 悬停弹窗模板 · T3 进度仪表 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t3-progress-ledger.html) — `webui-hr-popup-t3`
- [26-09-25-1823] [计划 · HR 在线核实的 WEB UI 呈现（删除安全档位 × 来源档位）](26-09-25-1823-plan-webui-hr-safety-display.html) — `webui-hr-safety-display`
- [26-09-23-2008] [commands — 项目命令统一调用面 · 工程方案](26-09-23-2008-commands-plan.html) — `commands-unified-command-surface`
- [26-09-23-1959] [文档形态统一 — 计划与报告入库 · 工程方案](26-09-23-1959-memory-bank-doc-forms-plan.html) — `memory-bank-doc-forms`
- [26-09-22-2350] [activeContext 多 clone 冲突治理 — 工程方案](26-09-22-2350-activecontext-conflict-plan.html) — `memory-bank-activecontext-conflict`
- [26-09-22-2204] [部分种子 HR 的在线核实 — 可行性分析与实施计划](26-09-22-2204-partial-hr-site-verify-plan.html) — `backend-partial-hr-verify`
- [26-09-22-2112] [src/auto_qb 目录结构优化 · 分层归拢计划（方案 C 定稿）](26-09-22-2112-src-layout-restructure-plan.html) — `src-layout-restructure`
- [26-09-22-2038] [qB 移动已完成种子误判缺文件 · .!qB 过渡态容忍修复计划](26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html) — `backend-qb-move-dot-qb`
- [26-09-22-1912] [运行期状态周期落盘 · 修复「非优雅终止丢失整个运行期状态」](26-09-22-1912-backend-state-periodic-flush-plan.html) — `backend-state-persistence`
- [26-09-22-1857] [修复计划 · 热重载 L2 分支重读磁盘 state, 运行期内存态被回滚](26-09-22-1857-hot-reload-l2-state-rollback-fix-plan.html) — `hot-reload-l2-state-rollback-fix`
- [26-09-22-1857] [web.py create_app 拆分计划 · 926 行工厂函数 → web/ 包 + 按域 Router](26-09-22-1857-web-create-app-split-plan.html) — `web-create-app`
- [26-09-22-1801] [tracker URL 源头脱敏 · 可行性分析与实施计划](26-09-22-1801-tracker-url-source-sanitize-plan.html) — `tracker-url-source-sanitize`
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

- [26-09-30-1751] [计划 · 热重载机制简化: 统一挂载口 vs 保存即重启](26-09-30-1751-plan-hot-reload-simplify.html) — `hot-reload-simplify`
- [26-09-26-0822] [计划 · WEB UI 键盘快捷键（可自定义）· 可行性分析与实施计划](26-09-26-0822-plan-webui-keyboard-shortcuts.html) — `webui-keyboard-shortcuts`
- [26-09-25-2043] [HR 悬停弹窗模板 · T1 档案卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t1-spec-card.html) — `webui-hr-popup-t1`
- [26-09-25-2043] [HR 悬停弹窗模板 · T2 结论卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t2-verdict-card.html) — `webui-hr-popup-t2`
- [26-09-15-0910] [auto-qb · WEB UI 第七轮优化计划](26-09-15-0910-webui-optimization-plan-v2.html) — `webui-optimization`
- [26-09-15-0658] [auto-qb · WEB UI 优化计划](26-09-15-0658-webui-optimization-plan.html) — `webui-optimization`

# 文档形态总览 (按专题)

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描四形态 (plans / reports / issues / tasks) 的
> `doc-topic` / `**Topics:**` 与各自状态生成; 新增制品或改状态后重跑即可, 合并冲突也只需重跑。
> **一行一专题**: 该专题名下的 issue / 计划 / 报告 / 档案与各自状态 —— 「一件事的全部材料」的唯一入口。
> 协议与决策树见 [conventions/doc-forms.md](conventions/doc-forms.md); 各形态索引见
> [plans/_index.md](plans/_index.md) · [reports/_index.md](reports/_index.md) ·
> [issues/_index.md](issues/_index.md) · [tasks/_index.md](tasks/_index.md)。

## 跨形态专题 (≥2 件) —— 29 个

- **webui-optimistic-ui** (8) — issue [26-09-19-1939](issues/26-09-19-1939-perf-webui-optimistic-latency.html) `Done` · issue [26-09-19-1959](issues/26-09-19-1959-bug-webui-show-row-no-pending.html) `Done` · issue [26-09-19-2024](issues/26-09-19-2024-bug-webui-truth-convergence.html) `Done` · issue [26-09-19-2141](issues/26-09-19-2141-bug-webui-pending-timeout-stale-patch.html) `Done` · 计划 [26-09-19-2245](plans/26-09-19-2245-webui-optimistic-settle-plan.html) `Done` · 计划 [26-09-20-2139](plans/26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html) `Done` · 报告 [26-09-20-1806](reports/26-09-20-1806-optimistic-ui-half-fix-report.html) `Done` · 报告 [26-09-20-2131](reports/26-09-20-2131-optimistic-ui-event-driven-feasibility.html) `Done`
- **backend-state-persistence** (5) — issue [26-09-21-1347](issues/26-09-21-1347-bug-backend-hot-reload-l2-state-rollback.html) `Done` · issue [26-09-21-1347](issues/26-09-21-1347-bug-backend-state-save-only-on-exit.html) `Done` · issue [26-09-21-1347](issues/26-09-21-1347-bug-web-token-non-atomic-write.html) `Open` · 计划 [26-09-22-1912](plans/26-09-22-1912-backend-state-periodic-flush-plan.html) `Done` · 报告 [26-09-21-1329](reports/26-09-21-1329-backend-crash-safety-report.html) `Done`
- **webui-column-prefs** (5) — issue [26-09-20-1800](issues/26-09-20-1800-bug-webui-column-prefs-reset.html) `Done` · 计划 [26-09-20-1836](plans/26-09-20-1836-webui-column-prefs-sync-plan.html) `Done` · 计划 [26-09-21-1551](plans/26-09-21-1551-column-prefs-intent-redesign-plan.html) `Done` · 报告 [26-09-21-1248](reports/26-09-21-1248-column-prefs-fix-failure-analysis.html) `Done` · 档案 [26-09-20](tasks/26-09-20-webui-column-prefs-reset.md) `Done`
- **webui-qb-replacement** (4) — 计划 [26-09-16-0123](plans/26-09-16-0123-webui-qb-replacement-plan.html) `Done` · 计划 [26-09-16-1128](plans/26-09-16-1128-webui-qb-replace-wave3-plan.html) `Done` · 计划 [26-09-17-0346](plans/26-09-17-0346-webui-qb-replace-wave3-handover.html) `Done` · 档案 [26-09-15](tasks/26-09-15-webui-qb-replacement.md) `In Progress`
- **webui-statusbar** (4) — issue [26-09-20-1646](issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html) `Done` · issue [26-09-20-1840](issues/26-09-20-1840-bug-webui-statusbar-traffic-icon.html) `Done` · 计划 [26-09-20-1702](plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html) `Done` · 档案 [26-09-20](tasks/26-09-20-webui-statusbar-speed.md) `In Progress`
- **backend-partial-hr-verify** (3) — 计划 [26-09-22-2204](plans/26-09-22-2204-partial-hr-site-verify-plan.html) `Open` · 计划 [26-09-26-0031](plans/26-09-26-0031-plan-hr-ext-options-style.html) `In Progress` · 档案 [26-09-22](tasks/26-09-22-backend-partial-hr-verify.md) `Open`
- **backend-qb-move-dot-qb** (3) — issue [26-09-21-0219](issues/26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck.html) `In Progress` · 计划 [26-09-22-2038](plans/26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html) `In Progress` · 档案 [26-09-22](tasks/26-09-22-backend-qb-move-missing-tolerance.md) `In Progress`
- **deps-version-management** (3) — issue [26-09-21-1408](issues/26-09-21-1408-chore-version-dual-source.html) `Open` · 计划 [26-09-22-2318](plans/26-09-22-2318-version-management-plan.html) `In Progress` · 档案 [26-09-22](tasks/26-09-22-deps-version-management.md) `In Progress`
- **memory-bank-git-rules** (3) — issue [26-09-19-2359](issues/26-09-19-2359-docs-memory-bank-push-rule-drift.html) `Done` · 档案 [26-09-19](tasks/26-09-19-memory-bank-session-git-rules-sync.md) `Done` · 档案 [26-09-22](tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md) `Done`
- **qb-corpus-capture-replay** (3) — 计划 [26-09-21-0024](plans/26-09-21-0024-qb-corpus-capture-replay-plan.html) `Done` · 计划 [26-09-21-0257](plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html) `Done` · 档案 [26-09-21](tasks/26-09-21-qb-corpus-capture-replay.md) `Done`
- **sim-client-5000** (3) — issue [26-09-20-2145](issues/26-09-20-2145-test-sim-qb-maindata-snapshot-lag.html) `Done` · 计划 [26-09-19-1433](plans/26-09-19-1433-sim-client-5000-plan.html) `Done` · 档案 [26-09-19](tasks/26-09-19-sim-client-5000.md) `In Progress`
- **webui-optimization** (3) — 计划 [26-09-15-0658](plans/26-09-15-0658-webui-optimization-plan.html) `Superseded` · 计划 [26-09-15-0910](plans/26-09-15-0910-webui-optimization-plan-v2.html) `Superseded` · 计划 [26-09-15-1042](plans/26-09-15-1042-webui-optimization-plan-v3.html) `Done`
- **webui-responsiveness** (3) — 计划 [26-09-19-1241](plans/26-09-19-1241-webui-responsiveness-plan.html) `Done` · 计划 [26-09-19-1745](plans/26-09-19-1745-webui-responsiveness-review.html) `Done` · 档案 [26-09-19](tasks/26-09-19-webui-responsiveness.md) `In Progress`
- **webui-shows-view** (3) — issue [26-09-21-1408](issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html) `Open` · 计划 [26-09-15-1534](plans/26-09-15-1534-webui-shows-view-plan.html) `Done` · 档案 [26-09-15](tasks/26-09-15-webui-tvshows-view.md) `Done`
- **backend-file-split** (2) — 计划 [26-09-15-1124](plans/26-09-15-1124-backend-file-split-plan.html) `Done` · 档案 [26-09-15](tasks/26-09-15-backend-file-split.md) `Done`
- **backend-torrentrecord-fields** (2) — 计划 [26-09-15-1302](plans/26-09-15-1302-record-full-fields-plan.html) `Done` · 档案 [26-09-15](tasks/26-09-15-backend-torrentrecord-fields.md) `Done`
- **deps-env-modernization** (2) — 报告 [26-09-15-1150](reports/26-09-15-1150-report-dependency-lock.html) `Done` · 档案 [26-09-15](tasks/26-09-15-deps-env-modernization.md) `Done`
- **docker-deploy** (2) — 计划 [26-09-25-2241](plans/26-09-25-2241-plan-docker-deploy.html) `In Progress` · 档案 [26-09-25](tasks/26-09-25-deps-docker-deploy.md) `In Progress`
- **memory-bank-activecontext-conflict** (2) — 计划 [26-09-22-2350](plans/26-09-22-2350-activecontext-conflict-plan.html) `In Progress` · 档案 [26-09-22](tasks/26-09-22-memory-bank-activecontext-conflict.md) `In Progress`
- **memory-bank-dir-refactor** (2) — 计划 [26-09-22-1248](plans/26-09-22-1248-memory-bank-dir-refactor-plan.html) `Done` · 档案 [26-09-22](tasks/26-09-22-memory-bank-dir-refactor.md) `In Progress`
- **memory-bank-doc-forms** (2) — 计划 [26-09-23-1959](plans/26-09-23-1959-memory-bank-doc-forms-plan.html) `Done` · 档案 [26-09-23](tasks/26-09-23-memory-bank-doc-forms.md) `Done`
- **skill-hygiene** (2) — issue [26-09-20-1427](issues/26-09-20-1427-chore-skill-grill-me-empty-stub.html) `Open` · issue [26-09-20-1427](issues/26-09-20-1427-chore-skill-hatch-pet-api-cost.html) `Open`
- **test-timing-tolerance** (2) — issue [26-09-20-0952](issues/26-09-20-0952-test-mainloop-tick-timing-flaky.html) `Open` · issue [26-09-22-2052](issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html) `Open`
- **tracker-group** (2) — 计划 [26-09-15-1504](plans/26-09-15-1504-tracker-group-plan.html) `Done` · 档案 [26-09-15](tasks/26-09-15-rule-tracker-groups.md) `Done`
- **web-auth-hardening** (2) — issue [26-09-21-1408](issues/26-09-21-1408-bug-web-auth-hardening-minors.html) `Open` · issue [26-09-21-1408](issues/26-09-21-1408-bug-web-skip-local-verify-csrf.html) `Open`
- **web-create-app** (2) — issue [26-09-21-1408](issues/26-09-21-1408-refactor-web-create-app-monolith.html) `Done` · 计划 [26-09-22-1857](plans/26-09-22-1857-web-create-app-split-plan.html) `Done`
- **webui-decoupling** (2) — 计划 [26-09-20-0234](plans/26-09-20-0234-webui-decoupling-plan.html) `Done` · 档案 [26-09-20](tasks/26-09-20-webui-decoupling.md) `Done`
- **webui-hr-safety-display** (2) — 计划 [26-09-25-1823](plans/26-09-25-1823-plan-webui-hr-safety-display.html) `Done` · 档案 [26-09-25](tasks/26-09-25-webui-hr-safety-display.md) `In Progress`
- **webui-polling** (2) — issue [26-09-19-1900](issues/26-09-19-1900-bug-webui-poll-cadence-mismatch.html) `Done` · issue [26-09-19-2122](issues/26-09-19-2122-perf-webui-poll-gate-no-net-saving.html) `Open`

## 单件专题 (仅登记, 64 个)

- appjs-split · architecture · auto-qb-project · ci-no-windows-runner · commands-unified-command-surface · commands-unified-surface
- commit-gate-auto-run · config-value-range-validation · cross-group-file-conflict · dependency-lock · docs-readme-modules-drift · docs-restructure
- duplicate-test-name-shadowed-guard · fakeconfig-shared-state-order-pollution · full-checking-verdict · git-ship-skill-proposal
- hot-reload-l2-state-rollback-fix · issue-typing · memory-bank-migration · memory-bank-task-id · memory-bank-trigger-fix
- rule-conditions-expression · seed-group-status · skill-user-md-write-conflict · skill-vetter · skip-checking-readd-no-backup-window
- src-layout-restructure · state-load-corrupt-silent-reset · test-sidefx-guard · test-suite-perf · tracker-url-source-sanitize
- tray-join-timeout-abandons-save · type-annotations-mypy · web-runtime-host-protocol · web-tracker-url-passkey-log · webui-appjs-split
- webui-cols-store-version · webui-component-libraries · webui-config-health-warning · webui-ctx-menu-multi-select · webui-ctx-submenu
- webui-error-reason · webui-ext-hr-logging · webui-filter-data-and-color-flicker · webui-fix-plan-round10 · webui-fix-plan-round9
- webui-fix-round10 · webui-fix-round11 · webui-fix-round9 · webui-hot-endpoints-jsonable-encoder · webui-hr-popup · webui-hr-popup-t1
- webui-hr-popup-t2 · webui-hr-popup-t3 · webui-log-level-filter · webui-naming · webui-page-location-persist · webui-polish-and-redesign
- webui-redesign · webui-settings-unsaved-changes · webui-sites-import · webui-speed-refresh-fix · webui-torrent-meta-edit
- webui-view-rebuild

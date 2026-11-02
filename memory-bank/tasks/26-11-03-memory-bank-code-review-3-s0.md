# 26-11-03-memory-bank-code-review-3-s0 — 第三次全量代码评审 S0:准备与底册

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 第三次全量代码评审 S0:底册四表(Open issue / 坑档 / 在途件 / 二次 26 条去向), 入池 3 条计划底数漂移
**Topics:** memory-bank-code-review-3-s0
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/reports/26-10-30-0237-report-full-code-review-2.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-ledger-counts-drift.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-inflight-list-stale.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-baseline-anchor-stale.html, memory-bank/reports/26-11-03-0636-report-memory-bank-full-code-review-3.html

## 原始请求

1. 执行第三次 code review 计划的 **S0 步骤**（准备/底册），本轮只做 S0，不进入 S1 及之后。
2. 必读 `memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html`（S0 段与验收判据）；范围与结论已定，不改计划范围。
3. 开工先 `commands run my-commit-flow.sync`，贴「已同步 <hash>」；只在 clone1 操作。
4. 按 S0 产出底册：Open issue（计划记 52，从 `_index.md` 核对真实数）、坑档条目、在途计划、二次 review 26 条发现与去向；整理成 S1 可用的素材，不逐条复述成流水。
5. 计划文档不改流水：只允许更新状态/引用；过程记录写进单独 task 文档（`kb.new task`）。评审报告骨架放 `memory-bank/reports/`，只留结构。
6. S0 发现的真实问题当场按 create-issue 规范逐条入池，写清 8 类类型、档位、复现/判定依据。
7. 收尾按 DoD 回写（`kb.wrap`/`kb.index`），单独提交并推送；提交信息写 `.git/COMMIT_MSG_AI.txt`，走 `ship.commit` + `ship.push`，给出「提交成功 <hash>」与推送核验结果。
8. 若底册与计划记载数量不符且有实质影响，先停下报告，不自行改计划。

## 思考过程与决策

- **只做 S0**：S1 起的分批打标、逐文件评审、取证复验均不在本轮。
- **计划正文不回写底数**：实测与计划 §02 有三处漂移，全部入池记录（docs/light），本轮只把计划 `doc-status` 从 Open 推进到 In Progress；范围和判据一行未改。
- **Open 52 vs 54 的裁决**：多出的 2 条是 `26-11-03-0559` 两条 e2e 既有红（test），在计划 0557 定稿后入池。它们本来就会在 S1 被扫到，且 S6 去重口径按"当前 Open 集合"自然包含，**不改变评审范围与判据**，因此不阻塞、不要求用户裁决；S1 打标基数为 54（S0 本步入池 3 条后为 57）。
- **基线锚定**：现行最新全量基线是 `4933 passed + 2 skipped / 99%`（切片 `26-11-03-0534`）；计划引的 `4924+2`（切片 `0459`）是端口改 0 前的旧值，差额 +9 由 `tests/test_port_zero_guards.py` 解释。S1 各批以 **4933+2** 为比较基准，避免把已解释的 +9 误判成漂移；计划引用回写待用户确认（已入池）。
- **HEAD 漂移**：S0 开工 sync 从计划记载的 `812ad785` 快进到 `47a61c7c`（1 笔端口改 0），属计划 §11 已预告的 develop 演进，不作为缺陷。
- **零 src 改动**：本轮只读 + 文档/issue，未碰 `src/`、`web/`、`tests/`。

## 实现计划

1. S0-1 开工同步并记录 HEAD / 基线 / 分支。
2. S0-2 核对 `issues/_index.md` 的 Open 实数与类型分布。
3. S0-3 蒸馏 7 类坑档，按批次给出必读条目。
4. S0-4 清点在途计划/报告（按 `doc-status` 实测）。
5. S0-5 蒸馏二次评审 26 条发现与去向（按报告 §8.6 与 issue 状态复核）。
6. S0-6 把 3 条底数漂移按 create-issue 规范入池（docs/light，同 topic 串联）。
7. S0-7 建 task 文档（本件）与报告骨架；计划仅推进状态。
8. S0-8 DoD 回写（`kb.wrap`/`kb.index`）→ 单独提交 → 推送并核验。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0-1 | 同步与环境记录（812ad785 → 47a61c7c） | Done (2026-11-03) |
| S0-2 | Open issue 实数核对（54，非 52） | Done (2026-11-03) |
| S0-3 | 坑档 7 类蒸馏（277 条主题档） | Done (2026-11-03) |
| S0-4 | 在途计划清点（5 件 + 评审自身） | Done (2026-11-03) |
| S0-5 | 二次 26 条发现去向复核（18 池位全 Done） | Done (2026-11-03) |
| S0-6 | 入池 3 条计划底数漂移 | Done (2026-11-03) |
| S0-7 | task 文档 + 报告骨架 + 计划状态 | Done (2026-11-03) |
| S0-8 | DoD 回写 + 提交 + 推送 | Done (2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

- **S0-1 同步**：`commands run my-commit-flow.sync` 输出「已同步 47a61c7c」（无改写 HEAD 步骤）。分支 develop；HEAD `47a61c7c`（♻️ 测试侧 e2e 端口全面改 0）；相对计划起点 `812ad785` 前进 1 笔。最新全量基线：`4933 passed + 2 skipped / 99%`（`testing/baselines/26-11-03-0534-test-port-zero.md`，173.58s）。
- **S0-2 Open 核对**：`issues/_index.md` 生成物 Open 分区逐行计数 **54**（入池 3 条前；计划 §02 记 52）。分布：feat 21 / bug 8 / question 6 / perf 5 / test 5 / refactor 4 / docs 3 / chore 2。差额 2 = `26-11-03-0559` 两条 e2e 既有红（test），计划定稿后入池。入池前全仓 issue 状态：Open 54 / In Progress 2 / Done 359 / Dropped 6 / Superseded 3 = 424。
- **S0-3 坑档**：7 类共 277 条主题档（backend 46 / web-ui 92 / testing 85 / kb 20 / git 16 / ops 11 / docs 7）。各类另有 1 份 `_about.md` 与 1 份 `_index.md` 不计入（目录内共 291 个 .md）。
- **S0-4 在途**：按 `doc-status` 实测，除评审自身外真实在途计划 5 件：`26-11-02-2342` 大文件拆分(Open)、`26-10-31-1119` qB 5.3 支持(In Progress)、`26-09-22-2318` 版本管理(In Progress)、`26-10-10-2001` 选择触发一致性(In Progress)、`26-10-01-1758` issue 清池路线图(Open)。reports/ 无非 Done。
- **S0-5 二次 26 条**：1 P1 + 6 P2 + 19 P3；落地 18 个池位（18 个 issue 文件）**全部 Done**；C-02 并入 `26-09-21-1408`（该 issue 仍 Open，属"标注补强"，本轮不动）；11 条观察（9 条只记录 / 2 条并注）。详见底册 D。
- **S0-6 入池**：3 条 docs/light，topic `code-review-3-s0`，均已在 `_index.md` 登记（见"本步新增 issue"）。
- **S0-7 文档**：本件 + `memory-bank/reports/26-11-03-0636-report-memory-bank-full-code-review-3.html` 骨架；计划只改状态徽标/meta 为 In Progress（§02 数字与 §06 拍板记录未动）。
- **S0-8**：DoD 回写（`kb.wrap`/`kb.index`）完成；提交与推送按 `ship.commit` + `ship.push` 随本专题入库。

### R1 · S0 完成 (2026-11-03)

- S0 收口：底册四表（Open 54→57 / 坑档 7 类 277 条 / 在途计划 5 件 / 二次 26 条去向）落本档案，入池 3 条计划底数漂移，报告骨架建成，计划仅推进状态。

## 底册 A · Open issue（S0 起点 54，按类型）

> 用途：S1 按批打标时直接取自这里；S6 终验去重基数为「S0 起点 54 + 本步新增 3 = 57」。每条只留短 ID 与标题要点，正文/证据进各自 issue。

**feat（21）**
- `26-10-31-0711-feat-qb-5-3-new-capabilities` qB 5.3 新能力可优化点（非阻塞）
- `26-10-22-0308-feat-ops-skip-check-download-cost` 跳检缺"不完整数据重新下载"防线
- `26-10-14-0521-feat-content-tab-file-rename-missing` 内容页签"重命名…"入口缺失
- `26-10-07-0149-feat-webui-drawer-open-state-restore` 抽屉开合态持久化（与 D1 冲突待翻案）
- `26-10-07-0149-feat-webui-peer-ban-action` 09 变体 peer 悬停封禁（P-04 备选）
- `26-10-07-0149-feat-webui-traffic-interpret-hover-link` 14 变体解读栏悬停联动（P-05 备选）
- `26-10-05-0922-feat-hr-prune-notice` 30 天静默淘汰前的日志预告
- `26-10-01-2203-feat-disaster-site-rebuild` 硬盘/qB 损坏后重建现场
- `26-10-01-2203-feat-ext-info-display` 浏览器扩展信息展示
- `26-10-01-2203-feat-ext-version-pinning` 扩展版本号 + 固定版本 + 高度参数化
- `26-10-01-2203-feat-i18n-multi-language` 多语言（低优先级）
- `26-10-01-2147-feat-group-move-atomicity` 整组迁移防进度丢失
- `26-10-01-2147-feat-hr-verify-sync-hr-tags` HR 在线核实同步标签/分类
- `26-10-01-2147-feat-speedlimit-curve-emphasis` 限速曲线强调 + 弹窗提醒
- `26-10-01-2138-feat-webui-shows-grouping-research` 追剧视图同剧判定与排序
- `26-10-01-2138-feat-webui-tracker-error-warning-state` tracker error/warning 展示
- `26-10-01-2137-feat-webui-settings-help-followup` 设置页「?」遗漏补齐 + 语义色
- `26-10-01-2120-feat-webui-custom-chip-colors` 站点名/分类/标签自定义字体颜色
- `26-10-01-2119-feat-webui-search-highlight` 搜索命中高亮 + 命中域提示
- `26-09-30-0052-feat-hr-badge-total-crosscheck` HR 上限徽章总数轴互证（缓做）
- `26-09-27-1248-feat-stats-redesign-torrent-traffic` 单种周期流量统计重设计

**bug（8）**
- `26-11-03-0316-bug-webui-bind-failure-silent` WebUI 端口占用仅记 ERROR 且继续
- `26-11-03-0315-bug-hr-discovery-multi-clone-isolation` HR 发现端点 18788 + 共享 instances 跨 clone 混串
- `26-10-11-2045-bug-ops-skipcheck-dedup-shadowed-by-g3` 跳检 dedup 闸门被 G3 遮蔽
- `26-10-11-2045-bug-torrents-store-removed-pop-readd` 删后重加同 hash 的 removed 回写 pop
- `26-10-05-0402-bug-skip-check-self-fail-gate` 跳检候选自身校验失败可被洗白
- `26-10-01-2203-bug-tray-ctrl-c-not-exit` --tray 模式 Ctrl+C 无法退出
- `26-10-01-2129-bug-webui-delete-files-missing-warning` 连文件删除种子触发缺文件 WARNING
- `26-09-22-2002-bug-webui-config-health-warning` 设置页警示条为伪警示

**question（6）**
- `26-10-16-0020-question-agg-rate-lane-invisible-bytes` agg 速率 lane 是否含隐形字节
- `26-10-13-0626-question-grouping-transition-reflow-retrigger` A 系删回写回流重复扫描（幂等）
- `26-10-01-2212-question-config-split-per-site` 每站点一份配置是否做
- `26-10-01-2212-question-search-based-recheck-feasibility` 搜索式辅种可行性
- `26-10-01-2147-question-hr-same-group-download-priority` HR 同组优先高下载量
- `26-10-01-2147-question-skipcheck-no-completed-in-group` 组内无完成种子拒绝跳检

**perf（5）**
- `26-10-08-0411-perf-webui-api-state-pagination` /api/state 分页/按需字段未做
- `26-10-07-1420-perf-webui-group-row-hash-ref` 组行 hash 引用式响应体二次演进
- `26-10-01-2218-perf-mainloop-max-tasks-adaptive` 渐进灌入期主循环掉拍
- `26-09-30-0052-perf-hr-lastpage-fetch-skip` HR 末页追翻省略（缓做）
- `26-09-19-2122-perf-webui-poll-gate-no-net-saving` 节拍门控未减少总重建

**test（5）**
- `26-11-03-0559-test-e2e-big-table-existing-red` e2e 大表/详情既有红（与端口改造无关）
- `26-11-03-0559-test-e2e-ctx-menu-existing-red` e2e 右键菜单既有红（与端口改造无关）
- `26-11-03-0115-test-hr-discovery-port-bind-flake` Windows 并行全量偶发 WinError 10013
- `26-10-31-0641-test-real-machine-test-standing` 真机实测定期排期（常驻锚）
- `26-10-08-0642-test-mutation-audit-standing` 变异测试定期审计（常驻锚）

**refactor（4）**
- `26-11-03-0316-refactor-e2e-port-8236-legacy` e2e 列偏好仍引 8236 遗留端口
- `26-10-05-0922-refactor-hr-fetchable-dead-config` `SiteHrCheckConfig.fetchable` 零消费方
- `26-10-01-2120-refactor-webui-tag-category-dialog` 管理标签/分类弹窗重构
- `26-09-21-1408-refactor-type-annotations-mypy` 类型注解仅 43%，无 mypy 配置

**docs（3）**
- `26-11-03-0316-docs-port-doc-drift` 端口口径文档漂移
- `26-10-31-0711-docs-qb-5-3-upgrade-docs` qB 双版本口径 + 5.3 升级部署注记
- `26-09-28-1946-docs-config-plugin-spec-docs` 插件 spec 内部键无逐键参考文档

**chore（2）**
- `26-09-21-1408-chore-version-dual-source` 版本号双源矛盾（0.2.0 vs 0.1.0）
- `26-09-20-1427-chore-skill-hatch-pet-api-cost` hatch-pet 调付费图像 API 无成本提示

**In Progress（2，非 S1 新发现面）**
- `26-10-01-2212-question-transmission-compat-feasibility` 兼容 Transmission 可行性
- `26-10-01-2203-bug-taskbar-python-icon` 任务栏图标仍为 python 图标

## 底册 B · 坑档 7 类（共 277 条）

> 用途：S1 每批开工先按批读"必读"几条；全类清单走 `pitfalls/<类>/_index.md`，**不整目录通读**。

| 类 | 条数 | 本轮主要风险面 | S1 必读（按批） |
|---|---|---|---|
| backend | 46 | 主循环/并发/状态落盘、qB 语义、relocate、流量聚合、故障域 | B1-B3: `concurrency.md`, `behavior-core.md`, `high-risk-ops.md`, `qb-api.md`, `qb-content-path-semantics.md`, `relocate-restore-issued-marker.md`, `traffic-agg-reseal.md`, `config-duplicates-runtime-fact.md`, `last-round-snapshot-stale.md`, `sentinel-epoch-arith.md`, `fault-domain-classification.md` |
| web-ui | 92 | 组件契约/响应式、抽屉、表格几何、轮询/冷启动、覆层 | B4-B6: `contract-api.md`, `component-ref-ownership.md`, `vue-reactivity.md`, `template-render.md`, `derived-snapshot-render.md`, `drawer-open-vs-kind.md`, `drawer-switch-flicker.md`, `drawer-merge-hit-region.md`, `dur-cell-padding-rowheight.md`, `cell-frame-vs-text-width.md`, `header-cell-gutter.md`, `est-cold-start-vs-absolute-threshold.md`, `perf-cadence.md` |
| testing | 85 | 测试计划 docstring 边界、端口/临时目录、性能测量、红验、守阵 | B9: `plan-docstring-section-boundary.md`, `fixed-port-test-collision.md`, `tmpdir.md`, `perf-measurement.md`, `playwright-teardown.md`, `red-verify-must-hit-behavior.md`, `static-guard-mutation.md`, `parallel-run.md` |
| kb | 20 | 请求边界、范围限定、文档状态、引用链、cap/计数 | 全程: `request-boundary.md`, `scope-qualifier-parenthetical.md`, `doc-status-meta.md`, `refs-rename.md`, `cap-counting.md`, `wrap-did-test-numbers.md` |
| git | 16 | ref 三处核对、ship 流程、镜像、工作区隔离 | 全程: `refs.md`, `ship-commit-staged-delete.md`, `subagent-mixed-workspace.md`, `sync-pull.md`, `push.md` |
| ops | 11 | 生产文件红线、端口进程、控制台编码、写盘守卫 | B7 + 全程: `prod-files.md`, `port-kill-prod-instance.md`, `console-encoding.md`, `agent-write-guard-secret-false-positive.md` |
| docs | 7 | HTML/MD 编辑陷阱、锚点、漂移 | B10 + 全程: `drift.md`, `html-edit.md`, `md-edit.md`, `anchor-quote.md`, `html-endtag-missing-gt.md` |

## 底册 C · 在途计划/报告（除评审自身 5 件）

| 件 | 类型 | 状态 | 与评审的边界 |
|---|---|---|---|
| `plans/26-11-02-2342-plan-big-file-split.html` | 计划 | Open | 大文件拆分; 可能与 B1-B6 的文件面重叠, S1 只读现状不评审其方案 |
| `plans/26-10-31-1119-plan-qb-5-3-support.html` | 计划 | In Progress | qB 5.3 支持; 涉及 `backend/qb-api` 时必须区分既有兼容层与 5.3 新增面 |
| `plans/26-09-22-2318-plan-version-management.html` | 计划 | In Progress | 版本管理; 与 `chore-version-dual-source` 同域, 只标不修 |
| `plans/26-10-10-2001-plan-selection-trigger-parity.html` | 计划 | In Progress | 选择触发一致性; B2/B5 命中时先查该计划已覆盖边界 |
| `plans/26-10-01-1758-plan-issue-clearance-roadmap.html` | 计划 | Open | issue 清池路线; 仅作背景, 不改变本评审的 54/57 底册 |
| `issues/26-10-31-0641-test-real-machine-test-standing.html` | issue(常驻锚) | Open | 真机实测排期, 不是计划 |
| `issues/26-10-08-0642-test-mutation-audit-standing.html` | issue(常驻锚) | Open | 变异审计排期, 不是计划 |

报告侧：`memory-bank/reports/` 下无非 Done 报告；二次报告 `26-10-30-0237` 为 Done。

## 底册 D · 二次评审 26 条发现与去向

**总量与分级**：A/B/C/D/E/F1/F2/GH/T 九批共 26 条 = 1 P1 + 6 P2 + 19 P3；落地 18 个新池位（18 个 issue 文件），另 11 条观察。

**18 个池位（全部 Done，S0 复核文件状态）**

| 发现 | 去向 issue |
|---|---|
| B-01（P1，must） | `26-10-30-0550-bug-hr-cutoff-zero-position-proof` |
| A-01 | `26-10-30-0616-bug-relocate-phase-dry-run-shortcircuit` |
| A-02 | `26-10-30-0616-bug-resume-hashes-failure-path` |
| A-03 | `26-10-30-0616-bug-rebuild-respawn-backoff` |
| A-04 | `26-10-30-0616-bug-moving-phase-issue-restore` |
| A-05 | `26-10-30-0616-perf-finalize-members-filetable-filter` |
| A-06 | `26-10-30-0616-bug-defer-due-budget` |
| A-08 / B-02 / F2-01 / F2-02 / GH-02 / T-05 | `26-10-30-0620-chore-dead-code-batch-cleanup-2`（合并条） |
| A-07 / F1-02 / T-04 | `26-10-30-0620-chore-annotation-comment-contract-hygiene`（合并条） |
| C-01 | `26-10-30-0622-refactor-traffic-agg-cov-parse-contract` |
| D-01 | `26-10-30-0622-chore-config-qbittorrent-str-typecheck` |
| E-01 | `26-10-30-0622-bug-numeric-param-400-collect` |
| F1-01 | `26-10-30-0622-bug-alt-limits-submit-empty-gate` |
| F2-03 | `26-10-30-0622-bug-drawer-merge-seq-bump-conditional` |
| GH-01 | `26-10-30-0624-bug-relocate-journal-heartbeat-phase` |
| T-01 | `26-10-30-0624-bug-gtm-config-write-lock` |
| T-02 | `26-10-30-0624-bug-gtm-http-host-loopback-contract` |
| T-03 | `26-10-30-0624-bug-gtm-day-rolled-direction-check` |

**特殊去向**
- **C-02**：未单开 issue，按报告 §8.6 并入 `26-09-21-1408-refactor-type-annotations-mypy` 的池内备注；该 issue 仍 Open，是本轮唯一未清的关联项（"只标不修"）。
- **11 条观察**：9 条仅记录（F3-②、GH-①~④、T-①、T-②、T-④、T-⑤）；2 条并入既有池位备注（F3-① → `26-10-20-2231` 轮询族；T-③ → `26-10-20-2345` 成本议题）。均无新池位。
- **范围外产物**：`26-10-30-0626-perf-webui-sse-down-poll-latency`、`26-10-30-0818-bug-webui-rename-rollback-drawer-detail`、`26-10-30-0818-test-e2e-atlas-pinned-row-tint` 同批次入池但**不属二次评审 26 条**，S6 不计入二次去向核对。

## 本步新增 issue（3 条，docs/light）

1. `26-11-03-0630-docs-plan-review3-ledger-counts-drift` — §02 数字三处不符（Open 52/54、新入池 17/18、总数 424 与分项 422 自相矛盾）。
2. `26-11-03-0630-docs-plan-review3-inflight-list-stale` — §02 在途清单失效（2 已 Done、2 实为 issue、3 在途未列）。
3. `26-11-03-0630-docs-plan-review3-baseline-anchor-stale` — 起点基线引用过期（4924+2/0459 vs 现行 4933+2/0534，+9 已解释）。

## 交给 S1 的输入清单

1. **打标底册**：本节 A 的 54 条（+本步 3 条 = 57 条 Open），按 feat/bug/question/perf/test/refactor/docs/chore 八类直接用。
2. **基线锚**：`4933 passed + 2 skipped / 99%`（切片 0534）；`test.full` 全量复跑后只与它比，差额必须逐条解释。
3. **坑档入口**：本节 B 的必读清单；每批开工按类索引再选，禁止整目录通读。
4. **边界清单**：本节 C 的 5 个在途计划 + 2 个常驻 issue 锚；命中重叠文件时只标"已在他计划覆盖"，不重复评审其方案。
5. **排重基线**：本节 D 的 18 个 Done 池位 + C-02 并入项 + 11 条观察；同一模式若复现，按"二次遗留/新发现"标注，不重开旧单。
6. **禁止项**：本轮未改计划正文；S1 若需改 §02 数字/基线引用，先请用户确认（3 条 docs issue 已备好文案）。

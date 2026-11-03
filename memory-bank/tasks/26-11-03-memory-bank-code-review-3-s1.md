# 26-11-03-memory-bank-code-review-3-s1 — 第三次全量代码评审 S1:文件打标与批次定稿

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 第三次全量代码评审 S1: 479 个代码文件三类打标(实质 295 / move-only 184 / 未变 0), B1-B10 批次矩阵定稿并自证 0 漏 0 重, 入池 3 条范围/分类问题
**Topics:** memory-bank-code-review-3-s1
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s0.md, memory-bank/issues/26-11-03-0704-docs-plan-domain-table-count.html, memory-bank/issues/26-11-03-0704-test-split-carried-inrange-changes.html, memory-bank/issues/26-11-03-0704-docs-split-residue-rename.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s3.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s4.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s5.md

## 原始请求

1. 执行第三次 code review 计划的 S1 步骤(文件打标与批次定稿), 只做 S1, 不进入评审。
2. 必读计划 S1 段与 S0 底册(57 条 Open、基线锚 4933+2、坑档入口、边界清单、排重基线)。
3. 范围固定 `bf9920d3..812ad785`(358 笔提交、479 个代码文件、+122,931/−62,415); S0 期间产生的评审流程文档提交(如 `67345150`、`b31b7926`)不纳入, HEAD 前移不扩大范围。
4. 开工先 `commands run my-commit-flow.sync` 并贴「已同步 <hash>」; 只在 clone1 操作, 禁止跨 clone。
5. 479 个文件打三类标(实质改动 / move-only / 未变), 用 `git diff -M --stat`、`--name-status`、`-M50%` 判定; move-only 给源→目标配对表并标「待 S3 做等价核验」。
6. 校验完整性: 三类并集 = 479, 0 漏 0 重, 给出可复算口径(命令+数字)并解释计数差异。
7. 定稿批次矩阵 B1-B10: 文件清单/模块、标类、评审重点、依赖坑档、工作量、批间并行性; 与计划不一致要给理由。
8. S1 发现的真实问题当场按 create-issue 入池, 写清类型/档位/判定依据。
9. 过程与矩阵写进本步单独 task 文档, 计划文档不写流水; 收尾按 DoD 回写(kb.wrap/kb.index), 再单独提交并推送本步文档产出。

## 思考过程与决策

- **只做 S1**: 打标、完整性校验、批次矩阵与入池; 不进入逐文件评审(B1-B10 留给 S2-S5)。
- **范围终点不随 HEAD 漂移**: 开工同步 `b31b7926→253ada4f`, 但评审区间终点固定 `812ad785`; `253ada4f` 及 S0 流程文档提交不计入 479。
- **三类口径以「区间内是否有非拆分提交触达」为准**: 纯拆分提交(A/M/D)且无其他提交触达 = move-only; 有任一非拆分提交触达 = 实质(含「拆分后又修」的混合件, 按计划「疑似混合提交按实质全量审」保守归入实质); 区间内无纯改名/仅模式变动 → 未变 = 0。
- **未变=0 的原因**: 代码面 479 个文件里没有 R100 纯改名, 也没有 mode-only / 0+0 numstat; 679 条 R100 全部在 `memory-bank/` 等非代码面(不在 479)。
- **拆分提交认定**: R1 `a48ead5c`、R2 `63f47598`、R3 `60ee0bec`、R4 `20a74274`(提交信息均声明 move-only); `b5adba14` 是 R2 后守阵修复, 按实质计。
- **批次调整**: B6 只放 23 个纯分片; 8 个 static 根文件因被区间内其他提交触达(混合), 归入 B5 实质评审, 其搬迁等价核验仍按配对表在 B6/S3 执行 —— 这是与计划「B6 ≈30 件」的唯一实质差异。
- **config 12 件按内容主责拆分**: `models.py`/`validation/sections.py` 归 B1(web.transfer 段), `schema/rules.py`/`validation/rules.py` 归 B3, 其余 8 件归 B2(qB 5.3 compat 与配置骨架)。
- **计划正文不回写**: 发现的 3 条范围/分类问题全部入池, 计划只更新状态与引用(双向补链已由 kb.new 自动完成)。
- **零代码改动**: 本轮只读 git 与文档, 未碰 `src/`、`tests/`、`tests-real/`、`tools/`、`extensions/`、`scripts/`。

## 实现计划

1. S1-1 开工同步, 记录 HEAD/分支与范围端点。
2. S1-2 导出区间 `--name-status -M50%` 与 `--numstat`, 过滤 6 个代码根, 复算 479 与增删行。
3. S1-3 认定 R1-R4 拆分提交, 逐提交解析 A/M/D/R 形状。
4. S1-4 逐文件定类(实质/move-only/未变), 混合件保守归实质。
5. S1-5 完整性校验: 三类并集、批次并集、重号与漏项。
6. S1-6 生成 move-only 源→目标配对表(按拆分组)。
7. S1-7 定稿 B1-B10 矩阵与逐批清单, 给评审重点/坑档/工作量/并行性。
8. S1-8 发现入池 3 条; DoD 回写; 单独提交并推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1-1 | 开工同步与范围端点(812ad785 固定) | Done (2026-11-03) |
| S1-2 | 区间文件导出与 479/增删行复算 | Done (2026-11-03) |
| S1-3 | R1-R4 拆分提交形状解析 | Done (2026-11-03) |
| S1-4 | 479 文件三类打标(295/184/0) | Done (2026-11-03) |
| S1-5 | 完整性校验(并集 479, 0 漏 0 重) | Done (2026-11-03) |
| S1-6 | move-only 配对表(4 组 82 源) | Done (2026-11-03) |
| S1-7 | B1-B10 矩阵定稿 | Done (2026-11-03) |
| S1-8 | 入池 3 条 + DoD + 提交推送 | Done (2026-11-03) |

## 进度日志

### R0 · 立档与 S1 完成 (2026-11-03)

- **S1-1 同步**: `commands run my-commit-flow.sync` → 快进 `b31b7926→253ada4f`, 结果「已同步 253ada4f」; 分支 develop; 评审区间终点仍固定 `812ad785`(该终点含 358 笔, 与计划一致)。
- **S1-2 复算**: 代码面过滤 `src/ tests/ tests-real/ tools/global-traffic-monitor/ extensions/ scripts/` 得 479 文件; numstat 汇总 +122,931/−62,415(含 12 条 rename 行), 与计划逐字一致。
- **S1-3 拆分**: R1 10 源→48 目标; R2 25 源→110 目标; R3 4 个 >1000 行源→11 新分片(+9 配套); R4 8 根→23 分片(+4 皮肤 index.html 与测试支撑件配套)。每源均能对上目标, 未见缺源/缺目标。
- **S1-4/5 打标**: 实质 294(含 34 混合 + 22 区间新增)、move-only 185(165 现存目标/根 + 20 已删源)、未变 0; 并集 479, 0 漏 0 重。
- **S1-6 配对**: 82 个拆分源/根按组配对, 全部标「待 S3 做等价核验」; 12 条 R 残片按组解读(入池 docs)。
- **S1-7 矩阵**: B1 18 / B2 25 / B3 9 / B4 11 / B5 67 / B6 23 / B7 33 / B8 8 / B9 285 / B10 0(代码面); 合计 479。
- **S1-8 入池**: 3 条(2 docs/light + 1 test/standard, topic `code-review-3-s1`); DoD 回写与提交推送随本轮完成。
- **基线**: 仍引用 `4933 passed + 2 skipped / 99%`(切片 0534); 本步零代码改动, 不新建基线切片。

## 附录 A · 三类打标与完整性校验

**口径(可复算)**

```text
# 1) 代码面文件全集(479)
git diff --name-status -M50% bf9920d3..812ad785
  -> 按路径前缀过滤: src/ | tests/ | tests-real/ | tools/global-traffic-monitor/ | extensions/ | scripts/

# 2) 增删行(含 rename 行)
git diff --numstat -M50% bf9920d3..812ad785
  -> 同前缀过滤; rename 行形如 'a b tests/{old.py => new.py}' 按目标路径计入

# 3) 拆分提交形状(4 个 move-only 提交)
git diff-tree --no-commit-id --name-status -r -M50% <a48ead5c|63f47598|60ee0bec|20a74274>

# 4) 每文件是否被非拆分提交触达
git log --format=%H bf9920d3..812ad785 -- <path>
```

**三类计数**

| 类别 | 计数 | 构成 |
|---|---|---|
| 实质改动 | 294 | 纯实质 238 + 拆分后又被实质修改 34 + 区间新增(拆分提交仅改加载序) 22 + 非拆分删除 0 |
| move-only | 185 | 现存拆分目标/根 165 + 已删除拆分源 20 |
| 未变(仅路径/元数据) | 0 | 代码面无 R100 纯改名、无 mode-only、无 0+0 numstat |
| **合计** | **479** | 295 + 184 + 0 |

**完整性校验**

- 文件全集: `name-status` 代码面 479 个唯一路径; 三类计数相加 295+184+0 = 479, 集合互斥(分类函数单值)。
- 批次并集: B1-B9 相加 = 18+25+9+11+67+23+33+8+285 = 479; B10 为文档面, 代码文件 0; 每文件恰好归属 1 批(单值 `batch(path)`)。
- 增删行: +121,408/−54,061(普通行) + 12 条 rename 行 +1,523/−8,354 = **+122,931/−62,415**, 与计划一致。
- 计数差异解释: 计划 §02 域表 10 行相加为 478(漏 `src/auto_qb/tools/finalize_watch.py`), 合计行 479 与 git 一致; 已入池 docs。
- 未变=0 解释: 679 条 R100 全部在非代码面(memory-bank/issues/reports 等), 代码面 12 条 R 均为拆分残片(相似度 51–72%), 不是纯改名。

## 附录 B · 批次矩阵 B1-B10(定稿)

| 批 | 模块/范围 | 文件数 | 实质 | move-only | 增/删行 | 评审重点 | 依赖坑档(按类索引选读) | 工作量 | 并行性 |
|---|---|---|---|---|---|---|---|---|---|
| B1 | transfer / config(2) / webui route / shared transfer UI / 6 transfer 测试 | 18 | 18 | 0 | +4,686/-3 | transfer 新域全量: 状态门/导出/映射/跳检降级/验证轮询/删源; api_key 凭据与目标 URL 校验; config 两文件只读 transfer 段 | backend: concurrency / behavior-core / high-risk-ops / qb-api; web-ui: contract-api; kb: request-boundary | 1 轮(S2 并行) | 只读可并行 |
| B2 | core / torrents / config(8) / cli / tools finalize_watch | 25 | 25 | 0 | +1,295/-155 | taskqueue 护栏、qB 5.3 facade、traffic sample/store/source、relocate、torrents compat、config 骨架与 5.3 compat、cli/finalize_watch | backend: concurrency / qb-api / traffic-agg-reseal / relocate-restore-issued-marker / last-round-snapshot-stale; web-ui: perf-cadence | 1 轮(S2 并行) | 只读可并行 |
| B3 | rules / config 规则段(2) | 9 | 9 | 0 | +1,066/-177 | W1-W5 规则重设计: base/conditions/registry + actions; config 规则段与 schema/validation 两侧口径 | backend: config-duplicates-runtime-fact / behavior-core; test: plan-docstring-section-boundary | 1 轮(S2 并行) | 只读可并行 |
| B4 | webui py(11) | 11 | 11 | 0 | +276/-74 | webui py: state/torrent_cmds/torrent_detail/traffic_monitor 路由; 认证与输入校验面 | web-ui: contract-api / component-ref-ownership / vue-reactivity; backend: concurrency | 1 轮(S2 并行) | 只读可并行 |
| B5 | webui static 实质(67) | 67 | 67 | 0 | +9,128/-6,423 | static 实质面: shared 非拆分文件 + fx/flux + 四皮肤 CSS/HTML + tpl; 搜索/乐观写/抽屉窗口化/折叠/动效/浮层 | web-ui: drawer-open-vs-kind / drawer-switch-flicker / drawer-merge-hit-region / dur-cell-padding-rowheight / cell-frame-vs-text-width / header-cell-gutter / est-cold-start-vs-absolute-threshold / perf-cadence / template-render / derived-snapshot-render; test: static-guard-mutation | 2 轮(S3 并行) | 只读可并行 |
| B6 | webui static 分片(23) | 23 | 0 | 23 | +6,926/-0 | static move-only 分片: 23 个 R4 分片; 只做 R12 等价核验(加载序/挂载名/CSS 层叠序/守阵聚合读法) | web-ui: template-render / component-ref-ownership; test: static-guard-mutation; 全程 kb: refs-rename | 1 轮(S3 并行) | 只读可并行 |
| B7 | tools/gtm / extensions / scripts | 33 | 21 | 12 | +5,838/-3,965 | gtm GetIfTable2 整表单读、config 写锁/端口契约、proxy 拆分、sim/capture/ui-map 拆分等价 | backend: qb-api; ops: prod-files / console-encoding; test: port/tmpdir; kb: git 包 move-imports | 1 轮(S4 并行) | 只读可并行 |
| B8 | hr / infra / tray | 8 | 8 | 0 | +118/-43 | HR discovery 多 clone 混串、journal 心跳、tray Ctrl+C/信号 | backend: concurrency / fault-domain-classification; ops: port-kill-prod-instance | 1 轮(S4 并行) | 只读可并行 |
| B9 | tests(245 变更) + tests-real(40) | 285 | 135 | 150 | +93,598/-51,575 | tests 遗留质量面 + tests-real 新框架: 覆盖缺口、拆分等价、真机守卫三层与用例边界(不跑真机) | test: plan-docstring-section-boundary / fixed-port-test-collision / tmpdir / perf-measurement / playwright-teardown / red-verify-must-hit-behavior / static-guard-mutation / parallel-run | 2 轮(S5 并行) | 只读可并行 |
| B10 | docs / README / memory-bank 口径段 | 0 | 0 | 0 | +0/-0 | 文档漂移系统审计: qB 5.3 双版本、端口口径、拆分文件边界、命令漂移; 无代码文件 | docs: drift / html-edit / md-edit / anchor-quote; kb: doc-status-meta / refs-rename | 1 轮(S5 并行) | 只读可并行 |

**批次调整理由**

- B5/B6 边界: 计划记 B6≈30 件; 实测 8 个 static 根文件均被区间内其他提交触达(混合), 按「混合按实质全量审」归 B5; B6 只保留 23 个纯分片。8 根文件的搬迁等价仍按附录 C 配对表在 S3 执行。
- B1 config 只取 2 件: `config/models.py` 与 `config/validation/sections.py` 的 transfer 段为主责; 其余 10 件 config 含 qB 5.3/骨架改动, 归 B2/B3, 避免同一文件重复计批。
- B2 增加 `src/auto_qb/tools/finalize_watch.py`: 计划域表漏记(见附录 E), 按 core-adjacent 归 B2。
- B9 文件数 285 = 245 个区间变更 tests + 40 个 tests-real; B9 审计面另含 812ad785 时的 286 个 tests 文件(其中 35 个区间未变), 不计入 479 并集。

## 附录 C · move-only 源→目标配对表(R12 输入)

> 全部配对标注「待 S3 做等价核验」。配对按拆分提交的命名前缀与组推定; 12 条 git rename 残片按组解读(见 issue `docs-split-residue-rename`)。标「含区间改动」的源在拆分前已被非拆分提交修改, 其目标需扩大核验(见 issue `test-split-carried-inrange-changes`)。

### R1 `a48ead5c`

| 源 | 状态 | 目标分片 | 区间内前置改动 | 标注 |
|---|---|---|---|---|
| `tests/test_config.py` | R | `tests/test_config_misc.py` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_extension_proxy.py` | D | `tests/extension_proxy_support.py`, `tests/test_extension_proxy_manifest.py`, `tests/test_extension_proxy_options.py`, `tests/test_extension_proxy_page_fetch.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_grouping.py` | D | `tests/grouping_support.py`, `tests/test_grouping_conflict.py`, `tests/test_grouping_misc.py`, `tests/test_grouping_scan.py`, `tests/test_grouping_state.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_hr_service.py` | D | `tests/hr_service_support.py`, `tests/test_hr_service_misc.py`, `tests/test_hr_service_rows.py`, `tests/test_hr_service_store.py`, `tests/test_hr_service_wave.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_memory_bank.py` | D | `tests/test_memory_bank_cli.py`, `tests/test_memory_bank_docs.py`, `tests/test_memory_bank_naming.py`, `tests/test_memory_bank_structure.py` | 14 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_relocate_exec.py` | D | `tests/relocate_exec_support.py`, `tests/test_relocate_exec_jobs.py`, `tests/test_relocate_exec_misc.py`, `tests/test_relocate_exec_reconcile.py`, `tests/test_relocate_exec_run.py` | 7 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_traffic_sample.py` | R | `tests/test_traffic_sample_store.py` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_dom_page.py` | R | `tests/test_webui_static_dom_page_layout.py` | 6 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_dom_panel.py` | D | `tests/test_webui_static_dom_panel_dialogs.py`, `tests/test_webui_static_dom_panel_drawer.py`, `tests/test_webui_static_dom_panel_misc.py`, `tests/test_webui_static_dom_panel_traffic.py` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_skins.py` | D | `tests/test_webui_static_skins_skin.py`, `tests/test_webui_static_skins_table.py`, `tests/test_webui_static_skins_widget.py` | 15 笔 | 含区间改动; 待 S3 等价核验 |

**R1 共享支撑件/未按前缀配对的目标(按组整体核验)**: `tests/config_write_support.py`, `tests/kb_test_support.py`, `tests/test_config_load.py`, `tests/test_config_rules.py`, `tests/test_traffic_sample_config.py`, `tests/test_traffic_sample_core.py`, `tests/test_traffic_sample_misc.py`, `tests/test_webui_static_dom_page_hr.py`, `tests/test_webui_static_dom_page_store.py`, `tests/traffic_sample_support.py`, `tests/webui_dom_page_support.py`, `tests/webui_dom_panel_support.py`, `tests/webui_static_scan_common.py`, `tests/webui_static_scan_css.py`, `tests/webui_static_scan_js.py`

### R2 `63f47598`

| 源 | 状态 | 目标分片 | 区间内前置改动 | 标注 |
|---|---|---|---|---|
| `tests/test_actions.py` | R | `tests/test_actions_state.py` | 6 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_checking.py` | D | `tests/checking_support.py`, `tests/test_checking_full.py`, `tests/test_checking_group.py`, `tests/test_checking_single.py`, `tests/test_checking_skip.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_config_writer.py` | D | `tests/config_writer_support.py`, `tests/test_config_writer_helpers.py`, `tests/test_config_writer_mask.py`, `tests/test_config_writer_migrate.py`, `tests/test_config_writer_write.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_hr_config.py` | D | `tests/hr_config_support.py`, `tests/test_hr_config_bindings.py`, `tests/test_hr_config_defaults.py`, `tests/test_hr_config_migrate.py`, `tests/test_hr_config_misc.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_hr_report.py` | R | `tests/test_hr_report_status.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_hr_runtime.py` | M | `tests/hr_runtime_support.py`, `tests/test_hr_runtime_apply.py`, `tests/test_hr_runtime_feeder.py`, `tests/test_hr_runtime_lifecycle.py` | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_hr_status.py` | R | `tests/test_hr_status_status.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_hr_worker.py` | R | `tests/test_hr_worker_lifecycle.py` | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_kb_nav.py` | D | `tests/kb_nav_support.py`, `tests/test_kb_nav_data.py`, `tests/test_kb_nav_interaction.py`, `tests/test_kb_nav_server.py`, `tests/test_kb_nav_shell.py` | 5 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_ops.py` | D | `tests/ops_support.py`, `tests/test_ops_guard.py`, `tests/test_ops_misc.py`, `tests/test_ops_recheck.py`, `tests/test_ops_skip.py` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_qbmanager.py` | D | `tests/qbmanager_support.py`, `tests/test_qbmanager_connect.py`, `tests/test_qbmanager_loop.py`, `tests/test_qbmanager_query.py`, `tests/test_qbmanager_tasks.py`, `tests/test_qbmanager_w6.py` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_rule_base.py` | R | `tests/test_rule_base_rule.py` | 7 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_rule_compat.py` | D | `tests/rule_compat_support.py`, `tests/test_rule_compat_choose.py`, `tests/test_rule_compat_engine.py`, `tests/test_rule_compat_mapping.py`, `tests/test_rule_compat_misc.py` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_speed_curve.py` | M | `tests/speed_curve_support.py`, `tests/test_speed_curve_config.py`, `tests/test_speed_curve_curve.py`, `tests/test_speed_curve_dispatch.py`, `tests/test_speed_curve_traffic.py` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_torrents.py` | R | `tests/test_torrents_model.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_traffic_grid.py` | D | `tests/test_traffic_grid_agg.py`, `tests/test_traffic_grid_grid.py`, `tests/test_traffic_grid_group.py`, `tests/test_traffic_grid_seam.py`, `tests/traffic_grid_support.py` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_traffic_source_agent.py` | D | `tests/test_traffic_source_agent_probe.py`, `tests/test_traffic_source_agent_spawn.py`, `tests/test_traffic_source_agent_state.py`, `tests/traffic_source_agent_support.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_traffic_store.py` | D | `tests/test_traffic_store_agg.py`, `tests/test_traffic_store_codec.py`, `tests/test_traffic_store_paths.py`, `tests/test_traffic_store_slots.py`, `tests/test_traffic_store_store.py`, `tests/traffic_store_support.py` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_utils.py` | R | `tests/test_utils_windows.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_backend_misc.py` | D | `tests/test_web_backend_misc_config.py`, `tests/test_web_backend_misc_sites.py`, `tests/test_web_backend_misc_token.py`, `tests/test_web_backend_misc_views.py` | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_web_commands.py` | D | `tests/test_web_commands_bulk.py`, `tests/test_web_commands_commands.py`, `tests/test_web_commands_dispatch.py`, `tests/test_web_commands_reannounce.py` | 5 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_web_hr.py` | D | `tests/test_web_hr_endpoints.py`, `tests/test_web_hr_fs.py`, `tests/test_web_hr_search.py`, `tests/test_web_hr_views.py`, `tests/web_hr_support.py` | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_longtail.py` | D | `tests/test_web_longtail_commands.py`, `tests/test_web_longtail_frontend.py`, `tests/test_web_longtail_routes.py`, `tests/test_web_longtail_runtime.py`, `tests/test_web_longtail_traffic.py` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_web_shortcuts.py` | R | `tests/test_web_shortcuts_drawer.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_delta.py` | R | `tests/test_webui_delta_delta.py` | 0 笔 | -; 待 S3 等价核验 |

**R2 共享支撑件/未按前缀配对的目标(按组整体核验)**: `tests/actions_support.py`, `tests/hr_report_support.py`, `tests/hr_status_support.py`, `tests/hr_worker_support.py`, `tests/test_actions_on_error.py`, `tests/test_actions_skip.py`, `tests/test_actions_tags.py`, `tests/test_hr_report_once.py`, `tests/test_hr_status_entry.py`, `tests/test_hr_worker_notes.py`, `tests/test_rule_base_action.py`, `tests/test_rule_base_context.py`, `tests/test_torrents_store.py`, `tests/test_torrents_view.py`, `tests/test_utils_parse.py`, `tests/test_utils_path.py`, `tests/test_web_shortcuts_cursor.py`, `tests/test_web_shortcuts_engine.py`, `tests/test_web_shortcuts_registry.py`, `tests/test_webui_delta_merge.py`, `tests/torrents_support.py`, `tests/web_shortcuts_support.py`, `tests/webui_delta_support.py`

### R3 `60ee0bec`

| 源 | 状态 | 目标分片 | 区间内前置改动 | 标注 |
|---|---|---|---|---|
| `extensions/hr-fetch-proxy/background.js` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `scripts/qb_capture.py` | M | `scripts/qb_capture_cli.py`, `scripts/qb_capture_core.py` | 0 笔 | -; 待 S3 等价核验 |
| `scripts/sim_qb.py` | M | `scripts/sim_qb_cli.py`, `scripts/sim_qb_core.py`, `scripts/sim_qb_model.py`, `scripts/sim_qb_server.py` | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/extension_proxy_support.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_extension_proxy_manifest.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_extension_proxy_options.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_extension_proxy_page_fetch.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_sim_corpus.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tools/global-traffic-monitor/tests/test_server.py` | M | `tools/global-traffic-monitor/tests/server_support.py`, `tools/global-traffic-monitor/tests/test_server_autostart.py`, `tools/global-traffic-monitor/tests/test_server_routes.py` | 2 笔 | 含区间改动; 待 S3 等价核验 |

**R3 共享支撑件/未按前缀配对的目标(按组整体核验)**: `extensions/hr-fetch-proxy/background-log.js`, `extensions/hr-fetch-proxy/background-support.js`

### R4 `20a74274`

| 源 | 状态 | 目标分片 | 区间内前置改动 | 标注 |
|---|---|---|---|---|
| `src/auto_qb/webui/static/atlas/index.html` | M | (见共享支撑件) | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/console/index.html` | M | (见共享支撑件) | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/flux/index.html` | M | (见共享支撑件) | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/prism/index.html` | M | (见共享支撑件) | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/columns.js` | M | `src/auto_qb/webui/static/shared/columns_computed.js`, `src/auto_qb/webui/static/shared/columns_drag.js`, `src/auto_qb/webui/static/shared/columns_grid.js`, `src/auto_qb/webui/static/shared/columns_menu.js`, `src/auto_qb/webui/static/shared/columns_persist.js` | 5 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/commands.js` | M | `src/auto_qb/webui/static/shared/commands_optimistic.js`, `src/auto_qb/webui/static/shared/commands_send.js` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/config_editor.js` | M | `src/auto_qb/webui/static/shared/config_editor_curve.js`, `src/auto_qb/webui/static/shared/config_editor_form.js`, `src/auto_qb/webui/static/shared/config_editor_tree.js` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/config_hub.js` | M | `src/auto_qb/webui/static/shared/config_hub_hr.js`, `src/auto_qb/webui/static/shared/config_hub_tm.js`, `src/auto_qb/webui/static/shared/config_hub_tracker.js` | 4 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/console_hub.css` | M | `src/auto_qb/webui/static/shared/console_hub_controls.css`, `src/auto_qb/webui/static/shared/console_hub_layout.css`, `src/auto_qb/webui/static/shared/console_hub_panels.css` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/dialogs.js` | M | `src/auto_qb/webui/static/shared/dialogs_history.js`, `src/auto_qb/webui/static/shared/dialogs_meta.js` | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/drawer.js` | M | `src/auto_qb/webui/static/shared/drawer_files.js`, `src/auto_qb/webui/static/shared/drawer_general.js`, `src/auto_qb/webui/static/shared/drawer_rows.js` | 5 笔 | 含区间改动; 待 S3 等价核验 |
| `src/auto_qb/webui/static/shared/shortcuts.js` | M | `src/auto_qb/webui/static/shared/shortcuts_engine.js`, `src/auto_qb/webui/static/shared/shortcuts_panel.js` | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_memory_bank_docs.py` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_transfer_targets_editor.py` | M | (见共享支撑件) | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_web_backend_misc_sites.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_seed_center.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_shortcuts_cursor.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_shortcuts_drawer.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_shortcuts_registry.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_traffic_limit_card.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_web_traffic_monitor.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_ctx_menu_registry.py` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_drawer_fileprio_optimistic.py` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_error_history.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_optimistic_rename_alt.py` | M | (见共享支撑件) | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_dom_page_hr.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_dom_page_layout.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_dom_page_store.py` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_dom_panel_dialogs.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_dom_panel_drawer.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_dom_panel_misc.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_dom_panel_traffic.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_skins_skin.py` | M | (见共享支撑件) | 2 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_static_skins_table.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/test_webui_static_skins_widget.py` | M | (见共享支撑件) | 3 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/test_webui_trigger_registry.py` | M | (见共享支撑件) | 1 笔 | 含区间改动; 待 S3 等价核验 |
| `tests/web_shortcuts_support.py` | M | (见共享支撑件) | 0 笔 | -; 待 S3 等价核验 |
| `tests/webui_helpers.py` | M | (见共享支撑件) | 2 笔 | 含区间改动; 待 S3 等价核验 |

## 附录 D · 逐批文件清单

### B1(18 件)

- `src/auto_qb/config/models.py` · 实质 · M · +72/-1
- `src/auto_qb/config/validation/sections.py` · 实质 · M · +129/-2
- `src/auto_qb/transfer/__init__.py` · 实质 · A · +26/-0
- `src/auto_qb/transfer/adapters/__init__.py` · 实质 · A · +27/-0
- `src/auto_qb/transfer/adapters/base.py` · 实质 · A · +124/-0
- `src/auto_qb/transfer/adapters/qb.py` · 实质 · A · +279/-0
- `src/auto_qb/transfer/adapters/tr.py` · 实质 · A · +27/-0
- `src/auto_qb/transfer/orchestrator.py` · 实质 · A · +445/-0
- `src/auto_qb/webui/server/routes/transfer.py` · 实质 · A · +87/-0
- `src/auto_qb/webui/static/shared/tpl/transfer-targets.html` · 实质 · A · +152/-0
- `src/auto_qb/webui/static/shared/transfer_flow.js` · 实质 · A · +419/-0
- `src/auto_qb/webui/static/shared/transfer_targets.js` · 实质 · A · +314/-0
- `tests/test_transfer_adapters.py` · 实质 · A · +547/-0
- `tests/test_transfer_config.py` · 实质 · A · +313/-0
- `tests/test_transfer_flow_confirm.py` · 实质 · A · +427/-0
- `tests/test_transfer_orchestrator.py` · 实质 · A · +643/-0
- `tests/test_transfer_routes.py` · 实质 · A · +270/-0
- `tests/test_transfer_targets_editor.py` · 实质 · A · +385/-0

### B2(25 件)

- `src/auto_qb/cli.py` · 实质 · M · +5/-1
- `src/auto_qb/config/__init__.py` · 实质 · M · +10/-0
- `src/auto_qb/config/compat.py` · 实质 · A · +250/-0
- `src/auto_qb/config/loaders.py` · 实质 · M · +54/-0
- `src/auto_qb/config/schema/__init__.py` · 实质 · M · +31/-7
- `src/auto_qb/config/schema/fields.py` · 实质 · M · +27/-1
- `src/auto_qb/config/schema/groups.py` · 实质 · M · +14/-0
- `src/auto_qb/config/validation/__init__.py` · 实质 · M · +6/-0
- `src/auto_qb/config/writer.py` · 实质 · M · +96/-8
- `src/auto_qb/core/modules/ops_mod.py` · 实质 · M · +6/-2
- `src/auto_qb/core/modules/relocate_mod.py` · 实质 · M · +251/-53
- `src/auto_qb/core/modules/relocate_units.py` · 实质 · M · +47/-10
- `src/auto_qb/core/modules/rules_mod.py` · 实质 · M · +94/-16
- `src/auto_qb/core/modules/traffic_sample_mod.py` · 实质 · M · +1/-1
- `src/auto_qb/core/qbapi.py` · 实质 · M · +13/-2
- `src/auto_qb/core/qbmanager.py` · 实质 · M · +63/-5
- `src/auto_qb/core/state.py` · 实质 · M · +86/-6
- `src/auto_qb/core/taskqueue.py` · 实质 · M · +72/-24
- `src/auto_qb/core/traffic_source/agent.py` · 实质 · M · +1/-1
- `src/auto_qb/core/traffic_store.py` · 实质 · M · +13/-1
- `src/auto_qb/core/tvshows.py` · 实质 · M · +18/-7
- `src/auto_qb/tools/finalize_watch.py` · 实质 · M · +22/-9
- `src/auto_qb/torrents/compat.py` · 实质 · M · +6/-1
- `src/auto_qb/torrents/record.py` · 实质 · M · +3/-0
- `src/auto_qb/torrents/store.py` · 实质 · M · +106/-0

### B3(9 件)

- `src/auto_qb/config/schema/rules.py` · 实质 · M · +13/-5
- `src/auto_qb/config/validation/rules.py` · 实质 · M · +328/-45
- `src/auto_qb/rules/actions/basic.py` · 实质 · M · +8/-8
- `src/auto_qb/rules/actions/checking.py` · 实质 · M · +3/-3
- `src/auto_qb/rules/actions/full_checking.py` · 实质 · M · +4/-0
- `src/auto_qb/rules/actions/transfer.py` · 实质 · M · +4/-4
- `src/auto_qb/rules/base.py` · 实质 · M · +522/-94
- `src/auto_qb/rules/conditions.py` · 实质 · M · +6/-6
- `src/auto_qb/rules/registry.py` · 实质 · M · +178/-12

### B4(11 件)

- `src/auto_qb/webui/commands.py` · 实质 · M · +197/-46
- `src/auto_qb/webui/module.py` · 实质 · M · +1/-1
- `src/auto_qb/webui/runtime.py` · 实质 · M · +23/-8
- `src/auto_qb/webui/server/common.py` · 实质 · M · +20/-0
- `src/auto_qb/webui/server/routes/__init__.py` · 实质 · M · +2/-1
- `src/auto_qb/webui/server/routes/state.py` · 实质 · M · +4/-0
- `src/auto_qb/webui/server/routes/torrent_cmds.py` · 实质 · M · +10/-9
- `src/auto_qb/webui/server/routes/torrent_detail.py` · 实质 · M · +3/-3
- `src/auto_qb/webui/server/routes/traffic_monitor.py` · 实质 · M · +6/-1
- `src/auto_qb/webui/tool_client.py` · 实质 · M · +3/-3
- `src/auto_qb/webui/views.py` · 实质 · M · +7/-2

### B5(67 件)

- `src/auto_qb/webui/static/atlas/css/components.css` · 实质 · M · +12/-12
- `src/auto_qb/webui/static/atlas/css/views.css` · 实质 · M · +15/-1
- `src/auto_qb/webui/static/atlas/index.html` · 实质 · M · +29/-2
- `src/auto_qb/webui/static/atlas/style.css` · 实质 · M · +2/-0
- `src/auto_qb/webui/static/console/css/components.css` · 实质 · M · +25/-11
- `src/auto_qb/webui/static/console/css/views.css` · 实质 · M · +1/-1
- `src/auto_qb/webui/static/console/index.html` · 实质 · M · +29/-2
- `src/auto_qb/webui/static/console/style.css` · 实质 · M · +2/-0
- `src/auto_qb/webui/static/flux/css/components.css` · 实质 · A · +700/-0
- `src/auto_qb/webui/static/flux/css/dialogs.css` · 实质 · A · +582/-0
- `src/auto_qb/webui/static/flux/css/fx-mount.css` · 实质 · A · +382/-0
- `src/auto_qb/webui/static/flux/css/views.css` · 实质 · A · +498/-0
- `src/auto_qb/webui/static/flux/fx-mount.js` · 实质 · A · +448/-0
- `src/auto_qb/webui/static/flux/index.html` · 实质 · A · +256/-0
- `src/auto_qb/webui/static/flux/style.css` · 实质 · A · +205/-0
- `src/auto_qb/webui/static/fx/showcase-modern.css` · 实质 · A · +27/-0
- `src/auto_qb/webui/static/fx/showcase.html` · 实质 · A · +3045/-0
- `src/auto_qb/webui/static/prism/css/components.css` · 实质 · M · +25/-4
- `src/auto_qb/webui/static/prism/css/tokens.css` · 实质 · M · +2/-0
- `src/auto_qb/webui/static/prism/css/views.css` · 实质 · M · +8/-8
- `src/auto_qb/webui/static/prism/index.html` · 实质 · M · +29/-2
- `src/auto_qb/webui/static/shared/add_torrent.js` · 实质 · M · +6/-6
- `src/auto_qb/webui/static/shared/app.js` · 实质 · M · +30/-7
- `src/auto_qb/webui/static/shared/auth.js` · 实质 · M · +6/-0
- `src/auto_qb/webui/static/shared/columns.js` · 实质 · M · +108/-872
- `src/auto_qb/webui/static/shared/commands.js` · 实质 · M · +31/-591
- `src/auto_qb/webui/static/shared/config_editor.js` · 实质 · M · +15/-728
- `src/auto_qb/webui/static/shared/config_hub.js` · 实质 · M · +13/-855
- `src/auto_qb/webui/static/shared/config_rules.js` · 实质 · M · +516/-18
- `src/auto_qb/webui/static/shared/console_hub.css` · 实质 · M · +0/-1227
- `src/auto_qb/webui/static/shared/ctx_menu.js` · 实质 · M · +34/-8
- `src/auto_qb/webui/static/shared/ctx_menu_custom.js` · 实质 · M · +1/-1
- `src/auto_qb/webui/static/shared/delete_flow.js` · 实质 · M · +8/-6
- `src/auto_qb/webui/static/shared/dialogs.js` · 实质 · M · +12/-251
- `src/auto_qb/webui/static/shared/drawer.js` · 实质 · M · +35/-637
- `src/auto_qb/webui/static/shared/drawer_store.js` · 实质 · M · +19/-8
- `src/auto_qb/webui/static/shared/drawer_templates.js` · 实质 · M · +102/-0
- `src/auto_qb/webui/static/shared/drawer_tpl/05-trackers-health-groups-low.js` · 实质 · M · +0/-7
- `src/auto_qb/webui/static/shared/drawer_tpl/06-trackers-table-collapsed.js` · 实质 · M · +0/-7
- `src/auto_qb/webui/static/shared/drawer_tpl/09-peers-density-collapsed.js` · 实质 · M · +0/-2
- `src/auto_qb/webui/static/shared/drawer_tpl/10-content-tree-detail-tall.js` · 实质 · M · +60/-7
- `src/auto_qb/webui/static/shared/drawer_tpl/11-content-treegrid-batch-low.js` · 实质 · M · +82/-15
- `src/auto_qb/webui/static/shared/dt_table.css` · 实质 · M · +13/-0
- `src/auto_qb/webui/static/shared/filters.js` · 实质 · M · +13/-0
- `src/auto_qb/webui/static/shared/fx/fx-presets.css` · 实质 · A · +240/-0
- `src/auto_qb/webui/static/shared/fx/fx.css` · 实质 · A · +508/-0
- `src/auto_qb/webui/static/shared/fx/fx.js` · 实质 · A · +255/-0
- `src/auto_qb/webui/static/shared/hscroll.css` · 实质 · A · +73/-0
- `src/auto_qb/webui/static/shared/lifecycle.js` · 实质 · M · +4/-2
- `src/auto_qb/webui/static/shared/menu.js` · 实质 · M · +7/-4
- `src/auto_qb/webui/static/shared/polling.js` · 实质 · M · +25/-1
- `src/auto_qb/webui/static/shared/qb_traffic_chart.js` · 实质 · M · +1/-1
- `src/auto_qb/webui/static/shared/row_lang.css` · 实质 · M · +92/-44
- `src/auto_qb/webui/static/shared/selection.js` · 实质 · M · +11/-5
- `src/auto_qb/webui/static/shared/shortcuts.js` · 实质 · M · +0/-1001
- `src/auto_qb/webui/static/shared/state.js` · 实质 · M · +73/-6
- `src/auto_qb/webui/static/shared/tpl/ctx-menus.html` · 实质 · M · +22/-15
- `src/auto_qb/webui/static/shared/tpl/groups.html` · 实质 · M · +1/-1
- `src/auto_qb/webui/static/shared/tpl/overlays.html` · 实质 · M · +4/-1
- `src/auto_qb/webui/static/shared/tpl/rule-tree.html` · 实质 · A · +183/-0
- `src/auto_qb/webui/static/shared/tpl/settings-detail.html` · 实质 · M · +8/-0
- `src/auto_qb/webui/static/shared/tpl/settings.html` · 实质 · M · +66/-33
- `src/auto_qb/webui/static/shared/tpl/topbar.html` · 实质 · M · +6/-0
- `src/auto_qb/webui/static/shared/tpl/xtpl.html` · 实质 · M · +11/-1
- `src/auto_qb/webui/static/shared/triggers.js` · 实质 · M · +12/-0
- `src/auto_qb/webui/static/shared/ui_feedback.js` · 实质 · M · +25/-2
- `src/auto_qb/webui/static/shared/view.js` · 实质 · M · +75/-10

### B6(23 件)

- `src/auto_qb/webui/static/shared/columns_computed.js` · move-only · A · +191/-0
- `src/auto_qb/webui/static/shared/columns_drag.js` · move-only · A · +119/-0
- `src/auto_qb/webui/static/shared/columns_grid.js` · move-only · A · +477/-0
- `src/auto_qb/webui/static/shared/columns_menu.js` · move-only · A · +333/-0
- `src/auto_qb/webui/static/shared/columns_persist.js` · move-only · A · +218/-0
- `src/auto_qb/webui/static/shared/commands_optimistic.js` · move-only · A · +224/-0
- `src/auto_qb/webui/static/shared/commands_send.js` · move-only · A · +432/-0
- `src/auto_qb/webui/static/shared/config_editor_curve.js` · move-only · A · +308/-0
- `src/auto_qb/webui/static/shared/config_editor_form.js` · move-only · A · +185/-0
- `src/auto_qb/webui/static/shared/config_editor_tree.js` · move-only · A · +242/-0
- `src/auto_qb/webui/static/shared/config_hub_hr.js` · move-only · A · +187/-0
- `src/auto_qb/webui/static/shared/config_hub_tm.js` · move-only · A · +431/-0
- `src/auto_qb/webui/static/shared/config_hub_tracker.js` · move-only · A · +256/-0
- `src/auto_qb/webui/static/shared/console_hub_controls.css` · move-only · A · +514/-0
- `src/auto_qb/webui/static/shared/console_hub_layout.css` · move-only · A · +315/-0
- `src/auto_qb/webui/static/shared/console_hub_panels.css` · move-only · A · +459/-0
- `src/auto_qb/webui/static/shared/dialogs_history.js` · move-only · A · +40/-0
- `src/auto_qb/webui/static/shared/dialogs_meta.js` · move-only · A · +273/-0
- `src/auto_qb/webui/static/shared/drawer_files.js` · move-only · A · +152/-0
- `src/auto_qb/webui/static/shared/drawer_general.js` · move-only · A · +348/-0
- `src/auto_qb/webui/static/shared/drawer_rows.js` · move-only · A · +207/-0
- `src/auto_qb/webui/static/shared/shortcuts_engine.js` · move-only · A · +804/-0
- `src/auto_qb/webui/static/shared/shortcuts_panel.js` · move-only · A · +211/-0

### B7(33 件)

- `extensions/hr-fetch-proxy/background-log.js` · move-only · A · +219/-0
- `extensions/hr-fetch-proxy/background-support.js` · move-only · A · +574/-0
- `extensions/hr-fetch-proxy/background.js` · 实质 · M · +2/-794
- `scripts/check_command_drift.py` · 实质 · M · +26/-3
- `scripts/check_context_caps.py` · 实质 · M · +45/-16
- `scripts/e2e_selfcheck.py` · 实质 · A · +154/-0
- `scripts/qb_capture.py` · move-only · M · +6/-605
- `scripts/qb_capture_cli.py` · move-only · A · +122/-0
- `scripts/qb_capture_core.py` · move-only · A · +540/-0
- `scripts/sim_qb.py` · 实质 · M · +13/-1928
- `scripts/sim_qb_cli.py` · move-only · A · +365/-0
- `scripts/sim_qb_core.py` · move-only · A · +415/-0
- `scripts/sim_qb_model.py` · move-only · A · +894/-0
- `scripts/sim_qb_server.py` · move-only · A · +296/-0
- `scripts/ui_content_map.py` · 实质 · A · +210/-0
- `scripts/ui_harness.py` · 实质 · M · +102/-1
- `tools/global-traffic-monitor/README.md` · 实质 · M · +4/-2
- `tools/global-traffic-monitor/pyproject.toml` · 实质 · M · +4/-2
- `tools/global-traffic-monitor/src/gtm/__init__.py` · 实质 · M · +4/-2
- `tools/global-traffic-monitor/src/gtm/__main__.py` · 实质 · M · +1/-1
- `tools/global-traffic-monitor/src/gtm/config.py` · 实质 · M · +34/-8
- `tools/global-traffic-monitor/src/gtm/nic.py` · 实质 · A · +394/-0
- `tools/global-traffic-monitor/src/gtm/sampler.py` · 实质 · M · +28/-7
- `tools/global-traffic-monitor/src/gtm/server.py` · 实质 · M · +50/-9
- `tools/global-traffic-monitor/src/gtm/storage.py` · 实质 · M · +1/-1
- `tools/global-traffic-monitor/tests/conftest.py` · 实质 · M · +24/-0
- `tools/global-traffic-monitor/tests/server_support.py` · move-only · A · +115/-0
- `tools/global-traffic-monitor/tests/test_config.py` · 实质 · M · +28/-0
- `tools/global-traffic-monitor/tests/test_nic.py` · 实质 · A · +434/-0
- `tools/global-traffic-monitor/tests/test_sampler.py` · 实质 · M · +49/-1
- `tools/global-traffic-monitor/tests/test_server.py` · 实质 · M · +5/-585
- `tools/global-traffic-monitor/tests/test_server_autostart.py` · move-only · A · +395/-0
- `tools/global-traffic-monitor/tests/test_server_routes.py` · move-only · A · +285/-0

### B8(8 件)

- `src/auto_qb/hr/discovery.py` · 实质 · M · +2/-3
- `src/auto_qb/hr/events.py` · 实质 · M · +2/-2
- `src/auto_qb/hr/fetcher.py` · 实质 · M · +4/-2
- `src/auto_qb/hr/server.py` · 实质 · M · +2/-2
- `src/auto_qb/hr/service.py` · 实质 · M · +30/-12
- `src/auto_qb/hr/worker.py` · 实质 · M · +2/-2
- `src/auto_qb/infra/relocate_journal.py` · 实质 · M · +24/-4
- `src/auto_qb/tray/app.py` · 实质 · M · +52/-16

### B9(285 件)

- `tests-real/config/instances.example.json` · 实质 · A · +8/-0
- `tests-real/conftest.py` · 实质 · A · +96/-0
- `tests-real/lib/__init__.py` · 实质 · A · +7/-0
- `tests-real/lib/app.py` · 实质 · A · +356/-0
- `tests-real/lib/bencode.py` · 实质 · A · +48/-0
- `tests-real/lib/env_registry.py` · 实质 · A · +89/-0
- `tests-real/lib/guard.py` · 实质 · A · +172/-0
- `tests-real/lib/instances.py` · 实质 · A · +47/-0
- `tests-real/lib/net.py` · 实质 · A · +26/-0
- `tests-real/lib/proxy.py` · 实质 · A · +216/-0
- `tests-real/lib/qb.py` · 实质 · A · +151/-0
- `tests-real/lib/small_target.py` · 实质 · A · +114/-0
- `tests-real/lib/torrent.py` · 实质 · A · +150/-0
- `tests-real/lib/tracker.py` · 实质 · A · +116/-0
- `tests-real/rm00_infra/test_rm00_infra.py` · 实质 · A · +217/-0
- `tests-real/rm01_startup/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm01_startup/test_rm01_startup.py` · 实质 · A · +335/-0
- `tests-real/rm02_loop/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm02_loop/test_rm02_loop.py` · 实质 · A · +700/-0
- `tests-real/rm03_rules/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm03_rules/test_rm03_drift.py` · 实质 · A · +1209/-0
- `tests-real/rm03_rules/test_rm03_rules.py` · 实质 · A · +1008/-0
- `tests-real/rm04_relocate/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm04_relocate/test_rm04_relocate.py` · 实质 · A · +1534/-0
- `tests-real/rm05_tracker_tags/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm05_tracker_tags/test_rm05_tracker_tags.py` · 实质 · A · +852/-0
- `tests-real/rm06_hr/conftest.py` · 实质 · A · +57/-0
- `tests-real/rm06_hr/test_rm06_hr.py` · 实质 · A · +1253/-0
- `tests-real/rm07_traffic/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm07_traffic/test_rm07_traffic.py` · 实质 · A · +1025/-0
- `tests-real/rm08_webui_read/conftest.py` · 实质 · A · +57/-0
- `tests-real/rm08_webui_read/test_rm08_webui_read.py` · 实质 · A · +1390/-0
- `tests-real/rm09_webui_write/conftest.py` · 实质 · A · +56/-0
- `tests-real/rm09_webui_write/test_rm09_webui_write.py` · 实质 · A · +1086/-0
- `tests-real/rm10_notify/conftest.py` · 实质 · A · +57/-0
- `tests-real/rm10_notify/test_rm10_notify.py` · 实质 · A · +905/-0
- `tests-real/runner.py` · 实质 · A · +230/-0
- `tests-real/seed.py` · 实质 · A · +396/-0
- `tests-real/tools/diag_l2.py` · 实质 · A · +108/-0
- `tests-real/tools/diag_log.py` · 实质 · A · +19/-0
- `tests/_test_ports.py` · 实质 · A · +32/-0
- `tests/_tmp_bootstrap.py` · 实质 · A · +361/-0
- `tests/actions_support.py` · move-only · A · +61/-0
- `tests/checking_support.py` · move-only · A · +182/-0
- `tests/config_write_support.py` · move-only · A · +85/-0
- `tests/config_writer_support.py` · move-only · A · +49/-0
- `tests/conftest.py` · 实质 · M · +45/-0
- `tests/extension_proxy_support.py` · 实质 · A · +1237/-0
- `tests/fixtures/config_key_surface.txt` · 实质 · M · +9/-0
- `tests/grouping_support.py` · move-only · A · +120/-0
- `tests/helpers.py` · 实质 · M · +38/-8
- `tests/hr_config_support.py` · move-only · A · +45/-0
- `tests/hr_report_support.py` · move-only · A · +98/-0
- `tests/hr_runtime_support.py` · move-only · A · +108/-0
- `tests/hr_service_support.py` · move-only · A · +344/-0
- `tests/hr_status_support.py` · move-only · A · +102/-0
- `tests/hr_worker_support.py` · move-only · A · +73/-0
- `tests/kb_nav_support.py` · move-only · A · +118/-0
- `tests/kb_test_support.py` · move-only · A · +442/-0
- `tests/ops_support.py` · move-only · A · +95/-0
- `tests/qbmanager_support.py` · move-only · A · +53/-0
- `tests/relocate_exec_support.py` · move-only · A · +268/-0
- `tests/rule_compat_support.py` · move-only · A · +97/-0
- `tests/sidefx.py` · 实质 · M · +22/-5
- `tests/speed_curve_support.py` · move-only · A · +117/-0
- `tests/test_actions_on_error.py` · move-only · A · +253/-0
- `tests/test_actions_skip.py` · move-only · A · +219/-0
- `tests/test_actions_state.py` · 实质 · R057 · +260/-362
- `tests/test_actions_tags.py` · move-only · A · +204/-0
- `tests/test_alias_fs.py` · 实质 · M · +9/-2
- `tests/test_checking.py` · move-only · D · +0/-1822
- `tests/test_checking_full.py` · move-only · A · +470/-0
- `tests/test_checking_group.py` · 实质 · A · +526/-0
- `tests/test_checking_single.py` · move-only · A · +311/-0
- `tests/test_checking_skip.py` · move-only · A · +715/-0
- `tests/test_command_drift.py` · 实质 · A · +75/-0
- `tests/test_conditions.py` · 实质 · M · +44/-0
- `tests/test_config_key_surface.py` · 实质 · M · +76/-1
- `tests/test_config_load.py` · move-only · A · +467/-0
- `tests/test_config_misc.py` · 实质 · R072 · +42/-696
- `tests/test_config_rules.py` · move-only · A · +230/-0
- `tests/test_config_schema.py` · 实质 · M · +15/-9
- `tests/test_config_writer.py` · move-only · D · +0/-1746
- `tests/test_config_writer_helpers.py` · move-only · A · +402/-0
- `tests/test_config_writer_mask.py` · move-only · A · +421/-0
- `tests/test_config_writer_migrate.py` · move-only · A · +511/-0
- `tests/test_config_writer_write.py` · move-only · A · +642/-0
- `tests/test_docs_forms.py` · 实质 · M · +79/-0
- `tests/test_episodes.py` · 实质 · M · +24/-0
- `tests/test_exporter.py` · 实质 · M · +230/-0
- `tests/test_expr_eval.py` · 实质 · M · +370/-7
- `tests/test_expr_parse.py` · 实质 · M · +53/-0
- `tests/test_extension_proxy.py` · move-only · D · +0/-2300
- `tests/test_extension_proxy_manifest.py` · 实质 · A · +197/-0
- `tests/test_extension_proxy_options.py` · 实质 · A · +210/-0
- `tests/test_extension_proxy_page_fetch.py` · 实质 · A · +837/-0
- `tests/test_finalize_watch.py` · 实质 · M · +66/-0
- `tests/test_free_port.py` · 实质 · A · +81/-0
- `tests/test_grouping.py` · move-only · D · +0/-2014
- `tests/test_grouping_conflict.py` · move-only · A · +452/-0
- `tests/test_grouping_misc.py` · move-only · A · +614/-0
- `tests/test_grouping_scan.py` · move-only · A · +585/-0
- `tests/test_grouping_state.py` · move-only · A · +804/-0
- `tests/test_hr_config.py` · move-only · D · +0/-1562
- `tests/test_hr_config_bindings.py` · move-only · A · +669/-0
- `tests/test_hr_config_defaults.py` · move-only · A · +653/-0
- `tests/test_hr_config_migrate.py` · move-only · A · +247/-0
- `tests/test_hr_config_misc.py` · move-only · A · +81/-0
- `tests/test_hr_discovery.py` · 实质 · M · +15/-7
- `tests/test_hr_events.py` · 实质 · M · +15/-0
- `tests/test_hr_report_once.py` · move-only · A · +412/-0
- `tests/test_hr_report_status.py` · move-only · R064 · +21/-447
- `tests/test_hr_runtime.py` · 实质 · M · +5/-1161
- `tests/test_hr_runtime_apply.py` · move-only · A · +264/-0
- `tests/test_hr_runtime_feeder.py` · move-only · A · +478/-0
- `tests/test_hr_runtime_lifecycle.py` · move-only · A · +440/-0
- `tests/test_hr_server.py` · 实质 · M · +14/-7
- `tests/test_hr_service.py` · move-only · D · +0/-4439
- `tests/test_hr_service_misc.py` · move-only · A · +1543/-0
- `tests/test_hr_service_rows.py` · move-only · A · +1093/-0
- `tests/test_hr_service_store.py` · move-only · A · +642/-0
- `tests/test_hr_service_wave.py` · move-only · A · +1409/-0
- `tests/test_hr_status_entry.py` · move-only · A · +541/-0
- `tests/test_hr_status_status.py` · move-only · R059 · +14/-519
- `tests/test_hr_worker_lifecycle.py` · 实质 · R059 · +22/-503
- `tests/test_hr_worker_notes.py` · move-only · A · +520/-0
- `tests/test_kb_docrefs_tools.py` · 实质 · A · +170/-0
- `tests/test_kb_nav_data.py` · move-only · A · +152/-0
- `tests/test_kb_nav_interaction.py` · 实质 · A · +499/-0
- `tests/test_kb_nav_server.py` · move-only · A · +277/-0
- `tests/test_kb_nav_shell.py` · 实质 · R059 · +61/-462
- `tests/test_kb_writeform.py` · 实质 · A · +101/-0
- `tests/test_local_qb_service.py` · 实质 · M · +39/-0
- `tests/test_locking.py` · 实质 · M · +7/-11
- `tests/test_memory_bank.py` · move-only · D · +0/-2083
- `tests/test_memory_bank_cli.py` · move-only · A · +1573/-0
- `tests/test_memory_bank_docs.py` · 实质 · A · +1060/-0
- `tests/test_memory_bank_naming.py` · move-only · A · +135/-0
- `tests/test_memory_bank_structure.py` · move-only · A · +458/-0
- `tests/test_module_host.py` · 实质 · M · +334/-0
- `tests/test_modules_p5.py` · 实质 · M · +186/-1
- `tests/test_modules_w9b_s5.py` · 实质 · A · +1054/-0
- `tests/test_ops.py` · move-only · D · +0/-1532
- `tests/test_ops_guard.py` · move-only · A · +371/-0
- `tests/test_ops_misc.py` · move-only · A · +124/-0
- `tests/test_ops_recheck.py` · move-only · A · +733/-0
- `tests/test_ops_skip.py` · move-only · A · +975/-0
- `tests/test_qbapi_wire.py` · 实质 · A · +129/-0
- `tests/test_qbmanager.py` · move-only · D · +0/-1285
- `tests/test_qbmanager_connect.py` · move-only · A · +474/-0
- `tests/test_qbmanager_loop.py` · move-only · A · +301/-0
- `tests/test_qbmanager_query.py` · 实质 · A · +703/-0
- `tests/test_qbmanager_tasks.py` · move-only · A · +513/-0
- `tests/test_qbmanager_w6.py` · move-only · A · +548/-0
- `tests/test_real_machine_safety.py` · 实质 · A · +107/-0
- `tests/test_registry.py` · 实质 · M · +38/-24
- `tests/test_registry_derived.py` · 实质 · A · +247/-0
- `tests/test_relocate_exec.py` · move-only · D · +0/-893
- `tests/test_relocate_exec_jobs.py` · move-only · A · +629/-0
- `tests/test_relocate_exec_misc.py` · 实质 · A · +536/-0
- `tests/test_relocate_exec_reconcile.py` · move-only · A · +415/-0
- `tests/test_relocate_exec_run.py` · move-only · A · +1129/-0
- `tests/test_relocate_paths.py` · 实质 · M · +11/-2
- `tests/test_relocate_units.py` · 实质 · M · +419/-7
- `tests/test_rule_base.py` · move-only · D · +0/-808
- `tests/test_rule_base_action.py` · move-only · A · +45/-0
- `tests/test_rule_base_context.py` · move-only · A · +240/-0
- `tests/test_rule_base_rule.py` · 实质 · A · +955/-0
- `tests/test_rule_compat_choose.py` · move-only · A · +459/-0
- `tests/test_rule_compat_engine.py` · move-only · A · +146/-0
- `tests/test_rule_compat_mapping.py` · move-only · A · +541/-0
- `tests/test_rule_compat_misc.py` · move-only · A · +536/-0
- `tests/test_rule_engine.py` · 实质 · M · +173/-1
- `tests/test_rule_trace.py` · 实质 · A · +337/-0
- `tests/test_rules_core.py` · 实质 · M · +12/-12
- `tests/test_sidefx.py` · 实质 · M · +17/-0
- `tests/test_sim_corpus.py` · move-only · M · +5/-3
- `tests/test_snapshot_sync.py` · 实质 · M · +139/-0
- `tests/test_speed_curve.py` · 实质 · M · +9/-1234
- `tests/test_speed_curve_config.py` · move-only · A · +559/-0
- `tests/test_speed_curve_curve.py` · move-only · A · +171/-0
- `tests/test_speed_curve_dispatch.py` · move-only · A · +496/-0
- `tests/test_speed_curve_traffic.py` · move-only · A · +168/-0
- `tests/test_store_expect.py` · 实质 · A · +109/-0
- `tests/test_taskqueue.py` · 实质 · M · +257/-2
- `tests/test_tmp_bootstrap.py` · 实质 · A · +134/-0
- `tests/test_torrents_model.py` · move-only · R052 · +10/-628
- `tests/test_torrents_store.py` · move-only · A · +475/-0
- `tests/test_torrents_view.py` · move-only · A · +77/-0
- `tests/test_traffic_grid.py` · move-only · D · +0/-1355
- `tests/test_traffic_grid_agg.py` · move-only · A · +533/-0
- `tests/test_traffic_grid_grid.py` · move-only · A · +778/-0
- `tests/test_traffic_grid_group.py` · move-only · A · +249/-0
- `tests/test_traffic_grid_seam.py` · move-only · A · +358/-0
- `tests/test_traffic_limits.py` · 实质 · M · +277/-0
- `tests/test_traffic_monitor_client.py` · 实质 · M · +40/-0
- `tests/test_traffic_sample_config.py` · move-only · A · +233/-0
- `tests/test_traffic_sample_core.py` · move-only · A · +1851/-0
- `tests/test_traffic_sample_misc.py` · move-only · A · +102/-0
- `tests/test_traffic_sample_store.py` · 实质 · R052 · +603/-1699
- `tests/test_traffic_snapshot.py` · 实质 · M · +146/-1
- `tests/test_traffic_source_agent.py` · move-only · D · +0/-769
- `tests/test_traffic_source_agent_probe.py` · move-only · A · +526/-0
- `tests/test_traffic_source_agent_spawn.py` · move-only · A · +587/-0
- `tests/test_traffic_source_agent_state.py` · move-only · A · +144/-0
- `tests/test_traffic_source_paths.py` · 实质 · M · +32/-0
- `tests/test_traffic_source_reader.py` · 实质 · A · +104/-0
- `tests/test_traffic_store.py` · move-only · D · +0/-1952
- `tests/test_traffic_store_agg.py` · move-only · A · +370/-0
- `tests/test_traffic_store_codec.py` · move-only · A · +988/-0
- `tests/test_traffic_store_paths.py` · move-only · A · +772/-0
- `tests/test_traffic_store_slots.py` · move-only · A · +301/-0
- `tests/test_traffic_store_store.py` · move-only · A · +565/-0
- `tests/test_tray.py` · 实质 · M · +115/-3
- `tests/test_trigger_events.py` · 实质 · M · +1/-1
- `tests/test_tvshows.py` · 实质 · M · +251/-0
- `tests/test_ui.py` · 实质 · M · +4/-0
- `tests/test_utils_parse.py` · move-only · A · +834/-0
- `tests/test_utils_path.py` · move-only · A · +282/-0
- `tests/test_utils_windows.py` · move-only · R051 · +13/-1070
- `tests/test_web_auth.py` · 实质 · M · +1/-6
- `tests/test_web_backend_misc.py` · move-only · D · +0/-1294
- `tests/test_web_backend_misc_config.py` · move-only · A · +194/-0
- `tests/test_web_backend_misc_sites.py` · 实质 · A · +371/-0
- `tests/test_web_backend_misc_token.py` · move-only · A · +199/-0
- `tests/test_web_backend_misc_views.py` · move-only · A · +639/-0
- `tests/test_web_commands.py` · move-only · D · +0/-2014
- `tests/test_web_commands_bulk.py` · move-only · A · +411/-0
- `tests/test_web_commands_commands.py` · move-only · A · +205/-0
- `tests/test_web_commands_dispatch.py` · move-only · A · +1059/-0
- `tests/test_web_commands_reannounce.py` · move-only · A · +505/-0
- `tests/test_web_hr.py` · move-only · D · +0/-2005
- `tests/test_web_hr_endpoints.py` · move-only · A · +592/-0
- `tests/test_web_hr_fs.py` · move-only · A · +443/-0
- `tests/test_web_hr_search.py` · 实质 · A · +658/-0
- `tests/test_web_hr_views.py` · move-only · A · +463/-0
- `tests/test_web_longtail.py` · move-only · D · +0/-1059
- `tests/test_web_longtail_commands.py` · move-only · A · +247/-0
- `tests/test_web_longtail_frontend.py` · move-only · A · +169/-0
- `tests/test_web_longtail_routes.py` · move-only · A · +361/-0
- `tests/test_web_longtail_runtime.py` · move-only · A · +219/-0
- `tests/test_web_longtail_traffic.py` · 实质 · A · +333/-0
- `tests/test_web_relocate.py` · 实质 · M · +179/-1
- `tests/test_web_route_manifest.py` · 实质 · M · +5/-2
- `tests/test_web_seed_center.py` · move-only · M · +3/-9
- `tests/test_web_shortcuts_cursor.py` · 实质 · A · +522/-0
- `tests/test_web_shortcuts_drawer.py` · move-only · R054 · +18/-749
- `tests/test_web_shortcuts_engine.py` · move-only · A · +82/-0
- `tests/test_web_shortcuts_registry.py` · 实质 · A · +179/-0
- `tests/test_web_traffic_limit_card.py` · move-only · M · +3/-1
- `tests/test_web_traffic_monitor.py` · move-only · M · +3/-1
- `tests/test_web_views_reload.py` · 实质 · M · +1/-9
- `tests/test_webui_ctx_menu_registry.py` · 实质 · M · +44/-17
- `tests/test_webui_delta_delta.py` · move-only · R054 · +18/-527
- `tests/test_webui_delta_merge.py` · move-only · A · +484/-0
- `tests/test_webui_drawer_fileprio_optimistic.py` · 实质 · A · +212/-0
- `tests/test_webui_error_history.py` · move-only · M · +8/-2
- `tests/test_webui_optimistic_rename_alt.py` · 实质 · A · +517/-0
- `tests/test_webui_static_dom_page_hr.py` · 实质 · A · +364/-0
- `tests/test_webui_static_dom_page_layout.py` · move-only · R058 · +441/-692
- `tests/test_webui_static_dom_page_store.py` · 实质 · A · +225/-0
- `tests/test_webui_static_dom_panel.py` · move-only · D · +0/-6649
- `tests/test_webui_static_dom_panel_dialogs.py` · 实质 · A · +1870/-0
- `tests/test_webui_static_dom_panel_drawer.py` · 实质 · A · +2821/-0
- `tests/test_webui_static_dom_panel_misc.py` · 实质 · A · +1006/-0
- `tests/test_webui_static_dom_panel_traffic.py` · 实质 · A · +1445/-0
- `tests/test_webui_static_skins.py` · move-only · D · +0/-3073
- `tests/test_webui_static_skins_skin.py` · 实质 · A · +699/-0
- `tests/test_webui_static_skins_table.py` · 实质 · A · +1579/-0
- `tests/test_webui_static_skins_widget.py` · 实质 · A · +568/-0
- `tests/test_webui_trigger_registry.py` · 实质 · M · +24/-9
- `tests/torrents_support.py` · move-only · A · +122/-0
- `tests/traffic_grid_support.py` · move-only · A · +66/-0
- `tests/traffic_sample_support.py` · move-only · A · +336/-0
- `tests/traffic_source_agent_support.py` · move-only · A · +67/-0
- `tests/traffic_store_support.py` · move-only · A · +135/-0
- `tests/web_hr_support.py` · move-only · A · +32/-0
- `tests/web_shortcuts_support.py` · 实质 · A · +70/-0
- `tests/webui_delta_support.py` · move-only · A · +74/-0
- `tests/webui_dom_page_support.py` · move-only · A · +585/-0
- `tests/webui_dom_panel_support.py` · move-only · A · +39/-0
- `tests/webui_helpers.py` · 实质 · M · +62/-1
- `tests/webui_static_scan_common.py` · 实质 · A · +438/-0
- `tests/webui_static_scan_css.py` · 实质 · A · +437/-0
- `tests/webui_static_scan_js.py` · 实质 · A · +890/-0

## 附录 E · 本步新增 issue(3 条, topic `code-review-3-s1`)

1. `memory-bank/issues/26-11-03-0704-docs-plan-domain-table-count.html` — docs/light: 计划 §02 域表分项合计 478 vs 总数 479, 漏 `src/auto_qb/tools/finalize_watch.py`。
2. `memory-bank/issues/26-11-03-0704-test-split-carried-inrange-changes.html` — test/standard: 拆分目标承载区间内既有实质改动, move-only 仅做 R12 不覆盖逐行评审(污染源 R1 9/10、R2 18/25、R3 3/9、R4 22/38)。
3. `memory-bank/issues/26-11-03-0704-docs-split-residue-rename.html` — docs/light: 12 条 R051-R072 是拆分残片, 配对表不能按 1:1 改名解读。

## 附录 F · 交给 S2 的输入清单

1. **批次清单**: 附录 D 的 B1-B4 文件清单(18/25/9/11), 每文件带标类与增删行; B1/B2/B3 的 config 文件按主责段读, 不重复计批。
2. **基线锚**: `4933 passed + 2 skipped / 99%`(切片 0534); `test.quick` 收尾绿, 全量只在 S7 跑。
3. **坑档入口**: 附录 B 每批「依赖坑档」列; 先读 `pitfalls/<类>/_index.md`, 不整目录通读。
4. **边界清单**: S0 底册 C 的 5 个在途计划 + 2 个常驻 issue 锚; 命中重叠文件只标「已在他计划覆盖」, 不重复评审方案。
5. **排重基线**: S0 底册 D 的 18 个 Done 池位 + C-02 并入项 + 11 条观察; 本步新增 3 条(S1 范围/分类问题, 非代码缺陷)不参与代码发现去重。
6. **待 S3 的配对表**: 附录 C 全表(4 组 82 源), 含「含区间改动」标记与共享支撑件清单。
7. **禁止项**: 计划正文未改; S1 的 3 条入池 issue 未认领(保持 Open); 评审阶段不得改代码。

- 2026-11-03 07:23 S1 完成: 479 文件三类打标(实质 294/move-only 185/未变 0), B1-B10 矩阵定稿 0 漏 0 重, R1-R4 配对表, 入池 3 条; 零代码改动

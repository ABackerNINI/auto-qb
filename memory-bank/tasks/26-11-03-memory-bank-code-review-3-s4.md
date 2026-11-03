# 26-11-03-memory-bank-code-review-3-s4 — 全量代码评审 3 · S4（B7 gtm/扩展/scripts + B8 HR/infra/tray）

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** S4 完成 B7 33 件 + B8 8 件评审：4 条发现入池（P1×1/P2×1/P3×2）；test.gtm 1 failed 已入池；扩展安全复核无新增风险
**Topics:** memory-bank-code-review-3-s4
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s1.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s3.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s5.md

## 原始请求

1. 执行第三次 code review 计划的 **S4 步骤**（B7 gtm/扩展/scripts + B8 HR/infra/tray），只做 S4。
2. 必读 plan `26-11-03-0557-plan-full-code-review-3.html`（S4 段、R1–R11）+ S1 task 附录 B 的 B7/B8 清单 + S3 task 交给 S4 的输入清单。
3. 范围 `bf9920d3..812ad785`，B7（33 件）+ B8（8 件）。
4. 工作方式：遇到任何问题（含 P0/P1）一律当场按 create-issue 入池后继续评审，不停下等指示、不单独停下报告；零代码改动。
5. 开工先 `commands run my-commit-flow.sync` 并贴「已同步 <hash>」；只在 clone1 操作。
6. 按 plan 五步评审法逐批过目，全文件勾选不得抽样；维度 R1–R11；每批先读依赖坑档（走类索引）。
7. B7 门槛 `commands run test.gtm` 必须达标；扩展中转面用 TRAE-security-review 复核，只报可证实风险。
8. B8 校验 HR/infra/tray 的进程/托盘/锁/退出路径，不碰真实 qB、不启动真实托盘程序。
9. 每条发现七字段（含三锚与可达性），与全部 Open issue 去重（含 S3 留下的 5 条）；同类连续 >5 条合并。
10. 过程与发现写进本步单独 task 文档；计划只推进 S4 状态，不写流水。
11. 收尾 `kb.wrap`/`kb.index`/`kb.check`，单独提交推送。
12. 回复需含：同步结果、B7/B8 结论与发现数（按 P 级）、test.gtm 数字、新增 issue、task 路径、提交 hash 与推送核验、交给 S5 的输入清单。

## 思考过程与决策

- **区间以 plan 为准**：先按 `bf9920d3..HEAD` 取清单会多出 4 个 HEAD 之后变更的文件（`dev_webui.py`、`manual_e2e_relay.py`、`test_main_run.py`、`test_storage.py`）；改用 `bf9920d3..812ad785` 后恰为 41 件（B7 33 + B8 8），与 S1 附录 B 完全对齐。后续文件核对一律用指定区间。
- **门禁失败不阻断评审**：`test.gtm` 跑出 1 failed（`test_auth_required_on_all_write_endpoints`，WinError 10053）；按用户口径当场入池（`26-11-03-1144-bug-gtm-auth-body-drain`）后继续，单测 3/3 通过确认是间歇性。
- **扩展安全复核**：用 TRAE-security-review 对 3 个变更 JS 做 diff 引入面复核；拆分等价性用「旧文件非 importScripts 行 vs 新三文件行集」机检，仅 3 行语义改动（`poll-now` 增发 `requestBackendRefresh` 并回传 `requested`）。可证实的凭据/消息传递风险：无新增（X-Hr-Token 只发往回环/私网端点，配对码路径未变）。
- **B8 重点**：`_lane_covers_done` 是区间核心行为修复（对应 Open issue `26-10-30-0550` 的 lane 覆盖判据）；`write_journal` 前向合并的拒绝语义已被 guardian 四个写点全部消费（拒写即 stopped），auto-qb 侧三处 ARMED/DONE 写点忽略返回值但同一线程内无并发终态写者，判为不可达，不单独入池。
- **脱敏红线优先**：`--probe-fs` 的 `fs_delta` 未脱敏既有泄漏又致回放失配，按 P1 入池并注明 self-test 假绿。

## 实现计划

1. 开工同步 + 读 plan S4 / S1 附录 B / S3 交接 + 读坑档类索引。
2. B7 批一：gtm 17 件（README/pyproject/__init__/__main__/config/nic/sampler/server/storage + 8 个测试/支撑件）全文件读码。
3. B7 批二：扩展 3 件全文件读码 + 依赖链 `normalize/discovery/site-caps` 只读核验 + 拆分等价机检。
4. B7 批三：scripts 13 件全文件读码；跑 `test.gtm` 门禁。
5. B8：8 件逐变更函数读码 + 读调用方 `finalize_watch.py` / `relocate_exec.py` 核验拒绝语义。
6. 发现七字段登记 + 与 Open issue 去重 + create-issue 入池。
7. 建 task 档落盘 + 推进 plan S4 状态 + `kb.wrap`/`kb.index`/`kb.check` + 单独提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S4.1 | 开工同步与必读/坑档 | Done(2026-11-03) |
| S4.2 | B7 gtm 17 件全文件评审 | Done(2026-11-03) |
| S4.3 | B7 扩展 3 件 + 安全复核 + 拆分等价 | Done(2026-11-03) |
| S4.4 | B7 scripts 13 件 + test.gtm 门禁 | Done(2026-11-03) |
| S4.5 | B8 8 件变更函数评审 | Done(2026-11-03) |
| S4.6 | 发现登记/去重/入池 | Done(2026-11-03) |
| S4.7 | task 落盘 + plan 推进 + 收尾提交 | Done(2026-11-03) |

## 进度日志

### R0 · 立档并完成 S4 评审 (2026-11-03)

- 同步：`commands run my-commit-flow.sync` → `已同步 2f3a3d2e`（无改写 HEAD 的步骤）。
- 范围核对：`bf9920d3..812ad785` 的 41 件与 S1 附录 B 一一对应（B7 33 / B8 8），无漏无重。
- B7 逐文件勾选（17+3+13=33）：gtm（`README.md`/`pyproject.toml`/`__init__`/`__main__`/`config`/`nic`/`sampler`/`server`/`storage` + `conftest`/`server_support`/`test_config`/`test_nic`/`test_sampler`/`test_server`/`test_server_autostart`/`test_server_routes`）；扩展（`background.js`/`background-log.js`/`background-support.js`，另只读 `normalize.js`/`discovery.js`/`site-caps.js` 做安全可达性核验）；scripts（`check_command_drift`/`check_context_caps`/`e2e_selfcheck`/`qb_capture`/`qb_capture_cli`/`qb_capture_core`/`sim_qb`/`sim_qb_cli`/`sim_qb_core`/`sim_qb_model`/`sim_qb_server`/`ui_content_map`/`ui_harness`）。
- B7 拆分等价：`background.js` 旧文件非 importScripts 行 = 1360 行，新三文件缺 3 行（`poll-now` 分支新增 `requestBackendRefresh` + `requested` 回传），其余逐行存在——判为「搬移 + 一处有意增强」。
- 扩展安全复核（TRAE-security-review）：✅ 无可证实且由本次变更引入的凭据/消息传递风险（token/配对码仍只发往 normalize 允许的回环/私网端点）。
- `commands run test.gtm`：**FAIL**（1 failed / 462 passed / 2 skipped，84.6s，coverage 99.33% ≥ 98.5%）；失败点 `tests/test_server.py::test_auth_required_on_all_write_endpoints`，`ConnectionAbortedError WinError 10053`；单测重跑 3/3 通过 ⇒ 间歇性。已入池为 P2 bug。
- B8 逐件读码（8）：`hr/discovery.py`（删未用 import + 日志）、`hr/events.py` / `hr/fetcher.py` / `hr/server.py` / `hr/worker.py`（日志文案）、`hr/service.py`（`_lane_covers_done` 收口三处覆盖判据，修复 Open issue `26-10-30-0550` 的 `cutoff<=0` 误判）、`infra/relocate_journal.py`（`write_journal` 前向合并 + 整包替换）、`tray/app.py`（SIGTERM→quit 注入）。另读 `tools/finalize_watch.py` 的 4 个写点确认拒写=stopped 已接线；`relocate_exec.py` 3 处忽略返回值的写点判为不可达（同线程无并发终态写者）。未启动真实托盘、未触碰真实 qB。
- 发现（七字段已落 issue）：
  - P1 `26-11-03-1144-bug-qb-capture-fs-delta-sanitize`：`fs_delta` 未脱敏（真 hash/相对路径漏入 `sync-stream`，回放端伪 hash 查不到而静默丢增量，self-test 假绿）。
  - P2 `26-11-03-1144-bug-gtm-auth-body-drain`：401 短路未读请求体 → Windows 客户端连接重置而非 401。
  - P3 `26-11-03-1145-bug-sim-qb-export-bencode`：`torrents/export` announce 长度 26 vs 实际 25，bencode 非法。
  - P3 `26-11-03-1145-refactor-qb-capture-cli-dead-main`：`qb_capture_cli.py` 残留重复 `main()` 且引用未定义 `Capture`。
- 去重：以上 4 条与现有 Open issue 无重复；S3 遗留 5 条（group 窗口化 / 嵌套退役键 / `.ce-page` / 归一 parity / e2e `BASE_URL`）均不涉及 B7/B8，未撞车。B7/B8 无「同类连续 >5」合并项。
- 只读边界：全程零代码改动、无 commit 以外动作；未跨 clone。
- tests-real 清单：`commands run real.list` 只读核对，共 104 条、覆盖 `rm00_infra`–`rm10_notify` 11 个文件；未跑真机、未触碰真实 qB/生产配置。

## 交给 S5 的输入清单

1. **B7/B8 已完成，无遗留评审项**；S5 只需按原计划做 B9（测试缺口）与 B10（文档漂移），不要重复 B7/B8 的逐文件结论。
2. **门禁状态**：`test.gtm` 当前 **未达标**（1 failed / 462 passed / 2 skipped，coverage 99.33%）。根因已入池 `memory-bank/issues/26-11-03-1144-bug-gtm-auth-body-drain.html`；S5 在修复落地后需复跑 `commands run test.gtm` 并以其数字更新基线切片。
3. **新增 issue（4 条，均 Open，topic `code-review-3-s4`）**：
   - `26-11-03-1144-bug-qb-capture-fs-delta-sanitize`（P1）— B9 做测试缺口时注意：`self_test` 的流级一致性判据缺 `fs_delta` 覆盖，属本条的一部分，勿另立重复条目。
   - `26-11-03-1144-bug-gtm-auth-body-drain`（P2）
   - `26-11-03-1145-bug-sim-qb-export-bencode`（P3）
   - `26-11-03-1145-refactor-qb-capture-cli-dead-main`（P3）
4. **B8 已修但未标 Done 的既有 issue**：`26-10-30-0550`（lane 覆盖判据）在本区间由 `_lane_covers_done` 统一收口，S6 复验可达性时应重点确认 `cutoff_done<=0` / `done<=0` 两个边界的回归，再决定是否置 Done（S4 不擅自改状态）。
5. **扩展安全复核结论**：本次变更无新增可证实风险；B10 的 docs-sync-audit 可引用此结论，无需再对 3 个 JS 做安全复审。
6. **已知不属 B7/B8 的 S3 遗留 5 条**（group 窗口化 / 嵌套退役键 / `.ce-page` / 归一 parity / e2e `BASE_URL`）仍然 Open，S5/S6 不要把它们并入本轮 B7/B8 发现表。

- 2026-11-03 11:50 S4 完成 B7 33 件 + B8 8 件逐文件评审；test.gtm 1 failed 已入池；4 条发现入池（P1×1/P2×1/P3×2）；扩展安全复核无新增可证实风险

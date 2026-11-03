# 26-11-03-memory-bank-code-review-3-s5 — 全量代码评审 3 · S5（B9 tests/tests-real + B10 文档漂移）

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** S5 完成 B9（245 件测试 + 40 件 tests-real 静态审计）与 B10（文档漂移系统审计）：6 条发现入池（test×2 / docs×4），拆分等价 0 丢失 0 重复，无 P0/P1
**Topics:** memory-bank-code-review-3-s5
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s1.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s3.md, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s4.md

## 原始请求

1. 执行第三次 code review 计划的 **S5 步骤**（B9 tests + tests-real + B10 文档漂移），只做 S5。
2. 必读 plan `26-11-03-0557-plan-full-code-review-3.html`（S5 段）+ S1 task 附录 B 的 B9/B10 + S3 task + S4 task（交给 S5 的输入清单）。
3. 范围 `bf9920d3..812ad785`：B9 = 245 个变更测试 + 40 个 tests-real，另含 `812ad785` 时 286 个 tests 文件的审计面（35 个区间未变不计入 479）；B10 = 文档漂移系统审计（只读，代码面批次数 0）。
4. 工作方式：任何问题（含 P0/P1）当场按 create-issue 入池后继续，不停下等指示；仍只做 code review / 审计，零代码改动。
5. 开工先 `commands run my-commit-flow.sync` 并贴结果行；只在 clone1 操作。
6. B9 用 `test-gap-audit` 口径做覆盖缺口 + 拆分等价审计，不逐文件深读 286 个测试；重点：区间新增测试是否守住实现、弱断言/自证/跳过、R1–R4 拆分有无丢失或重复、tests-real 40 件仅静态评审（不跑真机）。
7. 与变异测试已入池项去重；`fs_delta` self-test 覆盖缺口属 S4 那条 issue，勿另立。
8. B10 用 `docs-sync-audit` 做系统漂移审计（只读）：代码事实 vs `memory-bank/` vs 根 README，按「代码 > memory-bank > README > 想法.md」裁决，只报可证实漂移。
9. 每条发现七字段（含三锚与可达性），与全部 Open issue 去重；同类连续 >5 条合并并注明覆盖数。
10. 过程与发现写进本步单独 task 文档；计划只推进 S5 状态，不写流水。
11. 收尾 `kb.wrap`/`kb.index`/`kb.check`，然后单独提交推送（`COMMIT_MSG_AI.txt` + `ship.commit` + `ship.push`）。
12. 回复：同步结果、B9 缺口要点（覆盖缺口/等价性/弱断言各多少）、B10 漂移要点、新增 issue、task 路径、提交 hash 与推送核验、交给 S6 的输入清单。

## 思考过程与决策

- **区间口径对齐**：`git diff --name-status -M50% bf9920d3..812ad785 -- tests/ tests-real/` 共 291 件；其中 tests/ 251 件（A168 / M51 / R12 / D20）。S1 附录 B 的 B9=285 = 245 测试 + 40 tests-real：245 已剔除归 B1 的 6 件 transfer 测试（`test_transfer_adapters.py` 等），另含 1 件 `tests/fixtures/config_key_surface.txt` 夹具。`812ad785` 时 tests/ 286 件 + tests-real/ 40 件 = 326 件静态审计面。
- **不逐文件深读**：B9 采用机检 + 抽样：①AST 断言强度扫描（区间变更测试 3812 个 `test_*` 函数）；②按拆分提交的父树做「整提交测试函数多重集等价」；③覆盖率映射脚本产出线索后只对 15 个区间变更源文件逐一复核；④tests-real 读守卫/运行器/基座 6 件 + rm00 自检 + 源级静态安全守卫。
- **拆分等价按整提交而非按前缀配对**：S1 附录 C 的“共享支撑件/未按前缀配对的目标”使单文件配对会误报（首轮机检出现大量假缺失）；改按 `a48ead5c`/`63f47598`/`60ee0bec`/`20a74274` 四个提交的「父树全部源 vs 提交全部目标」比对，结论才可证。
- **零断言不等于弱断言**：76 个零 Assert 节点用例里 53 个是 `pytest.raises`（负路径契约），22 个是已写明“不抛/空转”语义的 smoke 或经 mock API（`assert_called_once_with` 等语句非 Assert 节点）断言；仅 1 个用例名声称转发却无任何断言，判为真弱断言。另有 17 个“仅 mock 断言”与 1 个“单 mock 断言”属委托性验证，不判弱。
- **tests-real 只做静态评审**：未跑真机、未触碰真实 qB。守卫三层（白名单/端口→进程镜像→种子活动）、`rm00` 自检、`tests/test_real_machine_safety.py` 源级禁写扫描与 `tests/test_port_zero_guards.py` 重绑自检共同构成闭环，未发现安全缺口；`lib/runner.py` 的 CLI 门禁仅由真实运行间接覆盖，作为残余风险写入交接，不单独立项。
- **B10 裁决顺序**：以代码/`uv.lock`/配置模型为事实源，memory-bank 为一致性参照，README 为用户面；仅报“可证实”的版本/路径/数字矛盾，历史 task/plan 里的旧路径不算漂移（不报）。

## 实现计划

1. 开工同步 + 读 plan S5 / S1 附录 B / S3 / S4 交接 + 读坑档类索引。
2. B9 机检：区间清单、AST 断言强度、跳过标记、覆盖率映射线索。
3. B9 拆分等价：四个拆分提交的整提交测试函数多重集比对 + 全局区间等价（含 2 个退役键用例的替代覆盖核验）。
4. B9 tests-real：守卫/环境注册/运行器/实例基座静态读码 + rm00 自检与源级安全守卫核对（不跑真机）。
5. B10：`doc.drift`/`doc.links` + 锁定版本/路径/README 数字/配置参考/代码注释逐面裁决。
6. 发现七字段登记 + 与 Open issue 去重 + create-issue 入池（6 条）。
7. task 落盘 + 推进 plan S5 状态 + `kb.wrap`/`kb.index`/`kb.check` + 单独提交推送。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S5.1 | 同步 + 读 plan/S1/S3/S4 + 坑档 | Done(2026-11-03) |
| S5.2 | B9 机检（清单/断言强度/跳过/覆盖率线索） | Done(2026-11-03) |
| S5.3 | B9 拆分等价（R1–R4 + 全局） | Done(2026-11-03) |
| S5.4 | B9 tests-real 静态评审 | Done(2026-11-03) |
| S5.5 | B10 文档漂移系统审计 | Done(2026-11-03) |
| S5.6 | 发现登记/去重/入池 | Done(2026-11-03) |
| S5.7 | task 落盘 + plan 推进 + 收尾提交 | Done(2026-11-03) |

## 进度日志

### R0 · 立档并完成 S5 (2026-11-03)

- **同步**：`commands run my-commit-flow.sync` → 已同步 `90e86b16`；工作树干净，仅 clone1。
- **B9 审计面**：`812ad785` 时 tests/ 286 件（含非 py 夹具）+ tests-real/ 40 件；区间变更 291 件（tests 251 + tests-real 40），其中 B9 承 245 测试 + 40 tests-real。变更测试内共 **3812 个 `test_*` 函数**。
- **B9 覆盖缺口 = 1**：
  - `.agents/skills/deps-upgrade/scripts/check_updates.py` 全仓无测试引用（grep 仅 SKILL.md / `project/deps.toml` / `.codebuddy/` 镜像）。版本段切分（`:73`）、增量分类（`:96`）、部分源失败容错（`:128`）无回归网 → 入池 P2 test。
  - 覆盖率映射产出 375 源 / 383 测试、209 条启发式未匹配线索；过滤到区间变更源文件 15 条，14 条经 grep 确认有直接/间接测试（transfer adapters、hr events、rules actions、tray、traffic_source agent、webui routes 等），仅上述 1 条为真缺口。
- **B9 等价性 = 0 丢失 / 0 重复**：按整提交多重集比对，四个拆分提交的测试函数全部相等——R1 `a48ead5c` 10→48 件 / 907 函数；R2 `63f47598` 25→112 件 / 1503 函数；R3 `60ee0bec` 5→5 / 79；R4 `20a74274` 26→26 / 314；`missing=0 extra=0`（R3/R4 各多 2/3 个非测试 helper def，无测试增减）。全局 `bf9920d3` 3778 → `812ad785` 4591 个测试函数，缺 2：`test_rule_ignore_next_action_error` / `test_rule_action_chain_ignore_continue`，均为退役 `ignore_next_action_error` 语义，替换覆盖已在 `test_rule_base_rule.py:182/:428` 与 `test_actions_on_error.py:133`，判为有序退场而非丢失。
- **B9 弱断言 = 1（候选 76 分类后）**：零 Assert 用例 76 → 53 个 `pytest.raises`、22 个写明 no-exception/空转契约或用 mock API 断言、1 个真弱（`tests/test_hr_runtime_feeder.py:277-285` 用例名声称转发 `worker.wake()` 却无断言）→ 入池 P3 test。另 17 个仅 mock 断言 + 1 个单 mock 断言属委托验证，不判弱。
- **B9 跳过**：tests/ 共 20 个标记（`skipif` 11 / `skip` 9），**0 xfail / 0 importorskip 静默**；tests-real 26 处 skip 均为环境守卫不可用时的显式跳过。
- **B9 tests-real 静态评审（未跑真机）**：`real.list` 104 条覆盖 rm00–rm10 共 11 文件；守卫 `guard.py` 三层（端口白名单→进程镜像前缀→种子活动窗口）+ `env_registry` 双环境 + `runner.py` 默认 dry-run/`--yes` 门禁；`rm00_infra` 自检白名单/在线/不暂停，`tests/test_real_machine_safety.py` 源级禁写（卷访问/危险命令），`tests/test_port_zero_guards.py` 重绑自检。无安全缺口；残余风险仅 `lib/runner.py` CLI 门禁依赖真实运行间接覆盖。
- **B10 机械门**：`commands run doc.drift` → 0 漂移；`commands run doc.links` → 通过（0 失效相对链接）。
- **B10 可证实漂移 = 4（无 P0/P1）**：
  1. P2 `docs/context7/README.md`：声称文件名含 `pyproject.toml` 精确版本，实际 5/10 与 `uv.lock` 不符（qbittorrent-api 2026.8.1→2026.10.1、fastapi 0.141.1→0.162.0、uvicorn 0.53.0→0.54.0、pillow 12.3.0→13.0.0、filelock 3.32.6→4.2.5）；`:11` 的 `src/auto_qb/qbclient.py` 已迁至 `core/qbclient.py`，`:12` 的 `web_commands.py` 已迁至 `webui/server/`。
  2. P2 `README.md:247` 仍写“约 2300+ / 2312 / 2309 passed + 3 skipped”，最新基线 `26-11-03-1112` 为 **4971 passed + 2 skipped**；同时违反“测试基线数字只写一处”。
  3. P2 `docs/configuration.md` web 段（`:59` 起）无 `web.transfer` 子键说明；`memory-bank/config-reference/keys.md:23` 已有全量键（targets/enabled/fields/after_state/skip_check/path_map/api_key）。
  4. P3 `tests-real/lib/env_registry.py:27-28` 注释称“环境2 尚未实测, 留空”，实际 `:57-60` 已于 2026-11-01 回填 bt_listen。
- **发现（七字段已落 issue，均为 Open，topic `code-review-3`）**：
  - P2 test `26-11-03-1209-test-test-deps-upgrade-check-updates-uncovered`：现象=巡检脚本零测试；三锚=脚本 `:73/:96/:128` + SKILL.md 调用 + 日常巡检可达；影响=版本误判误导升级决策；建议=参数化单测（CalVer/rc/非数字段/单源失败）。
  - P3 test `26-11-03-1209-test-test-hr-runtime-feeder-wake-forward-unasserted`：现象=转发无断言；三锚=`test_hr_runtime_feeder.py:277-285` + `hr/runtime.py` `def wake` + 全量每日运行；可达=wake 丢转发仍绿（假绿）；建议=断言 worker 替身被调用。
  - P2 docs `26-11-03-1208-docs-docs-context7-version-path-drift`：现象=5/10 版本 + 2 路径漂移；三锚=`docs/context7/README.md:4/:11/:12` + `uv.lock` + `core/qbclient.py`/`webui/server/`；可达=查阅 API 速查即被误导；建议=重新抓取并重建索引。
  - P2 docs `26-11-03-1208-docs-docs-readme-test-scale-drift`：现象=README 旧规模数字；三锚=`README.md:247` + 基线切片 `26-11-03-1112` + `kb.baseline`；可达=贡献者误判测试规模；建议=改引用基线命令。
  - P2 docs `26-11-03-1208-docs-docs-configuration-transfer-missing`：现象=用户配置参考缺 transfer 段；三锚=`docs/configuration.md:59` 零命中 + `keys.md:23` + `config/models.py` TransferConfig；可达=用户无法从 docs 配转移；建议=补子表。
  - P3 docs `26-11-03-1209-docs-docs-tests-real-env2-comment-drift`：现象=注释与配置矛盾；三锚=`env_registry.py:27-28` + `:57-60`；可达=误判环境2 黑名单为空；建议=改注释。
- **去重**：6 条与全部 Open issue 无重复；`fs_delta` self-test 缺口属 S4 `26-11-03-1144-bug-qb-capture-fs-delta-sanitize`，未另立；变异测试既有提名未重复（`check_updates` 不在其 src/ 范围）；端口文档/ qB 5.3 文档口径已有 Open issue，未重复。test 类 2 条、docs 类 4 条，均低于“同类连续 >5 合并”阈值。
- **只读边界**：零代码改动；未跨 clone；未跑真机、未启动托盘、未触碰真实 qB/生产配置。

### 交给 S6 的输入清单

1. **B9/B10 已完成，无遗留评审项**；S6 不需重复测试缺口与文档漂移审计。
2. **新增 issue（6 条，均 Open）**：P2 test `26-11-03-1209-test-test-deps-upgrade-check-updates-uncovered`、P3 test `26-11-03-1209-test-test-hr-runtime-feeder-wake-forward-unasserted`、P2/P2/P2 docs `26-11-03-1208-docs-docs-context7-version-path-drift` / `...readme-test-scale-drift` / `...configuration-transfer-missing`、P3 docs `26-11-03-1209-docs-docs-tests-real-env2-comment-drift`。
3. **等价性证据**：R1–R4 拆分测试函数 0 丢失 0 重复；全局仅 2 个退役键用例移除且有替代；S6 无需再做拆分等价复核。
4. **门禁状态**：`test.gtm` 仍受 S4 已入池的 401 请求体问题影响（未在本步复跑）；`doc.drift`/`doc.links` 本步均通过。
5. **残余风险**：`tests-real/lib/runner.py` CLI 门禁仅由真实运行间接覆盖（未立项）；context7 快照未重建（本步只读，风险已在 issue 记录）；memory-bank 历史 plan/task 中旧路径属历史记录，不视为漂移。
6. **既有 Open 项提醒**：S4 的 `26-11-03-1144-bug-qb-capture-fs-delta-sanitize`（P1）仍 Open；B9 已知 `fs_delta` 自测缺口属其范围，S6 勿重复提名。

- 2026-11-03 12:13 S5 完成 B9 245+40 件与 B10 系统漂移审计；6 条发现入池（test×2/docs×4）；拆分等价 0 丢失 0 重复；无 P0/P1

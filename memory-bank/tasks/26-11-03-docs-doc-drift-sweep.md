# 26-11-03-docs-doc-drift-sweep — 文档漂移 7 条批量修复（评审计划 0557 + 端口口径）

**Status:** In Progress
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 文档漂移 7 条批量修复（评审计划 0557 + 端口口径）
**Topics:** docs-doc-drift-sweep
**Refs:** memory-bank/issues/26-11-03-0704-docs-plan-domain-table-count.html, memory-bank/issues/26-11-03-0704-docs-split-residue-rename.html, memory-bank/issues/26-11-03-0647-docs-plan-review3-legacy-html-refchain.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-baseline-anchor-stale.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-inflight-list-stale.html, memory-bank/issues/26-11-03-0630-docs-plan-review3-ledger-counts-drift.html, memory-bank/issues/26-11-03-0316-docs-port-doc-drift.html

## 原始请求

1. 依次认领并修复 7 条文档漂移 issue（同一文档面、串行、每件独立留痕）：
   `26-11-03-0704-docs-plan-domain-table-count` / `26-11-03-0704-docs-split-residue-rename` /
   `26-11-03-0647-docs-plan-review3-legacy-html-refchain` / `26-11-03-0630-docs-plan-review3-baseline-anchor-stale` /
   `26-11-03-0630-docs-plan-review3-inflight-list-stale` / `26-11-03-0630-docs-plan-review3-ledger-counts-drift` /
   `26-11-03-0316-docs-port-doc-drift`。
2. 开工先 `my-commit-flow.sync`；按 `memory-bank/README.md` 细路由与 `pitfalls/_index.md`（docs 类）读文档；逐件认领（issue doc-refs ↔ 档案 Refs 双向）。
3. 漂移裁决按 代码 > `memory-bank/` > 根 `README.md` > `想法.md`；每件先用命令/实测核对当前真值（计数/端口/锚点/清单/引用链），issue 可能过期；代码若错按范围守恒入池新 issue。
4. 计划文档单文件 HTML + dark 主题；测试数字只进 `testing/baselines/` 新切片；跑 `doc.caps`；改引用后 `kb.index`，`kb.check` 全绿。
5. 收尾 DoD：`kb.wrap --topic <slug> --did ".."`、状态与结论回写、新建基线切片、`ship.commit`（gitmoji+中文）；只操作当前 clone，`config.yml`/`auto-qb-data/` 为红线。

## 思考过程与决策

以代码/实测为事实源逐条复验，不照抄 issue 描述；7 件结论：

- **域表计数（已漂移）**：`git diff --name-status -M50% bf9920d3..812ad785 -- src/ tests/ tests-real/ tools/global-traffic-monitor/ extensions/ scripts/` 实测 479 件；计划 §02 域表行合计 478，缺 `src/auto_qb/tools/finalize_watch.py`（+22/−9）。补一行后合计 479。
- **split 残片（已自愈）**：区间 12 条改名前缀 `R05x–R07x` 为拆分残片；S1 档案附录 C 已于 07:23 按组列示并要求与共享支撑件同读，计划无 1:1 配对断言。无需再改。
- **旧 HTML 引用链（已漂移）**：按 issue 恢复计划 0557 ↔ 0221 计划 / 1036 报告的双向 `doc-refs`（人工补元数据行，避开 `kb.ref` 对 plans/reports 目标的限制）；同时清理两件旧 HTML 的 9 条 v.Nu error（0221 尖括号转义；1036 span 未闭合、`<dummy>`/`<=` 转义、h3→h2），使增量闸门放行；`kb.check` 认领链已双向闭环。
- **基线锚（已漂移）**：计划定稿时最新切片是 `26-11-03-0534`（非 0459）；按「测试数字只进基线切片」口径，正文改为引用切片、不手抄数字；§04 S7 验收改引用 S7 收尾切片 `26-11-03-1245`。
- **在途清单（已漂移）**：终验复验 `plans/` 非 Done 仅 2318 / 2001 / 1119（In Progress）与 1758（Open）；2342 / 0306 / 0106 已 Done；0641 / 0642 / 0711 是 `issues/` 常驻锚，不属 `plans/`。
- **底册数字（已漂移）**：按 S0 实测 54 Open / 2 In Progress / 359 Done / 3 Superseded / 6 Dropped（合计 424，Open 类型 test 5）；计划定稿时 52（0559 两条 e2e 既有红于定稿后入池）；二次评审池位 18 非 17。
- **端口口径（已漂移）**：代码 `_try_port`（`qbittorrent.port`/`web.port` 1-65535）与 `_try_port_or_zero`（`hr.channel.port`/`discovery_port` 0-65535）不同；`minimal.yml` 的 16585 是生产值，改示例 8080；`docs/sim-client-test-howto.md` 同步去掉 16585。

未发现「代码才是错的」项，无需入池新 issue。

## 实现计划

串行处理：每件 = 实测复验 → 判定（已漂移/已自愈）→ 最小改动 → 对应守卫复跑。7 件改完后统一 `kb.index` / `doc.caps` / `doc.drift` / `kb.check`，再跑 `test.full` 建基线切片，最后 `ship.commit`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 域表补 `src/auto_qb/tools/` 1 件（+22/−9），合计 479 | Done(2026-11-03) |
| 2 | split 残片按组口径复验（S1 已列示） | Done(2026-11-03) |
| 3 | 恢复 0557↔0221/1036 双向 refs；旧 HTML 9 条 v.Nu error 清理 | Done(2026-11-03) |
| 4 | 基线锚改引用 0534 / S7 切片 1245，去手抄数字 | Done(2026-11-03) |
| 5 | 在途清单按终验复验更新（4 件非 Done + 3 件 Done + issue 锚） | Done(2026-11-03) |
| 6 | 底册 54/2/359/3/6（合计 424）、18 池位回写 | Done(2026-11-03) |
| 7 | 端口三处文档按代码口径修正 | Done(2026-11-03) |
| 8 | `kb.index` + `doc.caps`/`doc.drift`/`kb.check` 全绿 | Done(2026-11-03) |
| 9 | `test.full` 实测并新建基线切片 | Done(2026-11-03) |
| 10 | `ship.commit` 提交推送 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

开工 `my-commit-flow.sync` 快进 `6133e941→f906f84c`（远端领先 28 笔）。7 条 issue 逐条实测后落盘：计划 0557 改域表/基线引用/在途清单/底册数字/池位数；`minimal.yml` 与 `config-reference/loading-and-write.md`、`docs/sim-client-test-howto.md` 改端口口径；0221 计划与 1036 报告清理 9 条 v.Nu error；split 残片确认 S1 已按组列示，无需改。全部 issue 状态回写 Done 并留实测结论。

- 2026-11-03 21:53 7 条文档漂移 issue 全部认领并处置: 0557 计划域表补 src/auto_qb/tools 行(合计 479)、基线改引 0534/S7 切片 1245、在途清单按终验复验更新、底册按 S0 实测 54/2/359/3/6(合计 424, test 5)与 18 池位回写; 0221/1036 清理 9 条 v.Nu error 并恢复与 0557 双向 doc-refs; minimal.yml 16585→8080, config-reference 与 sim 文档端口口径修正; 全量 test.full 零源码改动 4994 passed + 10 skipped, 新建基线切片 26-11-03-2146。

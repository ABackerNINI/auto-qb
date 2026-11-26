# RM04-38 真机脚本自动断言全通过：启动自愈清 3 留 2 + WebUI 换代 stale_rows=0 —— 外部旧路径通知账启动自愈计划 26-11-24-2204 的 S4 真机验收切片

> 摘要: 环境2(C盘机) 测试 qB 副实例 56589/56590，`real.env` 确认、`real.guard` 通过（双实例 v5.2.3、firewalled、0 真实种子、0 real-fake 残留）；`real.up --port 56589` / `--port 56590` 拉起，`real.run --case RM04-38 --yes` → PASS（1 passed in 10.13s），`real.down` 经 WebAPI 优雅退出两实例（无 taskkill）。用例停机注入 2 条 job（终态 rm04c38done + 活跃 rm04c38active）+ 5 条 foreign.notified 账 + 5 枚 real-fake 假种子，重启后**清 3 留 2**：孤儿 A / 终态 A / mismatch 三条陈旧账被清，B（rm04c38done）与活跃 A（rm04c38active）保留且字段无漂移；WebUI 只读视图换代 stale_rows=0，B 行呈现 `[foreign, B, rm04c38done]`。cleanup 证据 stop_rc=1 系进程内 SIGTERM 优雅停止返回码、用例未设断言，如实注明为非失败项。本批真机用例已在阶段 5a 评审零 blocker。
> 基线时间: 2026-11-27 03:25
> 基线 commit: c68d7c24b0ad8cb4b5901d0463289a4513c9e7ca（本地分支 feat/relocate-foreign-startup-cleanup，无远端；执行时工作树干净）

**Refs:** memory-bank/tasks/26-11-24-backend-relocate-foreign-notified-cleanup.md

## 01 环境指纹与执行口径

- **环境**: 环境2 / C盘机；测试 qB 副实例 56589 与 56590，由 `commands run real.env` 确认；`commands run real.guard` 在起实例后通过（双实例 v5.2.3、firewalled、0 真实种子、0 real-fake 残留）。
- **拉起**: `commands run real.up -- --port 56589` 与 `commands run real.up -- --port 56590` 分别拉起两实例；不读仓库根 `config.yml`，不碰生产实例。
- **执行**: `commands run real.run -- --case RM04-38 --yes` → PASS，`1 passed in 10.13s`；用例位于 `tests/real/rm04_relocate/test_rm04_foreign_startup_selfheal.py`。
- **收尾态**: `commands run real.down` 经 WebAPI app/shutdown 优雅退出两实例（无 taskkill）；执行时 HEAD = c68d7c24（本地分支，无远端），工作树干净，全程未动 `src/` 与 `tests/`（真机已 PASS，用例无需改）。
- **判据来源**: 计划 26-11-24-2204 §04 S4（全量测试 + 真机）+ `testing/real-machine.md` §08 用例成熟度；本轮 RM04-38 脚本自动逐键断言，按 §08 从 L0/L1 升到 L2。

## 02 逐条判据结果

### ① 启动自愈清 3 留 2 —— PASS

- **停机注入**: 2 条 job（`rm04c38done` 终态、`rm04c38active` 活跃）+ 5 条 `foreign.notified` 账 + 5 枚 real-fake 假种子（orphan_a / terminal_a / mismatch_gone / b / active_a）。
- **清 3**: 孤儿 A（job 不在）、终态 A（job 已终态）、mismatch（job 已不在）三条陈旧账被清，`ledger.cleared = 3`。
- **留 2**: B（`rm04c38done`）与活跃 A（`rm04c38active`）保留且字段无漂移，`ledger.kept = [["b","B","rm04c38done"],["active_a","A","rm04c38active"]]`。
- **机器判**: 上述 cleared / kept 键值由用例内逐键断言，非人判读。

### ② WebUI 只读视图换代 —— PASS

- 换代后 `web_view.stale_rows = 0`（无陈旧行留存）。
- B 行呈现 `["foreign","B","rm04c38done"]`，即 `[foreign, B, rm04c38done]`。
- 与 D9 口径一致：换代走写面的建键风险已由「只读视图先判账已在、仅账已在才换代」收窄；本轮换代未 materialize 多余账键。

## 03 证据文件（gitignored，保留不删）

`tests/real/.work/rm04/foreign/`：

- `rm04_38_ledger_evidence_20261127_032322.json` —— 停机注入快照（2 job + 5 账 + 5 假种子）。
- `rm04_38_final_evidence_20261127_032322.json` —— 清 3 留 2 + WebUI 换代（stale_rows=0、B 行）。
- `rm04_38_cleanup_evidence_20261127_032322.json` —— 同最终态 + `seeds_removed`（5 枚）+ `stop_rc=1`。

三份证据 `ts` 均为 `2026-11-27 03:23:22`。

## 04 收尾与合规

- **无 taskkill**: `real.down` 经 WebAPI app/shutdown 优雅退出两实例；cleanup 证据 `stop_rc=1` 是进程内 SIGTERM 优雅停止返回码，用例未设断言、不影响 PASS，如实注明为**非失败项**。
- **不碰生产**: 只在白名单测试实例 56589/56590 起进程，未改生产 `config.yml`、`auto-qb-data/` 或 `state.json`；5 枚 real-fake 种子随 `.work` 留存（gitignored）。
- **代码零改**: 执行时工作树干净、HEAD c68d7c24；真机已 PASS，未改任何 `src/` 或 `tests/` 代码。
- **评审留痕**: 本批真机用例已在阶段 5a 评审零 blocker。

## 05 升档口径（real-machine.md §08）

- 档位表：L0 人工目视 / L1 脚本采集+人判读 / **L2 脚本自动断言** / L3 L2+负向对照。
- 本轮 RM04-38 为脚本自动逐键断言（cleared / kept / web_view 由用例内 `assert` 机器判），按 §08「每轮至少 1 条升一档」从 L0/L1 升到 **L2**。
- 未达 L3：本轮未加负向对照（故意造错必须红），不冒充 L3。

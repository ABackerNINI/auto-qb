# 2676 —— memory-bank 三项 cap 债务清理轮 (切片 92→68 · issues 索引截断 · 第三项系口径误报)

> 摘要: 清理会话收口用户报的三项债务 —— ①`activeContext/` 切片 **92 → 68**(删 24 片: 无入链 + 无开放决策 + 内容已被档案/报告/坑档覆盖)
> ②`issues/_index.md` **25,598 → 23,170**(`gen_issues_index.SUMMARY_MAX` 40 → 24, 仍走渲染口径不上外迁)
> ③`pitfalls/web-ui/layout-css.md` **系口径误报**(报的 17.6KB 是**字节**, cap 口径是**字符**; 实测 9,717 < 12,000)⇒ 一行未改。
> **本轮零 `src/` 零 `tests/` 改动**, 数字与上一条 [26-10-06-1022](26-10-06-1022-webui-column-alignment-plan.md) 逐位持平。
> 基线时间: 2026-10-06 10:53

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

- 分支: develop @ **e0601315**(开工 `my-commit-flow.sync` 后; 工作树含本轮改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 单次采样 **42.37s**(wall 43.8s; 修索引前一跑 45.50s) ⇒ 区间约 **42~46s**。
- 相对上一条基线 [26-10-06-1022](26-10-06-1022-webui-column-alignment-plan.md)
  (2676 + 4 / 16021 / 163 / 5472 / 143): **逐位持平**(passed ±0 / 语句 ±0 / 未覆盖 ±0 / 分支 ±0 / partial ±0)
  —— 与「知识库维护轮, 零 `src/` 零 `tests/` 改动」预期一致; 该 +0 是**预期**而非漏测(改动面不进 `--cov=src`
  统计, 也不在 `testpaths(tests/)` 里)。
- 守卫: `commands run doc.caps` **债务 0 项** / `kb.check` 绿(459 文档 · 250 专题, 主键纪律 + 认领链 OK) /
  `doc.links` 绿 / `kb.active --check` 绿(切片计数 92 > 70 的债务已清) / `tests/test_memory_bank.py` **32 passed**。
- 改动面(全部为知识库维护, 无 `src/` 与 `tests/` 改动):
  - `memory-bank/activeContext/` —— **删 24 片**: full-code-review 族 13(S0-S1 + 批 A/B1/B2/C/D/E/F1/F2/G/H + S5/S6)
    + 实施/取证完结片 11(`test-throttle-timing-flaky` · `settings-help-rewrite` · `open-path-foreground-round2` ·
    `backend-issues-clearance` · `ops-recheck-false-success` · `hr-fetch-verify-forensics` · `webui-danger-guards` ·
    `hr-steady-throttle-impl` · `backend-reannounce-confirm` · `reannounce-confirm-rework-impl` · `webui-qb-traffic-drawer-page-guard`)。
    判据 = ①无入链(逐片 `git grep` 精确文件名核外部引用, 删前复检 0 处命中) 且 ②非开放决策片 且 ③内容已被
    `tasks/` 档案 · `reports/` 报告 · 坑档 · `progress/` 覆盖; **未抬 `SLICE_COUNT_LIMIT`、未删活跃片**。
  - `.agents/skills/create-issue/scripts/gen_issues_index.py` —— `SUMMARY_MAX` 40 → 24 + 判据注释(无摘要口径 18,744 < cap ⇒ 仍属摘要顶爆)。
  - `memory-bank/pitfalls/kb/cap-counting.md` —— 新条目「量 cap 的第三种形态: 拿「KB / 字节」去比「字符数」的 cap」+ 头部摘要/触发词同步。
  - `memory-bank/activeContext/26-10-05-0555-hr-steady-throttle-plan.md` —— 指向被删实施片的断链改指任务档案。
  - `memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md` —— 本轮清理记录(cap 治理线单点)。
  - 生成物 `_index.md` 族(20 个重建; 另含四处 `pitfalls/*/_index.md` 头部元数据同步)。
- **已入库**: `4236975c`(与修 check_kb_structure 债务计数口径的 `26-10-06-1102` 同笔)。

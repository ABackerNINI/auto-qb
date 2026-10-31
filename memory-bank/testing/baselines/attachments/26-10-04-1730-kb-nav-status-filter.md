# 基线切片 26-10-04-1730 — kb.nav 台账: 状态筛选器不再被轮询重播种 + 状态列移到标题左侧 (+2 条守阵)

> 摘要: 用户报「kb.nav 台账的**状态**筛选器每隔一段时间自动重置, 形态 / issue 类型筛选器正常」——
> 根因是 `derive()` 每轮数据都把数据里存在的状态值无条件 `add` 回 `S.aStatuses` / `S.cStatuses`
> (本意是"新状态自动入选"), 而形态/类型的候选是定长常量数组、不进这条派生, 所以只有状态中招;
> 30s 轮询一轮一盖 = 用户感知的"自动重置"。修法 = 加自动入选记账 `statusSeeded`(每个候选值只
> 自动补一次)。同时按用户定调把台账**状态列从标题右侧(第 6 列)移到形态右侧、标题左侧**, 表头与
> 行模板同步改。守阵 +2(列序双头绑定 / 状态只自动入选一次)。

> 基线时间: 2026-10-04 17:41
> 档案: memory-bank/activeContext/26-10-04-0952-kb-nav-page.md (第三跟进轮)

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md · memory-bank/pitfalls/web-ui/poll-reseed-filter.md

- 分支: develop @ bc23748b (+ 本轮未提交改动: .agents/skills/memory-bank/scripts/nav_page.html /
  tests/test_kb_nav.py / 本切片 / activeContext 切片 / pitfalls/web-ui/poll-reseed-filter.md)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2510 passed + 4 skipped, 34.90s (引擎计 36.3s), 覆盖率 TOTAL 99%**
  (14821 语句 / 152 未覆盖 / 4964 分支 / 112 partial; 门槛 98% 达标)
- 相对上基线 (26-10-04-1606: 2508 passed + 4 skipped / 99% / 29.61s): passed **+2, 全部可归因**
  —— 本文件新增 2 条守阵(test_ledger_status_column_between_form_and_title /
  test_status_filter_not_reseeded_every_poll)。语句数 +144 来自开工同步合入的
  bc23748b(qB 流量图取证报告轮), 与本轮无关。skip 集合不变(Windows 侧 4 条 POSIX 专属)。
- 运行时验证: Node 回放(页面脚本套最小 DOM 桩, 依次 `applyData` → `toggleSet(S.aStatuses,"Done")`
  → 再 `applyData` 模拟轮询)—— 取消的 Done **未被回填**、数据里新冒出的候选仍自动入选、形态/类型
  不受影响、行模板里 statc 先于 title-cell。另 `node --check` 过 shell 内联脚本(语法口径)。
- 静态导出 / 服务: 本轮未重跑 `--gen-static`(未改服务端; 服务路由契约由既有
  test_static_map_* 两条守阵钉住)。

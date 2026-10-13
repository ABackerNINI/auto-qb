# 3192 —— memory-bank cap 债务清零轮 (尺寸三件外迁 + 切片蒸馏) 基线

> 摘要: 清理会话清偿 `doc.caps` 尺寸债务 3 项 → 0 —— 三超 cap 文档按「触顶外迁原文到 `attachments/` 留一行指针」处置 (`webui-static-contract` 34,647→7,823 / `drawer-switch-flicker` 16,813→10,319 / `guards` 24,174→9,889), 随迁相对链接整体上移一层; kb-nav-page 切片 13,988→5,675 蒸馏跟进轮九~十七进 `progress/implemented-tooling.md`。`doc.caps --strict` 0 债务 / `doc.links` 绿 / `kb.check` 全绿。切片条数 94>70 属治理政策, 未调 `SLICE_COUNT_LIMIT`。
> 专题: memory-bank-cap-debt
> 基线时间: 2026-10-13 09:14

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

## test.full 实测

- 分支: `develop` (开工 `my-commit-flow.sync` 快进 280ed5e4→9769768e; 工作树含本轮改动时实测)
- 命令: `commands run test.full` (Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **3192 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16785 语句 / 159 未覆盖 / 5720 分支 / 140 partial; 门槛 98% 达标; 52.76s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列 (切片正文只写自己的 TOTAL)。
- 增量明细: passed 全来自开工快进并入的远端区间 (rollup_window docstring 漂移清偿等), **本轮零 `src/` 零 `tests/` 改动** —— 改动面全在知识库 (memory-bank/), 不进 `--cov=src` 统计, 也不在 `testpaths(tests/)` 里。

## 本轮改动面 (全部为知识库维护)

- `memory-bank/modules/webui-static-contract.md` —— 34,647 → 7,823 (外迁 21 长契约条目原文 → `modules/attachments/webui-static-contract-details.md`, 主档各条原位留一行指针, 速查短契约行保持)。
- `memory-bank/pitfalls/web-ui/drawer-switch-flicker.md` —— 16,813 → 10,319 (外迁 2026-10-04~12 六复发条目 → `pitfalls/web-ui/attachments/drawer-switch-flicker-2026-10-04-07-recurrences.md`, 主档原位留指针, 判据单点仍主档摘要)。
- `memory-bank/testing/guards.md` —— 24,174 → 9,889 (外迁批次守阵表格 → `testing/attachments/guards-batches-archive.md`, 主档各节原位留一行指针, 知识库结构/前端/流量聚合/种子状态 A 系/通用纪律 五节保持)。
- `memory-bank/activeContext/26-10-04-0952-kb-nav-page.md` —— 13,988 → 5,675 (跟进轮九~十七蒸馏进 `progress/implemented-tooling.md` 同名条目, 切片原位留一行指针)。
- 随迁相对链接整体上移一层 (外迁后位置深一层, 原文 `../x` 改 `../../x`); 主档侧新增「指回附件」链接不跟着改。

## 守卫收口

- `kb.check` 全绿 (主键 656 文档 · 312 专题 / 认领链闭环 / 回写措辞 / 日期)。
- `doc.links` 绿 / `doc.caps -- --strict` 债务 0 项 / `kb.active` 共 94 切片 (条数债务线 70 以下, 未调 `SLICE_COUNT_LIMIT`) / `test.one -- tests/test_memory_bank.py` 全绿。

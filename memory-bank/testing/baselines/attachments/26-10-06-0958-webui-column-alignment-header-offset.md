# 2676 —— WEBUI 右对齐列表头/值错位取证(纯文档轮, 零代码改动)

> 摘要: 用户报「右对齐列没有真正对齐标题文字」⇒ 只读取证轮次。产物全为文档 —— 取证报告
> [reports/26-10-06-0945](../../reports/26-10-06-0945-report-webui-column-alignment.html) ·
> 坑档 [pitfalls/web-ui/header-cell-gutter.md](../../pitfalls/web-ui/header-cell-gutter.md) ·
> 专题档案 [tasks/26-09-29-webui-column-alignment.md](../../tasks/26-09-29-webui-column-alignment.md)
> 追加(Status Done→Open) · activeContext 切片 · 索引重建。**零 Python 与测试改动** ⇒
> 数字应与上一条 [26-10-06-0731](26-10-06-0731-plan-playwright-e2e.md) 的 2676 + 4 持平 —— 实测一致。
> 基线时间: 2026-10-06 09:58

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md

- 分支: develop @ **295bb226**(开工 `my-commit-flow.sync` 后; 工作树含本次文档改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**(门槛 98% 达标, 实测 98.55%)
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 本轮两次采样 **52.43s / 56.18s**(后者含 3 条未重建索引的红) ⇒ 区间约 **50~56s**。
- 相对上一条基线 [26-10-06-0731](26-10-06-0731-plan-playwright-e2e.md)
  (2676 + 4 / 15823 / 163 / 5472 / 143): passed **±0** · 未覆盖 ±0 · 分支 ±0 · partial ±0;
  仅语句 15823 → **16021**(+198)。
  ⚠ **这 +198 不是本轮带来的**: `git diff --stat 0e278f12..295bb226 -- src/` **为空**
  (该区间 6 个 commit 全是文档 / `resources/` 模板), 且 16021 与更早的
  [26-10-06-0619](26-10-06-0619-playwright-e2e-teardown-fix-merged.md)(16021 / 166 / 5472 / 144) 一致
  ⇒ 判为 **0731 那一次采样的偏差**(该次工作树含并行会话未提交改动), 本轮回落到 16021。
- 过程: 首次 `test.full` 3 红 —— 全部是 `tests/test_memory_bank.py` 的「索引未重建」(新增坑档后没跑
  `kb.index`), 属**预期的中间态**; `commands run kb.index` 后 `tests/test_memory_bank.py` → **32 passed**。
  末次 `test.full` 1 红 —— `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`, 因认领链
  (档案 / 切片)指向**尚未写入**的本切片; 本切片落盘 + `kb.index` 后复验转绿(见下条)。
- 提交前复验: `commands run test.full` → **2676 passed + 4 skipped / 0 failed**(认领链闭合)。
- 旁证: `commands run kb.check` 主键纪律与认领链 OK; `commands run kb.index` 生成 20 个生成物。
- 改动面(全部为文档, 无 src/ / tests/ 改动): `memory-bank/reports/26-10-06-0945-report-webui-column-alignment.html`(新增)
  · `memory-bank/pitfalls/web-ui/header-cell-gutter.md`(新增) · `memory-bank/tasks/26-09-29-webui-column-alignment.md`(追加)
  · `memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md`(新增) · 各 `_index.md`(生成物重建)

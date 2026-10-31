# 2775 —— 方案 C 落地: 手抄测试数字上守卫(判据族 B) + 存量冻结

> 摘要: 用户报「基线维护成本高, 每轮要改切片/档案/切片正文/commit 至少 4 处」。核实: 口径**早已**
> 写着「数字只写 baselines/ 一处」(`baseline.md`), 只是**没守卫**所以反复违反 —— 真成本是同一数字的
> 四个副本。拍板方案 C: 数字只留 `testing/baselines/` 切片一处, 其余一律引用不手抄; 给 `check_wording.py`
> 加**判据族 B**(裸测试数字), 存量冻结(只拦新增)。切片正文的「逐位对比」也不再写。
> 相对上基线 26-10-08-0713(2772+4)passed **+3**(本轮新增 3 条守阵), 覆盖率四指标逐位持平。
> 档案: memory-bank/tasks/26-10-07-memory-bank-pending-wording.md
> 基线时间: 2026-10-08 08:42

**Refs:** memory-bank/tasks/26-10-07-memory-bank-pending-wording.md

## test.full 实测

- 分支: `develop`(已同步 `9ddd9193`; 工作树含本轮改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2775 passed + 4 skipped, 0 failed, 28.38s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 增量明细: `tests/test_memory_bank.py` 新增 3 条 ——
  `test_number_guard_exempts_dated_code_and_reports_only_overflow`(判据族 B 边界 + 存量冻结只报溢出)、
  `test_number_guard_is_green_on_current_kb`(存量未超冻结)、
  `test_number_guard_dated_exemption_does_not_cover_continuation_lines`(已知边界: 续行照常入判)。
  4 skipped 为 Windows 侧 POSIX 专属存量。

## 本专题面要点(非 pytest)

- **守卫判据族 B**: `check_wording.py` 的 `TEST_NUM_RES` 认「三位以上 passed / N+M skipped」, 扫面 =
  `tasks/` + `activeContext/`(滚动面); 豁免同 A 族(带日期行 / 代码围栏 / 行内代码 / `<!-- wording:allow -->`)。
  已知边界: 日期豁免只认**首行**, 多行流水的续行照常入判(见 `pitfalls/kb/scripts.md`)。
- **存量冻结(数目制)**: `FROZEN_TEST_NUM_COUNT = 394`(首测实测值); 命中数 ≤ 常数放行, 超出只报**溢出**
  条数(不刷全部存量 —— 否则提交闸门刷屏)。现算 `--count-numbers`, 全量清单 `--list-numbers`(清理会话用)。
- **口径单点**: `baseline.md`(切片正文只写自己 TOTAL, 逐位对比不写, 要看差值 `kb.baseline -n 2` 现列);
  `SKILL.md`「手抄测试数字」节 + DoD 第 3/4 步 + 反模式条; `AGENTS.md`「产出口径」一条。
- **不扫面**: `testing/baselines/`(数字事实源) · `plans/` `reports/` `issues/` 的 HTML(冻结快照)。
- **自证**: 本轮首次回写时, 本切片与档案的新增流水**被自家守卫拦下**(存量 394→397) —— 已改「见 kb.baseline」,
  存量回落 394。守卫对新规则的第一作用对象就是引入它的这次改动本身。

## 对照判据(后续沿用)

- 以本切片(2775+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。

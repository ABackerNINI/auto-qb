# 4799 passed + 10 skipped(根) —— 整组迁移 qb_temp 闸门按归属收窄

> 摘要: 整组迁移 qb_temp 闸门按归属收窄
> 基线时间: 2026-11-02 01:44
**Refs:**

## 验收数字

`commands run test.full` (2026-11-02 01:44 实测, 本机 Windows):

- 汇总行: `4799 passed, 10 skipped in 191.78s (0:03:11)`
- TOTAL 表: `TOTAL 22487 182 7708 140 99%` (语句 / 未达 / 分支 / 部分分支 / 覆盖率)
- 逐条口径: 主仓一套账 (全量含覆盖率报表); 本轮未动 tools/, 无工具侧独立账面
- 定向先行: `commands run test.one -- tests/test_web_relocate.py tests/test_relocate_units.py`
  67 passed (3.58s, 含新增三案)

## 本改动面

### 代码 (core/relocate)

- `src/auto_qb/core/modules/relocate_mod.py` (_group_facts): ext 的 `.!qB` 条目剥后缀后
  按归属三分 —— 对回本组 own → `qb_temp_entries`(硬拦面); 其余与 rest 一并送
  `_classify_entries` 单次扫描, 外组 → `external_entries`、无主 → `misc_entries`
  (均只 note)。结果按剥后缀名回流到带后缀原名; `exclusive = not ext` 不变。
- `src/auto_qb/core/modules/relocate_units.py`: GroupFacts docstring 与
  `GATE_QB_TEMP` 文案随新口径同步 (gate id `qb_temp` 不变), 判定逻辑零改动。

### 测试

- `tests/test_web_relocate.py`: 原 qb_temp 用例升级语义 (本组文件孪生 → blocked, docstring
  同步) + 新增 foreign_demoted / unowned_demoted 两案 (外组 .!qB → note+可迁 / 无主
  .!qB → note+可迁); 头部「## 测试计划」清单同步。
- `tests/test_relocate_units.py`: 闸门表文案断言同步 (内容根存在… → 本组存在…)。

### 知识库

- 计划 `plans/26-11-02-0134-plan-relocate-qbtemp-narrow.html` (doc-status Open, 实施轮
  已落地, 待收口翻 Done); 档案 `tasks/` 同轮立档 (Refs 双向)。
- 设计依据: libtorrent RC_1_2/RC_2_0 `aux::move_storage` 逐文件搬运语义源码核实
  (外组/无主文件既不搬也不删), 真机报告 26-10-18-0826 观测一致。

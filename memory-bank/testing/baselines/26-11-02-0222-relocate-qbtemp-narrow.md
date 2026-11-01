# 4801 passed + 10 skipped(根) —— 空间/同卷收集层祖先回退(方案A+B)

> 摘要: 空间/同卷收集层祖先回退(方案A+B)
> 基线时间: 2026-11-02 02:22
**Refs:**

## 验收数字

`commands run test.full` (2026-11-02 02:22 实测, 本机 Windows):

- 汇总行: `4801 passed, 10 skipped in 178.74s (0:02:58)`
- TOTAL 表: `TOTAL 22511 184 7722 142 99%` (语句 / 未达 / 分支 / 部分分支 / 覆盖率)
- 逐条口径: 主仓一套账 (全量含覆盖率报表); 本轮未动 tools/, 无工具侧独立账面
- 定向先行: `commands run test.one -- tests/test_web_relocate.py tests/test_relocate_units.py`
  69 passed (7.69s, 含 R1 新增四案; 首跑曾红 —— 叶子未建时 same_volume 也取不到
  st_dev 致形态降级, 补 _same_volume_resolved 后绿, 见计划 R1)

## 本改动面

### 代码 (core/relocate, 方案A+B)

- `src/auto_qb/core/modules/relocate_mod.py`: 新增收集层单点 `_volume_free_resolved`
  (disk_usage 失败逐级上溯最近存在祖先取卷剩余; 根不可用/裸名/空串 → None) 与
  `_same_volume_resolved` (same_volume None 逐级上溯第一个可读层比 st_dev ——
  实施中发现同卷判定在叶子未建时同根因, 与空间同一机制一并收口);
  `_group_facts` 两处改走单点, 全链不可达维持 None → GATE_SPACE 照旧硬拦。
- `src/auto_qb/core/modules/relocate_units.py`: same_fs 单成员 note 文案对齐实现
  (原文「目标冲突/空间未预检」不符, 实为其余闸门照跑; 方案B)。

### 测试

- `tests/test_web_relocate.py` 新增: `test_relocate_volume_free_ancestor_fallback`
  (真盘: 已存在叶子原语义/叶子未建祖先卷/裸名/空串) +
  `test_relocate_module_space_gate_ancestor_and_missing` (模块级桩: 叶子未建祖先解析
  无 space 闸门可迁移 / 整卷不可达仍硬拦); 头部「## 测试计划」同步。

### 知识库

- 计划 `26-11-02-0134` R1 改版 (doc-updated 26-11-02-0220, §03 增补/§04 S5-S6/§06 D3-D4/
  §07 风险行/变更记录); 档案 R1 并入 (原始请求 #5-#7, 子任务 S6-S8)。
- 用户 config 无 fs.path_map (已核实), 「容器映射未覆盖」文案属容器实现语义, Local 场景
  误导 —— 文案细分留待后续 (未纳入本轮)。

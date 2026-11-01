# 4807 passed + 10 skipped(根) —— 全闸门同族扫描三项处置(R2)

> 摘要: 全闸门同族扫描三项处置(R2)
> 基线时间: 2026-11-02 03:17
**Refs:**

## 验收数字

`commands run test.full` (2026-11-02 03:17 实测, 本机 Windows):

- 汇总行: `4807 passed, 10 skipped in 214.99s (0:03:34)`
- TOTAL 表: `TOTAL 22521 180 7726 140 99%` (语句 / 未达 / 分支 / 部分分支 / 覆盖率)
- 逐条口径: 主仓一套账 (全量含覆盖率报表); 本轮未动 tools/, 无工具侧独立账面
- 过程注记: 首跑全量红两处 —— ① docstring 守卫(新用例未列清单) ② 覆盖率 98.86%
  (新上溯单点的退化分支未覆盖), 补退化面守阵四案后回绿; 定向
  `commands run test.one`(relocate 三文件) 81 passed

## 本改动面

### 代码 (core/relocate, R2 三项)

- `src/auto_qb/core/modules/relocate_units.py`:
  #1 同卷豁免 —— `target_free` 不足/不可判定在 `same_volume is True` 时不再硬拦
  (rename 不占额外空间, 数值仅展示, note 同步); #3 新增稳定 gate id
  `target_type`(GATE_TARGET_TYPE, 目标已存在但不是目录 → blocked)。
- `src/auto_qb/core/modules/relocate_mod.py`:
  #2 冲突检测去 `names[:50]` 静默截断改全量(漏拦会让 mover 撞 need_full_check
  进度清零; 上限受 hard_max 约束, 规则重复发起被 T3 幂等挡在闸门前); #3 收集层
  `target_not_dir`(exists is True 且 isdir 非 True; 存在性抛错按不可判定由
  target_unknown 兑底)。

### 测试

- `tests/test_relocate_units.py`: 闸门表扩 target_type 行 + 新增
  `test_evaluate_group_same_volume_space_exempt`(同卷豁免四态) +
  `test_within_empty_scope_false`(覆盖补齐); 旧 space 行补 `same_volume=False`
  (同卷豁免后旧行为语义收窄); 头部测试计划清单同步。
- `tests/test_web_relocate.py` 新增: 60 文件组第 60 个冲突守阵(旧 [:50] 漏拦形态) /
  目标为文件 blocked 守阵 / 上溯退化面(层数走尽/空目标/卷根不动点/裸名) /
  _classify_entries 单条抛错 continue; 头部测试计划清单同步。

### 知识库

- 计划 `26-11-02-0134` R2 改版(doc-updated 26-11-02-0316: §03 扫描结果表/§04 S7-S9/
  §06 D5-D7/§10 变更记录); 档案原始请求 #8 + 子任务 S9-S11。

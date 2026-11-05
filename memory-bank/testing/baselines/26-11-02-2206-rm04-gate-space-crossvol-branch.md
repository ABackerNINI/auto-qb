# 4879 passed + 2 skipped(根) —— issue 1208 GATE_SPACE 跨卷空间不足分支红验补齐

> 摘要: 4879 passed + 2 skipped(根) —— issue 1208 GATE_SPACE 跨卷空间不足分支红验补齐
> 基线时间: 2026-11-02 22:06
**Refs:** memory-bank/issues/26-11-02-1208-bug-rm04-gate-space-crossvol-branch-missing.html

## 验收数字

`commands run test.full` (包装 151.4s / pytest 149.22s, 2026-11-02 实测):

```text
TOTAL                                                22521    134   7726    128    99%
4879 passed, 2 skipped, 3 warnings in 149.22s (0:02:29)
```

定向单文件 `tests/test_relocate_units.py`: 45 passed。

注记: 首跑曾因 gitignored 的 `tmp-analysis/w2b-save` 旧全量仓库副本被 `test_free_port_single_source` 的
`rglob` 扫到而红(环境残留, 非代码缺陷); 把该旧副本移出仓库后复跑本条数字。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/test_relocate_units.py`: 新增 `test_evaluate_group_space_cross_volume_branch`(L490 严格小于才拒 /
  恰等放行 / `same_volume=None` 按跨卷保守拒 / 同卷 rename 豁免), 并同步模块 docstring「## 测试计划」清单。
- issue `26-11-02-1208`: In Progress → Done; 修复后补充写明改道原因(本机各卷 free ≥ 30GB, 无法真机造出
  `target_free < needed` 的跨卷前置)与红验记录。
- 产品代码零改动(`src/auto_qb/core/modules/relocate_units.py` 保持原文)。

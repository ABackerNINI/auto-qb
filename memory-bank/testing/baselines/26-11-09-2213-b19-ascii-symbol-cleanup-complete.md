# 5856 passed + 2 skipped —— B19 全量实测: 非 ASCII 图形符号 13 批清偿完成, FROZEN 归零, 守阵 13 条全绿

> 摘要: B19 全量实测: 非 ASCII 图形符号 13 批清偿完成, FROZEN 归零, 守阵 13 条全绿
> 基线时间: 2026-11-09 22:13

## 验收数字

`commands run test.full`(2026-11-09, 分支 feat/ascii-symbol-cleanup, `tests/conftest.py` 1 行 docstring 修正后):

```text
TOTAL                                                26113     42   9082     54    99%
5856 passed, 2 skipped in 136.05s (0:02:16)
```

`commands run test.one -- tests/test_ascii_symbol_guard.py -n 0 --no-cov` → 13 passed, 0 失败, 副作用台账 0 条。

- 缺口净额 (M8 口径, miss + partial): 本片 42 + 54 = **96 单位**; 上基线 [26-11-09-0345](26-11-09-0345-issue-fix-batch-4bug.md) 为 33 + 51 = 84 ⇒ 净额 **+12**(≤ +15, 按口径不点名); 分母(语句 + 分支合并)35131 → 35195(语句 +40 / 分支 +24), 跨轮分母已变, 对比时注明。

## 本改动面

- 本轮为「非 ASCII 图形符号存量清偿」13 批全部完成的收尾实测(批次明细见计划 [26-11-08-1906-plan-ascii-graph-symbol-cleanup.html](../../plans/26-11-08-1906-plan-ascii-graph-symbol-cleanup.html) 的 §04, 此处不转抄); 存量冻结表 `tests/_ascii_symbol_frozen.py` 的 `FROZEN` 已归零(空字典), 全仓复扫 `{}` `[]`, 守阵 `tests/test_ascii_symbol_guard.py` 13 条全绿。
- 本批仅动 `tests/conftest.py:137` 一行 docstring: 覆盖率阈值陈述 `99` / `98.5` 改为与常量 `COVERAGE_FLOOR_WIN = 99.5` / `COVERAGE_FLOOR_OTHER = 99.0` 一致的 `99.5` / `99.0`; 产品代码与测试集合零改动。`dev.fmt` 带该文件参数跑零重排。

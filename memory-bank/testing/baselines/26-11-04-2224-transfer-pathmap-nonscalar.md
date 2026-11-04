# 5150 passed + 2 skipped; 覆盖率 99% —— 全量测试基线 · transfer path_map 非标量校验修复后

> 摘要: 全量测试基线 · transfer path_map 非标量校验修复后
> 基线时间: 2026-11-04 22:24
**Refs:** memory-bank/issues/26-11-03-0901-bug-transfer-pathmap-nonscalar.html, memory-bank/activeContext/26-11-04-2224-transfer-pathmap-nonscalar.md

## 验收数字

- 汇总行: `5150 passed, 2 skipped in 160.96s (0:02:40)`(2026-11-04 本机 Windows 实测, `commands run test.full` 总耗时 166.2s)
- 覆盖率 TOTAL: `23950 stmts / 208 miss / 8192 branch / 162 partial / 99%`
- 定向口径: `commands run test.one -- tests/test_transfer_config.py` 15 passed
- 口径注记: 关沙箱前台跑本次全量; 同一改动在后台跑时沙箱开关未生效、临时根回落 H:\Temp, 触发 junction/sidefx 假红(12 failed + 8 errors), 处置已记 pitfalls/testing/sandbox-full-run.md

## 本改动面

- `src/auto_qb/config/validation/sections.py`: `_validate_transfer_path_map` 先 `isinstance(value, str)` 再判空; 非字符串报「必须是字符串」, 缺键/空串仍沿用「不能为空」
- `tests/test_transfer_config.py`: 新增 `test_transfer_path_map_from_to_must_be_string`(dict/list/bool/int × from/to 矩阵 + 缺键口径)与 `test_transfer_path_map_nonscalar_blocks_load`(真实 YAML `load_config` 链路), 同步头部测试计划清单
- `memory-bank/issues/26-11-03-0901-*.html`: In Progress → Done, 补实际修法 / 验证方式 / 实测数字

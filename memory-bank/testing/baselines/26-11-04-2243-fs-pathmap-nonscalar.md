# 5152 passed + 2 skipped; 覆盖率 99% —— 全量测试基线 · fs.path_map 非标量校验修复后

> 摘要: 全量测试基线 · fs.path_map 非标量校验修复后(issue 26-11-03-0901 同批)
> 基线时间: 2026-11-04 22:43
**Refs:** memory-bank/issues/26-11-03-0901-bug-transfer-pathmap-nonscalar.html, memory-bank/activeContext/26-11-04-2243-fs-pathmap-nonscalar.md

## 验收数字

- 汇总行: `5152 passed, 2 skipped in 174.12s (0:02:54)`(2026-11-04 本机 Windows 实测, `commands run test.full` 总耗时 176.1s)
- 覆盖率 TOTAL: `23962 stmts / 208 miss / 8200 branch / 162 partial / 99%`
- 定向口径: `commands run test.one -- tests/test_config_misc.py` 67 passed
- 红验: 临时还原旧实现后两条新用例 2 failed(非标量被 str() 成 `"{'k': 'v'}"` / `"['D:/a']"` 后按「必须是绝对路径」报出)
- 口径注记: 本次全量**前台关沙箱**跑; 后台跑会让沙箱开关失效并回落 H:\Temp 产生假红, 见 pitfalls/testing/sandbox-full-run.md

## 本改动面

- `src/auto_qb/config/validation/sections.py`: `_validate_fs` 的 `path_map` 条目 from/to 先 `isinstance(value, str)` 再判空; 非字符串报「必须是字符串(当前为 dict|list|bool|int)」, 缺键/空串仍沿用「不能为空」; 绝对路径/挂载点/归一化/重复/前缀歧义检查不变
- `tests/test_config_misc.py`: 新增 `test_validate_fs_path_map_from_to_must_be_string`(dict/list/bool/int × from/to 矩阵 + 缺键口径)与 `test_fs_path_map_nonscalar_blocks_load`(真实 YAML `load_config` 链路抛 `ConfigError`), 同步头部测试计划清单
- `memory-bank/issues/26-11-03-0901-*.html`: 追加同批修法与实测数字, 状态保持 Done

# 4914 passed + 2 skipped(根) —— R2 测试文件 move-only 拆分后全量基线

> 摘要: R2 测试文件 move-only 拆分后全量基线
> 基线时间: 2026-11-03 01:57
**Refs:** memory-bank/tasks/26-11-03-test-big-file-split.md, memory-bank/plans/26-11-02-2342-plan-big-file-split.html

## 验收数字

`commands run test.full` 实测(合流远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22531    134   7732    128    99%
4914 passed, 2 skipped, 3 warnings in 169.76s (0:02:49)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率)。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `tests/`: 25 个大型测试文件 move-only 拆为 90 个分桶测试文件 + 20 个 support 模块; 原文件删除,
  2 个保留为无用例的 re-export shim(`test_speed_curve.py` / `test_hr_runtime.py`)。
- 拆分判据: 模块级界定逐字不变 + 测试函数名集合双向一致; 断言行/夹具原文未改; 每文件用例数守恒(合计 1524)。
- 同步并入远端新增用例: 远端 `tests/test_kb_nav.py` 的新 search 用例按同一分桶口径归 `test_kb_nav_interaction.py`。
- 新口径: 拆分后仍超千行的新桶不再就地二次切分, 登记计划「新桶超阈值 · 后续排期」
  (`tests/test_utils_windows.py` / `tests/test_web_commands_dispatch.py`)。
- 本轮不涉及 `src/`、`tests/helpers.py`、`tests/_tmp_bootstrap.py`、`tests-real/`。

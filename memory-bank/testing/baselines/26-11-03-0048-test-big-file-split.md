# 4913 passed + 2 skipped(根) —— R1 测试文件 move-only 拆分后全量基线

> 摘要: R1 测试文件 move-only 拆分后全量基线(已合流 Gitee develop)
> 基线时间: 2026-11-03 00:48
**Refs:** memory-bank/tasks/26-11-03-test-big-file-split.md

## 验收数字

`commands run test.full` 实测(合流远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22531    134   7732    128    99%
4913 passed, 2 skipped, 3 warnings in 175.69s (0:02:55)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `tests/`: 10 个大型测试文件 move-only 拆为 36 个测试文件 + 12 个支撑/扫描模块(清单见档案
  [`tasks/26-11-03-test-big-file-split.md`](../../tasks/26-11-03-test-big-file-split.md) 子任务表)。
- 拆分判据: 模块级界定逐字不变 + 测试函数名集合双向一致; 断言行/夹具原文未改。
- 拆分后用例集合与拆分前一致; 本轮不涉及 `src/`、`tests/helpers.py`、`tests/_tmp_bootstrap.py`。
- 收尾合流时远端 `test_webui_static_skins.py` 新增的右键目标行守阵按同一分桶口径并入
  `test_webui_static_skins_table.py`(测试体与「## 测试计划」条目原文未改)。

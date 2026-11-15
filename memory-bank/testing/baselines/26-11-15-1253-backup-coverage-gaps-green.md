# 6238 passed, 2 skipped —— webui 配置备份覆盖率闸回绿基线(补齐 backup.py/writer.py 闸门分支测试)

> 摘要: webui 配置备份覆盖率闸回绿基线(补齐 backup.py/writer.py 闸门分支测试)
> 基线时间: 2026-11-15 12:53

## 验收数字

`commands run test.full` 实测(2026-11-15 12:47, Windows 本机, feat/webui-config-backup 工作树):

```
TOTAL                                                27783     71   9788     77    99%
6238 passed, 2 skipped in 147.77s (0:02:27)
```

- **退出码 0: 覆盖率闸 PASS** —— 覆盖单元 37423/37571 = 99.61% >= 99.5(Windows 侧阈值, tests/conftest.py::pytest_configure); 取代 26-11-15-1226(闸红切片, 因补齐 backup.py 覆盖缺口)。
- 差分(对照上基线 26-11-15-1226 的 TOTAL 27783/104/9788/94): 缺语句 104 → 71, 缺分支 94 → 77; 用例 6219 → 6238(+19, 全部进 tests/test_web_backup.py, docstring 测试计划同步, test_test_plan_docstring_guard 过)。
- 补测面(以逐行报告为准): `routes/backup.py` 88% → 100%(alias 共享引用闸/深度上限/节点数上限/文本 1MiB 闸/解析 RecursionError 422/解析失败 500 收口/body 非 dict 400/`_aggregate_config_precheck` 三分支/提交路径本机坏 YAML 500/gtm ToolUnreachable 与非预期状态码 skipped); `config/writer.py` 97% → 99%(write_yaml_doc 直测/_mask_yaml_node、_unmask_yaml_node 非 dict 直通/targets 列表非 dict 条目两弧/残留哨兵扫描容器去重/本机无文件 _read_yaml_doc None 面)。残缺 369->exit(validate_yaml_doc finally 的 tmp_path 空值弧)端点面不可自然触发, 列报不改。
- test.quick(提交闸门同款): 6238 passed, 2 skipped in 53.23s(2026-11-15 12:50 实测)。

## 本改动面

- `tests/test_web_backup.py`: +19 用例(评审闸门分支回归 + writer 直测单元), docstring「## 测试计划」同步登记

# 3998 —— QbManager 构造单点扩参数 + 86 处内联装配回收 + AST 守阵后全量基线

> 摘要: QbManager 构造单点扩参数 + 86 处内联装配回收 + AST 守阵后全量基线
> 基线时间: 2026-10-22 04:08
**Refs:** memory-bank/tasks/26-10-22-test-manager-builder-params-dup.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- TOTAL 表: **20981** stmts / **101** miss / **7088** branch / **102** partial / **99%**
- 汇总行: **3998 passed, 2 skipped in 148.41s (0:02:28)**
- 覆盖率: **99%**(20981 stmts / 7088 branch, 99.28%)

逐条口径注记:

- 本轮只改 `tests/`(单点扩参数 + 86 处改调 + 新守阵 2 条用例), `src/` 零改动 ⇒ 覆盖率分母(20981/7088)与上一条基线一致, 差异只在用例数(新增守阵 2 条)
- 守阵红验(探针): 临时造一个含内联 `QbManager("", ...)` 的 `tests/test_zz_probe.py` → 守阵判红并报 `test_zz_probe.py:5`; 删除后归绿
- 基线测在「已含本次代码改动、尚未提交」的工作树上
- 耗时 148.41s 是单次采样(同时段机器负载口径见 `testing/baseline.md`)

## 本改动面

- `tests/helpers.py` —— `make_manager` 扩参数面(`cfg` / `bare` / `client` / `no_lock` / `load_rules` / `**cfg_overrides` + 未知段名 TypeError); 三条示例规则抽 `_example_rules_config()`; 新增 `grouping_cfg()` 分组段单点
- `tests/test_manager_single_point.py`(新) —— AST 守阵: `tests/` 除 `helpers.py` 外零 `QbManager(...)` 构造 + 自检用例
- `tests/test_grouping.py` —— 60 处内联装配改调单点(含 `_grp_env` 与删 `_group_cfg`), −137/+61 行
- `tests/test_episodes.py`(5) · `tests/test_delete_tags.py`(5) · `tests/test_hr.py`(4) · `tests/test_qbmanager.py`(3) · `tests/test_state_matrix.py`(2) · `tests/test_checking.py`(2) · `tests/test_ui.py`(1) · `tests/test_rules_core.py`(1) · `tests/test_ops.py`(1) · `tests/test_modules_p4.py`(1) · `tests/test_locking.py`(1) —— 同上改调, 三处包装器委派走 `cfg=` / `load_rules=True`
- 生产代码零改动

# 5080 passed + 2 skipped(根) —— 覆盖率第三轮 P0 验收全量基线(rules+fuse 家族清偿)

> 摘要: 覆盖率第三轮 P0 验收全量基线(rules+fuse 家族清偿)
> 基线时间: 2026-11-04 05:07
**Refs:** memory-bank/plans/26-11-04-0157-plan-test-coverage-uplift-3.html (§04 P0 验收)

## 验收数字

`commands run test.full` 实测(coverage-uplift-3, Windows 并行 + 覆盖率):

```text
[ok] test.full (172.2s)
  TOTAL                                                23325    108   7956    109    99%
  5080 passed, 2 skipped in 169.59s (0:02:49)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 172.2s(单次采样, 区间口径见 [../baseline.md](../baseline.md)); 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。精确 TOTAL **99.31%**(31064/31281, 语句+分支合并口径)—— 过 P0 验收线 99.3(计划 26-11-04-0157 §04)。

- **缺口单位 217**(miss 108 + partial 109), 对照计划快照 319(167m + 152p, 分母同为 31281)**净清偿 102**(M8 净额 = 217 − 319 = −102, 为负无新模块入榜)。
- **watchlist(合并覆盖 <95% 单文件)7→4**: 核销 3 个 —— rules/base 94→100%、fuse_mod 90→99%、cli 90→100%; 存量 4 个滚 P1 —— commands.py 90 / ops_jobs 90 / runtime_common 93 / views_episodes 94。
- **豁免行数**(`grep -rn "pragma: no cover" src/` 计数)8, 与计划快照持平。

## 本改动面

- T0a `4e4acde6`: `tests/test_rules_core.py`(+11 用例)+ `tests/test_config_rules.py`(+6 用例), 共 17 条 —— rules/base 35 单位清偿(条件树深度上限/节点形状/not 否认/非 dict 拒绝/choose 块构造守卫/异常 trace 与吞没等); config/validation/rules 22→3(余 3 分支支为到不了防御支)。
- T0b `806f954b`: `tests/test_fuse_mod.py`(+12 用例)+ `tests/test_cli.py`(+5 用例), 共 17 条 —— fuse_mod 33 单位清偿(武装/adopt/放行各路径/未知状态丢弃/标签外部移除/dry-run 等, 余 1 防御 partial); cli 16 单位清偿(100%)。
- **变异红验(抽 4/34 = 11.8%, 每次只变异一处, 定向跑测确认变红后 `git checkout --` 还原并复跑确认回绿)——4/4 全部杀死, 零假绿**:
  1. `rules/base.py` 深度守卫 `depth > CONDITION_TREE_MAX_DEPTH` 放宽一层 → `test_condition_tree_depth_limit` 红;
  2. `core/modules/fuse_mod.py` 未知状态丢弃守卫 `del entries[h]` 注释 → `test_fuse_unknown_status_entry_dropped` 红;
  3. `config/validation/rules.py` choose 分支非 dict 守卫 `if not isinstance(br, dict)` 短路为 False → `test_validate_rules_choose_branch_not_dict` 红;
  4. `cli.py` hash 清单解析去 `.lower()` → `test_main_fuse_release_dispatch_parses_hashes` 红。
  还原后 `git diff HEAD` 空、`git status` 仅本切片, 产品码零残留; 无红验临时文件入仓库根。

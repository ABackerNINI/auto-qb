# 2868 —— config 多条目循环 continue/break 守阵(issue 26-10-08-0903-loop-guards)基线

> 摘要: 认领并实施 `issues/26-10-08-0903-test-config-mutation-loop-guards.html` —— 首轮 config 变异审计入池的 6 条 `test` issue 之一(多条目循环缺 continue/break 守阵)。从首轮 dump 提取全部 **30 条** `continue→break`/`break→return` 候选, `mutants.verify` 复验 **21 SURVIVED / 9 KILLED**(9 条已被 R2/R7/R8 的同型守阵杀死)。补 **18 个守阵**(`tests/test_config.py` 10 + `tests/test_hr_config.py` 8)覆盖 21 条存活候选; 红验 **34/34**(30 条来自 dump + 4 条合成: `_validate_trigger_action_compat`×2 / `_validate_rules`×2)。S6 同目标同池 `--no-refresh` 复跑: 存活 **573 → 533(净 −40, 新增存活 0)**, 杀死率 **87.31% → 88.14%**。**零 `src/` 改动**(纯补测 + 文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-09 16:11

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(S6 复跑, 同目标同池)

- **目标(glob)**: `**/config/*.py`(与首轮 / R6 / R8 完全一致)
- **选择池(逐文件, 与首轮一致 —— 换池数字不可比)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · `process_isolation=forkserver` · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **复跑带 `--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_config.py` + `tests/test_hr_config.py` 进镜像**(否则被 `git checkout -f` 冲掉); 复跑前镜像已刷新到 `origin/develop`(含 R8 提交 `be706f94`)

| 轮次 | 变异总数 | 杀 | 存活 | `no tests` | 杀死率 |
|---|---|---|---|---|---|
| R8 基线(26-10-08-1228, schema-surface) | 4799 | 4190 | 573 | 36 | 87.31% |
| **本轮(26-10-09-1610, loop-guards)** | **4799** | **4230** | **533** | **36** | **88.14%** |

- **逐 id 对差**: 本轮新杀 **40** · 新增存活 **0**。

### 30 条 continue/break 候选的 S4 复验(判据干净)

- `commands run mutants.verify -- --ids-file <30 条清单> --workers 8` → **21 SURVIVED / 9 KILLED**, 耗时 451s(≈15s/条)。**无既有红守卫污染**(两类读源码守卫已在远端修复), 无需 `--deselect`。
- **9 条 KILLED(假存活, 已被既有守阵杀死)**: `_migrate_config_1_2` 三条跳过分支(R2 的 `test_migration_1_2_processes_every_tracker`)· `_collect_explicit_empty_paths`(R2)· `readonly_config_paths`(R8 的 `test_readonly_config_paths_walk_contract`)· `_validate_hr_site_bindings` 未登记档案分支(R2)· `_validate_fs` 非字典项分支(R2)· `unmask_tree`(R2)· `_fallback_readonly_fields`(R7)。⇒ issue 前提成立(21 条真缺口)。

### 补测(S5)与红验

新增 **18** 个测试函数, 全部为「多条目」形态(触发跳过分支的条目放前, 后一个必须照常被处理的条目放后):

| 守阵 | 文件 | 钉住的 continue/break |
|---|---|---|
| `test_validate_fs_reports_all_entries_after_skip_branches` | test_config | `_validate_fs` 空 from / 归一后为空 / 空 to 三处跳过分支(mutmut_87/94/97) |
| `test_validate_fs_prefix_ambiguity_keeps_scanning` | test_config | `_validate_fs` 前缀歧义自比 `continue`(106) + 命中后只 break 内层(113) |
| `test_validate_trackers_reports_all_entries` | test_config | `_validate_trackers` 非字典条目(9) |
| `test_validate_tag_lists_reports_after_absent_key` | test_config | `_validate_tag_lists` 前键缺失(6) |
| `test_validate_gslc_reports_all_curves` | test_config | `_validate_global_speed_limit_curve` 两条结构跳过(108/114) |
| `test_validate_curve_points_reports_all_entries` | test_config | `_validate_curve_points` 单项映射/阈值不可解析(14/22) |
| `test_validate_rule_refs_dedup_after_malformed` | test_config | `_check_rule_refs` 判重轮前置畸形引用(41) |
| `test_validate_checking_action_reports_all_segments` | test_config | `_validate_checking_action_spec` 缺段/段非字典(46) |
| `test_validate_trigger_action_compat_reports_all_actions` | test_config | `_validate_trigger_action_compat` 结构错/伪动作两条 continue(25/32) |
| `test_validate_rules_reports_all_groups_and_rules` | test_config | `_validate_rules` 非字典 group / 非字典 rule 两条 continue |
| `test_hr_check_sites_reports_all_entries` | test_hr_config | `_validate_hr_check` 未登记档案(237) |
| `test_site_bindings_reports_all_after_non_dict_tracker` | test_hr_config | `_validate_hr_site_bindings` 非字典 tracker(10) |
| `test_site_bindings_reports_all_after_disabled_entry` | test_hr_config | 未启用条目(50) |
| `test_site_bindings_reports_all_after_explicit_missing` | test_hr_config | 显式 tracker 键不存在(65) |
| `test_site_bindings_reports_all_after_default_zero_hit` | test_hr_config | 默认映射零命中(76) |
| `test_site_bindings_reports_all_after_ambiguous_mapping` | test_hr_config | 默认映射歧义(82) |
| `test_site_bindings_reports_all_after_duplicate_binding` | test_hr_config | 重复绑定(88, 合成第三档案让 break 后果可观测) |
| `test_resolve_hr_site_bindings_after_disabled_site` | test_hr_config | `loaders._resolve_hr_site_bindings` 未启用条目(2) |

- **红验 34/34 RED**: 30 条按首轮 dump 的 hunk 正文块**逐字节**套同构变异(保留 CRLF)→ 目标用例变红 → `git checkout --` 还原(主仓 `src/` 零残留); 另 4 条(`_validate_trigger_action_compat` 的两条 continue、`_validate_rules` 的两条 continue)首轮 dump 未收录(带行尾注释), **手工合成**同构变异后同样变红。
- **关键设计**: 全部用例都是**多条目** —— 单条目用例只有一次迭代, `continue` 与 `break` 行为相同, 这正是首轮池杀不掉的原因。

### 新杀 40 条的归因(诚实拆分)

- **21 条 = 本轮定向候选**(与 S4 复验的 21 条 SURVIVED 逐 id 对应)。
- **2 条 = `_validate_trigger_action_compat__mutmut_25/32`**(真正的 `continue→break`, 因 continue 行带行尾注释未被首轮「纯 continue 行」提取式命中; 由新守阵杀死, 与手工合成红验一致)。
- **17 条 = 同循环内的旁支变异**(collateral): `_validate_curve_points` 8/13/42(`pos=None` / `errors.append(None)` / `errors=None`)· `_validate_global_speed_limit_curve` 98/113/115/137/138/139/140/159 · `_validate_trigger_action_compat` 26(`name=None`)· `_validate_fs` 50/111/112 · `_validate_tag_lists` 3/4(键名变体)。它们与目标变异同处一条多条目循环, 被同一批新用例一并杀死。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2868 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial)
- 相对上基线 [26-10-09-1522](../baselines/26-10-09-1522-test-mutation-audit-hr-plan.md)
  (2850 passed + 4 skipped, 16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial):
  passed **+18**(= 本轮 18 个新测试函数) / 语句 **±0** / 未覆盖 **−2** / 分支 **±0** / partial **−2**。
- **−2 未覆盖 / −2 partial 的归属**: 新守阵走到此前无测试覆盖的分支(前缀歧义报错路径、各 `continue` 跳过分支等)。`src/` **零改动**。

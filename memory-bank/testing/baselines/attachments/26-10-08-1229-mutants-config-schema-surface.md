# 2819 —— config schema 键面/分支守阵(issue 26-10-08-0903-schema-surface)基线

> 摘要: 认领并实施 `issues/26-10-08-0903-test-config-mutation-schema-surface.html` —— `src/auto_qb/config/schema/__init__.py` 的 **27 条 S4 真洞候选**(schema_payload 16 / readonly_config_paths 8 / plugins_by_kind 3)。**S4 复验: 27 条全部 SURVIVED**(无既有红守卫污染, issue 前提成立)。补 **6 个守阵**(全部落 `tests/test_config_schema.py`)后**红验 26/27 KILLED**, 余 **1 条判定为等价变异**(`readonly_config_paths__mutmut_17`)。S6 同目标同池 `--no-refresh` 复跑: 存活 **653 → 573(净 −80)**, 其中 **26 条来自本轮补测**(与红验一一对应), 另 **57 条集中在 writer 模块**、系镜像刷新时纳入了 `fcc3cd69`(R7 的 22 守阵, R6 基线时点之后才进 develop)。**零 `src/` 改动**(纯补测 + 文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 12:29

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(S6 复跑, 同目标同池)

- **目标(glob)**: `**/config/*.py`(与首轮 / R6 完全一致)
- **选择池(逐文件, 与首轮一致 —— 换池数字不可比)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · `process_isolation=forkserver` · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **复跑带 `--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_config_schema.py` 进镜像**(否则被 `git checkout -f` 冲掉)

| 轮次 | 变异总数 | 杀 | 存活 | `no tests` | 杀死率 |
|---|---|---|---|---|---|
| R6 基线(26-10-08-1016, validator-strings) | 4799 | 4110 | 653 | 36 | 85.66% |
| **本轮(26-10-08-1228, schema-surface)** | **4799** | **4190** | **573** | **36** | **87.31%** |

- **逐 id 对差**: 本轮新杀 **83** · 新增存活 **3**(`writer.x__backup__mutmut_12/15/19`, 归类漂移、非退化、非本 issue 范围)

### 27 条候选的 S4 复验(判据干净)

- `commands run mutants.verify -- --from-report <27 条清单> --workers 8` → **27/27 SURVIVED**, 耗时 473s(≈17s/条)。**无误判**: 首轮「27 条真洞」结论成立。
- 与 R7 的区别: 本轮**未**出现「读源码文本守卫在基线就红」的判据污染(该两类守卫已在远端修复), 故无需 `--deselect` 即可直接用全套件当判据。

### 补测(S5)与红验

新增 **6** 个测试函数(全部落 `tests/test_config_schema.py`, 同步该文件 docstring「## 测试计划」):

| 守阵 | 钉住什么 |
|---|---|
| `test_readonly_config_paths_exact_and_order` | readonly 点路径**集合 + 顺序**逐位钉住(旧守卫只用 `set()` 比较, 丢了顺序) |
| `test_readonly_config_paths_walk_contract` | **合成结构探针**: 嵌套层 `[ui_only 叶][readonly 叶]` —— ui_only 须 `continue` 不断链; readonly 叶须带段前缀; 非 readonly object 段须递归 |
| `test_plugins_by_kind_condition_and_action_branches` | condition / action **两支**分别返回对应插件表(旧守卫只走 action 一支)+ 未知 kind 落到 action 兜底 |
| `test_schema_payload_constants_keys_exact` | `constants` 分区键集合**逐位**钉住(旧守卫只抽查 7 个名字的存在性) |
| `test_schema_payload_constants_values` | 每个常量表与源常量取值一致(顺序敏感), 钉住映射关系而非仅键名 |
| `test_schema_payload_preset_key_metadata` | `hr_check_site_presets` 每条键集合(7 个)+ 逐字段取值钉住(旧守卫只查 4 个键存在) |

- **红验 26/27 KILLED**(apply 同构变异 → 跑 `tests/test_config_schema.py` → 原字节还原, 主仓 `src/` 零残留)。
- **关键设计**: 现状里 4 条 readonly 路径**全在顶层**, 使 `walk` 的递归/前缀机制在真实数据上「看不出差别」—— 光断言当前输出钉不住 `continue→break`、`if prefix else` 改假条件、`f.kind == "object"` 变体、`walk(x, None)` 这类变异。故 **`test_readonly_config_paths_walk_contract` 用合成结构钉住机制本身**(注: ui_only 叶必须放在**嵌套层**才可达 —— 顶层已由 `real_config_fields()` 滤掉 ui_only, 放顶层探针是空转)。

### 等价变异 1 条(不追)

- **`x_readonly_config_paths__mutmut_17`**(`walk(real_config_fields(), "")` → `None`): 顶层 `prefix` 只被 `f"{prefix}.{f.key}" if prefix else f.key` 消费, `""` 与 `None` **同为假值**, 对所有输入产出逐一相同 —— 数学等价, 非真洞。

### 新杀 83 条的归因(诚实拆分)

- **26 条 = 本轮补测**, 与红验 26/26 逐 id 对应: `plugins_by_kind` 3 · `readonly_config_paths` 7(除等价的 mutmut_17)· `schema_payload` 16。
- **57 条集中在 writer 模块**(`_backup` / `_as_builtin` / `_build_yaml` / `_sync_mapping` / `_fallback_restart_fields` / `_set_path` / `_plain_scalar` / `_same_value` / `_stamp_schema_version` …)—— **非本轮补测**: 镜像在 12:07 的 `mutants.verify` 刷新到 `origin/develop` 时纳入了 `fcc3cd69`(R7「config writer 长尾」的 22 守阵), 而 R6 基线(10:16)时点尚未包含它。**数字可比性说明**: 两轮目标与池逐位一致, 差异只来自 develop 上新增的守阵, 属纵向可比范围内的正常推进。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2819 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16476 语句 / 161 未覆盖 / 5694 分支 / 145 partial)
- 新增测试 **+6**(`tests/test_config_schema.py` 34 → 40 个用例); `src/` **零改动**。

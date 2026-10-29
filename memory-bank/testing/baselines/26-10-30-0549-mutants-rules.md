# 3400 变异 / 实测杀死率 71.8% —— rules 包首轮变异审计

> 摘要: 计划 26-10-30-0049 的 rules 包首轮(整包单轮): 目标 `**/rules/*.py` · 16 文件定向池 → mutmut 报 **3400 变异 / 杀 2036 / 存活 1346 / 超时 18**(名义杀死率 **59.9%**)→ 逐条「apply 变异 → 跑池 → 还原」机器复测推翻工具判定: **伪存活 404 / 真存活 942 / 超时 18**, 实测杀死率 **71.8%**(工具低估 12 个点)→ 三分类 **真洞 284 / 等价 658 / 假存活 404** → 归并 **60 簇** → 补 **60 守阵**(A/B/C 三批, 逐簇红验全通过)→ 同目标同池复跑 → **284 条真洞逐条实测 KILLED 284 / 仍存活 0**, 守阵零缺口。**零 `src/` 改动**(纯补测 + 文档)。
> 基线时间: 2026-10-30 05:49

**Refs:** memory-bank/plans/26-10-30-0049-plan-mutation-audit.html, memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/tasks/attachments/26-10-30-rules-classification/, memory-bank/pitfalls/testing/mutmut-survived-verdict.md

## 变异面实测(首轮)

- **目标(glob)**: `**/rules/*.py` —— 命中 rules 包 **18 个 .py**, 实际产生变异的 **15 个**(另 3 个零变异: `expr/errors.py` / `registry.py` 仅被池旁及, 见下三分类表 0 真洞行)
- **选择池(逐个文件, 16 个 / 470 test fn; 跨轮必须一致)**:
  `tests/test_rule_base.py` · `tests/test_rule_engine.py` · `tests/test_rules_core.py` · `tests/test_conditions.py` · `tests/test_state_matrix.py` · `tests/test_file_access.py` · `tests/test_registry.py` · `tests/test_actions.py` · `tests/test_checking.py` · `tests/test_ops.py` · `tests/test_relocate_exec.py` · `tests/test_expr_parse.py` · `tests/test_expr_eval.py` · `tests/test_mixins_tags.py` · `tests/test_trigger_events.py` · `tests/test_hr.py`
  - 复跑时**同一 16 文件**, 但其中 **7 个已补守阵**(`test_actions` / `test_rule_base` / `test_rule_engine` / `test_expr_eval` / `test_expr_parse` / `test_conditions` / `test_checking`)⇒ 池内用例数增加: 首轮 470 test fn → 补测后同 16 文件 collect **692**(Windows 侧 `--collect-only` 实测)
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 3` · **专用镜像** `~/auto-qb-mut-rules`
- **机器**: WSL2 `Ubuntu-26.04` · Linux 6.18.33.2-microsoft-standard-WSL2 · **8 核** / 7 GB

| 轮次 | 变异 | 杀 | 存活 | no tests | 超时 | suspicious | 墙时 | 杀死率 |
|---|---|---|---|---|---|---|---|---|
| **首轮**(2026-10-30 01:25) | **3400** | **2036** | **1346** | **0** | **18** | **0** | **356.1s** | 名义 **59.9%** / 实测 **71.8%** |
| **复跑(S6)** | **3400** | **2240** | **1148** | 未单列 | **12** | 未单列 | **4m52s** | 名义 65.9%(含工具伪存活, 不作验收) |

## 杀死率口径(两个数字都对, 分母相同分子不同)

- **mutmut 名义 59.9%** = `2036 / 3400` —— 直接用工具自己的 killed 计数。
- **实测 71.8%** = `(2036 + 404) / 3400` —— 404 是**被工具判 survived、实测池能抓住**的变异(下节机器复测)。
- **差 12 个点的成因**: mutmut 对本包的存活判定**系统性失真**(import 期构建的模块级表 + `verify` 在本机不可用, 见「口径与边界」1–2)。⇒ 本包任何「存活数」在未实测前都只是工具声称, 不能当验收数字; 复跑那行 65.9% 同理。
- **验收判据不是这个百分数**, 是「284 条真洞逐条实测能不能被杀」—— 见末节。

## 机器复测(推翻工具判定)

逐条「apply 变异 → 跑 16 文件池(单进程)→ 还原」, 覆盖首轮全部 **1364** 条存活 + 超时:

| 面 | 条数 | 耗时 | KILLED | SURVIVED | TIMEOUT |
|---|---|---|---|---|---|
| 表类(`expr/env.py` 模块级 NAME_TABLE / FUNC_TABLE) | 614 | ≈1481s(614 × ≈2.4s) | **303** | **311** | 0 |
| 其余 | 750 | 4706s | **101** | **631** | **18** |
| **合计** | **1364** | **≈6187s** | **404** | **942** | **18** |

- **伪存活 404 / 真存活 942 / 超时 18** —— 404 与三分类的「假存活」**逐位吻合**(两条独立路径互证)。
- 表类伪存活率 **49.3%**(303/614), 其余 **13.5%**(101/750): 越靠近 import 期构建的数据, 工具越不可信。

## S3 三分类(1364 条, 18 份 md)

逐条读带 diff 的存活清单判三类, 落 `tasks/attachments/26-10-30-rules-classification/` 的 **18 份 md**(`rules__*.md` + `_clusters.md`):

- **真洞 284 / 等价 658 / 假存活 404**(1346 条存活的三分类; 18 条超时未分类, 单列于「口径与边界」3)

| 文件 | 真洞 | 等价 | 假存活 |
|---|---|---|---|
| `actions/basic.py` | 53 | 55 | — |
| `base.py` | 36 | 53 | — |
| `expr/env.py` A(`NAME_TABLE` 1/2) | 27 | 67 | 92 |
| `expr/env.py` B(`NAME_TABLE` 2/2) | 39 | 66 | 81 |
| `expr/env.py` C(`FUNC_TABLE`) | 52 | 59 | 131 |
| `expr/env.py` D(其余) | 12 | 57 | 100 |
| `actions/transfer.py` | 14 | 57 | — |
| `actions/checking.py` | 8 | 35 | — |
| `actions/full_checking.py` | 4 | 36 | — |
| `actions/skip_checking.py` | 5 | 2 | — |
| `expr/eval.py` | 18 | 20 | — |
| `expr/lexer.py` | 4 | 69 | — |
| `expr/parser.py` | 3 | 39 | — |
| `expr/types.py` | 4 | 18 | — |
| `conditions.py` | 3 | 9 | — |
| `checking_meta.py` | 2 | 9 | — |
| `registry.py` | 0 | 3 | — |
| `expr/errors.py` | 0 | 4 | — |
| **合计** | **284** | **658** | **404** |

## 归并与补测(S5)

- **284 真洞 → 60 簇**(覆盖 284/284, 明细 `_clusters.md`): **A 17 簇 / 79 条**(错动作作用到真实种子)· **B 25 簇 / 80 条**(引擎骨架与匹配顺序)· **C 18 簇 / 125 条**(配置期拒收与诊断)。
- **补 60 条守阵**, 分 A/B/C 三批, **逐簇红验**(打补丁 → 目标用例红 → 还原 → 绿)**全通过**; 改动文件 7 个: `tests/test_actions.py` · `test_rule_base.py` · `test_rule_engine.py` · `test_expr_eval.py` · `test_expr_parse.py` · `test_conditions.py` · `test_checking.py`。
- **`test.full` 实测**: **4142 passed / 2 skipped / TOTAL 99%**(补测前基线 4064 passed / 10 skipped / missed 117)。

## S6 复跑与真实验收

- 同目标同池(7 文件带新守阵): **3400 变异 / 杀 2240 / 存活 1148 / 超时 12**, 墙时 **4m52s**。
- ⚠ **这个 1148 不能当验收数字** —— 仍含 614 条表类变异被 mutmut **恒报 survived**(工具侧无差别, 与守阵无关)。
- **真实验收**: 284 条真洞**逐条实测** → **KILLED 284 / 仍 SURVIVED 0**, 守阵零缺口。

## 口径与边界(必须连同数字一起读)

1. **`mutants.verify` 在本机不可用**: 它跑全量套件, 而全量套件在 WSL Linux 上有 **3 个既有平台失败**(`tests/test_alias_fs.py` ×2 · `tests/test_relocate_paths.py` ×1), 基线本就红 ⇒ 任何变异恒判 **KILLED**。故本包一律不用 verify 出数。
2. **mutmut 对 import 期调用的函数里的变异不生效**: `_build_name_table` / `_build_func_table` 的变异 **614 条被无差别记为 survived**; 换 `process_isolation`(fork / forkserver)结果**完全一致** ⇒ **不是隔离问题**。且**不止表类**: 非表类抽查 3 条也有 **2 条**伪存活。⇒ 本轮判定**一律以「apply + 跑池」实测为准**, 不看工具声称。
3. **18 条超时未做三分类**(其中 1 条 `expr.lexer.x__read_string__mutmut_4` 在 150s 内已刷 F, **实质 KILLED**)—— 超时按「池未能在窗口内变绿」单列, 不混进真洞/等价分母。
4. **`RECHECK_FAIL_LIMIT` 的上限比较在 `core/modules/ops_mod.py:233`, 不在 rules 包内** —— 计划假设的这个高危面**本轮覆盖不到**, 需单开 ops_mod 轮。
5. **transfer 的路径拼接/冲突/跨盘逻辑在 `core/modules/relocate_mod.py`**, 不在 `actions/transfer.py` —— 本轮 transfer 的 14 条真洞只到动作层(作用域/confirm/限速方向), 路径面未覆盖。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_actions.py` · `test_rule_base.py` · `test_rule_engine.py` · `test_expr_eval.py` · `test_expr_parse.py` · `test_conditions.py` · `test_checking.py` | 60 条守阵(60 簇各一条), 头部「## 测试计划」同步 |
| `memory-bank/tasks/attachments/26-10-30-rules-classification/` | 18 份三分类 md + `_clusters.md`(60 簇)+ 两份复测 tsv |
| `memory-bank/testing/baselines/26-10-30-0549-mutants-rules.md` | 本切片 |
| `memory-bank/pitfalls/testing/mutmut-survived-verdict.md` | 新坑档(mutmut 存活判定不可靠 + verify 在 Linux 全量套件上失效) |
| `memory-bank/tasks/26-10-08-test-mutation-audit.md` | 追加本轮轮次行 |

**未改**: `src/` 零改动(纯补测 + 文档)。

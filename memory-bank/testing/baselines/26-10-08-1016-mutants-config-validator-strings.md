# 2789 —— config 变异审计: 字符串键名/布尔逻辑守阵补齐(issue 26-10-08-0903 validator-strings)

> 摘要: 认领并实施 issue `26-10-08-0903-test-config-mutation-validator-strings`(config 首轮真洞余量之「键名大小写 + and/or 互换」主题)。对 `src/auto_qb/config/validation/` 的 `_expr_gate` / `_check_rule_refs` / `_validate_trigger_action_compat` / `_validate_checking_action_spec` / `_validate_global_speed_limit_curve` / `_strip_none` / `validate_config` 补 **6** 个守阵测试函数(全部落在池内文件 `tests/test_config.py`); **红验 26/26 KILLED**(本 issue 范围内全部字符串键名 + and/or 互换存活变异)。同目标同池带新守阵复跑(`--no-refresh`): 存活 **772 → 653**(**−119**), `no tests` **55 → 36**, 杀死率 **82.77% → 85.66%**。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 10:16

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(本轮主体)

- **目标**: `**/config/*.py`(glob 相对仓库根; 不变)
- **选择池(逐个文件, 跨轮必须一致)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · `process_isolation=forkserver` · `-n 0 --no-cov` · 机器 = WSL2 `Ubuntu-26.04`(8 核)
- **首轮(承接上基线 26-10-08-0902, 池 = 6 文件)**: 变异 **4799** · 杀 **3972** · 存活 **772** · `no tests` **55** · 超时 **0** · 杀死率 **82.77%**
- **本轮复跑(同目标同池 + 6 个新守阵, `--no-refresh`)**: 变异 **4799** · 杀 **4110** · 存活 **653** · `no tests` **36** · 超时 **0** · 杀死率 **85.66%**
  - 耗时: 墙时 **4m20s**(260s) —— 与上一轮同量级
  - 存活清单: `R:/Temp/auto-qb/mutants/26-10-08-1016-config-py-results.txt`(689 行)
  - **存活 −119 / 新增存活 15**(逐 id 对差)。新增存活 15 条见下「口径说明」——**非新洞**, 是 `no tests` → `survived` 的覆盖归类漂移。
- **红验(本 issue 范围)**: 26 条候选(7 函数) → **KILLED 26 / 26**(全覆盖件下逐条 apply → 目标用例变红 → 还原复绿, 源码零残留; 用 `tmp-analysis/redverify_validator_strings.py` 机械执行)

## 口径说明(必读, 防误读新增存活)

- **新增存活 15 条全在 `_validate_expr_condition_spec`(7) 与 `writer._backup`(8)** —— 上一轮它们是 **`no tests`**, 本轮翻成 `survived`。两者都不在本 issue 范围内, 也**不是本轮引入的退化**: 是本轮池内文件 `tests/test_config.py` 内容变化后 mutmut 的**覆盖归类重算**(同一批变异, 状态字段从「无覆盖」变「有覆盖未杀」)。`no tests 55 → 36`(−19)与它同源: 其中 4 条转入 killed、15 条转入 survived。
- **跨轮对比只看同池数字**: 本切片存活 653 与上基线 772 同目标同池, 可比; 换上基线之前的任何轮次不可比(见 [../../pitfalls/testing/mutation-pool-artifact.md](../../pitfalls/testing/mutation-pool-artifact.md))。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2789 passed + 4 skipped, 2 failed, 覆盖率 TOTAL 99%**(16476 语句 / 162 未覆盖 / 5694 分支 / 146 partial; 门槛 98% 达标)
- **2 failed 是存量守卫违规, 与本件无关**: `tests/test_memory_bank.py::test_wording_guard_is_green_on_current_kb` 与 `::test_number_guard_is_green_on_current_kb` —— 违规源在 `memory-bank/activeContext/26-10-08-0713-webui-qb-traffic-head-layout.md:15`(手抄裸 passed 数字, 来源另一会话提交 `0e8d5432`)。已证与本次改动无关(stash 掉本件改动后守卫照样红), 经用户裁定「暂时不用管」。

## 对照判据(后续沿用)

- **跨轮必须同池** —— 本切片的选择池与 [26-10-08-0902](26-10-08-0902-mutants-config.md) 完全一致; 下一轮 config 复跑应得 `≤ 653` 存活。
- **真洞余量仍在**: config 首轮 220 条真洞候选, 本轮只覆盖「键名大小写 + and/or 互换」主题的 26 条(经红验确认 KILLED); 其余主题(schema-surface / writer-tail / loader-defaults / loop-guards / boundary-guards)另有 5 条 issue, 等排期。
- **守阵落点**: 6 个新测试函数全部在池内文件 `tests/test_config.py`, 故复跑必须 `--no-refresh` + 先 `cp` 进镜像(否则被 `git checkout -f` 冲掉 —— 本件第一遍默认刷新复跑即踩此坑, 存活数纹丝不动)。

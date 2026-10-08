# 2782 —— config 包变异审计首轮(含补测复跑)基线

> 摘要: 对 `src/auto_qb/config/` 跑首轮 mutmut 变异审计(池 = 6 个定向测试文件)。首轮 **4799 变异 / 杀 3851 / 存活 893 / no tests 55 / 超时 0**(杀死率 **80.25%**); 逐条 S4 手工确认(把候选变异 apply 回源码, 跑**全套件**看红不红)覆盖 **274** 条 → **54 条假存活**(全套件能杀, 池没选到) + **220 条真洞候选**(全套件仍杀不掉)。按确认结果补 10 个守阵(红验 18/18 全红), 同目标同池复跑: **杀 3972 / 存活 772**(杀死率 **82.77%**, 存活 **−121**, 新增存活 **0**)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 09:02

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(本轮主体)

- **目标**: `**/config/*.py`(glob 相对仓库根; mutmut 回显 `19 files mutated, 109 ignored`)
- **选择池(逐个文件, 跨轮必须一致)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · `process_isolation=forkserver` · `-n 0 --no-cov` · 机器 = WSL2 `Ubuntu-26.04`(8 核)
- **首轮(池=原始 6 文件)**: 变异 **4799** · 杀 **3851** · 存活 **893** · `no tests` **55** · 超时 **0** · 杀死率 **80.25%**
  - 耗时: 墙时 **294.4s**(含镜像刷新 / 依赖同步 / 清缓存 / 写配置), 变异阶段 **17.41 变异/s**(≈276s)
  - 存活清单: `R:/Temp/auto-qb/mutants/26-10-08-0742-config-py-results.txt`(948 行)
- **S4 手工确认(全套件下逐条同构变异)**: 覆盖 **274** 条(优先文件全量 + 其余文件的 `continue/break`·边界·`and/or`·语句删除类)
  - **54 条假存活**(全套件可杀 → 池未选到; 集中在 `validate_config` 15 · `_validate_qb_traffic` 10 · `_expr_gate` 6 · `_validate_global_speed_limit_curve` 5 · `_validate_trigger_action_compat` 5)
  - **220 条真洞候选**(全套件仍杀不掉; 分布: writer 74 · sections 45 · schema/__init__ 27 · core 25 · loaders 16 · rules 11 · migrations 10 · curves 9 · site_presets 2 · impact 1)
- **补测(S5)**: 新增 **10** 个测试函数(全部落在池内文件), 逐条**红验 18/18 全红**(apply 同构变异 → 目标测试变红 → 还原复绿)
- **复跑(S6, 同目标同池 + 补测)**: 变异 **4799** · 杀 **3972** · 存活 **772** · `no tests` **55** · 超时 **0** · 杀死率 **82.77%**
  - 耗时: 墙时 **3m46s**(226s), 变异阶段 **22.67 变异/s**
  - 存活清单: `R:/Temp/auto-qb/mutants/26-10-08-0901-config-py-results.txt`(827 行)
  - **存活 −121 / 新增存活 0**(逐 id 对差; 被新守阵杀死者按文件: sections 74 · core 23 · migrations 7 · curves 7 · loaders 6 · writer 3 · impact 1)

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2782 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16476 语句 / 164 未覆盖 / 5694 分支 / 148 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0727](26-10-08-0727-test-mutation-audit-config-plan.md)(2772 passed + 4 skipped / 165 未覆盖 / 149 partial):
  passed **+10**(新增 10 个测试函数) / 未覆盖 **−1** / partial **−1** / 语句与分支 ±0

## 对照判据(后续沿用)

- **跨轮必须同池** —— 本切片的选择池是下一轮 config 复跑的对照点; 换池数字不可比(见 [../../pitfalls/testing/mutation-pool-artifact.md](../../pitfalls/testing/mutation-pool-artifact.md))。
- 下轮 config 复跑应得 `≤ 772` 存活(本切片为单点事实源); 若上升, 先核池与 glob 是否漂移。
- **真洞候选 220 条未逐条补测**(本轮只补了其中被 10 个新守阵覆盖的 121 条所对应的那批)—— 余量按主题入池 `memory-bank/issues/`, 见档案的轮次记录。
- `no tests` 55 条全部在 `validation/rules.py` 的 `_validate_watch_fields`(36)/`_validate_expr_condition_spec`(19) —— 池内 6 个文件不覆盖规则条件校验, 属池边界而非代码缺口。
- 本机环境坑: WSL 里 `$()` 命令替换取错 cwd, `mutants.status` 恒报 `mutmut=no`(不影响 `mutants.run`)—— 见 [../../pitfalls/testing/mutants-wsl-shell.md](../../pitfalls/testing/mutants-wsl-shell.md) 与 issue `26-10-08-0758-bug-mutants-status-wsl`。

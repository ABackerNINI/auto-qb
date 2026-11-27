# 7071 passed, 7 skipped, 1 warning in 165.95s (0:02:45) —— webui/server/auth.py 变异测试审计

> 摘要: webui/server/auth.py 变异测试审计
> 基线时间: 2026-11-28 02:41
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

TOTAL                                                31453  31453     0%
7071 passed, 7 skipped, 1 warning in 165.95s (0:02:45)

`commands run test.full` 于 2026-11-28 在 rebase 后的组合树实测：任务分支 HEAD=`2e147a6b09d51c6fce644a5c4c073ac0d8268cba`，本地 `develop`=`e90267a1898490b9608a065308fa5aa1488fe1f6` 为其祖先。完整原始命令输出保存在 `H:\Temp\auto-qb-mutants\b7-test-full-26-11-28-0238.log`；本轮全绿。

## 变异审计

### 范围与运行环境

- 目标：`src/auto_qb/webui/server/auth.py`；定向池仅 `tests/unit/test_web_auth.py` + `tests/unit/test_web_traffic_stream.py`。
- 工具：mutmut 3.8.1；默认 mirror `/root/auto-qb-tests/mutation/src-auto-qb-webui-server-auth-py`；children=3；timeout multiplier=15；run 使用 `--no-refresh`。
- 机器：Docker testbed `auto-qb-testbed`，Linux WSL2 / x86_64 / 8 vCPU / 可见内存约 11.68 GiB。
- 首轮与复跑的墙时/CPU 耗时：首轮墙时与 CPU 耗时未提供；复跑墙时 48.6 秒、report 1.1 秒，CPU 耗时未提供。

### 首轮、分类与补测

- 首轮（dump `26-11-27-0714`）：215 total / 162 killed / 53 survived，杀死率 75.35%；no tests / timeout / suspicious / segfault 均为 0。
- B4 有效绿基线 suite fingerprint=`7303fae3660e`；47 条候选 47/47 SURVIVED、0 KILLED、0 未判定。分类终态：47 真洞 + 6 严格等价 + 0 假存活。
- B5a/B5b/B5c 三批分别以 14/15/21 条同构红验证通过，47 条真洞全部覆盖；生产源码 SHA-256 始终保持 `c640b5b2802cee5086c2d263fa24cc913f8f783e2fb7854aa4f9f2f48635fd0a`。真洞均在既有测试文件当场补测，无单独 issue；处置记录见[任务档案 R44](../../tasks/26-10-08-test-mutation-audit.md) 的 B4/B5a/B5b/B5c 段与[冻结计划 S5](../../plans/26-11-27-0321-plan-mutation-webui-auth.html)。

### 同池复跑与最终结论

- B6 复跑（dump `26-11-28-0215`）：215 total / 209 killed / 6 survived，杀死率 97.21%；48.6 秒；no tests / timeout / suspicious / segfault / skipped 均为 0。
- 逐 id 对差：新增存活 0、消失存活 47、新增 killed 47、原 killed 回退 0、编号漂移 0；消失的 47 条正是已补测真洞。
- 残留恰为 `_log_reject__mutmut_8`、`_reject_cross_site__mutmut_5/37`、`make_require_token__mutmut_1/77/80` 六条严格等价，无真洞余量。
- 证据：`H:\Temp\auto-qb-mutants\b6-rerun-comparison-2026-11-28.json`、`H:\Temp\auto-qb-mutants\26-11-28-0214-src-auto-qb-webui-server-auth-py-results.txt`、`H:\Temp\auto-qb-mutants\26-11-28-0215-src-auto-qb-webui-server-auth-py-mutants-dump.txt`；临时证据不复制进仓库。
- 结论仅覆盖 `webui/server/auth.py` 单模块；`infra/` 与 `webui/server/` 父包仍待做，不外推整包。

## 本改动面

- B7 在组合树完成全量验证与记录收口：新建本基线切片，更新任务档案、active-context、常驻锚 §07 的 `webui/server/auth.py` 行，以及冻结计划状态与变更记录。
- 最终宿主 `src/` 工作树与索引零 diff，生产源码未改；未改 `tests/`、`config.yml` 或 `auto-qb-data/`。

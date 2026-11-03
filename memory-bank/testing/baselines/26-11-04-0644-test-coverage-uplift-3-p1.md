# 5123 passed + 2 skipped(根) —— 覆盖率第三轮 P1 验收全量基线(ops+hr+transfer+config 家族清偿, 阈值抬 99.3/98.8)

> 摘要: 覆盖率第三轮 P1 验收全量基线(ops+hr+transfer+config 家族清偿, 阈值抬 99.3/98.8)
> 基线时间: 2026-11-04 06:44
**Refs:** memory-bank/plans/26-11-04-0157-plan-test-coverage-uplift-3.html (§04 P1 验收)

## 验收数字

`commands run test.full` 实测(coverage-uplift-3, Windows 并行 + 覆盖率, 新阈值 99.3 下复测):

```text
[ok] test.full (169.5s)
  TOTAL                                                23325     44   7956     74    99%
  5123 passed, 2 skipped in 167.55s (0:02:47)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 169.5s(单次采样, 区间口径见 [../baseline.md](../baseline.md); 本轮 4 次全量采样区间 155.7~169.5s); 覆盖率闸 Windows **99.3**(`tests/conftest.py` 单点, 本轮自 99.0/98.5 抬至 99.3/98.8, 见下)。精确 TOTAL **99.62%**(31163/31281, 语句+分支合并口径)—— 过 P1 验收线 99.55(计划 26-11-04-0157 §04)。

- **缺口单位 118**(miss 44 + partial 74), 对照 P0 验收切片 217(108m + 109p, 分母同为 31281)**净清偿 99**(M8 净额 = 118 − 217 = −99, 为负无新模块入榜)。
- **watchlist(合并覆盖 <95% 单文件)4→3**: 核销 1 个 —— ops_jobs 90→100%(T1a); 存量 3 个滚 P2 —— webui/commands.py 90 / runtime_common 93 / views_episodes 94(均属 T2 范围)。(rules/registry.py 合并 94.96%, term 表整数显示 95%, 与 P0 口径一致不列榜。)
- **豁免行数**(`grep -rn "pragma: no cover" src/` 计数)8, 与基线持平。
- 异常注记: 验收第 1 次全量采样中 `test_webui_static_dom_page_layout.py::test_frontend_config_default_ladder_single_point` 偶发失败(单跑与后续 3 次全量均绿; node 子进程探针偶发, 该文件本轮未动, 不处置如实记)。

## 本改动面

- T1a `a9aac90e`: ops 拆分叶(ops_skip 18→0 / ops_jobs 8→0)+ traffic_monitor 路由 10→0, 全清(`tests/test_ops_skip.py` +9 / `tests/test_ops_misc.py` / `tests/test_web_traffic_monitor.py` +3)。
- T1b `1d261b29`: hr/discovery 14→0 / hr/server 5→0 / service_wave 10→1 / hr/runtime 7→2(3 条到不了防御弧已列名)。
- T1c `3890c6a6`: transfer/orchestrator 10→0 / validation/sections 12→0 / writer 6→0 / loaders 2→0, 全清。
- **阈值抬升(验收动作)**: `tests/conftest.py` `COVERAGE_FLOOR_WIN` 99.0→**99.3** / `COVERAGE_FLOOR_OTHER` 98.5→**98.8**; 抬后 `commands run test.full` 复测全绿(169.5s, 上表)。
- **变异红验(抽 5/43 = 11.6%, 每次只变异一处, `commands run test.one` 定向跑确认变红后 `git checkout -- <产品文件>` 还原并复跑确认回绿)——5/5 全部杀死, 零假绿**:
  1. `core/modules/ops_skip.py::advance_due` 步数预算边界 `stepped >= budget_calls` 放宽为 `>` → `test_advance_due_budget_calls_truncates` 红(实推 2, 断言 1);
  2. `webui/server/routes/traffic_monitor.py::_ready_endpoint` 密钥空守卫 `if not token` 短路 → `test_write_endpoints_token_vanish_race_502` 红;
  3. `hr/service_wave.py` 零行波告警第二道守卫删 `not wave.parse_problem` 半边 → `test_finish_wave_zero_listing_warn_gated_by_parse_problem` 红;
  4. `transfer/orchestrator.py::run_batch` D6 单种子兜底 `except Exception` 收窄为 `except KeyError` → `test_batch_prepare_failure_settles_entry_and_continues` 红;
  5. `config/writer.py::_unmask_targets` 非 dict 条目守卫短路 → `test_unmask_targets_skips_non_dict_and_unnamed_old_entries` 红。
  还原后 `git diff HEAD` 仅 `tests/conftest.py` 阈值 2 行, 产品码零残留; 红验用 `--no-cov` 定向跑(覆盖率闸只归 test.full)。

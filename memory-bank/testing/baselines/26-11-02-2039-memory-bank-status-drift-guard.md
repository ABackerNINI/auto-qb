# 4851 passed + 10 skipped —— 状态漂移扫描器低置信输出收敛(C/D 默认仅计数, --verbose 展开)后全量

> 摘要: 状态漂移扫描器低置信输出收敛(C/D 默认仅计数, --verbose 展开)后全量
> 基线时间: 2026-11-02 20:39
**Refs:** memory-bank/tasks/26-11-01-memory-bank-status-drift-guard.md

## 验收数字

- `commands run test.full` 实测(wrapper 墙 207.2s, 2026-11-02 20:39, Windows 本机):
  - 汇总行: `4851 passed, 10 skipped, 3 warnings in 197.67s (0:03:17)`
  - TOTAL 表: `TOTAL  22521  152  7726  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: 通过(要求 99.0%, 实测 99.01%)
- **首跑红及处置**: 首跑 `1 failed, 4850 passed, 10 skipped` 红在 `test_gen_all_check_is_green` ——
  kb.wrap 改了档案但未重建生成物, `memory-bank/tasks/attachments/_archive.md` 漂移;
  `commands run kb.index` 重建 23 个生成物后复跑全绿(上方数字)。
- **定向测试**: `pytest tests/test_memory_bank.py -k drift -v` → 9 passed(含本轮改的三条)。

## 本改动面

- `.agents/skills/memory-bank/scripts/check_status_drift.py`: `_print_tier()` 加 `summary_only` 参数,
  C/D 两档默认只打一行 `== <tier>: N (--verbose to unfold per-row detail) ==`; 新增 CLI
  `--verbose` 才逐条展开; Tier A/B/anomalies 高置信路径与退出码零改动; 模块 docstring 的
  四输出层/Usage/测试计划同步。
- `.agents/skills/memory-bank/scripts/wrap_session.py`: 尾部 C/D 清单不再逐条 `print(row)`,
  改单行 `[<label>] N 条 (--verbose 展开详情)`(空档仍打「无」); 硬拦提示行不变。
- `tests/test_memory_bank.py`: `_drift_run` 支持透传 `extra_args`; 三条守卫改/扩断言 ——
  `test_status_drift_gate_c_never_fails` / `test_status_drift_gate_d_exemptions` 默认模式断言
  只出 summary 行且文件名/条目标签不出现、`--verbose` 断言逐条仍可展开;
  `test_wrap_reports_status_drift_lists` 软漂移段改为断言 summary 行且不展开条目。
- `memory-bank/tasks/26-11-01-memory-bank-status-drift-guard.md`: 子任务表补 T6、进度日志补 R1。
- 真实扫描实测(裸跑): `C list: 1 (--verbose …)` / `D list: 46 (--verbose …)` 两行,硬拦档空;
  旧形态为 47 行逐条展开。
- **不改产品 src/**、不碰 `config.yml` / `auto-qb-data/`。

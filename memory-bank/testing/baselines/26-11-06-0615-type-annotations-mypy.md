# 5467 passed + 2 skipped —— issue 26-11-06-0247 修复: _slot_agg_obs 注解改 4 元组 + call-arg 豁免递减一格

> 摘要: issue 26-11-06-0247 修复: _slot_agg_obs 注解改 4 元组 + call-arg 豁免递减一格
> 基线时间: 2026-11-06 06:15
**Refs:** memory-bank/issues/26-11-06-0247-refactor-slot-agg-obs-tuple-drift.html

## 验收数字

`commands run test.full` 汇总行(测于本轮工作树, 分支 develop, 基线 13f3def0):

- 5467 passed, 2 skipped, 1 warning in 180.90s
- coverage: 99%(TOTAL 24538 stmts / 57 miss / 8396 branch / 36 partial; 覆盖率闸 99.5 已达, 实测 99.71%)

**mypy 面**(`commands run dev.typecheck`):

- 退出码 0: `Success: no issues found in 195 source files`(豁免面外全绿)
- 豁免面(ignore_errors): 2 模式 —— `auto_qb.tray.*`、`auto_qb.rules.expr.env`(未动)
- 豁免面(disable_error_code): 16 个 override 块共 **54** 个错误码条目, 按模块×错误码展开 **154** 对
  (上一基线 26-11-06-0243 为 55 条 / 157 对; 本轮 `core.modules.*` 块摘除 `call-arg`, 递减 1 条 / 3 对)
- 收紧面(disallow_untyped_defs): 8 模式(未动)
- 守阵: `tests/test_mypy_allowlist_guard.py` 冻结清单同步撤下该码, 10 passed

## 本改动面

- `src/auto_qb/core/modules/traffic_sample_agg.py:511`: `_slot_agg_obs` 返回注解 `Optional[Tuple[int, int]]` → `Optional[Tuple[int, int, int, int]]`(与实际 4 元组契约对齐; `agg_totals` 形参注解经核对无漂移, 不动)
- `pyproject.toml`: ③ 号 override(`core.modules.*` + hr service 两模块)摘除 `call-arg`, 注释留摘除理由与 issue 编号
- `tests/test_mypy_allowlist_guard.py`: 冻结清单 `_FROZEN_DISABLE_GROUPS` 同步撤下 `call-arg`(冻结面不撤则加回不触发摩擦)
- 运行期零行为改动 —— 两条返回路径本就产 4 元组, 本轮只改注解与豁免面

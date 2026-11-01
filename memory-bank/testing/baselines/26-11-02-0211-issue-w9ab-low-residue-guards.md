# 4805 passed + 2 skipped —— W9a/W9b low-residue 变异守阵强化后的全量基线

> 摘要: W9a/W9b low-residue 变异守阵强化后的全量基线
> 基线时间: 2026-11-02 02:11
**Refs:** memory-bank/issues/26-11-01-1711-test-core-w9a-mutation-low-residue.html, memory-bank/issues/26-11-01-2024-test-core-w9b-mutation-low-residue.html

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 测于含本轮守阵的**未提交工作树**(HEAD `bd6c8a32` + 本轮改动: `tests/test_speed_curve.py` / `tests/test_ops.py` / `tests/test_grouping.py` 及知识库回写件)
- `commands run test.full` 实测(2026-11-02, Windows 本机):
  - 汇总行: `4805 passed, 2 skipped in 156.70s (0:02:36)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- 定向守护: `commands run test.one -- tests/test_speed_curve.py tests/test_ops.py tests/test_grouping.py` **233 passed + 1 skipped**
- 形态级手搓红验(`tmp-analysis/issue-w9ab-residue/redverify.py`, gitignored, 非变异工具全轮): **26/26** 条同构变异态使新守阵变红(逐条锚点唯一校验; 全程原字节还原, `git status` 确认 `src/` 零改动)
- **环境 / 工具**: Windows 本机(win32) · Python 3.13 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **口径注记**: 未跑 mutmut / gremlins 复跑 —— 因本 clone 无 W9a/W9b 逐 id 产物且全轮成本过高(工具链全轮被判定超出本 issue 范围)。故本轮**不声称任何具体变异 id 被杀死/存活数下降**; 手搓红验只证明"这些形态若出现守阵会红"。

## 本改动面

- `tests/test_speed_curve.py`: 强化 4 条既有守阵 —— ①`test_traffic_view_manual_reason_on_odd_kib` 双方向 + reasons 完整键面/文案 pin; ②`test_speed_curve_format_helpers` 补 `1.25GiB` 两位小数、`1023B`、`99D/100D` 边界、`1KiB/s`; ③`test_traffic_view_stale_when_dat_missing_or_empty` 补 reasons 键面/dir/文案前缀与 dat_empty 完整字典; ④`test_speed_curve_readback_failure_degrades_actual` 补 read_failed 完整键面与文案; 另把手动提醒周期用例改为**恰好整周期**触发(原写法"越过"周期, 对 `>=`→`>` 不敏感)。
- `tests/test_ops.py`: `test_guard_skip_readd_args_pin` 给 FakeTorrent 显式设 `up_limit`/`dl_limit`/`ratio_limit`/`seeding_time_limit` 非默认值并断言原样回传(重加属性丢失簇)。
- `tests/test_grouping.py`: `test_guard_content_root_*` 补反斜杠归一、首尾斜杠剥离、空文件名段过滤、`== 1` 边界与首/末段区分; `test_guard_within_scope_contract` 补空 scope 守卫。
- 零 `src/` 改动; `config.yml` / `auto-qb-data/` 红线未触碰。

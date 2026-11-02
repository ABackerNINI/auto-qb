# 4834 passed + 10 skipped(根) —— 端口单点 _test_ports 收敛后全量

> 摘要: 端口单点 _test_ports 收敛后全量
> 基线时间: 2026-11-02 09:43
**Refs:** memory-bank/plans/26-11-02-0657-plan-testing-tmpdir-bootstrap.html

## 验收数字

- **目标**: 全量 pytest, 测于端口单点 `_test_ports` 收敛(5 处 `_free_port` 复制改导入)+ 重试守卫后的工作树
- `commands run test.full` 实测(wrapper 墙 234.4s, 2026-11-02 09:42, Windows 本机):
  - 汇总行: `4834 passed, 10 skipped, 3 warnings in 229.14s (0:03:49)`
  - TOTAL 表: `TOTAL  22521  152  7726  135  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: 通过(要求 99.0%, 实测 99.00%)
- **口径注记**: 相对上基线 4830 → 4834, 增量 4 条 = 新增 `tests/test_free_port.py`(端口防散落/重试/响亮失败);
  无红无环境性抖动, 一轮直接全绿。

## 本改动面

- `tests/_test_ports.py`(新): 端口单点 `free_port` —— 至多取 3 个候选 + 逐个回绑自验,
  三抢不中 RuntimeError 响亮失败(承认 bind(0) TOCTOU 不可消除, 只压窗口)。
- `tests/test_free_port.py`(新): 4 条守卫(散落检测/返回即可绑/占住候选重试避开/耗尽响亮失败)。
- 5 处 `def _free_port` 复制删除, 改 `from _test_ports import free_port as _free_port`:
  test_hr_discovery / test_hr_server / test_hr_runtime / test_web_views_reload / test_web_auth。
- 计划 `26-11-02-0657`: 02.7 节标记已实施(harness/e2e 侧核实 E2E_PORT 注入口子已存在, 零代码改动)、
  04 节改动清单补 3 行、09 节补第 6 步实测证据、变更记录 R3。
- **零 src/ 改动**; config.yml / 生产端口契约未触碰。

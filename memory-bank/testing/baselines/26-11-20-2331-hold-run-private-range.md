# 6562 —— hold_run 私用段随机基址(issue 26-11-20-0320 修复)收尾全量基线

> 摘要: hold_run 私用段随机基址(issue 26-11-20-0320 修复)收尾全量基线
> 基线时间: 2026-11-21 00:08
**Refs:** memory-bank/issues/26-11-20-0320-test-hr-discovery-port-bind-flake.html

## 验收数字

TOTAL                                                29262     65  10428     75    99%
6562 passed, 6 skipped, 8 warnings in 195.05s (0:03:15)

`commands run test.full` 实测(2026-11-21 00:08, 覆盖率 99% 达标, 全绿)。初测 2026-11-20 23:31 为 6559P, 评审修复轮新增 3 守阵用例后重测刷新为上数。

## 本改动面

- `tests/_test_ports.py`: `hold_run` 基址脱离 bind(0) —— 改私用段随机数(新常量 `HOLD_RUN_PORT_LO/HI` = 21000-31000, 单点), 整段逐位真绑自验+失败整段丢弃重画随机基址结构不变, RETRIES=3/无 sleep 不变; 模块 docstring 与 RETRIES 注释同步; 新增 `import random`
- `tests/test_free_port.py`: `test_hold_run_returns_bindable_run` 加钉面「基址必须落私用段」(回潮 bind(0) 即红); `test_hold_run_discards_run_whose_offset_is_refused` 纯合成 socket 改写(取号 socket 消失后尝试边界改由 close 事件判定, 注入点只看「本尝试第几次 bind」, 与真实端口状态解耦); docstring 测试计划同步; 评审修复轮新增 3 守阵用例 —— `test_hold_run_width_guard_rejects_oversized_count`(超宽 guard 零网络钉面)/`test_hold_run_redraws_with_new_random_base`(重画必须重新抽取随机基址)/`test_hold_run_exhausted_retries_raises`(耗尽路径与 free_port 耗尽钉面对称)
- 验证链: 隔离两文件 52P(41+11, 含初版守卫状态机初值 bug 当场修复); `test_hr_discovery.py` 文件级 `-n 8` 连跑 3 轮 41P×3; `test_free_port.py -n 8` 11P; `test.full` 6562P/99%
- 收尾: 新坑档 `pitfalls/testing/hold-run-ephemeral-frontier.md`(bind(0) 前沿邻接, 与 consecutive-port-run 互为上下半场); issue 26-11-20-0320 修复后补充+翻 Done
- 未做: `test.linux` 一轮(docker CLI 本会话不可达, 记待办; Linux 侧动态段下界 32768 > 31000 由默认值推定, 待真机核实)

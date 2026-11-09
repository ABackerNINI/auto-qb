# 5907 passed + 2 skipped —— 齐平后最终组合树全绿(issue 0456 修复 + 两处闸门清障)

> 摘要: 齐平后最终组合树全绿(issue 0456 修复 + 两处闸门清障)
> 基线时间: 2026-11-10 07:38

## 验收数字

```text
TOTAL                                                26246     48   9146     58    99%
5907 passed, 2 skipped in 137.62s (0:02:17)
```

(实测时点: HEAD 436303b0 + 本轮工作树改动, `commands run test.full` 2026-11-10 07:38; 全绿, 覆盖率 99%。本片测在开工两轮快进(21 笔 + 1 笔 + 15 笔)齐平后的最终组合树, 是本次交付的唯一事实源; 06:17 那条切片是远端 15 笔合入前的中间态测量, 保留作历史快照)

## 本改动面

- **主体修复**: `tests/test_free_port.py::test_hold_run_discards_run_whose_offset_is_refused` 由「真实 socket 代理 + 单点注入 10013」改为纯合成 socket(零真实 bind), 断言加强; 文件头 docstring 测试计划清单同步; `tests/_test_ports.py::hold_run` 零改动。
- **用户授权的闸门清障(范围外两处, 显式扩范围)**: 远端 15 笔合入后 `test.quick`/`test.full` 撞见两条稳定红, 均来自另一个计划刚推的 `tests-real` 文件、与本轮修复无关 —— ① `tests-real/rm04_relocate/test_rm04_relocate_window.py` 三处 `schema_version: 6` 改 7(产品 config 现行 v7); ② `tests-real/tools/daemon_window_wrapper.py` docstring 里 ① ② 两个 circled 符号换 `[1]` `[2]`(ASCII 闸门冻结基线为 0)。两处守卫单跑 15 passed; 提交闸门按 `.my-commit-flow.toml` 对本次改过的 py 统一跑 `dev.fmt`(yapf), 该文件随之带出三处纯格式重排, 属闸门强制归一, 无语义变化。
- **记录面**: issue 26-11-10-0456 翻 Done(补复验 / 修复后补充 / kicker); 坑档 `pitfalls/testing/consecutive-port-run.md` 复发 +1 并补守阵用例本体口径(摘要/触发词同步后 `kb.index` 重建); 会话切片 26-11-10-0618 记 R0-R2。
- **验证**: 确定性红验(修复前模拟并行抢口 ⇒ 判红) + 修复后双探针(所有真实 bind 一律拒绝仍绿且真实 bind 次数 0 / 把 hold_run 改坏 ⇒ 判红) + 单文件守阵全绿(副作用台账越界 0) + `test.quick` 全量并发全绿 + `test.full` 全绿; `kb.check` 与 HTML 标签平衡机检全绿。真机不适用(纯桩可验)。

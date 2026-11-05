# 4355 passed + 10 skipped —— 提交闸门按改动收窄落地后的全量基线

> 摘要: 提交闸门按改动收窄落地后的全量基线
> 基线时间: 2026-11-01 05:41
**Refs:**

## 验收数字

```text
TOTAL                                                21823    163   7398    127    99%
4355 passed, 10 skipped in 173.90s (0:02:53)
```

- 口径: `commands run test.full`（uv run pytest tests -q，带覆盖率；pytest.ini 默认 -n 4），2026-11-01 05:41 本机实测。
- 同日 test.quick（-n 8, --no-cov）：4355 passed, 10 skipped in 153.88s；test.pkg（.commands + 引擎）：206 passed in 112.18s。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- 方案 A：`scripts/check_command_drift.py` 加 `--files`/`--full` 模式（scan(only=) 收窄读取面）+ 闸门 run 一拆三条；新增 `tests/test_command_drift.py`。
- 方案 B：`.commands/my-commit-flow/scripts/_pipeline.py::run_gates` 两阶段并发化（`GATE_WORKERS = 4`）；`test_pipeline.py` 加并发语义用例 + `GateScopingConfigTest`。
- 方案 C：新增 `.commands/test/scripts/pkg_scoped.py` + task `test.pkg.scoped`；闸门 run 一拆两条；自测 `test_pkg_scoped.py`。
- 方案 D：`scripts/check_context_caps.py` 加 `--files`（硬规定语义不变）；`check_kb_structure.check_caps` 加可选 `only` 参数；闸门 run 一拆三条。
- 无 src/ 改动 —— 全部在机检脚本/闸门配置/测试层。

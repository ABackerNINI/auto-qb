# 7037 passed + 7 skipped, TOTAL 31424/0% —— playwright 注释失效引用修复全量基线

> 摘要: playwright 注释失效引用修复全量基线
> 基线时间: 2026-11-27 02:35

## 验收数字

`commands run test.full` 首轮实测（Windows，rc=0，202.12s；2026-11-27 02:02），同环境 `-ra` 复跑（rc=0，169.17s；2026-11-27 02:35）。两次通过、跳过与覆盖一致；warning 首轮 2 条、复跑 1 条，取复跑为准：

```
TOTAL                                                31424  31424     0%
7037 passed, 7 skipped, 1 warning in 169.17s (0:02:49)
```

## 与上一基线对账

- 上一基线 `26-11-27-0125` 为 7036 passed / 6 skipped / 1 warning；本轮为 7037 / 7 / 1。
- 多出的 2 条 passed 来自 `0c2ab2ec`（kb.nav 拉取三态反馈）新增的 `tests/unit/test_kb_nav_interaction.py::test_do_pull_three_states_distinct` 与 `tests/unit/test_kb_nav_server.py::test_pull_ff_only_up_to_date_kind`。重构前快照 `03de1297` 收集 7042 条，当前收集 7044 条；归一化路径后的节点名差集只有这两条，非本注释修复引入。
- 多出的 1 条 skipped 是 `tests/unit/test_commands_engine.py::test_local_codepage_ignores_utf8_mode`：当前 pytest 进程 `sys.flags.utf8_mode=0`，按用例条件跳过；`PYTHONUTF8=1` 隔离复跑为 passed。
- 唯一可复现 warning 仍是 `test_platform_tolerance_guards.py::test_repo_text_subprocess_calls_pin_utf8` 的既有 `SyntaxWarning: invalid escape sequence '\P'`；首轮多出的第 2 条 warning 未在复跑中出现。

## 本改动面

- `playwright.config.mjs` 的 CommonJS 说明改为指向实际存在的 `tests/unit/test_extension_proxy_manifest.py::test_js_syntax_passes_node_check`；保留不能修改根 `package.json` 的 `"type": "module"` 的结论，纯注释修正、零行为变化。
- 问题单 `memory-bank/issues/26-11-27-0134-docs-playwright-config-stale-ref.html` 回写实际修法与验证结果并翻 Done。
- 定向验证：`node --check playwright.config.mjs` 通过；扩展 manifest 守阵 7 passed；`git diff --check` 通过。
- 纯注释与文档事实修正，不触发真机轨；既有未跟踪 `tests-real/` 目录保持原样，未纳入本轮改动。

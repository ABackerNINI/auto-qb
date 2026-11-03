# 4994 passed + 10 skipped(根) —— 四条文档漂移 issue 认领修复全量基线

> 摘要: 四条文档漂移 issue 认领修复全量基线
> 基线时间: 2026-11-03 21:45
**Refs:** memory-bank/issues/26-11-03-1209-docs-docs-tests-real-env2-comment-drift.html, memory-bank/issues/26-11-03-1208-docs-docs-configuration-transfer-missing.html, memory-bank/issues/26-11-03-1208-docs-docs-context7-version-path-drift.html, memory-bank/issues/26-11-03-1208-docs-docs-readme-test-scale-drift.html

## 验收数字

```text
TOTAL                                                23292    185   7948    158    99%
4994 passed, 10 skipped, 3 warnings in 190.59s (0:03:10)
```

- `commands run test.full` 引擎口径耗时 193.6s（含环境自检）。
- 定向：`commands run test.one -- tests/test_config_schema.py tests/test_real_machine_safety.py tests/test_docs_forms.py` = 73 passed。
- `10 skipped` 为本 clone 环境下的跳过集，非本轮文档改动引入。

## 本改动面

- `tests-real/lib/env_registry.py`：仅修注释（环境2 `bt_listen` 已实测回填，删「尚未实测」表述）。
- `docs/configuration.md`：`web:` 段补注释态 `transfer:` 示例（targets 全键，与 `keys.md` / `models.py` 对齐）。
- `docs/context7/README.md`：索引改「快照版本 / 当前锁定」双列并逐行对齐 `uv.lock`；两处模块路径改指 `core/qbclient.py`、`webui/server/`。
- `README.md`：删除手抄测试规模数字，改为引用 `commands run kb.baseline`。
- 四条 docs issue：状态 Done + 状态日志 + 修复后补充；`doc-refs` 与本切片双向补链。
- 生成物：`memory-bank/issues/_index.md`、`memory-bank/issues/attachments/_archive.md` 随 `kb.index` 重排。

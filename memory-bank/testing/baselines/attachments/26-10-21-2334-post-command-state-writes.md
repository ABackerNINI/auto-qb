# 3990 passed + 2 skipped —— S1 守阵扩容: 全库 AST 扫描 + apply_delta 调用点白名单

> 摘要: S1 守阵扩容: 全库 AST 扫描 + apply_delta 调用点白名单
> 基线时间: 2026-10-21 23:34
**Refs:** memory-bank/plans/26-10-21-2323-plan-command-writeback-boundary.html

## 验收数字

```text
TOTAL                                                20992      97   7090      99    99%
3990 passed, 2 skipped in 131.60s (0:02:11)
```

口径注记:

- pytest 全量口径(含覆盖率门槛 99%), 在 S1(守阵扩容)改动后的工作树上实测。
- 本轮新增 1 例红验用例(`test_state_write_scanner_detects_synthetic_writes`), 守阵本体改为 AST 全库扫描。
- 红验实测: 向 `ops_mod.py` 注入 `tor.apply_delta(live[0])` 后守阵立刻变红并指出 `ops_mod.py:1299`; 还原后复绿。
- 裸数字只写本切片一处; 档案与计划正文引用而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `tests/test_sync.py`: `test_no_synthetic_state_write_site` 扫描面从 `qbapi.py`/`store.py` 扩到 `src/auto_qb/**`; 检测方式从正则改为 AST(消除 docstring 假阳性); 判据从三条扩到四条(新增 `apply_delta` 调用点白名单: 只允许 `torrents/store.py` 与 `torrents/record.py`); 白名单收敛为 `core/qbmanager.py`(2 处) 与 `core/taskqueue.py`(6 处), 每条带理由且断言理由非空、文件存在。
- `tests/test_sync.py`: 新增 `test_state_write_scanner_detects_synthetic_writes` —— 三种 `.state` 形态 + `apply_delta` 调用各自可检出, docstring 同形文本不命中。
- 无生产代码改动。

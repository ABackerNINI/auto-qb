# 22531 —— 4914 passed + 2 skipped(根) —— R3 工具/脚本/扩展 move-only 拆分后全量基线

> 摘要: 4914 passed + 2 skipped(根) —— R3 工具/脚本/扩展 move-only 拆分后全量基线
> 基线时间: 2026-11-03 03:26
**Refs:** memory-bank/tasks/26-11-03-test-big-file-split.md, memory-bank/plans/26-11-02-2342-plan-big-file-split.html

## 验收数字

`commands run test.full` 实测(同步远端 `develop` 后的工作树, Windows 并行 + 覆盖率):

```text
TOTAL                                                22531    134   7732    128    99%
4914 passed, 2 skipped, 3 warnings in 137.66s (0:02:17)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `scripts/sim_qb.py` 2077 → 166 行入口 + 4 模块(`sim_qb_core.py` 418 / `sim_qb_model.py` 897 / `sim_qb_server.py` 298 / `sim_qb_cli.py` 367), 入口保留 `main`/`self_test` 与全量兼容 re-export。
- `scripts/qb_capture.py` 1559 → 959 行入口 + 2 模块(`qb_capture_core.py` 542 / `qb_capture_cli.py` 122); 入口保留 `Capture`/`main`, sibling import 加 `sys.path` 兜底。
- `extensions/hr-fetch-proxy/background.js` 1427 → 642 行入口 + `background-log.js` 219 + `background-support.js` 574; 仍是唯一 MV3 service worker 入口, `importScripts(log → support)` 组合, manifest 零改动。
- `tools/global-traffic-monitor/tests/test_server.py` 1274 → 552 + `server_support.py` 117 + `test_server_autostart.py` 398 + `test_server_routes.py` 287; 61 个 `test_` 全部保留。
- 测试引用最小同步: `tests/test_sim_corpus.py` 的 monkeypatch 目标移到 `sim_qb_core`; 扩展守阵按 service worker 加载顺序拼接 bundle(`tests/extension_proxy_support.py` + 3 个 `test_extension_proxy_*`), 断言语义未改。
- 3 个暂缓文件(`options.js` / `test_storage.py` / `ui_harness.py`)零改动; 本轮无新桶 >1000 行(最大 897), 计划 §07 排期清单无新增。

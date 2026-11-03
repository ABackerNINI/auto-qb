# 5002 passed + 2 skipped —— 全量 e2e 站点告警顺序污染修复收尾基线

> 摘要: 全量 e2e 站点告警顺序污染修复收尾基线
> 基线时间: 2026-11-03 13:18
**Refs:** memory-bank/issues/26-11-03-1135-test-e2e-site-alerts-order-pollution.html

## 验收数字

```text
TOTAL                                                23292    167   7948    152    99%
5002 passed, 2 skipped, 3 warnings in 138.80s (0:02:18)
```

- `commands run test.full` 引擎口径耗时 185.0s（含环境自检）；Python 侧与修前一致，桩脚本改动未影响 pytest。
- e2e（本轮主验收，非 pytest 口径）：全量 `commands run dev.e2e` 440 例 =
  **422 passed / 18 skipped / 0 failed**，总时长 **18.4m**（`dev.e2e` 引擎预算 2700s 未触发掐断）；
  隔离 `e2e/site-alerts.spec.mjs` = 8 passed；三件套组合（search-auto-refresh +
  search-uncovered-no-duplicate + site-alerts）= 26 passed。

## 本改动面

- `scripts/ui_harness.py`：`main()` 在 `seed_store()` + `client.torrents` 灌入后补一次
  `mgr.store.apply_sync(mgr.api)` 对齐增量同步游标（`rid`），并把 `_inject_site_alerts()` 移到其后 ——
  修 issue 26-11-03-1135 的桩侧共享状态泄漏（首个 add/remove 探针触发 full_round 重匹配
  `tracker_conf`，把注入的 no_site_conf 行改回 HHan）。
- `memory-bank/issues/26-11-03-1135-…html`：根因（已证实/已排除）/实际修法/复验/验证数字补齐，状态 Done。
- `memory-bank/pitfalls/testing/stub-bypass-apply.md`：新增「桩直写 store 不推进同步游标 → 首个探针
  触发 full_round 重写注入态」一条。
- `memory-bank/issues/_index.md`、`memory-bank/issues/attachments/_archive.md`：生成物随状态重排。

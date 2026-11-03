# 5002 passed + 2 skipped —— CI Playwright BASE_URL 收集崩溃修复收尾基线

> 摘要: CI Playwright 收集期 `BASE_URL` 导出缺失修复(改调用方用 `baseUrl()`) + e2e 回潮守阵收尾基线
> 基线时间: 2026-11-03 10:53
**Refs:** memory-bank/pitfalls/testing/smoke.md, memory-bank/tasks/26-11-03-webui-search-uncovered-dedup.md, memory-bank/issues/26-11-03-1035-test-e2e-harness-baseurl-import.html

## 验收数字

`commands run test.full` 实测(提交前于 90e86b16 复跑, 套件 188.9s):

```text
TOTAL                                                23292    167    7948    152    99%
5002 passed, 2 skipped, 3 warnings in 165.94s (0:02:45)
```

口径注记:
- 全量 1 轮; 3 条 warning 为既有存量, 2 skipped 为环境跳过用例。
- e2e 收集: `commands run dev.e2e -- --list` 通过 —— 48 个 spec / 440 用例。
- 定向 e2e(`commands run dev.e2e -- e2e/search-uncovered-no-duplicate.spec.mjs e2e/search-auto-refresh.spec.mjs`):
  18/18 全绿(prism/atlas/flux 覆盖皆过)。
- e2e 全量(`commands run dev.e2e` 等价的全量 playwright 运行, 本机 CI=true 故失败重试 1 次, 实测于 4a9e233c): 416 passed / 6 failed (21.9m) ——
  6 条全为 `site-alerts.spec.mjs` 在**全量顺序**下红、**单文件隔离跑 8/8 全绿**(既有顺序污染红, 与本改动无关)。
- `commands run dev.e2e` 原 1200s 引擎上限不够(全量约 21.9m): 本基线存续期间已抬到 2700s(≈2× 实测),
  `.github/workflows/playwright.yml` 的 job `timeout-minutes` 同轮 20→40(用户 2026-11-03 拍板)。

## 本改动面

- `e2e/search-uncovered-no-duplicate.spec.mjs`: `import { BASE_URL }` → `import { baseUrl }`, 4 处
  `${BASE_URL}/...` → `${baseUrl()}/...`(add_torrent 1 处 + goto 1 处 + remove_torrent 2 处), 不改 harness。
- `tests/test_port_zero_guards.py`: 新增 `test_e2e_modules_use_lazy_base_url` —— 扫 `e2e/` 全量 `.mjs`,
  断言 `BASE_URL` 零命中, 补住原守阵只查 `harness.mjs` 定义侧、拦不住调用方回潮的缺口; 同步头部「测试计划」。
- `memory-bank/pitfalls/testing/smoke.md`: 新增该坑的触发/判别/处置条目并扩触发词。
- 超时同源抬高(用户拍板): `.commands/dev/config.toml` `dev.e2e` `timeout = 1200 → 2700`,
  `.github/workflows/playwright.yml` job `timeout-minutes = 20 → 40`; 全仓仅这两处该量级上限。
- `memory-bank/issues/26-11-03-1135-test-e2e-site-alerts-order-pollution.html`: site-alerts 全量顺序污染入池(test/standard/Open)。
- 未改产品代码 / `config.yml` / `auto-qb-data/`; 未 commit/push。

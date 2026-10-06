# 78 —— Playwright e2e 全量矩阵验收轮(S7 收尾: 旧冒烟脚本退役, e2e 单点终态)

> 摘要: 迁移计划 [26-10-06-0708](../../plans/26-10-06-0708-plan-playwright-e2e.html) S7 批收尾基线。
> S0–S7a 已实施完成(删旧脚本 = `68f6e033`), 本轮 = S7b 全量矩阵验收(§5.2 六行, 串行人跑,
> 每轮独立起桩) + 知识库回写 + 计划收口。默认轮 collected **88 = 78 passed + 10 skipped**(skip 全部为
> 模式门控组, 消息带当前 env 值, 见 `e2e/lib/mode.mjs` requireMode)。
> 基线时间: 2026-10-06 14:25

**Refs:** memory-bank/plans/26-10-06-0708-plan-playwright-e2e.html, memory-bank/activeContext/26-10-06-0508-playwright-e2e.md, memory-bank/issues/26-10-06-0458-refactor-e2e-migrate-ui-smoke.html

- 分支: **playwright-e2e-migration** @ **68f6e033**(S7a; 已 rebase 并入 develop; 工作树含 S7b 文档回写未提交)
- 命令: `commands run dev.e2e` + env(hang 轮例外见下); 桩服务由 webServer 托管(8137,
  `reuseExistingServer: false`), 每轮收尾后 netstat 复核**端口零残留**(7/7 轮干净,
  `e2e/global-teardown.mjs` 兜底每轮都打出「强制结束监听 8137 的进程树」)。

## 矩阵六轮实测 (2026-10-06 13:56–14:31, 本机; ③ 行为 14:29 收口复跑值)

| 轮次(env) | 结果 | skipped | 时长 | 结论 |
|---|---|---|---|---|
| ① 默认 ok/on/on/300 | **78 passed** | 10 | 164s (2.7m) | 全绿; harness 首行 `种子=300 组=150 命令回执=ok` |
| ② `E2E_CMD_RESULT=error` | **78 passed** | 10 | 163s | 全绿; 回执=error, 回滚族绿, 门控外 skip 消息带 env 值 |
| ③ `E2E_CMD_RESULT=hang` | **64 passed** | 24 | **156s** | **0 failed**(S7b 收口后复跑, 经 commands 引擎 rc=0); hang 窗口三连(P0-3 hang: pending 立现 → 2500~6000ms 兜底清除 → 落回原状态)双皮肤全绿 —— 本轮验收主判据达成。W3 确认链 ×2 皮肤门控 skip(+2, 见「计划外发现」#1 已处置) |
| ④ `E2E_SKIP_CHECK=off` | **70 passed** | 18 | 150s | fail-closed 精简组绿, skip-check on 全套组 skip(+8) |
| ⑤ `E2E_HR_SCENE=empty` | **74 passed** | 14 | 101s | hr-history 组整组 skip(+4), 消息可读 |
| ⑤' `E2E_HR_SCENE=off` | **74 passed** | 14 | 100s | 同上 |
| ⑥ `E2E_TORRENTS=3000` (views.spec 抽验) | **18 passed** | 0 | 41s | 轮询分档断言按量取档正确(3000 → 2000ms 档), 桩与断言同源 env 不漂 |

- 每轮 skipped 数与门控组清点一致(基础 10 + 各模式专属组), 无静默少跑(计划 §6 R2 判据)。
- ⚠ hang 轮执行口径(收口前): `commands run dev.e2e` 的任务 timeout=180s 撑不住 hang 轮墙钟
  (引擎到点强杀 rc=1), 曾以该 task 的展开命令直跑绕过引擎超时做验证(不另立口径)。
  **已处置**(S7b 收口, 见「计划外发现」#2): timeout 放宽 360s 后经 commands 引擎复跑正常
  (rc=0 / 156s), 六行命令口径恢复全部走 `commands run dev.e2e`。

## pytest 层 (零波动)

- 命令: `commands run test.full`(Windows)
- **实测**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**, 单次采样 **29.62s**(wrapper 30.2s);
  语句 15823 / 未覆盖 163 / 分支 5472 / partial 143 —— 与上一条基线
  [26-10-06-0731](26-10-06-0731-plan-playwright-e2e.md) **逐项持平**(纯测试轨 + 文档轮, 零 Python 改动)。

## 迁移映射概要 (旧块 → spec 文件; 逐断言映射表在各 spec 头注释)

| 旧块(静态断言) | 承接 spec |
|---|---|
| A 渲染健康/视图/筛选器/轮询分档(≈15, 含 S7a 补迁孤儿断言「设置页刷新保持位置」) | `e2e/views.spec.mjs`(另含原 smoke.spec 的 2 条 @fast) |
| F 追剧 + D·CTX-03 多选(≈19, 存量 flaky 块) | `e2e/multiselect-shows.spec.mjs` |
| C+E 乐观 UI + hang 探针(≈24) | `e2e/optimistic.spec.mjs`(ok/error/hang 三模式门控) |
| D 其余菜单族 + W5-off(≈26) | `e2e/menus.spec.mjs`(on/off 双模式) |
| B 性能埋点(≈6, 阈值逐字保留) | `e2e/perf.spec.mjs` |
| G HR 表③(≈5) | `e2e/hr-history.spec.mjs`(hr-scene 门控) |
| H 列设置守阵 ×5(≈12) | `e2e/column-prefs.spec.mjs` |
| 收尾总检「无 console.error / pageerror」(1) | `e2e/lib/errors.mjs` afterEach 公共检查 |

「每次改前端」门禁口径(随本轮回写进 testing 文档): **`npm run test:e2e:fast`(@fast)绿;
触碰乐观 UI/菜单/列设置加跑对应 spec; 全量矩阵轮收尾/排障串行人跑**(六行命令见
`.commands/dev/config.toml` 的 `dev.e2e` note)。

## 计划外发现 → S7b 收口处置 (2026-10-06 14:35 追加, 两项均已修/调并复跑验证)

1. **`e2e/menus.spec.mjs` W3 跳检确认链不兼容 hang 模式** —— **已修**: 确认按钮
   `:disabled="modal.okDisabled"` 是 S4 跳检预检门控(进框即禁用, 预检回执解锁), hang 模式下预检
   **永不回执** ⇒ 按钮永不解锁 ⇒ `locator.click` 30s 超时(收口前矩阵 hang 轮 2 failed, 双皮肤同签名)。
   处置: 该 test 按 W2 toast「仅 ok 模式」同款口径补 `requireMode(test, { cmdResult: ['ok','error'] })`
   (test 内首行 + 注释 + 头注映射表 L572 行注 + 模式门控段), error 模式预检有回执照常解锁不受影响。
   复跑: hang 轮(经 commands 引擎)**0 failed / 64 passed + 24 skipped / 156s / rc=0 / 端口零残留**。
2. **`dev.e2e` 任务 timeout=180s 偏紧** —— **已调**: `.commands/dev/config.toml` 的 `dev.e2e`
   timeout 180 → **360**, note 首句写明理由(S7 矩阵实测默认轮 164s / hang 轮 219s, 180s 撑不住
   hang 轮)。复跑: hang 轮经 `commands run dev.e2e` 正常完成(rc=0, 156s, 引擎不再强杀)。

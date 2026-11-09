# 5877 —— GitHub CI 四组 e2e 既有红修复后全量

> 摘要: GitHub CI 四组 e2e 既有红修复后全量
> 基线时间: 2026-11-10 01:21

## 验收数字

`env -u TMPDIR -u TEMP -u TMP commands run test.full` 实测(2026-11-10, 208.5s):

```
  TOTAL                                                26152     41   9102     53    99%
  5877 passed, 2 skipped in 205.90s (0:03:25)
```

覆盖率 99%(TOTAL 行), `Required test coverage of 99.5% reached` 由闸门通过反证。数字来源: `commands run test.full` 输出, 未手算/未编造。

## 本改动面

- `e2e/gtm-alert.spec.mjs` — reload 后等服务端告警段落地的 `expect.poll` 显式 `timeout: 20_000`(原默认 5s), 断言仍严格 `toBe(ts)`。
- `e2e/perf.spec.mjs` — W5 注入 `window.__tickT0` / `window.__pollMs = vm.basePollMs()`, 拍数上界由固定 `<=3` 改为 `Math.ceil(elapsed / pollMs) + 1`, 日志带实测窗口与上限。
- `e2e/drawer-general-variants.spec.mjs` — 3 处磁力钮断言改「不得回潮」; `BASE_PATCH` 补 `content_path` / `download_path` / `root_path` 三个非空路径值(对齐 `26-11-08-1621` 条件式 wide); dt02 用例标题同步。
- `e2e/menus.spec.mjs` — 复制族断言三项改两项 + 补「复制 magnet 不得回潮」负向断言。
- `e2e/optimistic.spec.mjs` — BUG-9 从直调已退役 `copyTorrentInfo('magnet')` 的恒真断言改为验 name 两用有真实复制回执。
- `src/auto_qb/webui/static/shared/shortcuts_engine.js` — `_kbScrollRowIntoView` 抽 `reveal()` 并按真实 DOM 矩形校正; `revealWhenRendered(deadline)` 在 1s 时间窗跨帧重试到目标行渲染, 修窗口化重渲晚于 `$nextTick` 时末行被状态栏遮 25~31px; 边界落值仍只取一次。
- `memory-bank/issues/26-11-07-0326-test-ci-smoke-existing-red-backlog.html` — Open → In Progress → Done, 补复验/实际修法/验证数字, 认领链双向补齐。

e2e 侧(不进 pytest 数字): 目标 spec 全绿 —— drawer 4 passed、gtm 2 passed、kbd 6 passed、perf W5 2 passed、menus 2 passed、optimistic 2 passed; 静态守阵 `test_kb_view_band_single_points` 1 passed; 6 个 JS 文件 `node --check` 全过。两分片并行回归共 222 例各有 1 条无关偶发红, 串行单跑分别 2 passed / 6 passed。

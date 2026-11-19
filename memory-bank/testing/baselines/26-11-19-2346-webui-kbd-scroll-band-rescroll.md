# 6486 —— 基线切片 2026-11-19: kbd-scroll-band rescroll 修复后全量

> 摘要: 基线切片 2026-11-19: kbd-scroll-band rescroll 修复后全量
> 基线时间: 2026-11-19 23:46

## 验收数字

`commands run test.full` 实测(2026-11-19 23:43, 173.1s):

```text
TOTAL                                                28915     44  10322     61    99%
6486 passed, 6 skipped, 7 warnings in 173.10s (0:02:53)
```

差值口径: 上一基线 [26-11-19-2152](26-11-19-2152-sort-default-asc-tristate-fix.md) 6480P/6S → 本切片 6486P/6S, +6 passed(远端合流的用户表排序三态守阵等新用例落进来, 非本改动新增; 本改动面 e2e/守阵数字见下「本改动面」)。

## 本改动面

- `src/auto_qb/webui/static/shared/shortcuts_engine.js`: `_kbScrollRowIntoView` 窗口化分支滚动封 `rescroll` + 补正循环每帧幂等重发(26-11-18-0308 根因修复) + 代际令牌 `_kbRevealGen` + 用户滚轮/触摸退避 + deadline 1s→5s。
- `e2e/kbd-scroll-band.spec.mjs`: pollBand 超时 5s→10s(与 settleScroll 双窗一致) + 注释。
- 静态守阵(test_web_shortcuts_engine / cursor / drawer / r4 batteries): 46 passed。
- e2e 验证: kbd-scroll-band 全 spec 6/6; 同形态采样(grep 钉例 ×60 ×3 shard 全并发)修复前 240 例 39 红 → 修复后 180/180 绿。

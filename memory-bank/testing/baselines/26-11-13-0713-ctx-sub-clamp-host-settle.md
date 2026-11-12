# 6101 passed + 2 skipped —— ctx-sub 钳位二次收口批次

> 摘要: 6101 passed + 2 skipped —— test.full 全绿; ctx-sub 钳位二次收口批次(issue 26-11-13-0443)
> 基线时间: 2026-11-13 07:13

## 验收数字

```text
TOTAL                                                27113     65   9480     69    99%
6101 passed, 2 skipped in 210.98s (0:03:30)
```

e2e 面(同批实测): `npm run test:e2e:fast` 356 passed (18.9m); `menus.spec.mjs + ctx-custom.spec.mjs` 36 passed / 6 skipped; 新增「CTX-sub fit 首行场景」红绿双验(旧代码红: 底缘 894 > 893; 修后 2 用例 × 2 皮肤 × 5 轮 20/20 绿)。

## 本改动面

- `src/auto_qb/webui/static/shared/menu.js` —— `openSub` 同步捕获 `ev.currentTarget` 并传 `name` 给量测链; 新增 `_subFitRefit(anchor, name)`(rAF 有界复核 1+3 帧收敛 + 幂等 + name 闸), 驱动既有单次钳位 `_subFitViewport`(本体未动)。
- `e2e/menus.spec.mjs` —— 新增回归测试「CTX-sub fit 首行场景: 二次收口后子面板整盒仍收进视口」(四边收进 + subTop 收敛等待)。
- `memory-bank/pitfalls/web-ui/ctx-sub-clamp-host-settle.md` —— 新坑档(嵌套浮层钳位 vs 宿主二次收口时序 + e2e 读盒时机)。
- `memory-bank/architecture/webui.md` —— 「子面板宽度与视口钳位」行补 `_subFitRefit` 一句。
- `memory-bank/issues/26-11-13-0443-bug-webui-ctx-sub-overflow.html` —— 复验/修复后补充/状态推进。

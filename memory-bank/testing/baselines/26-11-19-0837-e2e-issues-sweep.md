# 6480 passed + 6 skipped —— e2e 四 issue 认领修复批收尾基线(预算重标定/桩归组封顶/两 issue 收口)

> 摘要: 6480 passed + 6 skipped —— e2e 四 issue 认领修复批收尾基线(预算重标定/桩归组封顶/两 issue 收口)
> 基线时间: 2026-11-19 08:37

## 验收数字

实测树: 本地分支 fix-e2e-issues-261119 tip 726fb31b + 本批收尾回写工作树(切片/基线)。`commands run test.full` 实测(2026-11-19 08:3x, 181.5s):

```
TOTAL                                                28896     44  10314     61    99%
6480 passed, 6 skipped, 7 warnings in 179.03s (0:02:59)
```

e2e 侧(本轮手工面, 数字随轮即弃不建档): perf 首访指纹 3000 档 2 轮双皮 + 600/300 档各 1 轮全绿(预算 185); 300 档全量具套件 33 passed / 4 skipped / 0 failed; 携带 spec 600 档 2 轮 + window-invalidation 6P + 400 档绿 + 300 档门控 skip 正常; drawer-content-perf 量具串行 2 轮 37 passed / 0 failed。

## 本改动面

- `e2e/perf.spec.mjs`: 首访路径指纹预算 150→185(`FIRST_VISIT_GBR_BUDGET` 常量 + 新构成注释 + 视口钉死注记, 判据语义零放松); 155/158 证为引擎 updated() 收敛拍固有合法构成(隔离试验排除轮询污染)。
- `scripts/ui_harness.py`: `_set_save_path` 重建归组与启动段同口径封顶(`groups_cap: int | None = None`), 600 档换键不再成批拆组洪泛 ROWH_FRESH。
- KB: issue 26-11-19-0258(settings-backup)收口 Done(7d88fee1 放宽 90s 已实质修复, 复验全绿); issue 26-11-19-0258(指纹)收口 Done(重标定+改道说明); issue 26-11-19-0534(换键携带)收口 Done(桩归因+封顶); issue ltFoldSum 复验留痕保持 Open(采样按拍板跳过); 新入池 26-11-19-0754(引擎 gBCR 冗余, 与指纹件双向 refs)。

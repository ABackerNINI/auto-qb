# 23102 —— SLOT 清理后全量基线（rebase 吸收远端 8 笔）

> 摘要: SLOT 清理后全量基线（rebase 吸收远端 8 笔）
> 基线时间: 2026-11-03 10:39
**Refs:** `memory-bank/plans/26-11-03-0456-plan-skip-check-download-fuse.html`

## 验收数字

`commands run test.full` 实测(Windows 并行 + 覆盖率):

```text
[ok] test.full (153.0s)
  TOTAL                                                23102    182   7892    157    99%
  4958 passed, 10 skipped, 3 warnings in 144.90s (0:02:24)
```

Windows 本机单次采样; Linux(WSL) 侧未重测。与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `memory-bank/testing/baselines/26-11-03-0956-skip-check-download-fuse.md`: 删除建后残留的模板 SLOT 注释(`kb.check` 新增面转绿), 数字与结论不变。
- `memory-bank/activeContext/26-11-03-0956-skip-check-download-fuse.md`: `kb.wrap` 补 R1 收尾行。
- 开工同步 rebase 吸收远端 8 笔(抽屉桥表钩子 / e2e 大表与右键菜单修复、后端大文件拆分等), 故 passed 4957→4958、TOTAL 22860→23102。

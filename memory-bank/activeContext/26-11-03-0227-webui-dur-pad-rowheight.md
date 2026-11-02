# webui-dur-pad-rowheight

> 摘要: 修做种时间格 padding 撑高整行并扩到四皮肤守阵: 四皮肤去 padding 改线偏移 + 静态/几何双守阵(SKINS_ALL 四皮肤) + 真机复验 + 全量基线切片
> 最后活动: 2026-11-03 02:53
**Refs:** memory-bank/testing/baselines/26-11-03-0252-e2e-skins-all-geometry.md, memory-bank/pitfalls/web-ui/dur-cell-padding-rowheight.md

**R0(2026-11-03 02:27):** 修做种时间格 6px padding 撑高整行: 四皮肤去 padding 改线偏移 + 静态/几何双守阵 + 真机四皮肤复验 + 全量基线切片

**R1(2026-11-03 02:53):** e2e 行高几何守阵扩到四皮肤: harness.mjs 新增 SKINS_ALL, views.spec 几何 describe 改数据驱动遍历四皮肤; 定向 e2e 4 皮肤全绿; 全量 test.full 实测 4908 passed/10 skipped; 新建基线切片 26-11-03-0252; 同步 smoke.md/browser-env.md 的 harness 口径

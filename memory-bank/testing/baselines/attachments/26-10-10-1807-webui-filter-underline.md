# 2958 —— 列表筛选选中强调改笔直下划线基线

> 摘要: 用户要求「筛选器选中强调从框改为下划线, 注意要统一」, 范围 = 列表内 `.f-on`(站点/标签/分类胶囊 + 明细站点格/路径格), 不含下拉弹层/状态图例/筛选按钮; 三皮肤由 inset 描边环统一改为 2px 底线, 再按"笔直横线"复报改用绝对定位 `::after` + 宿主 `overflow:hidden` 由圆角裁边。机理单点: pitfalls/web-ui/f-on-underline-radius.md。
> 基线时间: 2026-10-10 18:07

**Refs:** memory-bank/tasks/26-10-10-webui-filter-underline.md,memory-bank/pitfalls/web-ui/f-on-underline-radius.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 5303e64a→55ea1aa6; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2958 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 28.21s)
- 增量明细(本轮真正新增): `src/` 改动仅前端静态 CSS(三皮肤 `.f-on` 规则)+ 两份模板注释 + `memory-bank/modules/webui-static-contract.md` 契约回写; **零 Python 触碰** ⇒ 守阵收集面不变。
- 静态守阵: 三皮肤 700 行体量守阵含在 test.full 内, 全绿。

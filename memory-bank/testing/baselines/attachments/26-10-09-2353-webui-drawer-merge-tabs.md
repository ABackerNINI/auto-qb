# 2870 —— 面板页插件化 + 页签合并实施基线

> 摘要: 计划 26-10-09-2219 R2 四项拍板后实施完成 —— classic 四件页插件(drawer_pages/)、核心层双实例挂载/宽度门/合并双列布局、右键开关菜单、数据供给对偶扩展; e2e 新增 drawer-merge.spec.mjs(右键开合/双列渲染/门内置灰), 既有 e2e 全绿(128 passed)。
> 基线时间: 2026-10-09 23:53

**Refs:** memory-bank/plans/26-10-09-2219-plan-webui-drawer-merge-tabs.html,memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md

## test.full 实测

- 分支: `develop`(HEAD `66d746ec`, 会话开工同步所得; 工作树含本实现 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 24.7s —— 与上基线 28.4s 同区间噪声)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 收集面差异说明: 用例数与覆盖率逐位持平 —— 本轮守阵为**断言面更新**(registry_wiring / width_discipline / fallback 静态+电池 / shell 上限 206→210 / storage 写基线 drawer_templates 1→2), 未新增 pytest 用例; e2e 新增 `e2e/drawer-merge.spec.mjs` 4 用例(128 passed / 10 skipped 存量), 不入 pytest 覆盖面。
- 增量明细(本轮真正新增): `shared/` 改动 = drawer_templates.js(核心: classic 入表/kit/双实例/门/split CSS)+ drawer.js(供给对偶扩展 + _drawerMergeSupply)+ state/menu/lifecycle/dialogs/app 接线; 新增 drawer_pages/ classic 插件 x4; 模板 drawer.html(经典链退役 + 双结构宿主 + 右键接线)与 ctx-menus.html(抽屉菜单分支); 三 index.html manifest 各 +4 行; 桩 scripts/ui_harness.py 补文件数据; 知识库回写件(计划 R3 / 本切片 / 主题文档 / progress / activeContext)。

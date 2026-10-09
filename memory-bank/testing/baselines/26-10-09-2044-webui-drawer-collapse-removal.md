# 2870 —— WEBUI 种子详情面板折叠状态整体移除基线

> 摘要: 用户动议「WEBUI移除种子详情面板的折叠状态」—— 折叠状态(`drawer.collapsed`)全链摘除: 状态字段/收起钮/44px 收起态摘要条/收起态鼠标换目标(peek)/`toggleDrawerCollapse`/各挂点收起守卫/三皮肤 CSS; 收起档专供的核心摘要管线(dtSummaryHtml/_dtDefaultSummary/注册表 summary 槽)与 7 个变体 `summary()` 同撤(全成死代码); 面板行为回归纯「开/关 + 拖拽调高」。20 个源文件(19 代码/测试 + 回写件), 命中立档阈值(≥3 源文件)。
> 基线时间: 2026-10-09 20:44

**Refs:** memory-bank/tasks/26-10-09-webui-drawer-collapse-removal.md, memory-bank/activeContext/26-10-09-2040-webui-drawer-collapse-removal.md

## test.full 实测

- 分支: `develop`(HEAD `11c40a9a`, 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- **收集面变化**: peek 守阵 `test_frontend_drawer_collapsed_click_peek_target` 整函数删, `test_drawer_height_collapse_w3` 改名 `test_drawer_height_w3`(一删一改名, 用例总数不变) ⇒ 收集数与上基线持平。
- 增量明细(本轮真正新增): 无新文件 —— 19 个代码/测试文件均为原文件修改; 回写件 pitfalls×2 / progress / activeContext×2 / tasks 档案 / 本基线切片。

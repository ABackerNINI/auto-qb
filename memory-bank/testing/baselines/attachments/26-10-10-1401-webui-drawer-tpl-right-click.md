# 2887 —— 详情面板模板选择迁右键(头部下拉退役, 右键各区域弹各自模板)基线

> 摘要: 用户动议「模板选择改为右键选择, 在对应的区域弹右键; 合并时左边弹常规的模板选择, 右边弹内容的模板选择」。三项拍板: ①头部 `.dt-select` 下拉移除, 右键为唯一入口; ②菜单 = 模板选项 + 合并开关合一; ③范围含全局/分组流量头部。改: 核心删 `.dt-select` 定宽 CSS 与 `dtTplOptions`/`dtTplCurrent`/`dtPick`, 新增 `dtMenuTab`/`dtMenuTplOptions`/`dtMenuTplCurrent`/`dtMenuMergeOn` + `dtMenuPick`; `openDrawerMenu` 放行 seed/traffic 并新增 `_drawerMenuTab`(宿主 `data-dt-host` → 合并列 `data-dt-tab` → 当前页签); 合并列加 `data-dt-tab`。
> 档案: memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md
> 基线时间: 2026-10-10 14:01

**Refs:** memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 f07dd529; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2887 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 25.55s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL)。
- 增量明细: passed 与上基线持平 —— 本轮只改前端静态 JS/模板(不进 `--cov=src`), 守阵净变动为 0(删 `test_drawer_tpl_select_fixed_width_tab_independent`, 新增 `test_drawer_tpl_menu_right_click_selection`, `..._cross_seed_fold_and_select_width` 改名 `..._cross_seed_fold`)。
- e2e 实测: `drawer-merge.spec.mjs` **8 passed**(@fast 双皮肤 atlas/prism; 原 3 + 新增「右键各列弹各自模板选择(左常规/右内容)」, 真实右键钉菜单选项集按命中列切换)。

## 本轮改动面

- `shared/drawer_templates.js` —— 删 `00-core` 里 `.dt-select` 整套定宽 CSS; 删 computed `dtTplOptions`/`dtTplCurrent`; 新增 `dtMenuTab`/`dtMenuTplOptions`/`dtMenuTplCurrent`/`dtMenuMergeOn`; 删 `dtPick`, 新增 `dtMenuPick(id)`。
- `shared/menu.js` —— `openDrawerMenu` 放行 seed/traffic 两形态 + 落 `tab`; 新增 `_drawerMenuTab(event)`。
- `shared/state.js` —— `drawerMenu` 显式加 `tab` 字段。
- `shared/tpl/drawer.html` —— 删种子头部/流量头部两处 `<select class="dt-select">`; 合并列 `.dt-col` 加 `data-dt-tab`。
- `shared/tpl/ctx-menus.html` —— 抽屉菜单改「模板选项 v-for + 勾选态 `.ctx-tick` + 分隔线 + 条件合并开关」。
- 守阵 `tests/test_webui_static_dom_panel.py`(删 1 / 新增 1 / 改名 1, 头部测试计划清单同步); e2e `e2e/drawer-merge.spec.mjs`(新增用例)。
- 知识库回写: `modules/webui-static-contract.md` + `progress/implemented-webui.md` + activeContext 切片 R5 段 + 本切片。
- `src/` 后端零改动。Linux(WSL 沙箱)侧未重测 —— 本轮只改平台无关的前端静态 JS 与断言面(口径见 baseline.md 常驻警告; 与近几轮切片同处理)。

## 守卫收口

- `kb.check` 全绿 / `doc.caps` 无阻塞项无 cap 债务。

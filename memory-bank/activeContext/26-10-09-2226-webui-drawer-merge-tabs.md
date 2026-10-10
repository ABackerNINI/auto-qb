# WEBUI 种子详情面板页插件化 + 页签合并(已实施)

> 摘要: 用户动议「常规&内容 / Tracker&用户 合并, 仅宽度足够时提供选项, 可切换」—— R2 改版(右键开关 + 页插件化 + 功能全量保留)经四项拍板后实施完成: classic 四件页插件(drawer_pages/)入注册表, 合并 = 抽屉级布局标志 `drawerMerge` + 右键勾选菜单 + 宽度门 1920(暂态遮蔽); 双列各挂各自所选页插件, 交互全量保留。计划 `memory-bank/plans/26-10-09-2219-plan-webui-drawer-merge-tabs.html`(R3, Done)。**R3 修订(2026-10-10)见下方; R4 修订(2026-10-10, 页签快捷键随合并态重排)见下方; R5 修订(2026-10-10, 模板选择迁右键: 头部下拉退役, 右键各区域弹各自模板)见下方; R6 修订(2026-10-10, 合并列间隙/留白右键回落左列修正)见下方。**
> 最后活动: 2026-10-10 18:42

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-10
**Topics:** webui-drawer-merge-tabs

## 已完成(迁自「正在进行」)

- 核心层(drawer_templates.js): classic 入表 + kit 工具箱 + 双实例挂载(_dtMounted/_dtMounted2)+ ownerKey 回落通道(classic 抛错走错误外壳不复位)+ .dt-tpl 限宽收窄 + drawer-split 布局 CSS + 门常量/resize 防抖/drawerMerge $watch。
- classic 插件 x4(general/trackers/peers/content, drawer_pages/): DOM 逐类名移植, 事件委托 + 状态自保(rawOpen/滚动/选中), 交互全量保留; content destroy 收回 filePrio。
- drawer.html: 经典链退役, 双结构宿主(单栏 x4 / 合并双列 v-if 互斥)+ 右键接线; ctx-menus.html 抽屉菜单分支(置灰 is-gated); state/menu/lifecycle/dialogs(escBusy) 浮层链同步。
- drawer.js 数据供给: _drawerWaitSources/_loadDrawerTab/_startDrawerPoll 按生效对偶扩展(FX-29 全对齐掀罩)+ _drawerMergeSupply 补给单点(drawerMerge $watch 与 resize 回调共用)。
- 测试: 守阵同步 6 处; e2e drawer-merge.spec.mjs 4 用例 + 既有 e2e 全绿(128 passed / 10 skipped 存量); 基线切片 `26-10-09-2353-webui-drawer-merge-tabs`(2870+4, 99%)。
- 回写: 主题文档 modules/webui-static-contract.md + progress/implemented-webui.md。

## R3 修订(2026-10-10, 用户再动议; 已完成)

用户报: 合并开启后切到另一对页签显示错乱 —— 「选择 常规+内容 并排后, tracker/用户标签显示"常规"/"内容"且为空」; 且「标签页没有合并」, 期望页签栏本身收敛为 `[常规&内容] [Tracker&用户]` 两张合并页签、可切换(不再二选一)。拍板: **合并为两个页签**。

- 根因: R2 的 `dtSplitOn` 只查「当前页签属于某个对」, 而模板按 `drawerMerge` 的值(gc/tp)渲染**固定那一对** —— 切到另一对页签时模板渲染旧对的列头, 挂载 `_dtMountSplit`/数据供给却按当前对找宿主 → **列头在而两列空**。
- 修法 + 改版: 开关模型收敛为 `off|on`(R2 旧值 gc/tp 初值迁移为 on); 新增 computed `dtMergeOn`/`dtMergeTabsOn`/`dtPair`, **列组与生效判据统一读 `dtPair`**(与挂载/数据供给同源, 单一真相); 页签栏在 `dtMergeTabsOn` 时渲染两合并页签(`dtMergeTabActive` 命中 / `dtMergeTabPick` 落点), 门外/未开回落四页签; 右键两项互斥勾选 → **单开关** `dtToggleMerge`; `dtSetMerge` 退役。
- 验证: `commands run test.quick` 2886 passed / 4 skipped; e2e `drawer-merge.spec.mjs` 4 passed(含"切对页签不再空列"回归) + fast 子集 42 passed。
- 回写: modules/webui-static-contract.md + progress/implemented-webui.md; 守阵 `test_drawer_tpl_registry_wiring` 增 R3 钉子(dtSetMerge 禁残留 / 合并页签标签 / `:data-merge="dtPair"`)。

## R4 修订(2026-10-10, 用户再报; 已完成)

用户报: 合并页签后「没有同步修改快捷键」—— 页签栏收敛成两张合并页签, 而 Alt+1~5 仍是四页签映射, 按下去不是预期那一页。拍板: **合并成功就 Alt+1/2/3, 未合并就 Alt+1/2/3/4/5**。

- 实现: 新增位次重排表 `KB_MERGE_TAB_REMAP` + 判据单点 `_kbMergeTabsOn`(读 `dtMergeTabsOn`, 与页签栏 `v-if` 同一 computed); `_kbDrawerTab` 内按位次重排(**先于**流量门控): 合并态 1=常规&内容 / 2=Tracker&用户 / 3=流量, 4/5 停用; 未合并五档原样。只改键盘 `run` 路径, 鼠标页签点击(`dtMergeTabPick`/`drawerTab`)不受影响。
- 文案: 帮助浮层 / 设置页快捷键条目经新增 `kbLabel` 随态改写(仅「详情面板」组, 静态 label 未合并不变)。
- 验证: `commands run test.one -- tests/test_web_shortcuts.py` 34 passed; e2e `drawer-merge.spec.mjs` 6 passed(含新增合并态快捷键用例, 双皮肤); 基线见 kb.baseline 最新一条。
- 回写: modules/webui-static-contract.md + progress/implemented-webui.md; 坑档 `pitfalls/web-ui/kbd-tab-set-sync.md`(界面页签集合改了而键盘映射没同步)。

## R5 修订(2026-10-10, 用户动议「模板选择改为右键选择」; 已完成)

用户命题: 「WEBUI 种子详情页模板选择改为右键选择, 在对应的区域弹右键, 比如合并时左边弹常规的模板选择, 右边弹内容的模板选择」。三项拍板: ①头部下拉移除, 右键为唯一入口; ②菜单 = 模板选项 + 合并开关合一; ③范围含全局/分组流量头部(所有模板切换器)。

- 实现: 核心层删 `.dt-select` 整套定宽 CSS 与 `dtTplOptions`/`dtTplCurrent`/`dtPick`, 新增 computed `dtMenuTab`/`dtMenuTplOptions`/`dtMenuTplCurrent`/`dtMenuMergeOn` 与方法 `dtMenuPick(id)`; menu.js `openDrawerMenu` 放行 seed/traffic 两形态 + 新增 `_drawerMenuTab(event)`(变体/经典宿主 `data-dt-host` 去 `-pre/-post` → 合并列 `data-dt-tab` → 回落当前页签); drawer.html 删两处 `<select>`, 合并列加 `data-dt-tab`; ctx-menus.html 抽屉菜单改「模板选项 v-for + 勾选态 + 分隔线 + 条件合并开关」; state.js `drawerMenu` 加显式 `tab` 字段。
- 验证: `commands run test.one -- tests/test_webui_static_dom_panel.py` 33 passed(旧 `test_drawer_tpl_select_fixed_width_tab_independent` 删除, 新 `test_drawer_tpl_menu_right_click_selection`, `test_drawer_tpl_cross_seed_fold` 改名 + 禁 `.dt-select` 回潮); e2e `drawer-merge.spec.mjs` @fast 8 passed(含新增「右键各列弹各自模板选择(左常规/右内容)」双皮肤)。基线见 kb.baseline 最新一条。
- 回写: modules/webui-static-contract.md + progress/implemented-webui.md。

## R6 修订(2026-10-10, 用户报「合并后右侧鼠标右键菜单会显示更改左边的模板选项」; 已完成)

用户报: 合并态在**右侧**右键, 菜单出的是**左列(常规)**的模板选项(改错了列)。

- 根因(真浏览器实测): 右列(内容)通常远短于左列(常规) —— 步长 2560 视口下 `.dt-col[content]` 仅 ~204px 高, 而 `[general]` 高 ~2059px。grid `align-items:start` 不撑高低列, **右列下方大片留白不属于任何 `.dt-col`**; 列间 24px gap 与分栏居中封顶 2400 之外的两侧留白同样不落列元素。`_drawerMenuTab` 命不中 host/col 时裸回落 `_dtCurTab()`(= 当前页签, 合并态常为左列/常规)⇒ 右侧空白拿到左列模板选项。
- 修法: `menu.js::_drawerMenuTab` 在 host/col 都命不中时, 若 `dtSplitOn` 且指针落在**正文区**(`el.closest(".drawer-body")`), 改走新增 `_drawerMenuColByX(event)` —— 按指针 `clientX` 与各 `.dt-col[data-dt-tab]` 矩形归列(取首个右缘不早于 x 的列; 落在最右列之右取最右列、最左列之左取最左列), 与「左右半区」视觉直觉一致。页签栏/头部不在此限, 仍回落当前页签(不带回归)。
- 验证: 探针实测修复前右列下方空白/列间隙/右侧留白 `menuTab=general`, 修复后一律 `content`(左列/左留白仍 `general`)。`test.one -- tests/test_webui_static_dom_panel.py -k drawer_tpl` 12 passed(守阵加 R6 三钉); e2e `drawer-merge.spec.mjs` **8 passed**(用例扩「右列下方空白右键仍须弹内容模板」); `test.full` 2958 passed + 4 skipped / TOTAL 99%(基线 `26-10-10-1842`)。
- 回写: modules/webui-static-contract.md + progress/implemented-webui.md; 坑档 `pitfalls/web-ui/drawer-merge-hit-region.md`(几何分区式右键命中: 区域容器不必然覆盖其视觉范围)。

# WEB UI 悬浮提示与选中摘要

> 摘要: `conventions/webui.md` 的全局 tooltip `.aq-tip` 与选中摘要口径 —— 整段逐字外迁, 本节是该主题的现行权威。
> 触发: tooltip, 悬浮提示, aq-tip, 定位, 选中摘要, occ_key, 实际占用, 合计大小, 批量选择

## WEB UI 悬浮提示 .aq-tip (2026-09-28)

全局 tooltip 收敛为自绘单例, **新元素一律继续写原生 `title` 属性**(模板侧零成本接入), 不许再自造浮层:

- **触发面**: 一切带 `title` 的元素(含 Vue `:title` 绑定); 调度单点在 `shared/ui_feedback.js` 尾部的纯 DOM 委托层(不进 mixin)。机制(2026-10-04 二轮定稿, **原生 tooltip 断供式**): MutationObserver 盯全文档, title 属性在任何时刻出现(模板渲染 / Vue `:title` 写回 / 新插入节点)即刻迁进 `data-aq-tip` 并删掉原属性 —— DOM 里不存在 title, 原生气泡无从弹出; 浮层触发 = document 级委托 mouseover / focusin 命中 `[data-aq-tip]`, 350ms 后弹 `.aq-tip`, 文案 show() 时现读最新值。前两轮的「hover 时摘 + 离开还原 + 悬浮期补摘」被废弃 —— Vue 轮询把指针下节点整个换掉时指针不动、mouseover 不触发, 新节点带 title 还魂叠出双 tooltip(见 pitfalls/web-ui/aq-tip-nested-title-double.md)。代价: title 不再还原(原生悬浮语义由 `.aq-tip` 承接)。点击 / 滚动 / 窗口失焦立即收起。
- **定位**(2026-10-04 修): 上方优先 → 上方放不下转下方 → 两侧都放不下才允许溢出视口; **任何分支都不越过锚点**。旧版末尾无条件把浮层夹回视口内, 状态栏这类底缘锚点一旦走「转下方」分支就会被拉回状态栏上, 正好盖住它自己描述的元素。锚点在 350ms 延时窗口内被 Vue 整个换掉时已脱离文档(rect 全 0), 按记录的指针坐标 `elementFromPoint` 重解析当前锚点, 解析不到就收起(否则浮层落到视口左上角)。
- **样式单点**: `shared/console_hub.css` 的 `.aq-tip` 段(三皮肤同载)。视觉复刻设置页发光按钮配方: 描边 `--accent-line` + 负 spread 微光 `0 0 16px -8px`(同 `.hb-card` 静息 `--glow-soft`), 底 `--bg-elev` 字 `--fg`, 圆角随 `--radius-sm`(控制台自动方角)。⚠ 发光要在 `.aq-tip` 本层用 `--accent` 现算 —— `.hb-*` 的 `--glow-soft` 只声明在 hub 控件上, body 级单例继承不到(console_hub.css 文件头硬知识③)。
- **例外**: 需要富内容(仪表/表格/交互)的悬浮走既有专用浮层(hr-pop / hb-pop / search-help-pop), 不挤 `title` 通道。

## WEB UI 选中摘要口径 (2026-10-18, 计划 26-10-18-2013)

选中种子时筛选行显示「已选 N 个种子 · 合计 X · 实际占用 Y」——**纯展示**(零按钮, 清除走 Esc; 批量动作仍归右键菜单, 不复活 2026-10-05 退役的控制条):

- **位置与样式**: `shared/tpl/topbar.html` 的 `.sel-summary`(退役控制条原槽位), `v-if="selectedCount"`; 整行复用 `.strip-note` 既有规则(三套皮肤逐字同款) —— **零新 CSS**, `.sel-summary` 仅作 e2e 选择器钩子。
- **三个量的口径**: N = `selectedCount`(`selHashSet` 去重成员数, 选 1 组 = 全组成员); X = Σ 选中成员 `size`(每个种子各算一份, 与删除框既有「总大小」行同口径); Y = 按 `occ_key` 内容单元去重、**单元取选中成员最大 size**(最完整副本, 与后端 progress=max/availability=max 同族)。Y 仅在 `Y < X` 时显示(⇔ 选中了同一单元的 ≥2 个副本)。
- **occ_key 载荷契约**(后端 `views.py::_member_view`): 归组种子带其辅种组 key(`encode_group_key`, 与组行 `key` **同键空间** —— 守阵不变量), 未归组为 `null`(字段恒在、null = 不适用, 与 `availability` 同族契约; 前端按 `m.occ_key || ("self:"+m.hash)` 兜成自单元)。种子页平铺行经 `_seed_view` 的 `{**_member_view(r), ...}` 继承; 追剧页成员经 `memberByHash` 解析, 三视图同源。语义根: 组内成员指向**同一份文件**, 磁盘只占一份(组行 `size`/`total_size` 双口径的选中版)。
- **不去重的两层**: 跨组文件交叉(`cross_group_conflict`)不再去重(后端另有风险标记); 追剧页同集多版本不额外去重(「同一份文件」判据是 save_path = 组, 不是集; 不同版本是不同字节)。
- **算法单点**: `selection.js::selSizeSummaryOf(members)` —— 筛选行(`selectedSize` computed, 无选中早退)与删除确认框(`delete_flow.js::_deleteDetails` 的条件行)共用, 不另写求和。删除框那行仅 `Y < X` 时追加, 口径说明走 `d.hint`(popovers 详情行 `:title` 吃 `d.hint || String(d.value)`; 原生 title 由 .aq-tip 层迁移成 `data-aq-tip`)。
- **守阵**: `tests/test_web_backend_misc_views.py::test_member_view_occ_key`(契约三条) · `tests/test_webui_static_dom_page_layout.py::test_frontend_selection_size_summary_wiring`(模板/JS/删除行三层接线) · `e2e/multiselect-shows.spec.mjs`「选中摘要」两条(双皮肤)。

# 右键菜单项的勾误绑恒真形态判据 + title 提示被菜单自身盖住

> 摘要: 抽屉右键菜单「合并页签」项的勾误绑「该项是否出现」的形态判据(种子详情恒真)⇒勾永远在; 同项的 `:title` 经 .aq-tip 委托层(z90)自绘后恒被 .ctx-menu(z100)盖住⇒看不见的提示。两条都不报错、静态锚全绿, 只有用户看得见。
> 触发: 合并页签, 勾一直是勾选状态, 勾选态不随状态变, ctx-tick, dtMenuMergeOn, dtMergeOn, 被右键菜单覆盖的 tooltip, 被遮挡的提示, .aq-tip, .ctx-menu

## 本篇只回答

抽屉/浮层菜单项的「视觉反馈」为什么恒真或根本看不见 —— 勾选态误绑形态判据、悬停提示被菜单自身层级盖住这两类同源症状的判别与处置。

### 勾读的是「菜单项是否出现」而不是「开关是否打开」, 菜单一创生就恒打勾

- **触发**: 菜单项由形态判据条件渲染(`<template v-if="dtMenuMergeOn">`, `dtMenuMergeOn()` 返回 `drawerIsSeed` —— 种子详情形态恒 true), 顺手把同一个判据写到该项的勾上(`<svg v-if="dtMenuMergeOn" class="ctx-tick">`)。开关关闭时勾仍在, 用户点开/点关都看不出区别。
- **判别**: ①勾在「从未操作过开关」的初始态就存在; ②grep 该 `v-if` 的表达式, 计算其定义 —— 若只依赖形态/上下文而不读开关值(`drawerMerge` / `dtMergeOn`)即命中; ③静态守阵若只断言 `.ctx-tick` 存在于模板(不绑状态), 全绿也掩盖不住(2026-11-15 用户报障时正是此态)。
- **处置**: 勾改读**开关自身的真值** `dtMergeOn`(= `(drawerMerge || "off") !== "off"`), 与 `dtToggleMerge` 写入、`dtMergeTabsOn`/`dtSplitOn` 判据同源; 形态判据只留在 `<template v-if>` 控显隐。宽度门只做 `is-gated` 置灰遮蔽, 不撤销标志 —— 门跨越时勾仍反映用户意图(`drawer-merge.spec.mjs`「门跨越」用例 2026-11-15 评审补钉了窄视口置灰态下 `.ctx-tick` 仍为 1 的真断言; 此前只钉标志未查勾, 属引用未覆盖行为的证据)。守阵加两条: 静态钉 `v-if="dtMergeOn"` 在合并项块内且 `v-if="dtMenuMergeOn"` 不得回潮; e2e 真手势钉关态 0 勾 / 开态 1 勾 / 再关 0 勾。
- **守阵**: `tests/test_webui_static_dom_panel_drawer.py::test_drawer_tpl_menu_right_click_selection` §4; `e2e/drawer-merge.spec.mjs` 首例三态 `.ctx-tick` + `title`/`data-aq-tip` 双 null; 「门跨越」用例补窄视口置灰态 1 勾; 「再关 0 勾」段先钉合并项在场(`toBeVisible`)防安慰剂。三组红验各自必红(2026-11-15 实测): ①`dtMergeOn` 改回 `dtMenuMergeOn` → 静态守阵 1 failed + e2e 双皮肤 2 failed(Expected 0 / Received 1); ②把 `:title` 加回合并项 → 静态守阵 1 failed(「合并项又挂 title」) + e2e 双皮肤 2 failed(`[null, "功能说明文案"]` ≠ `[null, null]`, 原生 title 已被 `ui_feedback.js` 单向迁成 `data-aq-tip`); ③单独验「再关 0 勾」非恒绿(临时摘关态断言 + 回潮勾绑定) → e2e 双皮肤 2 failed 恰报在该行 `toHaveCount(0)`(Expected 0 / Received 1), 且前一行 `toBeVisible` 已通过。

### 菜单项挂 `title` 会弹一个被菜单本体盖住的 .aq-tip

- **触发**: 给 `.ctx-menu` 内的项写 `:title="..."`(本例是「合并页签」的功能说明 + 置灰原因「窗口宽度不足」)。`shared/ui_feedback.js` 的 MutationObserver 把 title 单向迁成 `data-aq-tip`, 350ms 后自绘 `.aq-tip`; 而 `.aq-tip` z-index 90 < `.ctx-menu` z-index 100(四皮肤同值), 提示整块落在菜单底下, 用户只看到菜单, 或边缘露出一角。同类机制见 [hr-tooltip-overlap.md](hr-tooltip-overlap.md)(原生 title 被更高层弹窗遮挡)。
- **判别**: ①悬停菜单项约 350ms 后出现「看不见/被盖住」的提示; ②项上有 `title` 或 DOM 里出现 `data-aq-tip`; ③查两级 z-index: `.aq-tip`(shared/console_hub_controls.css) 与 `.ctx-menu`(四皮肤 components.css) —— 后者更大即命中。`place()` 只对 `.err-panel` 做了「宁可不弹」避让, 没有 `.ctx-menu` 这一档。
- **处置**: 层级高于 `.aq-tip` 的浮层内部**不写** `title`(已写入 `memory-bank/conventions/webui.md`「悬浮提示」边界)。本例直接摘掉该项 `:title`, 置灰原因由 `.is-gated` 视觉 + `dtToggleMerge` 行为层双保险表达, 不再造第二份提示通道; 四皮肤 `components.css` 置灰规则注释同步删「title 提示」口径。守阵静态钉合并项块内 `:title=`/`title=` 零残留, e2e 钉该项 `title` 与 `data-aq-tip` 双双为 null。
- **守阵**: 同上两条用例(静态 §4 第三条断言 / e2e 首例 `item.evaluate` 取两属性)。
- **复发**: 0

# 3131 —— WEBUI 抽屉重构 W4 合并双列单一状态源(26-10-11-2106 计划)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-12-0009-webui-drawer-refactor-w3.md

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W4** —— 合并双列与右键模板选择收进新面板**单一状态源**: 合并状态(四判据 + 四方法 + 两条监听)自 `drawer_templates.js`(插件/变体层)整体迁 `drawer.js`(面板核心), 合并对常量改列表形态落 `window.AQB_DRAWER_MERGE` 跨文件单点; 合并页签按钮与双列列组改 `dtMergeTabList`/`dtPairCols` 两渲染单点 `v-for` 驱动, 模板不再硬编码 gc/tp 分支(**删「渲染列组 vs 命中」双份判据**, R2 空列 bug 类永久闭环); `_drawerMenuColByX` 复核后保留(几何根因与渲染技术无关, 注 W4 结论); 新增「门跨越 / 拉宽自动恢复」真手势 e2e。判据: ① `test.full` 对账吻合(W4 零新增 pytest 用例); ② e2e = 基线 + 本轮新增 2(1 用例 × 2 皮肤), 零失败; ③ 验收动词各有守阵/e2e 钉且红验**逐条非退化**。
> 基线时间: 2026-10-12 01:17

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 到 `acd0e26f`; 工作树含 W2+W3+W4 三轮回写件时实测, 均未提交)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3131 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial; 本轮 29.4s)
- **对账(重要 —— 基数变了)**: 上基线(W3 切片)记 3130。本轮实测 3131, 引发 +1 疑问后经**临时 worktree 收集清单 diff** 逐条核实: **HEAD 在 W2→W3 会话之间前移了**(本会话 sync 到的 `acd0e26f` 含其他会话提交的 +1 用例), HEAD 基线实为 **3130**; 工作树 = 3130 + W3 新增 1 条守阵 + **W4 零新增** = 3131, 账目吻合, 覆盖率四项逐位不变。W3 切片记的 3130 对其当时的 HEAD(3129 基数)是**自洽的**; 从本轮起对账基数以 `acd0e26f` = 3130 为准。
- **守阵改动(同轮改版, 不放宽)**: `test_drawer_tpl_registry_wiring` 合并钉块整体改版; `test_webui_error_history` 的 setItem 逐文件基线随落盘落点迁移(drawer.js 3→4 / drawer_templates.js 2→1, 断言口径不变)。

## e2e 实测

- 命令: `commands run dev.e2e`(Windows; 桩 `scripts/ui_harness.py` 由 webServer 自动起)
- **实测 (Windows)**: **166 passed + 0 failed + 10 skipped**(4.6m)
- **对账**: 上基线 **164** + 本轮新增 **2**(`drawer-merge.spec.mjs` 新用例 × 2 皮肤) = **166** ✅ 逐位对齐。
- **本轮新增**: 「门跨越: 窄视口无合并(标志保留) → 拉宽自动恢复 → 缩窗回落」—— 预置 `autoqb.ui.drawerMerge=on` → 1280 开面板(无双列/四页签) → 拉宽 2560(双列自动恢复 + `data-merge=gc` + 第二列数据补给到位 + 页签栏收敛) → 缩回 1280(回落单栏) → 再拉宽(直接恢复 = 门只遮蔽不撤销意图)。计划 W4 验收动词「拉宽自动恢复」此前无任何覆盖(既有窄视口用例只钉门内置灰), 且合并的两条监听本轮正好随状态迁移 —— 该链路必须有真手势。

## W4 验收动词 × 红验(「按下去到底行不行」的记录)

| 验收件 | 断言位置 | 红验注入 | 结果 |
|---|---|---|---|
| 合并开关(右键单开关) | `test_drawer_tpl_registry_wiring` + e2e 用例① | (既有覆盖, 未重注) | — |
| 高亮判据与列组同源 | `mt.id === dtPair` **代码形态** pin | **RC1**: `:class` 改回 `mt.id === 'gc'` | rc=1 (红 ✓; 首轮裸字符串 pin 被模板注释喂饱未红, 改锚 `:class="{...}"` 表达式后重验) |
| 删「渲染列组 vs 命中」双份判据 | `dtPair === 'gc'`/`'tp'` 负 pin + `dtPairCols` v-for pin | **RC2**: split 内回插 `<template v-if="dtPair === 'gc'">` | rc=1 (红 ✓) |
| 插件层不自建映射 | `MERGE_PAIRS not in drawer_templates.js` + `pairOf(this.drawer.tab)` 消费 pin | **RC3**: `_dtMountSplit` 内联自建映射 | rc=1 (红 ✓) |
| 拉宽自动恢复(两条监听随迁) | 监听**注册形态** pin + 新 e2e 门跨越用例 | **RC4**: 删 `addEventListener("resize", …)` 注册行 | rc=1 (红 ✓; 首轮裸名字 pin 被声明/摘除处喂饱未红, 改锚注册行后重验) |

- ⚠ **本轮新教训(两次实证)**: 给注释丰富/多处出现同名标识符的文件写 pin, **裸字符串必然退化** —— 要么被说明性注释喂饱(RC1), 要么被声明/摘除处喂饱(RC4)。pin 必须锚**代码形态**(完整表达式/注册行), 注入后立刻自验一次再记录。
- (补充)既有四条合并 e2e(开关/置灰/切对/右键各列 + 右列空白归列)全绿, R3/R6 回归防线未动。

## 增量明细(本轮真正新增/改动)

- **源(drawer.js, +约 120 行)**: 合并常量(`MERGE_STORE_KEY`/`DT_MERGE_MIN_WIDTH`/列表形态 `MERGE_PAIRS`/`DT_TAB_LABELS`)+ `window.AQB_DRAWER_MERGE` 跨文件单点(`PAIRS`/`MIN_WIDTH`/`pairOf`) + computed 群(四判据 + `dtMergeTabList`/`dtPairCols` 两渲染单点) + methods 群(四方法) + `mounted`/`beforeUnmount`(两条监听, 假实例守卫 `if (!this.drawer) return;` —— 全局 mixin 波及 BaseTransition, 同 traffic 通知规避式)。
- **源(drawer_templates.js, 净减约 90 行)**: 删合并 computed/methods 区、两条监听、四常量、`REG.merge*` 三处暴露; 头注改指 drawer.js; `_dtMountSplit` 改吃 `AQB_DRAWER_MERGE.pairOf`; `dtMergeTabActive` 删除; 保留插件机械(`_dtSync`/`_dtMount*`/`_dtNotify*`/右键菜单 computed)。
- **源(tpl/drawer.html)**: 页签栏合并按钮 `v-for="mt in dtMergeTabList"` + 高亮 `mt.id === dtPair`; 双列 `v-for="col in dtPairCols"`(列头 `{{ col.label }}` / `:data-dt-tab` / `:data-dt-host` 绑定化 / `<component :is="'aq-drawer-' + col.tab" v-bind="col.props">`); gc/tp 两 `<template>` 分支删除。
- **源(menu.js)**: `_drawerMenuColByX` 复核结论注释(W4 保留, 根因三条几何事实)。**CSS / qb_traffic_chart.js / uPlot 零改动**。
- **测试**: `test_drawer_tpl_registry_wiring` 合并钉块改版; `test_webui_error_history` 基线迁移; `e2e/drawer-merge.spec.mjs` 新用例。

## 风险 / 观察

- **00-core 注入的合并 CSS 尚未随迁**(W4 只迁状态与判据): `.drawer-split`/`.dt-col`/`.dt-col-head`/`.is-gated` 四组规则 + 2400 封顶仍由 `drawer_templates.js` 的 `dtInjectCss("00-core")` 注入。W6 退役该文件时必须把面板仍在用的规则迁三皮肤 CSS(变体专属的 `.dt-tpl` 限宽随退役消失) —— 已记入任务档案 W5/W6 冻结区备忘。
- **`<component :is>` 动态组件 + `v-bind="col.props"`**: general 列的详情经 `dtPairCols` 的 `props: { d: this.drawer.detail }` 传入 —— computed 对 `drawer.detail` 的依赖是响应式的, 详情更新自动续传; 四个页签组件保持 W2 的「只贡献模板」纪律, 无需为合并改组件面。
- **监听随迁的假实例守卫不能省**: 全局 mixin 的 `mounted` 会跑在 `<transition>` 的 BaseTransition 假实例上(无数据面), 迁入 drawer.js 的两条监听保留 `if (!this.drawer) return;` 守卫 —— 漏掉 = 13 个 transition 各抛一条 TypeError(R2 实测过的病状)。
- **对账纪律**: 基数可能因其他会话的提交而漂移 —— 遇到 passed 数与预期差 ±1, 先用 worktree 收集清单 diff 定位, 再下结论(本轮实证, 避免误判为"多了一条测试")。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2/W3/W4 各加一条); `kb.check` 切片数 > 70。两项均需另开新会话收口。
- W5–W6 待起(W5 = 15 变体 → 声明式密度变体 + `esc-attr-quote-dead-class` 随之消失; W6 = 退役第二套渲染技术 + 00-core CSS 迁三皮肤 + 摘 `qb_traffic_chart.js` 谓词冻结豁免)。

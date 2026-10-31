# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W4 已落地

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**。**W0** 冻结契约与验收基线; **W1** 数据层抽离(A/B DOM dump 逐字节等价); **W2** 四页签 Vue 重建 + 三列表接壳(拍板「全部一起做」+「Vue 连变体一起声明式实现」+「div 网格与主视图同源」+「观感变化整体接受」); **W3** 流量页签与形态收敛(拍板「缺陷留到 W5」—— `esc-attr-quote-dead-class` 随 W5 退役消失)。**W4**(本轮 26-10-12-0117)= 合并双列与右键模板选择: 合并状态(四判据/四方法/两条监听)自 `drawer_templates.js`(插件层)整体收进 `drawer.js`(面板核心**单一状态源**), 合并对常量落 `window.AQB_DRAWER_MERGE` 跨文件单点; 合并页签与双列列组改 `dtMergeTabList`/`dtPairCols` 两渲染单点 `v-for` 驱动 —— **删掉「渲染列组 vs 命中」双份判据**, R2 空列 bug 类(模板硬编码一对 + 判据读另一对)永久闭环; `_drawerMenuColByX` 复核后保留(几何根因与渲染技术无关); 新增「门跨越 / 拉宽自动恢复」真手势 e2e。`test.full` 3131 passed(HEAD 基线 3130 + W3 的 1 条, W4 零新增; HEAD 会话间前移已 worktree 对账) + e2e 166 passed(164 + 2) + 四条红验均 rc=1(RC1/RC4 首轮被**退化钉**放过, 改代码形态锚定后重验 —— 裸字符串 pin 在注释丰富的文件必退化)。数字见基线切片。W5–W6 待起。
>
> 最后活动: 2026-10-12 01:17

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/attachments/26-10-12-0117-webui-drawer-refactor-w4.md

## 本轮完成 (W4)

- **状态迁移**: `drawer.js` 新增合并判据群(`dtMergeOn`/`dtMergeTabsOn`/`dtPair`/`dtSplitOn`)+ 落点方法(`dtToggleMerge`/`dtMergeTabPick` 等, R3 语义逐字同义)+ 两条监听(resize 防抖回写 `dtWinW`、`drawerMerge` $watch, 假实例守卫保留); `drawer_templates.js` 只剩插件挂载机械(`_dtMountSplit` 经 `AQB_DRAWER_MERGE.pairOf` 消费)—— W6 退役该文件时合并不再陪葬。
- **删双份判据**: 合并对改列表形态单点, 页签栏与双列正文全部 `v-for` 数据驱动; `dtMergeTabActive` 方法删除(高亮 = `mt.id === dtPair` 与列组同源)。
- **复核结论**: `_drawerMenuColByX` **保留** —— `align-items:start` + 2400 封顶 + 24px gap 与列渲染技术无关, 短列下方/间隙/两侧留白照旧不落在 `.dt-col` 上(R6 回归防线)。
- **验收**: `test.full` = 3131 passed + 4 skipped / `TOTAL 16517 151 5626 134 99%`; e2e = 166 passed + 0 failed + 10 skipped(既有四条合并用例全绿 + 新增门跨越 2); 四条红验(RC1 高亮脱钩 / RC2 回插分支 / RC3 自建映射 / RC4 监听迁丢)均 rc=1 非退化; 三皮肤 CSS 与 `qb_traffic_chart.js`/uPlot 零改动。

## 三处非显然的判断(下轮别再踩)

1. **裸字符串 pin 在注释丰富的文件必然退化(RC1+RC4 两次实证)** —— 高亮判据 pin 被 drawer.html 里自己写的说明注释(`mt.id === dtPair` 字样)喂饱; 监听 pin 被 `_mergeOnResize` 的声明/摘除处喂饱。pin 必须锚**代码形态**(`:class="{...}"` 完整表达式 / `addEventListener` 注册行), 且注入后先自验一次再记结论。
2. **对账基数会因其他会话的提交漂移** —— 3131 vs 上片 3130 的 +1 疑问, 用 worktree 收集清单 diff 定位: HEAD 在会话间前移(+1 用例), 本轮实际零新增。遇 ±1 先对账再下结论, 别急着怀疑自己多了测试。
3. **不是 mixin 的全局单点要走「先建局部量再赋 window」形态**(`window.AQB_DRAWER_MERGE = AQB_DRAWER_MERGE_SINGLE`) —— `window.X = {` 字面量会被 `_scan_mixin_wiring` 当 mixin 要求 app.mixin 注入; `AQB_DRAWER_TPL_REG` 早已是同款先例。

## 待办 / 移交

- **W5–W6 待起**: W5 = 15 变体 → 声明式密度变体(**已拍板** `esc-attr-quote-dead-class` 随 W5 退役消失, 不回灌修法); W6 = 退役第二套渲染技术(① 摘 `qb_traffic_chart.js` 谓词冻结豁免换吃 `drawerIsTraffic`; ② **00-core 注入的合并 CSS 迁三皮肤** —— W4 只迁了状态判据, `.drawer-split`/`.dt-col`/`.dt-col-head`/`.is-gated` + 2400 封顶仍在 `drawer_templates.js` 注入, 变体专属 `.dt-tpl` 限宽随退役消失)。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2/W3/W4 各加一条); `kb.check` 切片数 > 70。两项均需另开新会话收口。
- **工作树**: W2 + W3 + W4 三轮改动均未提交(用户未要求 commit)。

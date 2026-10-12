# webui-column-picker — 「列」选择器信息架构重设计(调研 + 入池)

> 摘要: 用户报「表格太多, 统一到『列』按钮里显得杂乱难寻」并给出两个初步方向(① 保留按钮 + 分类折叠 / ② 右键 + 弹窗各表分开), 要求调研成熟方案并写详细报告。**取证把「杂乱」定性为信息架构问题**: 选择器作用域 = 全应用全部表, 生产态弹层恒定 **7 分组 / 107 勾选项**, 其中约 86 项与当前屏幕无关(作用域错配), 且无检索、分组不可折叠、无状态提示。**关键发现**: `columns.js::openColMenuAt(ev, page)` 的 `page` 参数已预留但闲置 ⇒ 方案 ② 不需新增 API 面。**裁定**: ① 必要但不充分(作用域仍全应用) / ② 方向正确但可发现性差 ⇒ 推荐 **②为骨、①为肉**(作用域收敛 + 双入口同语义 + 检索 + 按列语义族折叠)。报告 [26-10-12-1854](../reports/26-10-12-1854-report-webui-column-picker-redesign.html) 含 6 类业界模式调研 + 8 维对比矩阵 + 四波落地拆解; 附带发现(种子页扩展列「默认隐藏」注释与代码漂移 ⇒ 默认 28 列全显)单独立池 issue `26-10-12-1911`(Open, 未认领)。**本轮零代码改动; 重设计实施未排期, 待用户拍板。**

**创建:** 2026-10-12 19:12
**最后活动:** 2026-10-12 19:12
**主题:** webui-column-picker
**摘要:** 取证面 = `src/auto_qb/webui/static/shared/` 的列模型(`app.js` 的 `TABLE_COLUMNS` / `TABLE_DEFS` / `DRAWER_TABLE_DEFS` / `ALL_TABLE_PAGES`)、列交互引擎(`columns.js` 的 `tableDefs` computed / `openColMenuAt(ev,page)` / `persistPage` 唯一漏斗)、顶栏与表头模板(`tpl/topbar.html` 的 `.col-picker`/`.col-menu`、`menu.js` 的 `openHeadMenu`/`headMenuPicker`、`tpl/ctx-menus.html` 的表头菜单)。核心数字: 16 张表 / 生产态 7 组 107 项 / 弹层 300px + `max-height:70vh`; 两条入口(顶栏「列」按钮仅 `page==='groups'` 渲染; 表头右键 → `openColMenuAt`)。待用户拍板两件事: ① 顶栏「列」按钮是否放开到种子页/追剧页渲染(可发现性增强); ② 重设计是否立项实施。**不做**: 模式 E「保存视图」(新维度, 远期) / 模式 C 模态列选器(与既有浮层体系冲突) / 种子页默认隐藏漂移的修复(属范围外, 已入池)。
**Refs:** memory-bank/tasks/26-10-12-webui-column-picker.md

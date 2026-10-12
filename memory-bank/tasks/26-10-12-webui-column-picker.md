# 26-10-12-webui-column-picker — WEBUI「列」选择器信息架构重设计(调研 + 入池)

**Status:** Done(本轮调研与入池完成; 重设计实施未排期 —— 待用户拍板后另立计划)
**Added:** 2026-10-12
**Updated:** 2026-10-12 19:12
**Topics:** webui-column-picker
**Summary:** 用户命题「表格太多了, 统一到『列』按钮中显得杂乱难寻, 需要一个更好的方案」并给出两个初步方向(① 保留「列」按钮 + 分类折叠; ② 右键 + 弹窗、各表分开), 要求「调研成熟的解决方案, 对各方案进行对比, 写一个详细的报告」。产出报告 [26-10-12-1854](../reports/26-10-12-1854-report-webui-column-picker-redesign.html): 量化取证(生产态弹层恒定 **7 分组 / 107 勾选项**, 其中约 86 项与当前屏幕无关) + 6 类业界模式调研 + 8 维对比矩阵 + 推荐形态(② 为骨、① 为肉)。另把报告中的附带发现(种子页扩展列注释称「默认隐藏」但无 `hide: true`, 实际默认 28 列全显)单独立池 issue `26-10-12-1911-docs-webui-torrent-column-default-hidden`(Open, 未认领)。**本轮零代码改动。**
**Refs:** memory-bank/reports/26-10-12-1854-report-webui-column-picker-redesign.html,memory-bank/activeContext/26-10-12-1912-webui-column-picker.md

## 原始请求

用户原文: 「现在的表格太多了, 统一到"列"按钮中显得杂乱难寻, 需要一个更好的方案, 初步考虑下面的方案 1.仍使用"列"按钮, 但进行分类+折叠 2.右键+弹窗的形式, 各个表分开 调研成熟的解决方案, 对各个方案进行对比, 写一个详细的报告」。

## 思考过程与决策

- **现状取证(量化)**: 列模型单点在 `shared/app.js`; 表注册表 `ALL_TABLE_DEFS` = 16 张(主视图 4 + 抽屉/变体 12); 选择器数据源 `columns.js::tableDefs`(取 `ALL_TABLE_PAGES` 全集, 变体表按 `dtBridgeTbl` 过滤) ⇒ 生产态恒定 **7 个分组 / 107 个勾选项**(辅种表 21 / 明细表 28 / 种子页 28 / 追剧视图 11 / Tracker 列表 6 / 用户列表 9 / 文件列表 4), 弹层 300px 宽 / `max-height:70vh` / 线性滚动 / 无检索 / 分组标题不可折叠。用户在某张表上点「列」, 约 86 项与当前屏幕无关 —— 这是「杂乱难寻」的**结构性根因(作用域错配)**, 不是视觉问题。
- **关键发现(方案 ② 的地基已存在)**: `columns.js::openColMenuAt(ev, page)` 的 `page` 参数**已预留但闲置**(源码注释原文: 「page 参数当前仅区分语义(弹层四段全量展示), 留作按视图段落定位的扩展点」), 且表头右键菜单 `menu.js::openHeadMenu` → `headMenuPicker()` 已在线上 ⇒ **方案 ②「各表分开」不需新增 API 面, 只需让数据源按 `page` 过滤**。
- **业界调研(6 类模式)**: A 工具侧栏(AG Grid Columns Tool Panel / Grafana Fields) / B 弹层复选(TanStack+shadcn / MUI X Columns 面板 / DataTables `colvis`) / C 模态列选器(AG Grid Column Chooser / DevExtreme `columnChooser` / Syncfusion) / D 表头右键(原生 Finder / AG Grid 表头菜单) / E 按视图保存(Airtable·Notion·Excel 自定义视图) / F 命令面板。**没有任何成熟产品把「全部表的全部列」平铺进一个弹层**; 跨表/多列场景一律走「分组折叠 + 检索 + 全选」或「作用域收敛到当前表」。
- **裁定**: 方案 ① = **必要但不充分**(默认展开项可从 107 降到 21, 但作用域仍是全应用、仍无检索); 方案 ② = **方向正确**(作用域契合、地基已有 70%), 唯一短板是可发现性(右键无提示)。推荐 **② 为骨、① 为肉**: 作用域收敛到当前表 + 双入口同语义(表头右键为主 + 顶栏「列」按钮为**当前表**备选, 按钮标注表名) + 弹层内检索与**按列语义族**分类折叠 + 组头可见计数 + 三态勾选 + 重置本表显隐。
- **必须保住的不变式**: 现行「全表弹层」是 2026-10-11 W2(计划 26-10-11-2106)的**有意决策** —— 抽屉表头右键「隐藏本列」不可逆, 把抽屉表列进主选择器是为留恢复入口。作用域收敛后, 恢复入口迁到**各自表头的右键菜单**(抽屉表头已走同一条 `openHeadMenu`, 天然成立); 无表头的变体(04/05、内容 10)本无右键隐藏能力, 口径自洽。
- **不动**: 持久化层零改动(`persistPage` 唯一漏斗 + v5 按页子树双轨模型, **不升版本**, 符合 `pitfalls/web-ui/columns-persist.md` 判据); 列宽拖拽 / 拖序 / 双击自适应 / 对齐注入(`colAlignCss`) / 行窗口化全部不动。
- **附带发现单独立池(只取证不改)**: `TORRENT_COLUMNS` 扩展段注释(当时行号 158)与文件头注释(132–137)都称扩展字段「默认隐藏、按需开启」, 但 13 个列定义**无 `hide: true`**, 而播种判据 `loadColState` 的 `filter(c => c.hide)`(当时行号 739–744) ⇒ **种子页默认 28 列全显**。属注释/代码漂移, 与选择器改造独立, 入池 issue `26-10-12-1911-docs-webui-torrent-column-default-hidden`(type=docs / tier=light / **Open, 未认领**, 两方向待定调)。范围守恒: 只记不改。

## 实现计划

本轮无实施(纯调研 + 入池)。若用户拍板实施, 报告 §8 已给四波拆解:

| 波次 | 内容 | 触碰点 |
|---|---|---|
| W1 | 数据源收敛: `tableDefs` → 增加 `tableDefFor(page)`; `openColMenuAt` 消费 `page`; `toggleColMenu` 传当前表 id | `columns.js` / `topbar.html` |
| W2 | 弹层 IA: 检索框 + 分类折叠 + 组头计数 + 三态 + 「重置本表显隐」; 分组元数据单点 | `topbar.html` / `columns.js` / 三皮肤 CSS |
| W3 | 入口统一: 顶栏按钮标注当前表名; 抽屉/变体表头右键复用同一弹层 | `topbar.html` / `menu.js` |
| W4 | 测试迁移: `e2e/column-prefs.spec.mjs` 的**全局下标取项**改「分组 + 标签」定位; `e2e/drawer-tables.spec.mjs` 的「主选择器含抽屉三组」断言改为「抽屉表头右键可恢复」; `tableDefs` 形态守阵同步 | `e2e/` / `tests/test_webui_static_skins.py` / `tests/test_web_shortcuts.py` |

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| R1 | 现状取证(注册表规模 / 弹层规格 / 入口 / 测试面) | 完成(2026-10-12) |
| R2 | 业界方案调研(6 模式) + 8 维对比矩阵 | 完成(2026-10-12) |
| R3 | 报告成文([26-10-12-1854](../reports/26-10-12-1854-report-webui-column-picker-redesign.html)) | 完成(2026-10-12) |
| R4 | 附带发现入池(issue 26-10-12-1911) | 完成(2026-10-12) |
| W1-W4 | 重设计实施 | 未排期(待用户拍板) |

## 进度日志

- 2026-10-12 18:54 开工同步(`已同步 94e7ca62`); 取证现状(注册表 16 表 / 107 列 / 弹层规格 / 两条入口 / 测试面)并产出报告 [26-10-12-1854](../reports/26-10-12-1854-report-webui-column-picker-redesign.html)(dark 主题单文件 HTML, doc-topic `webui-column-picker`); `kb.index` 重建 + `kb.check` / `doc.links` 全绿。**零代码改动。**
- 2026-10-12 19:11 用户令「入池issue, 然后提交」⇒ 开工同步(远端领先 1 笔, 快进 `94e7ca62→7aef8bc2`, 本地未提交改动原样保留)后入池 issue `26-10-12-1911-docs-webui-torrent-column-default-hidden`(type=docs / tier=light / **Open, 未认领** / topic `webui-column-picker`); 正文按 L1 便签档补齐(现象 + 位置/grep 锚点 + 两方向建议待定调 + 报告回引)。收尾: 立本档案(**阈值 #4 命中** —— 已产出 `reports/` HTML 制品) + activeContext 切片 [26-10-12-1912](../activeContext/26-10-12-1912-webui-column-picker.md) + `kb.index` 重建。**纯文档轮: 零代码零测试改动, 不新建基线切片**(数字引用 `commands run kb.baseline`)。

# 能力判据源分裂: 视觉侧硬编码 + 行为侧门控 = 「看着能点、点了没反应」的静默全灭

> 摘要: 能力判据源分裂: 视觉侧硬编码 + 行为侧门控 = 「看着能点、点了没反应」的静默全灭
> 触发: 补门控, a11y 补课, headActivate, col.sortable, sortable, thead, 表头排序失效, 点了没反应, 视觉与行为分叉, 判据同源, 唯一调用方
**Refs:** memory-bank/issues/26-10-29-1348-bug-b-r23b10-aqtable-hr-sort-dead.html

### 模板/样式侧硬编码「能力提示」+ 行为侧按数据标记门控, 两半各取一个判据源

- **触发**: 给既有交互补门控(表头 a11y 补课把列头点击统一收进 `headActivate` 并新增 `if (!col.sortable) return;`, e33a8996 / issue 26-10-12-0800)时, 模板侧仍保留旧口径的「能力提示」—— thead 分支硬编码 `class="sortable"` 且排序箭头恒渲染(靠 CSS opacity 藏非激活箭头); 而 thead 唯一调用方(HR 详情表)的列定义恰好整列无 `sortable` 标记。视觉侧与行为侧各取一个判据源, 门控上线那一刻 HR 表排序整表静默失效(issue 26-10-29-1348, 潜伏约两周)。
- **判别**: ①症状是「看着能点、点了没反应」—— 无报错/无白屏/无 console 输出, CSS 把语义错误藏成纯视觉问题; ②grep 同一判据词在「模板分支」与「行为入口」的出现位置不对称: 一边写死、一边读数据标记; ③静态守阵全绿(守阵断的是源码字面, 断不出两个判据源彼此一致), 只有真浏览器点击路径现形; ④门控上线时若唯一调用方不满足判据, 表现为**功能当场全灭**而非部分退化 —— 盘「调用方 × 判据」矩阵比看单点更可靠。
- **处置**: 判据单点落数据声明(列定义/能力注册表是唯一事实源), 模板与行为全由它驱动 —— sortable 类/箭头位/tabindex/aria-sort/点击门控同读 `col.sortable`, 模板禁止硬编码。门控上线前盘一遍当前**全部调用方**的数据是否满足门控; 不满足宁可显式降级(摘掉提示/样式)也不留「能看不能点」的半态。
- **守阵**: `tests/test_webui_static_skins.py::test_frontend_table_shell_single_point` ④ + `test_frontend_hr_table_sort_filter_reorg_wiring` §2 —— 模板侧断 thead 分支 `:class="{ sortable: col.sortable, ... }"` 与箭头 `v-if="col.sortable"`(硬编码回潮即红), 数据侧断「声明 sortable 的列在能力注册表确有支持」(HRS_SORT_VAL 访问器对账, 防反向漂移: 标了 sortable 但能力函数不支持该 key, 点下去 hrsCompareRows 取 undefined 直接 TypeError)。红验两轮: 突变①markup 回潮 → 2 failed 恰落新断言; 突变②列定义摘标记 → 1 failed 红在计数断言。
- **复发**: 0

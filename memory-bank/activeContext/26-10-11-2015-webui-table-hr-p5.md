# WEBUI 表格公共组件 · 设置页 HR 表接入(P5)

> 摘要: 专题 `webui-table-component` 续作。计划 [26-10-11-1722](../plans/26-10-11-1722-plan-webui-table-component.html) 的 **P5 已落地**(设置页 HR 表接入, 口径经用户拍板「复用表壳 · th 模式」)。`<aq-table>` 加 **thead 模式**(同一表壳的第二根 = 原生 `<table>` 表头行), HR 详情表表头借壳渲染 —— 关键机制: 根模板是 in-DOM 的, 自定义元素直接放 `<thead>` 会被浏览器 **foster-parent 移出表格**, 占位必须写成 `<tr is="vue:aq-table" mode="thead">`; HR 三张表列定义单点进 `hr_status.js` 的 `HR_TABLE_DEFS`(与 `TABLE_DEFS` 同形但独立, 不进 `TABLE_PAGES`), 波次表表头改注册表 `v-for`, 排序仍走 `hrsSetSort`(D3=B), 死件 `hrsArrowHref` 退役; 守阵同轮改版 4 条(全红绿双验)。验收: 真浏览器 A/B 表头 DOM **逐字节等价**(表① outerHTML + 子节点骨架、表② outerHTML 与 HEAD 相同)+ e2e 与上片基线一致 + 覆盖率四项与上片逐位相同, 数字见 `commands run kb.baseline`。P6 待续。
> 最后活动: 2026-10-11 20:15

## 正在进行

- P5 已落地。P6 = 详情面板只留前向契约(零代码迁移, D4=A)。
- 本会话实测数字见 `commands run kb.baseline`。工作树含全部改动, 等用户显式说「提交」再 `ship.commit`。

## 关键结论

- **in-DOM 表内容模型是硬约束**: 根模板是 `#app` innerHTML(boot.js 先 `insertAdjacentHTML` 注入分片), 浏览器解析遵守表格内容模型 —— 自定义元素放 `<thead>`/`<table>` 里被 **foster-parent 移出表格**(表头整段消失、无报错, pytest 全绿); `<slot>` 方案也不可行(slot 内容在非表格上下文被按 in-body 解析, `<tr>` 被直接丢弃)。**唯一通路 = `<tr is="vue:aq-table">` 占位**(合法 `<tr>` + `vue:` 前缀让编译器当组件; 已核 vendored vue.global.prod.js 确实认 `vue:` 并置 tagType=COMPONENT)。
- **HR 表注册表与 `TABLE_DEFS` 同形但独立**: `TABLE_PAGES = Object.keys(TABLE_DEFS)` 驱动列选择器 / 列对齐 / 列偏好持久化, HR 表收进去 = 设置页多出三个列分组(观感变化) ⇒ `HR_TABLE_DEFS` 自成一张, `hrsCols()`/`hrsWaveCols()` 只做取数视图。
- **D3=B 的边界**: 「排序仍走 HR 自己的实现」指**三态状态机** `hrsSetSort`(逐站点独立 + 空值恒末位, 与主表语义不同); 箭头 href 的解析(`sortKey===key && dir===1 ? up : down`)是展示层, 并入表壳与主视图同源, 顺带删掉死件 `hrsArrowHref`。
- **v-for 会插零长文本锚点**: 纯 `v-for` 2 个(fragment start/end); `v-for` 里再有 `v-if/v-else` 每次迭代再插 2 个(分支切换靠锚点定位)⇒ 表② 8 列两支 = 18 个。`outerHTML` 序列化不含、CSS 表格修正对 whitespace-only 文本不参与布局 ⇒ 视觉/行为零影响, 但**子节点骨架**比对即见 —— 「DOM 逐字节等价」在骨架层面与 v-for 化不可兼得, 已记计划 §09 + 基线切片。连带修正 P2 的一个错误结论(「Vue 对 v-for 根片段不插占位节点」—— 当时 A/B 两侧都是同一个 v-for, 锚点相消所以 diff=0, 并不能证明"不插")。
- **`:class="{num}"` 与静态字面不等价**: normalizeClass 恒回字符串, 非 num 列会渲出空 `class=""`; 要逐字节等价就走 `v-if` 两支, 且 `v-for` 的 `<template>` 内不留换行缩进(空白被折成零长文本节点)。
- **守阵同轮改版 4 条**(不是放宽, 全红绿双验过): shell 单点守阵增 ④thead 分支与占位形态 + 内联 `<th>` 零残留; HR 排序守阵表头断言从「锚段 markup 字面」改为「锚段接线 + 表壳模板 markup」, 十列键改扫 `HR_TABLE_DEFS.hrDetail`, `hrsArrowHref` 进死代码零残留; diag 守阵增 `hrsWaveCols()`; 保留前缀守阵白名单并入 `$emit`。
- **e2e 首轮 1 failed 是已知抖动**: `delta-sync.spec.mjs:170`(prism)8s 轮询超时, 与既有 issue `26-10-11-1825-test-delta-sync-full-round-flake` 同签名(18:25 入池, 早于本轮); 隔离重跑 B 侧 3 次 + A(HEAD)侧 3 次均 8/8 绿, 复跑全量 158/0/10 与上片基线逐位一致 ⇒ 非本轮引入。
- **顺带发现(已入池, 待认领)**: `test_frontend_template_no_reserved_prefix_identifiers` 的**指令表达式分支是死的** —— 正则 `\s*=\s*(["'])(.*?)\1` 的捕获组 1 是引号本身, 守阵却读 `m.group(1)` 当表达式(表达式在组 2) ⇒ `@click="_x()"` 这类指令形态从未被真正检出(docstring 宣称覆盖)。按「范围守恒」一行未改, 证据/根因/建议修法见 issue [26-10-11-2030-test-guard-reserved-prefix-directive-dead](../issues/26-10-11-2030-test-guard-reserved-prefix-directive-dead.html)。

## 坑与意外

- **探针不依赖桩数据**: 桩 `--hr-scene on` 只灌 HR 历史事件(表③), **不灌逐站点清单**(表①)⇒ 表① 只渲空态, 靠桩做 A/B 等价不可行。改走自包含探针: 读盘上两侧真实 `settings-detail.html` 锚段里的 `<thead>`, `page.setContent` → 浏览器解析 → `mount("#app")` 用 innerHTML 编译, 混入真 `table.js`/`hr_status.js` —— 走的就是真 in-DOM 解析路径, 且两侧 markup 都来自真实文件。
- **A/B 的 dump 别放 `test-results/`**(Playwright 每轮清空)—— 延用上片结论, 本轮 dump 落 `/tmp`。
- 计划改动面写两文件, 实际扩到 `table.js`/`xtpl.html`(thead 模式本体)+ 4 条守阵 —— 开工先问口径再动手, 避免按字面两文件硬做。

# 26-10-11-webui-frozen-col-boundary — 首列吸左边界提示(横滚残根被读成"状态列被名称列盖住")

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-11 04:07
**Topics:** webui-frozen-col-boundary
**Summary:** 用户报「WEBUI 向右滚动时状态栏会被名称栏遮挡」并附截图。取证(桩服务真浏览器探针 + 截图)确认不是 z 序/层叠 bug: 吸左首格(issue 26-10-06-1717)横滚时相邻列从其下方滑过是冻结列的正确行为, 但未盖满的尾字("做种"的"种"、"下载"的"载")紧贴首格右缘露出, 与名称省略号之间无任何分隔, 读成"名称后面多了个坏字"。修 = 横滚非零时给吸左首格画右缘落影 + 发丝线, 让残根读成 pane 边界: 三个横滚同步单点(`sync*HeadScroll`: menu/selection/shows.js)给 `.group-table` 与吸顶表头打 `.is-hscrolled`(scrollLeft>0 打 / 回 0 摘), 三皮肤 `css/views.css` 据此给行吸左首格与表头吸左首格成对落规则。**用户复报「小窗时站点的徽标不会被名称列挡住」**: 根因 = `.group-row { align-items: center }` 网格项不拉伸, 吸左首格只有单行内容高(实测 22px), 站点/标签多 chip 格换行撑高行(实测 71px)后 chip 从首格上下两段成排漏出; 修 = 首格 `align-self: stretch`(行 padding 14px ≥ 圆角半径, 方角不戳行缘)。机理入坑档 `pitfalls/web-ui/frozen-column.md`(第④⑤条)。test.full 全绿(见基线切片)。
**Refs:** memory-bank/testing/baselines/26-10-11-0354-webui-frozen-col-boundary.md,memory-bank/pitfalls/web-ui/frozen-column.md,memory-bank/activeContext/26-10-11-0354-webui-frozen-col-boundary.md

## 原始请求

> 用户(2026-10-11): 「WEBUI向右滚动时状态栏会被名称栏遮挡, 修复」
> 用户(2026-10-11, 追问答复): 「全部UI, 种子页+辅种页」「表格里的『状态』列被名称列盖住」「大小窗都触发」+ 截图(暗色, 横滚后名称省略号后露出孤字"截/种")

## 思考过程与决策

- **取证路径**: 先按字面理解成"底部状态栏被盖" —— 三皮肤 × 三视图真浏览器探针(elementFromPoint 扫状态栏带 + 全视图扫描)全部显示状态栏 z 序正常, 一度无法复现。追问 + 截图后语义改判: "状态栏"= 表格的**「状态」列**, "名称栏"= 吸左的名称列。
- **根因**: 横滚时相邻列滑进吸左首格下方属冻结列正确行为(首格不透明 + z2, 见坑档②), 但**边界没有任何视觉线索** —— 滑入过渡期未盖满的尾字紧贴首格右缘露出, 读成渲染错乱。用户列序"状态"紧跟"名称"时首当其冲(默认列序"大小"紧跟时同理, 探针截到".00 GiB"残根)。
- **方案**: 不动冻结列行为本身(用户自请的特性), 补**边界落影 + 发丝线**(ag-grid/DataTables 同款处理): CSS 感知不了 scrollLeft, 借三个 `sync*HeadScroll` 单点打标; 行与表头首格成对(表头首格是 translateX 桥接, 不在滚动容器内, 必须单独打)。
- **红验**: 新守阵 `test_frontend_frozen_column_boundary_wiring` 摘掉 shows.js 的表头打标即红、还原即绿。

## 实现计划

- **S1** JS: menu.js / selection.js / shows.js 三个 `sync*HeadScroll` 各加两行 is-hscrolled 打标。
- **S2** CSS: 三皮肤 `css/views.css` 各加一条 `.is-hscrolled` 规则(行首格 + 表头首格成对)。
- **S2b** 用户复报「小窗时站点徽标漏出」: 三皮肤吸左首格补 `align-self: stretch`(行 align-items:center 不拉伸, 高行盖不住)。
- **S3** 守阵: `test_webui_static_skins.py` 新增静态接线守阵(含 stretch 断言) + 文件头测试计划同步。
- **S4** 验证 + 收尾: 真浏览器截图验证 / e2e fast / test.full 基线 / 坑档 / 档案 / 切片 / kb.index。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 三处 sync*HeadScroll 打标 | Done |
| S2 | 三皮肤 .is-hscrolled 边界规则 | Done |
| S2b | 吸左首格 align-self: stretch | Done |
| S3 | 静态守阵 + 红验 | Done |
| S4 | 验证 + 知识库收尾 | Done |

## 进度日志

- **2026-10-11 03:54** 全部落地。开工 sync 快进 8503f4d5→86138d33 → 字面理解"底部状态栏被盖"探针未复现 → 用户截图改判"状态列残根" → 复现(frozen-060: 名称后粘连".00 GiB") → JS 打标 ×3 + CSS 边界落影 ×3 皮肤 → 真浏览器暗/亮主题截图验证(残根渐隐、回 0 无绘制) → e2e fast 60 passed → test.full 全绿(基线切片 26-10-11-0354) → 坑档 frozen-column.md 补第④条 → kb.index 重建。
- **2026-10-11 04:07** 用户复报「小窗时站点的徽标不会被名称列挡住」→ 真浏览器注入多 chip 复现(`.group-row { align-items: center }` 网格项不拉伸, 首格 22px vs 行 71px, chip 上下两段成排漏出) → 三皮肤吸左首格补 `align-self: stretch` → 骑线位置截图对比(修复前徽标透出/修复后全盖, 只剩骑线残根在落影内渐隐) → 守阵补 stretch 断言 → e2e fast 60 passed → test.full 3113 passed 持平(基线切片更新) → 坑档补第⑤条 → kb.index 重建。

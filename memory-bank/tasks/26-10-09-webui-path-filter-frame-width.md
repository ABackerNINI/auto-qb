# 26-10-09-webui-path-filter-frame-width — 路径筛选强调框宽度贴文字(去列宽跟随)

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09 21:12
**Topics:** webui-filter-cell
**Summary:** 用户报「点击路径筛选后匹配的路径强调框宽度错误, 跟随保存路径栏宽度而不是文字宽度」。根因: `.f-cell.f-on` 的 inset 描边挂在 grid 行里被拉满列宽的 `.g-save-path` 单元格 div 上, 框随列宽 —— 与 `.m-dur` 整格线曾挂错位置的同一教训(彼时只写在模板注释, 未入坑档)。修法照 `.dur-body` 成法: 保存路径文字包 `<span class="sp-body f-cell">` 内联块包裹层, `f-cell`/`f-on`/点击/省略全部上移(torrents.html + groups.html 两处模板), 三皮肤 views.css 各增一条 `.g-save-path .sp-body` 规则(单页应用全局生效, 每皮肤一处; atlas/components.css 已顶 700 行上限不新增)。改动 5 个源文件, 静态守阵 69 绿, test.full 全绿(见基线切片)。
**Refs:** memory-bank/testing/baselines/26-10-09-2112-webui-path-filter-frame-width.md,memory-bank/pitfalls/web-ui/cell-frame-vs-text-width.md

## 原始请求

> 用户(2026-10-09): 「WEBUI点击路径筛选后匹配的路径强调框宽度错误, 当前宽度跟随保存路径栏宽度而不是文字宽度」

## 思考过程与决策

- **定位**: 模板 grep `f-on` —— chip 类(site/tag/cat)是 inline 元素天然贴文字; 仅 `.g-save-path f-cell`(torrents.html / groups.html 各一处)是块级 div 直接承载 `f-cell`, 被 grid 拉满列宽。
- **成法复用**: torrents.html 里 `.m-dur` 注释早已记录同族教训(「整格线必须挂 .dur-body(文字包裹层)」)—— 本次是它在筛选强调框上的同族复发, 教训此前未入 pitfalls(路由不到), 已补档。
- **落点选择**: 新规则每皮肤只放 views.css 一处(单页应用一次加载全部 CSS); atlas/css/components.css 实测 697 行, 顶 700 行体量守阵, 严禁往里加。
- **省略号随框走**: 包裹层自带 max-width:100% + ellipsis —— 短路径框贴文字, 超长路径铺满整列并省略, 行为两头正确。

## 实现计划

- **S1** 模板: torrents.html / groups.html 保存路径格包 `sp-body` 包裹层。
- **S2** CSS: 三皮肤 views.css 各增 `.g-save-path .sp-body` 规则。
- **S3** 验证: webui 静态守阵 + test.full + 基线切片。
- **S4** 收尾: 坑档 + 任务档案 + 切片 + kb.index。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S1 | 模板包裹层(2 份) | Done |
| S2 | 三皮肤 views.css 规则 | Done |
| S3 | 静态守阵 + test.full + 基线 | Done |
| S4 | 坑档 + 档案 + 切片 + kb.index | Done |

## 进度日志

- **2026-10-09 21:12** 全部落地。同步(快进 22988fce→aec6e2e8)→ 定位 → S1/S2 五文件改动 → `test.one -k webui_static` 69 passed → `test.full` 2870 passed + 4 skipped, TOTAL 99%(基线切片 26-10-09-2112)→ 坑档 `pitfalls/web-ui/cell-frame-vs-text-width.md` 入库 → `kb.index` 重建。真机视觉核验待用户刷新页面目检(静态守阵不覆盖渲染宽度)。用户未下「提交」指令, 工作树保持未提交现状。

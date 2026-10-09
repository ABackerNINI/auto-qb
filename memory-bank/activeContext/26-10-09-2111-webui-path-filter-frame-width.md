# webui 路径筛选强调框宽度贴文字

> 摘要: 用户报「点击路径筛选后匹配的路径强调框宽度跟随保存路径栏宽度而不是文字宽度」→ 根因是 `.f-cell.f-on` 的 inset 描边挂在 grid 拉满列宽的 `.g-save-path` 单元格 div 上; 修法照 `.m-dur` 的 `.dur-body` 成法, 文字包 `sp-body` 内联块包裹层承载强调(torrents/groups 两模板 + 三皮肤 views.css)。根因与修法见坑档(单点)与任务档案, 本切片只留会话滚动状态。
> 最后活动: 2026-10-09 21:12

**Refs:** memory-bank/tasks/26-10-09-webui-path-filter-frame-width.md,memory-bank/pitfalls/web-ui/cell-frame-vs-text-width.md,memory-bank/testing/baselines/26-10-09-2112-webui-path-filter-frame-width.md

## 已完成

- 修复落地: shared/tpl/torrents.html + groups.html 保存路径格包 `<span class="sp-body f-cell">`; 三皮肤(atlas/console/prism)views.css 各增 `.g-save-path .sp-body` 规则(max-width:100% + ellipsis, 短路径贴文字、超长铺满整列省略)。
- 验证: `test.one -k webui_static` 69 passed(含 700 行体量守阵); `test.full` 2870 passed + 4 skipped, TOTAL 99%(见基线切片 26-10-09-2112)。
- 回写: 坑档 `pitfalls/web-ui/cell-frame-vs-text-width.md` 入库(.dur-body 同族教训首次进坑档) + 任务档案 + 基线切片; `kb.index` 已重建。

## 正在进行

- (无 —— 修复与回写已收口; 用户未下「提交」指令, 工作树保持未提交改动现状)

## 下一步(候选, 未认领)

- 用户刷新页面目检三皮肤下强调框宽度(静态守阵不覆盖渲染宽度; 若还有视觉偏差按坑档判据复查)。

# WEBUI 挂件点击即筛选(站点/标签/分类/路径)

> 摘要: 表格里点 站点/标签/分类/路径 挂件 = 切换顶栏筛选弹层里的对应值(toggle 语义, 再点取消)。单点 `filters.js::filterFromChip`(kind→field 查 filterDefs, 复用 toggleFilterValue); 挂件 `@click.stop` 镜像补收浮层; f-on=inset currentColor 环 + f-cell 文本格, 三皮肤 CSS 成对(atlas 规则放 views.css —— components.css 顶格 700 行 cap)。15 处挂件覆盖 组级/明细/种子页/追剧。档案: tasks/26-09-29-webui-chip-click-filter.md
> 最后活动: 2026-09-29 23:54

## 已完成

- 功能落地并全量验证(1760 passed + 2 skipped / 91%): 实现计划、守阵红转绿经过、决策理由见任务档案。
- 回写: modules/webui-static-contract.md「挂件点击即筛选」bullet + README「批量操作利落」句 + 基线切片 26-09-30-0009。
- 真浏览器冒烟: 桩数据 14/14 + 三皮肤挂载 3/3(pageerror=0)。注意: 8127 是运行中的生产实例, 冒烟桩固定用 8201。
- 已触发「提交」: 合入远端 58d72e0a(模板相邻 hunk 手工合流, 提示 title 遵 hr-tooltip-overlap 口径摘除), 闸门全绿(1768 passed), 由 ship.commit 入库。

## 正在进行

- 无 —— 等用户真机验一眼(三皮肤观感: 悬停亮度/选中环)。

## 下一步(候选, 未拍板)

- `+N` 折叠 chip 点击开对应筛选弹层 —— 需要给 .pop-menu 一条「行内锚点」定位路径, 单独拍板再做。

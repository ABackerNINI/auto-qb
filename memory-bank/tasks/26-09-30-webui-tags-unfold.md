# 26-09-30-webui-tags-unfold — WEBUI 标签列全量展开(+N 折叠移除)

**Status:** Done
**Added:** 2026-09-30
**Updated:** 2026-09-30 18:53
**Topics:** webui-tags-unfold
**Summary:** 用户要求标签不再折叠成「+1/+2」。移除 4 处模板的 tagSlice/slice 截断与 `+N` 徽标(tags 超过 3/2 个时只显示前几个), 改为 `v-for` 全量渲染; 三皮肤 `.g-tags, .m-tags` 加 `flex-wrap: wrap`(标签多时列内换行完整显示, 行高逐行实测的虚拟滚动可承接变高行), 清掉 `.tag-more` 死样式; decorate.js 删只为折叠服务的 tagSlice()。单个超长标签仍是 ellipsis(完整值在悬浮), 只移除数量折叠。

## 原始请求

> WEBUI标签改为不隐藏为+1/+2

## 思考过程与决策

- **意图判定**: 「标签」指 qBittorrent 种子标签(tag 列), 非页签; 现状是 tags 超过 3 个(组级/明细表)或 2 个(成员/追剧)就折叠成「+N」计数徽标 —— 「不隐藏为+1/+2」即不再折叠, 全量展示。
- **换行 vs 截断**: 只删截断不换行的话, 超出列宽的 chip 仍被容器 `overflow: hidden` 静默裁掉, 等于没解决。行高是逐行实测制(`state.js` `_rowHs` 逐行真值 + `_rowHVer` 触发窗口重算), 变高行可承接 ⇒ 选 `flex-wrap: wrap` 全量展开。行会变高, 属展开显示的预期代价。
- **CSS 位置**: `.g-tags, .m-tags` 规则三皮肤各一份(atlas/console components.css, prism views.css), 成对同改; `align-content: center` 让多行 chip 在行内垂直居中。
- **死样式清扫**: `.tag-more` 规则三皮肤 + atlas views.css 共享选择器里的残留一并清掉。
- **关联**: tasks/26-09-29-webui-chip-click-filter 的「不做」项「+N 折叠 chip 不接点击」随本改动失效(该 chip 不存在了), 已在该档案标注。

## 实现计划

1. `shared/decorate.js`: 删 `tagSlice()`。
2. `shared/tpl/{torrents,groups,shows}.html` 4 处: `v-for` 全量 + 删 `+N` 徽标行。
3. 三皮肤 CSS: `.g-tags, .m-tags` 加 wrap; 清 `.tag-more`。
4. 验证: grep 无残留 + test.full 全绿。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 4 处模板全量渲染 | ✅ |
| 2 | decorate.js 删 tagSlice | ✅ |
| 3 | 三皮肤 CSS wrap + 清死样式 | ✅ |
| 4 | test.full 全绿 + 基线切片 | ✅ |

## 进度日志

- 2026-09-30 18:53: 开工 sync 至 74fc151c; 一次性落全部改动, grep 确认 tagSlice/tag-more 零残留。
- 2026-09-30 「提交」触发: sync 合入远端 02a8e5d9; 首跑 test.full 1 失败 = 远端带入的 `plans/26-09-30-1819-plan-kernel-module-refactor.html` doc-refs 写了裸文件名(守卫要求仓库根相对路径)且三个目标未反向声明 —— 认领链补闭环后全绿(见基线切片); 修复为独立 📝 提交, 不混入本档案主提交。
